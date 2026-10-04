#!/usr/bin/env python3
"""gpu-slot-ak-20261004 shared helpers (stdlib only).

Derived from /mnt/raid0/llm/tmp/x0-27b-quants/x0_common_v2.py + x0_shape_b_v2.py (peer files, untouched;
digests in SOURCES.sha256). Differences:
  * BIN defaults to the KVU-19a+19b build gpu-20261004-c7f5ac9ad (set_bin() overrides). Children always run
    with a CLEAN LD_LIBRARY_PATH=<bin>:/opt/rocm/lib (env -u semantics); every inherited GGML_CUDA_FA_* and
    LLAMA_ARG_* variable is dropped so only the arm's own knobs reach the server.
  * knob_env(skip): ON  = GGML_CUDA_FA_MASK_SKIP / _MIN_KV / GGML_CUDA_FA_SEQ_ROWS all unset (build defaults);
                    OFF = GGML_CUDA_FA_MASK_SKIP=0 GGML_CUDA_FA_SEQ_ROWS=0 (in-binary control).
  * Server argv = :8083's PRODUCTION argv (live /proc/<pid>/cmdline if :8083 is listening, else the stack's
    launch record logs/server_launches/8083.json, else ds41-c95/X0_ARGV_8083.txt), transformed ONLY by:
    binary -> <bin>/llama-server, --host 127.0.0.1, --port <scratch>, --slot-save-path <own dir>,
    -b/-ub <arm>, --device ROCm0 --device-draft ROCm0 (already in prod), -lv 4. Launch prefix is the
    production one: numactl --membind=3 -- taskset -c 184-191 (SMT siblings of cores 88-95, NUMA node 3).
  * start_own() pipes the server's stdout/stderr through a reader thread that prefixes every line with the
    arrival epoch time ("<t> <line>"): per-iteration timing from the -lv 4 debug lines with NO extra argv
    flag. (common_log fflush()es each line.)
  * VramSampler defaults to 1 Hz (device total + every KFD pid).
Process discipline unchanged: only PIDs this module started are ever signalled (TERM -> KILL, ps -p verified),
each in its own session; nothing is signalled by name.
"""
from __future__ import annotations

import atexit
import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

SLOT = Path("/mnt/raid0/llm/tmp/gpu-slot-ak-20261004")
BIN = Path(os.environ.get("GPU_SLOT_BIN", "/mnt/raid0/llm/kernels/builds/gpu-20261004-c7f5ac9ad/bin"))
BIN_OVERRIDDEN = True  # always clean LD_LIBRARY_PATH (experimental build, never the store)
EXPECT_BUILD = "10312 (c7f5ac9ad)"
MODELS = {"q8": Path("/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf")}
DRAFTER = Path("/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf")
TEMPLATE = Path("/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja")
LINKAGE = Path("/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh")
KFD_PROC = Path("/sys/class/kfd/kfd/proc")
LAUNCH_RECORD_8083 = Path("/mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json")
X0_ARGV = Path("/mnt/raid0/llm/tmp/ds41-c95/X0_ARGV_8083.txt")
CTX_DIR = Path("/mnt/raid0/llm/tmp/ds41-c95/contexts")
KNOBS = ("GGML_CUDA_FA_MASK_SKIP", "GGML_CUDA_FA_MASK_SKIP_MIN_KV", "GGML_CUDA_FA_SEQ_ROWS")

# production launch prefix and stack env (x0_shape_b_v2.PREFIX / STACK_ENV == launch record argv[0:6])
PREFIX = ["numactl", "--membind=3", "--", "taskset", "-c", "184-191"]
STACK_ENV = {"OMP_PROC_BIND": "spread", "OMP_PLACES": "cores", "OMP_WAIT_POLICY": "active",
             "OMP_DYNAMIC": "false", "KMP_BLOCKTIME": "10", "GGML_IQK": "1"}
TASK = ("\n\n---\nTask: using the material above, reason about which single change to the tinyBLAS "
        "gemm4xN<3> kernel would most improve CPU decode throughput, then state it in one paragraph.")
# production-shape invariants the source argv must carry (else: prod drifted -> refuse, do not guess)
PROD_REQUIRED = [(("-np", "--parallel"), "4"), (("-c", "--ctx-size"), "393216"), (("-ctk", "--cache-type-k"), "q8_0"),
                 (("-ctv", "--cache-type-v"), "q8_0"), (("-fa", "--flash-attn"), "on"), (("-ngl", "--n-gpu-layers"), "all"),
                 (("--spec-type",), "draft-dflash"), (("--spec-draft-n-max",), "7"), (("--device", "-dev"), "ROCm0"),
                 (("--device-draft", "-devd"), "ROCm0")]
PROD_FLAGS = ["--kv-unified", "--no-mmap"]
COHERENCE_PROMPT = ("In three short sentences, explain why the sky looks blue during the day and red at sunset.")

OWN_CHILDREN: list[subprocess.Popen] = []


def set_bin(path) -> None:
    global BIN
    BIN = Path(path)


def ld_path() -> str:
    return f"{BIN}:/opt/rocm/lib"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------- env
def knob_env(skip: bool) -> tuple[list[str], dict]:
    """(unset, set) for the FA mask-skip knobs. skip=True -> build defaults (19a+19b on)."""
    if skip:
        return list(KNOBS), {}
    return ["GGML_CUDA_FA_MASK_SKIP_MIN_KV"], {"GGML_CUDA_FA_MASK_SKIP": "0", "GGML_CUDA_FA_SEQ_ROWS": "0"}


def arm_env(skip: bool) -> tuple[list[str], dict]:
    """Full `env` prefix (env exec's -> captured PID stays the server's) and the record of what it does."""
    k_unset, k_set = knob_env(skip)
    inherited_bad = sorted(k for k in os.environ if k.startswith("LLAMA_ARG_") or
                           (k.startswith("GGML_CUDA_FA") and k not in k_set))
    unset = ["LD_LIBRARY_PATH", "GGML_NOHUGEPAGE_PROCESS"] + sorted(set(k_unset) | set(inherited_bad))
    sets = {"LD_LIBRARY_PATH": ld_path(), **STACK_ENV, **k_set}
    pre = ["env"] + [x for u in unset for x in ("-u", u)] + [f"{k}={v}" for k, v in sets.items()]
    return pre, {"unset": unset, "set": sets, "skip": "on" if skip else "off"}


def child_env(skip: bool) -> dict:
    """The same environment as a dict (belt and braces: Popen env == what the `env` prefix produces)."""
    unset, ov = arm_env(skip)[1]["unset"], arm_env(skip)[1]["set"]
    env = {k: v for k, v in os.environ.items() if k not in unset}
    env.update(ov)
    return env


# ---------------------------------------------------------------- argv
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


def _flag_val(argv: list[str], names: tuple) -> str | None:
    for i, t in enumerate(argv[:-1]):
        if t in names:
            return argv[i + 1]
    return None


def port_pid(port: int) -> int | None:
    try:
        out = subprocess.run(["ss", "-ltnpH", f"sport = :{port}"], capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return None
    m = re.search(r"pid=(\d+)", out)
    return int(m.group(1)) if m else None


def port_listening(port: int) -> bool:
    try:
        return bool(subprocess.run(["ss", "-ltnH", f"sport = :{port}"], capture_output=True, text=True,
                                   timeout=5).stdout.strip())
    except Exception:  # noqa: BLE001
        return True  # unknown -> treat as busy


def source_argv() -> dict:
    """:8083 production argv. Priority: live pid cmdline > stack launch record > X0_ARGV_8083.txt.
    Returns {argv (llama-server onward), source, sha256, raw, cross_check}."""
    res: dict = {}
    pid = port_pid(8083)
    if pid:
        try:
            raw = [a for a in Path(f"/proc/{pid}/cmdline").read_bytes().decode().split("\0") if a]
            res = {"raw": raw, "source": f"live :8083 /proc/{pid}/cmdline"}
        except OSError:
            res = {}
    if not res and LAUNCH_RECORD_8083.exists():
        rec = json.loads(LAUNCH_RECORD_8083.read_text())
        res = {"raw": rec["argv"], "source": f"{LAUNCH_RECORD_8083} (launch {rec.get('launched_at')}, "
                                             f"pid {rec.get('pid')}, argv_sha256 {rec.get('argv_sha256', '')[:12]})"}
    if not res and X0_ARGV.exists():
        res = {"raw": read_argv(X0_ARGV), "source": str(X0_ARGV)}
    if not res:
        raise SystemExit("no :8083 argv source (live pid / launch record / X0_ARGV_8083.txt)")
    raw = res["raw"]
    idx = next((i for i, t in enumerate(raw) if t.endswith("llama-server")), None)
    if idx is None:
        raise SystemExit(f"argv source has no llama-server: {raw[:6]}")
    res["prefix_in_source"] = raw[:idx]
    res["argv"] = raw[idx:]
    res["sha256"] = hashlib.sha256("\0".join(raw).encode()).hexdigest()
    if X0_ARGV.exists():
        x0 = read_argv(X0_ARGV)
        res["cross_check_x0_argv_8083"] = "identical (after the launch prefix)" if x0[1:] == res["argv"][1:] else \
            f"DIFFERS from {X0_ARGV}"
    return res


def validate_prod_argv(argv: list[str]) -> list[str]:
    probs = []
    for names, val in PROD_REQUIRED:
        got = _flag_val(argv, names)
        if got != val:
            probs.append(f"prod argv {names[0]} = {got!r}, expected {val!r}")
    for f in PROD_FLAGS:
        if f not in argv:
            probs.append(f"prod argv missing {f}")
    m = _flag_val(argv, ("-m", "--model")) or ""
    md = _flag_val(argv, ("-md", "--model-draft")) or ""
    if Path(m).name != MODELS["q8"].name:
        probs.append(f"prod -m {m} is not {MODELS['q8'].name}")
    if Path(md).name != DRAFTER.name:
        probs.append(f"prod -md {md} is not {DRAFTER.name}")
    return probs


def build_server_argv(port: int, b: int, ub: int, slot_save: Path, extra: list[str] | None = None,
                      src: dict | None = None) -> tuple[list[str], list[str], dict]:
    src = src or source_argv()
    a = [str(BIN / "llama-server")] + src["argv"][1:]
    notes = [f"binary {src['argv'][0]} -> {a[0]}"]
    if src.get("prefix_in_source"):
        notes.append(f"source launch prefix {' '.join(src['prefix_in_source'])!r} -> PREFIX {' '.join(PREFIX)!r}")
    for names, val in ((("--host",), "127.0.0.1"), (("--port",), str(port)), (("--slot-save-path",), str(slot_save)),
                       (("-b", "--batch-size"), str(b)), (("-ub", "--ubatch-size"), str(ub)),
                       (("--device", "-dev"), "ROCm0"), (("--device-draft", "-devd"), "ROCm0"),
                       (("-lv", "--verbosity", "--log-verbosity"), "4")):
        before = list(a)
        a = _set(a, names, val)
        if a != before:
            old = _flag_val(before, names)
            notes.append(f"{names[0]} {old if old is not None else '(absent)'} -> {val}")
    for x in extra or []:
        a.append(x)
    if extra:
        notes.append("+ " + " ".join(extra))
    return a, notes, src


def launch_cmd(skip: bool, argv: list[str]) -> list[str]:
    return arm_env(skip)[0] + PREFIX + argv


# ---------------------------------------------------------------- process lifecycle (own PIDs only)
def _pump(stream, fh) -> None:
    for line in iter(stream.readline, b""):
        fh.write(b"%.3f " % time.time() + line)
        fh.flush()
    fh.close()


def start_own(argv: list[str], log_path: Path, env: dict | None = None, timestamp_lines: bool = True) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if timestamp_lines:
        p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env or dict(os.environ),
                             start_new_session=True)
        fh = open(log_path, "wb")
        t = threading.Thread(target=_pump, args=(p.stdout, fh), daemon=True)
        t.start()
        p._pump_thread = t  # type: ignore[attr-defined]
    else:
        fh = open(log_path, "w")
        p = subprocess.Popen(argv, stdout=fh, stderr=subprocess.STDOUT, env=env or dict(os.environ),
                             start_new_session=True)
    OWN_CHILDREN.append(p)
    return p


def stop_own(p: subprocess.Popen, term_wait: float = 30.0) -> dict:
    """SIGTERM -> wait -> SIGKILL on a PID this process started; verify with ps -p."""
    rec = {"pid": p.pid, "already_exited": p.poll() is not None, "sent": []}
    if p.poll() is None:
        p.send_signal(signal.SIGTERM)
        rec["sent"].append("TERM")
        try:
            p.wait(timeout=term_wait)
        except subprocess.TimeoutExpired:
            p.send_signal(signal.SIGKILL)
            rec["sent"].append("KILL")
            p.wait(timeout=30)
    t = getattr(p, "_pump_thread", None)
    if t is not None:
        t.join(timeout=10)
    alive = subprocess.run(["ps", "-p", str(p.pid)], capture_output=True).returncode == 0
    rec["verified_dead"] = not alive
    rec["returncode"] = p.returncode
    if p in OWN_CHILDREN:
        OWN_CHILDREN.remove(p)
    if alive:
        raise RuntimeError(f"own child {p.pid} still alive after TERM/KILL")
    return rec


def _cleanup(*_a):
    for p in list(OWN_CHILDREN):
        try:
            print(f"[slot] cleanup: stopping own pid {p.pid}", flush=True)
            stop_own(p, term_wait=60)
        except Exception as exc:  # noqa: BLE001
            print(f"[slot] cleanup of own pid {p.pid} failed: {exc}", flush=True)


atexit.register(_cleanup)


def _sig(signum, _frame):
    _cleanup()
    raise SystemExit(128 + signum)


def install_signal_handlers() -> None:
    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)


install_signal_handlers()


# ---------------------------------------------------------------- VRAM (KFD) sampler, 1 Hz
def kfd_pids() -> dict:
    res = {}
    try:
        for d in KFD_PROC.iterdir():
            if not d.name.isdigit():
                continue
            v = 0
            for f in d.glob("vram_*"):
                try:
                    v += int(f.read_text())
                except (OSError, ValueError):
                    pass
            try:
                name = Path(f"/proc/{d.name}/comm").read_text().strip()
            except OSError:
                name = "?"
            res[int(d.name)] = {"name": name, "vram_b": v}
    except OSError:
        pass
    return res


def vram_now() -> dict:
    out = {"t": round(time.time(), 3)}
    used = total = 0
    for card in sorted(Path("/sys/class/drm").glob("card[0-9]*/device/mem_info_vram_used")):
        try:
            used += int(card.read_text())
            total += int((card.parent / "mem_info_vram_total").read_text())
        except (OSError, ValueError):
            pass
    if total:
        out["used_b"], out["total_b"] = used, total
    else:
        out["err"] = "no amdgpu mem_info_vram_used in sysfs"
    out["pids"] = kfd_pids()
    return out


class VramSampler:
    def __init__(self, path: Path, period: float = 1.0):
        self.path, self.period = path, period
        self.samples: list[dict] = []
        self.marks: list[tuple[float, str]] = []
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as fh:
            while not self._stop.is_set():
                s = vram_now()
                self.samples.append(s)
                fh.write(json.dumps(s) + "\n")
                fh.flush()
                self._stop.wait(self.period)

    def mark(self, label: str) -> None:
        self.marks.append((time.time(), label))
        with open(self.path, "a") as fh:
            fh.write(json.dumps({"t": round(time.time(), 3), "mark": label}) + "\n")

    def start(self):
        self._t.start()
        return self

    def stop(self):
        self._stop.set()
        self._t.join(timeout=30)

    def summary(self, own_pid: int | None, baseline_b: int | None) -> dict:
        used = [s["used_b"] for s in self.samples if "used_b" in s]
        own = [s["pids"].get(own_pid, {}).get("vram_b", 0) for s in self.samples] if own_pid else []
        pk = max(used) if used else None
        t_pk = next((s["t"] for s in self.samples if s.get("used_b") == pk), None) if pk else None
        return {"n_samples": len(used), "period_s": self.period, "peak_used_b": pk, "baseline_used_b": baseline_b,
                "peak_minus_baseline_b": (pk - baseline_b) if (pk is not None and baseline_b is not None) else None,
                "own_pid_peak_vram_b": max(own) if own else None,
                "nonzero_samples": sum(1 for v in own if v > 0) if own else None,
                "peak_used_gib": round(pk / 2**30, 3) if pk else None, "peak_at": t_pk,
                "own_pid_peak_vram_gib": round(max(own) / 2**30, 3) if own else None,
                "own_pid_after_load_gib": next((round(v / 2**30, 3) for v in own if v > 40 * 2**30), None)}


def foreign_gpu_procs(exclude: set[int] | None = None) -> dict:
    exclude = exclude or set()
    return {pid: v for pid, v in kfd_pids().items() if pid not in exclude and v["vram_b"] > 0}


def hip_dlopen_proof(pid: int) -> dict:
    try:
        maps = Path(f"/proc/{pid}/maps").read_text()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "err": str(exc)[:200]}
    libs = sorted({ln.split()[-1] for ln in maps.splitlines() if "libggml" in ln and ln.split()[-1].startswith("/")})
    hip = [x for x in libs if "libggml-hip" in x]
    real_bin = str(BIN.resolve())
    ok = bool(hip) and all(os.path.realpath(x).startswith(real_bin + "/") for x in libs)
    return {"ok": ok, "ggml_libs": libs, "hip_mapped": hip}


def live_env(pid: int) -> dict:
    try:
        env = Path(f"/proc/{pid}/environ").read_bytes().split(b"\0")
        pairs = (e.decode(errors="replace").split("=", 1) for e in env if b"=" in e)
        return {k: v for k, v in pairs if k == "LD_LIBRARY_PATH" or k.startswith("GGML_CUDA_FA") or k.startswith("LLAMA_ARG_")}
    except OSError as exc:
        return {"err": str(exc)}


# ---------------------------------------------------------------- HTTP
def http_json(url: str, body: dict | None = None, timeout: float = 30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_healthy(base: str, proc: subprocess.Popen, timeout: float = 900) -> float:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited rc={proc.returncode} before healthy")
        try:
            if http_json(base + "/health", timeout=5).get("status") == "ok":
                return round(time.time() - t0, 1)
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    raise TimeoutError("server not healthy")


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=str) + "\n")
    tmp.replace(path)


def stream_chat(base: str, body: dict, keep_text: bool = False) -> dict:
    body = {**body, "stream": True, "stream_options": {"include_usage": True}}
    req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    out = {"ttft_s": None, "reasoning_chars": 0, "content_chars": 0, "timings": None, "finish": None}
    h = hashlib.sha256()
    parts: list[str] = []
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
                    h.update(b"R" + d["reasoning_content"].encode())
                    if keep_text:
                        parts.append(("R", d["reasoning_content"]))
                    got = True
                if d.get("content"):
                    out["content_chars"] += len(d["content"])
                    h.update(b"C" + d["content"].encode())
                    if keep_text:
                        parts.append(("C", d["content"]))
                    got = True
                if got and out["ttft_s"] is None:
                    out["ttft_s"] = round(time.time() - t0, 3)
                if ch.get("finish_reason"):
                    out["finish"] = ch["finish_reason"]
    out["wall_s"] = round(time.time() - t0, 2)
    out["text_sha"] = h.hexdigest()[:16]
    if keep_text:
        out["reasoning_text"] = "".join(t for k, t in parts if k == "R")
        out["content_text"] = "".join(t for k, t in parts if k == "C")
    return out


def summarize(r: dict) -> dict:
    t = r.get("timings") or {}
    dn, da = t.get("draft_n"), t.get("draft_n_accepted")
    return {"prompt_n": t.get("prompt_n"), "cache_n": t.get("cache_n"),
            "prefill_tps": round(t.get("prompt_per_second") or 0, 1),
            "decode_tps": round(t.get("predicted_per_second") or 0, 3), "predicted_n": t.get("predicted_n"),
            "draft_n": dn, "draft_n_accepted": da, "draft_acc": round(da / dn, 4) if dn else None,
            "ttft_s": r.get("ttft_s"), "wall_s": r.get("wall_s"), "finish": r.get("finish"),
            "reasoning_chars": r.get("reasoning_chars"), "content_chars": r.get("content_chars"),
            "text_sha": r.get("text_sha")}


def coherence_check(base: str, out_json: Path, label: str) -> dict:
    """ONE short greedy spot-check (no classifier): text saved for a human to read; sha for on/off identity."""
    body = {"messages": [{"role": "user", "content": COHERENCE_PROMPT}], "max_tokens": 160,
            "temperature": 0.0, "top_k": 1, "top_p": 1.0, "chat_template_kwargs": {"enable_thinking": False}}
    try:
        r = stream_chat(base, body, keep_text=True)
        rec = {"label": label, "at": now(), "prompt": COHERENCE_PROMPT, "request": body, **summarize(r),
               "content_text": r.get("content_text"), "reasoning_text": r.get("reasoning_text")}
    except Exception as exc:  # noqa: BLE001
        rec = {"label": label, "at": now(), "error": f"{type(exc).__name__}: {exc}"[:400]}
    write_json(out_json, rec)
    out_json.with_suffix(".txt").write_text(
        f"# coherence spot-check {label} ({rec.get('at')}), greedy, enable_thinking=false\n# prompt: {COHERENCE_PROMPT}\n\n"
        + (rec.get("reasoning_text") or "") + ("\n---\n" if rec.get("reasoning_text") else "")
        + (rec.get("content_text") or rec.get("error", "")) + "\n")
    return rec


def log_memory_lines(log_path: Path, limit: int = 60) -> dict:
    """-lv 4 memory lines: load-time buffer/KV/compute sizes (first `limit`) and the exit memory breakdown table
    (common_memory_breakdown_print, printed on graceful SIGTERM shutdown), plus any realloc/pool debug lines."""
    load_pats = ("buffer size", "KV self size", "compute buffer", "graph splits", "llama_kv_cache",
                 "llama_memory_recurrent", "model buffer", "RS buffer", "llama_context:")
    grow_pats = ("reallocat", "ggml_gallocr", "pool", "hipMalloc", "out of memory")
    out = {"load": [], "breakdown": [], "growth_debug": [], "growth_debug_total": 0}
    try:
        with open(log_path, "rb") as fh:
            for raw in fh:
                ln = raw.decode(errors="replace").rstrip()
                if "memory_breakdown" in ln or "memory breakdown" in ln:
                    out["breakdown"].append(ln[:300])
                elif any(p in ln for p in grow_pats):
                    out["growth_debug_total"] += 1
                    if len(out["growth_debug"]) < 40:
                        out["growth_debug"].append(ln[:300])
                elif len(out["load"]) < limit and any(p in ln for p in load_pats):
                    out["load"].append(ln[:300])
    except OSError as exc:
        out["error"] = str(exc)
    return out
