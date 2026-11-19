#!/usr/bin/env python3
"""Provisional V11-FA-8 capture coverage reader; no inference verdict.

The instrument must adopt and independently qualify this schema before use.
"""
import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

KEYS = ('arm', 'context', 'layer', 'kind', 'index')
KINDS = {'v_abs_max', 'row_sum'}


def key(row):
    if not isinstance(row, dict) or any(k not in row for k in KEYS):
        raise ValueError('missing identity')
    if row['arm'] not in ('A', 'C') or row['kind'] not in KINDS:
        raise ValueError('invalid arm or kind')
    for field in ('context', 'layer', 'index'):
        if type(row[field]) is not int or row[field] < (1 if field == 'context' else 0):
            raise ValueError('invalid numeric identity')
    return tuple(row[k] for k in KEYS)


def validate_capture(manifest, records):
    """Compare frozen per-value identity list to emitted values; never infer a gate."""
    if not isinstance(manifest, dict) or manifest.get('schema') != 'v11-fa8-identities-v1':
        raise ValueError('manifest schema')
    identities = manifest.get('expected')
    if not isinstance(identities, list) or not identities:
        raise ValueError('empty identity set')
    expected = [key(row) for row in identities]
    if len(set(expected)) != len(expected):
        raise ValueError('duplicate expected identity')
    groups = {(arm, context, layer) for arm, context, layer, _, _ in expected}
    arms = {row[0] for row in expected}
    contexts = {row[1] for row in expected}
    if arms != {'A', 'C'} or len(contexts) != 2:
        raise ValueError('expected both arms and two frozen context lengths')
    layers = {row[2] for row in expected}
    if any(not any((a, c, l) == row[:3] for row in expected)
           for a in arms for c in contexts for l in layers):
        raise ValueError('incomplete arm/context/layer matrix')
    if any({kind for a, c, l, kind, _ in expected if (a, c, l) == group} != KINDS for group in groups):
        raise ValueError('missing metric kind in group')
    if not isinstance(records, list):
        raise ValueError('records must be list')
    seen = {}
    for row in records:
        identity = key(row)
        if identity in seen:
            raise ValueError('duplicate observation')
        value = row.get('value')
        if type(value) in (int, float):
            try:
                value = float(value)
            except OverflowError as exc:
                raise ValueError('out-of-range JSON number') from exc
            if not math.isfinite(value):
                raise ValueError('nonfinite values must be encoded as strings')
            if row['kind'] == 'v_abs_max' and value < 0:
                raise ValueError('negative absolute maximum')
        elif value not in ('nan', '+inf', '-inf'):
            raise ValueError('invalid value')
        seen[identity] = value
    if set(seen) != set(expected):
        raise ValueError(f'coverage mismatch: missing={len(set(expected)-set(seen))}, unexpected={len(set(seen)-set(expected))}')
    result = defaultdict(lambda: {'count': 0, 'finite_max_abs': None, 'nonfinite': 0, 'above_fp16_range': 0})
    for (arm, context, layer, kind, _), value in seen.items():
        row = result[(arm, context, layer, kind)]
        row['count'] += 1
        if isinstance(value, str):
            row['nonfinite'] += 1
        else:
            magnitude = abs(value)
            row['finite_max_abs'] = max(row['finite_max_abs'] or 0, magnitude)
            row['above_fp16_range'] += magnitude > 65504
    return [{'arm': a, 'context': c, 'layer': l, 'kind': k, **v}
            for (a, c, l, k), v in sorted(result.items())]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('manifest', type=Path)
    p.add_argument('records', type=Path)
    args = p.parse_args()
    # Python's JSON decoder otherwise silently accepts NaN/Infinity numeric literals.
    def invalid(token):
        raise ValueError(f'nonstandard JSON literal {token}')
    manifest = json.loads(args.manifest.read_text(), parse_constant=invalid)
    records = [json.loads(line, parse_constant=invalid) for line in args.records.read_text().splitlines()]
    print(json.dumps({'status': 'coverage_complete', 'verdict': None,
                      'summary': validate_capture(manifest, records)}, allow_nan=False, sort_keys=True))


if __name__ == '__main__':
    main()
