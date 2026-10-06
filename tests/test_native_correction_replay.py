"""Synthetic custody/mechanics fixtures; no scientific findings or canonical writes."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts/vidya'))
import native_correction_replay as replay
from adapters import research_intake as a
import intake_assertion_kinds
import semantic_impact_audit
import ledger_write_lease
from fold import fold,FT_RETRACT
from frames import make_frame,validate_frame
from canonical import envelope_hash
from ledger import Ledger
AS_OF='2026-10-06T00:00:00Z'
sha=lambda data:hashlib.sha256(data).hexdigest()
bind=lambda p:{'path':str(p),'sha256':sha(p.read_bytes())}

class ReplayTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.d=Path(self.temp.name)
  entry={'id':'intake-2001','url':'https://example.org/synthetic','key_claims':['original synthetic claim'],'verification':'dive-verified'}
  self.base=self.d/'base.jsonl';led=Ledger(self.base)
  self.old=a._frames_for_entry(entry,'2026-09-01T00:00:00Z')
  for f in self.old:led.append(f)
  old=next(f for f in self.old if f['frame_type']==a.FT_SUPPORT);self.retired=old['frame_id'];entry['key_claims']=['bounded current synthetic claim']
  retract=make_frame(frame_type=FT_RETRACT,assertion={'retracts':self.retired,'reason':'Synthetic reviewed current-slot scope repair'},provenance={'method':a.ADAPTER_ID},actor=a.ADAPTER_ID,authority_scope=a.AUTHORITY,created_at=AS_OF)
  self.frames=[retract]+a._frames_for_entry(entry,AS_OF)
  self.after=self.d/'reviewed.jsonl';shutil.copyfile(self.base,self.after);led=Ledger(self.after)
  for f in self.frames:led.append(f)
  self.destination=self.d/'canonical-fixture.jsonl';shutil.copyfile(self.base,self.destination)
  self.index=self.d/'index.yaml';self.index.write_text('synthetic-fixture-index\n')
  cid='clm_intake_2001_00';before=fold(self.old,as_of=AS_OF);after=fold(self.old+self.frames,as_of=AS_OF)
  impact=semantic_impact_audit.audit_semantic_impact(self.old,self.old+self.frames,before,after,{cid},{self.retired})
  def write(name,obj):
   p=self.d/name;p.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n');return p
  self.review=write('review.json',{'status':'infrastructure_pass','label':'synthetic-reviewed-batch','exact_appended_frames':self.frames,'before_state_hash':before.state_hash(),'after_state_hash':after.state_hash(),'native_dependency_impact_audit':impact})
  marker=write('marker.json',{'status':'infrastructure_pass','as_of':AS_OF,'candidate_sha256':sha(self.index.read_bytes())})
  self.payload=write('frames.json',{'frames':self.frames});empty=write('source-manifest.json',{'synthetic':True})
  oa=old['assertion'];op=old['pubinfo']
  target={'frame_id':self.retired,'frame_type':old['frame_type'],'actor':op['actor'],'authority_scope':op['authority_scope'],'source_id':oa['source_id'],'claim_id':cid,'old_assertion_sha256':sha(json.dumps(oa,sort_keys=True,separators=(',',':'),allow_nan=False).encode())}
  self.plan={'schema':'epyc.native-correction-replay-plan/v1','native_identity':{'actor':a.ADAPTER_ID,'authority_scope':a.AUTHORITY},'native_adapter':bind(Path(a.__file__)),'pure_precondition':bind(Path(intake_assertion_kinds.__file__)),'semantic_audit_module':bind(Path(semantic_impact_audit.__file__)),'replay_module':bind(Path(replay.__file__)),'write_lease_module':bind(Path(ledger_write_lease.__file__)),'candidate_index':bind(self.index),'reviewed_receipt':bind(self.review),'reviewed_receipt_label':'synthetic-reviewed-batch','frame_manifest':bind(self.payload),'completed_validation':bind(marker),'canonical_old_prefix':dict(bind(self.base),frontier=len(self.old)),'reviewed_after_ledger':bind(self.after),'source_manifest':bind(empty),'demotion_manifest':bind(empty),'input_bindings':bind(empty),'direct_claim_ids':[cid],'native_to_canonical':{cid:cid},'exact_retired_frame_ids':[self.retired],'retirement_bindings':[target],'fresh_verified_source_claim_ids':[cid],'fresh_hinted_claim_ids':[],'record_status_claim_ids':[],'exact_type_whitelist':dict(Counter(f['frame_type'] for f in self.frames)),'as_of':AS_OF}
  self.plan_path=self.d/'plan.json'
 def args(self,apply=True):
  self.plan_path.write_text(json.dumps(self.plan,sort_keys=True,indent=2)+'\n')
  return {'ledger_path':self.destination,'index_path':self.index,'plan_path':self.plan_path,'expected_plan_sha256':sha(self.plan_path.read_bytes()),'output_receipt_path':self.d/('receipt-'+str(len(list(self.d.glob('receipt-*'))))+'.json'),'apply':apply}
 def test_full_replay_and_zero_append_identical_retry(self):
  first=replay.replay_native_correction_batch(**self.args());expected=self.after.read_bytes();self.assertEqual(self.destination.read_bytes(),expected);self.assertTrue(first['exact_frame_ids_appended'])
  second=replay.replay_native_correction_batch(**self.args());self.assertEqual(second['exact_frame_ids_appended'],[]);self.assertEqual(self.destination.read_bytes(),expected)
 def test_partial_append_resumes_exact_reviewed_order(self):
  led=Ledger(self.destination);led.append(self.frames[0]);report=replay.replay_native_correction_batch(**self.args());self.assertEqual(report['partial_batch_frames_already_present'],1);self.assertEqual(self.destination.read_bytes(),self.after.read_bytes())
 def test_preflight_only_no_ledger_mutation(self):
  original=self.destination.read_bytes();report=replay.replay_native_correction_batch(**self.args(False));self.assertEqual(report['status'],'preflight_only');self.assertEqual(self.destination.read_bytes(),original)
 def test_changed_index_zero_append(self):
  original=self.destination.read_bytes();args=self.args();self.index.write_text('changed\n')
  with self.assertRaises(ValueError):replay.replay_native_correction_batch(**args)
  self.assertEqual(self.destination.read_bytes(),original)
 def test_malformed_late_frame_zero_append(self):
  original=self.destination.read_bytes();bad=copy.deepcopy(self.frames);bad[-1]['pubinfo']['authority_scope']='other-authority';bad[-1]['frame_id']=envelope_hash(bad[-1]);validate_frame(bad[-1]);self.payload.write_text(json.dumps({'frames':bad}));self.plan['frame_manifest']=bind(self.payload)
  review=json.loads(self.review.read_text());review['exact_appended_frames']=bad;self.review.write_text(json.dumps(review));self.plan['reviewed_receipt']=bind(self.review)
  shutil.copyfile(self.base,self.after);led=Ledger(self.after)
  for frame in bad:led.append(frame)
  self.plan['reviewed_after_ledger']=bind(self.after)
  with self.assertRaisesRegex(ValueError,'frame actor/authority/time mismatch'):replay.replay_native_correction_batch(**self.args())
  self.assertEqual(self.destination.read_bytes(),original)
 def test_unrelated_interleaved_append_refused(self):
  led=Ledger(self.destination);entry={'id':'intake-2002','url':'https://example.org/other-synthetic','key_claims':['unrelated'],'verification':'stage1-unverified'};led.append(a._frames_for_entry(entry,AS_OF)[0]);original=self.destination.read_bytes()
  with self.assertRaises(ValueError):replay.replay_native_correction_batch(**self.args())
  self.assertEqual(self.destination.read_bytes(),original)
 def test_rebased_current_prefix_preserves_peer_frames(self):
  peer=a._frames_for_entry({'id':'intake-2002','url':'https://example.org/peer-synthetic','key_claims':['peer current finding'],'verification':'stage1-unverified'},AS_OF)
  baseline=Ledger(self.base)
  for f in peer:baseline.append(f)
  shutil.copyfile(self.base,self.destination);shutil.copyfile(self.base,self.after)
  after_ledger=Ledger(self.after)
  for f in self.frames:after_ledger.append(f)
  base=self.old+peer;before=fold(base,as_of=AS_OF);after=fold(base+self.frames,as_of=AS_OF)
  review=json.loads(self.review.read_text());review.update(before_state_hash=before.state_hash(),after_state_hash=after.state_hash(),native_dependency_impact_audit=semantic_impact_audit.audit_semantic_impact(base,base+self.frames,before,after,set(self.plan['direct_claim_ids']),{self.retired}))
  self.review.write_text(json.dumps(review));self.plan['reviewed_receipt']=bind(self.review);self.plan['canonical_old_prefix']=dict(bind(self.base),frontier=len(base));self.plan['reviewed_after_ledger']=bind(self.after)
  report=replay.replay_native_correction_batch(**self.args());self.assertEqual(self.destination.read_bytes(),self.after.read_bytes());self.assertEqual(report['old_prefix_frontier'],len(base));self.assertEqual([r.frame for r in Ledger(self.destination).read_all()][len(self.old):len(base)],peer)
 def test_torn_tail_refused_without_repair_or_append(self):
  with self.destination.open('ab') as f:f.write(b'{"torn":')
  original=self.destination.read_bytes()
  with self.assertRaises(ValueError):replay.replay_native_correction_batch(**self.args())
  self.assertEqual(self.destination.read_bytes(),original)
if __name__=='__main__':unittest.main()
