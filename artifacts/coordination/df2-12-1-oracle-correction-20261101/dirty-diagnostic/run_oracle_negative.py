#!/usr/bin/env python3
"""R11 bounded test-only preclear probe; not a production rollback repair."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from r11_cpu_dirty_smoke import admitted, LOCK, MODEL, MODEL_SHA, RSS_LIMIT
from owner_pregrant import ROOT, drain_group, members, sha
import fcntl


def main():
    out = Path(__file__).resolve().parent
    binary = out / 'test-oracle-negative'
    source = out / 'test-oracle-negative.cpp'
    source_original = Path('/mnt/raid0/llm/llama.cpp/tests/test-recurrent-state-rollback.cpp')
    if sha(MODEL) != MODEL_SHA or sha(source_original) != 'b200438e63d75b051782b4f2face659d1fb62c4b7da45d2266e2096abe22d3e3':
        raise RuntimeError('model/source changed')
    if not binary.is_file() or not source.is_file():
        raise RuntimeError('diagnostic binary/source missing')
    lock = LOCK.open('a+')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    before = admitted()
    pair = before['cpus']
    argv = ['taskset', '-c', ','.join(map(str, pair)), str(binary), '--model', str(MODEL),
            '--ctx-size', '1024', '--batch-size', '128', '--ubatch-size', '128', '--n-gpu-layers', '0']
    env = dict(os.environ, LD_LIBRARY_PATH='/mnt/raid0/llm/kernels/production/cpu',
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    started = time.monotonic()
    captured = {}
    mapped = set()
    peak = 0
    failure = None
    log = out / 'ORACLE-NEGATIVE-RAW.log'
    with log.open('wb') as stream:
        proc = subprocess.Popen(argv, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                start_new_session=True)
        birth = int((Path('/proc') / str(proc.pid) / 'stat').read_text().rsplit(') ', 1)[1].split()[19])
        captured[proc.pid] = birth
        try:
            while proc.poll() is None:
                group = members(proc.pid)
                captured.update({pid: data['birth_ticks'] for pid, data in group.items()})
                peak = max(peak, sum(data['rss_bytes'] for data in group.values()))
                if peak > RSS_LIMIT:
                    raise RuntimeError('R11 RSS exceeded 8 GiB')
                if time.monotonic() - started >= 295:
                    raise RuntimeError('R11 300s bound approaching')
                for line in (Path('/proc') / str(proc.pid) / 'maps').read_text().splitlines():
                    path = line.rsplit(' ', 1)[-1]
                    if path.startswith('/') and ('libllama' in path or 'libggml' in path):
                        mapped.add(str(Path(path).resolve()))
                time.sleep(.1)
        except BaseException as exc:
            failure = repr(exc)
        try:
            drained = drain_group(proc.pid, birth, captured)
            rc = proc.wait(timeout=4)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            drained = False
            rc = proc.poll()
            failure = (failure or '') + '; drain failure: ' + repr(exc)
    raw = log.read_text(errors='replace')
    receipt = {'scope': 'R11_TEST_ONLY_ORACLE_NEGATIVE_DIAGNOSTIC', 'argv': argv,
               'model_sha256': MODEL_SHA, 'binary_sha256': sha(binary), 'source_sha256': sha(source),
               'original_test_source_sha256': sha(source_original), 'before_admission': before,
               'leader_pid': proc.pid, 'birth_ticks': birth, 'captured': captured,
               'mapped_libraries': {path: sha(path) for path in sorted(mapped)},
               'peak_rss_bytes': peak, 'wall_s': time.monotonic() - started,
               'returncode': rc, 'failure': failure, 'drained': drained,
               'raw_log_sha256': sha(log), 'raw_output': raw,
               'success_marker': 'recurrent rollback checkpoint restored successfully' in raw}
    (out / 'ORACLE-NEGATIVE-RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    lock.close()
    if not drained or failure or receipt['wall_s'] > 300:
        return 2
    return rc or 0


if __name__ == '__main__':
    raise SystemExit(main())
