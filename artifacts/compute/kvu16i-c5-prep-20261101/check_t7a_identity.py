#!/usr/bin/env python3
"""Verify reconstructed row-4c T7A request-body hashes against original arm C.

Offline only: reads prompt mix and historical receipt, sends no requests.
"""
import hashlib
import json
from pathlib import Path

MIX = Path('/mnt/raid0/llm/tmp/inf70/agents/e3-alpha/prompts.json')
HISTORY = Path('/workspace/artifacts/kvu16h-vram-20261004/results/fuc-20261004T110509Z/armC_fix/requests.jsonl')
EXPECTED_MIX_SHA256 = 'ea154096eb110850ab5be5e4f574e995e5dbf17540dcbb9461b8cc38c0855783'
raw = MIX.read_bytes()
if hashlib.sha256(raw).hexdigest() != EXPECTED_MIX_SHA256:
    raise SystemExit('REFUSE: prompt mix hash changed')
mix = json.loads(raw)
if not isinstance(mix, list) or len(mix) != 24 or len({p['id'] for p in mix}) != 24:
    raise SystemExit('REFUSE: expected 24 unique prompts')
old = [json.loads(line) for line in HISTORY.read_text().splitlines() if line.strip()]
old = [r for r in old if r['phase'] == 't7a']
new = []
for p in mix:
    for name, extra in (('dflash2', {}), ('nodraft', {'speculative.n_max': 0})):
        body = {'messages': [{'role': 'user', 'content': p['prompt']}], 'max_tokens': 200,
                'temperature': 0.0, 'cache_prompt': False,
                'chat_template_kwargs': {'enable_thinking': False}, **extra}
        new.append((p['id'] + '|' + name, hashlib.sha256(json.dumps(body).encode()).hexdigest()))
expected = [(r['tag'], r['body_sha256']) for r in old]
if len(old) != 48 or new != expected:
    raise SystemExit('REFUSE: reconstructed T7A does not match historical body hashes and order')
print('PASS: all 48 T7A request body hashes and order match arm C; no server was contacted')
