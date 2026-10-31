"""R11 smoke admission draft. Fail closed; never used by production grants."""
import datetime
import os
import re
import shutil
import time
from pathlib import Path

FLAGS = Path('/mnt/raid0/llm/tmp/compute-flags')

def check_class(row):
    cells=[cell.strip() for cell in row.strip().strip('|').split('|')]
    if len(cells)!=18:raise RuntimeError('malformed grant row')
    cls=cells[8]
    if cls not in ('block-correctness','diagnostic','block-timing-pairable','block-timing'):
        raise RuntimeError('unknown grant class: '+cls)
    return cls

def check(cpus):
    cpus = set(cpus)
    if len(cpus) != 2 or any(c < 96 or c > 183 for c in cpus):
        raise RuntimeError('R11 requires two allowed SMT sibling CPUs')
    quarters = {(c - 96) // 24 for c in cpus}
    if len(quarters) != 1 or os.sched_getaffinity(0) != cpus:
        raise RuntimeError('R11 smoke affinity/quarter mismatch')
    outside = Path('/mnt/raid0/llm/tmp/HOLD_GPU_FOR_QUIET_20261024')
    if list(FLAGS.glob('HOLD_*')) or outside.exists() or outside.is_symlink():
        raise RuntimeError('global HOLD')
    if shutil.disk_usage(FLAGS).free < 150*1024**3+128*1024**2:
        raise RuntimeError('RAID below 150 GiB floor plus 128 MiB metadata reserve')
    if shutil.disk_usage('/mnt/micron').free < 151*1024**3:
        raise RuntimeError('Micron below 150 GiB floor plus 1 GiB native reserve')
    q = next(iter(quarters))
    now = time.time()
    for path in sorted((FLAGS / 'grants').glob('*.grant')):
        fields = {}
        for token in path.read_text().split():
            k, sep, value = token.partition('=')
            if not sep or k in fields:
                raise RuntimeError('malformed grant')
            fields[k] = value
        if set(fields) != {'regions', 'start', 'end'}:
            raise RuntimeError('unknown grant schema')
        def parse(value):
            parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                raise RuntimeError('grant time lacks timezone')
            return parsed.timestamp()
        start, end = parse(fields['start']), parse(fields['end'])
        if start >= end:
            raise RuntimeError('invalid grant interval')
        if end <= now or start >= now + 300:
            continue
        rows = [line for line in (FLAGS / 'FILLERS.md').read_text().splitlines() if line.startswith('| ' + path.stem + ' |')]
        if len(rows) != 1:
            raise RuntimeError('grant lacks unique FILLERS row')
        cls=check_class(rows[0])
        for region in fields['regions'].split(','):
            if region == 'mi210_0':
                continue
            if region in ('q0', 'q1', 'q2', 'q3'):
                covered = {int(region[1])}
            else:
                match = re.fullmatch(r'(\d+)(?:-(\d+))?', region)
                if not match:
                    raise RuntimeError('unknown grant region')
                first, last = int(match[1]), int(match[2] or match[1])
                if first > last or last >= 192:
                    raise RuntimeError('invalid grant CPU range')
                covered = {(cpu % 96) // 24 for cpu in range(first, last + 1)}
            if q in covered and cls in ('block-timing-pairable','block-timing'):
                raise RuntimeError('timing grant overlaps smoke quarter')
            if cls in ('block-correctness','diagnostic') and any(cpu in cpus for cpu in range(first,last+1)) if region not in ('q0','q1','q2','q3') else False:
                raise RuntimeError('grant names smoke CPUs')
    return {'kind': 'r11-unlocked-smoke', 'quarter': q, 'cpus': sorted(cpus), 'checked_epoch': now}
