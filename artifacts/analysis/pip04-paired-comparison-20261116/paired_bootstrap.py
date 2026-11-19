#!/usr/bin/env python3
"""PIP-04 PARSER-PAIRED-COMPARISON: paired per-document bootstrap. Zero inference."""
import json, itertools, random, hashlib, sys
T='/mnt/raid0/llm/tmp/'; A='/mnt/raid0/llm/archives/pip04-odl013-r2-20261107/run/prediction/'
SRC={'docling':T+'parser-docling-200pdf-20261109/out/evaluation-final.json',
 'lighton':T+'parser-lighton-200pdf-20261109/out/evaluation-final.json',
 'odl_hybrid':T+'parser-odl-hybrid-200pdf-r2-20261109/out/evaluation-final.json',
 'liteparse':A+'liteparse/evaluation.json','odl_local':A+'opendataloader/evaluation.json',
 'pdftotext':A+'pdftotext/evaluation.json'}
B=10000; SEED=20261116
def load(p):
    d=json.load(open(p)); out={}
    for x in d['documents']:
        out[x['document_id']]=x['scores'] if x.get('prediction_available',True) else {}
    return out,d['metrics']['score']
arms={};reported={}
for k,p in SRC.items(): arms[k],reported[k]=load(p)
ids=sorted(set.intersection(*[set(a) for a in arms.values()]))
def pct(v,q):
    v=sorted(v); i=q*(len(v)-1); lo=int(i); hi=min(lo+1,len(v)-1); return v[lo]+(v[hi]-v[lo])*(i-lo)
def paired(a,b,m,docs):
    d=[(arms[a][i].get(m),arms[b][i].get(m)) for i in docs]
    d=[(x,y) for x,y in d if x is not None and y is not None]
    n=len(d); diffs=[x-y for x,y in d]
    if n==0: return None
    rng=random.Random(SEED); means=[]
    for _ in range(B):
        s=0.0
        for _ in range(n): s+=diffs[rng.randrange(n)]
        means.append(s/n)
    mean=sum(diffs)/n; lo,hi=pct(means,.025),pct(means,.975)
    return dict(a=a,b=b,metric=m,n=n,mean_diff=round(mean,4),ci95=[round(lo,4),round(hi,4)],
      excludes_zero=(lo>0 or hi<0),wins_a=sum(x>y for x,y in d),wins_b=sum(y>x for x,y in d),ties=sum(x==y for x,y in d))
res=[]
ids200=sorted(set.intersection(*[set(arms[k]) for k in arms if k!='odl_hybrid']))
sets={'common_199_all_arms':ids,'full_200_excl_odl_hybrid':ids200}
for sn,docs in sets.items():
    for a,b in itertools.combinations(arms,2):
        if sn.startswith('full') and 'odl_hybrid' in (a,b): continue
        for m in ('overall','nid','teds','mhs'):
            r=paired(a,b,m,docs)
            if r: r['docset']=sn; res.append(r)
# sanity: recomputed means vs reported
san={k:round(sum(arms[k][i]['overall'] for i in ids if arms[k][i].get('overall') is not None)/len(ids),4) for k in arms}
out=dict(question='paired per-doc overall/nid/teds/mhs difference with CI95 across finished parser arms',
 method=f'paired percentile bootstrap over documents, B={B}, seed={SEED}; diff = a minus b, higher=better; teds/mhs paired only where both arms have the metric',
 sources=SRC,n_common_docs=len(ids),missing_per_arm={k:200-sum(1 for i in arms[k] if arms[k][i]) for k in arms},
 reported_overall={k:reported[k]['overall_mean'] for k in arms},recomputed_overall_on_common=san,
 marker='withheld per handoff (one-document scoring defect unfixed)',results=res)
json.dump(out,open(T+'pip04-paired-comparison-20261116/paired_bootstrap.json','w'),indent=1)
print(out['n_common_docs'],out['missing_per_arm'],san)
for r in res:
    if r['metric']=='overall': print(r['docset'],r['a'],'-',r['b'],r['n'],r['mean_diff'],r['ci95'],'SIG' if r['excludes_zero'] else '')
