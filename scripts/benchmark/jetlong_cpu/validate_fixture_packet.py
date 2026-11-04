#!/usr/bin/env python3
"""Verify draft fixture contents against the exact generator snapshot."""
import hashlib, importlib.util, json, os, struct, subprocess, sys
from pathlib import Path
import aggregate

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('generator_snapshot', BASE / 'generate-v2.snapshot.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)

def tokenize(text):
    env = dict(os.environ, LD_LIBRARY_PATH='/mnt/raid0/llm/worktrees/llama-jetlong-hip-20261006/build-cpu/bin')
    proc = subprocess.run([str(BASE/'tokenize_vocab'), '/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf'], input=text.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=True)
    if len(proc.stdout) % 4: raise ValueError('invalid tokenizer output')
    return list(struct.unpack('<'+'i'*(len(proc.stdout)//4), proc.stdout))

def validate(root):
    root=Path(root).resolve(strict=True)
    plan=json.loads((root/'plan.json').read_bytes())
    aggregate.validate_matrix(plan,aggregate.load_scorer())
    needles=[tokenize(f'\nThe secret entry in {key} is {answer}.\n') for key, answer in generator.FACTS]
    suffixes=[tokenize(f'\n\nWhat is the secret entry in {key}? Answer briefly.\n') for key, _ in generator.FACTS]
    prefix=tokenize('Read the following material carefully.\n\n')
    inventory=json.loads((BASE/'input-inventory.DRAFT.json').read_text())
    texts=[]
    for entry in inventory['haystack_files']:
        content=Path(entry['path']).read_bytes()
        if hashlib.sha256(content).hexdigest()!=entry['sha256']:
            raise ValueError('haystack digest mismatch')
        texts.append(content.decode('utf-8'))
    haystack=tokenize('\n\n'.join(texts))
    seen=set()
    for x in plan['items']:
        p=(root/x['tokens_path']).resolve(strict=True)
        if not p.is_relative_to(root): raise ValueError('fixture path escapes root')
        raw=p.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=x['tokens_sha256']: raise ValueError('fixture hash mismatch')
        ids=json.loads(raw); pos=x['needle_start_token']; n=x['needle_index']
        if len(ids)!=x['length'] or pos!=x['length']*x['depth_percent']//100 or x['needle_tokens']!=len(needles[n]): raise ValueError('fixture geometry')
        if ids[:len(prefix)]!=prefix or ids[pos:pos+len(needles[n])]!=needles[n] or ids[-len(suffixes[n]):]!=suffixes[n]: raise ValueError('prompt content mismatch')
        if x['expected']!=generator.FACTS[n][1] or x['seed']!=generator.SEEDS[x['seed_index']] or x['id'] in seen: raise ValueError('fixture identity')
        reconstructed, expected_pos=generator.assemble(haystack,prefix,needles[n],suffixes[n],x['length'],x['depth_percent'],x['seed'])
        if ids!=reconstructed or pos!=expected_pos: raise ValueError('haystack or seeded assembly mismatch')
        if any(type(v) is not int or v<0 for v in ids): raise ValueError('token ID')
        seen.add(x['id'])
    print(f'PASS: {len(seen)} hashed raw token arrays; exact seeded full-prompt reconstruction, geometry, identity and aggregator matrix; server prompt_n unverified')

if __name__ == '__main__': validate(sys.argv[1])
