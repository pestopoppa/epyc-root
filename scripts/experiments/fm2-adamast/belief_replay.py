#!/usr/bin/env python3
"""Offline replay of a captured request and reply through its pinned AdaMAST judge."""
import base64
import json
from pathlib import Path
import sys

root, unit = map(Path, sys.argv[1:])
sys.path.insert(0, str(root / 'code'))
from adamast.core.trace_formats import load_trace_bundle
from adamast.judges.contract import SelectionTraceJudge
from adamast.llm.learning_calls import parse_json_object

read = lambda p: json.loads(p.read_bytes())
request = read(unit / 'request.json')
response = read(unit / 'response.json')
body = json.loads(base64.b64decode(request['body_b64'], validate=True))
raw = json.loads(base64.b64decode(response['body_b64'], validate=True))
row = read(unit / 'receipt.json')
payload = parse_json_object(raw['choices'][0]['message']['content'])
if (not isinstance(payload, dict) or type(payload.get('none_apply')) is not bool
        or not isinstance(payload.get('failure_modes'), list)):
    raise ValueError('raw diagnosis has invalid field types')
if type(row.get('max_trace_chars')) is not int or row['max_trace_chars'] != 12000:
    raise ValueError('unexpected trace truncation')
if body.get('max_completion_tokens') != row.get('max_output_tokens') or row.get('max_output_tokens') != 1536:
    raise ValueError('unexpected output cap')
trace = load_trace_bundle(root / 'inputs/traces' / (row['unit_id'] + '.jsonl')).traces[0]
class Provider:
    model = 'local-fm2'
    def complete(self, prompt, *, response_format):
        if body['messages'] != [{'role': 'user', 'content': prompt}] or response_format != 'json':
            raise ValueError('captured request differs from native trace/taxonomy prompt')
        return raw['choices'][0]['message']['content']
judge = SelectionTraceJudge(root / 'code/adamast/core/mast.json', Provider(),
                            max_trace_chars=row['max_trace_chars'], max_retries=0)
result = judge.judge(trace).to_dict()
recorded = read(unit/'diagnosis.json')['diagnoses'][0]
# AdaMAST creates this timestamp during parsing; the remaining native metadata
# and the complete multilabel payload must be identical to replay.
for data in (result, recorded):
    meta = data['judge_metadata']
    if type(meta.get('created_at')) is not int:
        raise ValueError('invalid native judge timestamp')
    del meta['created_at']
if type(recorded['none_apply']) is not bool or result != recorded or result['judge_metadata']['warnings']:
    raise ValueError('recorded diagnosis differs from native replay')
print(json.dumps(result, sort_keys=True))
