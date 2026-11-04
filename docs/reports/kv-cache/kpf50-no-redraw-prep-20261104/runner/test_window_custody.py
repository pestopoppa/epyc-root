import ast, hashlib, json, os, sys, tempfile, unittest
from pathlib import Path
import window_custody as c

class Receipt(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);c.begin(self.root,'full-a','r1')
 def make(self):
  ev={}
  for key in ('outcome','cleanup','clock_before','clock_after','trace_manifest'):
   x={'window':'full-a','run_id':'r1'}
   if key=='outcome':x.update(schema='kpf50.window-outcome.v1',complete=True)
   if key=='cleanup':x.update(schema='kpf50.cleanup.v1',verified_dead=True,remaining_children=0)
   name=key+'.json';b=json.dumps(x).encode();(self.root/name).write_bytes(b);ev[key]={'file':name,'sha256':hashlib.sha256(b).hexdigest()}
  b=(self.root/'full-a.start.json').read_bytes();r={'schema':'kpf50.window-complete.v1','window':'full-a','run_id':'r1','start_sha256':hashlib.sha256(b).hexdigest(),'evidence':ev}
  (self.root/'full-a.complete.json').write_text(json.dumps(r))
 def test_valid_independent_receipt(self):
  self.make();c.begin(self.root,'mask-a','r1',c.validate_prior);self.assertTrue((self.root/'mask-a.start.json').is_file())
 def test_missing_and_tamper_refused(self):
  self.make();(self.root/'cleanup.json').write_text('{}')
  with self.assertRaises(ValueError):c.begin(self.root,'mask-a','r1',c.validate_prior)
 def test_wrong_lineage_refused(self):
  self.make()
  with self.assertRaises(ValueError):c.begin(self.root,'mask-a','r2',c.validate_prior)
 def test_evidence_symlink_refused(self):
  self.make();p=self.root/'cleanup.json';p.unlink();p.symlink_to('/dev/null')
  with self.assertRaises(ValueError):c.begin(self.root,'mask-a','r1',c.validate_prior)
 def test_marker_integrated_before_request(self):
  tree=ast.parse((Path(__file__).parent/'kpf18_gate.py').read_text());fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='fan' and any(isinstance(x,ast.ImportFrom) and x.module=='window_custody' for x in ast.walk(n)))
  class Stop(Exception):pass
  class Ctx:
   def check_boundary(self):pass
  calls=[]
  def run(*a,**kw):calls.append('run');raise Stop()
  env={'arm':'fork_on','wid':'w','srv':None,'state':{},'w':0,'ctx':Ctx(),'Run':run,'os':os}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'isolated-fan','exec'),env)
  (self.root/'full-a.start.json').unlink();os.environ['KPF50_EXPOSURE_DIR']=str(self.root);os.environ['KPF50_LINEAGE_ID']='r1'
  self.addCleanup(os.environ.pop,'KPF50_EXPOSURE_DIR',None);self.addCleanup(os.environ.pop,'KPF50_LINEAGE_ID',None)
  with self.assertRaises(Stop):env['fan']()
  self.assertEqual(calls,['run']);self.assertTrue((self.root/'full-a.start.json').is_file())
  with self.assertRaises(FileExistsError):env['fan']()
if __name__=='__main__':unittest.main()
