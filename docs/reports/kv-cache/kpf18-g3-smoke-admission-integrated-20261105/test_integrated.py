"""Actual copied admission -> publisher context -> provider witness entry, under isolated fakes."""
import importlib.util, os, sys, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).resolve().parent
ROW='kpf18-g3-provider-transport-prep-20261104'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name, BASE/path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
class IntegratedAdmission(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.flags=Path(self.tmp.name)/'flags'; (self.flags/'grants').mkdir(parents=True)
  (self.flags/'FILLERS.md').write_text('')
  self.cpus={0,1,2,3}; self.checked=[]; self.break_recheck=False
  provider=types.ModuleType('current_lock')
  def capture(row,sources):
   self.checked.append(('capture',row,len(sources)));return {'row_id':row,'owner':'fixture-owner'}
  def recheck(w):
   self.checked.append(('recheck',w['row_id']))
   if self.break_recheck:raise ValueError('provider lock lost')
   return True
  provider.capture=capture; provider.recheck=recheck
  self.module_patch=patch.dict(sys.modules,{'current_lock':provider});self.module_patch.start()
  self.smoke=load('publisher_smoke','publisher_smoke.py');sys.modules['publisher_smoke']=self.smoke
  self.lock=load('lock_witness','lock_witness.py');sys.modules['lock_witness']=self.lock
  self.original=load('original','original.py');self.corrected=load('corrected','corrected.py');self.original.FLAGS=self.flags;self.corrected.FLAGS=self.flags
  self.env=patch.dict(os.environ,{'FILLER_ID':ROW,'FILLER_SMOKE':'1','FILLER_DRYRUN':'1','FILLER_CPUS':'0-3','FILLER_THREADS':'4','FILLER_NEEDGPU':'1','FILLER_STOPFILE':str(BASE/'STOP'),'FILLER_END':'1990','FILLER_DEADLINE':'1900'},clear=False);self.env.start()
  self.clock=patch('time.time',return_value=1000);self.clock.start();self.aff=patch('os.sched_getaffinity',side_effect=lambda _: self.cpus);self.aff.start();self.disk=patch('shutil.disk_usage',return_value=types.SimpleNamespace(free=300*1024**3));self.disk.start()
 def tearDown(self):
  self.disk.stop();self.aff.stop();self.clock.stop();self.env.stop();self.module_patch.stop();self.tmp.cleanup()
 def grant(self,region,start='1970-01-01T00:00:00+00:00',end='1970-01-01T00:25:00+00:00'):
  (self.flags/'grants'/'other.grant').write_text(f'regions={region} start={start} end={end}\n'); cells=['other']+['x']*17;cells[5]='1';cells[8]='block-correctness';(self.flags/'FILLERS.md').write_text('| '+' | '.join(cells)+' |\n')
 def test_overlap(self):
  self.grant('q0');self.assertTrue(self.original.check());self.assertIn(('recheck',ROW),self.checked)
  with self.assertRaisesRegex(RuntimeError,'overlaps'):self.corrected.check()
 def test_disjoint_expired_and_explicit(self):
  self.grant('q1');self.assertTrue(self.corrected.check());self.grant('q0',end='1970-01-01T00:15:00+00:00');self.assertTrue(self.corrected.check());self.grant('2-5')
  with self.assertRaisesRegex(RuntimeError,'overlaps'):self.corrected.check()
 def test_smt_quarters(self):
  for q in range(4):
   self.cpus=set(range(96+24*q,100+24*q));os.environ['FILLER_CPUS']=f'{96+24*q}-{99+24*q}';self.grant('q'+str(q))
   with self.subTest(q=q),self.assertRaisesRegex(RuntimeError,'overlaps'):self.corrected.check()
 def test_wrong_row_rejected(self):
  os.environ['FILLER_ID']='wrong'
  with self.assertRaisesRegex(ValueError,'identity absent'):self.corrected.check()
 def test_witness_rechecked(self):
  self.assertTrue(self.corrected.check());self.break_recheck=True
  with self.assertRaisesRegex(ValueError,'lock lost'):self.corrected.check()
 def test_actual_smoke_context_required(self):
  os.environ['FILLER_CPUS']='0-2'
  with self.assertRaisesRegex(ValueError,'exactly four'):self.corrected.check()
 def test_gpu_unknown_and_hold_refused(self):
  for region,reason in [('mi210_0','GPU grant overlap'),('q4','unknown grant region')]:
   self.grant(region)
   with self.subTest(region=region),self.assertRaisesRegex(RuntimeError,reason):self.corrected.check()
  (self.flags/'HOLD_TEST').touch()
  with self.assertRaisesRegex(RuntimeError,'global HOLD'):self.corrected.check()
