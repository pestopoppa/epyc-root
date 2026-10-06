"""Materialize exact application custody AFTER actual combined native rehearsal passes.

This builder only writes the requested NEW scratch/public artifact directory.
It never opens the canonical ledger for append or modifies the candidate index.
"""
from pathlib import Path
import argparse,hashlib,json,shutil

def sha(data):return hashlib.sha256(data).hexdigest()
def binding(p):return {'path':str(p),'sha256':sha(p.read_bytes())}
def build(*,run_dir,rebase_dir,index_rebase_dir,owning_repo,out_dir):
 run=Path(run_dir);repo=Path(owning_repo);out=Path(out_dir)
 if out.exists():raise ValueError('output directory exists; preserve prior custody')
 rebase=Path(rebase_dir)
 receipt_path=rebase/'reviewed-rebase-receipt.json'
 marker_path=rebase/'completed-rebase-validation.json'
 if json.loads((rebase/'rebase.done.json').read_text())['status']!='infrastructure_pass':raise ValueError('actual current-snapshot rebase pass required')
 receipt=json.loads(receipt_path.read_text());marker=json.loads(marker_path.read_text())
 if (run/'outputs/root-v2.exit').read_text().strip()!='0' or receipt['status']!='infrastructure_pass' or marker['status']!='infrastructure_pass':raise ValueError('actual V2 pass receipts are required')
 inputs=run/'inputs';manifest=json.loads((inputs/'source-warrant-refresh-manifest.proposed.json').read_text());demotions=json.loads((inputs/'demotion-targets.json').read_text())
 source_ids=set(manifest['target_ids']);demotion_ids={t['entry_id'] for t in demotions['targets']}
 if len(source_ids)!=22 or len(demotion_ids)!=8 or source_ids&demotion_ids:raise ValueError('reviewed bounded30 scope differs')
 if len(receipt['expected_retired_targets'])!=132 or receipt['fresh_source_verified']!=108 or receipt['fresh_demotion_hinted']!=22:raise ValueError('actual reviewed batch counts differ')
 historical_candidate=inputs/'candidate.intake_index.yaml'
 index_rebase=Path(index_rebase_dir);index_receipt_path=index_rebase/'index-rebase-receipt.json';index_receipt=json.loads(index_receipt_path.read_text())
 candidate=index_rebase/'candidate.intake_index.yaml';current_base=index_rebase/'current-base.intake_index.yaml'
 from rebase_current_index import validate_rebase_custody
 validate_rebase_custody(index_receipt,historical_candidate.read_bytes(),current_base.read_bytes(),candidate.read_bytes(),source_ids|demotion_ids)
 if index_receipt['source_event_manifest_sha256']!=sha((inputs/'source-warrant-refresh-manifest.proposed.json').read_bytes()):raise ValueError('historical event manifest custody differs')
 baseline=rebase/'canonical-current-prefix.jsonl';after=rebase/'reviewed-current-after.jsonl'
 if sha(historical_candidate.read_bytes())!=marker['candidate_sha256'] or sha(after.read_bytes())!=receipt['ledger_sha256'] or sha(baseline.read_bytes())!=receipt['original_prefix_sha256']:raise ValueError('original byte custody differs from actual receipts')
 if not after.read_bytes().startswith(baseline.read_bytes()):raise ValueError('reviewed bytes lost prefix')
 # Installed owning code must exactly match the tested guard/native/audit copies.
 native=repo/'scripts/vidya/adapters/research_intake.py';pure=repo/'scripts/vidya/intake_assertion_kinds.py';audit=repo/'scripts/vidya/semantic_impact_audit.py';replay=repo/'scripts/vidya/native_correction_replay.py'
 if sha(native.read_bytes())!=receipt['helper_module_sha256']:raise ValueError('installed native adapter differs from actual reviewed module')
 if sha(pure.read_bytes())!=manifest['native_projection_module_binding']['precondition_sha256']:raise ValueError('installed pure precondition differs')
 if sha(audit.read_bytes())!=sha((run/'semantic_impact_audit.py').read_bytes()):raise ValueError('installed audit differs from actual reviewed audit')
 out.mkdir(parents=True)
 copies={'reviewed-receipt.json':receipt_path,'complete-validation.json':marker_path,'canonical-old-prefix.jsonl':baseline,'reviewed-after-ledger.jsonl':after,'candidate.intake_index.yaml':candidate,'source-manifest.json':inputs/'source-warrant-refresh-manifest.proposed.json','demotion-manifest.json':inputs/'demotion-targets.json','input-bindings.json':run/'input-bindings.json'}
 copies.update({'index-rebase-receipt.json':index_receipt_path,'historical-candidate.intake_index.yaml':historical_candidate,'current-base.intake_index.yaml':current_base})
 for name,p in copies.items():shutil.copyfile(p,out/name)
 payload=out/'exact-frame-manifest.json';payload.write_text(json.dumps({'schema':'epyc.native-correction-frame-manifest/v1','frames':receipt['exact_appended_frames']},sort_keys=True,indent=2)+'\n')
 fresh_verified=set(receipt['expected_supported_current_claims']);hinted={f['assertion']['claim_id'] for f in receipt['exact_appended_frames'] if f['frame_type']=='epyc.vidya/frame/evidence_supports_claim/v1' and f['assertion']['grade']['Q']=='Hinted'}
 old_frames={}
 for line in baseline.read_bytes().splitlines():
  row=json.loads(line);f=row.get('frame',row);old_frames[f['frame_id']]=f
 bindings=[]
 for fid in receipt['expected_retired_targets']:
  f=old_frames[fid];a=f['assertion'];p=f['pubinfo']
  bindings.append({'frame_id':fid,'frame_type':f['frame_type'],'actor':p['actor'],'authority_scope':p['authority_scope'],'source_id':a.get('source_id'),'claim_id':a.get('claim_id'),'old_assertion_sha256':sha(json.dumps(a,sort_keys=True,separators=(',',':'),allow_nan=False).encode())})
 plan={'schema':'epyc.native-correction-replay-plan/v1','bounded_reviewed_entry_ids':sorted(source_ids|demotion_ids),
       'native_identity':{'actor':'vidya.adapters.research_intake/v1','authority_scope':'research-verification'},
       'as_of':receipt['as_of'],'batch_created_at':receipt.get('batch_created_at',receipt['as_of']),'reviewed_receipt_label':receipt['label'],'reviewed_receipt':binding(out/'reviewed-receipt.json'),
       'completed_validation':binding(out/'complete-validation.json'),'canonical_old_prefix':dict(binding(out/'canonical-old-prefix.jsonl'),frontier=receipt['old_frontier']),
       'reviewed_after_ledger':binding(out/'reviewed-after-ledger.jsonl'),'candidate_index':binding(out/'candidate.intake_index.yaml'),
       'reviewed_scoped_candidate_sha256':marker['candidate_sha256'],'index_rebase_receipt':binding(out/'index-rebase-receipt.json'),'historical_candidate_index':binding(out/'historical-candidate.intake_index.yaml'),'current_base_index':binding(out/'current-base.intake_index.yaml'),'index_rebase_module':binding(repo/'scripts/vidya/rebase_current_index.py'),
       'frame_manifest':binding(payload),'native_adapter':binding(native),'pure_precondition':binding(pure),'semantic_audit_module':binding(audit),'replay_module':binding(replay),'write_lease_module':binding(repo/'scripts/vidya/ledger_write_lease.py'),
       'source_manifest':binding(out/'source-manifest.json'),'demotion_manifest':binding(out/'demotion-manifest.json'),
       'direct_claim_ids':sorted(receipt['native_to_canonical']), 'native_to_canonical':receipt['native_to_canonical'],
       'retirement_bindings':bindings,'exact_retired_frame_ids':receipt['expected_retired_targets'],'fresh_verified_source_claim_ids':sorted(fresh_verified),
       'fresh_hinted_claim_ids':sorted(hinted),'record_status_claim_ids':receipt['administrative_evidence_exclusions'],
       'exact_type_whitelist':receipt['exact_type_whitelist'],'input_bindings':binding(out/'input-bindings.json'),
       'scope':'Exact completed combined reviewed batch only; no global ingest. Main-owned code/index/ledger application. No new grades/trust policy.'}
 pp=out/'application-plan.json';pp.write_text(json.dumps(plan,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'application_plan_path':str(pp),'application_plan_sha256':sha(pp.read_bytes()),'frame_manifest_sha256':plan['frame_manifest']['sha256'],'canonical_mutations':False},indent=2))
 return plan
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-dir',required=True);p.add_argument('--rebase-dir',required=True);p.add_argument('--index-rebase-dir',required=True);p.add_argument('--owning-repo',required=True);p.add_argument('--new-output-dir',required=True);a=p.parse_args();build(run_dir=a.run_dir,rebase_dir=a.rebase_dir,index_rebase_dir=a.index_rebase_dir,owning_repo=a.owning_repo,out_dir=a.new_output_dir)
