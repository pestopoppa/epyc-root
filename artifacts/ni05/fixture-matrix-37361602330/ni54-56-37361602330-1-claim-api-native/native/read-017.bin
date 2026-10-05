#!/usr/bin/env python3
"""SS-BENCH-GATE-b — read a live CPU bench's REAL core claim from /proc.

The bench's campaign-continuity gate (epyc-inference-research, Laguna Q4 CPU
bench runner) keys on CORE OVERLAP: any foreign process whose threads can run
on the pinned bench cores invalidates the run. On 2026-07-27 a `reload
orchestrator` spawned an accelerated sidecar whose default affinity covered
the bench's cores and destroyed 1h09m of decision-gating measurement.

`guard_against_running_bench` (orchestrator_stack.py) refuses lifecycle
actions while a bench driver is detectable (SS-BENCH-GATE-a, 2026-07-27).
This module is the durable half (b): the launcher must not SPAWN anything onto
the bench's cores in the first place.

Why read the claim from the live process instead of re-declaring it: a
declared core set can drift from reality (the whole class of defect this repo
is eliminating). The bench's real claim is the union of `Cpus_allowed_list`
across every thread of every live bench driver, parsed with the same
fail-closed semantics the bench runner itself uses. Unknown must mean busy: if
any thread set is unreadable or unstable, the claim is UNOBSERVABLE and is
treated as overlapping everything.

The placement decision is a pure function of (requested placement, claim) so
it is unit-testable without live processes; the /proc and ps readers are
behind injectable seams (proc_root / detect callable).
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

# Single source of truth for bench-driver identity. `guard_against_running_bench`
# in orchestrator_stack.py imports `detect_running_cpu_bench` from here, and the
# placement guard below uses the same detection — a process-name list must not
# be restated anywhere else (a second table is one drift away from the first).
_BENCH_PROCESS_MARKERS = (
    "_bench_runner.py",
    "bench_runner.py",
    "v7_quality_gate_runner.py",
    "llama-bench",
    "run_e8_quality_baseline_reseed.py",
)

_CPU_ITEM_RE = re.compile(r"\d+(?:-\d+)?")


class BenchObservationError(RuntimeError):
    """A bench's core claim could not be read or parsed reliably. Fail closed."""


class BenchPlacementRefusal(RuntimeError):
    """A requested spawn placement cannot be proven disjoint from a live bench.

    Raised by `enforce_placement` AFTER the incident context has been printed;
    the CLI boundary maps it to exit 2 (same exit code as
    `guard_against_running_bench`). A non-empty message is printed at the
    boundary (used by defects that raise before a context was printed).
    """


def is_bench_process(cmd: str) -> bool:
    """Identify the executable or Python script, not text in its arguments.

    `ps args` flattens argv: do not shell-parse an actor's free-text prompt.
    Shell/launch wrappers remain conservative because their command may run a
    bench. The actual benchmark child is independently present in the ps scan.
    """
    words = cmd.split()
    if not words:
        return False
    executable = Path(words[0]).name
    if any(marker in executable for marker in _BENCH_PROCESS_MARKERS):
        return True
    if re.fullmatch(r"(?:python|pypy)(?:\d+(?:\.\d+)*)?", executable):
        index = 1
        while index < len(words):
            operand = words[index]
            if operand in {"-c", "-m"}:
                # Inline/module launch is ambiguous, not an exemption.
                return any(marker in cmd for marker in _BENCH_PROCESS_MARKERS)
            if operand == "--":
                index += 1
                break
            if operand in {"-W", "-X", "--check-hash-based-pycs"}:
                index += 2
            elif operand.startswith("-"):
                index += 1
            else:
                break
        return index < len(words) and any(
            marker in Path(words[index]).name for marker in _BENCH_PROCESS_MARKERS
        )
    if executable in {
        "sh", "bash", "dash", "zsh", "ksh", "env", "taskset", "numactl",
        "timeout", "setsid", "nice", "ionice", "nohup", "sudo",
    }:
        return any(marker in cmd for marker in _BENCH_PROCESS_MARKERS)
    return False


def detect_running_cpu_bench() -> list[tuple[int, str]]:
    """Return [(pid, cmdline)] for any bench driver currently running."""
    found: list[tuple[int, str]] = []
    try:
        out = subprocess.run(
            ["ps", "-eo", "pid,args"], capture_output=True, text=True, timeout=10
        ).stdout
    except Exception:
        return found
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        pid_str, _, cmd = line.partition(" ")
        # Skip self and the probe; supervisors that merely name bench binaries
        # in their arguments are excluded inside is_bench_process.
        if "orchestrator_stack.py" in cmd or "ps -eo" in cmd:
            continue
        if not is_bench_process(cmd):
            continue
        try:
            found.append((int(pid_str), cmd[:160]))
        except ValueError:
            continue
    return found


def parse_cpu_list(value: str) -> set[int]:
    """Parse Linux Cpus_allowed_list syntax without accepting malformed affinity.

    Mirrors the parsing proven in the Laguna CPU bench runner
    (laguna_q4_cpu_bench_runner.py): every item must match ``\\d+(?:-\\d+)?``,
    descending ranges are refused, and an empty list is refused. Raising
    `BenchObservationError` on ANY malformed input is the fail-closed contract
    the caller relies on — a claim we cannot parse must mean busy.
    """
    cpus: set[int] = set()
    for item in value.split(","):
        if not _CPU_ITEM_RE.fullmatch(item):
            raise BenchObservationError(f"invalid Cpus_allowed_list: {value!r}")
        start_text, separator, end_text = item.partition("-")
        start = int(start_text)
        end = int(end_text) if separator else start
        if end < start:
            raise BenchObservationError(f"descending Cpus_allowed_list range: {value!r}")
        cpus.update(range(start, end + 1))
    if not cpus:
        raise BenchObservationError("empty Cpus_allowed_list")
    return cpus


def format_cpu_list(cores) -> str:
    """Fold a collection of cpu ids into "0-95,120-143" list syntax."""
    ordered = sorted(cores)
    if not ordered:
        return ""
    ranges: list[str] = []
    start = prev = ordered[0]
    for cpu in ordered[1:]:
        if cpu == prev + 1:
            prev = cpu
            continue
        ranges.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = cpu
    ranges.append(str(start) if start == prev else f"{start}-{prev}")
    return ",".join(ranges)


def placement_overlaps(placement: str, claimed: set[int]) -> bool:
    """True when an explicit placement intersects a claimed core set.

    Raises BenchObservationError on a malformed placement — a placement we
    cannot parse cannot be proven disjoint, so the caller treats it as overlap.
    """
    return bool(parse_cpu_list(placement) & claimed)


def _status_cpu_allowed_list(status_path: Path) -> str:
    """Read + validate Cpus_allowed_list from a /proc `status` file."""
    try:
        text = status_path.read_text()
    except FileNotFoundError as exc:
        raise BenchObservationError(f"{status_path} unreadable") from exc
    for line in text.splitlines():
        if line.startswith("Cpus_allowed_list:"):
            value = line.split(":", 1)[1].strip()
            parse_cpu_list(value)
            return value
    raise BenchObservationError(f"{status_path} lacks Cpus_allowed_list")


def _list_task_tids(task_dir: Path) -> list[str]:
    """Stable-sorted numeric tid listing of a /proc/<pid>/task directory."""
    return sorted(entry.name for entry in task_dir.iterdir() if entry.name.isdigit())


def _pid_thread_core_sets(pid: int, proc_root: Path) -> list[frozenset[int]]:
    """One stable all-thread affinity snapshot; fail closed on churn.

    Mirrors the bench runner's `proc_thread_cpu_allowed_lists`: capture the
    tid set BEFORE reading, read every thread's status, verify the tid set
    AFTER is identical. A thread set that changes mid-capture is a racing
    process, and a racing process cannot be safely classified.
    """
    task_dir = proc_root / str(pid) / "task"
    try:
        before = _list_task_tids(task_dir)
        if not before:
            raise BenchObservationError(f"bench pid {pid} has no task entries")
        sets = [
            frozenset(parse_cpu_list(_status_cpu_allowed_list(task_dir / tid / "status")))
            for tid in before
        ]
        after = _list_task_tids(task_dir)
    except FileNotFoundError as exc:
        raise BenchObservationError(f"bench pid {pid} vanished during affinity capture") from exc
    if before != after:
        raise BenchObservationError(f"bench pid {pid} thread set changed during affinity capture")
    return sets


@dataclass(frozen=True)
class BenchClaim:
    """Union of core ids a live bench's threads can run on.

    `unobservable=True` means the claim could not be read reliably — unknown
    must mean busy, so such a claim overlaps EVERY placement. `procs` carries
    (pid, cmdline) of the detected drivers so refusal messages can print the
    incident context.
    """

    unobservable: bool = False
    cores: frozenset[int] = frozenset()
    procs: tuple[tuple[int, str], ...] = ()

    @property
    def empty(self) -> bool:
        return not self.unobservable and not self.cores


EMPTY_BENCH_CLAIM = BenchClaim()


def read_bench_claim(
    proc_root: Path = Path("/proc"),
    detect: Callable[[], list[tuple[int, str]]] | None = None,
) -> BenchClaim:
    """Read the LIVE core claim of every running bench driver.

    Main pid `Cpus_allowed_list` (/proc/<pid>/status) plus every thread
    (/proc/<pid>/task/*/status), unioned. If ANY process or thread is
    unreadable, malformed, or unstable the whole claim is UNOBSERVABLE — one
    unreadable driver already disqualifies the spawn, so the partial union of
    the rest buys nothing.
    """
    detector = detect if detect is not None else detect_running_cpu_bench
    procs = detector()
    if not procs:
        return EMPTY_BENCH_CLAIM
    union: set[int] = set()
    for pid, _cmdline in procs:
        try:
            union.update(parse_cpu_list(_status_cpu_allowed_list(proc_root / str(pid) / "status")))
            for cores in _pid_thread_core_sets(pid, proc_root):
                union.update(cores)
        except BenchObservationError:
            return BenchClaim(unobservable=True, procs=tuple(procs))
    return BenchClaim(cores=frozenset(union), procs=tuple(procs))


def host_core_set(
    online_path: Path = Path("/sys/devices/system/cpu/online"),
) -> frozenset[int] | None:
    """All logical cpu ids on the host; None when unreadable (fail closed)."""
    try:
        return frozenset(parse_cpu_list(online_path.read_text().strip()))
    except (OSError, BenchObservationError):
        return None


def decide_placement(
    placement: str | None,
    *,
    force: bool,
    claim: BenchClaim,
    host_cores: frozenset[int] | None = None,
) -> tuple[str, str | None, str | None]:
    """Decide a spawn placement against a bench claim. PURE — no IO, no printing.

    Args:
        placement: declared cpu list ("0-95,...") of the spawn, or None when
            the spawn has no explicit pinning (default affinity = all cores).
        force: --allow-during-bench semantics; force bypasses refusals.
        claim: the bench's live core claim (EMPTY_BENCH_CLAIM when no bench).
        host_cores: all host cpu ids, needed only when `placement` is None and
            the claim is non-empty. None means the host set is unknown.

    Returns (kind, effective, reason):
        ("proceed", None, None)      — spawn as requested (claim empty, or
                                       placement proven disjoint, or force).
        ("pin", cpu_list, None)      — spawn pinned to cpu_list instead of its
                                       default affinity (non-overlapping subset).
        ("refuse", None, reason)     — abort the spawn unless force. `reason`
                                       is the human-readable cause.
    """
    if claim.empty:
        return ("proceed", None, None)
    if claim.unobservable:
        # Unknown must mean busy: overlap with everything.
        if force:
            return ("proceed", None, None)
        return (
            "refuse",
            None,
            "the bench's core claim is unobservable (unknown must mean busy)",
        )
    if placement is not None:
        try:
            overlap = placement_overlaps(placement, set(claim.cores))
        except BenchObservationError:
            # A declared placement we cannot parse cannot be proven disjoint.
            if force:
                return ("proceed", None, None)
            return (
                "refuse",
                None,
                f"declared placement {placement!r} cannot be parsed",
            )
        if overlap:
            if force:
                return ("proceed", None, None)
            return (
                "refuse",
                None,
                f"requested placement {placement} overlaps CPU bench cores "
                f"{format_cpu_list(claim.cores)}",
            )
        return ("proceed", None, None)
    # No explicit placement: default affinity covers every core. Prefer pinning
    # to a non-overlapping subset over refusing — the stack stays functional
    # during a bench. Refuse only when no such subset exists.
    if host_cores is None:
        if force:
            return ("proceed", None, None)
        return (
            "refuse",
            None,
            "cannot determine a non-overlapping placement (host core set unknown)",
        )
    fallback = host_cores - set(claim.cores)
    if not fallback:
        if force:
            return ("proceed", None, None)
        return (
            "refuse",
            None,
            "the bench claims every host core; no non-overlapping placement exists",
        )
    return ("pin", format_cpu_list(fallback), None)


def refusal_message(label: str, placement: str | None, claim: BenchClaim, reason: str) -> str:
    """The incident-context refusal text, mirroring guard_against_running_bench."""
    lines = [f"REFUSING to spawn {label}: {reason}"]
    for pid, cmd in claim.procs:
        lines.append(f"    PID {pid}: {cmd}")
    lines.append(
        "  A lifecycle action spawns stack processes that can overlap the bench's\n"
        "  pinned cores, and the bench's campaign-continuity gate will invalidate\n"
        "  the run (this destroyed 1h09m of decision-gating measurement on\n"
        "  2026-07-27). Wait for the bench, or pass --allow-during-bench if the\n"
        "  operator has accepted that the run may be invalidated."
    )
    return "\n".join(lines)


def pin_message(label: str, cpu_list: str, claim: BenchClaim) -> str:
    """Notice printed when a default-affinity spawn is pinned off the claim."""
    return (
        f"Pinning {label} to cores {cpu_list}: a CPU benchmark claims cores "
        f"{format_cpu_list(claim.cores)} and this spawn has no explicit placement "
        "(default affinity would overlap the bench's campaign-continuity gate)."
    )


def enforce_placement(
    placement: str | None,
    *,
    force: bool,
    label: str,
    claim: BenchClaim | None = None,
    host_cores: frozenset[int] | None = None,
    proc_root: Path = Path("/proc"),
    online_path: Path = Path("/sys/devices/system/cpu/online"),
) -> str | None:
    """Guarded spawn placement — the launcher-facing entry point.

    Returns the cpu list to pin the spawn to, or None when the spawn keeps its
    original prefix (either no bench is live, or the placement is disjoint, or
    force bypassed a refusal). On refusal, prints the incident context and
    raises BenchPlacementRefusal; the CLI boundary maps it to exit 2.
    """
    claim_used = claim if claim is not None else read_bench_claim(proc_root=proc_root)
    needs_host = placement is None and not claim_used.empty
    host = (
        host_cores
        if host_cores is not None
        else (host_core_set(online_path) if needs_host else None)
    )
    kind, effective, reason = decide_placement(
        placement, force=force, claim=claim_used, host_cores=host
    )
    if kind == "refuse":
        print(refusal_message(label, placement, claim_used, reason))
        raise BenchPlacementRefusal()
    if kind == "pin":
        print(pin_message(label, effective, claim_used))
        return effective
    return None


# The running API has no CLI flags, so the launcher's --allow-during-bench
# (SS-BENCH-GATE-b) becomes an env knob for the API's own spawn layer
# (SS-BENCH-GATE-c), evaluated at spawn time so it can be toggled without a
# restart. Same semantics: 1 = the operator has accepted that the bench run
# may be invalidated.
API_BENCH_ALLOW_ENV = "ORCHESTRATOR_ALLOW_DURING_BENCH"


def api_enforce_placement(
    placement: str | None,
    *,
    label: str,
    claim: BenchClaim | None = None,
    host_cores: frozenset[int] | None = None,
    proc_root: Path = Path("/proc"),
    online_path: Path = Path("/sys/devices/system/cpu/online"),
) -> str | None:
    """SS-BENCH-GATE-c — placement guard for the running API's own spawns.

    Same decision machinery as `enforce_placement` (reused unchanged), with
    `--allow-during-bench` replaced by the ORCHESTRATOR_ALLOW_DURING_BENCH=1
    environment variable. Refusals raise `BenchPlacementRefusal` exactly as
    in the CLI path; the spawn site maps the exception to its own failure
    handling, which must fail closed (nothing spawns). Every spawn that
    happens while a bench claim is live and the knob is set is logged loudly —
    a bypass an operator cannot see in the logs is a bypass that silently
    invalidates a run.

    Returns the cpu list to pin the spawn to, or None when the spawn keeps its
    original prefix (no bench live, requested placement disjoint, or the knob
    bypassed a refusal).
    """
    claim_used = claim if claim is not None else read_bench_claim(proc_root=proc_root)
    force = os.environ.get(API_BENCH_ALLOW_ENV, "") == "1"
    if force and not claim_used.empty:
        logger.warning(
            "%s=1: spawning %s while a CPU bench claims cores %s — the bench's "
            "campaign-continuity gate may invalidate the run",
            API_BENCH_ALLOW_ENV,
            label,
            format_cpu_list(claim_used.cores) if not claim_used.unobservable else "UNOBSERVABLE",
        )
    return enforce_placement(
        placement,
        force=force,
        label=label,
        claim=claim_used,
        host_cores=host_cores,
        proc_root=proc_root,
        online_path=online_path,
    )
