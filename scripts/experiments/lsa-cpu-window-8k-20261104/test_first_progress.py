import json,os,subprocess,tempfile,time,unittest
from pathlib import Path
SCRIPT=Path(__file__).with_name('first_progress.py')
class ProgressTest(unittest.TestCase):
 def test_requires_current_native_callback_and_completed_full_result(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'state').mkdir();native=root/'native'/'attempt-1';native.mkdir(parents=True);env=dict(os.environ,FILLER_STATE_DIR=str(root/'state'),FILLER_SMOKE_T0=str(int(time.time())))
   def run(e=env):return subprocess.run(['python3',str(SCRIPT)],env=e,capture_output=True).returncode
   self.assertNotEqual(run(),0)
   trace=native/'trace.jsonl';trace.write_text(json.dumps({'layer':0,'queries':512,'allowed_before':1024})+'\n');self.assertNotEqual(run(),0)
   trace.write_text(json.dumps({'layer':3,'queries':512,'allowed_before':1024})+'\n');self.assertEqual(run(),0)
   full=dict(env);full.pop('FILLER_SMOKE_T0');self.assertNotEqual(run(full),0)
   (native/'RESULT.json').write_text(json.dumps({'status':'pass','unit':'window-exact-retrieval-8204'}));self.assertEqual(run(full),0)
   os.utime(trace,(0,0));self.assertNotEqual(run(),0)
if __name__=='__main__':unittest.main()
