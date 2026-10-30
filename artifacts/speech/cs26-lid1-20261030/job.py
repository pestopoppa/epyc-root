#!/usr/bin/env python3
import json,os,signal,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent; model=sys.argv[1]; assert model in ('tiny','base','large-v3-turbo')
result=D/'results'/model;result.mkdir(parents=True,exist_ok=True)
cores=[]
for cpu in sorted(os.sched_getaffinity(0)):
 if all(cpu%96!=c%96 for c in cores): cores.append(cpu)
assert len(cores)>=2
stop=False
def handler(s,f):
 global stop
 stop=True
signal.signal(signal.SIGTERM,handler);signal.signal(signal.SIGINT,handler)
children=[]; logs=[]
for i,cpu in enumerate(cores[:min(3,len(cores))]):
 log=open(result/f'worker-{i}.log','ab',buffering=0);logs.append(log)
 command=['taskset','-c',str(cpu),sys.executable,str(D/'runner.py'),str(D/'liblid.so'),f'/mnt/raid0/llm/models/whisper-ggml/ggml-{model}.bin',str(D/(f'cases-{i}.jsonl' if len(cores)>=3 else f'cases-two-{i}.jsonl')),str(result/f'worker-{i}.jsonl')]
 children.append(subprocess.Popen(command,stdout=log,stderr=log))
peak=0;reason=None
while any(p.poll() is None for p in children) and not stop:
 rss=0
 for p in children:
  try: rss+=int(Path(f'/proc/{p.pid}/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
  except FileNotFoundError: pass
 peak=max(peak,rss)
 if rss>7*1024**3: reason='sampled RSS exceeds 7 GiB';break
 time.sleep(.5)
if stop or reason:
 for p in children:
  if p.poll() is None: p.terminate()
for p in children:
 try:p.wait(timeout=10)
 except subprocess.TimeoutExpired:p.kill();p.wait()
for f in logs:f.close()
starts=set();outcomes=set()
for p in result.glob('worker-*.jsonl'):
 for line in p.read_text().splitlines():
  x=json.loads(line); (starts if x['event']=='started' else outcomes).add(x['case_id'])
unknown=len(starts-outcomes); finished=len(starts)==9150 and len(outcomes)==9150 and not unknown
summary={'model':model,'cores':cores[:min(3,len(cores))],'started':len(starts),'outcomes':len(outcomes),'unknown':unknown,'unexposed':9150-len(starts),'sampled_peak_rss_bytes':peak,'co_tenancy':'uncontrolled','reason':reason,'worker_returncodes':[p.returncode for p in children]}
(result/'status.json').write_text(json.dumps(summary,indent=2)+'\n')
if finished: (result/'COMPLETE.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary),flush=True)
sys.exit(0 if finished else 75)
