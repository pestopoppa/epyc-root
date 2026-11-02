#!/usr/bin/env python3
"""Offline P6 catalog-growth comparison over prospectively bound run records.

This comparator defines a provisional input contract. The P0.4/SC86 runner does
not yet emit it; historical records must not be retrofitted to satisfy it.
"""
import argparse
import json
from pathlib import Path

ARMS = ('baseline', 'candidate')
TRIALS = (1, 2)
IDENTITY = ('model', 'server', 'plugin', 'base_catalog')


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def compare(manifest, records):
    """Return per-task decisions; reject ambiguous or mismatched input identities."""
    if not isinstance(manifest, dict) or not isinstance(records, list):
        raise ValueError('manifest must be an object and records an array')
    shared = manifest.get('identity')
    catalogs = manifest.get('catalogs')
    tasks = manifest.get('tasks')
    if not isinstance(shared, dict) or not all(_text(shared.get(k)) for k in IDENTITY):
        raise ValueError('missing frozen shared identity')
    if not isinstance(catalogs, dict) or not all(_text(catalogs.get(k)) for k in ARMS):
        raise ValueError('missing frozen arm catalogs')
    if catalogs['baseline'] == catalogs['candidate']:
        raise ValueError('baseline and candidate catalog identities must differ')
    if not isinstance(tasks, list) or not tasks:
        raise ValueError('empty task set')
    task_map = {}
    for task in tasks:
        if not isinstance(task, dict) or not _text(task.get('id')) or not _text(task.get('fixture')) or task.get('previously_passing') is not True:
            raise ValueError('task requires id, fixture identity and previously_passing=true')
        if task['id'] in task_map:
            raise ValueError('duplicate task')
        task_map[task['id']] = task
    indexed = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('record must be an object')
        task_id, arm, trial = record.get('task'), record.get('arm'), record.get('trial')
        if not isinstance(task_id, str) or task_id not in task_map or arm not in ARMS or type(trial) is not int or trial not in TRIALS:
            raise ValueError('unexpected task, arm or trial')
        key = (task_id, arm, trial)
        if key in indexed:
            raise ValueError('duplicate trial')
        identity = record.get('identity')
        if not isinstance(identity, dict) or any(identity.get(k) != shared[k] for k in IDENTITY):
            raise ValueError('shared identity mismatch')
        if record.get('fixture') != task_map[task_id]['fixture'] or record.get('catalog') != catalogs[arm]:
            raise ValueError('fixture or catalog mismatch')
        outcome = record.get('outcome')
        if outcome not in ('pass', 'fail', 'infra_error'):
            raise ValueError('unknown outcome')
        tokens = record.get('tokens')
        if outcome == 'infra_error':
            if tokens is not None and (type(tokens) is not int or tokens < 0):
                raise ValueError('invalid token count')
        elif type(tokens) is not int or tokens < 0:
            raise ValueError('missing or invalid token count')
        indexed[key] = record
    expected = {(task, arm, trial) for task in task_map for arm in ARMS for trial in TRIALS}
    if set(indexed) != expected:
        raise ValueError('missing trials')
    outputs = []
    for task in task_map:
        before = [indexed[(task, 'baseline', n)] for n in TRIALS]
        after = [indexed[(task, 'candidate', n)] for n in TRIALS]
        before_tokens = sum(r['tokens'] for r in before) if all(r['tokens'] is not None for r in before) else None
        after_tokens = sum(r['tokens'] for r in after) if all(r['tokens'] is not None for r in after) else None
        ratio = after_tokens / before_tokens if before_tokens and after_tokens is not None else None
        if any(r['outcome'] == 'infra_error' for r in before + after) or ratio is None:
            verdict = 'unknown'
        elif all(r['outcome'] == 'fail' for r in before):
            verdict = 'unknown'  # The frozen previously-passing baseline did not reproduce.
        elif all(r['outcome'] == 'fail' for r in after):
            verdict = 'fail'
        else:
            verdict = 'pass'
        outputs.append({'task': task, 'baseline_outcomes': [r['outcome'] for r in before],
                        'candidate_outcomes': [r['outcome'] for r in after],
                        'baseline_tokens': before_tokens, 'candidate_tokens': after_tokens,
                        'candidate_to_baseline_token_ratio': ratio, 'verdict': verdict})
    overall = 'fail' if any(r['verdict'] == 'fail' for r in outputs) else 'unknown' if any(r['verdict'] == 'unknown' for r in outputs) else 'pass'
    return {'verdict': overall, 'tasks': outputs, 'token_ratio_basis': 'sum of both candidate trials / sum of both baseline trials'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('records', type=Path, help='JSON array of prospectively bound trial records')
    args = parser.parse_args()
    print(json.dumps(compare(json.loads(args.manifest.read_text()), json.loads(args.records.read_text())), indent=2))


if __name__ == '__main__':
    main()
