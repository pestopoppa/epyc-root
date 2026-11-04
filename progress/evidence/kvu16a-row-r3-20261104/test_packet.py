import importlib.util,json,os,re,socket,subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
import producer,job,lock_bootstrap
D=Path(__file__).resolve().parent

class PacketTests(unittest.TestCase):
 def test_frozen_render_keeps_memory_shape_and_no_weight_reads(self):
  expected=json.loads((D/'preflight.json').read_text())['plan']['rendered_argv']
  with patch.dict(os.environ,{'FILLER_DRYRUN':'0'}),patch.object(producer.os,'sched_getaffinity',return_value=set(range(184,192))),patch.object(producer,'digest',side_effect=AssertionError('render must not hash assets')):
   p,env=producer.render(19763,Path('/private/slots'))
  normalized=producer.replace_single(producer.replace_single(p['argv'][:-2],'--port',8083),'--slot-save-path',expected[expected.index('--slot-save-path')+1])
  self.assertEqual(normalized,expected);self.assertEqual(p['argv'][-2:],['-lv','4'])
  self.assertIn('--no-cache-idle-slots',p['argv'])
  self.assertEqual(env,p['effective_env'])
 def test_smoke_narrows_actual_grant_and_recipe_prefix(self):
  with patch.dict(os.environ,{'FILLER_DRYRUN':'1','FILLER_CPUS':'184-191'}),patch.object(job.os,'sched_getaffinity',return_value=set(range(184,192))),patch.object(job.os,'sched_setaffinity') as setter:
   self.assertEqual(job.grant_affinity(),[184,185,186,187]);setter.assert_called_once_with(0,[184,185,186,187])
  with patch.dict(os.environ,{'FILLER_DRYRUN':'1'}),patch.object(producer.os,'sched_getaffinity',return_value=set(range(184,188))):
   p,_=producer.render(19763,Path('/private/slots'))
   self.assertEqual(p['prefix'][p['prefix'].index('-c')+1],'184,185,186,187')
 def test_smoke_requires_four_and_full_eight_actual_cpus(self):
  for mode in ('0','1'):
   with patch.dict(os.environ,{'FILLER_DRYRUN':mode,'FILLER_CPUS':'184-186'}),patch.object(job.os,'sched_getaffinity',return_value=set(range(184,187))),patch.object(job.os,'sched_setaffinity') as setter:
    with self.assertRaises(RuntimeError):job.grant_affinity()
    setter.assert_not_called()
 def test_port_ownership_is_birth_bound(self):
  with socket.socket() as s:
   s.bind(('127.0.0.1',0));s.listen();port=s.getsockname()[1]
   birth=producer.sampler.start_ticks(Path('/proc')/str(os.getpid()))
   self.assertTrue(producer.owns_listener(port,os.getpid(),birth))
   self.assertFalse(producer.owns_listener(port,os.getpid(),birth+1))
 def test_current_registry_and_old_plan_only_allowed_diagnostic_delta(self):
  spec=json.loads((D/'spec.json').read_text())
  self.assertEqual(spec['handoff_task'],'kv-cache-program.md:KVU-16a')
  self.assertEqual(spec['lineage'],'rtg57-kvu16a-shape-load-20261102-v2')
  self.assertEqual(spec['result_path'],str(D/'RESULT.json'))
 def test_private_lock_sources_are_hash_bound(self):
  sources=lock_bootstrap.verified_sources()
  self.assertIn('src.runtime.region_lock_cli',sources)
  self.assertTrue(all('lock-source/' in p for p,blob in sources.values()))
 def test_no_generation_or_synthetic_native_smoke(self):
  source=(D/'producer.py').read_text()
  self.assertNotIn('fake_dry_run',source)
  self.assertNotIn('/completion',source)
  self.assertNotIn('start_new_session=True',(D/'server_lifecycle.py').read_text())
 def test_target_kv_discriminates_draft_and_wrong_pool(self):
  log='llama_kv_cache: size = 13056.00 MiB (393216 cells,  16 layers,  4/1 seqs), K (q8_0): 6528.00 MiB\nllama_kv_cache: size = 0.00 MiB (393216 cells, 0 layers, 4/1 seqs), K (f16): 0.00 MiB'
  pattern=r'llama_kv_cache: size =\s*([0-9.]+) MiB \(393216 cells,\s*16 layers,\s*4/1 seqs\), K \(q8_0\)'
  self.assertEqual(re.findall(pattern,log),['13056.00'])

if __name__=='__main__':unittest.main()

class RealCustodyTests(unittest.TestCase):
 def test_abrupt_worker_death_leaves_no_live_child(self):
  with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
   marker=Path(tmp)/'ready'
   code="import os,subprocess,sys,time; p=subprocess.Popen([sys.executable,sys.argv[1],str(os.getpid()),sys.executable,'-c','import pathlib,sys,time; pathlib.Path(sys.argv[1]).touch(); time.sleep(20)',sys.argv[2]]); print(p.pid,flush=True); time.sleep(20)"
   p=subprocess.Popen([sys.executable,'-c',code,str(D/'pdeath_exec.py'),str(marker)],stdout=subprocess.PIPE,text=True)
   child=int(p.stdout.readline())
   def alive():
    try:return Path(f'/proc/{child}/stat').read_text().rsplit(') ',1)[1].split()[0]!='Z'
    except FileNotFoundError:return False
   try:
    end=time.monotonic()+5
    while not marker.exists() and time.monotonic()<end:time.sleep(.02)
    self.assertTrue(marker.exists());p.kill();p.wait(timeout=5)
    end=time.monotonic()+5
    while alive() and time.monotonic()<end:time.sleep(.02)
    self.assertFalse(alive())
   finally:
    if p.poll() is None:p.kill();p.wait(timeout=5)
    if alive():os.kill(child,9)
    p.stdout.close()
 def test_deadline_watcher_interrupts_live_owned_process(self):
  import server_lifecycle
  p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'])
  done=threading.Event();server_lifecycle.ACTIVE=p
  with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp,patch.dict(os.environ,{'FILLER_STOPFILE':str(Path(tmp)/'absent'),'FILLER_DEADLINE':str(time.time()+30.2)}):
   thread=threading.Thread(target=job.watcher,args=(done,));thread.start()
   try:p.wait(timeout=5);self.assertIsNotNone(p.poll())
   finally:
    done.set();thread.join(timeout=5)
    if p.poll() is None:p.kill();p.wait(timeout=5)
    server_lifecycle.ACTIVE=None

class CoverageControls(unittest.TestCase):
 def test_original_unknown_startup_is_preserved_and_healthy_scope_explicit(self):
  source=(D/'producer.py').read_text()
  self.assertIn("'startup_unknown_samples':",source)
  self.assertIn("'raw_load_samples_path':str(samples_path)",source)
  self.assertIn("'whole_load_coverage_qualified':False",source)
  self.assertNotIn("all(x['own_vram_b'] is not None for x in observed)",source)
 def test_projection_keeps_original_shared_grader(self):
  source=(D/'vidya/adapters/kvu16a_native.py').read_text()
  self.assertIn('from claim_tuple import ProjectionError, register, to_frames',source)
  self.assertNotIn('def grade(',source)

class NativeProjectionFixture(unittest.TestCase):
 def test_existing_adapter_accepts_explicit_new_healthy_window(self):
  import hashlib,importlib.util
  spec=importlib.util.spec_from_file_location('kvu16a_native_fixture',D/'vidya/adapters/kvu16a_native.py')
  adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
  with tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu') as tmp:
   root=Path(tmp);args=['/fake/server','-m','/fake/target.gguf'];pid=123;birth=456;own=50*1024**3;kv=13056*1024**2
   rows=[{'status':'observed','phase':'healthy','pid':pid,'birth_ticks':birth,'hip_resident':True,'own_vram_b':own,'sample_start_monotonic_s':x,'sample_end_monotonic_s':x+.01} for x in (10.,10.5)]
   (root/'samples.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
   (root/'server.log').write_text('llama_kv_cache: size = 13056.00 MiB (393216 cells, 16 layers, 4/1 seqs), K (q8_0): 6528.00 MiB\n')
   plan={'belief_adapter_sha256':hashlib.sha256((D/'vidya/adapters/kvu16a_native.py').read_bytes()).hexdigest(),'producer_sha256':'a'*64,'producer_files_sha256':{n:'a'*64 for n in ('producer.py','sampler.py','device_identity.py','server_lifecycle.py')},'argv':args,'effective_env':{},'identities':{'/fake/target.gguf':'b'*64},'max_gap_seconds':1.5,'healthy_samples':2}
   result={'schema':'kvu16a.load.sampled.v1','state':{'error':None,'started_at':10.,'ended_at':10.51},'cleanup':{'verified_dead':True,'pid':pid,'birth_ticks':birth},'runtime_identity':{'argv':args,'effective_env':{},'mapped_libraries_sha256':{'fake':'c'*64}},'grant':{'FILLER_NEEDGPU':'1','FILLER_DEADLINE':'999999'},'coverage_qualified':True,'sampling_gaps_s':[0,.4900000000000002,0],'sample_count':2,'target_kv_b_from_log':kv,'healthy_sampled_max_non_kv_b':own-kv,'coverage_scope':'post-health selected-pair window only; startup unqualified','whole_load_coverage_qualified':False}
   (root/'plan.json').write_text(json.dumps(plan));(root/'result.json').write_text(json.dumps(result))
   self.assertEqual(adapter._derive(root)[3],own-kv)
   result['whole_load_coverage_qualified']=False # the old adapter does not elevate the declared scope
   rows[0]['own_vram_b']=None
   (root/'samples.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
   with self.assertRaises(ValueError):adapter._derive(root)
