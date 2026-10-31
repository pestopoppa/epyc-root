#!/usr/bin/env python3
"""One custodied Paddle server with a bounded multi-shard page pool."""
import fcntl,hashlib,importlib.util,json,os,pathlib,shutil,sys,time,uuid
BASE=pathlib.Path('/mnt/raid0/llm/tmp/pip02-pipeline-prep-20261029')
OLD=pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029')
HERE=pathlib.Path(__file__).resolve().parent
RAID_META=pathlib.Path('/mnt/raid0/llm/tmp/codex3-pip-head-r26-20261030')
E2=pathlib.Path('/mnt/raid0/llm/tmp/rtg28-e2-nodelete-successor-20261029')
RTG=pathlib.Path('/mnt/raid0/llm/tmp/rtg56-td29-m0a-raw-v5-20261029')
YARN=pathlib.Path('/mnt/raid0/llm/tmp/yarn-oolong-s0-nodelete-successor-20261029')
PLAN='63028e74950ba7250f33cbce13f4f0bdd165bba2a075242db4475c26f645ed68'
POP='c45fe25f44169b9e57a0772cf809682920f933e4dc7b862c1f28e4e4f812b762'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def owned_rss():
 pending=[os.getpid()];seen=set();total=0
 while pending:
  pid=pending.pop()
  if pid in seen:continue
  seen.add(pid)
  try:
   for line in pathlib.Path('/proc',str(pid),'status').read_text().splitlines():
    if line.startswith('VmRSS:'):total+=int(line.split()[1])*1024;break
   for child in pathlib.Path('/proc',str(pid),'task').glob('*/children'):
    try:pending.extend(map(int,child.read_text().split()))
    except (FileNotFoundError,ProcessLookupError):pass
  except (FileNotFoundError,ProcessLookupError):continue
 return total

LAST_RECORD=None
def run(shards,region,port,smoke,check):
 global LAST_RECORD
 ident=os.environ['FILLER_ID'];stop=pathlib.Path(os.environ['FILLER_STOPFILE']);grant=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(ident+'.grant')
 aff=os.sched_getaffinity(0);lo,hi=map(int,region.split('-'))
 if any(not lo<=x%96<=hi for x in aff):raise RuntimeError('affinity outside quarter')
 if smoke:
  admission=load('parallel_admission',HERE/'smoke_admission.py');admission.check(aff)
  class SmokeGate:
   end=time.time()+993
   def __init__(self):self.last=0.;self.ok=False
   def active(self):
    if stop.exists():return False
    if time.monotonic()-self.last>=0.5:
     try:admission.check(aff);self.ok=True
     except (OSError,ValueError,RuntimeError):self.ok=False
     self.last=time.monotonic()
    return self.ok
  gate=SmokeGate();deadline=time.monotonic()+210
 else:
  gate=load('parallel_gate',E2/'grant_gate.py').Gate(str(grant),[region],str(stop),93)
  deadline=time.monotonic()+gate.end-93-time.time()
 if not gate.active():raise RuntimeError('admission failed')
 cfg=json.loads((BASE/'paddle-cpu-campaign-config-v3.json').read_text())['server'];cfg['port']=port;cfg['threads']=12 if not smoke or os.environ.get('R25_NORMAL_THREADS_SMOKE')=='1' else 2
 roots=[];locks=[]
 try:
  legacy_roots=[];prior_output_roots=[]
  for n in shards:
   if smoke:
    root=HERE/'control-campaign'/f'page-{n}';legacy=HERE/'absent-control-legacy'/str(n)
   else:
    original=OLD/'campaigns-fresh'/f'shard-{n:02d}'
    legacy=original/f'shard-{n}'
    lockmod=load('legacy_lock',HERE/'legacy_lock.py');fd=lockmod.acquire(OLD/'campaigns-fresh',n);locks.append(fd)
    root=HERE/'campaigns-fresh'/f'shard-{n:02d}'
   root.mkdir(mode=0o700,parents=True,exist_ok=True)
   fd=os.open(root/'campaign.serial.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(fd)
   roots.append(str(root/('page-'+str(n) if smoke else 'shard-'+str(n))));legacy_roots.append(str(legacy));prior_output_roots.append(str(HERE/'absent-control-prior'/str(n) if smoke else pathlib.Path('/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh')/f'shard-{n:02d}'/f'shard-{n}'))
  attempt=HERE/'attempts'/f'{ident}-{uuid.uuid4().hex}';attempt.mkdir(mode=0o700,parents=True)
  pins=json.loads((HERE/'source-pins.json').read_text());grant_bytes=grant.read_bytes() if not smoke else b''
  capture={'schema':'pip02-native-attempt/v1','id':ident,'shards':shards,'smoke':smoke,'grant':grant_bytes.decode() if grant_bytes else None,'source_pins':pins,'launcher_path':os.environ['R25_LAUNCHER'],'launcher_sha256':hashlib.sha256(pathlib.Path(os.environ['R25_LAUNCHER']).read_bytes()).hexdigest(),'output_roots':roots,'legacy_roots':legacy_roots,'prior_output_roots':prior_output_roots,'output_devices':[os.stat(pathlib.Path(x).parent).st_dev for x in roots],'legacy_devices':[os.stat(pathlib.Path(x).parent).st_dev if pathlib.Path(x).parent.exists() else None for x in legacy_roots],'protocol_sha256':hashlib.sha256((HERE/'PROTOCOL.md').read_bytes()).hexdigest(),'grant_sha256':hashlib.sha256(grant_bytes).hexdigest() if grant_bytes else None,'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
  with (attempt/'capture.json').open('x') as f:json.dump(capture,f,sort_keys=True);f.flush();os.fsync(f.fileno())
  layout={'inference.json':'2b68367c5b312a03de5a6e1642c597c8f95165a7e40cd59c6700cf4a5042f4fd','inference.pdiparams':'70bd316b0582769ec968829fd1feb1a6a58b7c941b938327e551b6b12b45c137','inference.yml':'506fcfac13b3b546ae40d7886b44126420f392adb694e3f8bb6a6286a1f90fdc'}
  population=POP if smoke else PLAN
  campaign={'scope':'owner-parallel-control' if smoke else 'pip02-english-fresh-20261029-Paddle-full-4096','population_sha256':population,'layout_sha256':layout,'server_pins':cfg['pins']}
  wc={'mode':'smoke' if smoke else 'normal','shards':shards,'output_roots':roots,'legacy_roots':legacy_roots,'prior_output_roots':prior_output_roots,'population_sha256':population,'image_root':'/mnt/raid0/llm/datasets/omnidocbench/images','layout_dir':'/mnt/raid0/llm/models/PP-DocLayoutV3-paddle3.0.0','endpoint':f'http://127.0.0.1:{port}/v1','deadline_epoch':time.time()+(deadline-time.monotonic()),'stop_path':str(stop),'campaign':campaign,'capture_path':str(attempt/'capture.json')}
  raw=json.dumps(wc,sort_keys=True,separators=(',',':')).encode();path=attempt/'worker-config.json';path.write_bytes(raw)
  sys.path[:0]=[str(BASE),str(E2),str(RTG),str(YARN)]
  venv=load('parallel_venv',BASE/'venv_witness.py').Witness('/mnt/raid0/llm/venvs/paddleocr',HERE/'venv-files-r9.json','254e35f1edf3fcc3a880825e6f05874a9174c71f78d67ff6eb4c0d536afb4588',HERE/'venv-dirs-r9.json','7d4ce147150cdb7b32e9548c4857ddb68f8c995e75dd6136a346cc657063ff1e',gate.active)
  external=load('parallel_external',BASE/'external_monitor.py').Monitor(attempt,64*1024**2)
  state={'last':0.,'vtime':0.,'peak':0,'samples':0,'reason':None}
  def active():
   if time.monotonic()>=deadline or not gate.active():return False
   now=time.monotonic()
   if now-state['last']>=1:
    check();external.check();state['peak']=max(state['peak'],owned_rss());state['samples']+=1;state['last']=now
    if state['peak']>96*1024**3:state['reason']='rss limit';return False
    if shutil.disk_usage(HERE).free < 150*1024**3+3*192*1024**2+64*1024**2:state['reason']='micron disk floor';return False
    if shutil.disk_usage(RAID_META).free < 150*1024**3+128*1024**2:state['reason']='raid metadata floor';return False
   if now-state['vtime']>=2:venv.check();state['vtime']=now
   return True
  def builder(proc,identity):return ['/usr/bin/python3.12','-B','-S','-X','pycache_prefix='+str(attempt/'pycache'),str(HERE/'host_worker_bootstrap.py'),str(HERE/'parallel_worker.py'),str(path),hashlib.sha256(raw).hexdigest()]
  window=load('parallel_window',BASE/'owned_window_v7.py');factory=load('parallel_factory',HERE/'cpu_server_factory.py');recipe=load('parallel_recipe',HERE/'cpu_recipe_v11.py');witness=load('parallel_witness',E2/'cpu_witness_v5.py');projector=load('parallel_projector',BASE/'cpu_projector_witness.py');helper=load('parallel_helper',pathlib.Path('/mnt/raid0/llm/tmp/evl39-e3b-server-witness-20261029/server_witness.py'))
  result=None;error=None
  try:result=factory.run(window,witness,projector,recipe,helper,cfg,active,attempt,builder,deadline)
  except Exception as e:error=type(e).__name__+': '+str(e)
  rc=0 if not smoke and error is None and result and result.get('worker_rc')==0 else 75
  record={'schema':'pip02-paddle-parallel-owner/v1','shards':shards,'smoke':smoke,'factory':result,'error':error,'rc':rc,'partial':rc!=0,'sampled_peak_tree_rss_bytes':state['peak'],'samples':state['samples'],'reason':state['reason']}
  LAST_RECORD=record
  (attempt/'result.json').write_text(json.dumps(record,sort_keys=True)+'\n')
  print(json.dumps({'event':'parallel_complete' if rc==0 else 'parallel_partial','result':str(attempt/'result.json'),'rc':rc,'error':error},sort_keys=True),flush=True)
  return rc
 finally:
  for fd in locks:os.close(fd)
