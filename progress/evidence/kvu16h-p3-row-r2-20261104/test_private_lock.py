import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from contextlib import contextmanager
import lock_bootstrap as b
import job
class PrivateLockTests(unittest.TestCase):
 def setUp(self):
  self.saved={k:v for k,v in sys.modules.items() if k=='src' or k.startswith('src.')}
  for k in list(self.saved):del sys.modules[k]
  self.loader=b.install()
  from src.runtime import region_lock_cli
  self.cli=region_lock_cli
 def tearDown(self):
  sys.meta_path.remove(self.loader)
  for k in list(sys.modules):
   if k=='src' or k.startswith('src.'):del sys.modules[k]
  sys.modules.update(self.saved)
 def args(self):return SimpleNamespace(command=['/bin/true'],gpu_quiet='exclusive',claim_receipt_prefix=None,claim_grant_file=None,regions=None,cpu_list=None,tag='fixture',role='bench',timeout_s=1,no_preflight=False)
 def test_source_loader_excludes_shared_modules_and_bytecode(self):
  self.assertIs(self.cli.__loader__,self.loader)
  self.assertIn('lock-source',self.cli.__file__)
  with self.assertRaises(ModuleNotFoundError):__import__('src.runtime.live_telemetry')
 def test_catalog_corruption_refuses_before_import(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'fixture.py').write_text('X=1')
   (root/'lock-catalog.json').write_text(json.dumps({'modules':[{'module':'fixture','path':'fixture.py','sha256':'0'*64}]}))
   with self.assertRaises(ValueError):b.verified_sources(root)
 def test_dryrun_preserves_no_lock_policy_and_four_cpu_taskset(self):
  with patch.dict('os.environ',{'FILLER_DRYRUN':'1','WS58_REGIONS':'184-187'}),patch.object(self.cli.subprocess,'call',return_value=0) as call,patch.object(self.cli,'gpu_quiet_then_regions') as claim:
   self.assertEqual(self.cli._run(self.args()),0)
   call.assert_called_once_with(['taskset','-c','184-187','/bin/true']);claim.assert_not_called()
 def test_full_retains_exclusive_gpu_provider_path(self):
  seen=[]
  @contextmanager
  def claim(*args,**kwargs):seen.append(kwargs);yield {'regions':[]}
  with patch.dict('os.environ',{'FILLER_DRYRUN':'0','FILLER_SMOKE':'0'}),patch.object(self.cli,'_resolve_regions',return_value=frozenset()),patch.object(self.cli,'gpu_quiet_then_regions',claim),patch.object(self.cli,'_spawn',return_value=0):
   self.assertEqual(self.cli._run(self.args()),0)
  self.assertEqual(seen[0]['gpu_quiet'],'exclusive')
 def test_eight_cpu_smoke_is_narrowed_to_exact_four(self):
  self.assertEqual(job.granted_cpus({'FILLER_DRYRUN':'1','FILLER_CPUS':'184-191'},set(range(184,192))),'184,185,186,187')
  with self.assertRaises(ValueError):job.granted_cpus({'FILLER_DRYRUN':'1','FILLER_CPUS':'184-186'},set(range(184,192)))
 def test_full_eight_cpu_shape_preserved(self):
  self.assertEqual(job.granted_cpus({'FILLER_DRYRUN':'0','FILLER_CPUS':'184-191'},set(range(184,192))),'184,185,186,187,188,189,190,191')
if __name__=='__main__':unittest.main()
