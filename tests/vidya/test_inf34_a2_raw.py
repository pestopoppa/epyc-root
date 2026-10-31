"""Native-shaped fixture tests only; no model, GPU or shared ledger access."""
import copy,hashlib,json,shutil,sys,tempfile,unittest,time
from pathlib import Path
D=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(D/'scripts/vidya'))
from adapters import inf34_a2_capture as c,inf34_a2_raw as a
from claim_tuple import ProjectionError,grade
V=json.loads((D/'tests/vidya/fixtures/inf34-a2-unit-view.json').read_text())
V['cpu']=V['gpu']
class CaptureTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory(prefix='inf34-fixture-');self.base=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def fixture(self,mode='official',state='complete',root=None):
  root=Path(root) if root is not None else self.base/'fixture-run';root.mkdir();backend='cpu' if mode.startswith('control') else 'gpu';v=V[backend]
  shape={'n_prompt':16384,'reps':1,'threads':8,'ngl':99,'ubatch':512,'n_gen':0}
  if mode.startswith('control'):shape.update(n_prompt=128,threads=2,ngl=0)
  if mode.startswith('gpu-qual'):shape.update(n_prompt=8192,reps=10)
  argv=[v['private_frontend'],'-m',a.MODEL,'-p',str(shape['n_prompt']),'-n','0','-r',str(shape['reps']),'-ub','512','-t',str(shape['threads']),'-ngl',str(shape['ngl']),'-ot',c.OVERRIDE,'-o','json']
  intent=c.begin(root,{'run_id':root.name,'mode':mode,'backend':backend,'geometry':shape,'argv':argv,'models':[{'path':a.MODEL.replace('00001-of-00003',f'{n:05d}-of-00003'),'declared_sha256':h,'verification':'sidecar plus size/edge'} for n,h in enumerate(a.MODEL_SHAS,1)],'frontend_sha256':v['frontend_sha256'],'view_aliases':v['aliases'],'source_manifest_sha256':a.TRUSTED_SOURCE_SHA256,'window':{'id':'refactor-inf34-a2-raw-v12-20261031','regions':'mi210_0,0-95','grant_sha256':'0'*64},'actual_cpu_affinity':[124,125] if backend=='cpu' else list(range(184,192)),'applicability':{'model_file':a.MODEL,'quant':'UD-IQ4_XS','backend':backend,'device':'CPU' if backend=='cpu' else 'ROCm0','context_tokens':shape['n_prompt'],'scope_basis':'native','surface':'single_raw_A2','threads':shape['threads']},'created_at':'2026-10-31T00:00:00+00:00','metric':'prompt_throughput','metric_direction':'higher_better'})
  native={'build_number':10303,'build_commit':'ffc1bac82','n_prompt':shape['n_prompt'],'n_gen':0,'tensor_buft_overrides':c.OVERRIDE,'samples_ts':[100.0]*shape['reps'],'samples_ns':[1e9]*shape['reps'],'autokernel_hardened':False}
  (root/'bench.json').write_text(json.dumps([native]));(root/'bench.log').write_text('NATIVE-SHAPED UNIT FIXTURE ONLY\n')
  images=[{'path':p,'sha256':h} for p,h in {x['target']:x['sha256'] for x in v['aliases'].values()}.items()]
  samples=[{'pid':1234,'birth':7,'monotonic':time.monotonic(),'mapped_images':images,'actual_cpu_affinity':[124,125] if backend=='cpu' else list(range(184,192)),'kfd_pid_directory':backend=='gpu','device':'0' if backend=='gpu' else None,'vram_bytes':1024 if backend=='gpu' else 0} for x in (1.0,2.0)]
  (root/'samples.json').write_text(json.dumps(samples))
  attempt={'stdout':'bench.json','stderr':'bench.log','telemetry':'samples.json','state':'complete','returncode':0,'pid':1234,'birth':7,'attempted':True}
  if backend=='gpu':
   (root/'INHERITED-START.json').write_text(json.dumps({'state':'inherited-held','scope':'NATIVE_SHAPED_UNIT_FIXTURE_ONLY'}))
   (root/'INHERITED-SAMPLES.jsonl').write_text('{}\n{}\n')
   (root/'INHERITED-FINISH.json').write_text(json.dumps({'state':'inherited-held','outer_lock_held_at_finish':True,'samples':2}))
  c.finish(root,intent,[attempt],state,True)
  return root
 def rewrite_native(self,root,edit):
  p=root/'bench.json';n=json.loads(p.read_bytes());edit(n[0]);p.write_text(json.dumps(n));self.rehash_file(root,'bench.json')
 def rehash_file(self,root,name):
  p=root/'raw-a2.observation.json';r=json.loads(p.read_bytes());r['files'][name]=c.file_sha(root/name);r['content_sha256']=c.digest({k:v for k,v in r.items() if k!='content_sha256'});p.write_text(json.dumps(r))
 def test_writer_reader_standard_grader(self):
  root=self.fixture();rows=a.native_rows(root);self.assertEqual(len(rows),1)
  t=a.project(rows[0]);self.assertEqual((t.value,t.reps,t.protocol_id,t.metric_direction),(100.0,1,'','higher_better'))
  self.assertEqual(grade(t)[:2],('Judged','Located'))
 def test_actual_raw_tamper_refuses(self):
  root=self.fixture();(root/'bench.json').write_text('tampered')
  with self.assertRaises(ProjectionError):a.native_rows(root)
 def test_replay_different_root_refuses(self):
  root=self.fixture();copyroot=self.base/'replayed';shutil.copytree(root,copyroot)
  with self.assertRaises(ProjectionError):a.native_rows(copyroot)
 def test_partial_kept_but_declines_rate(self):
  root=self.fixture(state='partial');self.assertEqual(len(c.read(root)['native_rows']),1);self.assertEqual(a.native_rows(root),())
 def test_real_CPU_control_cannot_be_GPU_measurement(self):
  root=self.fixture(mode='control-normal');self.assertEqual(a.native_rows(root),())
 def test_GPU_qualification_cannot_be_full_cell(self):
  root=self.fixture(mode='gpu-qual-normal');self.assertEqual(a.native_rows(root),())
 def test_unrequested_hardened_refuses_existing_protocol_guard(self):
  root=self.fixture();self.rewrite_native(root,lambda x:x.update(autokernel_hardened=True))
  with self.assertRaisesRegex(ProjectionError,'unrequested_hardened'):a.native_rows(root)
 def test_unknown_protocol_refuses(self):
  root=self.fixture();self.rewrite_native(root,lambda x:x.pop('autokernel_hardened'))
  with self.assertRaisesRegex(ProjectionError,'unknown_protocol_strict'):a.native_rows(root)
 def test_wrong_sample_denominator_refuses(self):
  root=self.fixture();self.rewrite_native(root,lambda x:x.update(samples_ts=[100.,101.]))
  with self.assertRaises(ProjectionError):a.native_rows(root)
 def test_wrong_mapped_image_even_with_valid_file_hash_refuses(self):
  root=self.fixture();p=root/'samples.json';samples=json.loads(p.read_bytes())
  for s in samples:
   for m in s['mapped_images']:
    if 'libggml-hip.so' in m['path']:m['sha256']='a'*64
  p.write_text(json.dumps(samples));self.rehash_file(root,'samples.json')
  with self.assertRaises(ProjectionError):a.native_rows(root)
 def test_no_GPU_residency_is_not_pass(self):
  root=self.fixture();p=root/'samples.json';samples=json.loads(p.read_bytes())
  for s in samples:s['vram_bytes']=0
  p.write_text(json.dumps(samples));self.rehash_file(root,'samples.json')
  with self.assertRaises(ProjectionError):a.native_rows(root)
 def test_missing_KFD_refuses(self):
  root=self.fixture();p=root/'samples.json';samples=json.loads(p.read_bytes())
  for item in samples:item.pop('kfd_pid_directory')
  p.write_text(json.dumps(samples));self.rehash_file(root,'samples.json')
  with self.assertRaises(ProjectionError):a.native_rows(root)
 def test_false_KFD_refuses(self):
  root=self.fixture();p=root/'samples.json';samples=json.loads(p.read_bytes())
  for item in samples:item['kfd_pid_directory']=False
  p.write_text(json.dumps(samples));self.rehash_file(root,'samples.json')
  with self.assertRaises(ProjectionError):a.native_rows(root)
 def test_wrong_device_refuses(self):
  root=self.fixture();p=root/'samples.json';samples=json.loads(p.read_bytes())
  for item in samples:item['device']='1'
  p.write_text(json.dumps(samples));self.rehash_file(root,'samples.json')
  with self.assertRaises(ProjectionError):a.native_rows(root)
 def test_missing_commit_not_accepted_as_prefix(self):
  root=self.fixture();self.rewrite_native(root,lambda x:x.update(build_commit=''))
  with self.assertRaises(ProjectionError):a.native_rows(root)
 def test_create_only_preserves_original_attempt(self):
  root=self.fixture();before=(root/'intent.json').read_bytes()
  with self.assertRaises(FileExistsError):c.begin(root,{'run_id':root.name})
  self.assertEqual((root/'intent.json').read_bytes(),before)

 def test_untrusted_source_epoch_refuses(self):
  root=self.fixture();p=root/'intent.json';r=json.loads(p.read_bytes());r['source_manifest_sha256']='b'*64;r['content_sha256']=c.digest({k:v for k,v in r.items() if k!='content_sha256'});p.write_text(json.dumps(r));row=json.loads((root/'raw-a2.observation.json').read_bytes());row['intent_sha256']=c.file_sha(p);row['intent']=r;row['content_sha256']=c.digest({k:v for k,v in row.items() if k!='content_sha256'});(root/'raw-a2.observation.json').write_text(json.dumps(row))
  with self.assertRaisesRegex(ProjectionError,"unreviewed producer/source/view epoch"):a.native_rows(root)

 def rewrite_intent(self,root,edit):
  p=root/'intent.json';r=json.loads(p.read_bytes());edit(r)
  r['content_sha256']=c.digest({k:v for k,v in r.items() if k!='content_sha256'});p.write_text(json.dumps(r))
  terminal=root/'raw-a2.observation.json';row=json.loads(terminal.read_bytes());row['intent']=r;row['intent_sha256']=c.file_sha(p)
  row['content_sha256']=c.digest({k:v for k,v in row.items() if k!='content_sha256'});terminal.write_text(json.dumps(row))
 def test_wrong_applicability_cannot_poison_planner(self):
  root=self.fixture();self.rewrite_intent(root,lambda r:r['applicability'].update(model_file='/fixture/unmeasured-model.gguf'))
  with self.assertRaisesRegex(ProjectionError,'applicability contradicts'):a.native_rows(root)
 def test_wrong_affinity_even_with_matching_samples_refuses(self):
  root=self.fixture();p=root/'samples.json';rows=json.loads(p.read_bytes())
  for row in rows:row['actual_cpu_affinity']=list(range(8))
  p.write_text(json.dumps(rows));self.rehash_file(root,'samples.json')
  self.rewrite_intent(root,lambda r:r.update(actual_cpu_affinity=list(range(8))))
  with self.assertRaisesRegex(ProjectionError,'native affinity'):a.native_rows(root)

 def test_reviewed_9059_epoch_is_exact(self):
  self.assertEqual(a.TRUSTED_SOURCE_SHA256,'9059f5b6aef65e4741c74cbf3b7a35de3c7b1a30b0a2664b67a33fc4763d044e')
  root=self.fixture();self.assertEqual(len(a.native_rows(root)),1)
 def test_superseded_unexposed_11fa_epoch_refuses(self):
  root=self.fixture();self.rewrite_intent(root,lambda r:r.update(source_manifest_sha256='11fa583bb0160cc2babce6fd035014322cbbe22ac861fe5811812d1c2aec5ec7'))
  with self.assertRaisesRegex(ProjectionError,'unreviewed producer/source/view epoch'):a.native_rows(root)

if __name__=='__main__':unittest.main()


def write_fixture(tmp_path):
 case=CaptureTests();case.base=Path(tmp_path)
 return case.fixture(root=case.base/"NATIVE_SHAPED_FIXTURE_ONLY")/"raw-a2.observation.json"
