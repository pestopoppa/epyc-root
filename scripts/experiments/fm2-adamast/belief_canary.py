#!/usr/bin/env python3
"""Verify an actual prospective FM-2 receipt in the scoped planning reader."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'scripts/vidya'), str(ROOT)]
import ingest_sources
import loop_beliefs
from adapters import fm2_adamast as adapter
from ledger import Ledger
from scripts.coordination import alarm_channel

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--receipt', required=True, type=Path)
p.add_argument('--scratch', required=True, type=Path)
a = p.parse_args()
scratch = a.scratch.resolve()
if not scratch.is_relative_to(Path('/mnt/raid0/llm/tmp')):
    p.error('scratch must be under /mnt/raid0/llm/tmp')
scratch.mkdir(parents=True, exist_ok=True)
out = Path(tempfile.mkdtemp(prefix='fm2-context-', dir=scratch))
rows = adapter.native_rows(a.receipt)
if len(rows) != 1:
    raise RuntimeError('native run has no valid diagnosis; UNKNOWN is not a canary pass')
ledger = Ledger(out/'ledger.jsonl')
index = out/'index.yaml'; index.write_text('[]\n')
with ledger.write_lock():
    report = ingest_sources.ingest(ledger, adapter.SOURCE_KIND, [a.receipt], as_of=datetime.now(timezone.utc).isoformat())
if report['refused'] or report['rows_projected'] != 1 or report['frames_emitted'] != 3:
    raise RuntimeError(f'ingestion failed: {report}')
alarm = SimpleNamespace(load_config=lambda _: {'backend':'file','file':{'path':str(out/'alarms.jsonl')}}, raise_alarm=alarm_channel.raise_alarm, clear_alarm=alarm_channel.clear_alarm)
def prepare(consumer):
    answer = loop_beliefs.prepare(consumer, {'scope':'lineup','stack_regime':'fm2'}, ledger=ledger.path,
        index_path=index, known_good=out/(consumer+'.json'), read_log=out/'reads.jsonl',
        alarm_state=out/'alarm-state.json', alarm_config=out/'alarms.jsonl', alarm_api=alarm)
    if answer['status'] != 'ready': raise RuntimeError(str(answer))
    return answer
answer=prepare(adapter.CONSUMER); e=answer['evidence']
claims=[c for c in e['claims'] if c.get('source_kind') == adapter.SOURCE_KIND]
native = rows[0]
expected = {'claim_id': f"clm_{adapter.SOURCE_KIND}:{native['sha256']}",
            'locator': native['path'], 'value': len(native['codes']), 'unit': 'assigned_codes',
            'grade': 'Judged/Located', 'tier': 'harness', 'not_evidence': True}
if (adapter.native_rows(a.receipt) != rows or len(claims) != 1
    or any(claims[0].get(k) != v for k,v in expected.items())
    or expected['claim_id'] in e['claim_ids'] or expected['claim_id'] not in e['section']
    or adapter.LIMIT not in e['section']):
    raise RuntimeError('FM-2 exact native diagnostic missing or improperly promoted')
other=prepare('autokernel.planner')
if any(c.get('source_kind')==adapter.SOURCE_KIND for c in other['evidence']['claims']):
    raise RuntimeError('FM-2 leaked to unrelated consumer')
receipt={'schema':'epyc.fm2.planning-canary.v1','status':'passed','consumer':adapter.CONSUMER,
         'native_receipt_sha256':hashlib.sha256(a.receipt.read_bytes()).hexdigest(),
         'claim_id':claims[0]['claim_id'],'grade':claims[0]['grade'], 'tier':claims[0]['tier'],
         'unrelated_consumer_excluded':True,'ledger_state_digest':answer['ledger_state_digest'],
         'scope':adapter.LIMIT}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(out/'receipt.json')
