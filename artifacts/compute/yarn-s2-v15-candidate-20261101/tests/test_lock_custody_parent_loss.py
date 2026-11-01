"""Reproduce the v15 custody gap with only test-owned processes and locks."""
import json, pathlib, subprocess, sys, tempfile, unittest

HARNESS = r'''
import ctypes,fcntl,json,os,signal,subprocess,sys,time
from pathlib import Path
root=Path(sys.argv[1]); hostsrc=sys.argv[2]; lock=root/'custody.lock'; ready=root/'ready'; worker_pid=root/'worker.pid'
lib=ctypes.CDLL(None,use_errno=True)
if lib.prctl(36,1,0,0,0): raise OSError(ctypes.get_errno(),'subreaper')
# The child below represents host-launch: it retains the flock in its own fd,
# but the currently committed owned_window uses close_fds=True for its worker.
host_code="""import fcntl,os,sys,time
from pathlib import Path
sys.path.insert(0,sys.argv[4]); import owned_window
fd=os.open(sys.argv[1],os.O_CREAT|os.O_RDWR,0o600); fcntl.flock(fd,fcntl.LOCK_EX)
server_code="import os,sys,time; from pathlib import Path; Path(sys.argv[1]).write_text(str(os.getpid())); Path(sys.argv[2]).touch(); time.sleep(120)"
server=[sys.executable,'-c',server_code,sys.argv[2],sys.argv[3]]
worker=[sys.executable,'-c','import time; time.sleep(120)']
owned_window.run(server,worker,dict(os.environ),Path(sys.argv[3]).parent,lambda:True,lambda p,i:False,time.monotonic()+120)
"""
host=subprocess.Popen([sys.executable,'-c',host_code,str(lock),str(worker_pid),str(ready),hostsrc])
worker=None
try:
 until=time.monotonic()+5
 while not ready.exists() and time.monotonic()<until:time.sleep(.01)
 if not ready.exists():raise RuntimeError('host readiness missing')
 worker=int(worker_pid.read_text());wfd=os.pidfd_open(worker,0)
 # PID was captured from the process we started; never use a name pattern.
 host.kill();host.wait(timeout=5)
 fd=os.open(lock,os.O_RDWR)
 try:
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  lock_reacquired=True
 finally:os.close(fd)
 worker_alive=Path('/proc',str(worker)).exists()
 print(json.dumps({'lock_reacquired_while_worker_alive':lock_reacquired and worker_alive}))
finally:
 if host.poll() is None:host.kill();host.wait(timeout=5)
 if worker is not None:
  try:signal.pidfd_send_signal(wfd,signal.SIGKILL)
  except ProcessLookupError:pass
  until=time.monotonic()+5
  while time.monotonic()<until:
   try:
    if os.waitpid(worker,os.WNOHANG)[0]==worker:break
   except ChildProcessError:break
   time.sleep(.01)
  os.close(wfd)
'''

class ParentLoss(unittest.TestCase):
    def test_reacquired_lock_while_orphan_worker_still_alive(self):
        with tempfile.TemporaryDirectory() as d:
            result = subprocess.run([sys.executable, '-c', HARNESS, d, str(pathlib.Path(__file__).resolve().parent.parent/'host-src')], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout.splitlines()[-1])['lock_reacquired_while_worker_alive'])

if __name__ == '__main__': unittest.main()
