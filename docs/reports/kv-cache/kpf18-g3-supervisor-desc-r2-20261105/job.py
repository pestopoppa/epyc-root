#!/usr/bin/env python3
import hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
import owned_drain
D=Path(__file__).resolve().parent
interrupted=False
def on_signal(*_):
 global interrupted
 interrupted=True
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,on_signal)
def boundary():
 if interrupted or (D/'STOP').exists() or Path(os.environ['FILLER_STOPFILE']).exists():raise RuntimeError('STOP')
 if time.time()>=float(os.environ['FILLER_DEADLINE']):raise RuntimeError('deadline')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def seal():
 data=json.loads((D/'PINS.json').read_text())
 for n,h in data.items():
  p=D/n
  if p.is_symlink() or digest(p)!=h:raise RuntimeError('source drift: '+n)
 return data
def main():
 smoke=os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1'
 result=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
 if sys.argv[1:]==['--complete']:
  if (D/'STOP').exists(): raise RuntimeError('STOP')
  seal();r=json.loads(result.read_text());assert r['status']=='PASS' and r['case_count']==(1 if smoke else 4);return
 boundary();pins=seal()
 if owned_drain.children():raise RuntimeError('unexpected preexisting child')
 owned_drain.enable()
 p=None;fd=None;interrupted_run=None
 args=[sys.executable,'-B','-m','unittest','-v','test_real_supervisor.RealSupervisor.test_normal' if smoke else 'test_real_supervisor']
 out=D/('smoke-test.log' if smoke else 'full-test.log')
 try:
  with out.open('w') as log:
   p=subprocess.Popen(args,cwd=D,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   fd=os.pidfd_open(p.pid)
   while p.poll() is None:
    try:boundary()
    except RuntimeError as e:interrupted_run=str(e);break
    time.sleep(.1)
   if interrupted_run and p.poll() is None:
    try:signal.pidfd_send_signal(fd,signal.SIGTERM)
    except ProcessLookupError:pass
    try:p.wait(timeout=3)
    except subprocess.TimeoutExpired:
     try:signal.pidfd_send_signal(fd,signal.SIGKILL)
     except ProcessLookupError:pass
     p.wait()
   else:p.wait()
 finally:
  if p is not None and p.poll() is None:
   p.kill();p.wait()
  if fd is not None:os.close(fd)
  owned_drain.drain()
 if interrupted_run:raise RuntimeError(interrupted_run)
 boundary()
 if p.returncode!=0:raise RuntimeError('test failure; see '+str(out))
 if seal()!=pins:raise RuntimeError('source drift after controls')
 r={'status':'PASS','case_count':1 if smoke else 4,'scope':'copied supervisor, inert direct children and descendants, mocked admission/STOP/deadline; no native GPU or complete lifecycle verdict','source_pins':pins,'test_log_sha256':digest(out),'child_cleanup':'confirmed by fixture'}
 result.parent.mkdir(parents=True,exist_ok=True)
 if result.exists():raise RuntimeError('result exists')
 result.write_text(json.dumps(r,sort_keys=True)+'\n')
if __name__=='__main__':main()
