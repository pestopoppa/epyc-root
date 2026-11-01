"""The two exact speech exceptions must not widen each other."""
import copy,importlib.util,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent;V=HERE.parents[1]/'qual_v2';sys.path.insert(0,str(V));spec=importlib.util.spec_from_file_location('speech_combined',V/'qualify_launcher.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
class CrossScope(unittest.TestCase):
 def setUp(self):self.p=HERE/'fixtures/parakeet/manifest.json';self.u=HERE/'fixtures/unified/manifest.json';self.a=q.load_manifest(self.p);self.b=q.load_manifest(self.u)
 def test_both_exact_and_unknown(self):
  for m,fn in ((self.a,q.parakeet_unknown_ok),(self.b,q.unified_unknown_ok)):
   self.assertTrue(fn(m));self.assertIsNone(q.feasible_rate(m,{}));self.assertTrue(q.feasible_window(m,None));self.assertEqual(q.feasibility_record(m,None)['feasibility'],'UNKNOWN')
  self.assertFalse(q.parakeet_unknown_ok(self.b));self.assertFalse(q.unified_unknown_ok(self.a))
 def test_swap_scopes_and_components_refused(self):
  for a,b in ((self.a,self.b),(self.b,self.a)):
   for key in ('id','production_recipe','source_manifest','speech','qualification_row','shared_state'):
    m=copy.deepcopy(a);m[key]=copy.deepcopy(b[key])
    with self.subTest(key=key):self.assertFalse(q.parakeet_unknown_ok(m));self.assertFalse(q.unified_unknown_ok(m))
   m=copy.deepcopy(a);m['rate_basis']=copy.deepcopy(b['rate_basis'])
   with tempfile.TemporaryDirectory() as td:
    p=pathlib.Path(td)/'candidate.json';p.write_text(json.dumps(m))
    with self.assertRaises(q.Refused):q.load_manifest(p)
 def test_both_require_real_receipt(self):
  for path,m in ((self.p,self.a),(self.u,self.b)):
   with patch.object(q,'load_manifest',return_value=m),patch.object(pathlib.Path,'is_file',return_value=False):
    with self.assertRaises(q.Refused):q.verify(path,pathlib.Path('/no-flags'),False)
 def test_parakeet_first_request_rule_unchanged(self):
  m=self.a;s=m['speech'];first={'ok':True,'scope':'TARGET_NATIVE_SPEECH','production_recipe_sha256':m['production_recipe']['sha256'],'manifest_sha256':m['request_manifest_sha256'],'input_sha256':s['fixture_audio']['sha256'],'pcm_sha256':s['pcm_sha256'],'source_binary_sha256':s['source_binary']['sha256'],'audio_duration_s':s['fixture_audio_seconds'],'sample_rate':s['sample_rate_hz'],'decode_mode':s['decode_mode'],'right_context':s['right_context'],'batch':s['batch_size'],'threads':2,'wall_s':1.0}
  self.assertTrue(q.first_request_ok(m,first));self.assertFalse(q.first_request_ok(m,dict(first,decode_mode='buffered-streaming-c1r0')))
  other=copy.deepcopy(m);other['speech']['qualification_decode_mode']='buffered-streaming-c1r0';self.assertTrue(q.first_request_ok(other,first))
 def test_owner_selector_and_signal_guard_remain(self):
  for m in (self.a,self.b):self.assertEqual(m['qualifier_version'],'epyc.qual-v2-row')
  s=(V/'qualify_launcher.py').read_text()
  for value in ('drain_owned_group','claim_issue_run','request_interrupt','qualification interrupted after nonce issuance'):self.assertIn(value,s)
if __name__=='__main__':unittest.main()
