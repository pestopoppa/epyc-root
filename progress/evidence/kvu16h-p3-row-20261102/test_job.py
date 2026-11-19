import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import job
class Tests(unittest.TestCase):
 def test_non_model_spec_configuration_refused(self):
  for argv in (["server","--spec-type","draft-mtp"],["server","--spec-type=draft-dflash"],["server","--spec-draft-n-max","7"]):
   with self.assertRaises(ValueError):job.p.DG.validate_request(argv,{"speculative.n_max":0})
   self.assertFalse(job.p.DG.has_drafter(job.p.DG.dedicated_no_draft_argv(argv)))
 def test_grant_cannot_widen_smoke_affinity(self):
  self.assertEqual(job.granted_cpus({'FILLER_CPUS':'184-191'}, {184,185,186,187}), '184,185,186,187')
  self.assertEqual(job.granted_cpus({'FILLER_CPUS':'184-187'}, set(range(184,192))), '184,185,186,187')
  for raw in ('','0-3','187-184','184;x'):
   with self.assertRaises(ValueError):job.granted_cpus({'FILLER_CPUS':raw},set(range(192)))
 def test_explicit_draft_counts_required(self):
  for variant in ('drafted','nodraft'):
   for value in (False,'0',-1):
    with self.assertRaises(RuntimeError):job.p.require_draft_count(variant,{'draft_n':value})
   if variant=='drafted':
    with self.assertRaises(RuntimeError):job.p.require_draft_count(variant,{})
   else:self.assertIsNone(job.p.require_draft_count(variant,{}))
  self.assertEqual(job.p.require_draft_count('nodraft',{'draft_n':0}),0)
  self.assertEqual(job.p.require_draft_count('drafted',{'draft_n':1}),1)
  with self.assertRaises(RuntimeError):job.p.require_draft_count('drafted',{'draft_n':0})
  with self.assertRaises(RuntimeError):job.p.require_draft_count('nodraft',{'draft_n':1})
 def test_grant_and_mode_required(self):
  for env in ({},{'FILLER_NEEDGPU':'1','FILLER_DRYRUN':'bogus'},{'FILLER_NEEDGPU':'0','FILLER_DRYRUN':'1'}):
   with self.assertRaises(ValueError):job.context(env)
 def test_native_result_path_and_deadline(self):
  env=dict(FILLER_NEEDGPU='1',FILLER_DRYRUN='1',FILLER_DRYRUN_RESULT_PATH='/tmp/fixture-native',FILLER_DEADLINE=str(int(time.time())+300),FILLER_PIDFILE='/tmp/pids',FILLER_STOPFILE='/tmp/stop')
  self.assertEqual(job.context(env)[2],Path('/tmp/fixture-native'))
  env['FILLER_DEADLINE']='1'
  with self.assertRaises(ValueError):job.context(env)
 def test_completion_cannot_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'result.json';job.write_result(out,{'mode':'qualification'})
   with self.assertRaises(FileExistsError):job.write_result(out,{'mode':'full'})
 def test_captured_children_stay_in_engine_group(self):
  source=Path(job.p.C.__file__).read_text()
  self.assertIn('start_new_session=False',source)
  self.assertIn('pdeath_exec.py',source)
  self.assertIn('FILLER_PIDFILE',source)
if __name__=='__main__':unittest.main()
