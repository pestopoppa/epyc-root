"""Bind the already validated official full summary to the terminal D1 result path."""
import hashlib
import json
import os
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parent
fingerprint = sys.argv[1]
source = root / 'outputs' / f'GATE2-FULL-SUMMARY-{fingerprint}.json'
raw = source.read_bytes(); summary = json.loads(raw)
if summary.get('n_per_arm') != 3671 or summary.get('delta_over_base_ratio') is None:
    raise SystemExit('full official Gate 2 matrix absent')
ratio = float(summary['delta_over_base_ratio'])
if not __import__('math').isfinite(ratio): raise SystemExit('nonfinite Gate 2 ratio')
summary['kind'] = 'epyc.inf12.gate2.full-result.v1'
summary['full_gate_completed'] = True
summary['partial'] = False
summary['source_summary_sha256'] = hashlib.sha256(raw).hexdigest()
summary['predeclared_gate_ratio_range'] = [1.31 * 0.8, 1.31 * 1.2]
summary['predeclared_gate_2_pass'] = 1.31 * 0.8 <= ratio <= 1.31 * 1.2
summary['decision_rule'] = 'MemoryAgentBench official full-matrix delta/base accuracy ratio within ±20% of 1.31× (1.048–1.572 inclusive); higher ratio is better.'
target = root / 'outputs' / 'RESULT.json';tmp=target.with_suffix('.json.tmp.'+str(os.getpid()))
with tmp.open('x') as f:
    json.dump(summary,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
os.replace(tmp,target)
