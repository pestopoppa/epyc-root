#!/usr/bin/env python3
"""Read retained private server and canonical native logs for this frozen cohort."""
import json
from pathlib import Path

D = Path(__file__).resolve().parent
out = D / 'out'
assessment = out / 'ASSESSMENT.json'
if assessment.exists():
    a = json.loads(assessment.read_text())
    print('assessment', a.get('state'), 'partial', a.get('partial'),
          'complete', a.get('complete'), 'unknown', a.get('exposed_incomplete_unknown'),
          'unexposed', a.get('unexposed'))
manifest = out / 'native' / 'manifest.json'
if manifest.exists():
    m = json.loads(manifest.read_text())
    print('native', m.get('verdict'), m.get('join'), 'runs', len(m.get('runs', [])))
    for r in m.get('runs', []):
        print(r.get('run_id'), r.get('pass'), r.get('error'))
ledger = out / 'native-attempts.jsonl'
if ledger.exists():
    print('native_ledger_lines', len(ledger.read_text().splitlines()))
server = out / 'server.log'
if server.exists():
    lines = server.read_text(errors='replace').splitlines()
    print('server_log_lines', len(lines), 'tail', lines[-8:])
