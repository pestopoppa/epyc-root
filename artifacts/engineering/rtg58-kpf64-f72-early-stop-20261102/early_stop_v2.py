#!/usr/bin/env python3
import hashlib,json,os,random,signal,sys,time
from pathlib import Path
job=Path('/mnt/raid0/llm/tmp/kv-prefix-fork/kpf64-f72-20261102'); f=Path('/mnt/raid0/llm/tmp/kv-prefix-fork/kpf64-live-f-20261102/out/replay/requests.jsonl'); b=Path('/mnt/raid0/llm/tmp/kv-prefix-fork/kpf64-fb72-20261102/out/replay/requests.jsonl'); r=job/'out/replay/requests.jsonl'; driver=1458625
key=lambda x:(x['session'],x['k'])
def family(x): return x.get('parent') or x['session']
def read(p):
 data=p.read_bytes(); complete=data[:data.rfind(b'\n')+1]; return [json.loads(line) for line in complete.splitlines()],complete
def share(xs):
 c=sum(x['cache_n'] for x in xs);t=sum(x['cache_n']+x['prompt_n'] for x in xs);return c/t if t else 0

def evaluate(pairs, expected):
 groups={}
 for x,y in pairs: groups.setdefault(family(x),[]).append((x,y))
 state={'paired_requests':len(pairs),'families':{k:len(v) for k,v in sorted(groups.items())},'decision':'waiting','reason':None}
 if len(pairs)<20: state['reason']='fewer than 20 matched requests'; return state
 if set(groups)!=expected: state['reason']='not all four source families represented'; return state
 base=sum(x['prompt_n']+x['cache_n'] for x,y in pairs)
 if base<=0 or sum(x['cache_n'] for x,y in pairs)<10000: state['reason']='insufficient F24 cached-token denominator'; return state
 drift=sum(abs((x['prompt_n']+x['cache_n'])-(y['prompt_n']+y['cache_n'])) for x,y in pairs)/base; state['prompt_token_abs_drift_fraction']=drift
 if drift>0.02:
  state['reason']='prompt-token drift exceeds 2%';state['decision']='inconclusive_stop' if len(pairs)>=49 else 'waiting';return state
 rng=random.Random(640172);clusters=[groups[k] for k in sorted(groups)]; values=[]
 for _ in range(5000):
  sample=[pair for i in range(4) for pair in rng.choice(clusters)]
  values.append(100*(share([y for x,y in sample])-share([x for x,y in sample])))
 values.sort();lo,hi=values[124],values[4874];state.update({'f24_cached_share':share([x for x,y in pairs]),'f72_cached_share':share([y for x,y in pairs]),'delta_pp':100*(share([y for x,y in pairs])-share([x for x,y in pairs])),'descriptive_family_resample_interval_pp':[lo,hi]})
 state['decision']='broadly_consistent' if lo>=-5 and hi<=5 else ('material_difference' if lo>5 or hi< -5 else 'waiting');state['reason']='exploratory family-resampling interval compared with +/-5pp practical band' if state['decision']!='waiting' else 'interval overlaps practical band boundary';return state

def save(path,obj):
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2)+'\n');os.chmod(tmp,0o600);os.replace(tmp,path)
if '--self-test' in sys.argv:
 def row(fam,idx,c,p): return {'session':fam+'.c','parent':fam,'k':idx,'cache_n':c,'prompt_n':p}
 pairs=[(row(str(i%4),i,1000,1000),row(str(i%4),i,1000,1000)) for i in range(20)]
 assert evaluate(pairs,{'0','1','2','3'})['decision']=='broadly_consistent'
 pairs=[(x,{**y,'cache_n':0,'prompt_n':2000}) for x,y in pairs];assert evaluate(pairs,{'0','1','2','3'})['decision']=='material_difference'
 print('early-stop self-test passed');sys.exit(0)
F,fd=read(f);B,bd=read(b);fm={key(x):x for x in F};target={key(x) for x in B};families={family(fm[k]) for k in target if k in fm}
if len(F)!=len(fm) or len(B)!=len(target) or len(target)!=49 or len(families)!=4: raise SystemExit('unexpected baseline/partial cohort; no stop')
proc=Path(f'/proc/{driver}');birth=proc.joinpath('stat').read_text().split()[21]
while proc.exists():
 try:
  if proc.joinpath('stat').read_text().split()[21]!=birth or b'replay_driver.py' not in proc.joinpath('cmdline').read_bytes(): raise SystemExit('driver identity changed; no signal')
  if not r.exists(): time.sleep(15);continue
  rows,rd=read(r);rm={key(x):x for x in rows}
  if len(rows)!=len(rm): raise ValueError('duplicate F72 request identity')
  keys=sorted(target & rm.keys());keys=sorted(fm.keys() & rm.keys()) if len(keys)>=49 else keys
  pairs=[(fm[k],rm[k]) for k in keys if k in fm];doc=evaluate(pairs,families)
  doc.update({'classification':'exploratory operational stopping; not a gate or formal confidence interval','source_limitations':'nonrandom completion order, only four families, repeated looks; similar token counts do not prove identical histories','baseline_sha256':hashlib.sha256(fd).hexdigest(),'fb_partial_sha256':hashlib.sha256(bd).hexdigest(),'f72_complete_lines_sha256':hashlib.sha256(rd).hexdigest(),'driver_pid':driver,'driver_birth_ticks':birth,'recorded_unix':time.time()})
  save(job/'EARLY_STOP_STATUS.json',doc)
  if doc['decision']!='waiting':
   snap=job/'EARLY_STOP_SNAPSHOT.jsonl';snap.write_bytes(rd);os.chmod(snap,0o600);save(job/'EARLY_STOP_KEYS.json',{'keys':[list(k) for k in keys]});save(job/'EARLY_STOP_DECISION.json',doc);os.kill(driver,signal.SIGTERM);break
 except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as e:
  save(job/'EARLY_STOP_STATUS.json',{'decision':'waiting','reason':f'monitor error: {e}','recorded_unix':time.time()})
 time.sleep(15)
