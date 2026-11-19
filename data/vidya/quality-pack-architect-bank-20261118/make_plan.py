#!/usr/bin/env python3
"""Freeze a new architect-critic semantic production bank before capture."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import quality_parity as parity

D = Path(__file__).resolve().parent
OLD = D.parent / 'architect-critic-20261118'
OLD_PLAN_PIN = '61aa74d218b11c96a5e05626465d15e348f7988cb768713c709537eadc989244'
ROW = 'handoff-vidya-quality-pack-architect-critic-bank-20261118'
PORT = 19482


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_original():
    raw = (OLD / 'plan.json').read_bytes()
    if sha(raw) != OLD_PLAN_PIN:
        raise ValueError('architect-critic original plan SHA-256 changed')
    return json.loads(raw)


def build_plan(original):
    plan = copy.deepcopy(original)
    plan['scope'] = 'new production-only architect-critic semantic-bank prerequisite'
    plan['recipes']['architect_critic_slice']['request_s'] = 240
    for item in plan['items']:
        item['id'] = item['id'].replace('architect-critic-', 'architect-critic-bank-', 1)
        body = item['request_body']
        user = body['messages'][0]
        if item['output_format'] == 'json':
            body['max_tokens'] = 256
            user['content'] += ' Limit fatal_flaw to one sentence of at most 12 words. Do not use Markdown.'
        elif item['output_format'] == 'reasoning':
            body['max_tokens'] = 384
            user['content'] += ' Give the final answer in two short sentences.'
        elif item['output_format'] == 'prose':
            body['max_tokens'] = 256
            user['content'] += ' Write at least 1000 words, starting with the exact word Reject.'
    plan['question_pool_sha256'] = sha(parity.canonical_json(plan['items']))
    plan['architect_critic_model']['receipt_snapshot'] = str(D / 'model-hash-receipt.json')
    plan['smoke_model']['receipt_snapshot'] = str(D / 'smoke-model-plan.original-bytes.json')
    plan['prior_frontdoor_json_mismatch']['snapshot'] = str(D / 'frontdoor-full-receipt.json')
    plan['original_architect_critic'] = {
        'plan_sha256': OLD_PLAN_PIN,
        'filing_sha256': sha((D / 'original-architect-critic-receipt.json').read_bytes()),
    }
    return plan


def row_spec():
    return {
        'id': ROW, 'owner': 'handoff-vidya-belief-substrate',
        'launcher': str(D / 'row-launch.sh'), 'lane': 'cpu', 'regions': 'any-cpu-quarter',
        'shape': 'quarter', 'ram_gib': 48, 'result_path': str(D / 'out/RESULT.json'),
        'result_format': 'json', 'estimate_s': 900, 'min_window_s': 1350, 'max_window_s': 1800,
        'priority_rank': 38, 'kind': 'compute', 'scratch_root': str(D),
        'handoff_task': 'handoffs/active/vidya-belief-substrate-program.md:VB-V9-8-QUALITY-PACK-ARCHITECT-BANK',
        'dryrun_native_result': True, 'first_progress_s': 100,
        'smoke_predicate': f'/usr/bin/python3 -B {D}/smoke_predicate.py',
        'decision_rule': (
            'Capture four newly pinned architect-critic requests on the original isolated v10 24-CPU '
            'MTP-cap-4 server and seal the production bank with the native output bytes. '
            'Stop on answer after strict item validation and owned server cleanup. '
            'Stop on STOP, deadline, failed identity, startup, transport or cleanup, or an inadmissible '
            'bank, recording the disposition and original bytes. Publisher smoke uses four CPUs '
            'and the pinned v10 no-spec small model for one native completion. '
            'Candidate collection awaits the complete seven-profile pack pin.'
        ),
        'verdict_by': 'agent',
        'keep': ['out/**', '*.py', '*.json', '*.md', '*.sh', 'SOURCE.sha256'],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, value in (('plan.json', build_plan(load_original())), ('row.spec.json', row_spec())):
        path = D / name
        generated = parity.pack_bytes(value)
        if args.check:
            if path.read_bytes() != generated:
                raise ValueError(f'generated {name} differs from the sealed file')
        else:
            with path.open('xb') as stream:
                stream.write(generated)


if __name__ == '__main__':
    main()
