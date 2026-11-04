import hashlib, importlib, os, pathlib, sys, tempfile, time, types, unittest
from unittest import mock
ROOT=pathlib.Path(__file__).parent
for name,digest in {'guard.py':'8c8dac0efdadb9552e0b826b1d9ba832b4a2ed6eab5393dc690319fe4b3faac3','output_reserve.py':'a763c65fc953c1ec2957b0b0784e7ed94f52b63985a12a6c633422460dd5d4fe','ledger.py':'ca2837fae282ecd0316f9216e6d03e46897168f1629ffef8437ccff1cc3fb53a'}.items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
sys.path.insert(0,str(ROOT)); import guard,output_reserve
class TestGuardOutput(unittest.TestCase):
 def test_attempt_growth_is_checked_at_each_boundary(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=pathlib.Path(tmp); root=base/'attempts'/'run-1'; root.mkdir(parents=True)
   disk=types.SimpleNamespace(free=1024**4)
   env={'KPF_OUTPUT_ROOT':str(root),'KPF_SMOKE':'1','FILLER_END':str(int(time.time())+300),'FILLER_DEADLINE':str(int(time.time())+200)}
   admission=types.SimpleNamespace(check=mock.Mock())
   with mock.patch.object(guard,'BASE',base), mock.patch.object(guard.shutil,'disk_usage',return_value=disk), mock.patch.dict(os.environ,env,clear=True), mock.patch.dict(sys.modules,{'gpu_smoke_admission':admission}):
    guard.boundary()
    with (root/'sparse').open('wb') as f: f.truncate(output_reserve.CAP)
    with self.assertRaisesRegex(RuntimeError,'output budget exhausted'):guard.boundary()
    self.assertEqual(admission.check.call_count,1)
if __name__=='__main__':unittest.main()
