#!/usr/bin/env python3
"""One-server-at-a-time launch matrix harness.

Runs a llama-server arm, waits for /health, sends a fixed prompt via
/completion, records timings + placement, terminates the captured process
group, and writes runs/<arm>/result.json.

The harness is deliberately model-agnostic: argv/env come from matrix.json.
It is intended to be run under the orchestrator region-lock:

  region-lock run --cpu-list 0-95 --gpu-quiet shared --role bench \
      -- python3 harness.py --phase cpu
  region-lock run --gpu-quiet exclusive --role bench-gpu \
      -- python3 harness.py --phase gpu
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"
STOP = ROOT / "STOP"

CPU_MODEL = "/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
CPU_MTP = "/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf"
GPU_MODEL = "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf"
GPU_DFLASH = "/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf"

CPU_STORE = "/mnt/raid0/llm/kernels/builds/cpu-20261105-65da39eb1-c6fold2"
CPU_FA_STORE = "/mnt/raid0/llm/kernels/builds/cpu-20261031-729599d69-c6-iqkfa-on"
GPU_STORE = "/mnt/raid0/llm/kernels/builds/gpu-20261106-65da39eb1-c6fold2"

CPU_ENV = {
    "GGML_FA_SPLIT_KV": "0",
    "GGML_FUSED_DECODE_OFF": "1",
    "GGML_IQK": "1",
    "GGML_NOHUGEPAGE_PROCESS": "1",
    "OMP_DYNAMIC": "false",
    "OMP_PLACES": "cores",
    "OMP_PROC_BIND": "spread",
    "OMP_WAIT_POLICY": "active",
}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def http_json(url: str, payload=None, timeout: float = 7200):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def http_text(url: str, timeout: float = 30) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read().decode(errors="replace")


def wait_health(port: int, proc: subprocess.Popen, log_path: Path, timeout: float = 1200) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited rc={proc.returncode}; log tail:\n{tail(log_path, 80)}")
        try:
            d = http_json(f"http://127.0.0.1:{port}/health", timeout=5)
            if d.get("status") == "ok":
                return
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(f"server did not become healthy on :{port} in {timeout}s")


def tail(path: Path, n: int = 120) -> str:
    try:
        lines = path.read_text(errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return ""


def build_argv(cfg: dict) -> list[str]:
    store = Path(cfg["store"])
    argv: list[str] = []
    if cfg.get("cpu_list"):
        argv += ["taskset", "-c", str(cfg["cpu_list"])]
    if cfg.get("interleave"):
        argv += ["numactl", "--interleave=all"]
    argv += [
        str(store / "bin" / "llama-server"),
        "-m", cfg["model"],
        "-np", str(cfg["np"]),
        "-c", str(cfg["ctx"]),
        "-t", str(cfg["threads"]),
        "-tb", str(cfg["threads"]),
        "-b", str(cfg.get("batch", 2048)),
        "-ub", str(cfg.get("ubatch", 512)),
        "-ctk", cfg.get("ctk", "f16"),
        "-ctv", cfg.get("ctv", "f16"),
        "--device", cfg.get("device", "none"),
        "-ngl", str(cfg.get("ngl", 0)),
        "-fa", "on",
        "--host", "127.0.0.1",
        "--port", str(cfg["port"]),
        "--metrics",
        "--slots",
    ]
    spec = cfg.get("spec", "none")
    if spec == "draft-mtp":
        argv += [
            "-md", cfg["drafter"],
            "-ngld", "0",
            "--spec-type", "draft-mtp",
            "--spec-draft-n-max", str(cfg.get("draft_n_max", 4)),
            "--device-draft", "none",
            "--draft-p-min", str(cfg.get("draft_p_min", 0.5)),
        ]
    elif spec == "draft-dflash":
        argv += [
            "-md", cfg["drafter"],
            "-ngld", str(cfg.get("ngld", 99)),
            "--spec-type", "draft-dflash",
            "--spec-draft-n-max", str(cfg.get("draft_n_max", 8)),
        ]
    elif spec != "none":
        raise ValueError(f"unknown spec {spec!r}")
    argv += ["--kv-unified" if cfg.get("kv_unified") else "--no-kv-unified"]
    if cfg.get("kind") == "cpu":
        argv += [
            "-lv", "4",
            "--load-threads", str(cfg.get("load_threads", 96)),
            "--no-mmap",
            "--no-webui",
        ]
    argv += list(cfg.get("extra_flags", []))
    return argv


def build_env(cfg: dict) -> dict:
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(("GGML_", "OMP_")) or key in ("LD_LIBRARY_PATH", "HSA_OVERRIDE_GFX_VERSION"):
            env.pop(key, None)
    env["LD_LIBRARY_PATH"] = str(Path(cfg["store"]) / "bin")
    env.update({k: str(v) for k, v in (cfg.get("env") or {}).items()})
    if cfg.get("kind") == "gpu":
        env.pop("HSA_OVERRIDE_GFX_VERSION", None)
    return env


def capture_process(pid: int) -> dict:
    out = {"pid": pid, "status": {}, "task_masks": {}, "numastat": ""}
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith(("THP_enabled:", "Cpus_allowed_list:", "Mems_allowed_list:", "VmRSS:", "Threads:")):
                k, v = line.split(":", 1)
                out["status"][k] = v.strip()
    except Exception as e:
        out["status_error"] = repr(e)
    try:
        masks: dict[str, int] = {}
        for t in Path(f"/proc/{pid}/task").iterdir():
            try:
                for line in (t / "status").read_text().splitlines():
                    if line.startswith("Cpus_allowed_list:"):
                        m = line.split(":", 1)[1].strip()
                        masks[m] = masks.get(m, 0) + 1
                        break
            except Exception:
                pass
        out["task_masks"] = masks
    except Exception as e:
        out["task_masks_error"] = repr(e)
    try:
        out["numastat"] = subprocess.run(
            ["numastat", "-p", str(pid)], capture_output=True, text=True, timeout=30
        ).stdout
    except Exception as e:
        out["numastat_error"] = repr(e)
    return out


def capture_gpu(pid: int) -> dict:
    out = {"kfd_pids": [], "rocm_smi": ""}
    try:
        out["kfd_pids"] = sorted(os.listdir("/sys/class/kfd/kfd/proc"))
    except Exception as e:
        out["kfd_error"] = repr(e)
    try:
        out["rocm_smi"] = subprocess.run(
            ["rocm-smi", "--showuse", "--showmemuse", "--showpower", "--showclocks"],
            capture_output=True, text=True, timeout=30,
        ).stdout
    except Exception as e:
        out["rocm_smi_error"] = repr(e)
    return out


def parse_numastat_max_dev(text: str):
    for line in text.splitlines():
        s = line.split()
        if len(s) >= 6 and s[0] == "Total":
            try:
                vals = [float(x) for x in s[1:-1]]
                total = float(s[-1])
                if total <= 0 or not vals:
                    return None
                n = len(vals)
                return round(max(abs(v / total - 1.0 / n) for v in vals) * 100.0, 2)
            except Exception:
                return None
    return None


def parse_acceptance(log_path: Path):
    try:
        text = log_path.read_text(errors="replace")
    except Exception:
        return None
    matches = re.findall(
        r"draft acceptance = ([0-9.]+)\s*\(\s*([0-9]+) accepted\s*/\s*([0-9]+) generated\)",
        text,
    )
    if not matches:
        return None
    alpha, acc, gen = matches[-1]
    return {"alpha": float(alpha), "accepted": int(acc), "generated": int(gen)}


def completion(port: int, prompt: str, n_predict: int, cache_prompt: bool) -> dict:
    body = {
        "prompt": prompt,
        "n_predict": n_predict,
        "temperature": 0.0,
        "top_k": 1,
        "top_p": 0.95,
        "stream": False,
        "cache_prompt": cache_prompt,
    }
    t0 = time.time()
    try:
        d = http_json(f"http://127.0.0.1:{port}/completion", body, timeout=7200)
        content = d.get("content", "")
        return {
            "ok": True,
            "wall_s": round(time.time() - t0, 3),
            "timings": d.get("timings"),
            "stop_reason": d.get("stop_reason"),
            "tokens_predicted": d.get("tokens_predicted"),
            "tokens_evaluated": d.get("tokens_evaluated"),
            "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
            "content_chars": len(content),
        }
    except Exception as e:
        return {"ok": False, "wall_s": round(time.time() - t0, 3), "error": repr(e)}


def terminate(proc: subprocess.Popen, log_path: Path) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    for _ in range(60):
        if proc.poll() is not None:
            return
        time.sleep(1)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=30)
    except Exception:
        pass


def select_props(d: dict) -> dict:
    keys = ("model_path", "build_info", "total_slots", "n_ctx")
    out = {k: d.get(k) for k in keys}
    g = d.get("default_generation_settings") or {}
    out["default_generation_settings"] = {
        k: g.get(k) for k in ("n_ctx", "n_predict", "n_batch", "n_ubatch", "n_parallel", "temperature", "top_k", "top_p")
    }
    return out


def run_arm(cfg: dict, run_dir: Path) -> dict:
    run_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    result = {
        "arm": cfg["name"],
        "phase": cfg.get("phase"),
        "config": cfg,
        "started_utc": now(),
        "ok": False,
    }
    if cfg.get("evict"):
        log(f"{cfg['name']}: evicting page cache")
        ev = subprocess.run(
            ["/mnt/raid0/llm/tmp/inf70/evict_nodes_force.sh", "58"],
            capture_output=True, text=True, timeout=1800,
        )
        ev_text = ev.stdout + ev.stderr
        (run_dir / "evict.log").write_text(ev_text)
        result["evict"] = {"rc": ev.returncode, "tail": ev_text[-3000:]}
    argv = build_argv(cfg)
    env = build_env(cfg)
    result["argv"] = argv
    log_path = run_dir / "server.log"
    log(f"{cfg['name']}: launching {argv[0]} ... :{cfg['port']}")
    proc = None
    try:
        with open(log_path, "w") as f:
            proc = subprocess.Popen(
                argv, env=env, stdout=f, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        result["pid"] = proc.pid
        wait_health(cfg["port"], proc, log_path, timeout=cfg.get("health_timeout_s", 1200))
        result["health"] = "ok"
        result["props"] = select_props(http_json(f"http://127.0.0.1:{cfg['port']}/props", timeout=60))
        result["slots_before"] = http_json(f"http://127.0.0.1:{cfg['port']}/slots", timeout=60)
        result["process_before"] = capture_process(proc.pid)
        if cfg.get("kind") == "gpu":
            result["gpu_before"] = capture_gpu(proc.pid)

        warm = cfg.get("warmup") or {}
        if warm.get("prompt"):
            warm_prompt = (ROOT / warm["prompt"]).read_text()
            log(f"{cfg['name']}: warmup n_predict={warm.get('n_predict', 16)}")
            result["warmup"] = completion(
                cfg["port"], warm_prompt, int(warm.get("n_predict", 16)), False
            )

        prompt = (ROOT / cfg["prompt"]).read_text()
        repeats = int(cfg.get("repeats", 1))
        reqs = []
        for i in range(repeats):
            log(f"{cfg['name']}: measured request {i + 1}/{repeats} (cache_prompt={i > 0})")
            reqs.append(completion(cfg["port"], prompt, int(cfg.get("n_predict", 256)), i > 0))
        result["requests"] = reqs
        result["slots_after"] = http_json(f"http://127.0.0.1:{cfg['port']}/slots", timeout=60)
        result["metrics_after"] = http_text(f"http://127.0.0.1:{cfg['port']}/metrics", timeout=60)
        result["process_after"] = capture_process(proc.pid)
        if cfg.get("kind") == "gpu":
            result["gpu_after"] = capture_gpu(proc.pid)
        result["acceptance"] = parse_acceptance(log_path)
        result["ok"] = all(r.get("ok") for r in reqs) if reqs else False
    except Exception as e:
        result["error"] = repr(e)
        result["ok"] = False
    finally:
        if proc is not None:
            terminate(proc, log_path)
            result["exit_code"] = proc.poll()
        result["elapsed_s"] = round(time.time() - started, 1)
        result["server_log_tail"] = tail(log_path, 160)
        (run_dir / "result.json").write_text(json.dumps(result, indent=1))
        log(f"{cfg['name']}: done ok={result.get('ok')} elapsed={result.get('elapsed_s')}s")
    return result


def tok_s_values(result: dict) -> list[float]:
    """Primary metric: the first measured request.

    Later requests are cache-prompt repeats; they can hit EOS early (the 32k
    arms did), so they are retained in result.json but not used for ranking.
    """
    for r in result.get("requests", []):
        t = (r.get("timings") or {})
        v = t.get("predicted_per_second")
        # llama.cpp's 1e6 sentinel means predicted_n=1/predicted_ms~0 (EOS on the
        # first token); those arms are invalid for throughput, not fast.
        if isinstance(v, (int, float)) and 0 < v < 100000:
            return [float(v)]
    return []


def write_summary() -> None:
    rows = []
    for rp in sorted(RUNS.glob("*/result.json")):
        try:
            r = json.loads(rp.read_text())
        except Exception:
            continue
        cfg = r.get("config", {})
        tps = tok_s_values(r)
        prompt_n = []
        predicted_n = []
        for q in r.get("requests", []):
            t = q.get("timings") or {}
            if isinstance(t.get("prompt_n"), int):
                prompt_n.append(t["prompt_n"])
            if isinstance(t.get("predicted_n"), int):
                predicted_n.append(t["predicted_n"])
        numa = r.get("process_after", {}).get("numastat", "") or r.get("process_before", {}).get("numastat", "")
        rows.append({
            "arm": r.get("arm"),
            "phase": r.get("phase"),
            "ok": r.get("ok"),
            "np": cfg.get("np"),
            "ctx": cfg.get("ctx"),
            "threads": cfg.get("threads"),
            "ctk": cfg.get("ctk"),
            "kv_unified": cfg.get("kv_unified"),
            "spec": cfg.get("spec"),
            "draft_n_max": cfg.get("draft_n_max"),
            "cpu_list": cfg.get("cpu_list"),
            "prompt_n": prompt_n,
            "predicted_n": predicted_n,
            "tok_s": [round(v, 3) for v in tps],
            "mean_tok_s": round(sum(tps) / len(tps), 3) if tps else None,
            "max_tok_s": round(max(tps), 3) if tps else None,
            "acceptance": r.get("acceptance"),
            "numastat_max_dev_pct": parse_numastat_max_dev(numa),
            "thp_enabled": (r.get("process_after", {}).get("status", {}) or {}).get("THP_enabled"),
            "task_masks": (r.get("process_after", {}).get("task_masks", {}) or {}),
            "elapsed_s": r.get("elapsed_s"),
            "error": r.get("error"),
        })
    (ROOT / "summary.json").write_text(json.dumps({"generated_utc": now(), "rows": rows}, indent=1))
    lines = [
        "# Local launch optimization — summary",
        "",
        f"Generated: {now()}",
        "",
        "| arm | phase | np | ctx | thr | KV | unified | spec | prompt_n | tok/s | mean | accept | NUMA dev% | THP |",
        "|---|---|---:|---:|---:|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(
            "| {arm} | {phase} | {np} | {ctx} | {threads} | {ctk} | {kv} | {spec}{nmax} | {pn} | {tps} | {mean} | {acc} | {numa} | {thp} |".format(
                arm=r["arm"], phase=r["phase"], np=r["np"], ctx=r["ctx"], threads=r["threads"],
                ctk=r["ctk"], kv=r["kv_unified"], spec=r["spec"],
                nmax=(f" n{r['draft_n_max']}" if r.get("draft_n_max") else ""),
                pn=r["prompt_n"], tps=r["tok_s"], mean=r["mean_tok_s"],
                acc=(r["acceptance"] or {}).get("alpha") if r.get("acceptance") else "",
                numa=r["numastat_max_dev_pct"], thp=r["thp_enabled"],
            )
        )
    (ROOT / "SUMMARY.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", default=str(ROOT / "matrix.json"))
    ap.add_argument("--phase", choices=["cpu", "gpu", "all"], default="all")
    ap.add_argument("--only", default=None, help="comma-separated arm names")
    ap.add_argument("--no-evict", action="store_true", help="skip the page-cache eviction step")
    ap.add_argument("--stop-file", default=str(STOP))
    args = ap.parse_args()

    matrix = json.loads(Path(args.matrix).read_text())
    arms = matrix["arms"] if isinstance(matrix, dict) else matrix
    if args.phase != "all":
        arms = [a for a in arms if a.get("phase") == args.phase]
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        arms = [a for a in arms if a["name"] in wanted]
    if not arms:
        print("no arms selected", file=sys.stderr)
        return 2
    if args.no_evict:
        for arm in arms:
            arm["evict"] = False

    RUNS.mkdir(parents=True, exist_ok=True)
    for arm in arms:
        if Path(args.stop_file).exists():
            log(f"STOP file present: {args.stop_file}")
            break
        run_dir = RUNS / arm["name"]
        try:
            res = run_arm(arm, run_dir)
            log(json.dumps({
                "arm": arm["name"],
                "ok": res.get("ok"),
                "tok_s": tok_s_values(res),
                "acceptance": res.get("acceptance"),
            }))
        except Exception as e:
            log(f"ARM FAILED {arm['name']}: {e!r}")
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "ERROR.txt").write_text(repr(e))
    write_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
