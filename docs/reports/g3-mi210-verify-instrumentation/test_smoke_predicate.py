import hashlib,json,tempfile,unittest
from pathlib import Path
from smoke_predicate import valid_progress

class SmokeTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.runs=self.root/'runs'; self.cell=self.runs/'attempt-x/q8_0-d1'; self.cell.mkdir(parents=True)
  self.result=self.cell/'result.json'; self.log=self.cell/'server.log'; self.unit=self.root/'native.json'
  self.native={'status':'complete','process_group_drained':True,'requests':[{'content':'answer','tokens_predicted':5}]}
  self.log.write_text('G3_TARGET_BEGIN_V3\nG3_FATTN_DISPATCH_V3\nG3_TARGET_END_V3\n'); self.save()
 def tearDown(self): self.tmp.cleanup()
 def save(self):
  self.result.write_text(json.dumps(self.native)); row={'cell':'q8_0-d1','status':'complete','result':str(self.result),'result_sha256':hashlib.sha256(self.result.read_bytes()).hexdigest(),'server_log':str(self.log)}; self.unit.write_text(json.dumps(row)+'\n')
 def check(self): return valid_progress(self.unit,runs_root=self.runs,smoke_t0=0)
 def test_real_cell_passes(self): self.assertTrue(self.check())
 def test_rejects_placeholder_and_partial(self):
  for n in (0,None,True,-1):
   self.native['requests'][0]['tokens_predicted']=n; self.save(); self.assertFalse(self.check())
  self.native['requests'][0]['tokens_predicted']=5; self.native['process_group_drained']=False; self.save(); self.assertFalse(self.check())
 def test_changed_payload_and_trace_refused(self):
  self.result.write_text('{}'); self.assertFalse(self.check()); self.save(); self.log.write_text('not trace'); self.assertFalse(self.check())
 def test_stale_result_refused(self): self.assertFalse(valid_progress(self.unit,runs_root=self.runs,smoke_t0=10**15))
 def test_other_root_refused(self):
  other=self.root/'other'; other.mkdir()
  self.assertFalse(valid_progress(self.unit,runs_root=other,smoke_t0=0))

if __name__=='__main__': unittest.main()
