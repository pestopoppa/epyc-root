"""Own server and worker until all descendants drain; bounded pipe logs."""
import os,signal,subprocess,threading,time
from pathlib import Path
import bounded_log,pidfd_custody_v2 as custody,pidfd_subreaper_v3 as subreaper
from resource_budget import ResourcePause
LIMIT=256*1024
class WindowDeadline(TimeoutError):
 pass
def run(server_argv,worker_argv,env,window,active,ready,deadline,on_cutoff=None):
 window=Path(window);processes=[];threads=[];logs=[];truncated=threading.Event();interrupted=threading.Event();errors=[];signalled={};killed=set()
 def emit(source,sink):
  try:bounded_log.drain(source,sink,LIMIT,truncated.set)
  except BaseException as e:errors.append(type(e).__name__);truncated.set()
 def spawn(argv,name):
  sink=(window/(name+'.log')).open('xb');logs.append(sink)
  p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,start_new_session=True,close_fds=True)
  processes.append(p)
  fd,ident=custody.open_child(p.pid);os.close(fd)
  t=threading.Thread(target=emit,args=(p.stdout,sink),daemon=True);threads.append(t);t.start()
  return p,ident
 def allowed():return not interrupted.is_set() and not truncated.is_set() and not errors and time.monotonic()<deadline and active()
 subreaper.enable()
 previous={sig:signal.signal(sig,lambda *_:interrupted.set()) for sig in (signal.SIGTERM,signal.SIGINT)}
 try:
  if not allowed():raise TimeoutError("admission")
  server,server_id=spawn(server_argv,"server")
  while allowed() and server.poll() is None:
   if ready(server,server_id):break
   time.sleep(.1)
  else:raise TimeoutError("server not ready")
  actual_worker=worker_argv(server,server_id) if callable(worker_argv) else worker_argv
  worker,worker_id=spawn(actual_worker,"worker")
  observer_started=False
  while allowed() and server.poll() is None and worker.poll() is None:
   if not ready(server,server_id):raise RuntimeError('server witness lost')
   if on_cutoff is not None and not observer_started and 0<deadline-time.monotonic()<=5.0:
    observer_started=True
    t=threading.Thread(target=on_cutoff,args=(server,server_id),daemon=True);threads.append(t);t.start()
   time.sleep(.1)
  if worker.poll() is None:
   if truncated.is_set() or errors:raise ResourcePause("output cap or drain failure")
   if interrupted.is_set():raise RuntimeError("interrupted before window cutoff")
   if server.poll() is not None:raise RuntimeError("server exited before window cutoff")
   if time.monotonic()>=deadline:raise WindowDeadline("actual owned worker window deadline")
   raise RuntimeError("admission lost before window cutoff")
  result={"worker_rc":worker.returncode,"worker_identity":worker_id,"server_identity":server_id}
 finally:
  warned=False
  while True:
   try:
    children=subreaper.children()
    if not children:break
    for pid in children:
     try:fd,identity=custody.open_child(pid)
     except ProcessLookupError:continue
     try:
      owned=next((p for p in processes if p.pid==pid),None)
      if owned is not None:
       if owned.poll() is not None:continue
      elif subreaper.reap(fd):continue
      key=(pid,identity["birth"])
      if key not in signalled:
       signalled[key]=time.monotonic()
       try:custody.send(fd,signal.SIGTERM)
       except ProcessLookupError:pass
      elif key not in killed and time.monotonic()-signalled[key]>=3.0:
       killed.add(key)
       try:custody.send(fd,signal.SIGKILL)
       except ProcessLookupError:pass
     finally:os.close(fd)
   except BaseException as exc:
    if not warned:print("retaining custody after drain fault",type(exc).__name__,flush=True);warned=True
   time.sleep(.1)
  for p in processes:p.poll()
  for t in threads:t.join()
  for sink in logs:sink.flush();os.fsync(sink.fileno());sink.close()
  for sig,handler in previous.items():signal.signal(sig,handler)
  if truncated.is_set() or errors:raise ResourcePause('output cap exceeded or drain failed')
 return result
