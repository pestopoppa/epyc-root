#!/usr/bin/env python3
"""INF-80 X0 shared helpers: own-child process lifecycle, VRAM sampler, HTTP, residency proof.

Stdlib only. Every process this module starts is tracked by PID in OWN_CHILDREN and is the
only thing it will ever signal. Never signals anything by name.
"""
from __future__ import annotations

import atexit
import json
import os
import signal
import sys
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

X0 = Path("/mnt/raid0/llm/tmp/x0-27b-quants")
RESULTS = X0 / "results"
BIN = Path("/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin")  # == kernels/production/gpu
STORE = Path("/mnt/raid0/llm/kernels/production/gpu")
MODELS = {
    "q8": Path("/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf"),
    "q4": Path("/mnt/raid0/llm/models/Qwen3.8-27B-UD-Q4_K_M.gguf"),
}
DRAFTER = Path("/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf")
TEMPLATE = Path("/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja")
LINKAGE = Path("/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh")
KFD_PROC = Path("/sys/class/kfd/kfd/proc")

OWN_CHILDREN: list[subprocess.Popen] = []


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def gpu_env() -> dict:
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = f"{BIN}:" + env.get("LD_LIBRARY_PATH", "")
    env.pop("GGML_NOHUGEPAGE_PROCESS", None)  # CPU-only shim; must not ride on GPU recipes
    return env


# ---------------------------------------------------------------- process lifecycle (own PIDs only)
def start_own(argv: list[str], log_path: Path, cpu_list: str | None = None) -> subprocess.Popen:
    full = (["taskset", "-c", cpu_list] if cpu_list else []) + argv
    fh = open(log_path, "w")
    full = [sys.executable, "-B", str(Path(__file__).with_name("pdeath_exec.py")), str(os.getpid())] + full
    p = subprocess.Popen(full, stdout=fh, stderr=subprocess.STDOUT, env=gpu_env(),
                         start_new_session=False)  # own process group: our signals never leak
    OWN_CHILDREN.append(p)
    if os.environ.get("FILLER_PIDFILE"):
        with open(os.environ["FILLER_PIDFILE"], "a") as pidfile:
            pidfile.write(str(p.pid) + "\n"); pidfile.flush(); os.fsync(pidfile.fileno())
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
            stop_own(p, term_wait=15)
        except Exception as exc:  # noqa: BLE001
            print(f"[x0] cleanup of own pid {p.pid} failed: {exc}", flush=True)


atexit.register(_cleanup)


def _sig(signum, _frame):
    _cleanup()
    raise SystemExit(128 + signum)


signal.signal(signal.SIGTERM, _sig)
signal.signal(signal.SIGINT, _sig)


# ---------------------------------------------------------------- VRAM sampler (during the run)
def vram_now() -> dict:
    """Device-total used VRAM (amdgpu sysfs mem_info_vram_used) + per-KFD-pid VRAM
    (/sys/class/kfd/kfd/proc/<pid>/vram_<gpuid>). Pure sysfs reads: no subprocess, no KFD
    context, negligible CPU (DS41 measures CPU A/Bs on this host)."""
    out = {"t": time.time()}
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


def kfd_pids() -> dict:
    """{pid: {name, vram_b}} for every KFD process, from sysfs."""
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


class VramSampler:
    def __init__(self, path: Path, period: float = 2.0):
        self.path, self.period = path, period
        self.samples: list[dict] = []
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        with open(self.path, "a") as fh:
            while not self._stop.is_set():
                s = vram_now()
                self.samples.append(s)
                fh.write(json.dumps(s) + "\n")
                fh.flush()
                self._stop.wait(self.period)

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
        return {"n_samples": len(used), "peak_used_b": pk, "baseline_used_b": baseline_b,
                "peak_minus_baseline_b": (pk - baseline_b) if (pk is not None and baseline_b is not None) else None,
                "own_pid_peak_vram_b": max(own) if own else None,
                "nonzero_samples": sum(1 for v in own if v > 0) if own else None,
                "peak_used_gib": round(pk / 2**30, 2) if pk else None,
                "own_pid_peak_vram_gib": round(max(own) / 2**30, 2) if own else None}


def foreign_gpu_procs(exclude: set[int] | None = None) -> dict:
    """KFD processes holding VRAM that are not ours (CPU-only speech servers show 0 B and are ignored)."""
    exclude = exclude or set()
    return {pid: v for pid, v in kfd_pids().items() if pid not in exclude and v["vram_b"] > 0}


def hip_dlopen_proof(pid: int) -> dict:
    """llama.cpp dlopens libggml-hip: prove the LIVE process mapped it from our bin dir."""
    try:
        maps = Path(f"/proc/{pid}/maps").read_text()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "err": str(exc)[:200]}
    libs = sorted({ln.split()[-1] for ln in maps.splitlines() if "libggml" in ln and ln.split()[-1].startswith("/")})
    hip = [x for x in libs if "libggml-hip" in x]
    real_bin = str(BIN.resolve())
    ok = bool(hip) and all(os.path.realpath(x).startswith(real_bin + "/") for x in libs)
    return {"ok": ok, "ggml_libs": libs, "hip_mapped": hip}


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
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1) + "\n")
    tmp.replace(path)
