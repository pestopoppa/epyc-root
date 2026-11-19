"""Allocator row for three original private GitNexus base indexes, no scoring."""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gitnexus_build as build

native = build.native
ROW = 'dcp10-gitnexus-build-20261118'
MAX_SECONDS = 3600


def save(path, record):
    build.write_new(path, record)


def smoke_marker():
    if os.environ.get('FILLER_SMOKE') != '1' or os.environ.get('FILLER_DRYRUN') != '1':
        raise ValueError('publisher smoke required')
    t0 = os.environ['FILLER_SMOKE_T0']
    if not t0.isdigit() or len(t0) != 10:
        raise ValueError('invalid smoke time')
    return Path(os.environ['FILLER_DRYRUN_DIR']) / f'{ROW}-{t0}.json'


def clock():
    if os.environ.get('FILLER_ID') != ROW:
        raise ValueError('allocator row required')
    deadline = min(float(os.environ['FILLER_DEADLINE']), time.time() + MAX_SECONDS)
    stop = Path(os.environ['FILLER_STOPFILE'])

    def remaining(cap):
        left = min(cap, deadline - time.time())
        if stop.exists() or left <= 0:
            raise RuntimeError('allocator STOP/deadline')
        return left
    return remaining


def qualify(root, remaining):
    marker = smoke_marker()
    fixture = root / f'smoke-{uuid4().hex}'
    fixture.mkdir(mode=0o700)
    base = fixture / 'base'
    base.mkdir(mode=0o700)
    (base / 'alpine.py').write_text('def alpine_sensor():\n    return 42\n\ndef read_sensor():\n    return alpine_sensor()\n')
    output = fixture / 'output'
    output.mkdir(mode=0o700)
    binding = {'root': str(base), 'base_commit': 'publisher-fixture'}
    before = build.inventory(base)

    def verify():
        if build.inventory(base) != before:
            raise ValueError('smoke fixture mutated')
    command, result = build.run_isolated(output, binding, remaining(120), verify)
    meta = json.loads((output / 'index/meta.json').read_text())
    stats = meta['stats']
    if ({path.name for path in (output / 'index').iterdir()} != {'meta.json', 'lbug'}
            or stats['files'] != 1 or stats['nodes'] < 3 or stats['edges'] < 1 or stats['embeddings'] != 0):
        raise ValueError('native smoke did not produce checkpointed graph')
    save(marker, {'row': ROW, 'unit': 'native-fixture', 'stats': stats,
                  'command': command, 'stderr_sha256': native.sha256(result.stderr).hexdigest(),
                  'files': build.inventory(output / 'index')})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument('--request-sha', required=True)
    parser.add_argument('mode', choices=['precondition', 'run', 'complete', 'smoke'])
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    assets = root / 'assets'
    result_path = root / 'native/RESULT.json'
    if args.mode == 'smoke':
        return 0 if smoke_marker().is_file() else 1
    if args.mode == 'complete':
        return 0 if result_path.exists() and json.loads(result_path.read_text()).get('completed') == 3 else 1
    build.check_build_path(assets)
    native.read_record(assets / 'build-request.json', args.request_sha, 32 * 1024**2)
    if result_path.exists():
        raise ValueError('row never retries completed output')
    if args.mode == 'precondition':
        return 0
    signal.signal(signal.SIGTERM, native._stop_on_term)
    remaining = clock()
    if os.environ.get('FILLER_SMOKE') == '1':
        qualify(root, remaining)
        return 0
    output = root / 'native'
    output.mkdir(mode=0o700)
    receipts, error = {}, None
    try:
        for task_id, task in native.original_tasks().items():
            receipt = build.build_private_index(assets, args.request_sha, task_id, remaining)
            receipts[task_id] = receipt
            save(output / f"{task['language']}.json", {'unit': task_id, 'receipt_sha256': receipt})
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - checkpoint every failed original attempt
        error = f'{type(exc).__name__}: {exc}'
    save(result_path, {'row': ROW, 'completed': len(receipts), 'receipt_sha256': receipts,
                       'request_sha256': args.request_sha, 'error': error,
                       'unknown': [key for key in native.original_tasks() if key not in receipts]})
    return 0 if error is None else 1


if __name__ == '__main__':
    sys.exit(main())
