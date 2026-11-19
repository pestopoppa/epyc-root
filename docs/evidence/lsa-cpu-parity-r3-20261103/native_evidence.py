"""Capture one original LSA item through the existing research-screen writer."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts' / 'vidya'))
from adapters import research_screen as screen


def _spec(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def emit(record, manifest_path, output_path, producer_path=None):
    """Seal an already-written original record at producer time; return receipt path.

    One item is one denominator; missing runtime identity remains in the original
    binding, and unsuccessful items remain failures/invalid/abstentions.
    """
    manifest_path, output_path = Path(manifest_path), Path(output_path)
    if json.loads(output_path.read_bytes()) != record:
        raise ValueError('original output bytes do not match the producer record')
    original = _spec(output_path)
    manifest = _spec(manifest_path)
    if record.get('manifest_sha256') != manifest['sha256']:
        raise ValueError('manifest digest mismatch')
    status = {'pass': 'scored', 'failure': 'failure', 'timeout': 'failure',
              'invalid': 'invalid', 'abstention': 'abstention'}[record['status']]
    row = {'item_id': record['item']['id'], 'status': status, 'original': record}
    row_path = output_path.with_name(output_path.name + '.research-screen.jsonl')
    row_bytes = json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'
    if row_path.exists() and row_path.read_bytes() != row_bytes:
        raise ValueError('existing evidence row differs')
    if not row_path.exists():
        with row_path.open('xb') as stream:
            stream.write(row_bytes)
    raw = _spec(row_path)
    raw['row_count'] = 1
    counts = {'eligible': 1, 'scored': 0, 'failure': 0, 'invalid': 0, 'abstention': 0}
    counts[status] = 1
    runner = _spec(producer_path if producer_path is not None else Path(__file__).with_name('runner.py'))
    identity = original['sha256']
    body = {
        'schema': screen.SCHEMA, 'receipt_id': 'lsa-item-' + identity,
        'run_id': 'lsa-item-' + identity, 'timestamp': record['time_utc'],
        'source': {'kind': 'lsa-screen-item', 'revision': record.get('binding', {}).get('source_commit') or 'unknown'},
        'producer': {'name': 'lsa-screen-runner', 'revision': runner['sha256']},
        'input_manifest': manifest, 'baseline': {'id': 'dense', 'revision': 'per-item reference; no comparison asserted'},
        'raw_outputs': raw,
        'window': {'kind': 'diagnostic', 'id': str(record['item'].get('split', 'unknown')),
                   'reason': 'Single item diagnostic; no completed held-out comparison.'},
        'counts': counts,
        'rule': {'id': 'lsa-item-capture', 'revision': _spec(Path(__file__))['sha256'],
                 'statement': 'Capture each attempted item; no promotion decision.'},
        'disposition': {'decision': 'diagnostic', 'reason': 'Observed status: ' + record['status'] + '; no comparison or promotion established.'},
        'claim': {'class': 'mechanism_feasibility', 'metric': 'lsa_item_passed',
                  'value': int(status == 'scored'), 'unit': 'items', 'direction': 'higher_better',
                  'category': 'CANDIDATE', 'protocol_id': '',
                  'text': 'One LSA diagnostic item attempted; value records whether the item passed, with no promotion claim.',
                  'reps_basis': 'one attempted item; failed and invalid attempts remain in denominator'},
        'profile': {'kind': 'lsa_item', 'original_record': original, 'producer_source': runner,
                    'model_file': json.loads(manifest_path.read_bytes())['model'],
                    'model_sha256': json.loads(manifest_path.read_bytes())['model_sha256']},
    }
    receipt_path = output_path.with_name(output_path.name + '.research-screen.json')
    screen.write_receipt(receipt_path, body)
    return receipt_path
