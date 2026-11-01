"""Exact predeclared Unified UNKNOWN scope: never a throughput claim."""
import copy,importlib.util,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent;V=HERE.parents[1]/'qual_v2';sys.path.insert(0,str(V));spec=importlib.util.spec_from_file_location('unified_source_q',V/'qualify_launcher.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
class UnifiedScope(unittest.TestCase):
 def setUp(self):self.path=HERE/'fixtures/unified/manifest.json';self.m=q.load_manifest(self.path)
 def test_unknown_exact_scope(self):
  self.assertTrue(q.unified_unknown_ok(self.m));self.assertIsNone(q.feasible_rate(self.m,{}));self.assertTrue(q.feasible_window(self.m,None));self.assertEqual(q.feasibility_record(self.m,None)['feasibility'],'UNKNOWN')
 def test_scope_refuses_manifest_changes(self):
  for key,value in [('qualifier_version','bad'),('id','other'),('window_s',72000),('gib',16),('shared_state',[]),('items',1)]:
   m=copy.deepcopy(self.m);m[key]=value
   with self.subTest(key=key):self.assertFalse(q.unified_unknown_ok(m))
 def test_source_drift_and_no_receipt_fail(self):
  import dryrun_check
  m=self.m;pins={m[k]['path']:m[k]['sha256'] for k in ('production_recipe','launcher','engine','job','qual_fixture','qualification_row')}
  with patch.object(q,'sha',side_effect=lambda path:pins[str(path)]),patch.object(dryrun_check,'checked_manifest',return_value='0'*64):
   with self.assertRaises(q.Refused):q.bound_files(m)
  with patch.object(q,'load_manifest',return_value=m),patch.object(pathlib.Path,'is_file',return_value=False):
   with self.assertRaises(q.Refused):q.verify(self.path,pathlib.Path('/none'),False)
 def test_qualification_proof_is_c1r0_not_six_contexts(self):
  s=self.m['speech'];first={'ok':True,'scope':'TARGET_NATIVE_SPEECH','production_recipe_sha256':self.m['production_recipe']['sha256'],'manifest_sha256':self.m['request_manifest_sha256'],'input_sha256':s['fixture_audio']['sha256'],'pcm_sha256':s['pcm_sha256'],'source_binary_sha256':s['source_binary']['sha256'],'audio_duration_s':s['fixture_audio_seconds'],'sample_rate':s['sample_rate_hz'],'decode_mode':'buffered-streaming-c1r0','right_context':0,'batch':1,'threads':2,'wall_s':1.0}
  self.assertTrue(q.first_request_ok(self.m,first))
  for mode in ('buffered-streaming-six-contexts','buffered-streaming-c1r1','native-default-auto'):
   x=dict(first,decode_mode=mode);self.assertFalse(q.first_request_ok(self.m,x))
  bad=copy.deepcopy(self.m);bad['speech']['qualification_decode_mode']='buffered-streaming-six-contexts';self.assertFalse(q.first_request_ok(bad,first))
 def test_draft_row_then_canonical_required(self):
  with tempfile.TemporaryDirectory() as td:
   f=pathlib.Path(td);(f/'ready').mkdir();(f/'FILLERS.md').write_text('| filler-id | owner |\n');m=copy.deepcopy(self.m);row=f/'ready'/(m['id']+'.row.md');row.write_bytes((HERE/'fixtures/unified/row.md').read_bytes());m['qualification_row']['path']=str(row)
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
