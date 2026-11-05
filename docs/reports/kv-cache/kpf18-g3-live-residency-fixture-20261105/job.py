#!/usr/bin/env python3
import hashlib, json, os, select, signal, subprocess, sys, time, threading
from pathlib import Path
D=Path(__file__).resolve().parent
BACKEND=Path('/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin/libggml-hip.so.0.16.0')
PIN='65063d18e76079c2e74b5ca882e72f8266c9237dc9d9f598edc50576babc51e9'
stopped=False
def stop(*_):
 global stopped; stopped=True
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
def boundary():
 if stopped or (D/'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()) or time.time()>=float(os.environ.get('FILLER_DEADLINE','9999999999')): raise RuntimeError('STOP/deadline')
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  while True:
   b=f.read(1048576)
   if not b: break
   h.update(b)
 return h.hexdigest()
def main():
 smoke=os.getenv('FILLER_SMOKE')=='1' or os.getenv('FILLER_DRYRUN')=='1'
 out=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
 if sys.argv[1:]==['--complete']:
  r=json.loads(out.read_text()); assert r['status']=='PASS' and r['samples']==7 and r['observation_seconds']>=12 and r['cleanup']; boundary(); return
 boundary()
 if digest(BACKEND)!=PIN: raise RuntimeError('backend drift')
 exe=D/('fixture-%d'%os.getpid())
 env=dict(os.environ,LD_LIBRARY_PATH=str(BACKEND.parent)+':/opt/rocm/lib',HIP_VISIBLE_DEVICES='0')
 child=None
 try:
  subprocess.run(['/opt/rocm/bin/hipcc','--offload-arch=gfx90a',str(D/'fixture.cpp'),'-ldl','-o',str(exe)],check=True,timeout=90,env=env)
  boundary(); executable_sha=digest(exe)
  child=subprocess.Popen([str(exe),str(BACKEND)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
  if not select.select([child.stdout],[],[],30)[0] or child.stdout.readline().strip()!=b'READY': raise RuntimeError('fixture did not become ready')
  import gpu_witness
  device=gpu_witness.discover(); w=gpu_witness.Witness(device,binary=exe,backend=BACKEND)
  observations=[]; begin=time.monotonic()
  for i in range(7):
   boundary(); observations.append(w.sample(child.pid))
   if i<6: threading.Event().wait(2.1)
  observation_seconds=time.monotonic()-begin
  if observation_seconds<12 or any(x['status']!='RESIDENT_SNAPSHOT' or x['own_vram_bytes']<=0 for x in observations): raise RuntimeError('live residency unknown or window too short')
  child.stdin.write(b'x');child.stdin.flush();rc=child.wait(timeout=20)
  if rc or Path('/proc',str(child.pid)).exists(): raise RuntimeError('fixture cleanup failed')
  result={'status':'PASS','samples':len(observations),'observation_seconds':observation_seconds,'observations':observations, 'binary_sha256':executable_sha,'backend_sha256':PIN,'cleanup':True,'scope':'model-free own child live snapshots only; no native gate, actual model, continuous residency, or inference verdict'}
  boundary();out.parent.mkdir(parents=True,exist_ok=True)
  with out.open('x') as f: json.dump(result,f,sort_keys=True);f.write('\n')
 finally:
  if child is not None and child.poll() is None:
   child.terminate()
   try: child.wait(timeout=5)
   except subprocess.TimeoutExpired: child.kill();child.wait(timeout=5)
  exe.unlink(missing_ok=True)
if __name__=='__main__':main()
