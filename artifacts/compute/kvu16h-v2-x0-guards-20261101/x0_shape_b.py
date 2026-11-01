#!/usr/bin/env python3
"""INF-80 X0 shape (b): the PRODUCTION :8083 architect_critic shape, np1 single-stream decode at
~2k and ~50k prompt context, temperature 0 AND server-default sampling, on a scratch port.

Argv source (in order): --argv-file <file> (workspace-ec's pasted live argv; plain argv line, or a
DFLASH2_LIVE-style file with an `argv:` line), else /mnt/raid0/llm/tmp/ds41-c95/DFLASH2_LIVE.
Transforms applied to that argv (and printed): binary forced to the v10 store binary; -m -> arm
model; --host 127.0.0.1 --port <scratch>; -c -> --ctx (default 393216); --spec-draft-n-max ->
--draft-n-max (default 7); --slot-save-path dropped. Nothing else is touched. The per-slot 262144
cap is the v10 server's own n_ctx_train clamp (server-context.cpp:1316-1322), not a flag.
Launch prefix and env mirror the stack: numactl --membind=3 -- taskset -c 184-191, OMP env
(stack_env._CANONICAL_OMP_ENV), GGML_IQK=1, LD_LIBRARY_PATH=<store bin>:/opt/rocm/lib.

Prompts: probe_decode.py's construction (C2 + C4 inline planner prompts, truncated by measured
chars/token to the target, + the same TASK suffix); a FIXED tag instead of a random nonce so both
arms see byte-identical prompts. Per target: temp0 rep1 (pays prefill), temp0 rep2, default rep1,
default rep2 (reps 2-4 reuse the cached prompt: decode-only). Metric = timings.predicted_per_second.

Usage: x0_shape_b.py --arm q8|q4 --rep N [--port 18083] [--argv-file F] [--dry-run]
Writes results/shape_b.<arm>.rep<N>.json (one file per launch), server log under results/logs/.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
import traceback
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import x0_common as C  # noqa: E402

PROBE = Path(__file__).resolve().parent / "probe_decode_x0.py"
LIVE = Path("/mnt/raid0/llm/tmp/ds41-c95/DFLASH2_LIVE")
CTX_DIR = Path("/mnt/raid0/llm/tmp/ds41-c95/contexts")
TARGETS = (2000, 50000)
GEN = 512
TASK = ("\n\n---\nTask: using the material above, reason about which single change to the tinyBLAS "
        "gemm4xN<3> kernel would most improve CPU decode throughput, then state it in one paragraph.")
TAG = "[x0 fixed prompt]\n"
PREFIX = ["numactl", "--membind=3", "--", "taskset", "-c", "184-191"]
STACK_ENV = {"OMP_PROC_BIND": "spread", "OMP_PLACES": "cores", "OMP_WAIT_POLICY": "active",
             "OMP_DYNAMIC": "false", "KMP_BLOCKTIME": "10", "GGML_IQK": "1"}
SAMPLING = {
    "temp0": {"temperature": 0.0, "top_k": 1, "top_p": 1.0},
    "default": {},  # omit every sampling field: server/GGUF defaults (recorded from /props)
}


def probe_label(a) -> str:
    return f"dflash2-{a.arm}-x0rep{a.rep}"


def read_argv(path: Path) -> list[str]:
    txt = path.read_text()
    for line in txt.splitlines():
        if line.strip().startswith("argv:"):
            return shlex.split(line.split("argv:", 1)[1])
    lines = [ln for ln in txt.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    return shlex.split(" ".join(lines))


def _set(argv: list[str], names: tuple, value: str | None) -> list[str]:
    """Replace the value of the first matching flag (or append it); value None = drop flag+value."""
    out, done, i = [], False, 0
    while i < len(argv):
        if argv[i] in names:
            if value is not None and not done:
                out += [argv[i], value]
                done = True
            i += 2
            continue
        out.append(argv[i])
        i += 1
    if value is not None and not done:
        out += [names[0], value]
    return out


def build_argv(src: list[str], arm: str, port: int, ctx: int, n_max: int) -> tuple[list[str], list[str]]:
    notes = []
    idx = next((i for i, t in enumerate(src) if t.endswith("llama-server")), None)
    if idx is None:
        raise SystemExit(f"argv source contains no llama-server binary: {src[:4]}")
    if idx:
        notes.append(f"dropped launch prefix {' '.join(src[:idx])!r} (the runner applies its own numactl/taskset)")
        src = src[idx:]
    a = [str(C.BIN / "llama-server")] + src[1:]
    if src[0] != a[0]:
        notes.append(f"binary {src[0]} -> {a[0]}")
    for names, val in ((("-m", "--model"), str(C.MODELS[arm])), (("--host",), "127.0.0.1"),
                       (("--port",), str(port)), (("-c", "--ctx-size"), str(ctx)),
                       (("--spec-draft-n-max",), str(n_max)), (("--slot-save-path",), None)):
        before = list(a)
        a = _set(a, names, val)
        if a != before:
            notes.append(f"{names[0]} -> {val if val is not None else '(dropped)'}")
    return a, notes


def stream_chat(base: str, body: dict) -> dict:
    body = {**body, "stream": True, "stream_options": {"include_usage": True}}
    req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    out = {"ttft_s": None, "reasoning_chars": 0, "content_chars": 0, "timings": None, "finish": None}
    with urllib.request.urlopen(req, timeout=3600) as r:
        for raw in r:
            line = raw.strip()
            if not line.startswith(b"data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == b"[DONE]":
                continue
            try:
                ev = json.loads(payload)
            except ValueError:
                continue
            if isinstance(ev.get("timings"), dict):
                out["timings"] = ev["timings"]
            for ch in ev.get("choices") or []:
                d = ch.get("delta") or {}
                got = False
                if d.get("reasoning_content"):
                    out["reasoning_chars"] += len(d["reasoning_content"])
                    got = True
                if d.get("content"):
                    out["content_chars"] += len(d["content"])
                    got = True
                if got and out["ttft_s"] is None:
                    out["ttft_s"] = round(time.time() - t0, 3)
                if ch.get("finish_reason"):
                    out["finish"] = ch["finish_reason"]
    out["wall_s"] = round(time.time() - t0, 2)
    return out


def summarize(r: dict) -> dict:
    t = r.get("timings") or {}
    dn, da = t.get("draft_n"), t.get("draft_n_accepted")
    return {"prompt_n": t.get("prompt_n"), "cache_n": t.get("cache_n"),
            "prefill_tps": round(t.get("prompt_per_second") or 0, 1),
            "decode_tps": round(t.get("predicted_per_second") or 0, 3), "predicted_n": t.get("predicted_n"),
            "draft_n": dn, "draft_n_accepted": da, "draft_acc": round(da / dn, 4) if dn else None,
            "ttft_s": r.get("ttft_s"), "wall_s": r.get("wall_s"), "finish": r.get("finish"),
            "reasoning_chars": r.get("reasoning_chars"), "content_chars": r.get("content_chars")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=sorted(C.MODELS), required=True)
    ap.add_argument("--rep", type=int, required=True)
    ap.add_argument("--port", type=int, default=18083)
    ap.add_argument("--argv-file", type=Path, default=None)
    ap.add_argument("--ctx", type=int, default=393216)
    ap.add_argument("--draft-n-max", type=int, default=7)
    ap.add_argument("--gen", type=int, default=GEN)
    ap.add_argument("--boot-timeout", type=float, default=900)
    ap.add_argument("--with-probe", action="store_true",
                    help="after the X0 rows, run probe_decode_x0.py (2k/16k/50k/80k, 1500 tok, + no-draft) on this live server")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.with_probe:
        ap.error("KVU-16h: probe requires separate drafted and no-draft servers")
    src_path = a.argv_file or LIVE
    argv, notes = build_argv(read_argv(src_path), a.arm, a.port, a.ctx, a.draft_n_max)
    out_path = C.RESULTS / f"shape_b.{a.arm}.rep{a.rep}.json"
    log_path = C.RESULTS / "logs" / f"shape_b.{a.arm}.rep{a.rep}.server.log"
    if a.dry_run:
        print(f"  [shape b] {a.arm} rep{a.rep} -> {out_path}")
        print(f"    argv source: {src_path}; transforms: {'; '.join(notes)}")
        print("    env: " + " ".join(f"{k}={v}" for k, v in STACK_ENV.items())
              + f" LD_LIBRARY_PATH={C.BIN}:/opt/rocm/lib:...")
        print("    cmd: " + " ".join(PREFIX + argv) + f"  > {log_path}")
        print(f"    requests: np1 solo, targets {TARGETS} tok x [temp0 x2, default x2], max_tokens {a.gen}, "
              "/v1/chat/completions stream, template-default thinking")
        if a.with_probe:
            print(f"    + probe: python3 {PROBE} --url http://127.0.0.1:{a.port} --label {probe_label(a)} "
                  f"--out-dir {C.RESULTS / 'probe'} --wait-idle-s 60   (same live server, before teardown)")
        return 0

    log_path.parent.mkdir(parents=True, exist_ok=True)
    base = f"http://127.0.0.1:{a.port}"
    rec = {"schema": "x0.shape_b.launch.v1", "arm": a.arm, "rep": a.rep, "started_at": C.now(),
           "argv_source": str(src_path), "argv_transforms": notes, "argv": PREFIX + argv,
           "env_overrides": STACK_ENV, "gen": a.gen, "rows": []}
    rec["vram_before"] = C.vram_now()
    rec["foreign_gpu_procs_before"] = C.foreign_gpu_procs()
    sampler = C.VramSampler(C.RESULTS / "logs" / f"shape_b.{a.arm}.rep{a.rep}.vram.jsonl").start()
    proc = None
    try:
        import os
        os.environ.update(STACK_ENV)
        os.environ["LD_LIBRARY_PATH"] = f"{C.BIN}:/opt/rocm/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
        proc = C.start_own(PREFIX + argv, log_path)
        rec["pid"] = proc.pid
        rec["load_s"] = C.wait_healthy(base, proc, timeout=a.boot_timeout)
        rec["hip_dlopen_proof"] = C.hip_dlopen_proof(proc.pid)
        props = C.http_json(base + "/props")
        rec["build_info"] = props.get("build_info")
        dgs = props.get("default_generation_settings") or {}
        p = dgs.get("params") or dgs
        rec["default_sampling"] = {k: p.get(k) for k in ("temperature", "top_k", "top_p", "min_p",
                                                          "speculative.n_max", "speculative.types") if k in p}
        slots = C.http_json(base + "/slots")
        rec["n_slots"], rec["n_ctx_slot"] = len(slots), min(s.get("n_ctx", 0) for s in slots)
        # warmup (discarded): short temp-0 request, absorbs first-launch kernel/graph setup
        rec["warmup"] = summarize(stream_chat(base, {"messages": [{"role": "user", "content": "Say hello."}],
                                                     "max_tokens": 64, **SAMPLING["temp0"]}))
        text = ((CTX_DIR / "C2/prompt.inline.txt").read_text() + "\n\n"
                + (CTX_DIR / "C4/prompt.inline.txt").read_text())
        full_tok = len(C.http_json(base + "/tokenize", {"content": text}, timeout=120)["tokens"])
        cpt = len(text) / full_tok
        rec["source_tokens"], rec["chars_per_token"] = full_tok, round(cpt, 4)
        for target in TARGETS:
            msg = TAG + text[: int(min(len(text), target * cpt))] + TASK
            for mode in ("temp0", "default"):
                for rep in (1, 2):
                    busy = [s["id"] for s in C.http_json(base + "/slots") if s.get("is_processing")]
                    r = stream_chat(base, {"messages": [{"role": "user", "content": msg}],
                                           "max_tokens": a.gen, **SAMPLING[mode]})
                    row = {"target": target, "sampling": mode, "rep": rep, "busy_before": busy, **summarize(r)}
                    rec["rows"].append(row)
                    print(f"[shape b] {a.arm} rep{a.rep} ~{target // 1000}k {mode} r{rep}: decode "
                          f"{row['decode_tps']} tok/s, acc {row['draft_acc']}, prompt {row['prompt_n']} "
                          f"(cache {row['cache_n']}), gen {row['predicted_n']}", flush=True)
                    C.write_json(out_path, {**rec, "status": "partial"})  # incremental persistence
        if a.with_probe:
            t_p = time.time()
            cp = subprocess.run([sys.executable, "-B", str(PROBE), "--url", base, "--label", probe_label(a),
                                 "--out-dir", str(C.RESULTS / "probe"), "--wait-idle-s", "60"],
                                stdout=open(C.RESULTS / "logs" / f"probe.{probe_label(a)}.log", "w"),
                                stderr=subprocess.STDOUT)
            rec["probe"] = {"rc": cp.returncode, "wall_s": round(time.time() - t_p, 1), "label": probe_label(a),
                            "json": str(C.RESULTS / "probe" / f"probe-decode-vs-context.{probe_label(a)}.json")}
            print(f"[shape b] probe {probe_label(a)} rc {cp.returncode} in {rec['probe']['wall_s']} s", flush=True)
        rec["status"] = "ok"
    except Exception as exc:  # noqa: BLE001
        rec["status"] = "failed"
        rec["error"] = f"{type(exc).__name__}: {exc}"
        rec["traceback"] = traceback.format_exc()[-3000:]
    finally:
        sampler.stop()
        if proc is not None:
            rec["teardown"] = C.stop_own(proc, term_wait=180)
        rec["vram"] = sampler.summary(rec.get("pid"), rec["vram_before"].get("used_b"))
        try:
            log = log_path.read_text(errors="replace")
            rec["log_capping_line"] = [ln for ln in log.splitlines() if "capping" in ln][:2]
            rec["log_device_lines"] = [ln for ln in log.splitlines()
                                       if ("MI210" in ln or "ROCm0" in ln or "offloaded" in ln)][:8]
        except Exception:  # noqa: BLE001
            pass
        rec["finished_at"] = C.now()
        C.write_json(out_path, rec)
    resident = (rec["vram"].get("own_pid_peak_vram_b") or 0) > (1 << 30)
    print(f"[shape b] {a.arm} rep{a.rep}: {rec['status']}, own-pid peak VRAM {rec['vram'].get('own_pid_peak_vram_gib')} GiB, "
          f"hip-proof {(rec.get('hip_dlopen_proof') or {}).get('ok')} -> {out_path.name}", flush=True)
    if rec["status"] == "ok" and not resident:
        print("[shape b] RESIDENCY NOT PROVEN (own-pid VRAM never > 1 GiB): do not trust this launch", flush=True)
        return 3
    return 0 if rec["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
