#!/usr/bin/env python3
"""Offline prototype for validating an owned Linux process's CPU affinity.

This observes, it does not enforce, an allocation.  A caller must supply the
start ticks captured at child launch and repeat checks while the child runs.
The thread snapshot race and descendant coverage remain unresolved.
"""
import os
from pathlib import Path


class AffinityError(RuntimeError):
    pass


def _start_ticks(path):
    raw = path.read_text()
    close = raw.rfind(')')
    if close < 0:
        raise AffinityError('malformed proc stat')
    fields = raw[close + 2:].split()
    if len(fields) <= 19:
        raise AffinityError('short proc stat')
    return int(fields[19])


def verify_threads(pid, start_ticks, granted_cpus, *, proc_root=Path('/proc'), get_affinity=os.sched_getaffinity):
    if type(pid) is not int or pid <= 0 or type(start_ticks) is not int or start_ticks <= 0:
        raise AffinityError('invalid owned process identity')
    if not granted_cpus or any(type(cpu) is not int or cpu < 0 for cpu in granted_cpus):
        raise AffinityError('invalid granted CPU set')
    root = Path(proc_root) / str(pid)
    try:
        if _start_ticks(root / 'stat') != start_ticks:
            raise AffinityError('process identity changed')
        tids = {int(p.name) for p in (root / 'task').iterdir() if p.name.isdecimal()}
        if pid not in tids:
            raise AffinityError('leader thread missing')
        masks = {}
        for tid in sorted(tids):
            mask = set(get_affinity(tid))
            if not mask or not mask.issubset(granted_cpus):
                raise AffinityError('thread exceeds granted CPU set')
            masks[tid] = sorted(mask)
        again = {int(p.name) for p in (root / 'task').iterdir() if p.name.isdecimal()}
        if again != tids or _start_ticks(root / 'stat') != start_ticks:
            raise AffinityError('process or thread set changed during check')
        return masks
    except (OSError, ValueError, IndexError) as exc:
        raise AffinityError('cannot verify process affinity') from exc
