#!/usr/bin/env python3
import json,sys,statistics as st,collections
suite=sys.argv[1] if len(sys.argv)>1 else 'qts'
key='total_ms_frame' if suite=='qts' else 'total_ms'
rows=[json.loads(l) for l in open(f'/mnt/raid0/llm/tmp/qwentts_threadpool_20261020/timing/results_{suite}.jsonl')]
g=collections.OrderedDict()
for r in rows:
    if 'leg' not in r or r.get('variant')=='nb_alone': continue
    k=(r['leg'],r['variant'],r.get('block','main'))
    g.setdefault(k,[]).append(r)
legs=[]
for (leg,var,blk),rs in g.items():
    if leg not in legs: legs.append(leg)
print(f'{suite}: median [min-max] of {key}, n reps; TO = timeouts')
for leg in legs:
    base=None
    for (l,var,blk),rs in g.items():
        if l!=leg: continue
        v=[r[key] for r in rs if r.get(key) is not None and not r['timeout']]
        to=sum(1 for r in rs if r['timeout'])
        if not v: print(f'  {leg:16s} {var:10s}{blk:5s} n=0 TO={to}'); continue
        m=st.median(v)
        if var=='prod' and blk=='main': base=m
        sp=f'  x{base/m:.2f} vs prod' if base and var!='prod' else ''
        print(f'  {leg:16s} {var:10s}{blk:5s} {m:9.1f} [{min(v):.1f}-{max(v):.1f}] n={len(v)} TO={to}{sp}')
