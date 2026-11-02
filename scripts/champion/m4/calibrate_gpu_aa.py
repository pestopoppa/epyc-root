#!/usr/bin/env python3
"""Descriptively reduce paired C5/C5 GPU controls; never emits a gate verdict.

Inputs are a frozen pre-run plan and native capture records. This reader checks
structural matching and re-derives throughput. Independent admission, image,
residency and capture provenance must be validated by the owning producer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reduce(plan: dict, records: list[dict], expected_plan_hash: str) -> dict:
    if plan.get('schema') != 'epyc.m4.gpu.aa.plan.v1':
        raise ValueError('wrong plan schema')
    if plan.get('intent') != 'descriptive_only':
        raise ValueError('A/A cannot authorize a gate')
    cells = plan.get('cells')
    if not isinstance(cells, list) or not cells or len(cells) != len(records):
        raise ValueError('incomplete denominator')
    seen = set(); groups: dict[tuple, dict[str, float]] = {}
    for cell, record in zip(cells, records, strict=True):
        key = cell.get('id')
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError('duplicate or invalid cell')
        seen.add(key)
        if record.get('cell_id') != key or record.get('plan_sha256') != expected_plan_hash:
            raise ValueError('record differs from pre-run plan')
        if record.get('status') != 'COMPLETE' or record.get('cleanup_verified') is not True:
            raise ValueError('incomplete process or cleanup')
        for name in ('role', 'source_commit', 'image_sha256', 'recipe_sha256', 'model_sha256', 'prompt_sha256', 'np', 'pair', 'arm'):
            if cell.get(name) is None or record.get(name) != cell[name]:
                raise ValueError(f'cell {key}: conflicting {name}')
        if cell['arm'] not in ('A1', 'A2') or type(cell['np']) is not int or cell['np'] <= 0:
            raise ValueError('invalid calibration arm or concurrency')
        requests = record.get('requests')
        count = cell.get('request_count')
        if type(count) is not int or count <= 0 or not isinstance(requests, list) or len(requests) != count:
            raise ValueError('request denominator incomplete')
        sums: dict[int, list[float]] = {}; indices = set()
        for req in requests:
            idx = req.get('request_index'); stream = req.get('stream_id')
            tokens = req.get('predicted_tokens'); millis = req.get('predicted_ms')
            if (type(idx) is not int or idx in indices or type(stream) is not int or not 0 <= stream < cell['np']
                or req.get('success') is not True or req.get('http_status') != 200 or req.get('error') or type(tokens) is not int or tokens <= 0
                or type(millis) not in (int, float) or not math.isfinite(millis) or millis <= 0):
                raise ValueError('invalid request')
            indices.add(idx); s = sums.setdefault(stream, [0, 0.0]); s[0] += tokens; s[1] += millis / 1000
        if indices != set(range(count)):
            raise ValueError('request indices incomplete')
        value = sum(tokens / seconds for tokens, seconds in sums.values())
        if type(record.get('aggregate_decode_tps')) not in (float, int) or not math.isclose(value, record['aggregate_decode_tps'], rel_tol=1e-12):
            raise ValueError('aggregate does not rederive')
        group = tuple(cell[n] for n in ('role', 'source_commit', 'image_sha256', 'recipe_sha256', 'model_sha256', 'prompt_sha256', 'np', 'pair'))
        arms = groups.setdefault(group, {})
        if cell['arm'] in arms:
            raise ValueError('duplicate pair arm')
        arms[cell['arm']] = value
    pairs = []
    for key, arms in groups.items():
        if set(arms) != {'A1', 'A2'}:
            raise ValueError('unmatched process pair')
        pairs.append({'role': key[0], 'np': key[6], 'pair': key[7], 'a1_tps': arms['A1'],
                      'a2_tps': arms['A2'], 'a2_over_a1': arms['A2']/arms['A1']})
    return {'schema': 'epyc.m4.gpu.aa.descriptive.v1', 'plan_sha256': expected_plan_hash,
            'pairs': pairs,
            'decision': None, 'gate_authorized': False,
            'limitations': ['Descriptive only; not an acceptance floor',
                            'Independent admission, provenance and in-window residency verification required']}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--records', required=True, type=Path)
    args = parser.parse_args()
    try:
        if file_hash(args.plan) != args.plan_sha256:
            raise ValueError('plan digest mismatch')
        result = reduce(json.loads(args.plan.read_text()), json.loads(args.records.read_text()), args.plan_sha256)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc), 'gate_authorized': False}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
