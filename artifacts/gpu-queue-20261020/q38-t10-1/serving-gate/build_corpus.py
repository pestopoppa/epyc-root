#!/usr/bin/env python3
"""Q38-T10.1 serving-gate corpus builder. Deterministic: same pool + seed -> same JSONL. No model, no compute.
Source: epyc-inference-research/benchmarks/prompts/question_pool.jsonl (local, gold in-row). Writes corpus.jsonl + corpus.sha256."""
import hashlib, json, random, re, sys
from pathlib import Path
POOL = Path('/mnt/raid0/llm/epyc-inference-research/benchmarks/prompts/question_pool.jsonl')
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else '/mnt/raid0/llm/tmp/q38t101-serving-gate')
CONTROL = Path('/mnt/raid0/llm/tmp/gpu-staged-20261020/q38t101_prompts.json')
STAGE2 = Path('/mnt/raid0/llm/tmp/gpu-queue-20261020/df2-17/stage2_rendered_prompts.json')
SEED = 20261020
rng = random.Random(SEED)
control_text = ' '.join(p['prompt'] for p in json.loads(CONTROL.read_text()))
stage2_text = STAGE2.read_text() if STAGE2.exists() else ''
rows = [json.loads(l) for l in POOL.open() if not json.loads(l).get('__pool_metadata__')]
by = {}
for d in rows: by.setdefault(d.get('suite'), []).append(d)

def overlap(d):
    h = d['prompt'][:60]
    return h in control_text or h in stage2_text or h.replace('"', '\\"') in stage2_text

def pick(lst, n, key=None, filt=None):
    c = [d for d in lst if (filt is None or filt(d)) and not overlap(d)]
    c.sort(key=lambda d: d['id'])
    if key: c = sorted(c, key=key)[:max(n * 6, 60)]       # shortlist the most promising, then sample deterministically
    return sorted(rng.sample(c, n), key=lambda d: d['id'])

sel = []
def add(kind, lst, grader_of):
    for d in lst: sel.append((kind, d, grader_of(d)))

# GSM8K numeric: short problems (short solutions) -> fit the cap
math = [d for d in by['math'] if d['id'].startswith('gsm8k_')]
add('gsm8k', pick(math, 24, key=lambda d: len(d['prompt']), filt=lambda d: len(d['prompt']) < 330), lambda d: {'type': 'numeric_answer_tag'})
# multiple choice, letter only
add('mmlu', pick(by['general'], 18, filt=lambda d: len(d['prompt']) < 500), lambda d: {'type': 'mc_letter'})
add('mmlu_pro', pick(by['mmlu_pro'], 10, filt=lambda d: len(d['prompt']) < 700), lambda d: {'type': 'mc_letter'})
# CRUXEval output prediction: short deterministic answers
add('cruxeval', pick(by['cruxeval'], 14, key=lambda d: len(d['prompt']), filt=lambda d: '_output_' in d['id']), lambda d: {'type': 'crux_answer_tag'})
# SimpleQA closed QA, token-F1 >= 0.8 per the pool's own scoring_config
add('simpleqa', pick(by['simpleqa'], 4, filt=lambda d: len(d['prompt']) < 260), lambda d: {'type': 'f1_answer_tag', 'threshold': 0.8})
# IFEval single-instruction with a checker implemented in serving_gate.py
OK = {'change_case:english_lowercase', 'change_case:english_capital', 'startend:end_checker', 'startend:quotation', 'punctuation:no_comma', 'keywords:forbidden_words', 'detectable_format:json_format'}
def ife_ok(d):
    ins = d.get('ifeval_instructions') or []
    if len(ins) != 1 or ins[0] not in OK or len(d['prompt']) > 260: return False
    return not re.search(r'\b(blog|essay|story|article|letter|poem|song|speech|words|paragraph|sentences|resume|rap|lyrics|itinerary|review|proposal|riddle)\b', d['prompt'], re.I)
def ife_grader(d):
    ins = d['ifeval_instructions'][0]; kw = {k: v for k, v in d['ifeval_kwargs'][0].items() if v is not None}
    return {'type': 'ifeval', 'instruction': ins, 'kwargs': kw}
pool_if = [d for d in rows if d['id'].startswith('ifeval_')]
add('ifeval', pick(pool_if, 10, key=lambda d: len(d['prompt']), filt=ife_ok), ife_grader)

out = []
for kind, d, g in sel:
    out.append({'id': f"sg_{kind}_{d['id']}", 'kind': kind, 'source_suite': d['suite'], 'pool_id': d['id'], 'prompt': d['prompt'], 'gold': d.get('expected', ''),
                'grader': g, 'prompt_sha256': hashlib.sha256(d['prompt'].encode()).hexdigest()})
assert len({o['id'] for o in out}) == len(out) == 80, len(out)
data = ''.join(json.dumps(o, sort_keys=True, ensure_ascii=False) + '\n' for o in out)
(OUT / 'corpus.jsonl').write_text(data)
h = hashlib.sha256(data.encode()).hexdigest()
(OUT / 'corpus.sha256').write_text(f'{h}  corpus.jsonl\n')
import collections
print(len(out), h, dict(collections.Counter(o['kind'] for o in out)))
