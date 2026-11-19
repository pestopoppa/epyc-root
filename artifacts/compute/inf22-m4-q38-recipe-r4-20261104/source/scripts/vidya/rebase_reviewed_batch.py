"""Prepare current-snapshot replay custody in scratch; never append canonical ledger."""
from dataclasses import fields
from pathlib import Path
import argparse,hashlib,json,shutil
from fold import fold,FT_SUPPORT,FT_RETRACT,FT_CLAIM,FT_CORRECTION
from frames import validate_frame
from ledger import Ledger,_refuse_future_stamp
from semantic_impact_audit import audit_semantic_impact

def sha(data):return hashlib.sha256(data).hexdigest()
def normalize(value):
 if hasattr(value,'as_dict'):return value.as_dict()
 if isinstance(value,(tuple,list)):return [normalize(v) for v in value]
 if isinstance(value,dict):return {k:normalize(v) for k,v in value.items()}
 return value
def snapshot(b):
 out={f.name:normalize(getattr(b,f.name)) for f in fields(b) if f.name!='retracted_support'}
 out['review_required']=b.review_required;return out

def prepare(*,old_run_dir,current_snapshot,expected_current_sha256,as_of,new_output_dir):
 run=Path(old_run_dir);current=Path(current_snapshot);out=Path(new_output_dir)
 if out.exists():raise ValueError('preserve old attempt; new output directory required')
 raw=current.read_bytes()
 if sha(raw)!=expected_current_sha256:raise ValueError('externally pinned current snapshot changed')
 old_review=json.loads((run/'outputs/combined30-native-refresh-receipt.json').read_text())
 marker=json.loads((run/'outputs/full-refresh-validation.done.json').read_text())
 if (run/'outputs/root-v2.exit').read_text().strip()!='0' or old_review['status']!='infrastructure_pass' or marker['status']!='infrastructure_pass':raise ValueError('completed V2 custody required')
 original=run/'inputs/canonical-ledger.snapshot.jsonl';original_raw=original.read_bytes()
 if sha(original_raw)!=old_review['original_prefix_sha256'] or not raw.startswith(original_raw):raise ValueError('original historical ledger prefix changed')
 old_ledger=Ledger(original);current_ledger=Ledger(current)
 if old_ledger.verify() or current_ledger.verify() or not raw.endswith(b'\n'):raise ValueError('snapshot chain/tail integrity failure')
 old=[r.frame for r in old_ledger.read_all()];base=[r.frame for r in current_ledger.read_all()]
 if base[:len(old)]!=old:raise ValueError('original frames changed')
 batch=old_review['exact_appended_frames'];direct=set(old_review['native_to_canonical']);retired=set(old_review['expected_retired_targets'])
 historic_state=fold(old,as_of=as_of);before=fold(base,as_of=as_of)
 def resolve(state,cid):
  seen=set()
  while cid in state.alias_map:
   if cid in seen:raise ValueError('alias cycle')
   seen.add(cid);cid=state.alias_map[cid]
  return cid
 # ACTUAL source ownership determines siblings; no inference from CI/frame-class labels.
 canonical_direct=set(old_review['native_to_canonical'].values())
 own_sources={f['assertion'].get('source_id') for f in old if f['frame_type']==FT_CLAIM and resolve(historic_state,f['assertion']['claim_id']) in canonical_direct}
 sibling_claims={resolve(historic_state,f['assertion']['claim_id']) for f in old if f['frame_type']==FT_CLAIM and f['assertion'].get('source_id') in own_sources}
 protected=canonical_direct|sibling_claims
 for f in base[len(old):]:
  assertion=f.get('assertion',{});cid=assertion.get('claim_id')
  if cid and resolve(before,cid) in protected:raise ValueError('peer tail explicitly writes a target/sibling claim')
  if f['frame_type']==FT_CORRECTION and any(resolve(before,c) in protected for c in assertion.get('claim_ids',[])):raise ValueError('peer tail corrects a target/sibling')
  if f['frame_type']==FT_CLAIM and assertion.get('source_id') in own_sources:raise ValueError('peer tail changes target-source sibling declarations')
 stable={}
 for cid in sorted(sibling_claims):
  left=snapshot(historic_state.beliefs[cid]);right=snapshot(before.beliefs[cid])
  if left!=right:raise ValueError('peer tail changed actual sibling state: '+cid)
  stable[cid]={'canonical_claim_id':cid,'full_native_belief_before':left,'full_native_belief_current':right,'equal':True,'scope':'actual same-source sibling'}
 for raw_cid,expected in old_review['native_to_canonical'].items():
  if resolve(historic_state,raw_cid)!=expected or resolve(before,raw_cid)!=expected:raise ValueError('target alias closure changed during peer append')
  left=snapshot(historic_state.beliefs[expected]);right=snapshot(before.beliefs[expected])
  if left!=right:raise ValueError('peer tail changed a direct target/sibling state: '+raw_cid)
  stable[raw_cid]={'canonical_claim_id':expected,'full_native_belief_before':left,'full_native_belief_current':right,'equal':True}
 dead={fid for b in before.beliefs.values() for fid in b.retracted_support}
 if dead&retired:raise ValueError('reviewed old target already withdrawn by a different event')
 existing={f['frame_id']:f for f in base}
 for f in batch:
  validate_frame(f);_refuse_future_stamp(f)
  if f['frame_id'] in existing:raise ValueError('historical batch frame already present/collides; use frozen retry plan')
 prospective=fold(base+batch,as_of=as_of)
 impact=audit_semantic_impact(base,base+batch,before,prospective,direct,retired)
 # Carry exact historical expected propagation scope, but evaluate against CURRENT baseline.
 prior_rows=old_review['native_dependency_impact_audit']['expected_native_dependency_propagation']
 new_rows=impact['expected_native_dependency_propagation']
 if [r['claim_id'] for r in new_rows]!=[r['claim_id'] for r in prior_rows]:raise ValueError('current propagation footprint differs; explicit new review required')
 for prior,new in zip(prior_rows,new_rows):
  if prior['changed_fields']['dependency_alerts']!=new['changed_fields']['dependency_alerts']:raise ValueError('current dependency cause differs from historical review')
 # Prospective full fold and all invariants checked before first SCRATCH append.
 out.mkdir(parents=True);baseline=out/'canonical-current-prefix.jsonl';baseline.write_bytes(raw)
 after_path=out/'reviewed-current-after.jsonl';shutil.copyfile(baseline,after_path);after_ledger=Ledger(after_path)
 for f in batch:after_ledger.append(f)
 actual=[r.frame for r in after_ledger.read_all()]
 if after_ledger.verify() or actual!=base+batch or not after_path.read_bytes().startswith(raw):raise ValueError('scratch replay integrity failure')
 actual_state=fold(actual,as_of=as_of)
 if actual_state.state_hash()!=prospective.state_hash():raise ValueError('actual scratch fold differs')
 updated=dict(old_review);updated.update(label='rebased-native-refresh',as_of=as_of,batch_created_at=old_review['as_of'],
   old_frontier=len(base),new_frontier=len(actual),frontier_delta=len(batch),before_state_hash=before.state_hash(),after_state_hash=actual_state.state_hash(),
   original_prefix_byte_count=len(raw),original_prefix_sha256=sha(raw),ledger_sha256=sha(after_path.read_bytes()),native_dependency_impact_audit=impact,
   historical_v2_receipt_sha256=sha((run/'outputs/combined30-native-refresh-receipt.json').read_bytes()),historical_original_prefix_sha256=sha(original_raw),
   current_snapshot_sha256=expected_current_sha256,peer_tail_byte_count=len(raw)-len(original_raw),peer_tail_sha256=sha(raw[len(original_raw):]),
   peer_frame_ids=[f['frame_id'] for f in base[len(old):]],peer_frames_preserved=True,actual_target_sibling_equality=stable,
   current_snapshot_rebased=True,canonical_writes=False,lane_writes=False,as_of_is_evaluation_time_not_batch_created_at=True)
 (out/'reviewed-rebase-receipt.json').write_text(json.dumps(updated,sort_keys=True,indent=2)+'\n')
 marker={'status':'infrastructure_pass','validation_scope':'Current ledger prefix, protected target/sibling equality, exact batch schemas and prospective/actual folds only. Current citation/index validation NOT run.', 'as_of':as_of,'batch_created_at':old_review['as_of'],'candidate_sha256':marker['candidate_sha256'],'current_snapshot_rebased':True,'current_snapshot_sha256':expected_current_sha256,'historical_completed_validation':marker,'historical_completed_validation_sha256':sha((run/'outputs/full-refresh-validation.done.json').read_bytes())}
 (out/'completed-rebase-validation.json').write_text(json.dumps(marker,sort_keys=True,indent=2)+'\n')
 (out/'rebase.done.json').write_text(json.dumps({'status':'infrastructure_pass','current_snapshot_sha256':expected_current_sha256,'historical_v2_receipt_sha256':updated['historical_v2_receipt_sha256'],'canonical_mutations':False,'scratch_after_ledger_sha256':updated['ledger_sha256'],'preparation_as_of':as_of},indent=2)+'\n')
 print(json.dumps({'status':'scratch_rebase_pass','old_frontier':len(old),'current_frontier':len(base),'peer_frames_preserved':len(base)-len(old),'planned_batch_frames':len(batch),'canonical_writes':False}))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--old-run-dir',required=True);p.add_argument('--current-snapshot',required=True);p.add_argument('--expected-current-sha256',required=True);p.add_argument('--as-of',required=True);p.add_argument('--new-output-dir',required=True);a=p.parse_args();prepare(old_run_dir=a.old_run_dir,current_snapshot=a.current_snapshot,expected_current_sha256=a.expected_current_sha256,as_of=a.as_of,new_output_dir=a.new_output_dir)
