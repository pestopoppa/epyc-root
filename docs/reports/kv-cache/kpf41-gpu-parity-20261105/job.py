#!/usr/bin/env python3
import hashlib,json,os,pathlib,signal,subprocess,sys,time
D=pathlib.Path(__file__).resolve().parent
BUILD=D/'build'
ID='kpf41-gpu-parity-20261105'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def check():
 for p,h in json.loads((D/'pins.json').read_text()).items():
  if sha(p)!=h:raise RuntimeError('input drift: '+p)
 r=json.loads((BUILD/'out/RESULT.json').read_text())
 if r['status']!='BUILD_PASS' or r['source_commit']!='15caecbbf4cb27452dbd87fa1a68a0e75098388e':raise RuntimeError('build receipt mismatch')
if '--check' in sys.argv:check();sys.exit(0)
smoke=os.environ.get('FILLER_DRYRUN')=='1'; out=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
if out.exists():raise SystemExit('result exists')
out.parent.mkdir(parents=True,exist_ok=True)
result={'id':ID,'status':'INVALID','progress':0,'cases':[],'smoke':smoke}; p=None
try:
 check()
 if smoke:
  result.update(status='SMOKE_INPUTS_PINNED',progress=1,scope='input custody only; no GPU execution')
 else:
  stop=pathlib.Path(os.environ['FILLER_STOPFILE']);deadline=float(os.environ['FILLER_DEADLINE']); env=os.environ.copy();env['LD_LIBRARY_PATH']=str(BUILD/'bin')+':/opt/rocm/lib';exe=BUILD/'bin/test-kv-rows-vec-direct'
  for case,args in [('f16',[]),('q8',['q8'])]:
   if stop.exists() or time.time()>=deadline-5:raise RuntimeError('STOP/deadline')
   log=out.parent/(case+'.log')
   with log.open('xb') as f:
    p=subprocess.Popen([str(exe),*args],stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True);pid=p.pid;samples=[]
    while p.poll() is None:
     if stop.exists() or time.time()>=deadline-5:raise RuntimeError('STOP/deadline during fixture')
     kfd=pathlib.Path('/sys/class/kfd/kfd/proc')/str(pid)
     try:
      vs={x.name:int(x.read_text()) for x in kfd.glob('vram_*')}; maps=pathlib.Path(f'/proc/{pid}/maps').read_text(); samples.append({'t':time.time_ns(),'vram':vs,'hip_mapping':str(BUILD/'bin/libggml-hip.so') in maps})
     except (OSError,ValueError):pass
     time.sleep(.05)
    rc=p.wait();p=None
   text=log.read_text(errors='replace'); witness=any(sum(s['vram'].values())>0 and s['hip_mapping'] for s in samples)
   result['cases'].append({'case':case,'pid':pid,'rc':rc,'samples':samples,'log':str(log),'log_sha256':sha(log),'residency':witness});result['progress']+=1
   if rc!=0 or not witness or 'KPF-41 direct gfx90a vec row parity passed' not in text:raise RuntimeError('fixture or residency failure: '+case)
  check();result.update(status='PARITY_PASS',scope='model-free F16/Q8 D64 direct row fixture only')
except Exception as e:result['reason']=str(e)
finally:
 if p is not None and p.poll() is None:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  result['cleanup_rc']=p.returncode
 tmp=out.with_suffix('.tmp');tmp.write_text(json.dumps(result,indent=2)+'\n');tmp.replace(out)
sys.exit(0 if result['status'] in ('PARITY_PASS','SMOKE_INPUTS_PINNED') else 1)
