#!/usr/bin/env python3
import ctypes, hashlib, json, os, pathlib, re, signal, subprocess, sys, time
D=pathlib.Path(__file__).resolve().parent
BUILD=pathlib.Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-tests-build-20261105/build'); ID='kpf41-backend-gpu-qualification-20261105'; OWNED={}; SIGNALS=[]; STOP=False
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
SOURCE=BUILD.parent/'source'
COMMIT='15caecbbf4cb27452dbd87fa1a68a0e75098388e'
def check():
 r=json.loads((D/'receipt.json').read_text())
 if r['status']!='BUILD_PASS' or r['source_commit']!=COMMIT or len(r['files'])!=5:raise RuntimeError('receipt invalid')
 for p,h in r['files'].items():
  if sha(p)!=h:raise RuntimeError('artifact drift: '+p)
 def git(*args):return subprocess.check_output(['git','-C',str(SOURCE),*args],text=True).strip()
 if git('rev-parse','HEAD')!=COMMIT or git('status','--porcelain','--untracked-files=no'):raise RuntimeError('source drift')
 if subprocess.run(['git','-C',str(SOURCE),'symbolic-ref','-q','HEAD'],stdout=subprocess.DEVNULL).returncode==0:raise RuntimeError('source not detached')
 env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(BUILD/'bin')+':/opt/rocm/lib'}
 linkage=subprocess.check_output(['ldd',str(BUILD/'bin/test-backend-ops')],env=env,text=True)
 for name in ('libggml.so','libggml-base.so','libggml-cpu.so'):
  if not re.search(r'^\s*'+re.escape(name)+r'\S*\s*=>\s*'+re.escape(str(BUILD/'bin'))+r'/',linkage,re.M):raise RuntimeError('linkage mismatch: '+name)
 return linkage
def parse_corpus(text):
 text=re.sub(r'\x1b\[[0-9;]*m','',text)
 cases=[]
 for line in text.splitlines():
  if not line.startswith('  FLASH_ATTN_EXT('):continue
  m=re.fullmatch(r'  FLASH_ATTN_EXT\((.*)\): (OK|FAIL|not supported \[ROCm0\])\s*',line)
  if not m:raise ValueError('malformed case: '+line[:180])
  params,status=m.groups();shared=re.search(r'(?:^|,)\s*n_shared=([0-9]+)(?:,|$)',params)
  cases.append({'params':params,'status':status,'shared':bool(shared and int(shared.group(1))>0)})
 summaries=re.findall(r'^\s*(\d+)/(\d+) tests passed\s*$',text,re.M)
 backends=re.findall(r'^(\d+)/(\d+) backends passed\s*$',text,re.M)
 if len(summaries)!=1 or len(backends)!=1 or (int(backends[0][0])<1 or backends[0][0]!=backends[0][1]) or not re.search(r'^  Backend ROCm0: OK\s*$',text,re.M) or not re.search(r'\nOK\s*$',text):raise ValueError('missing/invalid summary')
 supported=[c for c in cases if c['status']!='not supported [ROCm0]'];shared=[c for c in cases if c['shared']]
 if not supported or tuple(map(int,summaries[0]))!=(len(supported),len(supported)) or any(c['status']!='OK' for c in supported):raise ValueError('nonzero case/summary mismatch')
 if len(shared)!=25 or any(c['status']!='OK' for c in shared):raise ValueError('shared-trunk missing or unsupported')
 return {'cases':cases,'selected':len(cases),'supported':len(supported),'unsupported':len(cases)-len(supported),'shared_trunk':len(shared)}
def smoke_test():
 prefix='  FLASH_ATTN_EXT(n_shared=2048): OK\n'*25
 good=prefix+'  25/25 tests passed\n  Backend ROCm0: OK\n1/1 backends passed\nOK\n'
 assert parse_corpus(good)['shared_trunk']==25
 for bad in (good.replace('25/25 tests passed','0/0 tests passed'), good.replace(': OK',': BROKEN',1),good.replace('1/1 backends passed',''),good.replace(': OK',': not supported [ROCm0]',1)):
  try:parse_corpus(bad)
  except ValueError:continue
  raise RuntimeError('negative parser control accepted')
 subreaper()
 if children(os.getpid()):raise RuntimeError('unexpected child')
 code='import os,time; p=os.fork(); (time.sleep(30),os._exit(0)) if p==0 else (print(p,flush=True),time.sleep(30))'
 p=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE)
 try:
  capture(p.pid)
  import select
  if not select.select([p.stdout],[],[],3)[0]:raise RuntimeError('child readiness timeout')
  child=int(p.stdout.readline());capture_tree(p.pid)
  if child not in OWNED:raise RuntimeError('grandchild not captured')
  cleanup()
  if proc_birth(child) is not None or proc_birth(p.pid) is not None:raise RuntimeError('cleanup survivor')
 finally:
  cleanup();p.wait();p.stdout.close();close_owned();SIGNALS.clear()
def gpu_smoke():
 if os.environ.get('FILLER_SMOKE')!='1' or os.environ.get('FILLER_NEEDGPU')!='1':raise RuntimeError('GPU witness requires publisher GPU smoke grant')
 exe=D/'clock-smoke'
 if sha(exe)!='c79d3f6069abd42c334b0203b1e621dc175582779b5c33e8c49018f22cb17076':raise RuntimeError('witness binary drift')
 stop=pathlib.Path(os.environ['FILLER_STOPFILE']);deadline=min(float(os.environ['FILLER_DEADLINE'])-5,time.time()+90)
 if STOP or stop.exists() or time.time()>=deadline:raise RuntimeError('STOP/deadline')
 env={'PATH':'/usr/bin:/bin','HOME':os.environ.get('HOME','/tmp'),'LD_LIBRARY_PATH':'/opt/rocm/lib','HIP_VISIBLE_DEVICES':'0','ROCR_VISIBLE_DEVICES':'0'}
 log=out.parent/'gpu-witness.log';samples=[];p=None
 try:
  with log.open('xb') as f:
   p=subprocess.Popen([str(exe)],stdout=f,stderr=subprocess.STDOUT,env=env);pid=p.pid;capture(pid)
   if pid not in OWNED:raise RuntimeError('witness vanished before capture')
   while True:
    capture_tree(pid);rc=p.poll()
    if rc is not None:break
    if STOP or stop.exists() or time.time()>=deadline:raise RuntimeError('STOP/deadline')
    try:
     vs={x.name:int(x.read_text()) for x in (pathlib.Path('/sys/class/kfd/kfd/proc')/str(pid)).glob('vram_*')};samples.append({'t':time.time_ns(),'vram':vs})
    except (OSError,ValueError):pass
    time.sleep(.1)
   cleanup();p.wait();p=None
  data=log.read_text(errors='replace')
  if rc or SIGNALS or sum(sum(x['vram'].values())>=64*1024*1024 for x in samples)<2 or 'KPF50_CLOCK_WITNESS begin_ns=' not in data:raise RuntimeError('GPU witness failed')
  return {'pid':pid,'samples':samples,'log':str(log),'log_sha256':sha(log),'binary_sha256':sha(exe)}
 finally:
  cleanup()
  if p is not None:p.wait()
  close_owned()
if '--check' in sys.argv:check();sys.exit(0)
smoke=os.environ.get('FILLER_DRYRUN')=='1';out=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
if out.exists():raise SystemExit('result exists')
out.parent.mkdir(parents=True,exist_ok=True);result={'id':ID,'status':'INVALID','progress':0,'smoke':smoke};p=None
for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,signal_stop)
try:
 result['linkage_before']=check()
 if smoke:
  smoke_test();result['gpu_witness']=gpu_smoke();check();result.update(status='SMOKE_PASS',progress=1,scope='synthetic parser, owned-descendant cleanup and bounded model-free GPU residency witness; no corpus execution')
 else:
  subreaper()
  if children(os.getpid()):raise RuntimeError('unexpected child')
  stop=pathlib.Path(os.environ['FILLER_STOPFILE']);deadline=float(os.environ['FILLER_DEADLINE'])
  if STOP or stop.exists() or time.time()>=deadline-5:raise RuntimeError('STOP/deadline')
  env={'PATH':'/usr/bin:/bin','HOME':os.environ.get('HOME','/tmp'),'LD_LIBRARY_PATH':str(BUILD/'bin')+':/opt/rocm/lib','HIP_VISIBLE_DEVICES':'0','ROCR_VISIBLE_DEVICES':'0','OMP_NUM_THREADS':'4'}
  log=out.parent/'corpus.log';samples=[]
  with log.open('xb') as f:
   p=subprocess.Popen([str(BUILD/'bin/test-backend-ops'),'test','-b','ROCm0','-o','FLASH_ATTN_EXT'],stdout=f,stderr=subprocess.STDOUT,env=env);pid=p.pid;capture(pid)
   if pid not in OWNED:raise RuntimeError('child vanished before capture')
   while True:
    capture_tree(pid);rc=p.poll()
    if rc is not None:break
    if STOP or stop.exists() or time.time()>=deadline-5:raise RuntimeError('STOP/deadline')
    try:
     kfd=pathlib.Path('/sys/class/kfd/kfd/proc')/str(pid);vs={x.name:int(x.read_text()) for x in kfd.glob('vram_*')};maps=pathlib.Path(f'/proc/{pid}/maps').read_text();samples.append({'t':time.time_ns(),'vram':vs,'hip_mapping':str((BUILD/'bin/libggml-hip.so').resolve()) in maps})
    except (OSError,ValueError):pass
    time.sleep(.05)
   cleanup();p.wait();p=None
  result.update(pid=pid,rc=rc,samples=samples,log=str(log),log_sha256=sha(log),cleanup_signals=SIGNALS)
  if rc or SIGNALS or not any(sum(s['vram'].values())>0 and s['hip_mapping'] for s in samples):raise RuntimeError('execution/residency/cleanup failed')
  result['corpus']=parse_corpus(log.read_text(errors='replace'));result['linkage_after']=check();result.update(status='QUALIFICATION_PASS',progress=1)
except Exception as e:result['reason']=str(e)
finally:
 if not smoke:
  try:
   cleanup()
   if p is not None:p.wait()
   if children(os.getpid()):raise RuntimeError('surviving child')
  except Exception as e:result['status']='INVALID';result['reason']='cleanup failure: '+str(e)
  close_owned()
 tmp=out.with_suffix('.tmp');tmp.write_text(json.dumps(result,indent=2)+'\n');tmp.replace(out)
sys.exit(0 if result['status'] in ('QUALIFICATION_PASS','SMOKE_PASS') else 1)
