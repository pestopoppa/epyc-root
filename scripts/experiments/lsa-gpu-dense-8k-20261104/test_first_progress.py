import json,os,subprocess,tempfile,time,unittest
from pathlib import Path
SCRIPT=Path(__file__).with_name('first_progress.py')
class PredicateTest(unittest.TestCase):
 def test_fresh_token_for_smoke_and_terminal_record_for_grant(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'state').mkdir();a=root/'native'/'attempt-1';a.mkdir(parents=True)
   env=dict(os.environ,FILLER_STATE_DIR=str(root/'state'),FILLER_SMOKE_T0=str(int(time.time())))
   run=lambda e:subprocess.run(['python3',str(SCRIPT)],env=e,capture_output=True).returncode
   self.assertNotEqual(run(env),0)
   f=a/'first-token.json';f.write_text(json.dumps({'unit':'dense-first-token'}));self.assertEqual(run(env),0)
   os.utime(f,(0,0));self.assertNotEqual(run(env),0)
   actual=dict(env);actual.pop('FILLER_SMOKE_T0');self.assertNotEqual(run(actual),0)
   (root/'native'/'RESULT.json').write_text(json.dumps({'unit':'dense-bf16-dev-8204','status':'failure'}));self.assertEqual(run(actual),0)
if __name__=='__main__':unittest.main()
