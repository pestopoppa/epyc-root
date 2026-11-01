#!/usr/bin/env python3
"""NI R6 model-free execution on a live-admitted physical pair; own children only."""
from __future__ import annotations

import datetime as dt
import fcntl
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
FLAGS = pathlib.Path('/mnt/raid0/llm/tmp/compute-flags')
LOCK = FLAGS / 'prep-locks/32-33.lock'
MAX_RSS = 8 * 1024**3
MAX_S = 900


def active_grants():
    classes = {}
    for line in (FLAGS / 'FILLERS.md').read_text().splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) == 18:
            classes[cells[0]] = cells[8]
    now = time.time()
    rows = []
    for path in sorted((FLAGS / 'grants').glob('*.grant')):
        fields = dict(part.split('=', 1) for part in path.read_text().split())
        stamp = lambda value: dt.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
        if not stamp(fields['start']) <= now < stamp(fields['end']):
            continue
        cpus = set()
        for part in fields['regions'].split(','):
            if part.startswith('mi210'):
                continue
            left, dash, right = part.partition('-')
            cpus.update(range(int(left), int(right if dash else left) + 1))
        kind = classes.get(path.stem)
        if not kind:
            raise RuntimeError(f'unknown live grant class: {path.stem}')
        rows.append({'id': path.stem, 'class': kind, 'cpus': sorted(cpus), 'regions': fields['regions']})
    return rows


def choose_pair(rows):
    # Same physical pair, relocated by +24 through q1/q2/q3/q0.
    for pair in ((32, 33), (56, 57), (80, 81), (8, 9)):
        physical = {cpu % 96 for cpu in pair}
        names = {cpu for row in rows for cpu in row['cpus']}
        if any('timing' in row['class'] and physical & {cpu % 96 for cpu in row['cpus']} for row in rows):
            continue
        if not names.intersection(pair):
            return pair
    # Only correctness grants remain: R6 may use this pair's SMT siblings.
    if any('timing' in row['class'] for row in rows):
        raise RuntimeError('no admissible prep pair beside timing grants')
    for pair in ((128, 129), (152, 153), (176, 177), (104, 105)):
        names = {cpu for row in rows for cpu in row['cpus']}
        if not names.intersection(pair):
            return pair
    raise RuntimeError('no admissible R6 CPU pair')


def rss_tree(pid):
    # Child is in its own process group; capture only our exact descendants.
    stack = [pid]
    seen = set()
    total = 0
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        proc = pathlib.Path('/proc') / str(current)
        try:
            total += int((proc / 'statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
            children = (proc / 'task' / str(current) / 'children').read_text().split()
            stack.extend(int(x) for x in children)
        except (FileNotFoundError, ProcessLookupError, ValueError):
            pass
    return total, sorted(seen)


def kill_owned(proc):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=3)
    if pathlib.Path('/proc') .joinpath(str(proc.pid)).exists():
        raise RuntimeError(f'captured child PID still live: {proc.pid}')


def main():
    if len(sys.argv) < 3 or sys.argv[1] != '--':
        raise SystemExit('usage: run_bounded_r6.py -- COMMAND [ARGS...]')
    lock = LOCK.open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('NI 32-33 R6 prep mutex held')
    rows = active_grants()
    pair = choose_pair(rows)
    os.sched_setaffinity(0, set(pair))
    lock.seek(0)
    lock.truncate()
    lock.write(f'owner=codex-ni task=DF2-12.1 family=32-33 cpus={pair} pid={os.getpid()}\n')
    lock.flush()
    env = dict(os.environ)
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
    started = time.monotonic()
    log = (ROOT / 'R6-MODEL-FREE.log').open('a')
    proc = subprocess.Popen(sys.argv[2:], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                            start_new_session=True)
    birth = (pathlib.Path('/proc') / str(proc.pid) / 'stat').read_text().split()[21]
    peak = 0
    failure = None
    sampled_pids = set()
    try:
        while proc.poll() is None:
            rows = active_grants()
            if pair != choose_pair(rows):
                raise RuntimeError('R6 pair admission changed during execution')
            rss, pids = rss_tree(proc.pid)
            sampled_pids.update(pids)
            peak = max(peak, rss)
            if peak > MAX_RSS:
                raise RuntimeError('sampled process-tree RSS >8GiB')
            if time.monotonic() - started > MAX_S:
                raise RuntimeError('R6 900s cap')
            time.sleep(0.1)
        if proc.returncode:
            raise RuntimeError(f'child rc={proc.returncode}')
    except BaseException as exc:
        failure = repr(exc)
    finally:
        kill_owned(proc)
        log.close()
        lock.seek(0)
        lock.truncate()
        lock.close()
    receipt = {'scope': 'MODEL_FREE_R6', 'command': sys.argv[2:], 'actual_cpus': pair,
               'live_grants_last': rows, 'child_pid': proc.pid, 'child_birth': birth,
               'sampled_pids': sorted(sampled_pids), 'sampled_peak_tree_rss_bytes': peak,
               'elapsed_s': time.monotonic() - started, 'returncode': proc.returncode,
               'failure': failure, 'child_drained': not pathlib.Path('/proc').joinpath(str(proc.pid)).exists(),
               'utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    with (ROOT / 'R6-LAST-RECEIPT.json').open('w') as out:
        json.dump(receipt, out, indent=2)
        out.write('\n')
    print(json.dumps(receipt, sort_keys=True))
    return 1 if failure else 0


if __name__ == '__main__':
    raise SystemExit(main())
