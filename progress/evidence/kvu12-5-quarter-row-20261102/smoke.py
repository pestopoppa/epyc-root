#!/usr/bin/env python3
"""Native four-CPU short control; never writes target events or a verdict."""
import hashlib,json,os,pathlib,signal,subprocess,sys,time,urllib.request
D=pathlib.Path(__file__).resolve().parent
BINARY=pathlib.Path('/mnt/raid0/llm/kernels/production/cpu/llama-server')
MODEL=pathlib.Path('/mnt/raid0/llm/models/Qwen2.5-0.5B-Instruct-f16.gguf')
def identity(p):
 s=p.stat();return {k:getattr(s,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')}
def verify_model(p):
 r=json.loads((D/'MODEL-INPUTS.json').read_text())[str(p)]
 if identity(p)!=r['identity']:raise RuntimeError('prepared model identity changed')
 return r['sha256']
def cpus(text):
 out=set()
 for part in text.split(','):
  ab=list(map(int,part.split('-')));out.update(range(ab[0],ab[-1]+1))
 return out
def owns_listener(pid,port=18970):
 inodes=set()
 for line in pathlib.Path('/proc/net/tcp').read_text().splitlines()[1:]:
  cols=line.split()
  if cols[1]==f'0100007F:{port:04X}' and cols[3]=='0A':inodes.add(cols[9])
 sockets=set()
 for fd in pathlib.Path('/proc',str(pid),'fd').iterdir():
  try:target=os.readlink(fd)
  except FileNotFoundError:continue
  if target.startswith('socket:['):sockets.add(target[8:-1])
 return bool(inodes & sockets)
def check_resident_linkage(pid):
 libs={line.split()[-1] for line in pathlib.Path('/proc',str(pid),'maps').read_text().splitlines() if '/' in line and any(x in line.split()[-1] for x in ('libggml','libllama'))}
 if not any('libggml-base' in x for x in libs) or any(not pathlib.Path(x).resolve().is_relative_to(BINARY.parent.resolve()) for x in libs):raise RuntimeError('native resident linkage mismatch')
 return sorted(libs)
def run():
 if os.environ.get('FILLER_DRYRUN')!='1':raise RuntimeError('smoke requires explicit dryrun')
 allowed=sorted(cpus(os.environ['FILLER_CPUS']) & os.sched_getaffinity(0))
 if len(allowed)<4:raise RuntimeError('four granted CPUs required')
 allowed=allowed[:4];os.sched_setaffinity(0,allowed)
 dest=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
 if dest.exists() or dest==D/'events.jsonl':raise RuntimeError('fresh distinct native result required')
 model_sha=verify_model(MODEL)
 cmd=[str(BINARY),'-m',str(MODEL),'-ngl','0','-t','4','-tb','4','-c','512','-np','1','--host','127.0.0.1','--port','18970']
 root=dest.parent;root.mkdir(parents=True,exist_ok=True)
 p=None;response=None
 def stopcheck():
  if pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=float(os.environ['FILLER_DEADLINE']):raise RuntimeError('smoke stopped/deadline')
 try:
  with (root/(dest.stem+'-server.log')).open('xb') as log:
   env={**os.environ,'LD_LIBRARY_PATH':str(BINARY.parent)}
   subprocess.run(['/bin/bash','/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',str(BINARY),str(BINARY.parent)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=15)
   p=subprocess.Popen([sys.executable,str(D/'parent_exec.py'),str(os.getpid()),*cmd],stdout=log,stderr=subprocess.STDOUT,env=env)
   with open(os.environ['FILLER_PIDFILE'],'a') as f:f.write(str(p.pid)+'\n');f.flush();os.fsync(f.fileno())
   deadline=min(time.monotonic()+180,time.monotonic()+max(0,float(os.environ['FILLER_DEADLINE'])-time.time()))
   while True:
    stopcheck()
    if p.poll() is not None:raise RuntimeError('native server exited early')
    if time.monotonic()>deadline:raise RuntimeError('native server start timeout')
    try:
     with urllib.request.urlopen('http://127.0.0.1:18970/health',timeout=1) as r:
      if r.status==200 and owns_listener(p.pid):break
    except OSError:pass
    time.sleep(.2)
   masks=[set(os.sched_getaffinity(int(t.name))) for t in pathlib.Path('/proc',str(p.pid),'task').iterdir()]
   if not masks or any(not m or not m<=set(allowed) for m in masks):raise RuntimeError('native worker escaped grant')
   linkage=check_resident_linkage(p.pid)
   if not owns_listener(p.pid):raise RuntimeError('captured PID does not own listener')
   req=urllib.request.Request('http://127.0.0.1:18970/completion',data=json.dumps({'prompt':'Say hello.','n_predict':4,'temperature':0,'cache_prompt':False}).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=30) as r:response=json.load(r)
   if not isinstance(response,dict) or response.get('tokens_predicted',0)<1 or not isinstance(response.get('content'),str):raise RuntimeError('native completion invalid')
   stopcheck()
 finally:
  if p is not None:
   if p.poll() is None:
    p.terminate()
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=10)
   if p.poll() is None:raise RuntimeError('captured native server cleanup failed')
 record={'schema':'epyc.kvu125.native-smoke.v1','mode':'smoke','measurement':False,'comparison_eligible':False,'binary_sha256':hashlib.sha256(BINARY.read_bytes()).hexdigest(),'model_sha256':model_sha,'cpu_list':allowed,'threads':4,'pid':p.pid,'cleanup_verified':p.poll() is not None,'native_completion':response,'resident_linkage':linkage}
 tmp=dest.with_name(dest.name+'.tmp')
 with tmp.open('x') as f:json.dump(record,f,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 os.rename(tmp,dest)
if __name__=='__main__':run()
