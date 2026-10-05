"""INF-78 OAB-3 (R2): the trailing-work witness.

After ``/chat`` replies, the AutoKernel loop's next step is a CPU measurement window, so no
orchestrator-owned process may keep working. ``ChatRequest.quiescent_after`` is the promise
(``src/runtime/quiescence.py``); this module is the proof. Acceptance is a witness, not a
promise: sample the cumulative ``utime+stime`` of every orchestrator-owned server for N
seconds after the reply and FAIL if any one of them accrues more than 0.5 core-seconds.

The reader is DS41-C2b-gate's (research
``scripts/kernel_rnd/autokernel/execution/screening_baseline.py``: ``_read_process_cpu`` /
``idleness_verdict``), ported rather than imported because the repos do not share code:

* ``/proc/<pid>/stat`` utime+stime is MONOTONE and CUMULATIVE, so two reads that BRACKET the
  window observe the whole window, not an instant inside it — work between the samples
  cannot hide. ``comm`` may contain spaces and parentheses, so fields are taken after the
  LAST ')': utime/stime/starttime are stat fields 14/15/22, offsets 11/12/19 in that tail.
* Unknown is a violation: a pid that vanished, whose number was reused (starttime changed)
  or that appeared mid-window (a new child of an orchestrator process — that IS work) fails
  the window. A present-but-unreadable stat raises rather than reading as idle.

What "orchestrator-owned" means (``discover_orchestrator_pids``): the uvicorn API processes
(cmdline names ``uvicorn`` and ``src.api``) and every descendant, plus each ``llama-server``
whose ``--port`` is one the orchestrator dispatches to (``get_config().server_urls``) or an
embedder port (8090-8095, q-scoring). Discovery only READS ``/proc``; it never signals
anything. Callers may pass explicit pids instead.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

SCHEMA = "epyc.orchestrator.trailing_work_witness.v1"
DEFAULT_WINDOW_S = 60.0
DEFAULT_THRESHOLD_CORE_S = 0.5
EMBEDDER_PORTS = frozenset(range(8090, 8096))

_CLOCK_TICKS_PER_S = os.sysconf("SC_CLK_TCK")
_PORT_RE = re.compile(r"(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d{2,5})")


class WitnessError(RuntimeError):
    """The witness could not read what it must read (fails closed)."""


# ── the reader (ported from DS41-C2b-gate) ───────────────────────────────────


def read_process_cpu(pid: int, proc_root: str = "/proc") -> tuple[int, int] | None:
    """``(cpu_ticks, starttime_ticks)`` for one pid, or None if it vanished."""
    try:
        text = Path(f"{proc_root}/{pid}/stat").read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:  # present but unreadable is NOT absent
        raise WitnessError(f"pid {pid} is present but unreadable: {exc}") from exc
    try:
        tail = text[text.rindex(")") + 2:].split()
        return int(tail[11]) + int(tail[12]), int(tail[19])
    except (ValueError, IndexError) as exc:
        raise WitnessError(f"pid {pid} has an unparsable /proc stat line") from exc


def _read_cmdline(pid: int, proc_root: str = "/proc") -> list[str]:
    try:
        raw = Path(f"{proc_root}/{pid}/cmdline").read_bytes()
    except OSError:
        return []
    return [p.decode("utf-8", "replace") for p in raw.split(b"\0") if p]


def _read_ppid(pid: int, proc_root: str = "/proc") -> int | None:
    try:
        text = Path(f"{proc_root}/{pid}/stat").read_text(encoding="utf-8")
        return int(text[text.rindex(")") + 2:].split()[1])
    except (OSError, ValueError, IndexError):
        return None


def _all_pids(proc_root: str = "/proc") -> list[int]:
    return [int(n) for n in os.listdir(proc_root) if n.isdigit()]


# ── discovery ────────────────────────────────────────────────────────────────


def configured_server_ports() -> set[int]:
    """Ports the orchestrator dispatches to (server_urls) plus the embedder ports."""
    ports: set[int] = set(EMBEDDER_PORTS)
    try:
        from src.config import get_config

        urls = get_config().server_urls
        values = dataclasses.asdict(urls) if dataclasses.is_dataclass(urls) else dict(vars(urls))
        for value in values.values():
            for match in _PORT_RE.finditer(str(value)):
                ports.add(int(match.group(1)))
    except Exception:
        pass
    ports.discard(8000)  # the API itself is found by cmdline, not as a model server
    return ports


def _llama_server_port(cmdline: list[str]) -> int | None:
    for i, arg in enumerate(cmdline):
        if arg == "--port" and i + 1 < len(cmdline):
            try:
                return int(cmdline[i + 1])
            except ValueError:
                return None
        if arg.startswith("--port="):
            try:
                return int(arg.split("=", 1)[1])
            except ValueError:
                return None
    return None


def _is_api_process(cmdline: list[str]) -> bool:
    joined = " ".join(cmdline)
    return "uvicorn" in joined and "src.api" in joined


def discover_orchestrator_pids(
    *,
    ports: Iterable[int] | None = None,
    include_model_servers: bool = True,
    proc_root: str = "/proc",
) -> dict[int, str]:
    """``{pid: label}`` of orchestrator-owned server processes (read-only /proc scan)."""
    wanted_ports = set(ports) if ports is not None else configured_server_ports()
    pids = _all_pids(proc_root)
    cmdlines = {pid: _read_cmdline(pid, proc_root) for pid in pids}
    found: dict[int, str] = {}
    roots = [pid for pid, cmd in cmdlines.items() if cmd and _is_api_process(cmd)]
    for pid in roots:
        found[pid] = "api"
    found.update(_descendants(roots, pids, proc_root, label="api-child"))
    if include_model_servers:
        for pid, cmd in cmdlines.items():
            if cmd and os.path.basename(cmd[0]) == "llama-server":
                port = _llama_server_port(cmd)
                if port is not None and port in wanted_ports:
                    found.setdefault(pid, f"llama-server:{port}")
    return found


def _descendants(roots: Iterable[int], pids: Iterable[int], proc_root: str, *, label: str) -> dict[int, str]:
    children: dict[int, list[int]] = {}
    for pid in pids:
        ppid = _read_ppid(pid, proc_root)
        if ppid is not None:
            children.setdefault(ppid, []).append(pid)
    out: dict[int, str] = {}
    stack = list(roots)
    while stack:
        for child in children.get(stack.pop(), ()):
            if child not in out:
                out[child] = label
                stack.append(child)
    return out


# ── ledger + verdict ─────────────────────────────────────────────────────────


@dataclass
class Ledger:
    read_at_monotonic_s: float
    clock_ticks_per_s: int
    entries: dict[int, dict[str, Any]] = field(default_factory=dict)


def read_ledger(
    pids: Mapping[int, str] | Iterable[int],
    *,
    reader: Callable[[int], tuple[int, int] | None] = read_process_cpu,
    clock: Callable[[], float] = time.monotonic,
) -> Ledger:
    labels = dict(pids) if isinstance(pids, Mapping) else {int(p): "" for p in pids}
    entries: dict[int, dict[str, Any]] = {}
    for pid, label in labels.items():
        sample = reader(int(pid))
        if sample is None:
            entries[int(pid)] = {"label": label, "vanished": True}
            continue
        entries[int(pid)] = {"label": label, "cpu_ticks": sample[0], "starttime_ticks": sample[1]}
    return Ledger(read_at_monotonic_s=clock(), clock_ticks_per_s=_CLOCK_TICKS_PER_S, entries=entries)


def verdict(
    before: Ledger,
    after: Ledger,
    *,
    threshold_core_s: float = DEFAULT_THRESHOLD_CORE_S,
) -> dict[str, Any]:
    """Decide the window. Any process over ``threshold_core_s`` or any unknown fails it."""
    span_s = after.read_at_monotonic_s - before.read_at_monotonic_s
    ticks = float(after.clock_ticks_per_s)
    violations: list[dict[str, Any]] = []
    tolerated: list[dict[str, Any]] = []
    total_core_s = 0.0
    if span_s <= 0 or before.clock_ticks_per_s != after.clock_ticks_per_s:
        violations.append({"pid": None, "reason": "non_monotonic_span", "span_s": span_s})
    for pid, was in sorted(before.entries.items()):
        now = after.entries.get(pid)
        record = {"pid": pid, "label": was.get("label", "")}
        if was.get("vanished"):
            violations.append({**record, "reason": "vanished_before_window"})
            continue
        if now is None or now.get("vanished"):
            violations.append({**record, "reason": "vanished_mid_window"})
            continue
        if was["starttime_ticks"] != now["starttime_ticks"]:
            violations.append({**record, "reason": "pid_reused_mid_window"})
            continue
        delta = int(now["cpu_ticks"]) - int(was["cpu_ticks"])
        core_s = delta / ticks
        total_core_s += max(core_s, 0.0)
        record.update({"cpu_core_seconds": round(core_s, 4)})
        if delta < 0 or core_s > threshold_core_s:
            violations.append({**record, "reason": "cpu_work"})
        else:
            tolerated.append(record)
    for pid, now in sorted(after.entries.items()):
        if pid in before.entries:
            continue
        record = {"pid": pid, "label": now.get("label", ""), "reason": "appeared_mid_window"}
        if not now.get("vanished"):
            # A process born in the window: all of its accrual is window work.
            record["cpu_core_seconds"] = round(int(now["cpu_ticks"]) / ticks, 4)
        violations.append(record)
    return {
        "schema": SCHEMA,
        "span_s": round(span_s, 3),
        "threshold_core_s": threshold_core_s,
        "total_core_s": round(total_core_s, 4),
        "processes": len(before.entries),
        "quiescent": not violations,
        "violations": violations,
        "tolerated": tolerated,
    }


def witness(
    pids: Mapping[int, str] | Iterable[int] | None = None,
    *,
    window_s: float = DEFAULT_WINDOW_S,
    threshold_core_s: float = DEFAULT_THRESHOLD_CORE_S,
    rediscover: Callable[[], Mapping[int, str]] | None = None,
    reader: Callable[[int], tuple[int, int] | None] = read_process_cpu,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Bracket ``window_s`` seconds with two ledgers and return the verdict.

    ``pids=None`` discovers orchestrator-owned processes now and again at the close (so a
    child spawned mid-window is caught as ``appeared_mid_window``). Explicit pids are
    re-read as given unless ``rediscover`` is supplied. Call it IMMEDIATELY after the reply.
    """
    if pids is None:
        pids = discover_orchestrator_pids()
        rediscover = rediscover or discover_orchestrator_pids
    if not pids:
        raise WitnessError("no orchestrator-owned processes to witness (nothing found)")
    before = read_ledger(pids, reader=reader, clock=clock)
    sleep(window_s)
    close_pids: dict[int, str] = dict(pids) if isinstance(pids, Mapping) else {int(p): "" for p in pids}
    if rediscover is not None:
        for pid, label in rediscover().items():
            close_pids.setdefault(int(pid), label)
    after = read_ledger(close_pids, reader=reader, clock=clock)
    out = verdict(before, after, threshold_core_s=threshold_core_s)
    out["window_s"] = window_s
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI: exit 0 when quiescent, 1 when not, 2 when the witness cannot read."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--window-s", type=float, default=DEFAULT_WINDOW_S)
    ap.add_argument("--threshold-core-s", type=float, default=DEFAULT_THRESHOLD_CORE_S)
    ap.add_argument("--pid", type=int, action="append", default=None,
                    help="explicit pid(s); default: discover orchestrator-owned servers")
    ap.add_argument("--list", action="store_true", help="print discovered pids and exit")
    args = ap.parse_args(argv)
    try:
        if args.list:
            print(json.dumps({str(k): v for k, v in discover_orchestrator_pids().items()}, indent=2))
            return 0
        result = witness(args.pid, window_s=args.window_s, threshold_core_s=args.threshold_core_s)
    except WitnessError as exc:
        print(json.dumps({"schema": SCHEMA, "error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["quiescent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
