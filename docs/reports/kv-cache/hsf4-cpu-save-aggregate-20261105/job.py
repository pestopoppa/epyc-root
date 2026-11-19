#!/usr/bin/env python3
import hashlib,json,os,re,signal,statistics,sys,time
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/kvu/hsf4-cpu-save-aggregate-20261105')
ROOT=Path('/mnt/raid0/llm/tmp/qb2-kpf64/results')
PINS={'pass1-C':'f446eea4278d887e8520cc4e64d2bc7ce95b18b568a2a192ac8e953b7c0bdded','pass1-D':'5c4cb9f3c2c7734222aaf493c3aff1dd0e8c3df2b1e045ed293b3463381be55a','pass2-C':'c441db4b6fb7cb77766e995d26d84e309da0a8280e0331421495365982c957fd','pass2-D':'02b3d06dae1062747aac0ad29285f8f49a11761a2ec7aba7de166778ec34a47f'}
stop=False
def signal_stop(*_):
 global stop;stop=True
signal.signal(signal.SIGTERM,signal_stop);signal.signal(signal.SIGINT,signal_stop)
def check():
 if stop or (D/'STOP').exists() or (os.getenv('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()):raise RuntimeError('STOP')
 if time.time()>=float(os.getenv('FILLER_DEADLINE',os.getenv('FILLER_END','9999999999'))):raise RuntimeError('deadline')
start='srv  get_availabl: updating prompt cache'
end=re.compile(r'prompt cache update took ([0-9.]+) ms')
save=re.compile(r'prompt_save:  - saving prompt with length (\d+), total state size =\s*([0-9.]+) MiB')
def extract(lines):
 block=None;groups=[]; total=0; refused=0
 for s in lines:
  if start in s:
   if block is not None: refused+=1
   block=[];total+=1;continue
  if block is None:continue
  block.append(s);m=end.search(s)
  if not m:continue
  saves=[save.search(x) for x in block];saves=[x for x in saves if x]
  ms=float(m.group(1))
  if len(saves)==1 and ms>0:
   size=float(saves[0].group(2));tokens=int(saves[0].group(1))
   if size>0 and tokens>0:groups.append({'tokens':tokens,'state_mib':size,'update_ms':ms,'effective_state_gb_s':size*1048576/(ms*1e6)})
   else:refused+=1
  else:refused+=1
  block=None
 if block is not None:refused+=1
 return {'update_blocks':total,'eligible_single_save_blocks':len(groups),'other_blocks':refused,'samples':groups}
def snapshot(name):
 check();p=ROOT/name/'server.log'
 with p.open('rb') as f:
  a=os.fstat(f.fileno())
  if a.st_size>128*1024*1024:raise ValueError('too large')
  raw=f.read(a.st_size+1);b=os.fstat(f.fileno())
 if (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)!=(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns,b.st_ctime_ns) or len(raw)!=a.st_size or not raw.endswith(b'\n'):raise ValueError('unstable input')
 if hashlib.sha256(raw).hexdigest()!=PINS[name]:raise ValueError('source digest mismatch')
 return raw.decode('utf8').splitlines()
def write(p,x):
 check();p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,sort_keys=True);f.write('\n')
def main():
 smoke=os.getenv('FILLER_SMOKE')=='1' or os.getenv('FILLER_DRYRUN')=='1'
 out=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
 if sys.argv[1:]==['--complete']:
  obj=json.loads(out.read_text());assert obj['status']==('SMOKE_PASS' if smoke else 'COMPLETE') and obj['files']>0;check();return
 if smoke:
  assert len(os.sched_getaffinity(0))==4
  v=extract([start,'srv   prompt_save:  - saving prompt with length 100, total state size = 64.000 MiB','prompt cache update took 10.00 ms',start,'prompt cache update took 1.00 ms'])
  assert v['update_blocks']==2 and v['eligible_single_save_blocks']==1 and v['other_blocks']==1
  write(out,{'schema':'hsf4.cpu-cache-update.v1','status':'SMOKE_PASS','files':1,'fixture':v});return
 results={}
 for name in PINS:
  check();x=extract(snapshot(name));assert x['update_blocks']>0, 'no recognized cache update blocks';samples=x.pop('samples');rates=[z['effective_state_gb_s'] for z in samples];x['effective_state_gb_s']={'n':len(rates),'median':statistics.median(rates) if rates else None,'min':min(rates) if rates else None,'max':max(rates) if rates else None};x['source_sha256']=PINS[name];results[name]=x
 write(out,{'schema':'hsf4.cpu-cache-update.v1','status':'COMPLETE','files':len(results),'arms':results,'scope':'CPU historical single-save inclusive update effective state bytes / elapsed update; may include allocator, cache search, checkpoint and load overhead. Not pure copy bandwidth, restore speed, controlled timing, or HSF-4 completion.'})
if __name__=='__main__':main()
