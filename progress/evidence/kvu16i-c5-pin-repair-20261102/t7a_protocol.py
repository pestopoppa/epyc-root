#!/usr/bin/env python3
"""Bounded row-4c T7A body reconstruction; this module never launches inference."""
import hashlib
import json
from pathlib import Path

MIX = Path('/mnt/raid0/llm/tmp/inf70/agents/e3-alpha/prompts.json')
HISTORY = Path('/mnt/raid0/llm/tmp/handoff-kvu-16i-c5-20261101/historical-t7a-receipt.jsonl')
MIX_SHA256 = 'ea154096eb110850ab5be5e4f574e995e5dbf17540dcbb9461b8cc38c0855783'
RECEIPT_SHA256 = 'a0d173a619e4953a3aacd61fe1cf741fa3816a10ccff9aaad7b30d50f81afefa'

def verified_t7a_bodies(mix=MIX, receipt=HISTORY):
    raw, oldraw = mix.read_bytes(), receipt.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MIX_SHA256:
        raise ValueError('prompt mix sha256 mismatch')
    if hashlib.sha256(oldraw).hexdigest() != RECEIPT_SHA256:
        raise ValueError('historical receipt sha256 mismatch')
    prompts = json.loads(raw)
    if not isinstance(prompts, list) or len(prompts) != 24 or len({p['id'] for p in prompts}) != 24:
        raise ValueError('expected 24 unique prompt ids')
    old = [json.loads(line) for line in oldraw.splitlines() if line.strip()]
    old = [r for r in old if r['phase'] == 't7a']
    bodies = []
    for p in prompts:
        for name, extra in (('dflash2', {}), ('nodraft', {'speculative.n_max': 0})):
            body = {'messages': [{'role': 'user', 'content': p['prompt']}], 'max_tokens': 200,
                    'temperature': 0.0, 'cache_prompt': False,
                    'chat_template_kwargs': {'enable_thinking': False}, **extra}
            tag = p['id'] + '|' + name
            digest = hashlib.sha256(json.dumps(body).encode()).hexdigest()
            bodies.append((tag, body, digest))
    if len(old) != 48 or [(t, h) for t, _, h in bodies] != [(r['tag'], r['body_sha256']) for r in old]:
        raise ValueError('T7A request body hash/order mismatch')
    return bodies

if __name__ == '__main__':
    print(f'PASS: {len(verified_t7a_bodies())}/48 original T7A request hashes and order')
