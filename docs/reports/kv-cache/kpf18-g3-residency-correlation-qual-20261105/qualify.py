import hashlib,json,os,signal,time,types
from pathlib import Path
D=Path(__file__).resolve().parent
started=time.monotonic()
stop=D/'STOP'
def interrupted(*_): raise RuntimeError('signal')
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
def boundary():
 if stop.exists() or time.monotonic()-started>30 or time.time()>float(os.environ['FILLER_END'])-7: raise RuntimeError('STOP/deadline')
def seals():
 for line in (D/'SEALED.sha256').read_text().splitlines():
  sha,name=line.split('  ',1)
  p=D/name
  if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha: raise RuntimeError('source drift')
seals();boundary()
mods=[]
for name in ('original','corrected'):
 m=types.ModuleType(name);exec(compile((D/(name+'.py')).read_bytes(),name,'exec'),m.__dict__);mods.append(m)
base=dict(pid=42,birth=123,gpu_id=77,hip_mapped=True,kfd_pid_present=True,own_vram_bytes=50,device_vram_bytes=100,exe_matches_binary=True,status='RESIDENT_SNAPSHOT')
cases=[('honest',{},'BOUNDED_OBSERVATION','BOUNDED_OBSERVATION'),('wrong_executable',{'exe_matches_binary':False,'status':'UNKNOWN'},'BOUNDED_OBSERVATION','UNKNOWN'),('unknown_status',{'status':'UNKNOWN'},'BOUNDED_OBSERVATION','UNKNOWN'),('missing_executable',{'exe_matches_binary':None},'BOUNDED_OBSERVATION','UNKNOWN'),('missing_status',{'status':None},'BOUNDED_OBSERVATION','UNKNOWN'),('zero_own',{'own_vram_bytes':0},'UNKNOWN','UNKNOWN'),('wrong_birth',{'birth':124},'UNKNOWN','UNKNOWN'),('no_mapping',{'hip_mapped':False},'UNKNOWN','UNKNOWN'),('no_kfd',{'kfd_pid_present':False},'UNKNOWN','UNKNOWN')]
smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
if smoke: cases=cases[:2]
controls=[]
for name,patch,*expected in cases:
 boundary()
 samples=[dict(base,**patch,observation_start=a,observation_end=b) for a,b in ((1.,3.),(3.,4.))]
 for mod,want in zip(mods,expected):
  got=mod.correlate(calls=[dict(invocation='synthetic',native_begin=0.,native_dispatch=2.,native_end=5.)],samples=samples,pid=42,birth=123,gpu_id=77)[0]
  controls.append(dict(case=name,implementation=mod.__name__,expected=want,actual=got,matched=got['status']==want))
  if got['status']!=want: raise RuntimeError('control mismatch')
seals();boundary()
result=dict(status='PASS',mode='SMOKE_ONLY' if smoke else 'MODEL_FREE_QUALIFICATION',controls=controls,source_seals=(D/'SEALED.sha256').read_text(),model_opened=False,gpu_accessed=False,processes_spawned=0,affinity=sorted(os.sched_getaffinity(0)))
p=Path(os.environ['CORRELATION_RESULT']);p.parent.mkdir(parents=True,exist_ok=True)
with p.open('x') as f: json.dump(result,f,indent=2)
