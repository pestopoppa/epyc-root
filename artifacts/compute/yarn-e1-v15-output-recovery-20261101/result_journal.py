"""Fail-closed E1 output namespaces and completion notification recovery.

Markers remain the source of completion. This module only recovers one
notification per marker; it does not validate scientific evidence or lock
against concurrent writers. The outer job must enforce exclusive ownership.
"""
import json
import os
from pathlib import Path


def output_root(env):
    real = env.get('FILLER_RESULTS_DIR')
    if not real:
        raise ValueError('FILLER_RESULTS_DIR required')
    production = Path(real).resolve()
    dry = env.get('FILLER_DRYRUN', '0')
    if dry not in ('0', '1'):
        raise ValueError('invalid FILLER_DRYRUN')
    if dry == '0':
        return production
    path = env.get('FILLER_DRYRUN_DIR')
    if not path:
        raise ValueError('FILLER_DRYRUN_DIR required')
    root = (Path(path).resolve() / 'yarn-e1-results').resolve()
    if root == production or root in production.parents or production in root.parents:
        raise ValueError('dry-run and production output roots overlap')
    return root


def notify_completed(root, step):
    root = Path(root).resolve()
    marker = root / '-'.join(step) / 'complete.json'
    payload = json.loads(marker.read_text())
    if payload.get('status') != 'COMPLETE' or [payload.get('image'), payload.get('arm'), payload.get('level')] != list(step):
        raise ValueError('completion marker identity mismatch')
    result = root / 'completed-cells.jsonl'
    result.parent.mkdir(parents=True, exist_ok=True)
    record = {'image': step[0], 'arm': step[1], 'level': step[2], 'complete_path': str(marker)}
    if result.exists():
        data = result.read_bytes()
        if data and not data.endswith(b'\n'):
            raise ValueError('partial journal line; manual reconciliation required')
        seen = [json.loads(line) for line in data.splitlines()]
        matches = [row for row in seen if [row.get('image'), row.get('arm'), row.get('level')] == list(step)]
        if matches:
            if len(matches) != 1 or matches[0] != record:
                raise ValueError('conflicting or duplicate notification')
            return False
    with result.open('a') as f:
        f.write(json.dumps(record, sort_keys=True) + '\n')
        f.flush()
        os.fsync(f.fileno())
    return True
