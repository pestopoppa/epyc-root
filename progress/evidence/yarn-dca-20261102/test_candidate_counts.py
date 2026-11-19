import tempfile,unittest,json,os
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
import candidate_counts as m

class TestCpuGuard(unittest.TestCase):
 def test_real_cpu_artifact_closure_is_pinned_and_no_gpu_dependency(self):
  with tempfile.TemporaryDirectory() as d:
   pins=m.stage_cpu(m.CPU,Path(d))
   self.assertEqual(set(pins),set(m.PINS))
   self.assertEqual({p.name for p in Path(d).iterdir()},set(m.PINS))
 def test_gpu_candidate_refused_before_executing_anything(self):
  with tempfile.TemporaryDirectory() as d,patch.object(m.subprocess,'run') as run:
   with self.assertRaises(m.Refused):m.stage_cpu(m.c.STORE,Path(d))
   run.assert_not_called()
 def test_changed_cpu_pin_refused_before_execution(self):
  with tempfile.TemporaryDirectory() as d,patch.dict(m.PINS,{'llama-tokenize':'0'*64}),patch.object(m.subprocess,'run') as run:
   with self.assertRaises(m.Refused):m.stage_cpu(m.CPU,Path(d))
   run.assert_not_called()
 def test_unexpected_library_dependency_refused(self):
  class X:stdout='0x1 (NEEDED) Shared library: [libamdhip64.so.6]'
  with tempfile.TemporaryDirectory() as d,patch.object(m.subprocess,'run',return_value=X()):
   with self.assertRaises(m.Refused):m.stage_cpu(m.CPU,Path(d))
 def test_failure_keeps_stderr_and_partial_status(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);model=root/'model';model.write_bytes(b'x');st=model.stat()
   receipt={'status':'PASS','sha256':'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348','fd_after':{'device':st.st_dev,'inode':st.st_ino,'size_bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}}
   (root/'model-receipt.json').write_text(json.dumps(receipt));out=root/'out'
   def run(cmd,**kw):
    self.assertNotIn('GGML_BACKEND_PATH',kw['env']);self.assertNotIn('HIP_VISIBLE_DEVICES',kw['env'])
    kw['stderr'].write(b'failure diagnostic');return SimpleNamespace(returncode=1)
   inp={'bad':[],'segments':{x:'segment' for x in m.STAGES}}
   with patch.object(m,'ROOT',root),patch.object(m.c,'MODEL',str(model)),patch.object(m.y,'load_inputs',return_value=inp),patch.object(m,'stage_cpu',return_value={}),patch.object(m.subprocess,'run',side_effect=run):
    with self.assertRaises(m.Refused):m.main(out)
   self.assertEqual((out/'128k.stderr').read_bytes(),b'failure diagnostic')
   self.assertEqual(json.loads((out/'status.json').read_text())['status'],'partial_no_verdict')
if __name__=='__main__':unittest.main()
