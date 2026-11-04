#!/usr/bin/env python3
import hashlib,json,os,random,signal,sys,time
from pathlib import Path
job=Path('/mnt/raid0/llm/tmp/kv-prefix-fork/kpf64-f72-20261102')
f=Path('/mnt/raid0/llm/tmp/kv-prefix-fork/kpf64-live-f-20261102/out/replay/requests.jsonl')
b=Path('/mnt/raid0/llm/tmp/kv-prefix-fork/kpf64-fb72-20261102/out/replay/requests.jsonl')
r=job/'out/replay/requests.jsonl'; driver=1458625
key=lambda x:(x['session'],x['k'])
def read(p):
 data=p.read_bytes(); lines=data.splitlines(keepends=True); rows=[]
 for line in lines:
  if not line.endswith(b'\n'): break
  rows.append(json.loads(line))
 return rows,data
def family(x): return x.get('parent') or x['session']
def share(xs):
 c=sum(x['cache_n'] for x in xs); t=sum(x['cache_n']+x['prompt_n'] for x in xs)
 return c/t if t else 0
F,fd=read(f); B,bd=read(b); fm={key(x):x for x in F}; target={key(x) for x in B}; families={family(fm[k]) for k in target if k in fm}
if len(F)!=len(fm) or len(B)!=len(target) or len(target)!=49 or len(families)!=4: raise SystemExit('unexpected baseline/partial cohort; no stop')
proc=Path(f'/proc/{driver}'); birth=proc.joinpath('stat').read_text().split()[21]
while proc.exists():
 try:
  if proc.joinpath('stat').read_text().split()[21]!=birth or b'replay_driver.py' not in proc.joinpath('cmdline').read_bytes(): raise SystemExit('driver identity changed; no signal')
  if not r.exists(): time.sleep(15); continue
  rows,rd=read(r); rm={key(x):x for x in rows}
  if len(rows)!=len(rm): raise ValueError('duplicate F72 request identity')
  pairs=[(fm[k],rm[k]) for k in target & rm.keys() if k in fm]
  if len(pairs)>=49: pairs=[(fm[k],rm[k]) for k in fm.keys() & rm.keys()]
  groups={}
  for x,y in pairs: groups.setdefault(family(x),[]).append((x,y))
  if len(pairs)<20 or set(groups)!=families: time.sleep(15); continue
  base=sum(x['prompt_n']+x['cache_n'] for x,y in pairs); drift=sum(abs((x['prompt_n']+x['cache_n'])-(y['prompt_n']+y['cache_n'])) for x,y in pairs)/base
  if drift>0.02 or sum(x['cache_n'] for x,y in pairs)<10000: time.sleep(15); continue
  rng=random.Random(640172); cluster=list(groups.values()); values=[]
  for _ in range(5000):
   sample=[pair for i in range(4) for pair in rng.choice(cluster)]
   values.append(100*(share([y for x,y in sample])-share([x for x,y in sample])))
  values.sort();lo,hi=values[124],values[4874];delta=100*(share([y for x,y in pairs])-share([x for x,y in pairs]))
  result='broadly_consistent' if lo>=-5 and hi<=5 else ('material_difference' if lo>5 or hi< -5 else 'inconclusive')
  doc={'classification':'exploratory early stopping, not a gate or formal confidence interval','paired_requests':len(pairs),'families':{k:len(v) for k,v in groups.items()},'f24_cached_share':share([x for x,y in pairs]),'f72_cached_share':share([y for x,y in pairs]),'delta_pp':delta,'descriptive_family_resample_interval_pp':[lo,hi],'prompt_token_abs_drift_fraction':drift,'decision':result,'baseline_sha256':hashlib.sha256(fd).hexdigest(),'fb_partial_sha256':hashlib.sha256(bd).hexdigest(),'f72_snapshot_sha256':hashlib.sha256(rd).hexdigest(),'driver_pid':driver,'driver_birth_ticks':birth,'recorded_unix':time.time()}
  tmp=job/'EARLY_STOP_STATUS.json.tmp'; tmp.write_text(json.dumps(doc,indent=2)+'\n');os.replace(tmp,job/'EARLY_STOP_STATUS.json')
  if result!='inconclusive':
   (job/'EARLY_STOP_DECISION.json').write_text(json.dumps(doc,indent=2)+'\n')
   os.kill(driver,signal.SIGTERM);break
 except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as e:
  (job/'EARLY_STOP_MONITOR_ERROR.txt').write_text(str(e)+'\n')
 time.sleep(15)
