import json, subprocess, sys, tempfile, unittest
from pathlib import Path

SRC=Path(__file__).resolve().parent/'complete.py'

class CompletionPrecedence(unittest.TestCase):
 def check(self,status,*,sealed=True,dead=True,smoke=False):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'complete.py').write_bytes(SRC.read_bytes());(p/'custody.py').write_text('def digest(path): return ""\n');(p/'out').mkdir()
   (p/'binding.json').write_text(json.dumps({'build':{'x':1},'model':{'m':2}}))
   (p/'out/RESULT.json').write_text(json.dumps({'schema':'kpf17.oracle-test.v1','sealed':sealed,'smoke':smoke,'status':status,'process_verified_dead':dead,'build':{'x':1},'model':{'m':2},'files':{}}))
   return subprocess.run([sys.executable,str(p/'complete.py')]).returncode
 def test_validated_pass_allows_completion(self): self.assertEqual(self.check('PASS'),0)
 def test_invalid_never_masks_engine_stop(self):
  for reason in ('disk-floor','hard-end','stop','natural-invalid'):
   with self.subTest(reason=reason): self.assertNotEqual(self.check('INVALID'),0)
 def test_incomplete_pass_refused(self):
  for kw in ({'sealed':False},{'dead':False},{'smoke':True}):
   with self.subTest(kw=kw): self.assertNotEqual(self.check('PASS',**kw),0)
if __name__=='__main__': unittest.main()
