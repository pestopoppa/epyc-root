#!/usr/bin/env python3
"""GDB-owned historical allocator fixture; model-free observer qualification only."""
import hashlib,json,os,signal,subprocess,sys,time,uuid
from pathlib import Path
D=Path(__file__).resolve().parent
ROW='kvfork-kpf131-findslot-observer-r3-20261105'
FIX=D/'fixture'
BIN='078cafd6e72d274f40d82c50012b0170f80d2f0d8e72f5574cca6f88e7de7d7d'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ck(x,msg):
 if not x: raise RuntimeError(msg)
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix('.tmp');t.write_text(json.dumps(x,indent=2)+'\n');os.replace(t,p)
def birth(pid): return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19])
def clean(proc,marker):
 # Signal only recorded, birth-matched owned processes; pidfd binds identity.
 if proc.poll() is None:
  if marker.exists():
   ident=json.loads(marker.read_text()); pid=ident['pid']
   try:
    fd=os.pidfd_open(pid); ck(birth(pid)==ident['birth'],'inferior PID reused');signal.pidfd_send_signal(fd,signal.SIGKILL);os.close(fd)
   except ProcessLookupError: pass
  fd=os.pidfd_open(proc.pid);signal.pidfd_send_signal(fd,signal.SIGTERM);os.close(fd)
  try: proc.wait(timeout=2)
  except subprocess.TimeoutExpired:
   fd=os.pidfd_open(proc.pid);signal.pidfd_send_signal(fd,signal.SIGKILL);os.close(fd);proc.wait(timeout=2)
 ck(proc.poll() is not None,'debugger survived')
 if marker.exists():
  i=json.loads(marker.read_text())
  try: ck(birth(i['pid'])!=i['birth'],'inferior survived')
  except FileNotFoundError: pass
 return True
smoke=os.getenv('FILLER_SMOKE')=='1' or os.getenv('FILLER_DRYRUN')=='1'
out=D/'out'/('smoke' if smoke else 'full')/uuid.uuid4().hex
out.mkdir(parents=True,exist_ok=False)
result={'status':'INVALID','case_count':0,'records':[],'smoke':smoke,'scope':'model-free breakpoint observer only; no historical layout or task binding'}
try:
 ck(os.environ.get('FILLER_ID')==ROW,'wrong row')
 ck(not (D/'STOP').exists() and not Path(os.getenv('FILLER_STOPFILE',str(D/'STOP'))).exists(),'STOP')
 ck(sha(FIX)==BIN,'fixture digest drift')
 for p,h in json.loads((D/'seal.json').read_text()).items(): ck(sha(D/p)==h,'seal drift '+p)
 before=sha(D/'seal.json')
 for arm,expected in [('honest','RESULT PASS 2 3'),('skip_apply','RESULT DETECTED 0 1')]:
  folder=out/arm;folder.mkdir();(folder/'input').write_text('g\nq\n')
  env=dict(os.environ,LD_LIBRARY_PATH='/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin',DEBUGINFOD_URLS='',OBSERVER_OUT=str(folder),OBSERVER_ARM=arm,OBSERVER_FIX=str(FIX),OBSERVER_DIR=str(D))
  env.pop('LD_PRELOAD',None);env.pop('LD_AUDIT',None)
  marker=folder/'identity.json'; proc=subprocess.Popen(['/usr/bin/gdb','-q','-nx','-batch','-x',str(D/'observer.gdb'),'--args',str(FIX),arm],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
  try:
   deadline=time.monotonic()+35
   while True:
    ck(not Path(os.getenv('FILLER_STOPFILE',str(D/'STOP'))).exists() and not (D/'STOP').exists(),'STOP')
    ck(time.monotonic()<deadline,'debugger timeout')
    if os.getenv('FILLER_DEADLINE'): ck(time.time()<float(os.environ['FILLER_DEADLINE'])-7,'grant deadline')
    try:
     stdout,stderr=proc.communicate(timeout=.2);break
    except subprocess.TimeoutExpired: pass
  finally:
   cleanup=clean(proc,marker)
  (folder/'gdb.stdout').write_bytes(stdout);(folder/'gdb.stderr').write_bytes(stderr)
  ck(proc.returncode==0,'gdb failed');ck(expected in stdout.decode(errors='replace'),'fixture result missing')
  native=json.loads((folder/'native.json').read_text());ck(native['hits']==2 and native['exit_code']==0,'hits or exit')
  ck(native['before']==native['after'] and len(native['before']['maps'])==5,'mapping identity mismatch')
  ck(native['before']['exe_sha256']==BIN,'executable mismatch')
  result['records'].append({'arm':arm,'expected':expected,'native':native,'cleanup_confirmed':cleanup,'gdb_rc':proc.returncode});result['case_count']+=1
  ck(not Path(os.getenv('FILLER_STOPFILE',str(D/'STOP'))).exists(),'STOP')
 ck(before==sha(D/'seal.json'),'seal changed');result.update(status='PASS',seal_sha256=before)
 save(out/'RESULT.json',result)
 if smoke:
  target=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']);ck(not target.exists() and target.is_absolute(),'bad smoke output');save(target,result)
 else: save(D/'out'/'RESULT.json',result)
 print('OBSERVER_PASS',flush=True)
except BaseException as e:
 result['error']=repr(e);save(out/'RESULT.json',result);print(repr(e),file=sys.stderr);sys.exit(1)
