import hashlib, importlib.util, json, pathlib, tempfile, unittest
import numpy as np
p=pathlib.Path(__file__).resolve().parents[1]/'scripts/speech/stt5_ultra_structural.py'; spec=importlib.util.spec_from_file_location('cmp',p); c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
class StructuralTests(unittest.TestCase):
 def test_unaligned_not_trimmed(self):
  r=c.stats('encoder',np.ones((3,2)),np.ones((2,2))); self.assertEqual(r['state'],'UNALIGNED'); self.assertNotIn('max_abs',r)
 def test_nonfinite_even_when_unaligned(self): self.assertEqual(c.stats('x',np.array([np.nan]),np.ones(2))['state'],'NONFINITE')
 def test_equal_shape(self):
  r=c.stats('x',np.array([1.,3.]),np.array([0.,1.])); self.assertEqual(r['max_abs'],2); self.assertEqual(r['mean_abs'],1.5)
 def test_missing_seal_and_output(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError): c.validate(d,'torch')
class FixtureTests(unittest.TestCase):
 def fixture(self, root):
  root=pathlib.Path(root)
  for arm in ('torch','f32','q8'):
   d=root/arm; d.mkdir()
   if arm=='torch':
    for name,arr in [('frontend',np.ones((1,2,128),dtype=np.float32)),('attention_mask',np.ones((1,2),dtype=np.int64)),('encoder',np.ones((1,3,1024),dtype=np.float32)),('joint_logits',np.ones((1,1,8198),dtype=np.float32))]: np.save(d/(name+'.npy'),arr)
    (d/'result.json').write_text(json.dumps({'token_ids_including_blanks':[[0,2]],'durations':[[0,3]],'audio_file_sha256':'same','pcm_sha256':hashlib.sha256(b'\0'*16).hexdigest(),'samples':4,'model_sha256':'same','processor_config_sha256':'same','generation_config_sha256':'same'}))
   else:
    for name,arr in [('mel',np.ones((2,128),dtype='<f4')),('encoder',np.ones((2,1024),dtype='<f4')),('joint_logits',np.ones((1,8198),dtype='<f4'))]: arr.tofile(d/(name+'.f32'))
    (d/'steps.tsv').write_text('0 0 2 0 3\n'); (d/'pcm.f32').write_bytes(b'\0'*16); (d/'shapes.txt').write_text('synthetic fixture\n')
   exp={'arm':arm, **{k:'same' for k in ('clip_id','catalog_sha256','wav_sha256','pcm_s16_sha256','plan_sha256','input_manifest_sha256','processor_config_sha256','generation_config_sha256','ultra_model_sha256','native_library_sha256')}}
   (root/(arm+'-run.stdout')).write_text(''); (root/(arm+'-run.stderr')).write_text('')
   (root/(arm+'.exposure.json')).write_text(json.dumps(exp))
   files={str(x.relative_to(root)):c.digest(x) for x in d.iterdir()}; files.update({arm+'-run.'+suffix:c.digest(root/(arm+'-run.'+suffix)) for suffix in ('stdout','stderr')})
   (root/(arm+'.result.json')).write_text(json.dumps({'files':files,'rc':0,'interrupted':False}))
   seal={'exposure_sha256':c.digest(root/(arm+'.exposure.json')),'result_sha256':c.digest(root/(arm+'.result.json'))}
   (root/(arm+'.seal.json')).write_text(json.dumps(seal))
 def test_fixture_and_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   self.fixture(d); report=c.compare(d,'f32'); self.assertEqual(report['comparisons'][1]['state'],'UNALIGNED'); self.assertEqual(report['verdict'],'NOT_EVALUATED')
   (pathlib.Path(d)/'f32/encoder.f32').write_bytes(b'bad')
   with self.assertRaisesRegex(ValueError,'inventory mismatch'): c.compare(d,'f32')
 def test_preflight_refuses_missing_originals_without_redraw(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d); key='a'*64; case=root/key; case.mkdir(); self.fixture(case)
   (case/'torch-run.stderr').unlink(); (case/'f32/encoder.f32').unlink()
   before={str(p.relative_to(root)):c.digest(p) for p in root.rglob('*') if p.is_file()}
   report=c.preflight(root,[key])
   self.assertFalse(report['ready']); self.assertEqual(report['arms_checked'],3)
   self.assertEqual([e['arm'] for e in report['errors']],['torch','f32'])
   self.assertIn('torch-run.stderr',report['errors'][0]['error'])
   self.assertEqual(before,{str(p.relative_to(root)):c.digest(p) for p in root.rglob('*') if p.is_file()})
 def test_preflight_requires_complete_inventories(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d); key='b'*64; case=root/key; case.mkdir(); self.fixture(case)
   self.assertTrue(c.preflight(root,[key])['ready'])
   (case/'q8/extra').write_text('unexpected')
   report=c.preflight(root,[key]); self.assertFalse(report['ready'])
   self.assertIn('inventory changed',report['errors'][0]['error'])
 def test_truncated_and_resealed(self):
  with tempfile.TemporaryDirectory() as d:
   self.fixture(d); root=pathlib.Path(d); f=root/'f32/encoder.f32'; f.write_bytes(b'\0'*12)
   result=root/'f32.result.json'; data=json.loads(result.read_text());data['files']['f32/encoder.f32']=c.digest(f);result.write_text(json.dumps(data))
   seal=root/'f32.seal.json'; data=json.loads(seal.read_text());data['result_sha256']=c.digest(result);seal.write_text(json.dumps(data))
   with self.assertRaisesRegex(ValueError,'invalid native length'): c.compare(d,'f32')
 def reseal(self,root,arm):
  root=pathlib.Path(root); result=root/(arm+'.result.json'); data=json.loads(result.read_text())
  data['files']={name:c.digest(root/name) for name in data['files']}; result.write_text(json.dumps(data))
  seal=root/(arm+'.seal.json'); data=json.loads(seal.read_text()); data['result_sha256']=c.digest(result); seal.write_text(json.dumps(data))
 def test_bool_rc_refused(self):
  with tempfile.TemporaryDirectory() as d:
   self.fixture(d); root=pathlib.Path(d); p=root/'f32.result.json'; v=json.loads(p.read_text()); v['rc']=False; p.write_text(json.dumps(v)); self.reseal(root,'f32')
   with self.assertRaisesRegex(ValueError,'invalid arm result'): c.compare(d,'f32')
 def test_added_output_refused(self):
  with tempfile.TemporaryDirectory() as d:
   self.fixture(d); (pathlib.Path(d)/'f32/extra').write_text('extra')
   with self.assertRaisesRegex(ValueError,'inventory changed'): c.compare(d,'f32')
 def test_pcm_mismatch_refused(self):
  with tempfile.TemporaryDirectory() as d:
   self.fixture(d); (pathlib.Path(d)/'f32/pcm.f32').write_bytes(b'x'*16); self.reseal(d,'f32')
   with self.assertRaisesRegex(ValueError,'decoded PCM mismatch'): c.compare(d,'f32')
 def test_nonfinite_resealed(self):
  with tempfile.TemporaryDirectory() as d:
   self.fixture(d); np.full((2,1024),np.nan,dtype='<f4').tofile(pathlib.Path(d)/'f32/encoder.f32'); self.reseal(d,'f32')
   self.assertEqual(c.compare(d,'f32')['comparisons'][1]['state'],'NONFINITE')
 def test_symlink_refused(self):
  with tempfile.TemporaryDirectory() as d:
   self.fixture(d); p=pathlib.Path(d)/'f32/encoder.f32'; p.rename(p.with_suffix('.saved')); p.symlink_to(p.with_suffix('.saved'))
   with self.assertRaisesRegex(ValueError,'symlink'): c.compare(d,'f32')
if __name__=='__main__': unittest.main()

