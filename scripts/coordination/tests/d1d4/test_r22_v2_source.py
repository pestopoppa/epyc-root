import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
D=Path(__file__).resolve().parents[2];V2=D/'qual_v2';sys.path.insert(0,str(V2))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
q=load('r22_source_q',V2/'qualify_launcher.py');b=load('r22_source_b',V2/'batched_qual.py');gate=load('r22_source_gate',V2/'keeper_qual_gate.py');router=load('r22_source_router',D/'qual_router.py')
class SourceContract(unittest.TestCase):
 def setUp(self):self.path=Path(__file__).resolve().parent/'fixtures/r22/manifest.json';self.m=json.loads(self.path.read_text())
 def test_exact_unknown_scope_and_no_rate_fabricated(self):
  m=q.load_manifest(self.path);self.assertTrue(q.r22_unknown_calibration_ok(m));self.assertIsNone(q.feasible_rate(m,{}));self.assertTrue(q.feasible_window(m,None));self.assertEqual(q.feasibility_record(m,None),{'rate_scope':'r22-unknown-calibration','production_threads':8,'feasibility':'UNKNOWN','work_unit':'four-shape calibration'})
 def test_scope_cannot_widen(self):
  cases=[('id','other'),('class','decision'),('regions','0-95'),('window_s',43200),('gib',9),('items',2),('scratch_root','/mnt/raid0/llm/tmp/other')]
  for key,value in cases:
   m=copy.deepcopy(self.m);m[key]=value
   with self.subTest(key=key):self.assertFalse(q.r22_unknown_calibration_ok(m))
  for path in [('engine','sha256'),('production_recipe','sha256'),('job','sha256')]:
   m=copy.deepcopy(self.m);m[path[0]][path[1]]='0'*64;self.assertFalse(q.r22_unknown_calibration_ok(m))
  for key,value in [('slots',4),('prompt_tokens',32),('source_commit','0'*40)]:
   m=copy.deepcopy(self.m);m['llm']['batched'][key]=value;self.assertFalse(q.r22_unknown_calibration_ok(m))
 def test_unknown_refuses_changed_source_manifest(self):
  import dryrun_check
  m=self.m;pins={m[k]['path']:m[k]['sha256'] for k in ('production_recipe','launcher','engine','job','qual_fixture','qualification_row')}
  pins.update({m['llm']['batched'][k]['path']:m['llm']['batched'][k]['sha256'] for k in ('binary','model','hip_library')})
  with patch.object(q,'sha',side_effect=lambda path:pins[str(path)]),patch.object(dryrun_check,'checked_manifest',return_value='0'*64):
   with self.assertRaises(q.Refused):q.bound_files(m)
 def test_unknown_still_requires_receipt(self):
  with patch.object(q,'load_manifest',return_value=self.m),patch.object(Path,'is_file',return_value=False):
   with self.assertRaises(q.Refused):q.verify(self.path,Path('/no-flags'),False)
 def test_v1_stays_selected_and_unknown_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'m.json';p.write_text('{}');self.assertEqual(router.version(p),router.V1)
   p.write_text(json.dumps(self.m));self.assertEqual(router.version(p),router.V2)
   m=copy.deepcopy(self.m);m['llm']['backend']='bogus';p.write_text(json.dumps(m))
   with self.assertRaises(ValueError):router.version(p)
 def test_keeper_dispatch_paths_and_cross_version_conflict(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'m.json';path.write_text(json.dumps(self.m))
   for cmd,target in [('check',router.V2),('qualify-pending',router.V2),('conflict',router.V2),('bootstrap-row',router.V2),('canonical-row',router.V2)]:
    with self.subTest(command=cmd),patch.object(router.os,'execv',side_effect=RuntimeError('captured')) as call:
     with self.assertRaises(RuntimeError):router.main([cmd,'--manifest',str(path),'--flags','/tmp/flags'])
     self.assertEqual(call.call_args.args[1][2],str(target/'keeper_qual_gate.py'))
   path.write_text('{}')
   with patch.object(router.os,'execv',side_effect=RuntimeError('captured')) as call:
    with self.assertRaises(RuntimeError):router.main(['check','--manifest',str(path),'--flags','/tmp/flags'])
    self.assertEqual(call.call_args.args[1][2],str(router.V1/'keeper_qual_gate.py'))
 def test_ni_legacy_disjoint_overlap_and_unknown(self):
  m={'id':'candidate','regions':'72-95','ports':[],'shared_state':[],'exclusive_class':None}
  with patch.object(gate.q,'sha',return_value='pinned'):
   self.assertIsNone(gate._legacy_conflict(m,{'shared_state':[]},'peer',Path('/none'),Path('/none'),'0-23'))
   self.assertIn('region-overlap',gate._legacy_conflict(m,{},'peer',Path('/none'),Path('/none'),'168-191')[1])
  m['shared_state']=['s']
  with patch.object(gate.q,'sha',return_value='pinned'),patch.object(gate,'_owned_launcher',return_value=(1,1)),patch.object(gate,'_sidecar',side_effect=OSError):
   with self.assertRaises(gate.UnknownLegacy):gate._legacy_conflict(m,{},'peer',Path('/none'),Path('/none'),'0-23')
 def test_native_first_row_and_cross_identity(self):
  m=self.m;v=m['llm']['batched'];row={'n_kv_max':2048,'n_batch':512,'n_ubatch':512,'flash_attn':0,'is_pp_shared':0,'n_gpu_layers':99,'n_threads':2,'n_threads_batch':2,'pp':128,'tg':128,'pl':8,'n_kv':2048,'speed_tg':1.0}
  first={'ok':True,'scope':'TARGET_NATIVE_BATCHED_BENCH','manifest_sha256':m['request_manifest_sha256'],'production_recipe_sha256':m['production_recipe']['sha256'],'work_unit':m['rate_basis']['work_unit'],'argv':b.expected_argv(v),'binary_sha256':v['binary']['sha256'],'model_sha256':v['model']['sha256'],'source_commit':v['source_commit'],'native_pid':42,'native_birth_ticks':123,'native_row':row}
  self.assertTrue(b.first_ok(m,first))
  for key,value in [('n_threads',8),('n_threads_batch',96),('pl',4),('flash_attn',1),('speed_tg',float('nan'))]:
   f=copy.deepcopy(first);f['native_row'][key]=value;self.assertFalse(b.first_ok(m,f),key)
  f=copy.deepcopy(first);f['work_unit']='different';self.assertFalse(b.first_ok(m,f))
 def test_legacy_bootstrap_never_writes_registry(self):
  m=copy.deepcopy(self.m);m.pop('qualification_row')
  with tempfile.TemporaryDirectory() as tmp:
   flags=Path(tmp);(flags/'ready').mkdir();row=flags/'ready'/(m['id']+'.row.md');row.write_bytes((self.path.parent/'row.md').read_bytes());registry=flags/'FILLERS.md';registry.write_text('sentinel\n')
   with patch.object(gate.q,'load_manifest',return_value=m),patch.object(gate.q,'bound_files',return_value={}),patch.object(gate.q,'local_namespace'),patch.object(gate.q,'row_binding'):
    self.assertEqual(gate.bootstrap_row(flags/'manifest.json',flags)[0],'bad');self.assertEqual(registry.read_text(),'sentinel\n')
 def test_cutoff_requires_real_child_identity_and_native_row(self):
  source=(V2/'qualify_launcher.py').read_text();engine=(D/'filler_run14.sh').read_text()
  for key in ('native_row_ok(event','live_ok(m,event','native_birth_ticks','trigger_cutoff'):
   self.assertIn(key,source)
  self.assertIn('trigger-cutoff',engine);self.assertIn('wait "$jobpid"; qrc=$?',engine)
if __name__=='__main__':unittest.main()
