#!/usr/bin/env python3
"""KVU-16h shared helpers (stdlib only): production argv/env sourcing, own-PID server lifecycle, 1 Hz KFD/card
sampler + rocm-smi sampler with a VRAM ceiling watchdog, phase markers.

Provenance (reused, adapted; originals untouched):
  * /mnt/raid0/llm/tmp/gpu-slot-ak-20261004/slot_common.py — source_argv / validate_prod_argv / start_own (epoch
    line prefix) / stop_own (TERM -> KILL, ps -p verified) / kfd_pids. Differences: BIN is the PRODUCTION kernel
    store (kernels/production/gpu, v10 ffc1bac82), the argv transform changes ONLY --port, --slot-save-path and -lv
    (plus -b/-ub in an optional arm), env is the production env (no FA knobs), and an LD_PRELOAD hipMalloc
    interposer can be added (shim/).
  * /mnt/raid0/llm/tmp/gpu-block-27b-20261003/lib_gpublock.py — imported as-is for prompts (fit_prompt over the
    DS41 C1..C7 contexts), /tokenize and the streaming client.
Process discipline: only PIDs this module started are ever signalled; nothing is signalled by name.
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

HERE = Path(__file__).resolve().parent
GPUBLOCK = Path("/mnt/raid0/llm/tmp/gpu-block-27b-20261003")
STORE_GPU = Path("/mnt/raid0/llm/kernels/production/gpu")          # -> builds/gpu-20260921-ffc1bac82/bin (v10)
EXPECT_BIN_REAL = Path("/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin")
EXPECT_BUILD = "10303 (ffc1bac82)"
LAUNCH_RECORD_8083 = Path("/mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json")
X0_ARGV = Path("/mnt/raid0/llm/tmp/ds41-c95/X0_ARGV_8083.txt")
B4I_LAUNCH_ON = GPUBLOCK / "results" / "b4i" / "launch_ON.sh"   # env recorded from live :8083 PID 1703677 environ
LINKAGE = Path("/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh")
CLAIM_MOD_DIR = Path("/workspace/repos/epyc-inference-research/scripts/kernel_rnd")
SHIM = HERE / "shim" / "libhipmalloc_trace.so"
MODEL = Path("/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf")
DRAFTER = Path("/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf")
KFD_PROC = Path("/sys/class/kfd/kfd/proc")
CARD = Path("/sys/class/drm/card2/device")                         # the MI210 (lib_gpublock.VRAM_CARD)
GIB = 1024 ** 3

# Production env. Primary source: the live :8083 environ (whitelisted keys). Fallback: the env the B4i launch
# scripts recorded from live :8083 PID 1703677 at 2026-10-04T02:48Z (same launch as the 8083.json record).
ENV_KEYS = ("LD_LIBRARY_PATH", "HIP_PATH", "ROCM_PATH", "OMP_PROC_BIND", "OMP_PLACES", "OMP_WAIT_POLICY",
            "OMP_DYNAMIC", "GGML_IQK", "KMP_BLOCKTIME")
ENV_FALLBACK = {
    "LD_LIBRARY_PATH": "/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin:/opt/rocm/lib:/usr/lib/llvm-20/lib:"
                       "/opt/AMD/aocc-compiler-5.0.0/lib:/opt/rocm/lib",
    "HIP_PATH": "/opt/rocm", "ROCM_PATH": "/opt/rocm", "OMP_PROC_BIND": "spread", "OMP_PLACES": "cores",
    "OMP_WAIT_POLICY": "active", "OMP_DYNAMIC": "false", "GGML_IQK": "1",
}
# Production-shape invariants the sourced argv must carry; on drift we REFUSE (never guess flags).
PROD_REQUIRED = [(("-np", "--parallel"), "4"), (("-c", "--ctx-size"), "393216"), (("-ctk", "--cache-type-k"), "q8_0"),
                 (("-ctv", "--cache-type-v"), "q8_0"), (("-fa", "--flash-attn"), "on"), (("-ngl", "--n-gpu-layers"), "all"),
                 (("--spec-type",), "draft-dflash"), (("--spec-draft-n-max",), "7"), (("--device", "-dev"), "ROCm0"),
                 (("--device-draft", "-devd"), "ROCm0"), (("-ub", "--ubatch-size"), "2048"),
                 (("--cache-ram", "-cram"), "65536")]
PROD_FLAGS = ["--kv-unified", "--no-mmap"]
PROD_PREFIX = ["numactl", "--membind=3", "--", "taskset", "-c", "184-191"]

OWN_CHILDREN: list[subprocess.Popen] = []


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=str) + "\n")
    tmp.replace(path)


class Jsonl:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path, self._lock = path, threading.Lock()

    def add(self, rec: dict) -> None:
        with self._lock, open(self.path, "a") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
            fh.flush()


def sha256_file(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


# ---------------------------------------------------------------- ports / processes (read-only)
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


def proc_environ(pid: int) -> dict:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes().decode(errors="replace").split("\0")
    except OSError:
        return {}
    return dict(kv.split("=", 1) for kv in raw if "=" in kv)


def kfd_pids() -> dict[int, dict]:
    res: dict[int, dict] = {}
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


def card_vram() -> tuple[int | None, int | None]:
    try:
        return int((CARD / "mem_info_vram_used").read_text()), int((CARD / "mem_info_vram_total").read_text())
    except (OSError, ValueError):
        return None, None


def foreign_gpu_procs(exclude: set[int] | None = None) -> dict:
    exclude = exclude or set()
    return {p: v for p, v in kfd_pids().items() if p not in exclude and v["vram_b"] > 0}


# ---------------------------------------------------------------- production argv / env
def _flag_val(argv: list[str], names: tuple) -> str | None:
    for i, t in enumerate(argv[:-1]):
        if t in names:
            return argv[i + 1]
    return None


def _set(argv: list[str], names: tuple, value: str | None) -> list[str]:
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


def read_x0_argv(path: Path) -> list[str]:
    txt = path.read_text()
    for line in txt.splitlines():
        if line.strip().startswith("argv:"):
            return shlex.split(line.split("argv:", 1)[1])
    return shlex.split(" ".join(ln for ln in txt.splitlines() if ln.strip() and not ln.lstrip().startswith("#")))


def source_argv() -> dict:
    """:8083 production argv. Priority: live :8083 /proc cmdline > the stack's launch record (written by
    `orchestrator_stack.py reload architect_critic`) > X0_ARGV_8083.txt. Never assembled by hand."""
    res: dict = {}
    pid = port_pid(8083)
    if pid:
        try:
            raw = [a for a in Path(f"/proc/{pid}/cmdline").read_bytes().decode().split("\0") if a]
            res = {"raw": raw, "source": f"live :8083 /proc/{pid}/cmdline", "live_pid": pid}
        except OSError:
            res = {}
    if not res and LAUNCH_RECORD_8083.exists():
        rec = json.loads(LAUNCH_RECORD_8083.read_text())
        res = {"raw": rec["argv"], "record": rec,
               "source": f"{LAUNCH_RECORD_8083} (launched_at {rec.get('launched_at')}, pid {rec.get('pid')}, "
                         f"argv_sha256 {rec.get('argv_sha256', '')[:12]}, launcher {' '.join(rec.get('launcher_argv') or [])}, "
                         f"stack_commit {str(rec.get('stack_commit'))[:12]})"}
    if not res and X0_ARGV.exists():
        res = {"raw": read_x0_argv(X0_ARGV), "source": str(X0_ARGV)}
    if not res:
        raise SystemExit("no :8083 argv source (live pid / launch record / X0_ARGV_8083.txt)")
    raw = res["raw"]
    idx = next((i for i, t in enumerate(raw) if t.endswith("llama-server")), None)
    if idx is None:
        raise SystemExit(f"argv source has no llama-server: {raw[:6]}")
    res["prefix"] = raw[:idx]
    res["argv"] = raw[idx:]
    res["sha256_raw"] = hashlib.sha256("\0".join(raw).encode()).hexdigest()  # the stack's argv_sha256 scheme
    rec_sha = (res.get("record") or {}).get("argv_sha256")
    if rec_sha:
        res["record_sha_matches"] = rec_sha == res["sha256_raw"]
    if X0_ARGV.exists():
        try:
            x0 = read_x0_argv(X0_ARGV)
            xi = next((i for i, t in enumerate(x0) if t.endswith("llama-server")), 0)
            res["cross_check_x0"] = "identical after the binary" if x0[xi + 1:] == res["argv"][1:] else \
                f"differs from {X0_ARGV} (informational; the launch record is newer)"
        except Exception as exc:  # noqa: BLE001
            res["cross_check_x0"] = f"unreadable: {exc}"
    return res


def validate_prod_argv(src: dict) -> list[str]:
    argv = src["argv"]
    probs = []
    for names, val in PROD_REQUIRED:
        got = _flag_val(argv, names)
        if got != val:
            probs.append(f"prod argv {names[0]} = {got!r}, expected {val!r}")
    for f in PROD_FLAGS:
        if f not in argv:
            probs.append(f"prod argv missing {f}")
    if Path(_flag_val(argv, ("-m", "--model")) or "").name != MODEL.name:
        probs.append(f"prod -m is not {MODEL.name}")
    if "DFlash2" not in Path(_flag_val(argv, ("-md", "--model-draft")) or "").name:
        probs.append("prod -md is not a DFlash2 drafter")
    if os.path.realpath(argv[0]) != str(EXPECT_BIN_REAL / "llama-server"):
        probs.append(f"prod binary {argv[0]} is not the v10 store binary {EXPECT_BIN_REAL}/llama-server")
    if os.path.realpath(STORE_GPU) != str(EXPECT_BIN_REAL):
        probs.append(f"kernel store {STORE_GPU} -> {os.path.realpath(STORE_GPU)}, expected {EXPECT_BIN_REAL} "
                     "(production moved: re-derive this runner)")
    if src.get("prefix") != PROD_PREFIX:
        probs.append(f"prod launch prefix {src.get('prefix')} != {PROD_PREFIX}")
    if src.get("record_sha_matches") is False:
        probs.append("launch record argv_sha256 does not match its argv")
    return probs


def build_argv(src: dict, port: int, slot_save: Path, lv: int, b: int | None = None, ub: int | None = None
               ) -> tuple[list[str], list[str]]:
    """Production argv with ONLY: --port, --slot-save-path, -lv (and -b/-ub when an arm caps them)."""
    a = list(src["argv"])
    notes = []
    changes = [(("--port",), str(port)), (("--slot-save-path",), str(slot_save)),
               (("--verbosity", "-lv", "--log-verbosity"), str(lv))]  # --verbosity: confirmed in v10 strings
    if b is not None:
        changes.append((("-b", "--batch-size"), str(b)))
    if ub is not None:
        changes.append((("-ub", "--ubatch-size"), str(ub)))
    for names, val in changes:
        old = _flag_val(a, names)
        a = _set(a, names, val)
        notes.append(f"{names[0]} {old if old is not None else '(absent)'} -> {val}")
    return a, notes


def source_env() -> dict:
    pid = port_pid(8083)
    if pid:
        pe = proc_environ(pid)
        if pe:
            return {"env": {k: pe[k] for k in ENV_KEYS if k in pe}, "source": f"live :8083 PID {pid} environ"}
    env = dict(ENV_FALLBACK)
    src = "fallback: env recorded by b4i launch_ON.sh from live :8083 PID 1703677 (2026-10-04T02:48Z)"
    try:  # cross-check against the recorded script so a stale constant cannot slip through
        txt = B4I_LAUNCH_ON.read_text()
        line = next(ln for ln in txt.splitlines() if ln.startswith("nohup env "))
        rec = {}
        for tok in shlex.split(line):
            m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", tok)
            if m and m.group(1) in ENV_KEYS:
                rec[m.group(1)] = m.group(2)
        src += "; matches the script" if rec == env else f"; DIFFERS from the script {rec}"
    except Exception as exc:  # noqa: BLE001
        src += f"; script cross-check failed: {exc}"
    return {"env": env, "source": src}


def child_env(prod_env: dict, extra: dict | None = None, shim_log: Path | None = None) -> tuple[dict, dict]:
    """Ambient env minus anything that could change the server (LLAMA_ARG_*, GGML_*, LD_PRELOAD, SLOTS_DEBUG,
    rocBLAS/HIP debug knobs), plus the production env, plus the arm's own knobs."""
    drop = [k for k in os.environ if k.startswith(("LLAMA_ARG_", "GGML_", "ROCBLAS_", "HIPBLASLT_", "AMD_LOG", "HIP_TRACE"))
            or k in ("LD_PRELOAD", "LLAMA_SERVER_SLOTS_DEBUG", "LD_LIBRARY_PATH")]
    env = {k: v for k, v in os.environ.items() if k not in drop}
    env.update(prod_env)
    env.update(extra or {})
    if shim_log is not None:
        env["LD_PRELOAD"] = str(SHIM)
        env["KVU16H_SHIM_LOG"] = str(shim_log)
    return env, {"dropped_ambient": sorted(drop), "set": {**prod_env, **(extra or {})},
                 "shim": None if shim_log is None else {"LD_PRELOAD": str(SHIM), "KVU16H_SHIM_LOG": str(shim_log)}}


# ---------------------------------------------------------------- own-PID lifecycle
def _pump(stream, fh) -> None:
    for line in iter(stream.readline, b""):
        fh.write(b"%.3f " % time.time() + line)  # arrival epoch prefix -> phase windows by wall time
        fh.flush()
    fh.close()


def start_own(argv: list[str], log_path: Path, env: dict) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    fh = open(log_path, "ab")
    t = threading.Thread(target=_pump, args=(p.stdout, fh), daemon=True)
    t.start()
    p._pump_thread = t  # type: ignore[attr-defined]
    OWN_CHILDREN.append(p)
    return p


def stop_own(p: subprocess.Popen, term_wait: float = 120.0) -> dict:
    """SIGTERM (graceful: llama-server prints the exit memory breakdown) -> wait -> SIGKILL; verify with ps -p."""
    rec = {"pid": p.pid, "already_exited": p.poll() is not None, "sent": [], "at": now_iso()}
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
    rec.update(verified_dead=not alive, returncode=p.returncode)
    if p in OWN_CHILDREN:
        OWN_CHILDREN.remove(p)
    if alive:
        raise RuntimeError(f"own child {p.pid} still alive after TERM/KILL")
    return rec


def _cleanup(*_a) -> None:
    for p in list(OWN_CHILDREN):
        try:
            print(f"[kvu16h] cleanup: stopping own pid {p.pid}", flush=True)
            stop_own(p, term_wait=90)
        except Exception as exc:  # noqa: BLE001
            print(f"[kvu16h] cleanup of own pid {p.pid} failed: {exc}", flush=True)


atexit.register(_cleanup)


def install_signal_handlers() -> None:
    def _sig(signum, _frame):
        _cleanup()
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)


def http_json(url: str, body: dict | None = None, timeout: float = 30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def wait_healthy(base: str, proc: subprocess.Popen, timeout: float = 900, abort: threading.Event | None = None) -> float:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited rc={proc.returncode} before healthy")
        if abort is not None and abort.is_set():
            raise RuntimeError("VRAM ceiling abort during load")
        try:
            if http_json(base + "/health", timeout=5).get("status") == "ok":
                return round(time.time() - t0, 1)
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    raise TimeoutError("server not healthy")


def hip_dlopen_proof(pid: int, bin_real: Path) -> dict:
    """/proc/<pid>/maps: which libggml* and the shim are mapped (ldd cannot prove a dlopen'ed HIP backend)."""
    try:
        maps = Path(f"/proc/{pid}/maps").read_text()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "err": str(exc)[:200]}
    libs = sorted({ln.split()[-1] for ln in maps.splitlines() if ln.split() and ln.split()[-1].startswith("/")
                   and (".so" in ln.split()[-1])})
    ggml = [x for x in libs if "libggml" in x or "libllama" in x]
    hip = [x for x in ggml if "libggml-hip" in x]
    ok = bool(hip) and all(os.path.realpath(x).startswith(str(bin_real) + "/") for x in ggml)
    return {"ok": ok, "ggml_libs": ggml, "hip_mapped": hip, "shim_mapped": [x for x in libs if "hipmalloc_trace" in x],
            "all_libs": libs}


# ---------------------------------------------------------------- samplers + ceiling watchdog
class VramSampler:
    """1 Hz: card2 used/total (sysfs) + every KFD pid's VRAM. Started BEFORE the server launch. Sets `abort`
    when the own pid's KFD VRAM or the card's used VRAM exceeds the ceiling."""

    def __init__(self, path: Path, ceiling_gib: float, period: float = 1.0) -> None:
        self.sink = Jsonl(path)
        self.period, self.ceiling_b = period, int(ceiling_gib * GIB)
        self.own_pid: int | None = None
        self.abort = threading.Event()
        self.abort_reason: str | None = None
        self.last: dict = {}
        self.peak_own_b = 0
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            used, total = card_vram()
            pids = kfd_pids()
            own = pids.get(self.own_pid, {}).get("vram_b") if self.own_pid else None
            s = {"t": round(time.time(), 3), "card_used_b": used, "card_total_b": total, "own_pid": self.own_pid,
                 "own_vram_b": own, "pids": {str(k): v for k, v in pids.items()}}
            self.last = s
            if own:
                self.peak_own_b = max(self.peak_own_b, own)
            self.sink.add(s)
            if not self.abort.is_set():
                if own is not None and own > self.ceiling_b:
                    self.abort_reason = f"own pid {self.own_pid} KFD VRAM {own / GIB:.3f} GiB > ceiling {self.ceiling_b / GIB} GiB"
                elif used is not None and used > self.ceiling_b:
                    self.abort_reason = f"card used {used / GIB:.3f} GiB > ceiling {self.ceiling_b / GIB} GiB"
                if self.abort_reason:
                    self.abort.set()
                    self.sink.add({"t": round(time.time(), 3), "abort": self.abort_reason})
                    print(f"[kvu16h] ABORT: {self.abort_reason}", flush=True)
            self._stop.wait(self.period)

    def start(self):
        self._t.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._t.join(timeout=10)


class SmiSampler:
    """rocm-smi --showmeminfo vram --json, back to back at >= `period` s (one call takes ~0.3 s)."""

    def __init__(self, path: Path, period: float = 1.0) -> None:
        self.sink, self.period = Jsonl(path), period
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            t0 = time.time()
            rec: dict = {"t0": round(t0, 3)}
            try:
                out = subprocess.run(["rocm-smi", "--showmeminfo", "vram", "--json"], capture_output=True, text=True,
                                     timeout=10).stdout
                d = json.loads(out[out.index("{"):]) if "{" in out else {}
                rec["cards"] = {c: {"used_b": int(v.get("VRAM Total Used Memory (B)", 0)),
                                    "total_b": int(v.get("VRAM Total Memory (B)", 0))} for c, v in d.items()}
            except Exception as exc:  # noqa: BLE001
                rec["err"] = f"{type(exc).__name__}: {exc}"[:200]
            rec["t1"] = round(time.time(), 3)
            self.sink.add(rec)
            self._stop.wait(max(0.0, self.period - (time.time() - t0)))

    def start(self):
        self._t.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._t.join(timeout=15)


class Marks:
    """Phase markers with the server-log and shim-log byte offsets at each boundary."""

    def __init__(self, path: Path, server_log: Path, shim_log: Path | None) -> None:
        self.sink, self.server_log, self.shim_log = Jsonl(path), server_log, shim_log

    @staticmethod
    def _size(p: Path | None) -> int | None:
        try:
            return p.stat().st_size if p else None
        except OSError:
            return None

    def mark(self, phase: str, event: str, **extra) -> dict:
        rec = {"t": round(time.time(), 3), "at": now_iso(), "phase": phase, "event": event,
               "server_log_off": self._size(self.server_log), "shim_log_off": self._size(self.shim_log), **extra}
        self.sink.add(rec)
        print(f"[kvu16h {time.strftime('%H:%M:%SZ', time.gmtime())}] {phase} {event} "
              + " ".join(f"{k}={v}" for k, v in extra.items()), flush=True)
        return rec
