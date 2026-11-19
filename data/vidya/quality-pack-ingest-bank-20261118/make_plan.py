#!/usr/bin/env python3
"""Freeze the ingest reconciliation request and its source production custody."""
import argparse
import base64
import copy
import json
from pathlib import Path

import capture_base as capture
import quality_parity as parity

D = Path(__file__).resolve().parent
WORKDIR = Path('/mnt/raid0/llm/tmp/vidya-belief-substrate/ingest-bank-20261118')
ORIGINAL = Path('/mnt/raid0/llm/worktrees/mains/h-vidya-belief-substrate/data/vidya/'
                'quality-pack-ingest-long-context-20261118')
ORIGINAL_PLAN = 'd0fd4411fd423a5b133f9d8aed4bf276d14ee5323b73e7ced1f0b181c6231745'
ORIGINAL_RECEIPT = '21358b09c966d00181935a7346e96692078e757dfa44695a42af984410346a5b'
ORIGINAL_ITEM = 'ingest-document-reconciliation'
NEW_ITEM = 'ingest-document-reconciliation-signed-record'
ROW = 'handoff-vidya-quality-pack-ingest-bank-20261118'


def read_pinned(path, expected, *, envelope=False):
    raw = path.read_bytes()
    if envelope:
        wrapper = json.loads(raw)
        if wrapper['sha256'] != expected:
            raise ValueError(f'original-byte envelope digest disagrees: {path}')
        raw = base64.b64decode(wrapper['bytes_b64'], validate=True)
    if capture.sha(raw) != expected:
        raise ValueError(f'bytes differ from their pin: {path}')
    return raw


def load_original():
    return json.loads(read_pinned(ORIGINAL / 'plan.json.original-bytes.json', ORIGINAL_PLAN, envelope=True))


def load_filing():
    return json.loads(read_pinned(ORIGINAL / 'full-capture/receipt.json', ORIGINAL_RECEIPT))


def build_plan(original, filing):
    plan = copy.deepcopy(original)
    plan['scope'] = 'prospective production-only ingest reconciliation bank replacement'
    plan['arms'] = {'production': original['arms']['production']}
    item, = [entry for entry in plan['items'] if entry['id'] == ORIGINAL_ITEM]
    item['id'] = NEW_ITEM
    item['output_format'] = 'json'
    body = item['request_body']
    user = body['messages'][0]
    prior_prompt = user['content']
    first = prior_prompt.index('Inspection 001.')
    last = prior_prompt.index('\nAn unsigned worksheet')
    inspections = prior_prompt[first:last]
    user['content'] = (
        'Read the equipment register in order. For each equipment ID, only a SIGNED entry '
        'sets the active annex. A later SIGNED entry replaces an earlier one. Ignore all '
        'UNSIGNED entries and routine inspections.\n'
        'Entry E17 | 08:10 | SIGNED | equipment LARK | annex NORTH\n'
        + inspections + '\n'
        'Entry E42 | 13:05 | UNSIGNED | equipment LARK | annex WEST\n'
        'Entry E59 | 15:40 | SIGNED | equipment LARK | annex SOUTH\n'
        'Entry E63 | 16:15 | UNSIGNED | equipment LARK | annex WEST\n'
        'For equipment LARK, report the active annex and cite the entry ID that sets it. '
        'Return only a JSON object with string fields annex and governing_record. Use '
        'uppercase values and copy the governing entry ID exactly.'
    )
    item['validator'] = {
        'id': 'json-object-subset.v1', 'expected': {'annex': 'SOUTH', 'governing_record': 'E59'},
    }
    plan['question_pool_sha256'] = capture.sha(capture.canonical(plan['items']))
    plan['request_files'] = {}
    for entry in [*plan['items'], *plan['smoke_items']]:
        name = entry['id']
        wire = capture.canonical(entry['request_body'])
        plan['request_files'][name] = {'path': f'requests/{name}.json', 'sha256': capture.sha(wire)}
    plan['ingest_long_context_model']['receipt_snapshot'] = str(WORKDIR / 'model-hash-receipt.json')
    plan['smoke_model']['receipt_snapshot'] = str(WORKDIR / 'smoke-model-plan.original-bytes.json')
    plan['prior_frontdoor_json_mismatch']['snapshot'] = str(WORKDIR / 'frontdoor-full-receipt.json')
    plan['original_production'] = {
        'plan_sha256': ORIGINAL_PLAN,
        'filing_sha256': ORIGINAL_RECEIPT,
        'bank_sha256': filing['original_files_sha256']['native/banked-capture.json'],
        'replaced_id': ORIGINAL_ITEM,
        'replacement_id': NEW_ITEM,
    }
    return plan


def row_spec():
    return {
        'id': ROW, 'owner': 'handoff-vidya-belief-substrate',
        'launcher': str(WORKDIR / 'row-launch.sh'), 'lane': 'cpu', 'regions': 'any-cpu-quarter',
        'shape': 'quarter', 'ram_gib': 48, 'result_path': str(WORKDIR / 'out/RESULT.json'),
        'result_format': 'json', 'estimate_s': 500, 'min_window_s': 900, 'max_window_s': 1200,
        'priority_rank': 38, 'kind': 'compute', 'scratch_root': str(WORKDIR),
        'handoff_task': 'handoffs/active/vidya-belief-substrate-program.md:VB-V9-8-QUALITY-PACK-INGEST-BANK',
        'dryrun_native_result': True, 'first_progress_s': 100,
        'smoke_predicate': f'/usr/bin/python3 -B {WORKDIR}/smoke_predicate.py',
        'decision_rule': (
            'Capture one new ingest reconciliation request on the isolated v10 Qwen3.8-27B Q8_0 '
            '24-CPU no-spec server with one 16384-token split q8_0 KV slot. Revalidate three original '
            'production responses and admit only a clean stop with both correct structured values '
            'and at least 4096 uncached native prompt tokens on the replacement. Stop after the one '
            'request and owned cleanup, or on STOP, deadline, identity, capture, cleanup or strict '
            'admission failure. Publisher smoke uses the pinned four-CPU v10 small model. '
            'Candidate collection awaits a sealed seven-profile pack.'
        ),
        'verdict_by': 'agent',
        'keep': ['out/**', 'requests/**', '*.py', '*.json', '*.md', '*.sh', 'SOURCE.sha256'],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    plan = build_plan(load_original(), load_filing())
    files = {'plan.json': parity.pack_bytes(plan), 'row.spec.json': parity.pack_bytes(row_spec())}
    for item in [*plan['items'], *plan['smoke_items']]:
        files[f"requests/{item['id']}.json"] = capture.canonical(item['request_body'])
    for name, raw in files.items():
        path = D / name
        if args.check:
            if path.read_bytes() != raw:
                raise ValueError(f'generated {name} differs from the sealed file')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            capture.write(path, raw)


if __name__ == '__main__':
    main()
