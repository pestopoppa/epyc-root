"""Execute the prepared job's actual control loop with synthetic scorer outcomes."""
import ast,json,os,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
D=Path(__file__).parent
loop=next(n for n in reversed(ast.parse((D/'job.py').read_text()).body) if isinstance(n,ast.Try))
code=compile(ast.fix_missing_locations(ast.Module(body=[loop],type_ignores=[])),'job-control-loop','exec')
class NativeOutcome(unittest.TestCase):
 def run_case(self,broken=False,smoke=False,cleanup_failure=False):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);case={'instance_id':'case','FAIL_TO_PASS':'["f"]','PASS_TO_PASS':'["p"]'}
   arms=[('negative','noop'),('gold','patch')]
   statuses={}
   def run(spec,pred,*args,**kwargs):
    arm=pred['model_name_or_path'];folder=root/'logs/run_evaluation'/kwargs['run_id'] if 'run_id' in kwargs else root/'logs/run_evaluation'/args[3]
    folder=folder/arm/'case';folder.mkdir(parents=True)
    (folder/'report.json').write_text(json.dumps({'case':{'resolved':(arm=='gold') or broken}}))
    (folder/'test_output.txt').touch();statuses.update(f='PASSED' if arm=='gold' else 'FAILED',p='PASSED')
    return {'completed':True}
   def cleanup():
    if cleanup_failure:raise RuntimeError('cleanup refused')
   result={'schema':'p5.gold-control.v1','arms':{}}
   ns={'D':root,'Path':Path,'json':json,'os':os,'case':case,'arms':arms,'spec':None,'client':None,'result':result,'smoke':smoke,'deadline':10000,'time':types.SimpleNamespace(time=lambda:1,time_ns=lambda:1),'ev':types.SimpleNamespace(run_instance=run),'get_logs_eval':lambda *a:(statuses.copy(),True),'cleanup':cleanup}
   with patch.dict(os.environ,FILLER_ID='synthetic',FILLER_DRYRUN_RESULT_PATH=str(root/'RESULT.json')):
    try:exec(code,ns)
    except (AssertionError,RuntimeError):pass
   return json.loads((root/'RESULT.json').read_text())
 def test_full_native_success(self):
  x=self.run_case();self.assertEqual(x['status'],'PASS');self.assertTrue(x['owned_containers_removed']);self.assertEqual(set(x['arms']),{'gold','negative'})
 def test_wrong_negative_cannot_pass_full_or_smoke(self):
  for smoke in (False,True):self.assertEqual(self.run_case(broken=True,smoke=smoke)['status'],'FAIL')
 def test_cleanup_failure_cannot_pass(self):self.assertEqual(self.run_case(cleanup_failure=True)['status'],'FAIL')
 def test_smoke_runs_full_controls(self):
  x=self.run_case(smoke=True);self.assertEqual(x['status'],'PASS');self.assertEqual(set(x['arms']),{'gold','negative'})
if __name__=='__main__':unittest.main()
