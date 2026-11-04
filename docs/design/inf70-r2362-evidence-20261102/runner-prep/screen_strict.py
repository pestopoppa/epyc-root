#!/usr/bin/env python3
"""Provisional R23-62 raw-sampler screen. Missing/invalid telemetry is REFUSE."""
import argparse,json,math
from pathlib import Path

def read(path, meta=False):
    lines=Path(path).read_text().splitlines(); out=[]
    for line in lines:
        r=json.loads(line)
        if meta and 'meta' in r: continue
        if not isinstance(r,dict): raise ValueError('sample is not object')
        out.append(r)
    if len(out)<2: raise ValueError('fewer than two samples')
    return out

def numeric(r,k):
    x=r[k]
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x): raise ValueError('bad '+k)
    return x

def screen(foreign,host,start,end):
    if not math.isfinite(start) or not math.isfinite(end) or end<=start: raise ValueError('bad measurement window')
    a=read(foreign,True); b=read(host)
    for samples in (a,b):
        ts=[numeric(r,'t') for r in samples]
        if any(t<start or t>end for t in ts) or any(y<=x for x,y in zip(ts,ts[1:])): raise ValueError('bad sample timestamps')
        if any(y-x>25 for x,y in zip(ts,ts[1:])): raise ValueError('sample gap exceeds 25 seconds')
        if ts[0]-start>25 or end-ts[-1]>25: raise ValueError('window not covered')
    foreign_max=max(numeric(r,'foreign_pct') for r in a)
    busy_max=max(numeric(r,'busy_cores') for r in b)
    pg=[numeric(r,'pgpgin_kb') for r in b]
    if any(x<0 for x in pg) or foreign_max<0 or busy_max<0: raise ValueError('negative sample')
    # No announced-lane subtraction: 184-191 overlaps the benchmark's SMT siblings.
    return {'status':'DIAGNOSTIC_ONLY', 'foreign_max_pct':foreign_max,'host_busy_max':busy_max,'pagein_kb':sum(pg),'foreign_samples':len(a),'host_samples':len(b)}

def main():
    p=argparse.ArgumentParser(); p.add_argument('foreign');p.add_argument('host');p.add_argument('start',type=float);p.add_argument('end',type=float);a=p.parse_args()
    try: result=screen(a.foreign,a.host,a.start,a.end)
    except (ValueError,KeyError,OSError,TypeError) as e: result={'status':'REFUSE','reason':str(e)}
    print(json.dumps(result)); return 2  # This provisional screen never grants permission to measure.
if __name__=='__main__': raise SystemExit(main())
