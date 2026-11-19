import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path('/mnt/raid0/llm/worktrees/research-ds41-run10')
sys.path.insert(0,str(ROOT));sys.path.insert(1,str(ROOT/'scripts/kernel_rnd'))
from scripts.kernel_rnd.autokernel.loop import serving
from scripts.kernel_rnd.autokernel.loop.planned_serving import FrozenPromptManifest
import verification_pin as v

MANIFEST=Path('/mnt/raid0/llm/tmp/akagg-ch26b-r2-20261101/input/prompt-manifest.ds41-decode.json')

class PinTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'pin.json'
  self.recipe=SimpleNamespace(np=1,n_predict=256,temperature=0.0,top_k=1,top_p=0.95,recipe_hash='recipe-pin',name='test',env={},metric='tps',describe=lambda:{})
  m=FrozenPromptManifest.from_dict(json.loads(MANIFEST.read_bytes()))
  self.frozen=m.requests(tuple(p.prompt_id for p in m.prompts),self.recipe)
 def make(self):return v.prepare(self.path,MANIFEST,self.recipe,self.frozen,serving,FrozenPromptManifest)
 def test_actual_manifest_and_native_schedule_exclusive(self):
  pin,digest=self.make();self.assertEqual(pin['request']['request_digest'],serving.request_digest(self.recipe,self.frozen))
  self.assertEqual(pin['calibration_plan'],serving._matched_plan(24,seed=pin['calibration_plan']['seed']))
  self.assertEqual(v.sha(self.path.read_bytes()),digest)
  with self.assertRaises(FileExistsError):self.make()
 def test_rejects_missing_changed_manifest_and_request(self):
  missing=Path(self.tmp.name)/'missing';wrong=Path(self.tmp.name)/'wrong';wrong.write_bytes(MANIFEST.read_bytes()+b' ')
  for path in (missing,wrong):
   with self.subTest(path=path),self.assertRaises((OSError,ValueError)):v.prepare(self.path,path,self.recipe,self.frozen,serving,FrozenPromptManifest)
  with self.assertRaisesRegex(ValueError,'differs'):v.prepare(self.path,MANIFEST,self.recipe,((self.frozen[0][0],b'other'),),serving,FrozenPromptManifest)
  self.assertFalse(self.path.exists())
 def test_calibration_uses_pin_once_before_observation_and_restores_native(self):
  pin,digest=self.make();original=serving._matched_plan;seen=[]
  with v.use_pinned_plan(serving,self.path,pin,digest,self.frozen,self.recipe,FrozenPromptManifest):
   def fake_calibration():
    plan=serving._matched_plan(24);seen.append(('observation',plan));return plan
   self.assertEqual(fake_calibration(),pin['calibration_plan'])
  self.assertEqual(seen[0][1],pin['calibration_plan']);self.assertIs(serving._matched_plan,original)
 def test_real_native_calibrator_uses_pinned_schedule_before_stub_measurements(self):
  pin,digest=self.make(); seen=[]
  def measure(*args, **kwargs):
   seen.append(len(seen)); return 1.0
  with patch.object(serving,'_measure_once',side_effect=measure), patch.object(serving,'_matched_frame',return_value={}), patch.object(serving,'_matched_summary',return_value={}), patch.object(serving,'_resolved_launch_options',return_value={}):
   with v.use_pinned_plan(serving,self.path,pin,digest,self.frozen,self.recipe,FrozenPromptManifest):
    row=serving.calibrate_floor(self.recipe,Path('/synthetic'),samples=24,resolved_recipe=SimpleNamespace(to_dict=lambda:{}),frozen_requests=self.frozen,instrument=serving.MATCHED_INSTRUMENT,pairs=5)
  self.assertEqual(len(seen),48); self.assertEqual(row['calibration_plan'],pin['calibration_plan'])
 def test_calibration_argument_mismatch_fails_before_observation(self):
  pin,_=self.make();kw={'samples':24,'pairs':5,'instrument':serving.MATCHED_INSTRUMENT,'frozen_requests':self.frozen}
  v.verify_calibration_inputs(serving.calibrate_floor,(self.recipe,Path('/synthetic')),kw,pin,self.frozen,self.recipe)
  for key,val in [('samples',23),('pairs',4),('frozen_requests',(('wrong',b'bad'),))]:
   bad=dict(kw,**{key:val})
   with self.subTest(key=key),self.assertRaises(ValueError):v.verify_calibration_inputs(serving.calibrate_floor,(self.recipe,Path('/synthetic')),bad,pin,self.frozen,self.recipe)
 def test_refuses_tampering_wrong_draw_or_no_draw(self):
  pin,digest=self.make();original=serving._matched_plan
  with self.assertRaisesRegex(ValueError,'did not consume'):
   with v.use_pinned_plan(serving,self.path,pin,digest,self.frozen,self.recipe,FrozenPromptManifest):pass
  with self.assertRaisesRegex(ValueError,'unexpected'):
   with v.use_pinned_plan(serving,self.path,pin,digest,self.frozen,self.recipe,FrozenPromptManifest):serving._matched_plan(23)
  self.assertIs(serving._matched_plan,original)
  self.path.write_bytes(self.path.read_bytes()+b' ')
  with self.assertRaisesRegex(ValueError,'pin changed'):
   with v.use_pinned_plan(serving,self.path,pin,digest,self.frozen,self.recipe,FrozenPromptManifest):pass

if __name__=='__main__':unittest.main()
