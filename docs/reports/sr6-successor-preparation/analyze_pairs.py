#!/usr/bin/env python3
"""SR-6 paired analysis draft; never a verdict or a grant-time launcher.

Input contains one response per arm for each (window, prompt_id), including
an A/A repeat. This model-free analysis fails closed on missing matching metadata,
invalid or unequal generated token sequences, and incomplete independent windows.
Runtime, residency and exposure checks remain external prerequisites.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

ARMS = ('composed3', 'composed4', 'mtp3', 'mtp4', 'mtp4_repeat')
MATCH = ('prompt_sha256', 'rendered_sha256', 'sampler_sha256', 'seed', 'class')

def analyze(rows):
    groups = defaultdict(dict)
    errors = []
    for r in rows:
        try:
            key = (r['window'], r['prompt_id'])
            arm = r['arm']
            if arm not in ARMS or arm in groups[key]:
                raise ValueError('unknown or duplicate arm')
            if r.get('status') != 'complete' or r.get('predicted_n', 0) <= 0 or r.get('predicted_ms', 0) <= 0:
                raise ValueError('invalid or incomplete response')
            if not r.get('output_tokens_sha256') or any(r.get(k) is None for k in MATCH):
                raise ValueError('missing matching evidence')
            groups[key][arm] = r
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(str(exc))
    if len({k[0] for k in groups}) < 3:
        errors.append('fewer than three independent windows')
    results = []
    for key, arms in sorted(groups.items(), key=lambda x: str(x[0])):
        if set(arms) != set(ARMS):
            errors.append(f'{key}: incomplete arms')
            continue
        baseline = arms['mtp4']
        if any(any(r[k] != baseline[k] for k in MATCH) for r in arms.values()):
            errors.append(f'{key}: mismatched request identity')
            continue
        if any(r['output_tokens_sha256'] != baseline['output_tokens_sha256'] or r['predicted_n'] != baseline['predicted_n'] for r in arms.values()):
            errors.append(f'{key}: generated work differs')
            continue
        speeds = {a: 1000 * arms[a]['predicted_n'] / arms[a]['predicted_ms'] for a in ARMS}
        results.append({'window': key[0], 'prompt_id': key[1], 'class': baseline['class'], 'tokens_per_second': speeds,
                        'composed_3_vs_4_pct': 100 * (speeds['composed3'] / speeds['composed4'] - 1),
                        'mtp_3_vs_4_pct': 100 * (speeds['mtp3'] / speeds['mtp4'] - 1),
                        'mtp4_repeat_vs_first_pct': 100 * (speeds['mtp4_repeat'] / speeds['mtp4'] - 1)})
    return {'schema':'sr6.paired-analysis-draft.v1', 'status':'UNKNOWN' if errors else 'DESCRIPTIVE_ONLY',
            'errors':errors, 'groups':results, 'verdict':None,
            'limitations':['No runtime, residency, grant independence, exposure or uncertainty validation',
                           'DESCRIPTIVE_ONLY is not a performance claim or registry authorization']}

def main():
    p=argparse.ArgumentParser(); p.add_argument('input',type=Path); p.add_argument('output',type=Path)
    a=p.parse_args(); doc=json.loads(a.input.read_text()); out=analyze(doc['records'])
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    return 0 if out['status']=='DESCRIPTIVE_ONLY' else 2
if __name__=='__main__': raise SystemExit(main())
