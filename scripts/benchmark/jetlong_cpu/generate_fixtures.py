#!/usr/bin/env python3
"""Draft token-ID fixture generator; requires scientific review before sealing.

Direct token concatenation deliberately avoids retokenization and preserves the
length and insertion index. Model/tokenizer provenance must be pinned separately.
"""
import argparse
import hashlib
import json
import os
import random
import subprocess
from pathlib import Path

FACTS = [
 ('the blue heron ledger', 'cobalt teapot'),
 ('the silver badger ledger', 'amber compass'),
 ('the quiet otter ledger', 'violet lantern'),
 ('the golden lark ledger', 'jade telescope'),
 ('the striped marten ledger', 'crimson umbrella'),
]
SEEDS = (1701, 1702, 1703)
DEPTHS = (10, 30, 50, 70, 90)

def digest(data): return hashlib.sha256(data).hexdigest()

def coordinate(depth, needle_index, seed_index):
    if depth not in DEPTHS or needle_index not in range(5) or seed_index not in range(3):
        raise ValueError('invalid matrix coordinate')
    return {'depth_percent': depth, 'depth_fraction': depth / 100,
            'needle_index': needle_index, 'seed_index': seed_index}

def assemble(haystack, prefix, needle, suffix, length, depth, seed):
    if not haystack or depth not in DEPTHS or length <= 0:
        raise ValueError('invalid fixture configuration')
    start = length * depth // 100
    filler_len = length - len(prefix) - len(needle) - len(suffix)
    before = start - len(prefix)
    if filler_len < 0 or not 0 <= before <= filler_len:
        raise ValueError('framing does not fit at requested depth')
    # Seed chooses a reproducible circular offset in a single pinned corpus.
    off = random.Random(seed).randrange(len(haystack))
    repeats = (off + filler_len + len(haystack) - 1) // len(haystack)
    filler = (haystack * repeats)[off:off + filler_len]
    ids = prefix + filler[:before] + needle + filler[before:] + suffix
    if len(ids) != length or ids[start:start+len(needle)] != needle:
        raise AssertionError('bad fixture geometry')
    return ids, start

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tokenizer', required=True)
    ap.add_argument('--library-dir', required=True)
    ap.add_argument('--model', required=True)
    ap.add_argument('--inventory', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, LD_LIBRARY_PATH=args.library_dir)
    def tokenize(text):
        import struct
        proc = subprocess.run([args.tokenizer,args.model],input=text.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,check=True)
        if len(proc.stdout) % 4: raise ValueError('non-int32 tokenizer output')
        return list(struct.unpack('<'+'i'*(len(proc.stdout)//4),proc.stdout))
    inv=json.loads(Path(args.inventory).read_text())
    texts=[]
    for entry in inv['haystack_files']:
        b=Path(entry['path']).read_bytes()
        if digest(b) != entry['sha256']: raise ValueError('haystack digest changed')
        texts.append(b.decode('utf-8'))
    haystack=tokenize('\n\n'.join(texts))
    prefix=tokenize('Read the following material carefully.\n\n')
    items=[]
    for needle_index, (key,answer) in enumerate(FACTS):
        needle=tokenize(f'\nThe secret entry in {key} is {answer}.\n')
        suffix=tokenize(f'\n\nWhat is the secret entry in {key}? Answer briefly.\n')
        for seed_index, seed in enumerate(SEEDS):
            for depth in DEPTHS:
                for length in (300000,524288):
                    ids,pos=assemble(haystack,prefix,needle,suffix,length,depth,seed)
                    item_id=f'l{length}-d{depth}-n{FACTS.index((key,answer))}-s{seed}'
                    raw=(json.dumps(ids,separators=(',',':'))+'\n').encode()
                    path=output/(item_id+'.json')
                    path.write_bytes(raw)
                    items.append({'id':item_id,'expected':answer,'length':length,**coordinate(depth, needle_index, seed_index),'needle_start_token':pos,'needle_tokens':len(needle),'seed':seed,'tokens_path':path.name,'tokens_sha256':digest(raw)})
    plan={'status':'DRAFT_NOT_SEALED','items':items,'caveats':['token-concatenated prompt; differs from original character-based adapter','seeds and five needle texts defined by this draft','no automatic BOS or chat-template framing; validate against served endpoint before use']}
    (output/'plan.json').write_text(json.dumps(plan,sort_keys=True,indent=2)+'\n')
    print(f'wrote {len(items)} draft fixtures to {output}')
if __name__ == '__main__': main()
