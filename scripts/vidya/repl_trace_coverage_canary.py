#!/usr/bin/env python3
"""Exercise synthetic trace capture through ingest and real planning context.

This canary deliberately refuses to invent applicability for a coverage claim.
It fails unless the actual consumer presents the captured measurement.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'scripts' / 'vidya'
sys.path[:0] = [str(ROOT), str(HERE)]
import ingest_sources
import loop_beliefs
from scripts.vidya.producers.repl_trace_capture import TraceCapture


class Sync:
    def status(self, *args, **kwargs):
        return {'fresh': True, 'lag_entries': 0, 'index_max_id': 1,
                'synced_max_id': 1, 'last_sync': datetime.now(timezone.utc).isoformat()}

    def sync(self, *args, **kwargs):
        raise AssertionError('unexpected sync')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    now = lambda: datetime.now(timezone.utc).isoformat()
    capture = TraceCapture(out, run_id='synthetic-canary', source_sha256='a' * 64)
    capture.record({'v': 2, 'kind': 'search', 'provenance': 'trace',
                    'session': 'a' * 16, 'ts': now(), 'section': 'h:' + 'a' * 12,
                    'content_digest': 'b' * 64, 'content_chars': 30,
                    'query_digest': 'c' * 64, 'k': 1, 'mode': 'grep',
                    'hits': [['h:' + 'a' * 12, 0, 10]]})
    sidecar = capture.finalize()
    adapter = ingest_sources.SOURCES['repl-trace-coverage'].load()
    claim = adapter.project(adapter.native_rows(sidecar)[0])
    if claim.value != 1 or claim.protocol_id:
        raise RuntimeError('incorrect synthetic projection')
    ledger = out / 'ledger.jsonl'
    as_of = now()
    report = json.loads(subprocess.run(
        [sys.executable, str(HERE / 'cli.py'), '--ledger', str(ledger), '--json',
         'ingest', 'repl-trace-coverage', '--path', str(sidecar), '--as-of', as_of],
        check=True, capture_output=True, text=True).stdout)
    if report['rows_projected'] != 1 or report['refused']:
        raise RuntimeError('synthetic ingest failed')
    alarm = out / 'alarm.yaml'
    alarm.write_text('backend: file\nfile:\n  path: ' + str(out / 'alarm.jsonl') + '\n')
    answer = loop_beliefs.prepare(
        'test.repl_trace_coverage', {'backend': 'cpu', 'model_file': 'synthetic-fixture.gguf'},
        ledger=ledger, index_path=out / 'index.yaml', as_of=as_of, sync_module=Sync(),
        known_good=out / 'known.json', alarm_state=out / 'alarm-state.json',
        alarm_config=alarm, read_log=out / 'reads.jsonl')
    visible = [x for x in answer.get('evidence', {}).get('claims', [])
               if x.get('source_kind') == 'repl-trace-coverage']
    passed = answer['status'] == 'ready' and len(visible) == 1 and visible[0].get('value') == 1
    receipt = {'synthetic': True, 'status': 'passed' if passed else 'failed',
               'scope': 'coverage only; no retrieval quality or real capture',
               'rows_projected': report['rows_projected'], 'planning_status': answer['status'],
               'visible_claims': len(visible), 'planning_evidence': answer.get('evidence', {})}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, default=str) + '\n')
    print(out / 'receipt.json')
    if not passed:
        raise SystemExit('planning-context canary failed: synthetic coverage not visible')


if __name__ == '__main__':
    main()
