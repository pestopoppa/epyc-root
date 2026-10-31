import json, unittest
from classifier import classify
class Tests(unittest.TestCase):
 def test_pre_only(self):
  line="supervisor admission refused: timing grant\n"
  self.assertEqual(classify(78,line,False),"RETRYABLE_PRE_NATIVE_ADMISSION_REFUSAL")
  for rc,log,created in [(1,line,False),(75,line,False),(78,line,True),(78,line+"extra\n",False),(78,"",False),(78,"supervisor admission refused: \n",False)]:
   self.assertEqual(classify(rc,log,created),"HALT_PRESERVE_AND_INSPECT")
 def test_failure(self):
  for failure in ["monitoring/admission gap: timing grant","post-drain admission loss: timing grant","supervisor deadline",None]:
   for rc in [1,75,78]:
    s=dict(schema="hil15-r11-smoke-supervisor/v1",elapsed_s=10,sampled_peak_tree_rss_bytes=100,child_rc=1,children_drained=True,failure=failure)
    self.assertEqual(classify(rc,json.dumps(s),True),"HALT_PRESERVE_AND_INSPECT")
 def test_pass_requires_result_validation(self):
  s=dict(schema="hil15-r11-smoke-supervisor/v1",elapsed_s=10,sampled_peak_tree_rss_bytes=100,child_rc=0,children_drained=True,failure=None)
  self.assertEqual(classify(0,json.dumps(s),True),"SUPERVISOR_PASS_REQUIRES_RESULT_VALIDATION")
  for k,v in [("failure","gap"),("children_drained",False),("elapsed_s",301),("sampled_peak_tree_rss_bytes",8*1024**3+1),("elapsed_s","bad")]:
   t=dict(s);t[k]=v;self.assertEqual(classify(0,json.dumps(t),True),"HALT_PRESERVE_AND_INSPECT")
 def test_ambiguous(self):
  self.assertEqual(classify(78,"trace\nsupervisor admission refused: x\n",False),"HALT_PRESERVE_AND_INSPECT")
if __name__=="__main__": unittest.main()
