#!/usr/bin/python3
"""Serial R13 group invocations within one real pool grant; no cohort replay reset."""
import argparse, datetime, hashlib, json, os, pathlib, re, signal, subprocess, time, stat, sys, shutil
sys.path.insert(0,"/mnt/raid0/llm/tmp/rtg56-td29-m0a-raw-v5-20261029")
import pidfd_subreaper_v3 as subreaper
H=pathlib.Path('/mnt/micron/codex3-pip-relocatable-r25-20261030')
R=pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip02-paddle-relocatable-r13-20261030')
F=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags')
RAID_META=pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip-relocatable-r25-20261030')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def active_group(n):
 for d in (F/'ready',F/'ready/armed',F/'grants'):
  for p in d.glob('*pip02*paddle*'):
   if p.suffix not in ('.grant','.json'):continue
   pm=re.search(r'-pool([0-3])-',p.name)
   if pm and p.stem!=os.environ.get('FILLER_ID') and int(pm[1])==((n-5)//3)%4:return str(p)
   m=re.search(r'-g(\d+)-',p.name)
   if m and set(range(n,min(n+3,151))) & set(range(int(m[1]),min(int(m[1])+3,151))):return str(p)
   m=re.search(r'-s(\d+)-',p.name)
   if m and int(m[1]) in range(n,min(n+3,151)):return str(p)
 return None
def cpu_set(text):
 out=set()
 for part in text.split(','):
  m=re.fullmatch(r'(\d+)(?:-(\d+))?',part)
  if not m:raise ValueError('invalid FILLER_CPUS')
  a=int(m[1]);b=int(m[2] or m[1])
  if b<a:raise ValueError('invalid FILLER_CPUS range')
  out.update(range(a,b+1))
 return out


class OutputCredit:
 def __init__(self,roots,soft=512*1024**2):
  self.roots=roots;self.soft=soft;self.base={};self.high={};self.scan(initial=True)
 def scan(self,initial=False):
  for root in self.roots:
   if not root.exists():continue
   items=[]
   if root.is_file():items=[root]
   elif root.is_dir():
    for parent,dirs,files in os.walk(root,followlinks=False,onerror=lambda e: (_ for _ in ()).throw(e)):
     dirs[:]=[d for d in dirs if not pathlib.Path(parent,d).is_symlink()]
     items.extend(pathlib.Path(parent,f) for f in files)
   for path in items:
    try:
     st=path.stat(follow_symlinks=False)
     if not stat.S_ISREG(st.st_mode):continue
     key=(str(path),st.st_dev,st.st_ino);size=max(st.st_size,st.st_blocks*512)
     if initial:self.base[key]=size
     self.high[key]=max(size,self.high.get(key,0))
    except FileNotFoundError:continue
  return sum(max(0,n-self.base.get(k,0)) for k,n in self.high.items())

class SplitCredit:
 def __init__(self,micron_roots,raid_roots):
  self.micron=OutputCredit(micron_roots);self.raid=OutputCredit(raid_roots,soft=64*1024**2);self.soft=self.micron.soft;self.raid_bytes=0
 def scan(self):
  used=self.micron.scan();self.raid_bytes=self.raid.scan();return used
 def raid_exceeded(self):return self.raid_bytes>=self.raid.soft

def run_with_credit(cmd,env,credit,outer_stop,interrupted,emit,floor=150*1024**3):
 private=pathlib.Path(env['FILLER_STOPFILE']);p=subprocess.Popen(cmd,env=env);fd=None;cutoff=None;why=None;problem=None
 def send(sig):
  try:
   if fd is None:p.send_signal(sig)
   else:signal.pidfd_send_signal(fd,sig)
  except ProcessLookupError:pass
 try:
  try:fd=os.pidfd_open(p.pid)
  except ProcessLookupError:pass
  while p.poll() is None:
   used=credit.scan();low=shutil.disk_usage(H).free<floor or shutil.disk_usage(RAID_META).free<150*1024**3+128*1024**2;raid_cap=credit.raid_exceeded()
   if cutoff is None and (used>=credit.soft or raid_cap or low or outer_stop.exists() or interrupted[0]):
    why='output-credit' if used>=credit.soft else 'raid-metadata-credit' if raid_cap else 'disk-floor' if low else 'stop';cutoff=time.monotonic();private.touch(exist_ok=True);emit({'event':'credit-stop','reason':why,'sampled_bytes':used,'raid_metadata_bytes':credit.raid_bytes,'soft_bytes':credit.soft})
   if cutoff is not None and time.monotonic()-cutoff>=30:send(signal.SIGTERM)
   if cutoff is not None and time.monotonic()-cutoff>=60:send(signal.SIGKILL)
   time.sleep(.25)
 except BaseException as e:problem=e
 finally:
  try:
   if p.poll() is None:
    try:private.touch(exist_ok=True)
    except OSError:pass
    send(signal.SIGTERM);limit=time.monotonic()+30
    while p.poll() is None and time.monotonic()<limit:time.sleep(.05)
    if p.poll() is None:send(signal.SIGKILL)
   p.wait()
   while subreaper.children():
    try:subreaper.drain(timeout=10)
    except RuntimeError:continue
  finally:
   if fd is not None:os.close(fd)
 if problem is not None:
  emit({'event':'monitor-failure','error':repr(problem),'drained':True});raise problem
 used=credit.scan();emit({'event':'credit-sample','sampled_bytes':used,'soft_bytes':credit.soft,'overshoot_bytes':max(0,used-credit.soft),'raid_metadata_bytes':credit.raid_bytes,'raid_metadata_overshoot_bytes':max(0,credit.raid_bytes-credit.raid.soft),'reason':why,'drained':True})
 return p.returncode,why

def main():
 a=argparse.ArgumentParser();a.add_argument('--pool',type=int,choices=range(4),required=True);a.add_argument('--regions',choices=['0-23','24-47','48-71','72-95'],required=True);a.add_argument('--port',type=int,required=True);a.add_argument('--smoke',action='store_true');x=a.parse_args()
 ident=os.environ['FILLER_ID'];family=json.loads((H/'family.json').read_bytes());expected=list(range(5,150,3))[x.pool::4]
 if family['groups'][str(x.pool)]!=expected or family['pool_ids'][str(x.pool)]!=f'codex3-pip02-paddle-relocatable-r25-pool{x.pool}-20261030':raise RuntimeError('family scope mismatch')
 if x.smoke:
  subreaper.enable();outer=pathlib.Path(os.environ['FILLER_STOPFILE']);private=H/'smoke-runtime.STOP'
  if private.exists():raise RuntimeError('smoke STOP already exists')
  events=[];credit=SplitCredit([H],[RAID_META]);env=dict(os.environ,FILLER_STOPFILE=str(private))
  rc,cutoff=run_with_credit(['/usr/bin/python3','-B',str(H/'parallel_entry.py'),'--first-shard','5','--regions',x.regions,'--port',str(x.port),'--smoke'],env,credit,outer,[False],events.append)
  print(json.dumps({'event':'smoke-credit','events':events,'cutoff':cutoff,'native_rc':rc},sort_keys=True),flush=True)
  return 75 if cutoff else rc
 grant=F/'grants'/f'{ident}.grant';stop=pathlib.Path(os.environ['FILLER_STOPFILE']);deadline=float(os.environ['FILLER_DEADLINE'])
 if ident!=f'codex3-pip02-paddle-relocatable-r28-pool{x.pool}-20261031' or not grant.is_file():raise RuntimeError('pool identity or real grant missing')
 rawgrant=grant.read_bytes(); match=re.search(r'(?:^|\s)regions=([^\s]+)',rawgrant.decode())
 cpus=cpu_set(os.environ['FILLER_CPUS']);lo,hi=map(int,x.regions.split('-'))
 if not match or match[1]!=x.regions or not cpus or any(not lo<=n%96<=hi for n in cpus) or os.sched_getaffinity(0)!=cpus:raise RuntimeError('grant, CPU affinity and assigned quarter differ')
 source=json.loads((H/'source-pins.json').read_bytes());assert all(digest(pathlib.Path(p))==v for p,v in source.items())
 interrupted=[False]
 def request_stop(signum,frame):interrupted[0]=True
 signal.signal(signal.SIGTERM,request_stop);signal.signal(signal.SIGINT,request_stop)
 subreaper.enable()
 out=H/'attempts';out.mkdir(exist_ok=True);record=out/f'{ident}-{time.time_ns()}.jsonl'
 credit=SplitCredit([H],[RAID_META,pathlib.Path(os.environ['FILLER_PIDFILE'])]+[pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh')/f'shard-{j:02d}' for i,g in enumerate(range(5,150,3)) if i%4==x.pool for j in range(g,min(g+3,151))])
 def emit(obj):
  with record.open('a') as f:f.write(json.dumps(obj,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
 emit({'event':'pool-start','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'id':ident,'grant':rawgrant.decode(),'grant_sha256':hashlib.sha256(rawgrant).hexdigest(),'wrapper_pins':source,'groups':[g for i,g in enumerate(range(5,150,3)) if i%4==x.pool]})
 pending=False;exhausted=[];failure=None
 for i,n in enumerate(range(5,150,3)):
  if i%4!=x.pool:continue
  if shutil.disk_usage(H).free<150*1024**3 or shutil.disk_usage(RAID_META).free<150*1024**3+128*1024**2:emit({'event':'credit-stop','reason':'disk-floor-before-group'});pending=True;break
  if credit.scan()>=credit.soft or credit.raid_exceeded():emit({'event':'credit-stop','reason':'before-group','sampled_bytes':credit.scan(),'soft_bytes':credit.soft});pending=True;break
  if interrupted[0] or stop.exists() or not grant.exists() or grant.read_bytes()!=rawgrant or time.time()+1200>=deadline:pending=True;break
  if (R/f'DONE-{n}').exists() or (H/f'DONE-{n}').exists():emit({'event':'skip-complete','group':n});continue
  owner=active_group(n)
  if owner:emit({'event':'skip-owned','group':n,'owner':owner});pending=True;continue
  if any(digest(pathlib.Path(p))!=v for p,v in source.items()):raise RuntimeError('pool source changed')
  emit({'event':'group-start','group':n,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
  private=record.with_name(record.name+f'.{n}.STOP');env=dict(os.environ,FILLER_STOPFILE=str(private))
  native_rc,cutoff=run_with_credit(['/usr/bin/python3','-B',str(H/'parallel_entry.py'),'--first-shard',str(n),'--regions',x.regions,'--port',str(x.port)],env,credit,stop,interrupted,emit)
  emit({'event':'group-end','group':n,'rc':native_rc,'at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
  if cutoff:pending=True;break
  if interrupted[0]:pending=True;break
  if native_rc==0:
   if not (H/f'DONE-{n}').is_file():failure=70;emit({'event':'failure','group':n,'reason':'native rc0 without DONE','rc':failure});break
  elif native_rc==75:pending=True;break
  elif native_rc==78:exhausted.append(n)
  else:failure=native_rc if native_rc>0 else 128-native_rc;emit({'event':'failure','group':n,'native_rc':native_rc,'rc':failure});break
 rc=failure if failure is not None else 75 if pending else 78 if exhausted else 0
 emit({'event':'pool-end','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rc':rc,'exhausted_unknown_groups':exhausted,'pending':pending})
 if rc==0:
  fd=os.open(H/f'DONE-{x.pool}',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
  try:os.write(fd,b'collection complete; no quality verdict\n');os.fsync(fd)
  finally:os.close(fd)
 return rc
if __name__=='__main__':raise SystemExit(main())
