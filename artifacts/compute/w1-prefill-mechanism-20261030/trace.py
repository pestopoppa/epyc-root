#!/usr/bin/env python3
"""Zero-inference check of the frozen W1 inputs and pre-generation slot filling."""
import itertools, json
from pathlib import Path
root = Path('/mnt/raid0/llm/tmp/codex-inf75-w1-full-census-20261029/w1')
recipe = json.loads((root/'recipes.json').read_text())['workloads'][0]
req = json.loads((root/'requests-prefill.json').read_text())
argv = recipe['argv']
assert argv[argv.index('-b')+1] == argv[argv.index('-ub')+1] == '512'
assert '--prefill-budget-decoding' not in argv and '--prefill-budget-target-ms' not in argv
assert len(req) == 4 and all(len(r['prompt']) == 1024 and r['cache_prompt'] is False and r['speculative.n_max'] == 0 for r in req)
for order in itertools.permutations(range(4)):
    left = {i: 1024 for i in order}
    batches = []
    while any(left.values()):
        room, counts = 512, {}
        for i in order:
            n = min(room, left[i]); left[i] -= n; room -= n
            if n: counts[i] = n
            if room == 0: break
        batches.append(counts)
    assert len(batches) == 8 and all(len(b) == 1 and next(iter(b.values())) == 512 for b in batches)
print('24/24 slot orders: prompt-only fill produces eight single-sequence 512 batches; actual generation can start after each slot completes.')
print('Later all-four API batches must include a generating sequence; its one sampled token prevents a 512-token equal-sequence native ubatch.')
