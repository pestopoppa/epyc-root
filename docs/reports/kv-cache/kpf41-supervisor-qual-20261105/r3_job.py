#!/usr/bin/env python3
import ctypes, hashlib, json, os, pathlib, re, signal, subprocess, sys, time
D=pathlib.Path(__file__).resolve().parent
BUILD=D/'build'; ID='kpf41-gpu-parity-r3-20261105'; OWNED={}; SIGNALS=[]; STOP=False
libc=ctypes.CDLL(None,use_errno=True)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
def proc_birth(pid):
 try:return int(pathlib.Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[19])
 except (FileNotFoundError,ProcessLookupError,IndexError):return None
def subreaper():
 v=ctypes.c_int()
 if libc.prctl(36,1,0,0,0)!=0 or libc.prctl(37,ctypes.byref(v),0,0,0)!=0 or v.value!=1:raise RuntimeError('subreaper unavailable')
def children(pid):
 out=set()
 try:
  for t in pathlib.Path(f'/proc/{pid}/task').iterdir():
   try:out.update(int(x) for x in (t/'children').read_text().split())
   except FileNotFoundError:pass
 except FileNotFoundError:pass
 return out
def capture(pid):
 if pid in OWNED:return
 try:fd=os.pidfd_open(pid)
 except ProcessLookupError:return
 birth=proc_birth(pid)
 if birth is None:os.close(fd);return
 info=pathlib.Path(f'/proc/self/fdinfo/{fd}').read_text()
 if not re.search(r'^Pid:\s*'+str(pid)+r'\s*$',info,re.M) or proc_birth(pid)!=birth:
  os.close(fd);raise RuntimeError('pidfd identity uncertain')
 OWNED[pid]=(birth,fd)
def capture_tree(root):
 todo=[root];seen=set()
 while todo:
  p=todo.pop()
  if p in seen:continue
  seen.add(p)
  for child in children(p):capture(child);todo.append(child)
def cleanup():
 deadline=time.monotonic()+4;term=set();killed=set();errors=[]
 while time.monotonic()<deadline:
  for pid in children(os.getpid()):capture(pid);capture_tree(pid)
  direct=children(os.getpid())
  for pid,(birth,fd) in list(OWNED.items()):
   current=proc_birth(pid)
   if current is None:continue
   if current!=birth:errors.append('identity changed');continue
   if pid in direct:
    try:
     got,_=os.waitpid(pid,os.WNOHANG)
     if got==pid:continue
    except ChildProcessError:errors.append('child ownership uncertain');continue
   sig=None
   if pid not in term:sig=signal.SIGTERM;term.add(pid)
   elif time.monotonic()>deadline-2 and pid not in killed:sig=signal.SIGKILL;killed.add(pid)
   if sig:
    try:signal.pidfd_send_signal(fd,sig);SIGNALS.append({'pid':pid,'birth':birth,'signal':sig.name})
    except ProcessLookupError:pass
  if not [p for p,(b,_) in OWNED.items() if proc_birth(p)==b] and not children(os.getpid()):
   if errors:raise RuntimeError('; '.join(errors))
   return
  time.sleep(.01)
 raise RuntimeError('cleanup bound exceeded')
def close_owned():
 for _,fd in OWNED.values():os.close(fd)
 OWNED.clear()
def signal_stop(*_):
 global STOP
 STOP=True
def check():
 for p,h in json.loads((D/'pins.json').read_text()).items():
  if sha(p)!=h:raise RuntimeError('input drift: '+p)
 r=json.loads((BUILD/'out/RESULT.json').read_text())
 if r['status']!='BUILD_PASS' or r['source_commit']!='15caecbbf4cb27452dbd87fa1a68a0e75098388e':raise RuntimeError('build receipt mismatch')
def cleanup_test():
 subreaper()
 if children(os.getpid()):raise RuntimeError('unexpected initial child')
 # Parent creates its own grandchild and reports readiness through a pipe.
 code='import os,sys,time; p=os.fork(); (time.sleep(30),os._exit(0)) if p==0 else (print(p,flush=True),time.sleep(30))'
 p=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
 try:
  capture(p.pid)
  import select
  if not select.select([p.stdout],[],[],3)[0]:raise RuntimeError('cleanup test readiness timeout')
  child=int(p.stdout.readline());capture_tree(p.pid)
  if child not in OWNED:raise RuntimeError('grandchild not captured')
  cleanup()
  if children(os.getpid()) or proc_birth(p.pid) is not None or proc_birth(child) is not None:raise RuntimeError('cleanup survivors')
  if len(SIGNALS)<2:raise RuntimeError('cleanup signal coverage missing')
 finally:
  cleanup();p.wait();p.stdout.close();close_owned();SIGNALS.clear()
if '--check' in sys.argv:check();sys.exit(0)
smoke=os.environ.get('FILLER_DRYRUN')=='1';out=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
if out.exists():raise SystemExit('result exists')
out.parent.mkdir(parents=True,exist_ok=True);result={'id':ID,'status':'INVALID','progress':0,'cases':[],'smoke':smoke};p=None
for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,signal_stop)
try:
 check()
 if smoke:
  cleanup_test();result.update(status='SMOKE_INPUTS_PINNED',progress=1,cleanup_test='PASS',scope='input custody and synthetic owned-descendant cleanup; no GPU execution')
 else:
  subreaper()
  if children(os.getpid()):raise RuntimeError('unexpected child before fixture')
  stop=pathlib.Path(os.environ['FILLER_STOPFILE']);deadline=float(os.environ['FILLER_DEADLINE']);env=os.environ.copy();env['LD_LIBRARY_PATH']=str(BUILD/'bin')+':/opt/rocm/lib';exe=BUILD/'bin/test-kv-rows-vec-direct'
  for case,args,expected in [('f16',[],'f16'),('q8',['q8'],'q8_0')]:
   if STOP or stop.exists() or time.time()>=deadline-5:raise RuntimeError('STOP/deadline')
   log=out.parent/(case+'.log');signal_count=len(SIGNALS)
   with log.open('xb') as f:
    p=subprocess.Popen([str(exe),*args],stdout=f,stderr=subprocess.STDOUT,env=env);pid=p.pid;samples=[];capture(pid)
    if pid not in OWNED:raise RuntimeError('child vanished before capture')
    while True:
     capture_tree(pid);rc=p.poll()
     if rc is not None:break
     if STOP or stop.exists() or time.time()>=deadline-5:raise RuntimeError('STOP/deadline during fixture')
     kfd=pathlib.Path('/sys/class/kfd/kfd/proc')/str(pid)
     try:
      vs={x.name:int(x.read_text()) for x in kfd.glob('vram_*')};maps=pathlib.Path(f'/proc/{pid}/maps').read_text();samples.append({'t':time.time_ns(),'vram':vs,'hip_mapping':str(BUILD/'bin/libggml-hip.so') in maps})
     except (OSError,ValueError):pass
     time.sleep(.05)
    cleanup();p.wait();p=None
   text=log.read_text(errors='replace');witness=any(sum(s['vram'].values())>0 and s['hip_mapping'] for s in samples);marker='KPF-41 direct gfx90a vec row parity passed: '+expected
   result['cases'].append({'case':case,'pid':pid,'rc':rc,'samples':samples,'log':str(log),'log_sha256':sha(log),'residency':witness,'type_marker':marker in text});result['progress']+=1
   if rc!=0 or len(SIGNALS)!=signal_count or not witness or marker not in text:raise RuntimeError('fixture, cleanup, type marker or residency failure: '+case)
   close_owned()
  check();result.update(status='PARITY_PASS',scope='model-free F16/Q8 D64 direct row fixture only')
except Exception as e:result['reason']=str(e)
finally:
 if not smoke:
  try:
   cleanup()
   if p is not None:p.wait()
   result['cleanup_signals']=SIGNALS
   if children(os.getpid()):raise RuntimeError('surviving adopted child')
  except Exception as e:result['status']='INVALID';result['reason']='cleanup failure: '+str(e)
  close_owned()
 tmp=out.with_suffix('.tmp');tmp.write_text(json.dumps(result,indent=2)+'\n');tmp.replace(out)
sys.exit(0 if result['status'] in ('PARITY_PASS','SMOKE_INPUTS_PINNED') else 1)
