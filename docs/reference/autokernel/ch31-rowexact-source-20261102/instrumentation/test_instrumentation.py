import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('compare_inputs',D/'compare_inputs.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def metadata():
 return ('node=node_13\nbase_source_commit='+mod.SOURCE+'\nmodel_sha256='+'a'*64+'\ninstrumentation_patch_sha256='+'b'*64+'\npregrant_receipt_sha256='+'c'*64+'\nactivation_capture=UNAVAILABLE\nrowexact_n=4\ndisable_rowexact=0\nsrc0 name=w type=q8_0 ne=32,2,1,1 nb=34,34,68,68 bytes=68 contiguous=1\nsrc1 name=x type=f32 ne=2,2,1,1 nb=4,8,16,16 bytes=16 contiguous=1\n')
class Checks(unittest.TestCase):
 def test_no_byte_capture(self):
  p=(D/'ch31-instrument.patch').read_text();self.assertNotIn('fwrite(',p);self.assertNotIn('src0.bin',p);self.assertNotIn('src1.bin',p);self.assertIn('activation_capture=UNAVAILABLE',p)
 def test_layout_rejects_empty_overlap_out_of_bounds(self):
  valid={'type':'f32','ne':[2,2,1,1],'nb':[4,8,16,16],'bytes':16};mod.validate_layout(valid)
  for delta in ({'ne':[0,2,1,1]},{'nb':[4,4,16,16]},{'nb':[4,8,16,0]},{'bytes':15},{'type':'other'}):
   with self.subTest(delta=delta),self.assertRaises(ValueError):mod.validate_layout({**valid,**delta})
 def test_duplicate_and_partial_capture_refused(self):
  with tempfile.TemporaryDirectory() as td:
   stem=Path(td)/'a';m=Path(str(stem)+'-meta.txt');r=Path(str(stem)+'-route.txt');m.write_text(metadata());r.write_text('iqk\n');mod.load(stem)
   m.write_text(metadata()+metadata().splitlines()[-1]+'\n')
   with self.assertRaisesRegex(ValueError,'duplicate tensor'):mod.load(stem)
   m.write_text(metadata());r.unlink()
   with self.assertRaises(OSError):mod.load(stem)
   r.write_text('iq');
   with self.assertRaisesRegex(ValueError,'partial route'):mod.load(stem)
 def test_valid_records_never_claim_input_equality(self):
  with tempfile.TemporaryDirectory() as td:
   a=Path(td)/'a';b=Path(td)/'b'
   for stem in (a,b):Path(str(stem)+'-meta.txt').write_text(metadata());Path(str(stem)+'-route.txt').write_text('iqk\n')
   cmd=[sys.executable,str(D/'compare_inputs.py'),str(a),str(b),'--a-row','0','--b-row','0'];run=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(run.returncode,2);x=json.loads(run.stdout);self.assertFalse(x['same_input_proven']);self.assertEqual(x['activation_identity'],'UNAVAILABLE')
 def test_descriptors_and_identity_claims_are_compared_not_trusted(self):
  with tempfile.TemporaryDirectory() as td:
   a=Path(td)/'a';b=Path(td)/'b'
   for stem in (a,b):Path(str(stem)+'-meta.txt').write_text(metadata());Path(str(stem)+'-route.txt').write_text('iqk\n')
   bmeta=Path(str(b)+'-meta.txt');bmeta.write_text(metadata().replace('model_sha256='+'a'*64,'model_sha256='+'d'*64).replace('pregrant_receipt_sha256='+'c'*64,'pregrant_receipt_sha256='+'e'*64).replace('bytes=68 contiguous=1','bytes=68 contiguous=0'))
   cmd=[sys.executable,str(D/'compare_inputs.py'),str(a),str(b),'--a-row','0','--b-row','0'];run=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(run.returncode,2);x=json.loads(run.stdout);self.assertFalse(x['src0_descriptor_equal']);self.assertTrue(x['src1_descriptor_equal']);self.assertEqual(x['identity_claims_equal'],{'model_sha256':False,'instrumentation_patch_sha256':True,'pregrant_receipt_sha256':False});self.assertFalse(x['same_input_proven']);self.assertEqual(x['weight_memory_identity'],'UNPROVEN')
if __name__=='__main__':unittest.main()
