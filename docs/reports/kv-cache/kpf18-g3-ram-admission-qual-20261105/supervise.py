import hashlib,json,math,os,signal,subprocess,sys,time,uuid
from pathlib import Path
D=Path(__file__).resolve().parent
interrupted=False
def stop(sig,frame):
 global interrupted
 interrupted=True
for sig in (signal.SIGTERM,signal.SIGINT):signal.signal(sig,stop)
def main():
 mode='SMOKE_ONLY' if os.environ.get('FILLER_SMOKE')=='1' or os.environ.get('FILLER_DRYRUN')=='1' else 'MODEL_FREE_QUALIFICATION'
 result=Path(os.environ['RAM_RESULT']); end=float(os.environ['FILLER_END'])
 if not math.isfinite(end) or end<=time.time()+12:raise RuntimeError('grant end invalid/too close')
 stopfile=Path(os.environ['FILLER_STOPFILE']); cutoff=min(time.monotonic()+120,time.monotonic()+end-time.time()-7)
 def boundary():
  if interrupted or stopfile.exists() or stopfile.is_symlink():raise RuntimeError('row STOP/signal')
  if time.monotonic()>=cutoff:raise RuntimeError('workload deadline')
 def seal():
  return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.is_file() and p.name not in ('launch.sh','SEALED.sha256','STOP')}
 before=seal(); boundary()
 result.parent.mkdir(parents=True,exist_ok=True)
 if result.exists() or result.is_symlink():raise RuntimeError('result already exists')
 out=D/'out'/('smoke-' if mode=='SMOKE_ONLY' else 'full-')/uuid.uuid4().hex;out.mkdir(parents=True)
 child=None;drained=False;error=None;worker=out/'worker.json'
 try:
  env=dict(os.environ,RAM_MODE=mode,PYTHONDONTWRITEBYTECODE='1')
  with (out/'stdout.log').open('xb') as stdout,(out/'stderr.log').open('xb') as stderr:
   child=subprocess.Popen([sys.executable,'-B',str(D/'worker.py'),str(worker)],stdout=stdout,stderr=stderr,env=env)
   while child.poll() is None:boundary();time.sleep(.05)
   if child.returncode!=0:raise RuntimeError('private guard control failure')
  boundary()
 except BaseException as exc:error=str(exc)
 finally:
  if child is not None:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=2)
    except subprocess.TimeoutExpired:child.kill();child.wait(timeout=2)
   # This is the captured direct child, reaped with wait; no descendants are launched by worker.
   try:os.kill(child.pid,0)
   except ProcessLookupError:drained=True
  after=seal()
  endrecord={'mode':mode,'error':error,'captured_pid':None if child is None else child.pid,'cleanup_verified':drained,'pre_seal':before,'post_seal':after,'affinity':sorted(os.sched_getaffinity(0))}
  (out/'END.json').write_text(json.dumps(endrecord,indent=2)+'\n')
 if error or not drained or before!=after:raise RuntimeError(error or 'cleanup/source seal failure')
 boundary();data=json.loads(worker.read_text())
 data.update({'mode':mode,'cleanup_verified':True,'attempt':str(out),'source_seal':before})
 boundary();result.write_text(json.dumps(data,indent=2)+'\n')
 try:boundary()
 except BaseException:
  result.unlink(missing_ok=True)
  raise
if __name__=='__main__':main()
