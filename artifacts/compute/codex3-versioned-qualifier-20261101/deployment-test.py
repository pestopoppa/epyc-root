"""Apply reviewed patch to copies; compare commit payload and unchanged v1."""
import hashlib,os,pathlib,shutil,subprocess,tempfile,unittest
from unittest.mock import patch
D=pathlib.Path(__file__).resolve().parent;F=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags');S=D.parents[2]/'scripts/coordination';PATCH=D/'deployment.patch'
BASE={'ws58-calendar-keeper-v8.sh':'a8fc18c67f08fed08c1f74e629083d55cbcd1b9560b21d3029e0e9e0f7b4e5a7','grant_ok.sh':'2e40f0cf5e93e91c1a55f2d3a22e0e08a209555cdb06c90181764f7546978908'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files(p):return {str(f.relative_to(p)):sha(f) for f in p.rglob('*') if f.is_file()}
class Deploy(unittest.TestCase):
 def test_apply_and_preserve_v1_and_selector(self):
  for n,h in BASE.items():self.assertEqual(sha(F/n),h)
  paths=[line[6:] for line in PATCH.read_text().splitlines() if line.startswith('+++ b/')]
  self.assertNotIn('ws58-calendar-keeper.current',paths);self.assertFalse(any(x.startswith('bin/qual-v1/') for x in paths))
  with tempfile.TemporaryDirectory() as td:
   root=pathlib.Path(td)
   for n in BASE:shutil.copy2(F/n,root/n)
   selector='ws58-calendar-keeper.current';shutil.copy2(F/selector,root/selector);sel_before=(root/selector).read_bytes()
   shutil.copytree(F/'bin/qual-v1',root/'bin/qual-v1',ignore=shutil.ignore_patterns('__pycache__'));v1_before=files(root/'bin/qual-v1');(root/'bin/qual-v2-row').mkdir(parents=True)
   for args in (['git','apply','--check',str(PATCH)],['git','apply',str(PATCH)]):subprocess.run(args,cwd=root,check=True,capture_output=True)
   self.assertEqual(files(root/'bin/qual-v1'),v1_before);self.assertEqual((root/selector).read_bytes(),sel_before)
   line=next(line.strip() for line in (root/'ws58-calendar-keeper-v8.sh').read_text().splitlines() if line.strip().startswith("gate = os.environ.get('WS58_QUAL_GATE'"))
   with patch.dict(os.environ,{},clear=True):
    scope={'os':os};exec(line,scope);self.assertEqual(scope['gate'],'/mnt/raid0/llm/tmp/compute-flags/bin/qual-router-v1.py')
   with patch.dict(os.environ,{'WS58_QUAL_GATE':'/tmp/custom'}):
    scope={'os':os};exec(line,scope);self.assertEqual(scope['gate'],'/tmp/custom')
   self.assertEqual((root/'bin/qual-router-v1.py').read_bytes(),(S/'qual_router.py').read_bytes())
   v2=root/'bin/qual-v2-row';self.assertEqual({p.name for p in v2.iterdir()},{p.name for p in (S/'qual_v2').iterdir() if p.is_file()})
   for p in v2.iterdir():self.assertEqual(p.read_bytes(),(S/'qual_v2'/p.name).read_bytes())
   for n in BASE:subprocess.run(['bash','-n',str(root/n)],check=True,capture_output=True)
if __name__=='__main__':unittest.main()
