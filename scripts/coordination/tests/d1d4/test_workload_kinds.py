#!/usr/bin/env python3
import copy,importlib.util,json,os,pathlib,tempfile,unittest
BASE=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('qualify_launcher',BASE/'qualify_launcher.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
PIN={'path':'/mnt/raid0/llm/tmp/fixture','sha256':'a'*64}
def base(root):
 rid='typed-test';return {'schema':'epyc.ready.v2','production':True,'workload_kind':'llm','id':rid,'owner':'codex3',
  'regions':'132-133','window_s':7200,'min_window_s':60,'gib':1,'scratch_root':str(root),
  'launcher':PIN,'engine':PIN,'job':PIN,'qual_fixture':{**PIN,'items':2},'source_manifest':'/mnt/raid0/llm/tmp/source',
  'request_manifest_sha256':'b'*64,'requires_tools':['python3'],'ports':[],'shared_state':[],'exclusive_class':None,
  'production_recipe':PIN,
  'items':2,'kv_cache_mode':'split','n_ctx_required':262144,'per_slot_n_ctx_required':65536,'n_parallel_required':4,
  'prompt_tokens_required':200,'tokens_per_item':96,'est_output_GiB':1,'job_floor_gib':150,
  'rate_basis':{'scope':'qualification-same-recipe','production_threads':2},
  'qualification':{'receipt':str(root/'qualification'/f'QUAL-{rid}.json')}}
class Typed(unittest.TestCase):
 def write(self,m):
  p=pathlib.Path(m['scratch_root'])/'manifest.json';p.write_text(json.dumps(m));return p
 def test_llm_context_never_dummy(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   m=base(pathlib.Path(td));q.load_manifest(self.write(m))
   for key in ('kv_cache_mode','n_ctx_required','per_slot_n_ctx_required','n_parallel_required','prompt_tokens_required','tokens_per_item'):
    wrong=copy.deepcopy(m);wrong.pop(key)
    with self.assertRaisesRegex(q.Refused,key):q.load_manifest(self.write(wrong))
 def test_unified_kv_and_full_work_unit_feasibility(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   m=base(pathlib.Path(td));m['kv_cache_mode']='unified';m['n_ctx_required']=393216
   m['per_slot_n_ctx_required']=262144;m['n_parallel_required']=4
   m['rate_basis']={'scope':'calibrated-work-unit','production_threads':8,
                   'wall_s_per_unit':900,'work_unit':'E1-A1-high-400k-plus-500k','evidence':PIN}
   m.pop('tokens_per_item');m['items']=2
   q.load_manifest(self.write(m))
   self.assertTrue(q.feasible_window(m,900))
   first={'ok':True,'scope':'TARGET_SCRATCH_SERVER','production_recipe_sha256':'a'*64,
          'manifest_sha256':'b'*64,'kv_cache_mode':'unified','n_ctx_total':393216,
          'n_ctx_per_slot':262144,'total_slots':4,'prompt_tokens':200,
          'work_unit':'E1-A1-high-400k-plus-500k'}
   self.assertTrue(q.first_request_ok(m,first))
   self.assertFalse(q.first_request_ok(m,dict(first,kv_cache_mode='split')))
   split=copy.deepcopy(m);split['kv_cache_mode']='split'
   with self.assertRaisesRegex(q.Refused,'context/parallel'):q.load_manifest(self.write(split))
 def test_speech_units_and_source_identity(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   m=base(pathlib.Path(td));m['workload_kind']='speech'
   for key in ('kv_cache_mode','n_ctx_required','per_slot_n_ctx_required','n_parallel_required','prompt_tokens_required','tokens_per_item'):m.pop(key)
   m['speech']={'fixture_audio':PIN,'source_catalog':PIN,'source_binary':PIN,'pcm_sha256':'c'*64,
    'fixture_audio_seconds':11.2,'planned_audio_seconds':1200,'sample_rate_hz':16000,'decode_mode':'streaming_greedy',
    'right_context':'UNKNOWN','batch_size':1,'threads':8}
   m['rate_basis']={'scope':'speech-calibrated-production','production_threads':8,'batch_size':1,
    'decode_mode':'streaming_greedy','rtf':2.0,'evidence':PIN}
   q.load_manifest(self.write(m))
   first={'ok':True,'scope':'TARGET_NATIVE_SPEECH','production_recipe_sha256':'a'*64,'manifest_sha256':'b'*64,'input_sha256':'a'*64,
    'pcm_sha256':'c'*64,'source_binary_sha256':'a'*64,'audio_duration_s':11.2,'sample_rate':16000,
    'decode_mode':'streaming_greedy','right_context':'UNKNOWN','batch':1,'threads':2,'wall_s':8.0}
   self.assertTrue(q.first_request_ok(m,first));self.assertTrue(q.feasible_window(m,2.0))
   self.assertFalse(q.first_request_ok(m,dict(first,sample_rate=8000)))
   self.assertFalse(q.first_request_ok(m,dict(first,input_sha256='0'*64)))
   self.assertFalse(q.first_request_ok(m,dict(first,scope='TARGET_SCRATCH_SERVER')))
   self.assertFalse(q.feasible_window(m,7.0))
   dummy=copy.deepcopy(m);dummy['n_ctx_required']=1
   with self.assertRaisesRegex(q.Refused,'must not invent'):q.load_manifest(self.write(dummy))
   wrong=copy.deepcopy(m);wrong['rate_basis']['batch_size']=2
   with self.assertRaisesRegex(q.Refused,'mismatch'):q.load_manifest(self.write(wrong))
 def test_command_real_work_units(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   m=base(pathlib.Path(td));m['workload_kind']='command'
   for key in ('kv_cache_mode','n_ctx_required','per_slot_n_ctx_required','n_parallel_required','prompt_tokens_required','tokens_per_item'):m.pop(key)
   m['command']={'work_unit':'compile-target','planned_work_units':4}
   m['rate_basis']={'scope':'command-same-recipe','production_threads':2}
   q.load_manifest(self.write(m))
   first={'ok':True,'scope':'COMMAND_NATIVE','production_recipe_sha256':'a'*64,'manifest_sha256':'b'*64,'work_unit':'compile-target',
          'work_completed':1,'wall_s':2.0,'measured_work_units_per_s':0.5}
   self.assertTrue(q.first_request_ok(m,first));self.assertTrue(q.feasible_window(m,0.5))
   self.assertFalse(q.first_request_ok(m,dict(first,work_unit='tokens')))
 def test_prework_cutoff_cannot_produce_production_partial(self):
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   flags=pathlib.Path(td);nonce='a'*64;d=flags/'qual'/nonce;d.mkdir(parents=True)
   (d/'proof-normal.json').write_text(json.dumps({'id':'row','nonce':nonce,'phase':'normal'}))
   (d/'proof-cutoff.json').write_text(json.dumps({'id':'row','nonce':nonce,'phase':'cutoff',
    'partial':True,'deadline_reached':True,'unknown_disposition':'UNKNOWN'}))
   original=q.load_manifest;q.load_manifest=lambda _:{'id':'row','production':True}
   old=os.environ.get('WS58_QUAL'),os.environ.get('WS58_QUAL_NONCE')
   os.environ['WS58_QUAL']='1';os.environ['WS58_QUAL_NONCE']=nonce
   try:
    with self.assertRaises((FileNotFoundError,q.Refused)):q.engine_partial(flags/'manifest.json',flags,nonce)
   finally:
    q.load_manifest=original
    for key,value in zip(('WS58_QUAL','WS58_QUAL_NONCE'),old):
     if value is None:os.environ.pop(key,None)
     else:os.environ[key]=value
if __name__=='__main__':unittest.main()
