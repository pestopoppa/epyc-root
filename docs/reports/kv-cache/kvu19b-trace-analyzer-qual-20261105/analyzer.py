#!/usr/bin/env python3
"""Synthetic-only phase verifier. Supplied clock bounds are not established here."""
import json, sys

def pair(x):
    if not isinstance(x,list) or len(x)!=2 or any(type(v) is not int or v<0 for v in x) or x[0]>=x[1]: raise ValueError('invalid interval')
    return x

def analyze(d):
    ident=d['identity']
    if not isinstance(ident,dict) or set(ident)!={'pid','birth','device','queue','profiler'} or any(not isinstance(v,str) or not v for v in ident.values()): raise ValueError('identity')
    if d['offset_scope']!='synthetic-assumption-only': raise ValueError('offset authority')
    bounds=d['offset_ns']
    if not isinstance(bounds,list) or len(bounds)!=2 or any(type(x) is not int for x in bounds) or bounds[0]>bounds[1]: raise ValueError('offset bounds')
    lo,hi=bounds; window=pair(d['host_window_ns']); phases=d['phases']; parsed=[]
    if not isinstance(phases,list) or not phases: raise ValueError('no phases')
    for p in phases:
        a,b=pair(p['host_ns']); name=p['id']
        if not isinstance(name,str) or not name or any(q[0]==name for q in parsed): raise ValueError('phase id')
        if parsed and a<parsed[-1][2]: raise ValueError('phase overlap/order')
        parsed.append((name,a,b))
    if parsed[0][1]<window[0] or parsed[-1][2]>window[1]: raise ValueError('phase window')
    rows=d['witnesses']
    if not isinstance(rows,list) or len(rows)!=3: raise ValueError('witness count')
    last=-1
    for w,expected in zip(rows,('edge_start','interior','edge_end')):
        if w['name']!=expected or w['identity']!=ident: raise ValueError('witness binding')
        a,b=pair(w['host_ns']); c,e=pair(w['trace_ns'])
        if not (window[0]<=a<b<=window[1]) or a<=last: raise ValueError('witness order/window')
        if c+lo<a or e+hi>b: raise ValueError('witness containment')
        last=b
    if rows[0]['host_ns'][1]>parsed[0][1] or rows[1]['host_ns'][0]<=parsed[0][1] or rows[1]['host_ns'][1]>=parsed[-1][2] or rows[2]['host_ns'][0]<parsed[-1][2]: raise ValueError('witness placement')
    kernels=d['kernels']
    if not isinstance(kernels,list) or not kernels: raise ValueError('missing trace')
    out=[]; ids=set()
    for k in kernels:
        if k['identity']!=ident or not isinstance(k['id'],str) or not k['id'] or k['id'] in ids: raise ValueError('kernel binding')
        ids.add(k['id']); a,b=pair(k['trace_ns']); x,y=a+lo,b+hi
        if x<window[0] or y>window[1]: raise ValueError('trace outside window')
        fits=[name for name,start,end in parsed if start<=x and y<=end]
        out.append({'id':k['id'],'classification':fits[0] if len(fits)==1 else 'AMBIGUOUS','trace_ns':[a,b]})
    counts={p[0]:sum(v['classification']==p[0] for v in out) for p in parsed}
    if not all(counts.values()): raise ValueError('missing phase coverage')
    return {'status':'SYNTHETIC_ONLY','counts':counts,'ambiguous':sum(v['classification']=='AMBIGUOUS' for v in out),'rows':out,'scope':'supplied synthetic bounds only; no clock drift, native alignment or attribution'}

if __name__=='__main__':
    try: print(json.dumps(analyze(json.load(open(sys.argv[1]))),indent=2))
    except (ValueError,KeyError,TypeError,IndexError,OSError) as e:
        print('INVALID: '+str(e),file=sys.stderr); sys.exit(1)
