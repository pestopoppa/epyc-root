#!/usr/bin/env python3 -I
"""GPU-ZOS-2.3 design 9.4 six-pass recompute (analysis only). Usage: sixpass.py [RESPONSE-PROJECTIONS.json]"""
import json,sys,math,itertools
P=sys.argv[1] if len(sys.argv)>1 else '/workspace/artifacts/compute/ni-gpu-zos23-r6-20261031/RESPONSE-PROJECTIONS.json'
d=json.load(open(P))['arms']
R={a:{r['prompt_index']:r for r in d[a]['counted_responses']} for a in d}
for a in R: assert len(R[a])==24
def tps(a,i): return R[a][i]['timings']['predicted_per_second']
def tok(a,i): return R[a][i]['token_sha256']
def g(xs): xs=list(xs); return math.exp(sum(map(math.log,xs))/len(xs))
def pct(xs,q):
    xs=sorted(xs); k=(len(xs)-1)*q; f=int(k); c=min(f+1,len(xs)-1); return xs[f]+(xs[c]-xs[f])*(k-f)
EMIN=0.01; NFCEIL=0.0185
def paired(arms, strict_all=None):
    """prompts whose tokens identical across `arms`"""
    return [i for i in range(24) if len({tok(a,i) for a in arms})==1]
def ratio(num,den,idx): return g(tps(num,i)/tps(den,i) for i in idx)-1
def pairwise_idx(x,y): return paired([x,y])
out={}
A=['A1','A2','A3'];B=['B1','B2','B3']
# token identity / exclusion
allarms=A+B
excl={}
for x,y in itertools.combinations(allarms,2): excl[f'{x}-{y}']=24-len(pairwise_idx(x,y))
out['pairwise_excluded_prompts']=excl
sixidx=paired(allarms); out['excluded_if_identical_in_all_six']=24-len(sixidx)
def verdict(S,NF,alt,excl_frac):
    if excl_frac>0.25: return 'INCONCLUSIVE (>25% prompts excluded)'
    U=0.0371+2*NF
    if S<=-2*NF: return 'REGRESS'
    if NF>NFCEIL: return 'INCONCLUSIVE (still UNDERPOWERED after the one allowed extension)'
    if S>U: return 'SUSPECT'
    if S>=max(EMIN,2*NF): return 'SHIP' if alt else 'NOT-SHIP (alternation fails)'
    if abs(S)<max(EMIN,2*NF): return 'NULL'
    return 'INCONCLUSIVE'
readings={}
def run(name, idxfn, NFfn, altpairs):
    # idxfn(): prompt set for S; pooled per-arm geomeans of the 3 passes
    idx=idxfn
    gm=lambda arms,i: g(tps(a,i) for a in arms)
    S=g(gm(B,i)/gm(A,i) for i in idx)-1
    nf_terms=NFfn(idx)
    NF=max(abs(v) for v in nf_terms.values())
    alt={f'{b}/{a}':ratio(b,a,paired([a,b]) if idx is None else idx) for b,a in altpairs}
    ok=all((v>0)==(S>0) and v!=0 for v in alt.values())
    ex=24-len(idx)
    readings[name]=dict(n_prompts=len(idx),S=S,NF=NF,NF_terms=nf_terms,alt=alt,alt_same_sign=ok,
        U=0.0371+2*NF,E_threshold=max(EMIN,2*NF),verdict=verdict(S,NF,ok,ex/24))
seqalt=[('B1','A1'),('B1','A2'),('B2','A2'),('B2','A3'),('B3','A3')]
consec=lambda idx:{f'{y}/{x}':ratio(y,x,idx) for arm in (A,B) for x,y in zip(arm,arm[1:])}
rng=lambda idx:{f'{y}/{x}':ratio(y,x,idx) for arm in (A,B) for x,y in itertools.combinations(arm,2)}
dev=lambda idx:{f'{a}/pooled_{arm[0][0]}':g(tps(a,i)/g(tps(z,i) for z in arm) for i in idx)-1 for arm in (A,B) for a in arm}
allidx=sixidx
run('R1 consecutive-pass NF (A2/A1,A3/A2,B2/B1,B3/B2), pooled S, all-six-identical prompts',allidx,consec,seqalt)
run('R2 max over all pass pairs NF (incl A3/A1,B3/B1), pooled S',allidx,rng,seqalt)
run('R3 NF = max |pass vs arm-pooled mean|, pooled S',allidx,dev,seqalt)
# R4: two-pass equations on LAST two passes? (A2,A3 / B2,B3 too) and A1/A2 original, for reference
def two(a1,a2,b1,b2,idx):
    S=g(math.sqrt(tps(b1,i)*tps(b2,i))/math.sqrt(tps(a1,i)*tps(a2,i)) for i in idx)-1
    return S,max(abs(ratio(a2,a1,idx)),abs(ratio(b2,b1,idx)))
refs={}
for nm,(a1,a2,b1,b2) in {'orig A1A2/B1B2':('A1','A2','B1','B2'),'A2A3/B2B3':('A2','A3','B2','B3'),'A1A3/B1B3':('A1','A3','B1','B3')}.items():
    idx=paired([a1,a2,b1,b2]);S,NF=two(a1,a2,b1,b2,idx);refs[nm]=dict(n=len(idx),S=S,NF=NF)
out['two_pass_reference']=refs
out['readings']=readings
# per-arm summary
out['arm_geomean_tps']={a:g(tps(a,i) for i in range(24)) for a in allarms}
print(json.dumps(out,indent=1))
