"""Validate inherited current-rowflow smoke bounds; never create authority."""
import os
from pathlib import Path
import re
import time


def context(base):
    if os.environ.get('FILLER_SMOKE') != '1' or os.environ.get('FILLER_DRYRUN') != '1':
        raise ValueError('publisher smoke context absent')
    text = os.environ.get('FILLER_CPUS', '')
    cpus = set()
    for part in text.split(','):
        match = re.fullmatch(r'(\d+)(?:-(\d+))?', part)
        if not match:
            raise ValueError('publisher smoke CPU schema')
        lo, hi = int(match[1]), int(match[2] or match[1])
        if not 0 <= lo <= hi < 192 or cpus.intersection(range(lo, hi + 1)):
            raise ValueError('publisher smoke CPU range')
        cpus.update(range(lo, hi + 1))
    if len(cpus) != 4 or os.sched_getaffinity(0) != cpus:
        raise ValueError('publisher smoke requires exactly four assigned CPUs')
    if os.environ.get('FILLER_THREADS') != '4' or os.environ.get('FILLER_NEEDGPU') != '1':
        raise ValueError('publisher smoke thread/GPU identity')
    stop = Path(os.environ.get('FILLER_STOPFILE', ''))
    if stop != Path(base) / 'STOP':
        raise ValueError('publisher smoke STOP identity')
    for name in ('STOP', 'STOP-smoke'):
        path = Path(base) / name
        if path.exists() or path.is_symlink():
            raise ValueError('publisher smoke STOP')
    try:
        end = int(os.environ['FILLER_END'])
        deadline = int(os.environ['FILLER_DEADLINE'])
    except (ValueError, KeyError) as exc:
        raise ValueError('publisher smoke deadline schema') from exc
    if not time.time() < deadline == end - 90:
        raise ValueError('publisher smoke deadline')
    return cpus, deadline
