"""Pure, fail-closed admission for a *native* canceled full-prompt seed.

This is not an allocator model or a model runner. Its inputs must be copied
from the own server's actual native slot response, full cell grids, and raw
SSE/task log. Run fixtures only under the owner's authorized CPU grant.
"""
from physical_trace import TraceError,attended

T=32000
SOURCE_TOTAL=32512

def require(condition,reason):
    if not condition:raise TraceError(reason)

def emitted_generated_tokens(events):
    """Progress sends a default null token (-1) and stale n_decoded.

    Never interpret that sentinel or tokens_predicted as a generation event.
    Conversely a real token in a progress envelope is not silently ignored.
    """
    generated=[]
    for event in events:
        tokens=event.get('tokens',[])
        require(isinstance(tokens,list) and all(type(t) is int for t in tokens),'malformed SSE tokens')
        require(all(t>=0 or t==-1 for t in tokens),'unknown negative SSE token sentinel')
        require(-1 not in tokens or isinstance(event.get('prompt_progress'),dict),
                'null token outside exact native progress envelope')
        real=[t for t in tokens if t>=0]
        if real:generated.extend(real)
    return generated

def admit(*,slot,seed_task_id,expected_prefix_hash,events,native_target,
          prefix_partition,reference_prefix_partition,
          current_task_generation_entered,source_error_lines,
          observed_cancel_task,mask_probe_seq=3,slot_id=1,T=T):
    """Accept only retained, fully computed T on an idle *same* seed task.

    native_target is captured at the mask probe's first target find_slot,
    BEFORE its allocation. This observes post-CANCEL retained state without
    forcing a control-slot restore or replay. The mask probe runs on slot3.
    target and source prefix partitions include actual cells and batch heads.
    Source-order proof guarantees task processing cannot cancel in decode.
    """
    require(type(seed_task_id) is int and seed_task_id>=0,'missing seed task identity')
    require(slot.get('id')==slot_id and slot.get('id_task')==seed_task_id,'seed task/slot identity mismatch')
    require(slot.get('is_processing') is False,'cancellation not acknowledged by idle slot')
    require(observed_cancel_task is True,'native cancellation handler not observed')
    require(slot.get('n_prompt_tokens')==T,'cancel early/late: retained logical prefix != T')
    require(slot.get('n_prompt_tokens_processed')==T,'seed scheduled/processed count != T')
    require(slot.get('prefix_hash')==expected_prefix_hash,'wrong actual retained token prefix')
    require((slot.get('kv_cells') or {}).get('private')==T,'native retained target private-cell count != T')
    require((slot.get('kv_cells') or {}).get('shared')==0,'seed secretly shared/forked target cells')
    require((slot.get('fork') or {}).get('n_fork_tokens')==0,'seed native fork counter absent/nonzero')
    require(not current_task_generation_entered,'current seed reached DONE_PROMPT/generation')
    require(not source_error_lines,'target/drafter forward error in seed task window')
    require(not emitted_generated_tokens(events),'real generated token in canceled seed')
    progress=[e['prompt_progress'] for e in events if isinstance(e.get('prompt_progress'),dict)]
    require(progress and all(p.get('total')==SOURCE_TOTAL for p in progress),'seed original full task length changed')
    require(all(type(p.get('processed')) is int and 0<=p['processed']<=T for p in progress),'observed seed progress past T')
    require(native_target.get('n_swa')==0,'not target native map')
    mapped=attended(native_target,str(slot_id),end=T)
    require(len(mapped)==T and sorted(p for _,p in mapped)==list(range(T)),'actual retained physical prefix incomplete')
    require(not any(owner==str(slot_id) and pos is not None and pos>=T for owner,pos in native_target['cells']),
            'actual retained future/scratch target cell')
    require(not any(owner=='M' for owner,pos in native_target['cells']),'shared native cell in independent control construction')
    require(prefix_partition==reference_prefix_partition,'actual original-source prefix write map/partition differs')
    # Stale next_token.n_decoded is intentionally NOT an input to acceptance.
    return {'admitted':True,'task_id':seed_task_id,'slot_id':slot_id,'retained_tokens':T,
            'target_private_cells':T,'source_task_total':SOURCE_TOTAL,
            'generation_evidence':'raw SSE + current-task branch trace; next_token.n_decoded excluded as stale',
            'state_basis':'target+drafter successful decode precedes progress; CANCEL release does not clear memory'}

def draft_boundary(*,native_base,native_swa,slot_id=1,T=T,window=2048):
    """Observe BOTH draft caches at the mask probe's pre-injection boundary.

    Native DFlash base exists even when every actual model layer is SWA.
    This proves logical retained window and records physical positions; it
    does NOT declare a different physical map matched to the fork arm.
    """
    require(native_base.get('n_swa')==0 and native_swa.get('n_swa')==window,'wrong native DFlash cache roles')
    base=attended(native_base,str(slot_id),end=T)
    require(sorted(p for _,p in base)==list(range(T)),'retained DFlash base prefix incomplete')
    swa=attended(native_swa,str(slot_id),start=max(0,T-window),end=T)
    require(sorted(p for _,p in swa)==list(range(max(0,T-window),T)),'retained DFlash current window incomplete')
    for snap in (native_base,native_swa):
        require(not any(o==str(slot_id) and p is not None and p>=T for o,p in snap['cells']),
                'DFlash future/scratch state after cancellation')
    return {'logical_boundary':T,'base_prefix':base,'swa_window':swa,
            'physical_geometry_matched_to_fork':False}

def nofork_continuation(*,row,log_lines,T=T,S=4000):
    timings=row.get('timings') or {}
    require(timings.get('cache_n')==T and timings.get('prompt_n')==S,'control cache/remainder != T/S')
    require(timings.get('n_fork_tokens',0)==0 and timings.get('fork_src_kind','none')=='none','not independent nofork')
    forbidden=('restored context checkpoint','forcing full prompt re-processing',
               'need to evaluate at least 1 token','n_past was set to','slot fork:')
    require(not any(term in line for line in log_lines for term in forbidden),'hidden restore/re-evaluation/fork in control')
    require((timings.get('draft_n') or 0)>0,'DFlash2 inactive in nofork continuation')
    return {'nofork':True,'cache_n':T,'prompt_n':S,'checkpoint_restore':False,'prefix_replayed':False}
