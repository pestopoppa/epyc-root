"""region-lock — hold CPU-region locks for the lifetime of a child command.

WHY: the orchestrator's dispatch path serializes inference through per-region
`flock`s (`cpu_region_lock`), but standalone benchmarks (`bench_canonical.sh` /
llama-bench) historically took NO lock at all, and `run_benchmark.py` took its
own `fcntl.flock` in a *different* namespace. A canonical bench and an
orchestrator placement could therefore occupy the same physical cores with
nothing preventing it — the per-run operator-approval clause was the only
serializer between them (a human being used as a mutex).

This wrapper closes that gap without a second lock implementation: it acquires
the SAME locks the dispatch path uses, holds them for exactly as long as the
child process lives, and releases them when the child exits (the kernel
releases the `flock` even on SIGKILL, because release is fd-close).

Usage:
    region-lock run --cpu-list 0-95 -- llama-bench -m model.gguf ...
    region-lock run --regions q0,q1 --role bench-cpu -- ./bench_canonical.sh
    region-lock run --gpu-quiet exclusive --role bench-gpu -- ./gpu_bench.sh
    region-lock run --cpu-list 0-47 --gpu-quiet shared -- ./cpu_measure.sh
    region-lock run --cpu-list 160-183 -- ./gpu_slot.sh   # SMT siblings of 64-87 -> q2,q3
    region-lock status

gpu-quiet (2026-10-04, `src/runtime/gpu_quiet_lock.py`): a separate host-wide
flock beside the region locks. GPU benches take it EXCLUSIVE and NO region
claim (pinned GPU host threads degrade the CPU A/A floor ~9x, but a region
claim also 503s every serving role placed there); CPU measurements take it
SHARED alongside their regions. Orchestrator per-call serving claims never
look at it. Order: gpu-quiet first, then regions (with back-off, see module).

gpu-quiet is OPT-IN (2026-11-03, session review 3.2): `--gpu-quiet` defaults to
`none`. Only rows classed decision-grade / quiet-host (timing or A/B evidence
whose noise floor the GPU would move) ask for `shared` or `exclusive`, and they
must say so explicitly. Diagnostic / indicative work does not take it: the
2026-10-22 co-residency policy permits GPU+CPU co-residency for that work, and a
default hold produced "held but idle" — a shared holder that blocked every
exclusive acquirer for its whole window. When a gpu-quiet acquire has to wait,
the holder line is printed WITH a read-only hardware sample (GPU busy %, VRAM
used/total from amdgpu sysfs, KFD process count; `rocm-smi --showuse
--showmemuse` only when sysfs has no amdgpu card) so the operator sees whether
the GPU is actually busy, not only that a flock is held. Set
GPU_QUIET_HW_CHECK=0 to omit the sample.

`--cpu-list` folds SMT sibling CPUs onto their physical cores' regions by
default (`--fold-siblings`, REGION-SIBLING-1); `--no-fold-siblings` restores the
legacy mapping that ignores CPUs 96-191. The library default in
`instance_topology` is unchanged ("drop"); only this CLI opts in.

Waiting (2026-11-03): `--timeout-s` defaults to 600 s (an explicit `0` blocks forever); while a lock is
held by someone else the holder's pid, role, tag and age are printed to stderr (first block, then every
REGION_LOCK_WAIT_PRINT_EVERY_S seconds, default 5; 0 = on every poll).

Exit codes:
    0..255  the child's exit status (or 128+N when it died on signal N)
    75      EX_TEMPFAIL — could not acquire the regions within the budget
    64      EX_USAGE    — bad arguments / failed preflight

CRITICAL — the cross-role layer. `cpu_region_lock` takes two layers: a
role-AGNOSTIC `GLOBAL` mutex per region (true cross-role exclusion) and a
per-role lock (attribution). The GLOBAL layer is gated behind
ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT. Without it, this wrapper would take
only `cpu_region.bench.*` locks that no orchestrator path ever contends —
providing false confidence rather than exclusion. So we force the flag on for
ourselves AND preflight that the live dispatch process has it too, failing
closed when it does not (fabric axiom 3).
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Must be set BEFORE cpu_region_lock evaluates _cross_role_mutex_enabled(),
# which reads os.environ at call time. Setting it at import is the safest point.
os.environ.setdefault("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "1")

from src.runtime.cpu_region_lock import (  # noqa: E402
    CpuRegionLockTimeout,
    cpu_region_lock,
    global_region_lock_path,
    read_region_lock_payload,
    region_lock_path,
)
from src.runtime.gpu_quiet_lock import (  # noqa: E402
    GPU_QUIET_MODES,
    gpu_quiet_then_regions,
)
from src.runtime.gpu_quiet_lock import holders as gpu_quiet_holders  # noqa: E402
from src.runtime.instance_topology import ATOMIC_REGIONS, cpu_list_to_regions  # noqa: E402
from src.runtime.lock_queue import queue_dir as _fifo_queue_dir  # noqa: E402
from src.runtime.lock_queue import queue_status as _fifo_queue_status  # noqa: E402

EX_TEMPFAIL = 75
EX_USAGE = 64

#: `--gpu-quiet` default: take no gpu-quiet lock (opt-in only, 2026-11-03).
GPU_QUIET_NONE = "none"
#: GPU_QUIET_HW_CHECK=0 omits the hardware sample printed beside a gpu-quiet holder line.
GPU_HW_CHECK_ENV = "GPU_QUIET_HW_CHECK"
_FALSY = {"0", "false", "no", "off"}

#: Default per-acquire budget. A caller that wants the old "block forever" says
#: ``--timeout-s 0`` explicitly (2026-11-03 session review, section 3.2: a default
#: of forever turned one idle-held region into a 2-hour convoy).
DEFAULT_TIMEOUT_S = 600.0
#: Seconds between holder lines while waiting (0 = a line on every poll).
WAIT_PRINT_EVERY_ENV = "REGION_LOCK_WAIT_PRINT_EVERY_S"
_DEFAULT_WAIT_PRINT_EVERY_S = 5.0

_TRUTHY = {"1", "true", "yes", "on"}
#: Key of the orchestrator API in the stack state file `orchestrator_stack.py` writes.
_STACK_STATE_API_KEY = "orchestrator"
#: A recorded pid counts as the dispatch process only while its cmdline still names the API module.
_DISPATCH_CMDLINE_MARK = b"src.api"


def _lock_dir() -> Path:
    """Directory holding every region lock file (derived, not a private import)."""
    return region_lock_path("x", "y").parent


def _flock_held(path: Path) -> bool:
    """True if some process currently holds an exclusive flock on `path`.

    Probes with LOCK_EX|LOCK_NB and immediately releases on success, so this
    never disturbs a real holder and never blocks. Treats an unreadable file as
    held (fail-closed, fabric axiom 3).
    """
    import fcntl

    if not path.exists():
        return False
    try:
        with open(path, "a+b") as fh:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                return True
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            return False
    except OSError:
        return True


def _stack_state_file() -> Path:
    """`orchestrator_stack.py`'s state file (`scripts/server/stack_paths.STATE_FILE`), resolved from the same env."""
    log_dir = os.environ.get("ORCHESTRATOR_PATHS_LOG_DIR")
    if log_dir:
        return Path(log_dir) / "orchestrator_state.json"
    root = os.environ.get("ORCHESTRATOR_PATHS_PROJECT_ROOT") or str(Path(__file__).resolve().parents[2])
    return Path(root) / "logs" / "orchestrator_state.json"


def _dispatch_pids(state_file: Path | None = None) -> list[int]:
    """The orchestrator API pid recorded by the stack launcher, read from its state file (config).

    No process-name scan (CLAUDE.md bans `pgrep`/`pkill` name patterns on this shared host). The
    recorded pid is trusted only while `/proc/<pid>/cmdline` still names the API module, so a
    stale record whose pid was reused never stands in for the dispatcher. An API the stack did not
    launch is not seen here; such a process is outside the stack contract that sets the flag.
    """
    path = _stack_state_file() if state_file is None else state_file
    try:
        record = json.loads(path.read_text(encoding="utf-8")).get(_STACK_STATE_API_KEY) or {}
        pid = int(record["pid"])
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return []
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return []
    return [pid] if _DISPATCH_CMDLINE_MARK in cmdline else []


def _proc_has_cross_role_flag(pid: int) -> bool | None:
    """True/False if readable, None if the environ could not be read."""
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except (OSError, PermissionError):
        return None
    for entry in raw.split(b"\0"):
        if entry.startswith(b"ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT="):
            return entry.split(b"=", 1)[1].decode(errors="replace").strip().lower() in _TRUTHY
    return False


def _preflight(strict: bool) -> str | None:
    """Return an error string when the cross-role layer would be one-sided.

    A dispatch process without the flag takes only per-role locks, so it would
    never contend our GLOBAL locks — we would appear protected while sharing
    cores. Fail closed on that; a merely-unreadable environ is a warning.
    """
    pids = _dispatch_pids()
    if not pids:
        return None  # nothing dispatching — nothing to be one-sided against
    unflagged = [p for p in pids if _proc_has_cross_role_flag(p) is False]
    if unflagged:
        msg = (
            f"orchestrator dispatch pid(s) {unflagged} do NOT have "
            "ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT enabled — they take per-role "
            "locks only and will not contend this wrapper's GLOBAL locks. Exclusion "
            "would be one-sided (false confidence)."
        )
        return msg if strict else None
    unreadable = [p for p in pids if _proc_has_cross_role_flag(p) is None]
    if unreadable:
        print(
            f"[region-lock] WARNING: could not read environ of pid(s) {unreadable}; "
            "cross-role flag unverified.",
            file=sys.stderr,
        )
    return None


def _pid_age_s(pid: int, *, now: float | None = None) -> float | None:
    """Seconds since `pid` started (from /proc starttime + btime); None if unreadable."""
    from src.runtime.gpu_quiet_lock import _start_ticks

    ticks = _start_ticks(pid)
    if ticks is None:
        return None
    try:
        btime = next(
            int(line.split()[1])
            for line in Path("/proc/stat").read_text().splitlines()
            if line.startswith("btime ")
        )
        return max(0.0, (time.time() if now is None else now) - (btime + ticks / os.sysconf("SC_CLK_TCK")))
    except (OSError, ValueError, StopIteration):
        return None


def describe_holders(lock_path: Path, region: str, *, now: float | None = None) -> str:
    """One-line "who holds this lock": pid, role, tag, age. Read-only witness (/proc/locks + payloads)."""
    from src.runtime.cpu_region_lock import _current_lock_owner_pids
    from src.runtime.gpu_quiet_lock import holders as _gq_holders
    from src.runtime.gpu_quiet_lock import lock_owners

    meta: dict[int, dict] = {}
    modes: dict[int, str] = {}
    if region == "gpu-quiet":
        owners = lock_owners(lock_path)
        modes = dict(owners or {})
        pids = sorted(modes)
        for rec in _gq_holders().get("holders", []):  # type: ignore[union-attr]
            try:
                meta[int(rec["pid"])] = rec  # type: ignore[index]
            except (KeyError, TypeError, ValueError):
                continue
    else:
        pids = sorted(int(p) for p in _current_lock_owner_pids(lock_path))
        for sibling in sorted(_lock_dir().glob(f"cpu_region.*.{region}.lock")):
            payload = read_region_lock_payload(sibling)
            if payload and isinstance(payload.get("pid"), int):
                meta[payload["pid"]] = payload
    if not pids:
        return "holder unknown (no /proc/locks owner for this lock)"
    parts = []
    for pid in pids:
        rec = meta.get(pid, {})
        started = rec.get("started_at")
        age = (time.time() if now is None else now) - float(started) if isinstance(started, (int, float)) else _pid_age_s(pid, now=now)
        parts.append(
            f"pid {pid}"
            + (f" mode={modes[pid]}" if pid in modes else "")
            + f" role={rec.get('role', '?')} tag={rec.get('request_tag') or '-'}"
            + (f" age={age:.0f}s" if age is not None else " age=?")
        )
    return "; ".join(parts)


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return None


def _rocm_smi_sample() -> str:
    """Fallback when sysfs exposes no amdgpu card: `rocm-smi --showuse --showmemuse` (a read-only query)."""
    try:
        out = subprocess.run(
            ["rocm-smi", "--showuse", "--showmemuse", "--csv"],
            capture_output=True, text=True, timeout=10, check=False,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return "rocm-smi unavailable"
    rows = [line.strip() for line in out.splitlines() if line.strip() and not line.startswith("=")]
    return "rocm-smi " + " | ".join(rows) if rows else "rocm-smi returned nothing"


def gpu_hw_sample(*, drm_dir: Path | None = None, kfd_dir: Path | None = None, rocm_smi=_rocm_smi_sample) -> str:
    """One line of READ-ONLY GPU evidence: busy %, VRAM used/total per amdgpu card, KFD process count.

    Reads amdgpu sysfs (the source `rocm-smi --showuse --showmemuse` reports from) and
    `/sys/class/kfd/kfd/proc`; falls back to `rocm-smi` only when sysfs shows no amdgpu card. Opens no
    device and signals nothing. GPU_QUIET_HW_CHECK=0 disables it.
    """
    if os.environ.get(GPU_HW_CHECK_ENV, "1").strip().lower() in _FALSY:
        return "hw sample disabled (GPU_QUIET_HW_CHECK=0)"
    drm = drm_dir or Path(os.environ.get("ORCHESTRATOR_DRM_CLASS_DIR", "/sys/class/drm"))
    kfd = kfd_dir or Path(os.environ.get("ORCHESTRATOR_KFD_PROC_DIR", "/sys/class/kfd/kfd/proc"))
    parts: list[str] = []
    try:
        cards = sorted(c for c in drm.glob("card*") if c.name[4:].isdigit())
    except OSError:
        cards = []
    for card in cards:
        dev = card / "device"
        total = _read_int(dev / "mem_info_vram_total")
        if not total:
            continue  # not an amdgpu card with VRAM (connector, other vendor)
        used = _read_int(dev / "mem_info_vram_used")
        busy = _read_int(dev / "gpu_busy_percent")
        parts.append(
            f"{card.name} busy={'?' if busy is None else busy}% "
            f"vram={'?' if used is None else f'{used / 2**30:.1f}'}/{total / 2**30:.1f}GiB"
        )
    if not parts:
        parts.append(rocm_smi())
    try:
        parts.append(f"kfd_procs={sum(1 for e in kfd.iterdir() if e.name.isdigit())}")
    except OSError:
        parts.append("kfd_procs=?")
    return "hw: " + "; ".join(parts)


def make_wait_observer(
    *,
    print_every_s: float | None = None,
    clock=time.monotonic,
    out=None,
    describe=describe_holders,
    hw_sample=gpu_hw_sample,
):
    """Build the per-poll hook for `cpu_region_lock._WAIT_OBSERVER`.

    Prints the holder (pid, role/tag, age) to stderr the FIRST time a given lock blocks and then
    every `print_every_s` seconds (0 = every poll). The lock module calls it on every wait iteration.
    A gpu-quiet wait also carries `hw_sample()` — flock state alone does not say the GPU is busy.
    """
    if print_every_s is None:
        try:
            print_every_s = float(os.environ.get(WAIT_PRINT_EVERY_ENV, _DEFAULT_WAIT_PRINT_EVERY_S))
        except ValueError:
            print_every_s = _DEFAULT_WAIT_PRINT_EVERY_S
    last: dict[tuple[str, str], float] = {}

    def observe(region: str, role: str, lock_path: Path, elapsed_s: float, tag: str | None) -> None:
        key = (region, str(lock_path))
        now = clock()
        if key in last and now - last[key] < print_every_s:
            return
        last[key] = now
        line = (
            f"[region-lock] waiting {elapsed_s:.1f}s for {region} ({lock_path.name}) as role={role!r} "
            f"tag={tag!r}: held by {describe(lock_path, region)}"
        )
        if region == "gpu-quiet":
            line += f" | {hw_sample()}"
        print(line, file=out if out is not None else sys.stderr)

    return observe


def _resolve_regions(args: argparse.Namespace) -> frozenset[str]:
    if args.cpu_list:
        # REGION-SIBLING-1: with --fold-siblings (the CLI default) SMT siblings
        # claim their physical core's region, so `--cpu-list 160-183` takes the
        # same regions as 64-87. The LIBRARY default stays "drop" for every
        # other caller; only this path opts in. --no-fold-siblings restores the
        # legacy CLI meaning exactly.
        fold = getattr(args, "fold_siblings", True)
        mode = "fold" if fold else "drop"
        try:
            regions = cpu_list_to_regions(args.cpu_list, smt_siblings=mode)
        except ValueError as e:  # incl. instance_topology.CpuTopologyUnavailable
            raise SystemExit(
                f"[region-lock] --cpu-list {args.cpu_list!r}: cannot resolve the physical "
                f"cores it occupies ({e}); refusing rather than under-claiming "
                f"(--no-fold-siblings restores the legacy primary-only mapping)"
            ) from e
        if not regions:
            raise SystemExit(f"[region-lock] --cpu-list {args.cpu_list!r} maps to no regions")
        if fold:
            legacy = cpu_list_to_regions(args.cpu_list, smt_siblings="drop")
            if legacy != regions:
                print(
                    f"[region-lock] --cpu-list {args.cpu_list!r} includes SMT siblings: "
                    f"claiming {sorted(regions)} (their physical cores) instead of the "
                    f"primary-only {sorted(legacy)}; --no-fold-siblings for the legacy mapping",
                    file=sys.stderr,
                )
        return regions
    if not args.regions:
        return frozenset()  # --gpu-quiet alone (validated in _run)
    names = [r.strip() for r in args.regions.split(",") if r.strip()]
    unknown = sorted(set(names) - set(ATOMIC_REGIONS))
    if unknown:
        raise SystemExit(
            f"[region-lock] unknown region(s) {unknown}; valid: {list(ATOMIC_REGIONS)}"
        )
    return frozenset(names)


def _subquarter_cores(cpu_list: str, fold: bool) -> dict[str, set[int]]:
    """ws58 2026-11-02 sub-quarter packing: quarter -> physical cores of `cpu_list` for every quarter it covers only
    PARTLY (< 24 cores; SMT siblings 96-191 count as their core when folding). Such a quarter is not locked whole:
    the holder takes LOCK_SH on the quarter (so a whole-quarter holder still excludes it) plus LOCK_EX per core, so
    holders on disjoint cpu lists inside one quarter run side by side. REGION_LOCK_SUBQUARTER=0 restores whole quarters."""
    if os.environ.get("REGION_LOCK_SUBQUARTER", "1").strip() not in _TRUTHY:
        return {}
    by: dict[str, set[int]] = {}
    for tok in cpu_list.split(","):
        a, _, b = tok.strip().partition("-")
        if not a.isdigit():
            return {}
        for c in range(int(a), int(b or a) + 1):
            if c >= 96:
                if not fold or c >= 192:
                    continue
                c -= 96
            by.setdefault(f"q{c // 24}", set()).add(c)
    return {q: cs for q, cs in by.items() if len(cs) < 24 and q in ATOMIC_REGIONS}


def _acquire_subquarter(role: str, partial: dict[str, set[int]], timeout_s: float, tag: str) -> list:
    """Open + flock the sub-quarter locks (sorted order); the returned handles hold them until closed."""
    import fcntl

    from src.runtime.cpu_region_lock import _acquire_one_with_timeout

    fhs: list = []
    try:
        for q in sorted(partial):
            paths = [(global_region_lock_path(q), fcntl.LOCK_SH), (region_lock_path(role, q), fcntl.LOCK_SH)]
            paths += [(_lock_dir() / f"cpu_core.{c}.lock", fcntl.LOCK_EX) for c in sorted(partial[q])]
            for path, mode in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                fh = open(path, "a+b")
                fhs.append(fh)
                _acquire_one_with_timeout(fh, region=q, role=role, timeout_s=timeout_s, deadline_s=None,
                                          cancel_check=None, request_tag=tag, lock_type=mode)
    except BaseException:
        for fh in fhs:
            fh.close()
        raise
    return fhs


def _run(args: argparse.Namespace) -> int:
    if not args.command:
        raise SystemExit("[region-lock] no command given after `--`")
    if getattr(args, "gpu_quiet", None) == GPU_QUIET_NONE:
        args.gpu_quiet = None  # opt-in: 'none' (the default) takes no gpu-quiet lock
    receipt_prefix = getattr(args, "claim_receipt_prefix", None)
    grant_file = getattr(args, "claim_grant_file", None)
    if bool(receipt_prefix) != bool(grant_file):
        raise SystemExit("[region-lock] receipt prefix and grant file must be supplied together")
    if receipt_prefix:
        return _run_receipted(args)
    if os.environ.get("FILLER_SMOKE") == "1" or os.environ.get("FILLER_DRYRUN") == "1":
        # ws58 2026-11-02 (operator): a dry run is tiny and never deals with leases or locks; it runs at once,
        # pinned to its own few cpus (WS58_REGIONS) when given.
        cmd = list(args.command[1:] if args.command[:1] == ["--"] else args.command)
        cpus = os.environ.get("WS58_REGIONS")
        print(f"[region-lock] dry run: no lock taken (cpus={cpus or 'any'})", file=sys.stderr)
        return subprocess.call((["taskset", "-c", cpus] if cpus else []) + cmd)
    if not (args.regions or args.cpu_list or args.gpu_quiet):
        print(
            "[region-lock] run needs --regions, --cpu-list and/or --gpu-quiet",
            file=sys.stderr,
        )
        return EX_USAGE

    regions = _resolve_regions(args)
    partial = _subquarter_cores(args.cpu_list, getattr(args, "fold_siblings", True)) if args.cpu_list else {}
    regions = frozenset(r for r in regions if r not in partial)
    if regions:
        # The cross-role preflight is about the region GLOBAL layer; a gpu-quiet-only
        # hold takes no region lock and has nothing to be one-sided against.
        err = _preflight(strict=not args.no_preflight)
        if err:
            print(f"[region-lock] REFUSING: {err}", file=sys.stderr)
            print(
                "[region-lock] re-run with --no-preflight to override deliberately.",
                file=sys.stderr,
            )
            return EX_USAGE

    tag = args.tag or f"region-lock:{Path(args.command[0]).name}"
    waited_from = time.time()
    what = f"regions {sorted(regions)}"
    if args.gpu_quiet:
        what = f"gpu-quiet {args.gpu_quiet}" + (f" + {what}" if regions else "")

    print(
        f"[region-lock] acquiring {what} as role={args.role!r} (timeout_s={args.timeout_s}) …",
        file=sys.stderr,
    )
    sub_fhs: list = []
    from src.runtime import cpu_region_lock as _crl_module

    prev_observer = _crl_module._WAIT_OBSERVER
    _crl_module._WAIT_OBSERVER = make_wait_observer()
    try:
        if partial:
            sub_fhs = _acquire_subquarter(args.role, partial, args.timeout_s, tag)
            print(f"[region-lock] held sub-quarter cores {{{', '.join(f'{q}: {sorted(c)}' for q, c in sorted(partial.items()))}}}",
                  file=sys.stderr)
        if not regions and args.gpu_quiet is None:
            return _spawn(args.command)
        if args.gpu_quiet is None:
            # Byte-for-byte the pre-gpu-quiet path.
            with cpu_region_lock(
                args.role,
                regions,
                timeout_s=args.timeout_s,
                request_tag=tag,
            ) as held:
                waited = time.time() - waited_from
                print(
                    f"[region-lock] held {sorted(held)} after {waited:.1f}s wait; "
                    f"running: {' '.join(args.command)}",
                    file=sys.stderr,
                )
                return _spawn(args.command)
        with gpu_quiet_then_regions(
            args.role,
            regions,
            gpu_quiet=args.gpu_quiet,
            timeout_s=args.timeout_s,
            request_tag=tag,
        ) as grant:
            waited = time.time() - waited_from
            print(
                f"[region-lock] held gpu-quiet {args.gpu_quiet} + regions "
                f"{sorted(grant['regions'])} after {waited:.1f}s wait; "
                f"running: {' '.join(args.command)}",
                file=sys.stderr,
            )
            return _spawn(args.command)
    except CpuRegionLockTimeout as e:
        print(f"[region-lock] TIMEOUT acquiring {what}: {e}", file=sys.stderr)
        if args.gpu_quiet:
            # A gpu-quiet refusal cites hardware, not only flock state.
            from src.runtime.gpu_quiet_lock import gpu_quiet_lock_path

            print(
                f"[region-lock] gpu-quiet at timeout: held by "
                f"{describe_holders(gpu_quiet_lock_path(), 'gpu-quiet')} | {gpu_hw_sample()}",
                file=sys.stderr,
            )
        return EX_TEMPFAIL
    finally:
        _crl_module._WAIT_OBSERVER = prev_observer
        for fh in sub_fhs:
            fh.close()


def _run_receipted(args: argparse.Namespace) -> int:
    """Opt-in full-quarter CPU provider receipts around the actual flock lifetime."""
    from src.runtime import cpu_region_lock as lock_module
    from src.runtime.region_claim_receipt import _cpu_set, close_receipt, open_receipt

    if (os.environ.get("FILLER_SMOKE") == "1" or os.environ.get("FILLER_DRYRUN") == "1"
            or not args.cpu_list or args.gpu_quiet or args.no_preflight
            or os.environ.get("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "").strip().lower() not in _TRUTHY
            or _subquarter_cores(args.cpu_list, getattr(args, "fold_siblings", True))):
        raise SystemExit("[region-lock] receipts require a real full-quarter CPU claim and strict preflight")
    prefix = Path(args.claim_receipt_prefix)
    grant = Path(args.claim_grant_file)
    if not prefix.is_absolute() or not grant.is_absolute():
        raise SystemExit("[region-lock] receipt and grant paths must be absolute")
    if any(Path(str(prefix) + suffix).exists() for suffix in (".open.json", ".close.json", ".grant")):
        raise SystemExit("[region-lock] receipt path already exists")
    regions = _resolve_regions(args)
    expected_cpus = {cpu for name in regions for cpu in range(int(name[1:]) * 24, (int(name[1:]) + 1) * 24)}
    if _cpu_set(args.cpu_list) != expected_cpus:
        raise SystemExit("[region-lock] receipt claims require exact primary full-quarter CPU lists")
    err = _preflight(strict=True)
    if err:
        raise SystemExit(f"[region-lock] refusing receipt claim: {err}")
    try:
        with cpu_region_lock(args.role, regions, timeout_s=args.timeout_s,
                             request_tag=args.tag or "region-lock-receipt") as held:
            opened = open_receipt(prefix, grant, args.cpu_list, held, Path(__file__), Path(lock_module.__file__),
                                  lock_module._tmp_dir())
            print(f"[region-lock] held {sorted(held)}; provider open receipt {opened['path']}", file=sys.stderr)
            child_rc = _spawn(args.command)
        # Only after the context releases its locks may the provider write close.
        close_receipt(prefix, opened, child_rc)
        return child_rc
    except CpuRegionLockTimeout as exc:
        print(f"[region-lock] receipt claim timed out: {exc}", file=sys.stderr)
        return EX_TEMPFAIL


def _spawn(command: list[str]) -> int:
    """Run the child, forwarding termination signals so drain works.

    Signals are forwarded rather than swallowed: a quiesce/drain SIGTERM must
    reach the benchmark so it can stop at its own boundary (fabric axiom 4 —
    no forcible mid-flight preemption).
    """
    proc = subprocess.Popen(command)
    forwarded: list[int] = []

    def _forward(signum, _frame):
        forwarded.append(signum)
        try:
            proc.send_signal(signum)
        except ProcessLookupError:
            pass

    previous = {}
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        try:
            previous[sig] = signal.signal(sig, _forward)
        except (OSError, ValueError):
            pass
    try:
        rc = proc.wait()
    finally:
        for sig, handler in previous.items():
            try:
                signal.signal(sig, handler)
            except (OSError, ValueError):
                pass
    if rc < 0:  # died on signal N
        rc = 128 + (-rc)
    if forwarded:
        print(f"[region-lock] forwarded signal(s) {forwarded} to child", file=sys.stderr)
    return rc


def _status(args: argparse.Namespace) -> int:
    """Report, per region, whether the cross-role GLOBAL mutex is held and by whom.

    `active_region_holders()` deliberately excludes the GLOBAL pseudo-role and
    only knows roles present in the instance topology, so a bench holding a
    region would not appear there. We probe the GLOBAL lock directly and
    attribute via whatever per-role payloads are present.
    """
    rows = []
    for region in ATOMIC_REGIONS:
        held = _flock_held(global_region_lock_path(region))
        holders = []
        for lock_file in sorted(_lock_dir().glob(f"cpu_region.*.{region}.lock")):
            if lock_file.name.startswith("cpu_region.GLOBAL."):
                continue
            # Realized-first truth (fabric axiom 2): a payload is a stored
            # record, the flock is the fact. A holder killed with SIGKILL never
            # runs its cleanup, so a stale payload outlives the lock — trust it
            # only for a lock that is *currently* held.
            if not _flock_held(lock_file):
                continue
            payload = read_region_lock_payload(lock_file)
            if payload:
                holders.append(payload)
        rows.append({"region": region, "global_held": held, "holders": holders})

    quiet = gpu_quiet_holders()
    queue_rows = _fifo_queue_status(_fifo_queue_dir(_lock_dir()))
    if args.json:
        # The bare list stays the default shape: consumers validate it as exactly
        # q0..q3 (e.g. the research reanchor runner). gpu-quiet is opt-in.
        if args.gpu_quiet:
            print(json.dumps(
                {"regions": rows, "gpu_quiet": quiet, "queue": queue_rows},
                indent=2, default=str,
            ))
        else:
            print(json.dumps(rows, indent=2, default=str))
        return 0
    for row in rows:
        state = "HELD" if row["global_held"] else "free"
        who = ", ".join(
            f"{h.get('role', '?')}[{h.get('instance_idx', '-')}] {h.get('request_tag', '')}".strip()
            for h in row["holders"]
        )
        print(f"{row['region']:>4}  {state:<5}  {who}")
    if quiet["held"]:
        state = "EXCL" if quiet["mode"] == "exclusive" else "SHRD" if quiet["mode"] else "HELD"
    else:
        state = "free"
    who = ", ".join(
        f"{h.get('role', '?')}[pid {h.get('pid', '-')}] {h.get('request_tag') or ''}".strip()
        for h in quiet["holders"]
    )
    print(f"gpu-quiet  {state:<5}  {who}")
    if queue_rows:
        print("queue (FIFO, EPYC_LOCK_FIFO=1 clients only):")
        for row in queue_rows:
            print(
                f"  #{row['position']:<3} age={row['age_s']:>6.1f}s "
                f"pid={row['pid']:<8} mode={row['mode']:<9} "
                f"regions={','.join(row['regions']) or '-':<12} tag={row['tag']}"
            )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="region-lock",
        description="Hold orchestrator CPU-region locks for the lifetime of a child command.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="acquire regions, run a command, release on exit")
    target = run.add_mutually_exclusive_group()
    target.add_argument("--regions", help="comma-separated region ids, e.g. q0,q1,q2,q3")
    target.add_argument(
        "--cpu-list",
        help="taskset-style cpu list, e.g. 0-95 (regions derived; SMT siblings such as "
        "160-183 claim the regions of their physical cores, here 64-87; see --fold-siblings)",
    )
    run.add_argument(
        "--fold-siblings",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="with --cpu-list, map SMT sibling CPUs (96-191 on this host) onto their "
        "physical cores' regions, read from the kernel's thread-sibling topology "
        "(default: on). --no-fold-siblings restores the legacy mapping, which ignores "
        "sibling CPUs entirely. No effect with --regions.",
    )
    run.add_argument(
        "--gpu-quiet",
        choices=(GPU_QUIET_NONE, *GPU_QUIET_MODES),
        default=GPU_QUIET_NONE,
        help="host-wide gpu-quiet lock, OPT-IN (default: none). Only for rows classed "
        "decision-grade / quiet-host: 'exclusive' for a GPU timing bench (valid with no "
        "regions — GPU benches should take NO region claim), 'shared' for a CPU timing "
        "measurement (waits for any exclusive holder). Diagnostic / indicative work leaves "
        "it at 'none' (2026-10-22 co-residency policy permits GPU+CPU co-residency). Taken "
        "BEFORE the regions; a wait prints the holder plus a read-only GPU hardware sample.",
    )
    run.add_argument(
        "--role",
        default="bench",
        help="attribution label for the per-role lock (default: bench). Not a real stack role.",
    )
    run.add_argument(
        "--timeout-s",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        help="per-region acquire timeout in seconds (default 600). An explicit 0 blocks "
        "indefinitely. While waiting, the holder's pid/role/tag/age is printed to stderr. "
        "With --gpu-quiet it bounds the whole gpu-quiet+regions acquisition. Exit 75 on expiry.",
    )
    run.add_argument("--tag", help="opaque tag recorded in the lock payload for diagnostics")
    run.add_argument("--claim-receipt-prefix", help="absolute prefix for opt-in provider open/close receipts")
    run.add_argument("--claim-grant-file", help="absolute rowflow grant whose CPU scope and window must match")
    run.add_argument(
        "--no-preflight",
        action="store_true",
        help="skip the cross-role-flag preflight (deliberate override; exclusion may be one-sided)",
    )
    run.add_argument("command", nargs=argparse.REMAINDER, help="-- COMMAND [ARGS...]")
    run.set_defaults(func=_run)

    st = sub.add_parser("status", help="show which regions are currently held")
    st.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    st.add_argument(
        "--gpu-quiet",
        action="store_true",
        help="with --json: emit {regions: [...], gpu_quiet: {...}} instead of the bare "
        "region list (the table always shows the gpu-quiet row)",
    )
    st.set_defaults(func=_status)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "command", None) and args.command and args.command[0] == "--":
        args.command = args.command[1:]
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
