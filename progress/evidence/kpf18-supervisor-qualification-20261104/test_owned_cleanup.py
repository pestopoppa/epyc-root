import hashlib, importlib.util, os, pathlib, select, signal, subprocess, sys, types, unittest
ROOT=pathlib.Path(__file__).parent
for name,sha in {'supervisor.py':'a85612e5c878d299c83a2dcac69b6f5126136354c3243c4f38394d56a29b0a9f','owned_drain.py':'6cf1d4159ee768b762ba76f911cab16b675a4b115b1fff34cf6c3e35aa461ec4'}.items():
 assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
sys.path.insert(0,str(ROOT))
for name in ('lock_witness','gpu_smoke_admission','ram_admission'):
 sys.modules.setdefault(name,types.ModuleType(name))
import owned_drain, supervisor
CHILD='''import os,signal,subprocess,sys,time\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\ncode="import os,signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);print(os.getpid(),flush=True);time.sleep(300)"\ng=subprocess.Popen([sys.executable,"-u","-c",code],stdout=subprocess.PIPE,text=True,start_new_session=True)\nprint(g.stdout.readline().strip(),flush=True)\ntime.sleep(300)\n'''
class OwnedCleanup(unittest.TestCase):
 def test_ignoring_term_on_owned_child_and_adopted_descendant(self):
  self.assertEqual(owned_drain.children(),[])
  owned_drain.enable()
  p=None; descendant=None
  try:
   p=subprocess.Popen([sys.executable,'-u','-c',CHILD],start_new_session=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   self.assertTrue(select.select([p.stdout],[],[],5)[0], 'child setup timed out')
   descendant=int(p.stdout.readline().strip())
   self.assertGreater(descendant,1);self.assertNotEqual(descendant,p.pid)
   self.assertTrue(pathlib.Path(f'/proc/{descendant}').exists())
   supervisor.stop_process(p)
   self.assertEqual(p.returncode,-signal.SIGKILL)
   self.assertFalse(pathlib.Path(f'/proc/{p.pid}').exists())
   self.assertIn(descendant,owned_drain.children())
   owned_drain.drain()
   self.assertFalse(pathlib.Path(f'/proc/{descendant}').exists())
   self.assertEqual(owned_drain.children(),[])
   print(f'captured child={p.pid} descendant={descendant}; parent SIGKILL; descendant drained',flush=True)
   p.stdout.close();p.stderr.close();p=None;descendant=None
  finally:
   for pid in (p.pid if p else None,descendant):
    if pid:
     try: os.kill(pid,signal.SIGKILL)
     except ProcessLookupError: pass
   if p:
    try:p.wait(timeout=2)
    except subprocess.TimeoutExpired:pass
   owned_drain.drain()
if __name__=='__main__':unittest.main()
