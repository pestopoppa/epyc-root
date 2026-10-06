"""Actual builder boundary tests using synthetic native records, never real receipts."""
import contextlib,copy,hashlib,io,json,shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/vidya'))
from adapters import research_intake as native
import intake_assertion_kinds,semantic_impact_audit,rebase_reviewed_batch,materialize_reviewed_batch
import native_correction_replay,ledger_write_lease,rebase_current_index
from fold import fold,FT_SUPPORT,FT_RETRACT,FT_ALIAS
from frames import make_frame
from ledger import Ledger
SHA=lambda b:hashlib.sha256(b).hexdigest()
OLD='2026-09-01T00:00:00Z';STAMP='2026-10-06T00:00:00Z';NOW='2026-10-06T01:00:00Z'
def write_json(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
def event(kind,assertion,actor='synthetic.fixture'):
 return make_frame(frame_type=kind,assertion=assertion,provenance={'method':'synthetic-builder-test'},actor=actor,authority_scope=native.AUTHORITY,created_at=STAMP)

class BuilderTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.d=Path(self.tmp.name);self.run=self.d/'run';self.inputs=self.run/'inputs';self.inputs.mkdir(parents=True)
  self.entries=[]
  for i in range(30):
   n=5 if i<22 else (3 if i<28 else 2)
   self.entries.append({'id':'intake-'+str(2000+i),'url':'https://example.org/synthetic/'+str(i),'verification':'dive-verified','key_claims':['Synthetic original '+str(i)+' slot '+str(j) for j in range(n)]})
  self.base=self.inputs/'canonical-ledger.snapshot.jsonl';led=Ledger(self.base);self.old=[]
  for e in self.entries:
   fs=native._frames_for_entry(e,OLD);self.old+=fs
   for f in fs:led.append(f)
  # A genuine same-source sibling outside the reviewed slots, plus a stable alias.
  extra=copy.deepcopy(self.entries[0]);extra['key_claims'].append('Synthetic unchanged sibling')
  for f in native._frames_for_entry(extra,OLD):
   if f.get('assertion',{}).get('claim_id')=='clm_intake_2000_05':led.append(f);self.old.append(f)
  alias=event(FT_ALIAS,{'claim_ids':['clm_intake_2000_00','zz_fixture_alias'],'independent':False});led.append(alias);self.old.append(alias)
  self.direct={f['assertion']['claim_id'] for f in self.old if f['frame_type']==FT_SUPPORT and f['assertion']['claim_id']!='clm_intake_2000_05'}
  self.retired={f['frame_id'] for f in self.old if f['frame_type']==FT_SUPPORT and f['assertion']['claim_id'] in self.direct}
  self.batch=[event(FT_RETRACT,{'retracts':fid,'reason':'Synthetic exact reviewed retirement'},native.ADAPTER_ID) for fid in sorted(self.retired)]
  for i,e in enumerate(self.entries):
   e=copy.deepcopy(e);e['key_claims']=['Synthetic current '+str(i)+' slot '+str(j) for j in range(len(e['key_claims']))]
   if i>=22:e['verification']='stage1-unverified'
   if i==0:
    e['claim_assertion_kinds']=[{'claim_index':j,'kind':'record_status','current_claim_text_sha256':SHA(e['key_claims'][j].encode()),'reason':'Synthetic administrative placeholder'} for j in (3,4)]
   self.batch+=native._frames_for_entry(e,STAMP)
  before=fold(self.old,as_of=STAMP);after=fold(self.old+self.batch,as_of=STAMP)
  audit=semantic_impact_audit.audit_semantic_impact(self.old,self.old+self.batch,before,after,self.direct,self.retired)
  verified={f['assertion']['claim_id'] for f in self.batch if f['frame_type']==FT_SUPPORT and f['assertion']['grade']['Q']=='Verified'}
  self.review={'status':'infrastructure_pass','label':'synthetic-combined-batch','as_of':STAMP,'original_prefix_sha256':SHA(self.base.read_bytes()),'exact_appended_frames':self.batch,'native_to_canonical':{cid:cid for cid in sorted(self.direct)},'expected_retired_targets':sorted(self.retired),'native_dependency_impact_audit':audit,'fresh_source_verified':len(verified),'fresh_demotion_hinted':22,'expected_supported_current_claims':sorted(verified),'helper_module_sha256':SHA(Path(native.__file__).read_bytes()),'administrative_evidence_exclusions':['clm_intake_2000_03','clm_intake_2000_04']}
  from collections import Counter
  self.review['exact_type_whitelist']=dict(Counter(f['frame_type'] for f in self.batch))
  self.assertEqual(len(self.retired),132);self.assertEqual(len(verified),108)
  self.assertEqual(sum(f['frame_type']==FT_SUPPORT and f['assertion']['grade']['Q']=='Hinted' for f in self.batch),22)
  write_json(self.run/'outputs/combined30-native-refresh-receipt.json',self.review)
  self.historical=b'# fixture\n'+b''.join(('- id: '+e['id']+'\n  key_claims: [synthetic]\n').encode() for e in self.entries)
  (self.inputs/'candidate.intake_index.yaml').write_bytes(self.historical)
  self.marker={'status':'infrastructure_pass','as_of':STAMP,'candidate_sha256':SHA(self.historical),'citation_gate':{'status':'synthetic_history_only'}}
  write_json(self.run/'outputs/full-refresh-validation.done.json',self.marker);(self.run/'outputs/root-v2.exit').write_text('0\n')
  self.current=self.d/'current.jsonl';shutil.copyfile(self.base,self.current)
  self.peer=native._frames_for_entry({'id':'intake-4000','url':'https://example.org/synthetic-ci-peer','key_claims':['Synthetic independent CI result'],'verification':'stage1-unverified'},STAMP)
  for f in self.peer:Ledger(self.current).append(f)
  self.out=self.d/'rebase'
 def prepare(self):
  with contextlib.redirect_stdout(io.StringIO()):rebase_reviewed_batch.prepare(old_run_dir=self.run,current_snapshot=self.current,expected_current_sha256=SHA(self.current.read_bytes()),as_of=NOW,new_output_dir=self.out)
 def assert_refused(self,pattern):
  original=self.current.read_bytes()
  with self.assertRaisesRegex(ValueError,pattern):self.prepare()
  self.assertFalse(self.out.exists());self.assertEqual(self.current.read_bytes(),original)
 def test_actual_rebase_preserves_ci_prefix_alias_sibling_and_historical_marker(self):
  original=self.current.read_bytes();self.prepare();r=json.loads((self.out/'reviewed-rebase-receipt.json').read_text())
  self.assertTrue((self.out/'reviewed-current-after.jsonl').read_bytes().startswith(original));self.assertEqual(self.current.read_bytes(),original)
  self.assertEqual(r['peer_frame_ids'],[f['frame_id'] for f in self.peer]);self.assertEqual(r['actual_target_sibling_equality']['clm_intake_2000_05']['full_native_belief_before'],r['actual_target_sibling_equality']['clm_intake_2000_05']['full_native_belief_current'])
  self.assertEqual(fold([x.frame for x in Ledger(self.out/'reviewed-current-after.jsonl').read_all()],as_of=NOW).alias_map,fold(self.old,as_of=NOW).alias_map)
  marker=json.loads((self.out/'completed-rebase-validation.json').read_text());self.assertEqual(marker['historical_completed_validation'],self.marker);self.assertIn('NOT run',marker['validation_scope'])
 def test_ci_named_peer_same_source_sibling_mutation_refused(self):
  sibling=next(f for f in self.old if f['frame_type']==FT_SUPPORT and f['assertion']['claim_id']=='clm_intake_2000_05')
  bad=event(FT_SUPPORT,copy.deepcopy(sibling['assertion']),'synthetic.ci.fixture');Ledger(self.current).append(bad)
  self.assert_refused('peer tail explicitly writes a target/sibling claim')
 def test_target_retirement_in_peer_tail_refused(self):
  target=next(f['frame_id'] for f in self.old if f['frame_type']==FT_SUPPORT and f['assertion']['claim_id']=='clm_intake_2000_00' and f['assertion']['grade']['Q']=='Verified')
  Ledger(self.current).append(event(FT_RETRACT,{'retracts':target,'reason':'Synthetic unexpected peer retirement'}))
  self.assert_refused('peer tail changed actual sibling state: clm_intake_2000_00')
 def materializer_fixture(self):
  self.prepare();self.repo=self.d/'repo';vidya=self.repo/'scripts/vidya';(vidya/'adapters').mkdir(parents=True)
  modules={'adapters/research_intake.py':native,'intake_assertion_kinds.py':intake_assertion_kinds,'semantic_impact_audit.py':semantic_impact_audit,'native_correction_replay.py':native_correction_replay,'ledger_write_lease.py':ledger_write_lease,'rebase_current_index.py':rebase_current_index}
  for name,module in modules.items():shutil.copyfile(module.__file__,vidya/name)
  shutil.copyfile(semantic_impact_audit.__file__,self.run/'semantic_impact_audit.py')
  source={'target_ids':[e['id'] for e in self.entries[:22]],'native_projection_module_binding':{'precondition_sha256':SHA(Path(intake_assertion_kinds.__file__).read_bytes())}}
  write_json(self.inputs/'source-warrant-refresh-manifest.proposed.json',source);write_json(self.inputs/'demotion-targets.json',{'targets':[{'entry_id':e['id']} for e in self.entries[22:]]});write_json(self.run/'input-bindings.json',{'synthetic':True})
  self.index_dir=self.d/'index-rebase';self.index_dir.mkdir();current=self.historical+b'- id: intake-4000\n  key_claims: [peer]\n'
  (self.index_dir/'current-base.intake_index.yaml').write_bytes(current);(self.index_dir/'candidate.intake_index.yaml').write_bytes(current)
  blocks=rebase_current_index.blocks(self.historical)
  write_json(self.index_dir/'index-rebase-receipt.json',{'reviewed_scoped_candidate_sha256':SHA(self.historical),'current_base_sha256':SHA(current),'candidate_sha256':SHA(current),'target_ids':[e['id'] for e in self.entries],'target_blocks':{k:{'current_base_sha256':SHA(blob),'reviewed_current_sha256':SHA(blob)} for k,(_,_,blob) in blocks.items()},'source_event_manifest_sha256':SHA((self.inputs/'source-warrant-refresh-manifest.proposed.json').read_bytes())})
  self.materialized=self.d/'materialized'
 def build(self):
  with contextlib.redirect_stdout(io.StringIO()):return materialize_reviewed_batch.build(run_dir=self.run,rebase_dir=self.out,index_rebase_dir=self.index_dir,owning_repo=self.repo,out_dir=self.materialized)
 def test_actual_materializer_preserves_both_candidate_and_historical_marker_custody(self):
  self.materializer_fixture();plan=self.build();self.assertEqual((self.materialized/'complete-validation.json').read_bytes(),(self.out/'completed-rebase-validation.json').read_bytes());self.assertEqual(json.loads((self.materialized/'complete-validation.json').read_text())['historical_completed_validation'],self.marker)
  self.assertEqual(plan['candidate_index']['sha256'],SHA((self.index_dir/'candidate.intake_index.yaml').read_bytes()));self.assertEqual(plan['reviewed_scoped_candidate_sha256'],SHA(self.historical));self.assertNotEqual(plan['candidate_index']['sha256'],plan['reviewed_scoped_candidate_sha256'])
 def test_materializer_changed_current_candidate_refused(self):
  self.materializer_fixture();(self.index_dir/'candidate.intake_index.yaml').write_bytes(b'changed\n')
  with self.assertRaisesRegex(ValueError,'index custody SHA mismatch'):self.build()
  self.assertFalse(self.materialized.exists())
 def test_materializer_changed_rebase_receipt_refused(self):
  self.materializer_fixture();p=self.out/'reviewed-rebase-receipt.json';r=json.loads(p.read_text());r['ledger_sha256']='0'*64;write_json(p,r)
  with self.assertRaisesRegex(ValueError,'original byte custody differs'):self.build()
  self.assertFalse(self.materialized.exists())
 def test_materializer_changed_completed_validation_candidate_refused(self):
  self.materializer_fixture();p=self.out/'completed-rebase-validation.json';r=json.loads(p.read_text());r['candidate_sha256']='0'*64;write_json(p,r)
  with self.assertRaisesRegex(ValueError,'original byte custody differs'):self.build()
  self.assertFalse(self.materialized.exists())
if __name__=='__main__':unittest.main()
