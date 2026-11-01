#!/usr/bin/env python3
"""Build an offline, digest-bound three-arm schedule; does not start inference."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path

ARMS = ('baseline', 'strategy_short', 'strategy_long')
ORDERS = tuple(itertools.permutations(ARMS))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(prompt_dir: Path, suite: Path, protocol: Path) -> dict:
    manifest_raw = (prompt_dir / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_raw)
    if manifest.get('schema') != 'epyc.strategy_prompt_ablation.preparation.v1':
        raise ValueError('foreign preparation manifest')
    specs = manifest.get('arms')
    if not isinstance(specs, dict) or set(specs) != set(ARMS):
        raise ValueError('manifest must contain exactly the three strategy arms')
    digests = {}
    for arm in ARMS:
        spec = specs[arm]
        if not isinstance(spec, dict) or spec.get('file') != arm + '.txt':
            raise ValueError('invalid prompt snapshot filename')
        data = (prompt_dir / spec['file']).read_bytes()
        if len(data) != spec.get('bytes') or sha(data) != spec.get('sha256'):
            raise ValueError('prompt snapshot failed custody check')
        digests[arm] = sha(data)
    if len(set(digests.values())) != 3:
        raise ValueError('arms must have distinct prompt bytes')
    suite_raw = suite.read_bytes()
    questions = json.loads(suite_raw).get('questions')
    if not isinstance(questions, list) or not questions:
        raise ValueError('suite must contain a nonempty questions list')
    ids = [q.get('id') if isinstance(q, dict) else None for q in questions]
    if any(not isinstance(q, str) or not q for q in ids) or len(set(ids)) != len(ids):
        raise ValueError('question IDs must be unique nonempty strings')
    protocol_raw = protocol.read_bytes()
    p = json.loads(protocol_raw)
    if p.get('schema') != 'epyc.strategy_prompt_ablation.protocol.v1':
        raise ValueError('foreign protocol')
    for key in ('role', 'model_identity', 'server_identity', 'tokenizer_identity', 'kernel_identity', 'decision_rule', 'stopping_rule'):
        if not isinstance(p.get(key), str) or not p[key].strip():
            raise ValueError(f'protocol requires {key}')
    max_loss = p.get('max_absolute_accuracy_loss')
    if isinstance(max_loss, bool) or not isinstance(max_loss, (int, float)) or not math.isfinite(max_loss) or not 0 <= max_loss <= 1:
        raise ValueError('max_absolute_accuracy_loss must be a fraction in [0,1]')
    return {'schema': 'epyc.strategy_prompt_ablation.plan.v1',
            'preparation_sha256': sha(manifest_raw), 'suite_sha256': sha(suite_raw),
            'protocol_sha256': sha(protocol_raw), 'prompt_sha256': digests,
            'schedule': [{'question_id': qid, 'order': list(ORDERS[i % len(ORDERS)])}
                         for i, qid in enumerate(ids)],
            'order_note': 'six permutations cycle in suite order; incomplete cycles are unbalanced',
            'run_authority': False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prompt-dir', required=True, type=Path)
    parser.add_argument('--suite', required=True, type=Path)
    parser.add_argument('--protocol', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    plan = build(args.prompt_dir, args.suite, args.protocol)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(plan, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
