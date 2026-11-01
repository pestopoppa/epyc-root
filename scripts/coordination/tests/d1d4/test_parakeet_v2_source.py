"""Exact predeclared Parakeet UNKNOWN scope: never a throughput claim."""
import copy,importlib.util,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent;V=HERE.parents[1]/'qual_v2';sys.path.insert(0,str(V));spec=importlib.util.spec_from_file_location('parakeet_source_q',V/'qualify_launcher.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
class ParakeetScope(unittest.TestCase):
 def setUp(self):self.path=HERE/'fixtures/parakeet/manifest.json';self.m=q.load_manifest(self.path)
 def test_unknown_exact_scope(self):
  self.assertTrue(q.parakeet_unknown_ok(self.m));self.assertIsNone(q.feasible_rate(self.m,{}));self.assertTrue(q.feasible_window(self.m,None));self.assertEqual(q.feasibility_record(self.m,None)['feasibility'],'UNKNOWN')
 def test_scope_refuses_manifest_changes(self):
  for key,value in [('qualifier_version','bad'),('id','other'),('window_s',72000),('gib',16),('shared_state',[]),('items',1)]:
   m=copy.deepcopy(self.m);m[key]=value
   with self.subTest(key=key):self.assertFalse(q.parakeet_unknown_ok(m))
 def test_source_drift_and_no_receipt_fail(self):
  import dryrun_check
  m=self.m;pins={m[k]['path']:m[k]['sha256'] for k in ('production_recipe','launcher','engine','job','qual_fixture','qualification_row')}
  with patch.object(q,'sha',side_effect=lambda path:pins[str(path)]),patch.object(dryrun_check,'checked_manifest',return_value='0'*64):
   with self.assertRaises(q.Refused):q.bound_files(m)
  with patch.object(q,'load_manifest',return_value=m),patch.object(pathlib.Path,'is_file',return_value=False):
   with self.assertRaises(q.Refused):q.verify(self.path,pathlib.Path('/none'),False)
 def test_draft_row_then_canonical_required(self):
  with tempfile.TemporaryDirectory() as td:
   f=pathlib.Path(td);(f/'ready').mkdir();(f/'FILLERS.md').write_text('| filler-id | owner |\n');m=copy.deepcopy(self.m);row=f/'ready'/(m['id']+'.row.md');row.write_bytes((HERE/'fixtures/parakeet/row.md').read_bytes());m['qualification_row']['path']=str(row)
   q.row_binding(m,f)
   with self.assertRaises(q.Refused):q.row_binding(m,f,require_canonical=True)
   cells=[x.strip() for x in row.read_text().strip().strip('|').split('|')];cells[2]+=' pid=123';cells[3]='0-23';cells[7]='ARMED';cells[12]='y';canonical='| '+' | '.join(cells)+' |\n'
   (f/'FILLERS.md').write_text(canonical);q.row_binding(m,f,require_canonical=True)
   (f/'FILLERS.md').write_text(canonical.replace('est_output_GiB=8','est_output_GiB=9'))
   with self.assertRaises(q.Refused):q.row_binding(m,f)
 def test_drain_claim_and_version_preserved(self):
  src=(V/'qualify_launcher.py').read_text();gate=(V/'keeper_qual_gate.py').read_text()
  for token in ('drain_owned_group','claim_issue_run','request_interrupt',"'epyc.qual-v2-row'"):self.assertIn(token,src)
  self.assertIn("'claim-run'",gate);self.assertIn('run_under_claim',gate)
if __name__=='__main__':unittest.main()
