import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
D=Path(__file__).resolve().parent
DRIVER='''import gdb, json, os, sys\nsys.path.insert(0, os.environ["EVENT_DIR"])\nimport gdb_events\nstate={}\ndef save():\n with open(os.environ["EVENT_OUTPUT"],"w") as f: json.dump(state,f)\nafter=gdb_events.install(state,save)\ndef run_test():\n gdb.execute("starti")\n try: gdb.execute("continue")\n finally: after()\n'''
class GdbEvents(unittest.TestCase):
 def run_case(self,src):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'driver.py').write_text(DRIVER)
   env=dict(os.environ,EVENT_DIR=str(D),EVENT_OUTPUT=str(root/'events.json'))
   cmd=['/usr/bin/gdb','-nx','--batch','-ex','set confirm off','-ex','source '+str(root/'driver.py'),'-ex','python run_test()','-ex','quit','--args',sys.executable,'-c',src]
   p=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=20)
   self.assertTrue((root/'events.json').exists(),p.stdout+p.stderr)
   return json.loads((root/'events.json').read_text())
 def test_normal_inferior_exit(self):
  w=self.run_case('print("hello")');ex=[e for e in w['debug_events'] if e['kind']=='exit'];self.assertEqual(len(ex),1);self.assertEqual(ex[0]['exit_code'],0);self.assertFalse(w['continue_return']['live']);self.assertEqual(ex[0]['inferior_num'],w['continue_return']['inferior_num'])
 def test_interrupted_inferior_is_not_success(self):
  w=self.run_case('import os,signal;os.kill(os.getpid(),signal.SIGTRAP)');self.assertTrue(w['continue_return']['live']);self.assertGreaterEqual(sum(e['kind']=='stop' for e in w['debug_events']),2);self.assertFalse(any(e['kind']=='exit' and e['exit_code']==0 for e in w['debug_events']))
if __name__=='__main__':unittest.main()
