import hashlib, json, subprocess, sys, tempfile, unittest
from pathlib import Path
SRC=Path(__file__).parent/'complete.py'
class TestCompletion(unittest.TestCase):
 def run_case(self, status='PASS', mutate=None):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp); (root/'complete.py').write_bytes(SRC.read_bytes()); (root/'custody.py').write_text('import hashlib\ndef digest(p): return hashlib.sha256(open(p,"rb").read()).hexdigest()\n')
   attempt=root/'out'/'attempt-123'; attempt.mkdir(parents=True)
   files={}
   for name in ('config.json','test.log','witness.json'):
    p=attempt/name;p.write_text(name);files[str(p)]=hashlib.sha256(name.encode()).hexdigest()
   binding={'build':{'commit':'a'},'model':{'sha256':'b'}}
   result={'schema':'kpf17.oracle-test.v1','sealed':True,'smoke':False,'status':status,'process_verified_dead':True,**binding,'files':files}
   if mutate:mutate(result)
   (root/'binding.json').write_text(json.dumps(binding));(root/'out/RESULT.json').write_text(json.dumps(result))
   return subprocess.run([sys.executable,str(root/'complete.py')],capture_output=True).returncode
 def test_valid(self): self.assertEqual(self.run_case(),0)
 def test_invalid_never_complete(self): self.assertNotEqual(self.run_case(status='INVALID'),0)
 def test_empty_missing_and_wrong_files(self):
  for mutate in (lambda r:r.update(files={}),lambda r:r['files'].pop(next(iter(r['files']))),lambda r:r['files'].update({'/tmp/outsider':'0'})):
   with self.subTest(mutate=mutate):self.assertNotEqual(self.run_case(mutate=mutate),0)
 def test_changed_evidence(self): self.assertNotEqual(self.run_case(mutate=lambda r:r['files'].update({next(iter(r['files'])):'bad'})),0)
 def test_mismatched_binding(self):self.assertNotEqual(self.run_case(mutate=lambda r:r.update(build={})),0)
if __name__=='__main__':unittest.main()
