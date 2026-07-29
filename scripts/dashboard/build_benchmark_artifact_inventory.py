#!/usr/bin/env python3
"""Index saved benchmark JSON by explicit model path; never infer from roles."""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = Path('/mnt/raid0/llm/epyc-inference-research/artifacts')
MODELS = ROOT / 'data/benchmark_model_inventory.json'
OUTPUT = ROOT / 'data/benchmark_artifact_inventory.json'

def model_path(d):
    if isinstance(d.get('model'), dict): return d['model'].get('path')
    if isinstance(d.get('meta'), dict): return d['meta'].get('models')
    for row in d.get('rows', []) if isinstance(d.get('rows'), list) else []:
        if isinstance(row, dict) and isinstance(row.get('response'), dict):
            if row['response'].get('model'): return row['response']['model']

models = {m['path']: m for m in json.loads(MODELS.read_text())['models'] if m.get('path')}
matched, unmatched = defaultdict(list), []
for path in sorted(ARTIFACTS.rglob('*.json')):
    try: d = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError): continue
    if not isinstance(d, dict): continue
    meta = d.get('meta') if isinstance(d.get('meta'), dict) else {}
    item = {'path': str(path.relative_to(ARTIFACTS)), 'model_path': model_path(d),
            'kernel': meta.get('kernel'), 'timestamp': meta.get('timestamp'),
            'grade': d.get('status', 'observation_only_unclassified'),
            'suites': d.get('suites', []) if isinstance(d.get('suites'), list) else []}
    (matched[item['model_path']] if item['model_path'] in models else unmatched).append(item)
out = {'schema_version': 'benchmark_artifact_inventory.v1', 'generated_at': datetime.now(timezone.utc).isoformat(),
       'models': [{'model': models[p]['model'], 'quant': models[p]['quant'], 'path': p, 'artifacts': a} for p,a in matched.items()],
       'unmatched_artifacts': unmatched, 'counts': {'matched_models': len(matched), 'matched_artifacts': sum(map(len, matched.values())), 'unmatched_artifacts': len(unmatched)}}
OUTPUT.write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out['counts']))
