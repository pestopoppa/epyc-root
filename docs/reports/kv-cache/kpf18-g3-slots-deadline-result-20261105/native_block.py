"""Proposed native KPF18 block; integrate into pinned gate only after review.

No entry point: importing this file never runs a model. The owning launcher
must supply the pinned gate, server, Run, and HTTP context. Real geometry is
decoded from the exact binary's native grids, never synthesized.
"""
from pathlib import Path
from itertools import chain
import time
from physical_trace import snapshots,TraceError,witness,suffix_partitions,prefix_partitions,cache_roles
from cancel_seed_admission import admit as admit_seed,draft_boundary,nofork_continuation

ARM='kpf18_g3_native_layout'
T,S,N=32000,4000,256

def slots_by_id(ctx):
    return {row['id']:row for row in ctx.client.slots()}

class TraceSlice:
    """Re-iterable immutable byte window; never materialize multi-GiB logs."""
    def __init__(self,path,start,end,allow_draft_restore=False):
        self.path,self.start,self.end=path,start,end
        self.allow_draft_restore=allow_draft_restore
    def lines(self):
        with open(self.path,'rb') as stream:
            stream.seek(self.start)
            while stream.tell()<self.end:
                raw=stream.readline(self.end-stream.tell())
                if not raw or not raw.endswith(b'\n'):raise TraceError('truncated timestamped native log line')
                line=raw.decode('utf-8',errors='strict')
                timestamp,sep,body=line.partition(' ')
                try:float(timestamp)
                except ValueError:raise TraceError('missing pinned pump timestamp')
                if not sep:raise TraceError('missing native log body')
                yield body
    def __iter__(self):
        for group in self.contexts():
            if group['event']=='forward':yield group['target']
    def contexts(self):
        return cache_roles(snapshots(self.lines()),allow_draft_restore=self.allow_draft_restore)

def target_trace(path,start,end,allow_draft_restore=False):return TraceSlice(path,start,end,allow_draft_restore)

def first_target(trace):
    try:return next(iter(trace))
    except StopIteration:raise TraceError('no complete native target map')

def request(gate,ctx,R,srv,role,body):
    ctx.check_boundary()
    # Snapshot log offsets, retaining raw native bytes for audit.
    start=Path(srv.log).stat().st_size
    reply=ctx.client.stream(body)
    # stdout pump flushes line-wise. An incomplete final grid FAILS; no
    # estimated grid/offset is substituted for an incomplete witness.
    end=Path(srv.log).stat().st_size
    row=R.row(role,reply,group=3,slot=body['id_slot'],timing='A')
    if row.get('http')!=200 or row.get('error'):
        raise gate.Abort(f'{role}: HTTP failure')
    trace=target_trace(srv.log,start,end,allow_draft_restore=body.get('slot_fork') is not False)
    return row,trace,dict(log=str(srv.log),byte_start=start,byte_end=end)

def native_block(gate,ctx,R,srv,*,seed_control):
    """seed_control is the reviewed full-prompt SSE/CANCEL transport.

    Required return: slot, seed_task_id, events, seed_trace, raw_record_path,
    expected_prefix_hash, current_task_generation_entered, source_error_lines,
    observed_cancel_task. No short-prefix control is available here.
    """
    group=gate.G(ctx,3)
    if group['T']!=T or len(group['suffixes'][2])!=S:
        raise gate.Abort('not the exact group3 fixture')
    source=group['trunk']+group['src_tail']
    child=group['trunk']+group['suffixes'][2]
    trials=[];tail=None;fork_baseline=None;source_prefix_partition=None
    before_nz=srv.sampler.n_own_nonzero
    for arm,index in [('X',1),('Cmask',1),('X',2),('Cmask',2),('Cmask',3)]:
        gate.erase_all(ctx)
        # Both source and control write the attended trunk after this SAME
        # real prefix filler. All requests retain raw native results.
        request(gate,ctx,R,srv,f'{arm}{index}_prefix_filler',gate.body_for(group['filler'],0,2,fork=False,cache=False,n_probs=0))
        if arm=='X':
            src,st,ss=request(gate,ctx,R,srv,f'X{index}_source',gate.body_for(source,N,0,fork=False,ckpt=[T],n_probs=20))
            slots=slots_by_id(ctx);source_slot=slots[0]
            cells=source_slot.get('kv_cells') or {}
            actual_tail=cells.get('private')
            if type(actual_tail)!=int or actual_tail<=T:
                raise gate.Abort('source native private-cell residency unavailable')
            actual_tail-=T
            if tail is not None and actual_tail!=tail:
                raise gate.Abort('source tail residency unstable')
            tail=actual_tail
            pinned=[x for x in source_slot.get('checkpoints',[]) if x.get('n_tokens')==T and x.get('pinned') and x.get('pos_max')==T-1]
            if not pinned or len(src.get('tokens',[]))!=N or (src.get('timings') or {}).get('draft_n',0)<=0:
                raise gate.Abort('source/pinned checkpoint/decode missing')
            result,tr,span=request(gate,ctx,R,srv,f'X{index}_native_child',gate.body_for(child,N,1,fork=True,n_probs=20))
            timings=result.get('timings') or {}
            if timings.get('n_fork_tokens')!=T or timings.get('fork_src_slot')!=0 or timings.get('fork_src_kind')!='checkpoint':
                raise gate.Abort('native checkpoint fork did not execute')
            actual=first_target(tr)
            # M is authorized only by native fork telemetry AND native pool
            # shared count; the actual cell map is retained separately.
            live=slots_by_id(ctx)
            shared=(live[0].get('kv_cells') or {}).get('shared')
            if shared!=T:raise gate.Abort('native shared-cell set not exactly the junction')
            if fork_baseline is None:fork_baseline=actual
            elif actual['cells']!=fork_baseline['cells'] or actual['head']!=fork_baseline['head']:
                raise gate.Abort('native fork geometry unstable')
            partition=suffix_partitions(tr,'1',T=T,S=S)
            prefix=prefix_partitions(st,'0',T=T)
            if source_prefix_partition is None:source_prefix_partition=prefix
            elif prefix!=source_prefix_partition:raise gate.Abort('native source prefix write partition unstable')
            trials.append(dict(arm=arm,index=index,child=result,source=src,source_slots=slots,log_span=span,source_log_span=ss,
                               source_tail_private_cells=tail,source_prefix_partition=prefix,suffix_partition=partition,before_suffix=actual))
        else:
            if tail is None or tail>len(group['filler']):raise gate.Abort('no valid measured source tail')
            construction=[]
            R.extra.setdefault('kpf18_native_layout_construction',[]).append({'control':index,'attempts':construction})
            for attempt in range(1,4):
                if attempt>1:
                    gate.erase_all(ctx)
                    request(gate,ctx,R,srv,f'Cmask{index}_retry{attempt}_prefix_filler',gate.body_for(group['filler'],0,2,fork=False,cache=False,n_probs=0))
                seed=seed_control(gate=gate,ctx=ctx,R=R,srv=srv,slot=1,source_ids=source,
                                  checkpoint=T,n_predict=N,control=index,attempt=attempt)
                raw={'attempt':attempt,'raw_record_path':seed['raw_record_path'],'admitted':False}
                construction.append(raw)
                # Refuse early/late seeds before any mask or judged child.
                if seed['slot'].get('n_prompt_tokens')!=T or (seed['slot'].get('kv_cells') or {}).get('private')!=T:
                    raw['refusal']='postcancel native logical/private count != T'
                    continue
                mask,masktrace,maskspan=request(gate,ctx,R,srv,f'Cmask{index}_attempt{attempt}_native_mask_tail',gate.body_for(group['filler'][:tail],0,3,fork=False,n_probs=0))
                try:
                    prefix=prefix_partitions(chain(seed['seed_trace'],masktrace),'1',T=T)
                    probe=next(g for g in masktrace.contexts() if g['event']=='forward')
                    admitted=admit_seed(slot=seed['slot'],seed_task_id=seed['seed_task_id'],
                        expected_prefix_hash=seed['expected_prefix_hash'],events=seed['events'],
                        native_target=probe['target'],prefix_partition=prefix,reference_prefix_partition=source_prefix_partition,
                        current_task_generation_entered=seed['current_task_generation_entered'],
                        source_error_lines=seed['source_error_lines'],observed_cancel_task=seed['observed_cancel_task'])
                    df_boundary=draft_boundary(native_base=probe['draft_base'],native_swa=probe['draft_swa'])
                except (TraceError,StopIteration) as error:
                    raw['refusal']=str(error)
                    continue
                raw.update(admitted=True,native_admission=admitted,draft_boundary=df_boundary)
                break
            else:
                raise gate.Abort('bounded full-prompt canceled-seed construction exhausted; no judged child')
            result,tr,span=request(gate,ctx,R,srv,f'Cmask{index}_child',gate.body_for(child,N,1,fork=False,n_probs=20))
            actual=first_target(tr)
            match=witness(fork_baseline,actual,T=T)
            part=suffix_partitions(tr,'1',T=T,S=S)
            previous=next(x for x in trials if x['arm']=='X')['suffix_partition']
            if part!=previous:raise gate.Abort('native suffix physical allocation/partition mismatch')
            tm=result.get('timings') or {}
            if tm.get('cache_n')!=T or tm.get('prompt_n')!=S or tm.get('n_fork_tokens',0)!=0:
                raise gate.Abort('control native reuse/partition invalid')
            nofork_continuation(row=result,log_lines=tr.lines())
            trials.append(dict(arm=arm,index=index,child=result,log_span=span,geometry=match,suffix_partition=part,
                               before_suffix=actual,cancel_construction=construction,mask_log_span=maskspan,
                               draft_boundary=df_boundary))
        if len(result.get('tokens',[]))!=N or (result.get('timings') or {}).get('draft_n',0)<=0:
            raise gate.Abort('child token count or DFlash2 inactive')
    nz=srv.sampler.n_own_nonzero-before_nz
    if nz<2:raise gate.Abort('no during-block native own-pid residency')
    R.extra['kpf18_native_layout']={'schema':'epyc.kpf18.native-layout.v1','trials':trials,'native_tail_cells':tail,
                                  'during_block_own_vram_nonzero_samples':nz,'load_replicates':1,
                                  'interpretation':'matched geometry only; canonical token/top2/acceptance judge must still pass'}
    return trials
