#!/usr/bin/env python3
"""Does every LIVE instance actually run on the cores its declared shape names?

A matching topology hash proves the declaration did not change. It proves nothing about
where threads ran: the cpuset reaches a process through taskset/numactl in the launcher,
and a launcher that dropped the pin, a shape edit applied without a restart, or a
hand-started server all look identical in the declaration.

So this reads the truth from the kernel, and it reads the RIGHT thing: llama.cpp pins
each worker thread to a single core, so /proc/<pid>/status alone reports "0" for a
correctly placed 96-core instance. The check folds Cpus_allowed_list over
/proc/<pid>/task/*/ and takes the modal mask -- the one the decode pool carries -- for
the server whose argv carries --port <p>, and compares it to the cpuset of the shape
that instance declares. Threads pinned outside the declared set fail; threads allowed on
every host cpu (the HIP runtime spawns exactly one per GPU server) are counted and named
rather than folded into a union that would then read 0-191.

Read-only and PID-safe: it matches on the exact `--port <n>` token of a captured argv,
never on a name pattern, and it never signals anything. Non-zero if any live instance
disagrees with its declaration, or if a declared instance has no process at all.

    affinity_check.py                 # every declared instance
    affinity_check.py --role frontdoor
    affinity_check.py --allow-missing # absent instances are reported, not failed
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ORCH = Path("/mnt/raid0/llm/epyc-orchestrator")


def parse_cpus(spec: str) -> set[int]:
    out: set[int] = set()
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return out


def fmt(cpus: set[int]) -> str:
    if not cpus:
        return "<empty>"
    out, cur = [], sorted(cpus)
    start = prev = cur[0]
    for c in cur[1:]:
        if c == prev + 1:
            prev = c
            continue
        out.append(f"{start}-{prev}" if start != prev else f"{start}")
        start = prev = c
    out.append(f"{start}-{prev}" if start != prev else f"{start}")
    return ",".join(out)


def counts_by_mask(pid: int) -> dict[str, int]:
    """How many of this process's threads carry each Cpus_allowed_list mask."""
    out: dict[str, int] = {}
    for task in Path(f"/proc/{pid}/task").glob("*/status"):
        try:
            for line in task.read_text().splitlines():
                if line.startswith("Cpus_allowed_list:"):
                    mask = line.split(":", 1)[1].strip()
                    out[mask] = out.get(mask, 0) + 1
                    break
        except OSError:
            continue
    return out


def servers_by_port() -> dict[int, int]:
    """port -> pid, from argv only. Exact token match, no name pattern."""
    out: dict[int, int] = {}
    ps = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True, check=True)
    for line in ps.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        pid_s, _, args = line.partition(" ")
        argv = args.split()
        if not argv or not argv[0].endswith("llama-server"):
            continue
        if "--port" not in argv:
            continue
        try:
            out[int(argv[argv.index("--port") + 1])] = int(pid_s)
        except (ValueError, IndexError):
            continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orchestrator", type=Path, default=ORCH)
    ap.add_argument("--role")
    ap.add_argument("--allow-missing", action="store_true")
    args = ap.parse_args()

    sys.path.insert(0, str(args.orchestrator))
    sys.path.insert(0, str(args.orchestrator / "scripts" / "server"))
    import stack_numa as sn

    host_cpus = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else 0
    host_cpus = max(host_cpus, os.cpu_count() or 0)
    live = servers_by_port()
    problems: list[str] = []
    missing: list[str] = []
    checked = 0

    for role, cfg in sorted(sn.NUMA_CONFIG.items()):
        if args.role and role != args.role:
            continue
        for idx, (cpus, port, threads) in enumerate(cfg.get("instances") or []):
            declared = parse_cpus(cpus)
            pid = live.get(int(port))
            label = f"{role}[{idx}] :{port}"
            if pid is None:
                missing.append(f"{label} declared on {cpus!r} but NO llama-server holds that port")
                continue
            try:
                status = Path(f"/proc/{pid}/status").read_text()
            except OSError as exc:
                problems.append(f"{label} pid {pid}: cannot read /proc status ({exc})")
                continue
            nthreads = None
            for line in status.splitlines():
                if line.startswith("Threads:"):
                    nthreads = int(line.split(":", 1)[1].strip())

            # THE MAIN THREAD'S MASK IS NOT THE INSTANCE'S SHAPE. llama.cpp pins each
            # worker thread to one core of the cpuset, so /proc/<pid>/status reads back a
            # single cpu ("0", "72,168") for a correctly placed 96-core instance. Fold
            # over /proc/<pid>/task/*/ instead and take the MODE: that is the mask the
            # decode pool carries.
            masks = counts_by_mask(pid)
            if not masks:
                problems.append(f"{label} pid {pid}: no readable threads (exited mid-check?)")
                continue
            modal, modal_n = max(masks.items(), key=lambda kv: kv[1])
            actual = parse_cpus(modal)
            checked += 1
            # A thread allowed on EVERY host cpu was spawned outside the pin (the HIP
            # runtime does exactly one of these per GPU server). Counted and reported,
            # never folded into the union -- a union would read "0-191" off one helper.
            unconfined = sum(n for m, n in masks.items() if len(parse_cpus(m)) >= host_cpus)
            stray = {
                m: n for m, n in masks.items()
                if not parse_cpus(m) <= declared and len(parse_cpus(m)) < host_cpus
            }
            if actual != declared:
                extra, short = actual - declared, declared - actual
                problems.append(
                    f"{label} pid {pid} modal thread affinity {modal!r} ({modal_n} threads) "
                    f"!= declared {cpus!r}"
                    + (f"; on {fmt(extra)} it must not touch" if extra else "")
                    + (f"; missing {fmt(short)}" if short else "")
                )
                continue
            if stray:
                problems.append(
                    f"{label} pid {pid} has thread(s) pinned OUTSIDE the declared cpuset: "
                    + ", ".join(f"{m} x{n}" for m, n in sorted(stray.items()))
                )
                continue
            note = f"  ({modal_n}/{nthreads} threads; declared -t {threads}"
            note += f"; {unconfined} unconfined helper" + ("s" if unconfined != 1 else "")
            note += ")"
            print(f"  OK {label} pid {pid} on {modal}{note}")

    for m in missing:
        print(("  MISSING " if args.allow_missing else "  FAIL ") + m)
    for p in problems:
        print("  FAIL " + p)

    rc = 1 if problems or (missing and not args.allow_missing) else 0
    print(f"{checked} live instance(s) checked, {len(problems)} mismatched, "
          f"{len(missing)} declared-but-absent")
    print("AFFINITY VERIFIED" if rc == 0 else "AFFINITY CHECK FAILED")
    return rc


if __name__ == "__main__":
    sys.exit(main())
