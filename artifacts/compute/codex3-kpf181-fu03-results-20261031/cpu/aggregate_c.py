#!/usr/bin/env python3
"""Aggregate split KPF-18.1 C native records on their common original floor.

No measurement is created here. A missing, partial, duplicate or incompatible
cell makes the grid unjudgeable. Inputs remain separate native observations.
"""
import json,sys,math
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D/'scripts/benchmark/kpf18'))
from kpf18_arms import eval_181_C

def aggregate(records,expected):
 out={}
 for enabled in (True,False):
  rows=[r for r in records if r.get('arm')==('C_length_sweep_drafter_on' if enabled else 'C_length_sweep_drafter_off')]
  cells=[]; floors=[]; seen=[]; problems=[]; identities=set()
  for r in rows:
   identities.add((r.get('binary_sha256'),r.get('prompt_set_sha256'),json.dumps(r.get('argv'),sort_keys=True)))
   if r.get('partial'):problems.append('partial native record')
   ch=[c for c in r.get('cells',[]) if c.get('role')=='child']
   if len(ch)!=1:problems.append('expected exactly one child per split record');continue
   c=ch[0]; cells.append(c);seen.append(c.get('expected'))
   floor=c.get('floor'); vs=c.get('vs_fresh')
   def valid_compare(x):
    return (isinstance(x,dict) and isinstance(x.get('top1'),bool)
            and all(isinstance(x.get(k),(float,int)) and math.isfinite(x[k]) for k in ('maxabs_union','kld','prefix')))
   if not valid_compare(floor) or not valid_compare(vs):problems.append('missing or invalid native comparison')
   else:floors.append(floor)
  if len(identities)!=1 or any(None in (x[0],x[1]) for x in identities):problems.append('missing or unequal binary/prompt/argv identity')
  if sorted(seen,key=lambda x:(x is None,x))!=sorted(expected):problems.append('missing, duplicate, or unexpected lengths')
  if len(set(seen))!=len(seen):problems.append('duplicate length')
  result=eval_181_C(cells,floors) if not problems else None
  out['on' if enabled else 'off']={'expected':expected,'observed':seen,'problems':problems,'result':result}
 return out
if __name__=='__main__':
 records=[json.loads(p.read_text()) for p in (Path(sys.argv[1])/'records').glob('*.json')]
 expected=[int(x) for x in sys.argv[2].split(',')]
 if len(expected)<16 or len(set(expected))!=len(expected):raise SystemExit('need >=16 distinct frozen lengths')
 print(json.dumps(aggregate(records,expected),indent=2))
