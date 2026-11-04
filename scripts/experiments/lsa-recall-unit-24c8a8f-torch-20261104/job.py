#!/usr/bin/env python3
"""One model-free recall unit suite under the keeper's CPU-quarter claim."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
CODE = HERE / 'code'
SOURCE = Path('/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/quality-screen-prep/recall-instrument-worktree')
COMMIT = '24c8a8f2aa7cb4800fe4637151aaa5e149a7af71'
FILES = ('reference.py', 'mask_worker.py', 'recall_runner.py', 'test_recall_instrument.py')
ROW = 'lsa-recall-unit-24c8a8f-torch-20261104'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_grant():
    e = os.environ
    if e.get('FILLER_ID') != ROW or e.get('FILLER_NEEDGPU') != '0' or not e.get('FILLER_CPUS'):
        raise ValueError('owned CPU-quarter filler grant required')
    for key in ('FILLER_STOPFILE', 'FILLER_DEADLINE', 'FILLER_END'):
        if not e.get(key):
            raise ValueError(f'{key} missing')
    if Path(e['FILLER_STOPFILE']).exists() or not float(e['FILLER_END']) > float(e['FILLER_DEADLINE']) > time.time():
        raise ValueError('filler stop or deadline reached')


def preflight():
    check_grant()
    import torch
    if torch.__version__ != '2.13.0+cu130':
        raise ValueError('unexpected torch version')
    head = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    if head != COMMIT or subprocess.check_output(['git', '-C', str(SOURCE), 'status', '--porcelain']):
        raise ValueError('isolated recall source commit or clean state changed')
    bound = {}
    for name in FILES:
        original = subprocess.check_output(['git', '-C', str(SOURCE), 'show', f'{COMMIT}:experiments/lsa-screen/{name}'])
        copied = (CODE / name).read_bytes()
        if copied != original:
            raise ValueError(f'committed recall test code changed: {name}')
        bound[name] = digest(copied)
    for name in ('src/models/qwen35.cpp', 'src/models/lsa-screen-reference.h'):
        bound[name] = digest(subprocess.check_output(['git', '-C', str(SOURCE), 'show', f'{COMMIT}:{name}']))
    return {'schema': 'lsa-recall-unit-binding-v1', 'source_commit': COMMIT,
            'files_sha256': bound, 'model_used': False, 'gpu_used': False}


def record(kind, binding, **extra):
    return dict(binding, kind=kind, time_utc=dt.datetime.now(dt.timezone.utc).isoformat(), **extra)


def stop_owned(proc):
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)
    if proc.poll() is None:
        raise RuntimeError('owned unit-test process still alive')


def main():
    binding = preflight()
    if os.environ.get('FILLER_SMOKE') == '1':
        target = Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
        target.write_text(json.dumps(record('smoke-preflight-only', binding, status='pass', tests_executed=0), sort_keys=True) + '\n')
        return
    check_grant()
    result = HERE / 'RESULT.json'
    if result.exists() or (HERE / 'results.jsonl').exists():
        raise ValueError('one-shot unit result already exists')
    log = HERE / 'unit-tests.log'
    environment = dict(os.environ, OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
                       HIP_VISIBLE_DEVICES='', ROCR_VISIBLE_DEVICES='', CUDA_VISIBLE_DEVICES='')
    started = time.monotonic()
    proc = None
    try:
        with log.open('wb') as stream:
            proc = subprocess.Popen([sys.executable, '-m', 'unittest', '-v', 'test_recall_instrument'],
                                    cwd=CODE, env=environment, stdout=stream, stderr=subprocess.STDOUT,
                                    start_new_session=True)
            while proc.poll() is None:
                check_grant()
                if time.monotonic() - started >= 120:
                    raise TimeoutError('model-free unit suite exceeded 120 seconds')
                if log.stat().st_size > 1024 * 1024:
                    raise ValueError('unit output exceeded 1 MiB')
                time.sleep(0.25)
        status = 'pass' if proc.returncode == 0 else 'fail'
        payload = record('unit-suite', binding, status=status, rc=proc.returncode,
                         log_sha256=digest(log.read_bytes()), elapsed_s=time.monotonic() - started)
        result.write_text(json.dumps(payload, sort_keys=True, indent=2) + '\n')
        (HERE / 'results.jsonl').write_text(json.dumps(payload, sort_keys=True) + '\n')
        if status != 'pass':
            raise RuntimeError('model-free recall unit suite failed')
    finally:
        if proc is not None:
            stop_owned(proc)
        if log.is_file() and log.stat().st_size > 1024 * 1024:
            with log.open('rb+') as stream:
                stream.truncate(1024 * 1024)


if __name__ == '__main__':
    main()
