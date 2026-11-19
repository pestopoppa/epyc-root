"""Bounded sampled execution placement for one owned process; never a continuity proof."""
from __future__ import annotations
import os
from pathlib import Path
import re
import time

MAX_SAMPLES = 4096
MAX_THREADS = 4096


def _cpulist(value: str) -> set[int]:
    out: set[int] = set()
    for part in value.strip().split(','):
        if not part:
            raise ValueError('empty cpu list component')
        if '-' in part:
            bits = part.split('-')
            if len(bits) != 2 or not all(x.isdigit() for x in bits):
                raise ValueError('malformed cpu range')
            lo, hi = map(int, bits)
            if hi < lo or hi - lo > 4096:
                raise ValueError('invalid cpu range')
            out.update(range(lo, hi + 1))
        elif part.isdigit():
            out.add(int(part))
        else:
            raise ValueError('malformed cpu id')
    if not out:
        raise ValueError('empty cpu set')
    return out


def topology(sysfs=Path('/sys/devices/system')) -> dict[int, int]:
    root = Path(sysfs)
    online = _cpulist((root / 'cpu/online').read_text())
    nodes = root / 'node'
    found: dict[int, int] = {}
    for p in sorted(nodes.glob('node[0-9]*')):
        if not re.fullmatch(r'node[0-9]+', p.name):
            continue
        nid = int(p.name[4:])
        for cpu in _cpulist((p / 'cpulist').read_text()):
            if cpu in found:
                raise ValueError('CPU mapped to multiple NUMA nodes')
            found[cpu] = nid
    if not found or set(found) != online:
        raise ValueError('NUMA topology does not cover online CPUs exactly')
    return found


def _processor(stat: str) -> int:
    # comm is parenthesized and may contain spaces or ')'; fields after its final ') '
    # begin at proc stat field 3. Processor is field 39, offset 36.
    close = stat.rfind(') ')
    if close < 0:
        raise ValueError('malformed proc stat')
    fields = stat[close + 2:].split()
    if len(fields) <= 36 or not fields[36].isdigit():
        raise ValueError('missing processor field')
    return int(fields[36])


def sample_process(pid: int, *, proc=Path('/proc'), sysfs=Path('/sys/devices/system')) -> dict:
    if type(pid) is not int or pid <= 0:
        raise ValueError('invalid pid')
    root = Path(proc) / str(pid)
    before = (root / 'stat').read_text()
    pclose = before.rfind(') ')
    if pclose < 0:
        raise ValueError('malformed process stat')
    start_ticks = before[pclose + 2:].split()[19]
    topo = topology(sysfs)
    taskdir = root / 'task'
    tids = sorted(int(p.name) for p in taskdir.iterdir() if p.name.isdigit())
    if not tids or len(tids) > MAX_THREADS:
        raise ValueError('empty or oversized task set')
    tasks = {}
    for tid in tids:
        stat_path = taskdir / str(tid) / 'stat'
        cpu = _processor(stat_path.read_text())
        if cpu not in topo:
            raise ValueError('observed CPU absent from validated topology')
        tasks[str(tid)] = {'cpu': cpu, 'node': topo[cpu]}
    after = (root / 'stat').read_text()
    aclose = after.rfind(') ')
    if aclose < 0 or after[aclose + 2:].split()[19] != start_ticks:
        raise ValueError('process identity changed during task census')
    now = time.monotonic_ns()
    return {'monotonic_ns': now, 'pid': pid, 'start_ticks': int(start_ticks),
            'topology': {str(c): n for c, n in sorted(topo.items())}, 'tasks': tasks}


class WindowSampler:
    def __init__(self, pid: int, *, sample=sample_process, interval_s=0.05):
        if not 0.005 <= interval_s <= 1:
            raise ValueError('sampling interval outside bounded range')
        self.pid, self.sample, self.interval_s = pid, sample, interval_s
        self.rows: list[dict] = []

    def collect(self, start_ns: int, end_ns: int) -> list[dict]:
        if end_ns <= start_ns or len(self.rows) > MAX_SAMPLES:
            raise ValueError('invalid or oversized placement window')
        rows = [r for r in self.rows if start_ns <= r['monotonic_ns'] <= end_ns]
        if len(rows) < 2:
            raise ValueError('insufficient placement samples in request window')
        topo = rows[0]['topology']
        for row in rows:
            if row['pid'] != self.pid or row['topology'] != topo or not row['tasks']:
                raise ValueError('placement identity/topology/task evidence changed')
            if any(type(v['cpu']) is not int or str(v['cpu']) not in topo or
                   v['node'] != topo[str(v['cpu'])] for v in row['tasks'].values()):
                raise ValueError('placement sample does not bind to topology')
        return rows
