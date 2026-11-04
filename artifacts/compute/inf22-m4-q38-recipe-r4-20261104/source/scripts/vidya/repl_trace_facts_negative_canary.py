#!/usr/bin/env python3
"""Synthetic negative canary for unscoped prospective trace facts.

A passing negative control proves the planner refused to present this synthetic
unscoped claim. It does not mean the source is wired: only a positive canary
with producer-declared, truthful applicability can establish that.
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
import loop_beliefs  # noqa: E402
from repl_trace_coverage_canary import Sync  # noqa: E402
from scripts.vidya.producers.repl_trace_capture import TraceCapture  # noqa: E402


def run_canary(out: Path) -> dict:
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    now = lambda: datetime.now(timezone.utc).isoformat()
    capture = TraceCapture(out, run_id='synthetic-facts-canary', source_sha256='a' * 64)
    capture.record({'v': 2, 'kind': 'search', 'provenance': 'trace',
                    'session': 'a' * 16, 'ts': now(), 'section': 'h:' + 'a' * 12,
                    'content_digest': 'b' * 64, 'content_chars': 30,
                    'query_digest': 'c' * 64, 'k': 1, 'mode': 'grep',
                    'hits': [['h:' + 'a' * 12, 0, 10]]})
    sidecar = capture.finalize()
    ledger = out / 'ledger.jsonl'
    as_of = now()
    proc = subprocess.run([sys.executable, str(HERE / 'cli.py'), '--ledger', str(ledger),
                           '--json', 'ingest', 'repl-trace-facts', '--path', str(sidecar),
                           '--as-of', as_of], capture_output=True, text=True, check=True)
    report = json.loads(proc.stdout)
    if report['rows_projected'] != 1 or report['refused']:
        raise RuntimeError('synthetic trace fact ingest failed')
    alarm = out / 'alarm.yaml'
    alarm.write_text('backend: file\nfile:\n  path: ' + str(out / 'alarm.jsonl') + '\n')
    answer = loop_beliefs.prepare(
        'test.repl_trace_facts_negative', {'backend': 'cpu', 'model_file': 'synthetic-fixture.gguf'},
        ledger=ledger, index_path=out / 'index.yaml', as_of=as_of, sync_module=Sync(),
        known_good=out / 'known.json', alarm_state=out / 'alarm-state.json',
        alarm_config=alarm, read_log=out / 'reads.jsonl')
    evidence = answer.get('evidence', {})
    passed = (answer.get('status') == 'ready' and evidence.get('status') == 'omitted'
              and evidence.get('reasons') == ['no_applicable_claims']
              and not evidence.get('claims') and not evidence.get('claim_ids'))
    receipt = {'synthetic': True, 'negative_control': 'passed' if passed else 'failed',
               'wired': False, 'reason': 'no native applicability; positive canary not passed',
               'rows_projected': report['rows_projected'], 'planning_status': answer.get('status'),
               'evidence_status': evidence.get('status'), 'evidence_reasons': evidence.get('reasons'),
               'visible_claims': len(evidence.get('claims', []))}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    if not passed:
        raise RuntimeError('negative canary failed: planner did not omit the unscoped claim')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    receipt = run_canary(parser.parse_args().out)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
