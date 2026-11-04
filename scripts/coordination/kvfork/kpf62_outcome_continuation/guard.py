#!/usr/bin/env python3
"""Refuse incomplete or unpaired G3 outcome inputs; does not score quality."""
import argparse
import json
from pathlib import Path


def validate(ids, outcomes, segments):
    ids = list(ids)
    if not ids or len(ids) != len(set(ids)) or any(not isinstance(x, str) or not x for x in ids):
        raise ValueError('invalid expected ids')
    expected = {(x, arm) for x in ids for arm in ('full', 'reuse')}
    indexed = {}
    for row in outcomes:
        key = (row.get('id'), row.get('arm'))
        if key not in expected or key in indexed:
            raise ValueError('unexpected or duplicate outcome')
        if row.get('complete') is not True or row.get('finish_reason') != 'eog':
            raise ValueError('incomplete outcome')
        if not isinstance(row.get('output_tokens'), list):
            raise ValueError('missing outcome tokens')
        indexed[key] = row
    if set(indexed) != expected:
        raise ValueError('missing paired outcome')
    ledger = {key: [] for key in expected}
    for row in segments:
        key = (row.get('id'), row.get('arm'))
        if key not in ledger:
            raise ValueError('unexpected segment')
        ledger[key].append(row)
    for key, rows in ledger.items():
        if not rows:
            raise ValueError('missing segment ledger')
        tokens = []
        for i, row in enumerate(rows):
            if row.get('segment') != i or row.get('start') != len(tokens) or not isinstance(row.get('tokens'), list):
                raise ValueError('out-of-order or malformed segment')
            expected_reason = 'eog' if i == len(rows) - 1 else 'continue'
            if row.get('finish_reason') != expected_reason:
                raise ValueError('incomplete segment ledger')
            tokens.extend(row['tokens'])
        if tokens != indexed[key]['output_tokens']:
            raise ValueError('segment/output token mismatch')
    return {'pairs': len(ids), 'outcomes': len(indexed), 'segments': sum(map(len, ledger.values()))}


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ids', required=True, help='JSON array of predeclared request IDs')
    p.add_argument('--outcomes', required=True)
    p.add_argument('--segments', required=True)
    a = p.parse_args()
    try:
        print(json.dumps(validate(json.loads(Path(a.ids).read_text()), rows(a.outcomes), rows(a.segments)), sort_keys=True))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as e:
        p.exit(2, f'INVALID: {e}\n')


if __name__ == '__main__':
    main()
