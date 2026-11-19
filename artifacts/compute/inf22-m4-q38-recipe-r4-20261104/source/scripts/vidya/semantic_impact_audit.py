"""Read-only native-fold delta audit; no grade, fold, or trust-policy changes."""
from dataclasses import fields
from fold import FT_SUPPORT, FT_OPPOSE, FT_DEPENDS, FT_RETRACT, FT_CLAIM, FT_CORRECTION, FT_SOURCE

def audit_semantic_impact(before_frames, after_frames, before, after, direct_claim_ids,
                          exact_retired_frame_ids):
    """Allow only native dependency-alert propagation outside direct claim mutations.

    Caller passes actual canonical fold results and exact reviewed retirement IDs.
    No inference about scientific truth or semantic validity of historical prose.
    """
    assert after_frames[:len(before_frames)] == before_frames, 'old frame bytes/order changed'
    assert before.alias_map == after.alias_map, 'alias topology changed'
    def resolve(cid):
        seen=set()
        while cid in before.alias_map:
            assert cid not in seen;seen.add(cid);cid=before.alias_map[cid]
        return cid
    direct={resolve(c) for c in direct_claim_ids}
    def retracted(state):
        return {fid for b in state.beliefs.values() for fid in b.retracted_support}
    old_retracted=retracted(before);new_retracted=retracted(after)
    old_ids={f['frame_id']:f for f in before_frames}
    added=after_frames[len(before_frames):]
    withdrawals={f['assertion']['retracts'] for f in added if f['frame_type']==FT_RETRACT}
    assert withdrawals == set(exact_retired_frame_ids), 'withdrawal whitelist changed'
    assert new_retracted-old_retracted == withdrawals-old_retracted, 'unapproved evidence retired'
    assert old_retracted <= new_retracted, 'historical retraction disappeared'
    allowed_sources={f.get('assertion',{}).get('source_id') for f in before_frames+added if f.get('assertion',{}).get('claim_id') and resolve(f['assertion']['claim_id']) in direct}
    for f in added:
        if f['frame_type']==FT_SOURCE:assert f['assertion']['source_id'] in allowed_sources, 'off-target source declaration'
        if f['frame_type']==FT_CORRECTION:assert all(resolve(c) in direct for c in f['assertion'].get('claim_ids',[])), 'off-target correction emission'
        if f['frame_type'] in (FT_CLAIM,FT_SUPPORT,FT_OPPOSE,FT_DEPENDS):
            assert resolve(f['assertion']['claim_id']) in direct, 'off-target native emission'
    for f in before_frames:
        if f['frame_type'] in (FT_SUPPORT,FT_OPPOSE) and f['frame_id'] not in exact_retired_frame_ids:
            assert (f['frame_id'] in old_retracted)==(f['frame_id'] in new_retracted), 'unrelated old contribution effectiveness changed'
    def supported(frames,dead):
        out={}
        for f in frames:
            if f['frame_type']==FT_SUPPORT and f['frame_id'] not in dead and f['assertion'].get('source_id'):
                out.setdefault(f['assertion']['source_id'],[]).append(f['frame_id'])
        return out
    old_support=supported(before_frames,old_retracted);new_support=supported(after_frames,new_retracted)
    changed_sources={s for s in set(old_support)|set(new_support) if bool(old_support.get(s))!=bool(new_support.get(s))}
    # Actual native dependency frames, preserving multiplicity and recorded coarse fanout.
    edges={}
    for f in before_frames:
        if f['frame_type']==FT_DEPENDS and f['frame_id'] not in old_retracted:
            a=f['assertion'];edges.setdefault(resolve(a['claim_id']),[]).append(f)
    def normalized(value):
        if hasattr(value,'as_dict'):return value.as_dict()
        if isinstance(value,(list,tuple)):return [normalized(v) for v in value]
        if isinstance(value,dict):return {k:normalized(v) for k,v in value.items()}
        return value
    def snapshot(b):
        out={f.name:normalized(getattr(b,f.name)) for f in fields(b)}
        out['review_required']=b.review_required
        return out
    direct_deltas={};propagated=[];unchanged_count=0
    for cid in sorted(set(before.beliefs)|set(after.beliefs)):
        assert cid in before.beliefs or cid in direct, 'unexpected belief created'
        assert cid in after.beliefs, 'belief removed'
        left=snapshot(before.beliefs[cid]) if cid in before.beliefs else None
        right=snapshot(after.beliefs[cid])
        # Belief.as_dict omits this native property; capture it explicitly.
        if left is not None:left['dependency_alerts']=list(before.beliefs[cid].dependency_alerts)
        right['dependency_alerts']=list(after.beliefs[cid].dependency_alerts)
        if left is not None:
            left=dict(left);right=dict(right)
            # Existing fold exposes a global retracted-frame inventory on every belief.
            left.pop('retracted_support',None);right.pop('retracted_support',None)
        if left==right:unchanged_count+=1;continue
        delta={k:{'before':left.get(k) if left is not None else None,'after':right.get(k)} for k in set(left or {})|set(right) if (left or {}).get(k)!=right.get(k)}
        if cid in direct:
            direct_deltas[cid]=delta;continue
        assert set(delta)<= {'dependency_alerts','review_required'}, (cid,'off-target evidence/grade/history mutation',delta)
        owned_edges=edges.get(cid,[]);assert owned_edges,(cid,'no actual dependency edge')
        # Compare canonical OP-11 alert visibility against the actual surviving support sources.
        expected_before=sorted(f['assertion'].get('depends_on_entry') or f['assertion']['depends_on_source'] for f in owned_edges if f['assertion']['depends_on_source'] not in old_support)
        expected_after=sorted(f['assertion'].get('depends_on_entry') or f['assertion']['depends_on_source'] for f in owned_edges if f['assertion']['depends_on_source'] not in new_support)
        assert left.get('dependency_alerts',[])==expected_before,(cid,'baseline dependency mismatch')
        assert right.get('dependency_alerts',[])==expected_after,(cid,'preview dependency mismatch')
        changed_edges=[f for f in owned_edges if f['assertion']['depends_on_source'] in changed_sources]
        assert changed_edges,(cid,'no changed source visibility')
        # review_required is the existing canonical fold property; no new classifier.
        assert left['review_required']==bool(before.beliefs[cid].corrections or before.beliefs[cid].dependency_alerts or before.beliefs[cid].dirty_inputs)
        assert right['review_required']==bool(after.beliefs[cid].corrections or after.beliefs[cid].dependency_alerts or after.beliefs[cid].dirty_inputs)
        propagated.append({'claim_id':cid,'changed_fields':delta,'dependency_frames':owned_edges,
                           'changed_visibility_dependency_frame_ids':[f['frame_id'] for f in changed_edges],
                           'scientific_evidence_changed':False})
    return {'status':'PASS','old_frames_immutable_prefix':True,'old_frame_count':len(before_frames),
            'new_exact_retired_frame_ids':sorted(withdrawals),'all_non_target_old_evidence_effectiveness_unchanged':True,
            'no_off_target_new_evidence_or_depends_frames':True,'direct_target_semantic_deltas':direct_deltas,
            'expected_native_dependency_propagation':propagated,'unchanged_beliefs':unchanged_count,
            'source_support_visibility_changes':{s:{'before_frame_ids':old_support.get(s,[]),'after_frame_ids':new_support.get(s,[])} for s in sorted(changed_sources)},
            'source_support_counts':{s:{'before':len(old_support.get(s,[])),'after':len(new_support.get(s,[]))} for s in sorted(set(old_support)|set(new_support))},
            'interpretation':'Native dependency flags follow preserved authored edges. This neither verifies dependent claims anew nor repairs historically coarse dependencies.'}
