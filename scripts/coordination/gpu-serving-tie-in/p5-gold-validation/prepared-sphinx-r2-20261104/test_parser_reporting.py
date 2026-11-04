import json,os,subprocess,tempfile,unittest,sys
from pathlib import Path
from swebench.harness.log_parsers.python import parse_log_pytest_v2
from swebench.harness.test_spec.test_spec import make_test_spec
from offline_eval import make_offline_eval,digest_lines
from complete import validate_native
from test_native_outcome import NativeOutcome
D=Path(__file__).resolve().parent
class Reporting(unittest.TestCase):
 def test_authentic_pytest_summary_parses_failures_and_pass(self):
  # Formatter-only fixture uses system pytest; actual arms validate image pytest.
  with tempfile.TemporaryDirectory(dir=os.environ['TMPDIR']) as tmp:
   root=Path(tmp);f=root/'test_native_reporting.py'
   f.write_text('def test_fail_a(): assert False\n'+'def test_pass(): assert True\n'+'def test_fail_b(): assert False\n')
   env=dict(os.environ,PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
   proc=subprocess.run(['/usr/bin/python3','-m','pytest','-o','addopts=','-rA','--color=no',str(f)],cwd=root,env=env,capture_output=True,text=True,timeout=30)
   self.assertEqual(proc.returncode,1,proc.stdout+proc.stderr)
   statuses=parse_log_pytest_v2(proc.stdout,None)
   self.assertEqual(sorted(statuses.values()),['FAILED','FAILED','PASSED'],proc.stdout+proc.stderr)
 def test_exact_selector_and_patch_binding(self):
  case=json.loads((D/'case.json').read_text());spec=make_test_spec(case,namespace='swebench');pins=json.loads((D/'pins.json').read_text())
  out,bind=make_offline_eval(spec.eval_script_list,pins['official_script_sha256'],pins['image_id'],pins['image_id'])
  changed=[(a,b) for a,b in zip(spec.eval_script_list,out) if a!=b];self.assertEqual(len(changed),2)
  old,new=changed[1];self.assertEqual(new,old+' -rA --color=no')
  self.assertEqual(bind['reporting_only_suffix'],'-rA --color=no')
 def test_strict_predicate_accepts_complete_diagnostic_fail(self):
  helper=NativeOutcome();case={'FAIL_TO_PASS':'["f"]','PASS_TO_PASS':'["p"]'}
  for kwargs in ({},{'broken':True},{'wrong_gold':True}):
   x=helper.run_case(**kwargs);self.assertEqual(validate_native(x,case),x['decision'])
 def test_strict_predicate_rejects_missing_or_cleanup_failure(self):
  helper=NativeOutcome();case={'FAIL_TO_PASS':'["f"]','PASS_TO_PASS':'["p"]'}
  for kwargs in ({'missing':True},{'cleanup_failure':True},{'error_status':True}):
   with self.assertRaises(AssertionError):validate_native(helper.run_case(**kwargs),case)
if __name__=='__main__':unittest.main()
