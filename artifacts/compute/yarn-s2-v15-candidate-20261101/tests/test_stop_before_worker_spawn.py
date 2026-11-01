"""Check STOP around readiness and worker setup using real owned_window."""
import json,os,pathlib,subprocess,sys,tempfile,unittest
HOST=pathlib.Path(__file__).resolve().parent.parent/'host-src'
HARNESS=r'''
import json,os,sys,time,importlib.util
from pathlib import Path
sys.path.insert(0,sys.argv[1]);spec=importlib.util.spec_from_file_location("owned_window",sys.argv[3]);owned_window=importlib.util.module_from_spec(spec);spec.loader.exec_module(owned_window)
root=Path(sys.argv[2]); mode=sys.argv[4]; stop=root/'stop'; callback=root/'callback'; started=root/'worker-started'
def ready(server,identity):
 if mode=='ready':stop.touch()
 return True
def worker(server,identity):
 callback.touch()
 if mode=='callback':stop.touch()
 return [sys.executable,'-c','import pathlib,sys,time; pathlib.Path(sys.argv[1]).touch(); time.sleep(120)',str(started)]
try:owned_window.run([sys.executable,'-c','import time; time.sleep(120)'],worker,dict(os.environ),root,lambda:not stop.exists(),ready,time.monotonic()+10)
except (TimeoutError,RuntimeError):pass
print(json.dumps({'callback':callback.exists(),'started':started.exists(),'stop':stop.exists()}))
'''
class StopDuringReadiness(unittest.TestCase):
 def check(self,mode):
  with tempfile.TemporaryDirectory() as d:
   p=subprocess.run([sys.executable,'-c',HARNESS,str(HOST),d,os.environ.get('YARN_STOP_TEST_PATCH',str(HOST/'owned_window.py')),mode],capture_output=True,text=True,timeout=20)
   self.assertEqual(p.returncode,0,p.stdout+p.stderr)
   result=json.loads(p.stdout.splitlines()[-1]);self.assertTrue(result['stop']);self.assertFalse(result['started']);return result
 def test_stop_at_readiness_refuses_worker_callback(self):self.assertFalse(self.check('ready')['callback'])
 def test_stop_during_worker_setup_refuses_spawn(self):self.assertTrue(self.check('callback')['callback'])
if __name__=='__main__':unittest.main()
