#!/usr/bin/env python3
"""Capture C5 same-model solo/batch diagnostics; never infer causal attribution."""
import json, math, os, pathlib, re, subprocess, sys, time
def parse_output(raw, seqs, n_tokens):
    nodes = re.findall(r'nodes multi-row vs alone-batch-row: compared (\d+), DIFFER (\d+), first=(\S+), shape-skip (\d+), unmatched-name (\d+)', raw)
    logits = re.findall(r'logits multi-row vs alone-batch-row: (IDENTICAL|DIFFER) n_diff=(\d+)/(\d+) max\|d\|=(\S+) argmax (\d+)(==|!=)(\d+)', raw)
    expected = seqs * n_tokens
    if len(nodes) != expected or len(logits) != expected:
        raise ValueError(f'expected {expected} node and logit records; got {len(nodes)} and {len(logits)}')
    if any(int(x[0]) <= 0 for x in nodes):
        raise ValueError('refusing vacuous zero-node comparison')
    if seqs == 1 and (any(int(x[1]) != 0 for x in nodes) or any(x[0] != 'IDENTICAL' for x in logits)):
        raise ValueError('solo control differs')
    return nodes, logits

D = pathlib.Path('/mnt/raid0/llm/tmp/akagg-ch31-rowexact-20261101')
IMAGE = pathlib.Path('/mnt/raid0/llm/kernels/builds/cpu-20261024-c72ec82f5-c5')
MODEL = '/mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf'
phase = 'dryrun' if os.environ.get('FILLER_DRYRUN') == '1' else 'full'
out = D / phase
out.mkdir(exist_ok=False)
stop = pathlib.Path(os.environ['FILLER_STOPFILE'])
deadline = int(os.environ['FILLER_DEADLINE'])
units = D / 'units.jsonl'
env = dict(os.environ, LD_LIBRARY_PATH=str(IMAGE / 'bin'), GGML_IQK='1', GGML_FA_SPLIT_KV='0', GGML_NOHUGEPAGE_PROCESS='1')
for key in ('LD_PRELOAD','GGML_ROWEXACT_N','GGML_FUSED_DECODE_ON','GGML_FUSED_DECODE_OFF'):
    env.pop(key, None)
link = subprocess.run([str(D/'verify_ggml_linkage.sh'), str(IMAGE/'bin/llama-rowexact'), str(IMAGE)], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
(out/'linkage.txt').write_text(link.stdout)
if link.returncode: raise SystemExit('REFUSED: linkage failed')
all_results=[]
for index, seqs in [(0,1),(0,4),(1,4),(2,4),(3,4)]:
    if stop.exists() or time.time() >= deadline: raise SystemExit(75)
    label = 'solo_control' if seqs == 1 else f'four_seq_prompt_{index}'
    n_tokens = 2 if seqs == 1 else 1
    argv = [str(IMAGE/'bin/llama-rowexact'), '-m', MODEL, '-t','24','-n',str(n_tokens),'--prefix','8','--mode','multi','--seqs',str(seqs),'--n-seq-max','4','--prompt',str(index),'--show','1000']
    with (out/f'{label}.out').open('wb') as raw:
        result = subprocess.run(argv, env=env, stdout=raw, stderr=subprocess.STDOUT)
    raw = (out/f'{label}.out').read_text(errors='replace')
    if result.returncode: raise SystemExit(f'REFUSED {label}: rc={result.returncode}')
    try: nodes, logits = parse_output(raw, seqs, n_tokens)
    except ValueError as exc: raise SystemExit(f'REFUSED {label}: {exc}') from exc
    item={'phase':phase,'case':label,'rc':result.returncode,'seqs':seqs,'nodes':nodes,'logits':logits,'raw':str(out/f'{label}.out'),'argv':argv,'claim':'diagnostic only; first difference is not causal attribution'}
    with units.open('a') as f:
        f.write(json.dumps(item,sort_keys=True)+'\n'); f.flush(); os.fsync(f.fileno())
    all_results.append(item)
    if stop.exists(): raise SystemExit(75)
tmp=out/'RESULT.tmp'; tmp.write_text(json.dumps({'state':'COMPLETE_DIAGNOSTIC_ONLY','phase':phase,'cases':all_results},indent=2)+'\n'); tmp.replace(out/'RESULT.json')
