#!/usr/bin/env python3
"""compare_corr.py <ref_label> <label> ...  : per text, compare pcm_sha, wav_sha, codes sha and every dump file sha vs the ref."""
import json,sys,pathlib
T=pathlib.Path('/mnt/raid0/llm/tmp/qwentts_threadpool_20261020/corr')
def load(l):
    p=T/l/'results.jsonl'
    return {json.loads(x)['id']:json.loads(x) for x in open(p)} if p.exists() else {}
ref=sys.argv[1]; R=load(ref)
for l in sys.argv[2:]:
    L=load(l); n=0; bad=[]
    for i,r in R.items():
        o=L.get(i)
        if not o: continue
        n+=1
        diffs=[]
        for k in ('rc','pcm_sha','wav_sha','codes_sha','dump_sha'):
            if r[k]!=o[k]: diffs.append(k if k!='dump_sha' else 'dump:'+','.join(f for f in r[k] if r[k][f]!=o[k].get(f)))
        if diffs: bad.append((i,diffs))
    print(f'{l} vs {ref}: compared {n}/{len(R)} texts, identical={n-len(bad)}, mismatches={bad}')
