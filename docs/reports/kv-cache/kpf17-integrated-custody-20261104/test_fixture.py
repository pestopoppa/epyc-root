#!/usr/bin/env python3
"""Model-free GDB witness and captured-child STOP/failure controls."""
import importlib.util,json,os,shutil,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
class Controls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='kpf17-control-',dir='/mnt/raid0/llm/tmp');self.d=Path(self.tmp.name)
  for n in ('job.py','witness.py','complete.py','fixture.c'):shutil.copy2(HERE/n,self.d/n)
  for n in ('job.py','witness.py'):
   p=self.d/n;t=p.read_text().replace('/mnt/raid0/llm/tmp/kvfork/kpf17-integrated-custody-20261104',str(self.d))
   if n=='witness.py':
    t=t.replace("(B/'test-save-load-state').resolve(strict=True)","(D/'fixture').resolve(strict=True)")
    t=t.replace('/mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf',str(self.d/'synthetic.gguf'))
   p.write_text(t)
  (self.d/'fixture.grant').write_text('synthetic fixture only\n')
  (self.d/'synthetic.gguf').write_bytes(bytes(4096))
  subprocess.run(['cc','-O0','-o',str(self.d/'fixture'),str(self.d/'fixture.c'),'-ldl'],check=True)
  bindir=self.d/'bin';bindir.mkdir();(bindir/'test-save-load-state').symlink_to(self.d/'fixture')
  realbin=Path('/mnt/micron/rtg58-integrated-c5-a58b513ba-20261102/bin')
  for lib in realbin.glob('lib*.so*'):
   if lib.is_file():(bindir/lib.name).symlink_to(lib)
  spec=importlib.util.spec_from_file_location('kpf17_custody_control',self.d/'job.py');self.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.mod);self.mod.B=self.d;self.mod.MODEL=self.d/'synthetic.gguf'
  self.real_popen=subprocess.Popen
 def tearDown(self):self.tmp.cleanup()
 def env(self):return {'KPF17_FAKE_MODEL':str(self.d/'synthetic.gguf'),'FILLER_ID':'fixture','FILLER_END':str(__import__('time').time()+150),'FILLER_GRANTS_DIR':str(self.d),'FILLER_CPUS':'0-3','FILLER_PIDFILE':str(self.d/'pids'),'FILLER_DEADLINE':str(__import__('time').time()+60),'FILLER_STOPFILE':str(self.d/'STOP'),'FILLER_DRYRUN':'0','FILLER_SMOKE':'0'}
 def run_mode(self, mode, smoke=False, stop_after_progress=True, native_failure=False):
  mod=self.mod;real=self.real_popen;d=self.d
  fake=d/'fake.py'
  fake.write_text('import subprocess,sys\nc=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"])\nc.wait()\n')
  def spawn(cmd,*a,**kw):
   if cmd[0]=='/usr/bin/gdb':
    self.assertEqual(Path(kw['cwd']),d)
    if mode=='pass':cmd=cmd[:cmd.index('--args')+1]+[str(d/'fixture')]
    elif mode=='stop':cmd=[sys.executable,str(fake)];kw['cwd']=str(d)
    else:cmd=[sys.executable,'-c','import sys;sys.exit(37)']
   return real(cmd,*a,**kw)
  if mode=='stop':
   timer=threading.Timer(1,lambda:(d/'STOP').touch());timer.start()
  env=self.env();native=d/'native-smoke.json';original_save=mod.save
  if smoke:env.update(FILLER_DRYRUN='1',FILLER_SMOKE='1',FILLER_DRYRUN_RESULT_PATH=str(native))
  if native_failure:env['KPF17_FAIL_AFTER_MODE0']='1'
  def capture(path,data):
   original_save(path,data)
   if smoke and stop_after_progress and path==native:(d/'STOP').touch()
  with patch.dict(os.environ,env,clear=False),patch.object(mod,'preflight',lambda:None),patch.object(mod.subprocess,'Popen',side_effect=spawn),patch.object(mod,'save',side_effect=capture):
   rc=mod.main()
  if mode=='stop':timer.join()
  result=d/('smoke-cleanup.json' if smoke else 'RESULT.json')
  return rc,json.loads(result.read_text())
 def test_fake_gdb_two_in_test_witnesses_per_mode(self):
  rc,r=self.run_mode('pass');self.assertEqual(rc,0,r);self.assertEqual(r['status'],'PASS');self.assertEqual(subprocess.run([sys.executable,str(self.d/'complete.py'),str(self.d/'RESULT.json')]).returncode,0);self.assertEqual([x['mode'] for x in r['witness']['samples']],[0,0,0,8,8,8]);self.assertEqual([(x['mode'],x['dest'],x['returned']) for x in r['witness']['restore_returns']],[(0,1,True),(0,2,True),(8,1,True),(8,2,True)]);self.assertTrue(all(x['dead'] for x in r['cleanup_checks']))
 def test_smoke_waits_for_test6_entry_and_reaps_debuggee(self):
  rc,r=self.run_mode('pass',smoke=True);self.assertEqual(rc,75,r);self.assertTrue(r['child_reaped'],r)
  unit=json.loads((self.d/'native-smoke.json').read_text());self.assertNotIn('qualification_only',unit);self.assertIn('not a full Test-6 result',unit['scope']);self.assertEqual(unit['test6_decode_entry_witnessed'],1);self.assertEqual(unit['n_rs_seq'],0);self.assertEqual(unit['sample']['point'],'decode_entry')
  self.assertFalse((self.d/'RESULT.json').exists());self.assertTrue((self.d/'smoke-witness.json').exists())
 def test_smoke_does_not_mask_natural_debugger_failure_after_progress(self):
  rc,r=self.run_mode('pass',smoke=True,stop_after_progress=False,native_failure=True);self.assertEqual(rc,1,r);self.assertTrue(r['child_reaped'],r)
  unit=json.loads((self.d/'native-smoke.json').read_text());self.assertEqual(unit['test6_decode_entry_witnessed'],1)
 def test_model_mapping_without_test6_entry_is_not_progress(self):
  child=(123,456);w={'pid':123,'birth_ticks':456,'nspid':[123],'exe':str((self.mod.B/'bin/test-save-load-state').resolve()),'error':None,'entries':[],'samples':[]}
  self.assertIsNone(self.mod.test6_smoke_unit(w,child))
  w['entries']=[{'mode':0,'monotonic_ns':1}];w['samples']=[{'mode':8,'point':'decode_entry'}]
  self.assertIsNone(self.mod.test6_smoke_unit(w,child))
 def test_stop_captures_and_reaps_inferior_and_supervisor(self):
  rc,r=self.run_mode('stop');self.assertEqual(rc,1);self.assertEqual(r['status'],'INVALID');self.assertTrue(r['child_reaped'],r);self.assertGreaterEqual(len(r['cleanup_checks']),2);self.assertTrue(all(x['dead'] for x in r['cleanup_checks']))
 def test_completion_refuses_missing_phase_and_live_child(self):
  r={'status':'PASS','qualification_only':False,'child_reaped':True,'witness':{'error':None,'entries':[{'mode':0},{'mode':8}],'samples':[{'mode':m,'point':p} for m in (0,8) for p in ('decode_entry','restore_dst_1','restore_dst_2')]},'cleanup_checks':[{'dead':True}]}
  f=self.d/'candidate.json';f.write_text(json.dumps(r));run=lambda:subprocess.run([sys.executable,str(self.d/'complete.py'),str(f)]).returncode
  self.assertEqual(run(),0);r['witness']['samples'].pop();f.write_text(json.dumps(r));self.assertNotEqual(run(),0)
  r['witness']['samples'].append({'mode':8,'point':'restore_dst_2'});r['cleanup_checks'][0]['dead']=False;f.write_text(json.dumps(r));self.assertNotEqual(run(),0)
 def test_wrong_inferior_executable_never_passes(self):
  w=self.d/'witness.py';w.write_text(w.read_text().replace("(D/'fixture').resolve(strict=True)","(B/'test-save-load-state').resolve(strict=True)"))
  rc,r=self.run_mode('pass');self.assertEqual(rc,1);self.assertEqual(r['status'],'INVALID');self.assertTrue(r['child_reaped'],r)
 def test_namespace_mismatch_fails_before_launch(self):
  with patch.object(self.mod.os,'readlink',return_value='999999'):
   with self.assertRaisesRegex(ValueError,'namespace mismatch'):self.mod.preflight()
 def test_gdb_failure_never_passes(self):
  rc,r=self.run_mode('fail');self.assertEqual(rc,1);self.assertEqual(r['status'],'INVALID');self.assertFalse(r['child_reaped'],r);self.assertTrue(r['cleanup_unverified'])
if __name__=='__main__':unittest.main()
