#!/usr/bin/env python3
"""Project native E1 call windows onto own-PID KFD and hipMalloc live bytes."""
import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def epoch(iso):
    return dt.datetime.fromisoformat(iso.replace('Z', '+00:00')).timestamp()


def shim_points(path):
    live = {}
    totals = defaultdict(int)
    points = []
    for line in path.open(errors='replace'):
        parts = line.split()
        if len(parts) < 7 or parts[0] not in ('A', 'F'):
            continue
        try:
            t, size, ptr, rc = float(parts[1]), int(parts[4]), parts[5], int(parts[6])
        except (ValueError, IndexError):
            continue
        if rc:
            continue
        if parts[0] == 'A':
            stack = line.split('|', 1)[-1]
            cat = ('ggml_cuda_pool_leg' if 'ggml_cuda_pool_leg' in stack or '_ZN18ggml_cuda_pool_leg' in stack else
                   'rocblas' if 'rocblas' in stack.lower() else
                   'hipblaslt' if 'hipblaslt' in stack.lower() else
                   'ggml-hip' if 'libggml-hip' in stack else 'other')
            live[ptr] = (size, cat)
            totals[cat] += size
        elif ptr in live:
            old, cat = live.pop(ptr)
            totals[cat] -= old
        points.append((t, dict(totals)))
    return points


def near(points, t):
    out = None
    for x in points:
        if x[0] > t:
            break
        out = x[1]
    return out


def main(d):
    reports = list((d / 'native').glob('*/*/calls.jsonl'))
    assert len(reports) == 1, f'expected one native calls record: {reports}'
    calls = [json.loads(x) for x in reports[0].read_text().splitlines() if x.strip()]
    samples = [json.loads(x) for x in (d / 'kfd.jsonl').read_text().splitlines() if x.strip()]
    assert samples and any(x['pid_vram_gib'] is not None for x in samples)
    kp = [(x['t'], x['pid_vram_gib']) for x in samples if x['pid_vram_gib'] is not None]
    sp = shim_points(d / 'hipmalloc.jsonl')
    assert sp, 'shim captured no public HIP allocation events'
    stages = defaultdict(list)
    for x in calls:
        if x.get('stage'):
            stages[x['stage']].append(x)
    out = {'schema': 'yarn-e1-mem-phase/v1', 'scope': 'diagnostic single-server historical A1 chain',
           'native_calls': str(reports[0]), 'kfd': str(d / 'kfd.jsonl'),
           'shim': str(d / 'hipmalloc.jsonl'), 'stages': {}}
    for name, rows in stages.items():
        begin = min(epoch(x['at']) - float((x.get('timings') or {}).get('wall_s') or 0) for x in rows)
        end = max(epoch(x['at']) for x in rows)
        window = [v for t, v in kp if begin <= t <= end]
        sb = near(sp, begin) or {}
        se = near(sp, end) or {}
        out['stages'][name] = {
            'start': begin, 'end': end, 'requests': len(rows),
            'own_kfd_start_gib': near(kp, begin), 'own_kfd_peak_gib': max(window) if window else None,
            'own_kfd_end_gib': near(kp, end),
            'shim_live_start_bytes': sb, 'shim_live_end_bytes': se,
            'shim_live_delta_bytes': {k: se.get(k, 0)-sb.get(k, 0) for k in set(sb)|set(se)}}
    p = d / 'phase-attribution.json'
    p.write_text(json.dumps(out, indent=2) + '\n')
    print(p)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
