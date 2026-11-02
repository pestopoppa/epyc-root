#!/usr/bin/env python3
"""Rowflow VKQ3 worker integration. Requires a separately reviewed plan.

The plan and prepared input must be bound by the launcher before publication.
Model digests are checked outside the grant; this worker refuses changed file
metadata, but metadata is not a cryptographic immutability guarantee.
"""
import hashlib
import json
import os
import re
from pathlib import Path
import signal
import sys
import time

from grant_bridge_draft import GrantGuard
from worker_draft import run_attempt
from completion_draft import publish_unit
from contained_supervisor_draft import _WRAPPER


def _stat(path):
    s = os.stat(path, follow_symlinks=False)
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def _grant_dir(env, dry):
    flags = Path(env.get('FILLER_FLAGS_DIR') or '/mnt/raid0/llm/tmp/compute-flags')
    grants = Path(env.get('FILLER_GRANTS_DIR') or flags / 'grants')
    if not flags.is_absolute() or not grants.is_absolute():
        raise ValueError('grant and flags directories must be absolute')
    if dry:
        dry_dir = env.get('FILLER_DRYRUN_DIR')
        if not dry_dir or not Path(dry_dir).is_absolute() or os.path.realpath(grants) != os.path.realpath(Path(dry_dir) / 'grants'):
            raise ValueError('dry-run grant directory mismatch')
    return grants


def run(plan, env, *, now=time.monotonic, wall=time.time, worker=run_attempt,
        publish=publish_unit):
    """Execute one real guard/worker/receipt/publish lifecycle.

    The caller supplies the reviewed plan, including prepared immutable paths;
    this checks path metadata rather than reading model weights under grant.
    """
    if env.get('FILLER_DRYRUN', '0') not in ('0', '1'):
        raise ValueError('invalid mode')
    dry = env.get('FILLER_DRYRUN', '0') == '1'
    mode = 'qualification' if dry else 'full'
    selected = env.get('FILLER_DRYRUN_RESULT_PATH') if dry else plan['result_path']
    if not selected or not Path(selected).is_absolute():
        raise ValueError('missing result path')
    if dry and os.path.realpath(selected) == os.path.realpath(plan['result_path']):
        raise ValueError('qualification aliases full result')
    paths = plan['inputs']
    if not paths or any(not Path(p).is_absolute() or _stat(p) != expected for p, expected in paths.items()):
        raise ValueError('prepared input or runtime changed since preflight')
    identities = plan['identity_sha256']
    if set(identities) != set(paths) or any(not isinstance(d, str) or not re.fullmatch(r'[0-9a-f]{64}', d) for d in identities.values()):
        raise ValueError('missing preflight identities')
    input_path = Path(plan['qualification_input'] if dry else plan['full_input'])
    runtime_files = plan['runtime_files']
    model_files = plan['model_files']
    required = [str(input_path), plan['tokenizer'], plan['model'], sys.executable, str(_WRAPPER)]
    if (not runtime_files or not model_files or plan['model'] not in model_files
            or any(p not in paths for p in required + runtime_files + model_files)):
        raise ValueError('unbound execution input')
    with input_path.open('rb') as stream:
        input_bytes = stream.read(plan['input_limit'] + 1)
    if len(input_bytes) > plan['input_limit']:
        raise ValueError('prepared input exceeds limit')
    if (hashlib.sha256(input_bytes).hexdigest() != plan['input_sha256'][mode]
            or identities[str(input_path)] != plan['input_sha256'][mode]):
        raise ValueError('prepared input digest mismatch')
    guard = GrantGuard(env, _grant_dir(env, dry), plan['local_stop'], expected_id=plan['id'], clock=wall)
    old = {}
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            old[sig] = signal.getsignal(sig)
            signal.signal(sig, guard.on_signal)
        deadline = now() + guard.remaining()
        # run_attempt's contained supervisor adds its own parent PID and wrapper.
        argv = [plan['tokenizer'], '-m', plan['model'], '--stdin', '--ids', '--no-escape']
        child_env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
                     'HIP_VISIBLE_DEVICES': '-1', 'ROCR_VISIBLE_DEVICES': '-1',
                     'LD_LIBRARY_PATH': plan['library_path'], 'OMP_NUM_THREADS': '1'}
        directory = worker(mode=mode, attempt_id=plan['attempt_id'], root=plan['receipt_root'],
                           argv=argv, input_bytes=input_bytes, env=child_env,
                           deadline_monotonic=deadline, cleanup_margin_s=plan['cleanup_margin_s'],
                           grant_valid=lambda: not guard.check(), stopped=guard.check, now=now)
        if guard.check():
            raise RuntimeError('grant lost before result publication')
        def check_before_publish():
            if guard.check():
                raise RuntimeError('grant lost during result publication')
        publish(mode, plan['attempt_id'], directory, selected, before_publish=check_before_publish)
        return selected
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: rowflow_worker.py PLAN PLAN_SHA256')
    raw = Path(sys.argv[1]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != sys.argv[2]:
        raise SystemExit('plan digest mismatch')
    run(json.loads(raw), os.environ)


if __name__ == '__main__':
    main()
