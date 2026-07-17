#!/usr/bin/env python3
"""B7 — Quiet-window detector for the inference-batch loop.

The operator rider (plan Constraints §21): the eventual /loop that consumes the
inference-batch manifest MUST NEVER compete with the parallel agent's compute.
This module is the read-only gate the loop consults before it does anything that
touches shared compute.

It answers two questions:

  * ``is_quiet_window() -> (bool, reasons)`` — True only when *every* competing
    signal is confirmed absent (see the exact predicate below). Any signal that
    is present, or that cannot be confirmed absent because a probe tool is
    missing, keeps the window non-quiet. Fail-safe by construction.

  * ``classify_load() -> dict`` — a three-way label ``quiet | serial_ok | busy``.
    ``serial_ok`` means "no hard compute competitor is running, but the window is
    not provably quiet" — light enough for ``serial_noninference`` batch entries
    (which perform no inference) but NOT for anything that would run a model.

Exact QUIET predicate (all five must hold):
  1. No live ``llama-server`` *decode* traffic. ``pgrep`` finds no llama-server, OR
     every discovered server port reports zero busy slots via /slots. A resident
     server we cannot probe ("unconfirmed") is NOT quiet.
  2. No ``llama-bench`` / ``llama-cli`` / eval / benchmark harness processes
     (the parallel session's smokes) — see BENCH_CLI_EVAL_PATTERNS.
  3. No heavy model downloads — hf / huggingface-cli / curl / wget / aria2c whose
     argv references a model path/extension (see DOWNLOAD_PATH_MARKERS).
  4. MI210 confirmed unoccupied via ``rocm-smi`` (util below MI210_UTIL_PCT_THRESHOLD
     AND VRAM-used below MI210_VRAM_USED_MB_THRESHOLD on every card). rocm-smi
     absent or unparseable → "cannot confirm" → NOT quiet (conservative).
  5. AutoPilot stopped — no ``autopilot.py start`` process and its singleton
     flock is not held.

Conservative-on-missing-tool: pgrep missing → the process-based conditions are
"unconfirmed" (not quiet, but not a positive busy signal → serial_ok). rocm-smi
missing/unparseable → GPU unconfirmed (not quiet → serial_ok).

Read-only everything: pgrep / rocm-smi / /proc cmdline reads / a non-blocking
flock *test* that acquires-and-immediately-releases without writing. No stack,
flag, registry, or file mutation. NO inference. Stdlib only.

This file deliberately does NOT import or call any nightshift script; it only
imitates the load-gating *idea* of scripts/nightshift/inference_guard.sh.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------- #
# Tunables / patterns
# --------------------------------------------------------------------------- #
# MI210 (gfx90a, 64 GB): a loaded model occupies GBs; idle driver overhead is a
# few MB (~13 MB observed). 512 MB used or >5% util means someone is on the GPU.
MI210_VRAM_USED_MB_THRESHOLD = 512.0
MI210_UTIL_PCT_THRESHOLD = 5.0

DEFAULT_HEALTH_TIMEOUT = 2.0

# Full-cmdline (pgrep -f) patterns for the parallel session's inference smokes.
BENCH_CLI_EVAL_PATTERNS = [
    "llama-bench",
    "llama-cli",
    "llama-batched",
    "llama-perplexity",
    "llama-speculative",
    "run_benchmark.py",
    "bench_canonical",
    "canonical_recipe",
    "run_batch_entry.py",
]

# Downloader binaries + argv markers that identify a *model* download (as opposed
# to an incidental curl to a health endpoint).
DOWNLOADER_BINS = ["aria2c", "wget", "curl", "huggingface-cli", "hf"]
DOWNLOAD_PATH_MARKERS = [
    ".gguf",
    ".safetensors",
    "/models/",
    "huggingface.co",
    "hf.co",
    "resolve/main",
    "/raid0/llm/models",
    "cdn-lfs",
]

LLAMA_SERVER_PATTERN = "llama-server"
AUTOPILOT_PATTERN = "autopilot.py start"
# The supervisor is a liveness signal in its own right: during its <=30s restart
# delay the main `autopilot.py start` loop is momentarily absent, so a probe that
# watched only AUTOPILOT_PATTERN would read "stopped" mid-restart. Mirror the
# canonical launcher's dual pattern (start_fable_authority_daemon.py:
# LIVE_PROCESS_PATTERN + LIVE_SUPERVISOR_PATTERN).
AUTOPILOT_SUPERVISOR_PATTERN = "autopilot_supervisor.py"
AUTOPILOT_LOCK = Path("/mnt/raid0/llm/epyc-orchestrator/orchestration/.autopilot.lock")

# Daemons whose argv *mentions* llama-* / bench binaries as regex arguments (not as
# an executed program) and must never be counted as inference/bench competitors.
# e.g. earlyoom --ignore ^(llama-server|sd-server)$ --prefer ^llama-bench$
_EXCLUDE_COMM = frozenset({"earlyoom", "pgrep", "grep", "tail", "watch"})

_PORT_RE = re.compile(r"--port[= ]+(\d+)")


# --------------------------------------------------------------------------- #
# Low-level read-only probes (all mockable at this boundary)
# --------------------------------------------------------------------------- #
def _run(cmd: list[str], timeout: float = 6.0) -> subprocess.CompletedProcess | None:
    """Run a read-only command. Returns None if the tool is missing or errors out.

    None is the "cannot run this probe" sentinel — callers treat it conservatively.
    """
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None


def _pgrep(pattern: str) -> list[tuple[int, str]] | None:
    """Return [(pid, argline), ...] for processes whose full cmdline matches
    `pattern` (extended regex). Returns None if pgrep is unavailable/errors —
    the "cannot confirm" sentinel. Excludes our own pid, this checker, and the
    known daemons in _EXCLUDE_COMM (argv[0] basename).
    """
    res = _run(["pgrep", "-af", pattern])
    if res is None or res.returncode not in (0, 1):
        return None
    out: list[tuple[int, str]] = []
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        try:
            pid = int(parts[0])
        except (ValueError, IndexError):
            continue
        argline = parts[1] if len(parts) > 1 else ""
        if pid == os.getpid() or "inference_load_check" in argline:
            continue
        argv0 = argline.split(None, 1)[0] if argline else ""
        if argv0.rsplit("/", 1)[-1] in _EXCLUDE_COMM:
            continue
        out.append((pid, argline))
    return out


def _runs_binary(argline: str, names: list[str]) -> bool:
    """True iff the process actually *executes* one of `names` — a token whose
    basename equals or starts with a name — rather than merely mentioning it as
    an argument value (e.g. earlyoom's ``--ignore ^llama-server$``).
    """
    for token in argline.split():
        base = token.rsplit("/", 1)[-1]
        for name in names:
            if base == name or base.startswith(name):
                return True
    return False


def _http_json(url: str, timeout: float):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (localhost)
            if getattr(resp, "status", 200) != 200:
                return None
            return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:  # noqa: BLE001 — any failure ⇒ cannot confirm
        return None


def _slots_active_count(port: int, timeout: float) -> int | None:
    """Count busy slots on a llama-server /slots endpoint.

    Returns 0 (idle), >0 (decoding), or None (endpoint unreachable/disabled ⇒
    cannot confirm idle).
    """
    data = _http_json(f"http://localhost:{port}/slots", timeout)
    if not isinstance(data, list):
        return None
    busy = 0
    for slot in data:
        if not isinstance(slot, dict):
            continue
        state = slot.get("state", slot.get("is_processing"))
        if state is True or (isinstance(state, int) and state != 0):
            busy += 1
    return busy


def _autopilot_lock_held(lock_path: Path = AUTOPILOT_LOCK) -> bool:
    """True iff AutoPilot's singleton EX flock is currently held by another process.

    Read-only: acquires a non-blocking lock and immediately releases it *without
    writing* to the file; if acquisition fails with BlockingIOError the lock is
    held elsewhere. Returns False when the file is absent or fcntl is unavailable.
    """
    if not lock_path.exists():
        return False
    try:
        import fcntl

        fd = os.open(str(lock_path), os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            return False
        except (BlockingIOError, OSError):
            return True
        finally:
            os.close(fd)
    except Exception:  # noqa: BLE001
        return False


def _to_float(value) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _first_present(fields: dict, keys: list[str]):
    for key in keys:
        if key in fields:
            return fields[key]
    return None


# --------------------------------------------------------------------------- #
# Signal collectors — each returns a JSON-serializable detail dict
# --------------------------------------------------------------------------- #
def _discover_ports(arglines: list[str]) -> list[int]:
    ports: list[int] = []
    for arg in arglines:
        for match in _PORT_RE.finditer(arg):
            port = int(match.group(1))
            if port not in ports:
                ports.append(port)
    return ports


def llama_decode_state(ports: list[int] | None = None,
                       timeout: float = DEFAULT_HEALTH_TIMEOUT) -> dict:
    """Classify llama-server decode activity.

    state ∈ {none, idle, active, unconfirmed, pgrep_missing}.
    """
    procs = _pgrep(LLAMA_SERVER_PATTERN)
    if procs is None:
        return {"state": "pgrep_missing", "pids": [], "ports": [],
                "detail": "pgrep unavailable — cannot confirm no llama-server"}
    procs = [(p, a) for p, a in procs if _runs_binary(a, ["llama-server"])]
    if not procs:
        return {"state": "none", "pids": [], "ports": [],
                "detail": "no llama-server processes"}
    pids = [p for p, _ in procs]
    discovered = list(ports) if ports is not None else _discover_ports([a for _, a in procs])
    if not discovered:
        return {"state": "unconfirmed", "pids": pids, "ports": [],
                "detail": "llama-server running but no --port discoverable; cannot confirm idle"}
    any_active = False
    unconfirmed_ports: list[int] = []
    per_port: dict[str, int | None] = {}
    for port in discovered:
        depth = _slots_active_count(port, timeout)
        per_port[str(port)] = depth
        if depth is None:
            unconfirmed_ports.append(port)
        elif depth > 0:
            any_active = True
    if any_active:
        state, detail = "active", "at least one slot decoding"
    elif unconfirmed_ports:
        state, detail = "unconfirmed", f"slots unreadable on ports {unconfirmed_ports}; cannot confirm idle"
    else:
        state, detail = "idle", "all discovered slots idle"
    return {"state": state, "pids": pids, "ports": discovered,
            "slots_busy_by_port": per_port, "detail": detail}


def bench_cli_eval_state() -> dict:
    """Detect the parallel session's llama-bench / llama-cli / eval smokes."""
    pattern = "|".join(BENCH_CLI_EVAL_PATTERNS)
    procs = _pgrep(pattern)
    if procs is None:
        return {"running": None, "matches": [],
                "detail": "pgrep unavailable — cannot confirm no bench/cli/eval"}
    matches = [{"pid": p, "arg": a} for p, a in procs
               if _runs_binary(a, BENCH_CLI_EVAL_PATTERNS)]
    return {"running": bool(matches), "matches": matches,
            "detail": f"{len(matches)} bench/cli/eval process(es)" if matches else "none"}


def heavy_download_state() -> dict:
    """Detect model downloads (downloader binary whose argv names a model path)."""
    matches: list[dict] = []
    pgrep_missing = False
    for binname in DOWNLOADER_BINS:
        procs = _pgrep(binname)
        if procs is None:
            pgrep_missing = True
            continue
        for pid, arg in procs:
            if _runs_binary(arg, [binname]) and any(m in arg for m in DOWNLOAD_PATH_MARKERS):
                matches.append({"pid": pid, "bin": binname, "arg": arg})
    if matches:
        return {"running": True, "matches": matches,
                "detail": f"{len(matches)} model download(s)"}
    if pgrep_missing:
        return {"running": None, "matches": [],
                "detail": "pgrep unavailable — cannot confirm no downloads"}
    return {"running": False, "matches": [], "detail": "none"}


def mi210_state() -> dict:
    """Occupancy of the MI210 via rocm-smi.

    occupied ∈ {True, False, None}; confirmable is False when rocm-smi is absent
    or unparseable (⇒ cannot confirm unoccupied ⇒ not quiet).
    """
    res = _run(["rocm-smi", "--showuse", "--showmeminfo", "vram", "--json"])
    if res is None or res.returncode != 0 or not res.stdout.strip():
        return {"occupied": None, "confirmable": False, "cards": {},
                "detail": "rocm-smi unavailable"}
    try:
        data = json.loads(res.stdout)
    except (ValueError, TypeError):
        return {"occupied": None, "confirmable": False, "cards": {},
                "detail": "rocm-smi output unparseable"}
    cards: dict[str, dict] = {}
    occupied = False
    for card, fields in data.items():
        if not isinstance(fields, dict):
            continue
        util = _to_float(fields.get("GPU use (%)"))
        used_b = _to_float(_first_present(
            fields,
            ["VRAM Total Used Memory (B)", "VRAM Total Used Memory (B) ",
             "VRAM Used Memory (B)"],
        ))
        used_mb = used_b / (1024 * 1024) if used_b is not None else None
        card_occ = bool(
            (util is not None and util > MI210_UTIL_PCT_THRESHOLD)
            or (used_mb is not None and used_mb > MI210_VRAM_USED_MB_THRESHOLD)
        )
        occupied = occupied or card_occ
        cards[card] = {"util_pct": util, "vram_used_mb": used_mb, "occupied": card_occ}
    if not cards:
        return {"occupied": None, "confirmable": False, "cards": {},
                "detail": "no GPU cards parsed"}
    return {"occupied": occupied, "confirmable": True, "cards": cards,
            "detail": "occupied" if occupied else "idle"}


def autopilot_state(lock_path: Path = AUTOPILOT_LOCK) -> dict:
    """Detect a running AutoPilot loop OR its supervisor (process + singleton flock).

    Two liveness signals are watched: the main ``autopilot.py start`` loop AND the
    ``autopilot_supervisor.py`` daemon — a live supervisor during its <=30s restart
    delay means autopilot IS present even when the loop process is momentarily
    absent (so it counts as ``running``). ``pgrep unavailable`` on BOTH patterns is
    the only "cannot confirm" case (running=None unless the flock is held).
    """
    pids: list[int] = []
    pgrep_ran = False
    # Main loop process.
    loop_procs = _pgrep(AUTOPILOT_PATTERN)
    if loop_procs is not None:
        pgrep_ran = True
        pids += [p for p, a in loop_procs if _runs_binary(a, ["autopilot.py"])]
    # Supervisor daemon (explicit — its basename does not match "autopilot.py").
    sup_procs = _pgrep(AUTOPILOT_SUPERVISOR_PATTERN)
    if sup_procs is not None:
        pgrep_ran = True
        pids += [p for p, a in sup_procs if _runs_binary(a, ["autopilot_supervisor.py"])]
    lock_held = _autopilot_lock_held(lock_path)
    if not pgrep_ran:
        running: bool | None = True if lock_held else None
        pids = []
    else:
        pids = sorted(set(pids))
        running = bool(pids) or lock_held
    detail = "running" if running is True else ("unconfirmed" if running is None else "stopped")
    return {"running": running, "pids": pids, "lock_held": lock_held, "detail": detail}


def collect_signals(ports: list[int] | None = None,
                    health_timeout: float = DEFAULT_HEALTH_TIMEOUT) -> dict:
    """Gather all read-only signals in one shot (JSON-serializable)."""
    return {
        "llama": llama_decode_state(ports, health_timeout),
        "bench_cli_eval": bench_cli_eval_state(),
        "downloads": heavy_download_state(),
        "mi210": mi210_state(),
        "autopilot": autopilot_state(),
    }


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def is_quiet_window(signals: dict | None = None,
                    ports: list[int] | None = None,
                    health_timeout: float = DEFAULT_HEALTH_TIMEOUT) -> tuple[bool, list[str]]:
    """Return (quiet, reasons). quiet is True only when the full predicate holds.

    `reasons` lists every condition that blocks a quiet window (empty ⇒ quiet).
    """
    if signals is None:
        signals = collect_signals(ports=ports, health_timeout=health_timeout)
    reasons: list[str] = []

    # 1 — no llama-server decode traffic
    state = signals["llama"]["state"]
    if state == "active":
        reasons.append("llama-server actively decoding")
    elif state == "unconfirmed":
        reasons.append("llama-server running; decode state unconfirmed (conservative)")
    elif state == "pgrep_missing":
        reasons.append("pgrep unavailable; cannot confirm no llama-server (conservative)")

    # 2 — no bench/cli/eval smokes
    bench = signals["bench_cli_eval"]
    if bench["running"] is True:
        reasons.append(f"bench/cli/eval process(es) running: {len(bench['matches'])}")
    elif bench["running"] is None:
        reasons.append("pgrep unavailable; cannot confirm no bench/cli/eval (conservative)")

    # 3 — no heavy model downloads
    dl = signals["downloads"]
    if dl["running"] is True:
        reasons.append(f"heavy model download(s) running: {len(dl['matches'])}")
    elif dl["running"] is None:
        reasons.append("pgrep unavailable; cannot confirm no downloads (conservative)")

    # 4 — MI210 confirmed unoccupied
    gpu = signals["mi210"]
    if gpu["occupied"] is True:
        reasons.append("MI210 occupied")
    elif not gpu["confirmable"]:
        reasons.append(f"MI210 occupancy unconfirmable ({gpu['detail']}) (conservative)")

    # 5 — autopilot stopped
    ap = signals["autopilot"]
    if ap["running"] is True:
        reasons.append("autopilot running")
    elif ap["running"] is None:
        reasons.append("autopilot state unconfirmable (conservative)")

    return (len(reasons) == 0, reasons)


def classify_load(signals: dict | None = None,
                  ports: list[int] | None = None,
                  health_timeout: float = DEFAULT_HEALTH_TIMEOUT) -> dict:
    """Three-way load classification: quiet | serial_ok | busy.

    * busy      — a hard compute competitor is *positively* running (active
                  decode, bench/cli/eval, model download, MI210 occupied, or
                  autopilot). Run nothing.
    * quiet     — the full quiet predicate holds. Any batch entry may run.
    * serial_ok — no hard competitor, but the window is not provably quiet
                  (a resident-but-unprobeable server, or a missing/unparseable
                  probe). Only ``serial_noninference`` entries may run.
    """
    if signals is None:
        signals = collect_signals(ports=ports, health_timeout=health_timeout)
    quiet, quiet_blockers = is_quiet_window(signals)

    busy_reasons: list[str] = []
    if signals["llama"]["state"] == "active":
        busy_reasons.append("llama-server decode active")
    if signals["bench_cli_eval"]["running"] is True:
        busy_reasons.append("bench/cli/eval running")
    if signals["downloads"]["running"] is True:
        busy_reasons.append("heavy model download running")
    if signals["mi210"]["occupied"] is True:
        busy_reasons.append("MI210 occupied")
    if signals["autopilot"]["running"] is True:
        busy_reasons.append("autopilot running")

    if busy_reasons:
        state = "busy"
    elif quiet:
        state = "quiet"
    else:
        state = "serial_ok"

    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "state": state,
        "quiet": quiet,
        "quiet_blockers": quiet_blockers,
        "busy_reasons": busy_reasons,
        "signals": signals,
    }


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
_EXIT_BY_STATE = {"quiet": 0, "serial_ok": 10, "busy": 20}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="B7 quiet-window detector (read-only).")
    ap.add_argument("--json", action="store_true", help="emit full classification as JSON")
    ap.add_argument("--ports", nargs="*", type=int, default=None,
                    help="override llama-server ports to probe (default: discover from cmdline)")
    ap.add_argument("--health-timeout", type=float, default=DEFAULT_HEALTH_TIMEOUT)
    ap.add_argument("--require", choices=["quiet", "serial_ok"], default=None,
                    help="exit 0 only if classification is at least this permissive")
    args = ap.parse_args(argv)

    result = classify_load(ports=args.ports, health_timeout=args.health_timeout)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"load = {result['state'].upper()}  (quiet={result['quiet']})")
        for reason in result["quiet_blockers"]:
            print(f"  quiet-blocker: {reason}")
        for reason in result["busy_reasons"]:
            print(f"  BUSY: {reason}")

    if args.require == "quiet":
        return 0 if result["state"] == "quiet" else 1
    if args.require == "serial_ok":
        return 0 if result["state"] in ("quiet", "serial_ok") else 1
    return _EXIT_BY_STATE[result["state"]]


if __name__ == "__main__":
    raise SystemExit(main())
