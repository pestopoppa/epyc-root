#!/usr/bin/env python3
"""Isolated receipt controls; synthetic target scope is never published."""
import copy, importlib.util, json, pathlib, shutil, tempfile, unittest
BASE=pathlib.Path(__file__).resolve().parents[2]
SRC=BASE/'qualify_launcher.py'
spec=importlib.util.spec_from_file_location('qualify_launcher',SRC)
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)

class VerifyControls(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=BASE);self.addCleanup(self.tmp.cleanup)
  self.flags=pathlib.Path(self.tmp.name);self.nonce='b'*64
  self.qdir=self.flags/'qual'/self.nonce;(self.qdir/'results').mkdir(parents=True)
  # Use the real model-free child's immutable evidence bytes, but transform the
  # receipt inside this test only to reach individual verifier branches.
  prior=sorted((BASE/'tests/d1d4/fixtures/qualification').glob('QUAL-ni-qual-fixture-*.json'))[-1]
  self.p=json.loads(prior.read_text());original=BASE/'tests/d1d4/fixtures/results/QUAL-RESULT.json'
  shutil.copyfile(original,self.qdir/'results/QUAL-RESULT.json')
  for name in ('proof-normal.json','proof-cutoff.json','receipt-partial.json'):
   shutil.copyfile(prior.parents[1]/'flags/qual'/self.p['nonce']/name,self.qdir/name)
  for name in ('cutoff-event.json','cutoff-observed.json'):
   (self.qdir/name).write_text(json.dumps({'test_only':True,'name':name})+'\n')
   self.p['evidence_sha256'][name]=q.sha(self.qdir/name)
  self.p.update(kind=q.KIND,nonce=self.nonce)
  self.p['first_request']['scope']='TARGET_SCRATCH_SERVER'
  self.p['first_request'].update(n_ctx_total=1,n_ctx_per_slot=1,total_slots=1,manifest_sha256='a'*64)
  self.p['first_request']['kv_cache_mode']='split'
  self.p['first_request']['production_recipe_sha256']='d'*64
  self.p['result_writer']['result_path']=str(self.qdir/'results/QUAL-RESULT.json')
  self.receipt=self.flags/'receipt.json'
  self.m={'id':self.p['id'],'production':True,'qualification':{'receipt':str(self.receipt)},
          'request_manifest_sha256':'a'*64,'production_recipe':{'path':'/tmp/fixture-recipe','sha256':'d'*64},'kv_cache_mode':'split','n_ctx_required':1,'per_slot_n_ctx_required':1,'n_parallel_required':1,'prompt_tokens_required':16,'rate_basis':{'scope':'qualification-same-recipe','production_threads':2},'items':2,'tokens_per_item':1,'window_s':600,'job_floor_gib':150,'regions':'132-133','hold':None}
  self.p['manifest_sha256']=q.manifest_digest(self.m)
  self.p['feasibility']={'rate_scope':'qualification-same-recipe','rate_tok_s':self.p['first_request']['measured_tok_s'],'production_threads':2}
  self.p['resource_claim']={'cpus':'132-133','gpu_quiet_exclusive':False,'region_lock_tag':'qual-'+self.m['id']}
  self.p['cutoff_observation']={'native_child_drained':True,'native_first_event':True}
  self.p['production_recipe_sha256']='d'*64
  self.p['receipt_sha256_excluding_self']=q.digest({k:v for k,v in self.p.items() if k!='receipt_sha256_excluding_self'})
  self.write_receipt()
  self.files={'launcher':{'path':self.p['launcher_path'],'sha256':self.p['launcher_sha256']},
   'engine':{'path':self.p['engine_path'],'sha256':self.p['engine_sha256']},
   'job':{'path':self.p['job_path'],'sha256':self.p['job_sha256']},
   'qual_fixture':{'path':self.p['fixture_path'],'sha256':self.p['fixture_sha256']},
   'source_manifest_sha256':self.p['source_manifest_sha256'],'policy_sha256':self.p['policy_sha256'],
   'helper_sha256':self.p['helper_sha256']}
  self.files['production_recipe_sha256']='d'*64
  self.old_load=q.load_manifest;self.old_files=q.bound_files;self.old_row=q.row_binding
  q.load_manifest=lambda _:self.m;q.bound_files=lambda _:self.files;q.row_binding=lambda *_:None
  self.addCleanup(lambda:setattr(q,'load_manifest',self.old_load))
  self.addCleanup(lambda:setattr(q,'bound_files',self.old_files))
  self.addCleanup(lambda:setattr(q,'row_binding',self.old_row))
  self.write_state('passed')
  marker=self.flags/'qual-nonces/by-id'/(self.m['id']+'.json');marker.parent.mkdir()
  marker.write_text(json.dumps({'id':self.m['id'],'nonce':self.nonce,
                                'manifest_sha256':q.manifest_digest(self.m),'test_only':True}))
 def write_receipt(self):self.receipt.write_text(json.dumps(self.p,sort_keys=True)+'\n')
 def write_state(self,state):
  path=q.store_path(self.flags,self.nonce);path.parent.mkdir(exist_ok=True)
  path.write_text(json.dumps({'kind':'epyc.qual.nonce.v1','id':self.m['id'],
    'manifest_sha256':q.manifest_digest(self.m),'receipt':str(self.receipt),
    'state':state,'receipt_sha256':q.sha(self.receipt)}))
 def test_control_baseline(self):self.assertEqual(q.verify(self.receipt,self.flags,False)['id'],self.m['id'])
 def test_edited_receipt_refused(self):
  self.p['completion']['is_complete_rc']=1;self.write_receipt()
  with self.assertRaisesRegex(q.Refused,'receipt edited'):q.verify(self.receipt,self.flags,False)
 def test_replayed_nonce_refused(self):
  self.write_state('issued')
  with self.assertRaisesRegex(q.Refused,'nonce state'):q.verify(self.receipt,self.flags,False)
 def test_helper_change_refused(self):
  self.files['helper_sha256']=dict(self.files['helper_sha256'],**{'dryrun_check.py':'0'*64})
  with self.assertRaisesRegex(q.Refused,'source/policy/helper'):q.verify(self.receipt,self.flags,False)
 def test_namespace_mismatch_refused(self):
  old=q.launcher_namespace;q.launcher_namespace=lambda *args,**kw:{'root_inode':-1}
  try:
   with self.assertRaisesRegex(q.Refused,'exec namespace changed'):q.verify(self.receipt,self.flags,True)
  finally:q.launcher_namespace=old
 def test_result_changed_refused(self):
  (self.qdir/'results/QUAL-RESULT.json').write_text('changed')
  with self.assertRaisesRegex(q.Refused,'qualification result changed'):q.verify(self.receipt,self.flags,False)
 def test_wrong_cpu_proof_refused(self):
  normal=json.loads((self.qdir/'proof-normal.json').read_text());normal['observed_cpus']=[90]
  (self.qdir/'proof-normal.json').write_text(json.dumps(normal))
  with self.assertRaisesRegex(q.Refused,'qualification evidence changed'):q.verify(self.receipt,self.flags,False)
if __name__=='__main__':unittest.main()
