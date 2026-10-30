#!/usr/bin/env python3
import json,os,signal,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;model=sys.argv[1]
weights={'tiny':'/mnt/raid0/llm/models/whisper-ggml/ggml-tiny.bin','base':'/mnt/raid0/llm/models/whisper-ggml/ggml-base.bin','large-v3-turbo':'/mnt/raid0/llm/models/whisper-ggml/ggml-large-v3-turbo.bin','silero':'/mnt/raid0/llm/models/cs26-lid/silero-lid-lang95-f32.gguf','firered':'/mnt/raid0/llm/models/cs26-lid/firered-lid-q8_0.gguf'}
limits={'tiny':15,'base':15,'large-v3-turbo':60,'silero':7,'firered':37}; assert model in weights
end=float(os.environ['FILLER_END']);stopfile=Path(os.environ['FILLER_STOPFILE']);smoke=os.getenv('CS26_SMOKE')=='1';reserve=90 if smoke else 620;case_limit=70 if smoke else 600
result=D/'results'/model;result.mkdir(parents=True,exist_ok=True)
cores=[]
for cpu in sorted(os.sched_getaffinity(0)):
 if all(cpu%96!=c%96 for c in cores):cores.append(cpu)
cores=cores[:24];assert cores
cases=[json.loads(x) for x in (D/'crops.jsonl').read_text().splitlines()];ids={x['case_id'] for x in cases};assert len(ids)==len(cases)
starts=set();outcomes=set()
for path in result.glob('worker-*.jsonl'):
 for line in path.read_text().splitlines():
  x=json.loads(line);cid=x['case_id'];assert cid in ids
  if x['event']=='started':assert cid not in starts;starts.add(cid)
  elif x['event']=='outcome':assert cid in starts and cid not in outcomes;outcomes.add(cid)
  else:raise ValueError('invalid event')
window=result/f'window-{time.time_ns()}-{os.getpid()}';window.mkdir()
for path in result.glob('worker-*.jsonl.active'):path.rename(window/path.name)
shards=[[] for _ in cores]
for i,x in enumerate(x for x in cases if x['case_id'] not in starts):shards[i%len(cores)].append(x)
assert sum(map(len,shards))==len(cases)-len(starts)
for i,shard in enumerate(shards):(window/f'cases-{i}.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in shard))
stop=False
def handler(s,f):
 global stop
 stop=True
signal.signal(signal.SIGTERM,handler);signal.signal(signal.SIGINT,handler)
children=[];logs=[];env=os.environ.copy();env['CS26_ASSIGNED']='1'
for i,cpu in enumerate(cores):
 if not shards[i] or stop or stopfile.exists() or time.time()+reserve>=end:continue
 log=open(result/f'worker-{i}.log','ab',buffering=0);logs.append(log);output=result/f'worker-{i}.jsonl'
 if model in ('silero','firered'):cmd=[sys.executable,str(D/'crisp_runner.py'),model,weights[model],str(window/f'cases-{i}.jsonl'),str(output)]
 else:cmd=[sys.executable,str(D/'runner.py'),str(D/'liblid.so'),weights[model],str(window/f'cases-{i}.jsonl'),str(output)]
 children.append((i,subprocess.Popen(['taskset','-c',str(cpu)]+cmd,stdout=log,stderr=log,env=env)))
peak=0;reason=None;timed_out=[]
while any(p.poll() is None for _,p in children) and not stop:
 rss=0
 for i,p in children:
  try:rss+=int(Path(f'/proc/{p.pid}/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
  except FileNotFoundError:pass
  marker=result/f'worker-{i}.jsonl.active'
  try:
   a=json.loads(marker.read_text())
   if p.poll() is None and time.time()-a['start']>case_limit:p.terminate();timed_out.append({'worker':i,'case_id':a['case_id']})
  except FileNotFoundError:pass
  except json.JSONDecodeError:pass
 peak=max(peak,rss)
 if rss>limits[model]*1024**3:reason='sampled RSS stop threshold exceeded';break
 time.sleep(.5)
if stop or reason:
 for _,p in children:
  if p.poll() is None:p.terminate()
for _,p in children:
 try:p.wait(timeout=10)
 except subprocess.TimeoutExpired:p.kill();p.wait()
for f in logs:f.close()
starts=set();outcomes=set()
for p in result.glob('worker-*.jsonl'):
 for line in p.read_text().splitlines():
  x=json.loads(line);(starts if x['event']=='started' else outcomes).add(x['case_id'])
unknown=len(starts-outcomes);finished=len(starts)==len(cases) and len(outcomes)==len(cases) and not unknown
summary={'model':model,'cores':cores,'started':len(starts),'outcomes':len(outcomes),'unknown':unknown,'unexposed':len(cases)-len(starts),'sampled_peak_rss_bytes':peak,'co_tenancy':'uncontrolled; concurrent pinned workers','reason':reason,'timed_out_unknown':timed_out,'worker_returncodes':[p.returncode for _,p in children]}
(result/'status.json').write_text(json.dumps(summary,indent=2)+'\n')
if finished:(result/'COMPLETE.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary),flush=True);sys.exit(0 if finished else 75)
