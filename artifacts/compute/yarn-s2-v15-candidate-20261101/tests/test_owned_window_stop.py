"""Exercise the real owned-window stop/drain path with only owned fake children."""
import json, os, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOST = ROOT / 'host-src'

# Isolated process is essential: subreaper ownership must never include the
# test framework's own children or any unrelated session processes.
HARNESS = r'''
import json,os,sys,threading,time
from pathlib import Path
sys.path.insert(0,sys.argv[1]); import owned_window,pidfd_subreaper_v3
root=Path(sys.argv[2]); stop=root/'stop'; worker_ready=root/'worker-ready'; grandchild=root/'grandchild'
server_code='import time; time.sleep(120)'
worker_code="import subprocess,sys,time; from pathlib import Path; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(120)']); Path(sys.argv[1]).write_text(str(p.pid)); Path(sys.argv[2]).touch(); time.sleep(120)"
server=[sys.executable,'-c',server_code]
worker=[sys.executable,'-c',worker_code,str(grandchild),str(worker_ready)]
def trigger():
  until=time.monotonic()+8
  while not worker_ready.exists() and time.monotonic()<until: time.sleep(.01)
  if worker_ready.exists(): stop.touch()
t=threading.Thread(target=trigger,daemon=True); t.start()
try:
 owned_window.run(server,worker,dict(os.environ),root,lambda: not stop.exists(),lambda p,i: True,time.monotonic()+10)
 print(json.dumps({'error':'unexpected success'}));sys.exit(2)
except RuntimeError as exc:
 t.join(1)
 if str(exc) != 'admission lost before window cutoff' or not stop.exists() or not grandchild.exists(): raise
 pid=int(grandchild.read_text())
 print(json.dumps({'stop':True,'grandchild_gone':not Path('/proc',str(pid)).exists(),'remaining_children':pidfd_subreaper_v3.children(),'exception':str(exc)}))
'''

class OwnedWindowStop(unittest.TestCase):
    def test_stop_during_active_fake_worker_drains_descendant(self):
        with tempfile.TemporaryDirectory() as d:
            run = subprocess.run([sys.executable, '-c', HARNESS, str(HOST), d],
                                 capture_output=True, text=True, timeout=20)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            result = json.loads(run.stdout.splitlines()[-1])
            self.assertTrue(result['stop'])
            self.assertTrue(result['grandchild_gone'])
            self.assertEqual(result['remaining_children'], [])

if __name__ == '__main__': unittest.main()
