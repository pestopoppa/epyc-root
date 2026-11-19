"""Replay a reviewed exact native correction batch; no global ingestion or grading."""
from pathlib import Path
import fcntl
from contextlib import nullcontext
from ledger_write_lease import OwnedWriteLease,LeasedLedger
import hashlib
import json
import sys
from adapters import research_intake as native
from fold import fold, FT_RETRACT, FT_SUPPORT, FT_OPPOSE
from frames import validate_frame
from ledger import Ledger, _refuse_future_stamp
from semantic_impact_audit import audit_semantic_impact


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_bound(binding):
    data=Path(binding['path']).read_bytes()
    if sha(data)!=binding['sha256']:
        raise ValueError('bound input bytes changed: '+binding['path'])
    return data


def replay_native_correction_batch(*, ledger_path, index_path, plan_path,
                                   expected_plan_sha256, output_receipt_path,
                                   apply=False):
    """Main-owned single writer; preflight whole batch before first append.

    Both fresh and partial-append retry must be an EXACT byte prefix of the
    externally pinned reviewed native ledger. Unrelated/interleaved/torn writes
    refuse. No adapter ingest, recomputation of native claims, or new grading.
    """
    plan_bytes=Path(plan_path).read_bytes()
    if sha(plan_bytes)!=expected_plan_sha256:raise ValueError('application plan SHA mismatch')
    plan=json.loads(plan_bytes)
    if plan.get('schema')!='epyc.native-correction-replay-plan/v1':raise ValueError('unknown plan schema')
    if plan['native_identity']!={'actor':native.ADAPTER_ID,'authority_scope':native.AUTHORITY}:
        raise ValueError('not the existing native intake adapter identity')
    read_bound(plan['native_adapter']);read_bound(plan['pure_precondition'])
    read_bound(plan['semantic_audit_module']);read_bound(plan['replay_module'])
    for field in ['source_manifest','demotion_manifest','input_bindings']:read_bound(plan[field])
    module_paths={
        'native_adapter':Path(native.__file__).resolve(),
        'pure_precondition':Path(sys.modules[native._validated_assertion_kinds.__module__].__file__).resolve(),
        'semantic_audit_module':Path(sys.modules[audit_semantic_impact.__module__].__file__).resolve(),
        'replay_module':Path(__file__).resolve(),
    }
    if any(Path(plan[k]['path']).resolve()!=path for k,path in module_paths.items()):
        raise ValueError('actual loaded module differs from pinned application module')
    if sha(Path(index_path).read_bytes())!=plan['candidate_index']['sha256']:
        raise ValueError('current owning index does not match reviewed candidate bytes')
    candidate_bytes=read_bound(plan['candidate_index'])
    if 'index_rebase_receipt' in plan:
        from rebase_current_index import validate_rebase_custody
        read_bound(plan['index_rebase_module'])
        if sha(Path(sys.modules[validate_rebase_custody.__module__].__file__).read_bytes())!=plan['index_rebase_module']['sha256']:raise ValueError('loaded index custody checker differs')
        validate_rebase_custody(json.loads(read_bound(plan['index_rebase_receipt'])),read_bound(plan['historical_candidate_index']),read_bound(plan['current_base_index']),candidate_bytes,set(plan['bounded_reviewed_entry_ids']))
    receipt_bytes=read_bound(plan['reviewed_receipt']);review=json.loads(receipt_bytes)
    if review['status']!='infrastructure_pass' or review['label']!=plan['reviewed_receipt_label']:
        raise ValueError('reviewed rehearsal did not pass')
    frames=json.loads(read_bound(plan['frame_manifest']))['frames']
    if frames!=review['exact_appended_frames']:raise ValueError('frame manifest differs from actual reviewed receipt')
    marker=json.loads(read_bound(plan['completed_validation']))
    if marker['status']!='infrastructure_pass' or marker['as_of']!=plan['as_of'] or marker['candidate_sha256']!=plan.get('reviewed_scoped_candidate_sha256',plan['candidate_index']['sha256']):
        raise ValueError('complete validation receipt does not match this batch')
    base_bytes=read_bound(plan['canonical_old_prefix'])
    after_bytes=read_bound(plan['reviewed_after_ledger'])
    if not after_bytes.startswith(base_bytes):raise ValueError('reviewed ledger lost original bytes')
    base_ledger=Ledger(plan['canonical_old_prefix']['path'])
    reviewed_ledger=Ledger(plan['reviewed_after_ledger']['path'])
    if base_ledger.verify() or reviewed_ledger.verify():raise ValueError('reviewed input ledger integrity failure')
    base_frames=[r.frame for r in base_ledger.read_all()]
    reviewed_frames=[r.frame for r in reviewed_ledger.read_all()]
    if len(base_frames)!=plan['canonical_old_prefix']['frontier']:raise ValueError('base frontier mismatch')
    if reviewed_frames!=base_frames+frames:raise ValueError('reviewed output is not exact whitelist extension')
    if len({f['frame_id'] for f in frames})!=len(frames):raise ValueError('duplicate batch frame IDs')
    old_ids={f['frame_id']:f for f in base_frames}
    direct=set(plan['direct_claim_ids']);retired=set(plan['exact_retired_frame_ids'])
    direct_canonical=set(plan['native_to_canonical'].values())
    target_bindings={r['frame_id']:r for r in plan['retirement_bindings']}
    if set(target_bindings)!=retired:raise ValueError('retirement scope bindings differ')
    actual_retired=set()
    source_claims=set(plan['fresh_verified_source_claim_ids'])
    hinted_claims=set(plan['fresh_hinted_claim_ids'])
    excluded=set(plan['record_status_claim_ids'])
    got_verified=set();got_hinted=set()
    for f in frames:
        validate_frame(f);_refuse_future_stamp(f)
        pub=f['pubinfo']
        if pub['actor']!=native.ADAPTER_ID or pub['authority_scope']!=native.AUTHORITY or pub['created_at']!=plan.get('batch_created_at',plan['as_of']):
            raise ValueError('frame actor/authority/time mismatch')
        if f['frame_type'] not in plan['exact_type_whitelist']:raise ValueError('unapproved frame type')
        if f['frame_id'] in old_ids:raise ValueError('batch collides with original frame ID')
        a=f['assertion']
        if f['frame_type']==FT_RETRACT:
            fid=a['retracts'];old=old_ids.get(fid)
            if fid not in retired or old is None:raise ValueError('unapproved retirement')
            validate_frame(old)
            op=old['pubinfo'];oa=old['assertion'];binding=target_bindings[fid]
            assertion_sha=sha(json.dumps(oa,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
            if binding!={'frame_id':fid,'frame_type':old['frame_type'],'actor':op['actor'],'authority_scope':op['authority_scope'],'source_id':oa.get('source_id'),'claim_id':oa.get('claim_id'),'old_assertion_sha256':assertion_sha}:
                raise ValueError('old native direction/actor/source/claim/assertion binding changed')
            if op['actor']!=native.ADAPTER_ID or op['authority_scope']!=native.AUTHORITY or oa.get('grade',{}).get('Q')!='Verified' or (oa.get('claim_id') not in direct and oa.get('claim_id') not in direct_canonical):
                raise ValueError('retirement is not exact native Verified scope')
            if old['frame_type'] not in (FT_SUPPORT,FT_OPPOSE):raise ValueError('retirement is not native evidence')
            actual_retired.add(fid)
        elif f['frame_type'] in (FT_SUPPORT,FT_OPPOSE):
            cid=a['claim_id']
            if cid in excluded or cid not in direct or f['frame_type']!=FT_SUPPORT:raise ValueError('unapproved replacement evidence')
            if cid in source_claims and a['grade']['Q']=='Verified':got_verified.add(cid)
            elif cid in hinted_claims and a['grade']['Q']=='Hinted':got_hinted.add(cid)
            else:raise ValueError('replacement does not match reviewed native disposition')
    from collections import Counter
    counts=dict(Counter(f['frame_type'] for f in frames))
    if counts!=plan['exact_type_whitelist'] or actual_retired!=retired or got_verified!=source_claims or got_hinted!=hinted_claims:
        raise ValueError('exact retirement/replacement/type whitelist mismatch')
    before=fold(base_frames,as_of=plan['as_of'])
    for raw,expected in plan['native_to_canonical'].items():
        cid=raw;seen=set()
        while cid in before.alias_map:
            if cid in seen:raise ValueError('alias cycle')
            seen.add(cid);cid=before.alias_map[cid]
        if cid!=expected:raise ValueError('reviewed alias closure changed')
    prospective=fold(base_frames+frames,as_of=plan['as_of'])
    impact=audit_semantic_impact(base_frames,base_frames+frames,before,prospective,direct,retired)
    if impact!=review['native_dependency_impact_audit']:raise ValueError('semantic impact differs from actual reviewed receipt')
    if before.state_hash()!=review['before_state_hash'] or prospective.state_hash()!=review['after_state_hash']:
        raise ValueError('canonical prospective fold differs from actual rehearsal')
    if apply:
        read_bound(plan['write_lease_module'])
        if sha(Path(sys.modules[OwnedWriteLease.__module__].__file__).read_bytes())!=plan['write_lease_module']['sha256']:raise ValueError('loaded lease module differs')
    destination=Path(ledger_path)
    if not destination.is_file():raise ValueError('owning canonical ledger is absent')
    if Path(output_receipt_path).exists():raise ValueError('receipt path already exists; preserve original receipt and use a new retry path')
    # Sidecar prevents duplicate replay callers; existing single-writer ownership still applies.
    # Sidecar serializes replay callers. Only the owned kernel inode lease excludes peer opens.
    with (OwnedWriteLease(destination) if apply else nullcontext()) as lease, destination.with_suffix(destination.suffix+'.native-replay.lock').open('a') as lock:
        fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        read_destination=lease.read_bytes if apply else destination.read_bytes
        current_bytes=read_destination()
        if not current_bytes.endswith(b'\n') or not current_bytes.startswith(base_bytes) or not after_bytes.startswith(current_bytes):
            raise ValueError('canonical bytes are not an exact reviewed prefix; no interleaved/torn writes permitted')
        ledger=LeasedLedger(lease) if apply else Ledger(destination)
        if ledger.verify():raise ValueError('canonical ledger integrity failure')
        current=[r.frame for r in ledger.read_all()]
        done=len(current)-len(base_frames)
        if done<0 or current!=base_frames+frames[:done]:raise ValueError('canonical partial frontier/order mismatch')
        appended=[]
        if apply:
            # Every schema, timestamp, identity, collision and complete-fold check above passed.
            if read_destination()!=current_bytes:raise ValueError('canonical changed after preflight')
            # Ledger.append has no shared-writer lock. Refuse an observed interleave
            # before every append; the caller must hold actual single-writer ownership.
            expected_bytes=current_bytes
            for i,f in enumerate(frames[done:],start=done):
                if read_destination()!=expected_bytes:raise ValueError('external append during batch; no further append permitted')
                lease.append(ledger,f);appended.append(f['frame_id'])
                expected_bytes=b''.join(after_bytes.splitlines(keepends=True)[:len(base_frames)+i+1])
                if read_destination()!=expected_bytes:raise ValueError('external write during append; stop and preserve all bytes')
            lease.check()
            actual_bytes=read_destination()
            actual=[r.frame for r in ledger.read_all()]
            if ledger.verify() or actual!=base_frames+frames or actual_bytes!=after_bytes:
                raise ValueError('applied ledger does not match exact reviewed output')
            actual_state=fold(actual,as_of=plan['as_of'])
            actual_impact=audit_semantic_impact(base_frames,actual,before,actual_state,direct,retired)
            if actual_impact!=impact or actual_state.state_hash()!=prospective.state_hash():raise ValueError('actual fold verification failed')
        else:
            actual_bytes=current_bytes;actual=current
        report={'schema':'epyc.native-correction-replay-receipt/v1','status':'applied_and_verified' if apply else 'preflight_only',
                'plan_sha256':expected_plan_sha256,'reviewed_receipt_sha256':plan['reviewed_receipt']['sha256'],
                'candidate_index_sha256':plan['candidate_index']['sha256'],'native_adapter_sha256':plan['native_adapter']['sha256'],
                'as_of':plan['as_of'],'native_identity':plan['native_identity'],'ledger_path':str(destination),
                'old_prefix_sha256':sha(base_bytes),'old_prefix_frontier':len(base_frames),'old_prefix_bytes_immutable':True,
                'partial_batch_frames_already_present':done,'exact_frame_ids_appended':appended,'actual_frontier':len(actual),
                'actual_ledger_sha256':sha(actual_bytes),'expected_reviewed_after_ledger_sha256':sha(after_bytes),
                'actual_after_state_hash':actual_state.state_hash() if apply else None,
                'prospective_after_state_hash':prospective.state_hash(),'semantic_impact_audit':impact,
                'canonical_mutation_performed':bool(appended),'index_or_handoff_mutation_performed':False,'ledger_integrity_errors':ledger.verify()}
        Path(output_receipt_path).write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
        return report


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ledger',required=True);p.add_argument('--index',required=True)
    p.add_argument('--plan',required=True);p.add_argument('--expected-plan-sha256',required=True)
    p.add_argument('--output-receipt',required=True);p.add_argument('--apply',action='store_true')
    a=p.parse_args()
    report=replay_native_correction_batch(ledger_path=a.ledger,index_path=a.index,plan_path=a.plan,
            expected_plan_sha256=a.expected_plan_sha256,output_receipt_path=a.output_receipt,apply=a.apply)
    print(json.dumps({k:report[k] for k in ['status','actual_frontier','actual_ledger_sha256','canonical_mutation_performed']}))
if __name__=='__main__':main()
