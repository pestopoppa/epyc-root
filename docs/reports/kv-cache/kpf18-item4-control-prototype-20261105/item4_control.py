"""Item-4 mixed-batch request orchestration; diagnostic only, no gate verdict.

Embedding caller MUST own a live server, supervise STOP/deadline/process cleanup,
prove mapped binaries and model/prompt custody, capture trace and raw logits, and
call the native witness guard. This module does not launch a server.
"""
import threading
import time

class Refusal(RuntimeError):
    pass


def run_arm(gate, ctx, group, prefix, *, fork, n_predict=256,
            decoder_tokens=1024, timeout_s=1800):
    """Run one arm with explicit slots and require final HTTP task bindings.

    Calls are bounded by the caller's boundary check. The returned requests do
    not alone establish a matching physical ubatch, layout, or raw logits.
    """
    if type(prefix) is not int or prefix < 1 or type(n_predict) is not int or n_predict < 1:
        raise Refusal('invalid request size')
    if type(decoder_tokens) is not int or decoder_tokens < 8 or timeout_s <= 0:
        raise Refusal('invalid decoder budget or deadline')
    deadline = time.monotonic() + timeout_s
    group_data = gate.G(ctx, group)
    trunk = group_data['trunk']
    source = gate.cat(trunk, group_data['src_tail_long'])
    target = gate.cat(trunk, group_data['suffixes'][ctx.args.item4_suffix])
    if len(trunk) != prefix or len(source) <= prefix or len(target) <= prefix:
        raise Refusal('invalid prompt geometry')
    def boundary():
        ctx.check_boundary()
        if time.monotonic() >= deadline:
            raise Refusal('deadline')
    def body(ids, n, slot, **kw):
        value = gate.body_for(ids, n, slot, **kw)
        # Every request disables speculation; raw capture is first-token only.
        value['speculative.n_max'] = 0
        return value
    def valid(response, slot):
        if not isinstance(response, dict) or response.get('http') != 200:
            raise Refusal('request failed')
        timing = response.get('timings') or {}
        task = timing.get('id_task')
        if type(task) is not int or task < 0 or timing.get('id_slot') != slot:
            raise Refusal('missing native HTTP task/slot binding')
        return {'slot':slot, 'task':task, 'response':response}
    boundary()
    gate.erase_all(ctx)
    if not fork:
        # Own checkpoint is established before concurrent workload starts.
        seed = ctx.client.complete(body(trunk, 0, 3, fork=False, ckpt=[prefix], n_probs=0))
        valid(seed, 3)
        checkpoints = ctx.client.slots()[3].get('checkpoints') or []
        if not any(c.get('n_tokens') == prefix and c.get('pinned') for c in checkpoints):
            raise Refusal('target seed checkpoint not pinned')
    done = [threading.Event() for _ in range(3)]
    responses = [None, None, None]
    errors = [None, None, None]
    def call(index, ids, n, slot, **kw):
        try:
            responses[index] = ctx.client.complete(body(ids, n, slot, **kw), timeout=timeout_s)
        except Exception as e:
            errors[index] = repr(e)
        finally:
            done[index].set()
    threads=[]
    for d in range(2):
        t=threading.Thread(target=call,args=(d,ctx.ps.decoders[d],decoder_tokens,1+d),
                           kwargs={'fork':False,'n_probs':0},daemon=True)
        t.start(); threads.append(t)
    snapshot = None
    while True:
        boundary()
        snapshot=ctx.client.slots()
        if len(snapshot)<4: raise Refusal('missing slot snapshots')
        if any(done[d].is_set() for d in range(2)): raise Refusal('decoder finished before overlap')
        if all(snapshot[1+d].get('is_processing') and
               (snapshot[1+d].get('next_token') or {}).get('n_decoded',0) >= 8 for d in range(2)):
            break
        done[0].wait(.25)
    t=threading.Thread(target=call,args=(2,source,0,0),
                       kwargs={'fork':False,'ckpt':[prefix],'n_probs':0},daemon=True)
    t.start();threads.append(t)
    junction = None
    while True:
        boundary()
        if done[2].is_set() or any(done[d].is_set() for d in range(2)):
            raise Refusal('source/decoder finished before junction')
        slots=ctx.client.slots()
        s=slots[0]
        ck=[c for c in (s.get('checkpoints') or []) if c.get('n_tokens') == prefix and c.get('pinned')]
        if ck and s.get('is_processing') and int(s.get('n_prompt_tokens') or 0)<len(source):
            junction={'source':s,'decoders':[slots[1],slots[2]],'checkpoint':ck[0]}
            if not all(x.get('is_processing') for x in junction['decoders']):
                raise Refusal('decoder overlap lost')
            break
        done[2].wait(.25)
    boundary()
    child=ctx.client.complete(body(target,n_predict,3,fork=fork,cache=True,n_probs=ctx.args.n_probs),timeout=timeout_s)
    target_binding=valid(child,3)
    timing=child.get('timings') or {}
    if fork:
        if timing.get('fork_src_kind') != 'checkpoint' or timing.get('n_fork_tokens') != prefix or timing.get('fork_src_slot') != 0:
            raise Refusal('child did not fork expected checkpoint')
    elif timing.get('cache_n') != prefix or timing.get('n_fork_tokens'):
        raise Refusal('control did not report target prefix restore')
    for event in done:
        while not event.is_set():
            boundary()
            event.wait(.25)
    if any(errors): raise Refusal('background request exception: '+repr(errors))
    bindings=[valid(responses[i], i+1) for i in range(2)]
    src_binding=valid(responses[2],0)
    all_bindings=[src_binding,*bindings,target_binding]
    if len({b['task'] for b in all_bindings}) != 4:
        raise Refusal('duplicate task ids')
    for snap, binding in zip([junction['source'],*junction['decoders']], all_bindings):
        if snap.get('id_task') != binding['task']:
            raise Refusal('active slot identity does not match final response')
    return {'fork':fork,'prefix':prefix,'junction':junction,'src':src_binding,
            'decoders':bindings,'target':target_binding}


def first_logits(raw, binding, expected_position, expected_input_token):
    """Return exact first-token bits for a final-response task, or refuse.

    Callers own file identity/size and collection. No reading of live log files
    here: they must supply a retained, complete snapshot after request end.
    """
    import json
    import math
    import struct
    if not isinstance(raw, bytes) or not raw.endswith(b'\n'):
        raise Refusal('missing or incomplete raw-logit stream')
    try:
        rows=[json.loads(line) for line in raw.splitlines() if line.strip()]
    except (ValueError, UnicodeDecodeError):
        raise Refusal('malformed raw-logit stream') from None
    if any(not isinstance(x,dict) for x in rows): raise Refusal('non-object raw logit row')
    hits=[x for x in rows if x.get('slot')==binding['slot'] and x.get('task')==binding['task']]
    if len(hits)!=1: raise Refusal('missing or ambiguous first-logit record')
    r=hits[0]; bits=r.get('float32_bits_u32'); n=r.get('n_vocab')
    if r.get('schema')!='kpf.first_logits.v1' or r.get('scope')!='first_token_speculation_disabled':
        raise Refusal('raw-logit scope invalid')
    if type(n) is not int or n <= 0 or not isinstance(bits,list) or len(bits)!=n:
        raise Refusal('incomplete vocabulary vector')
    if r.get('position')!=expected_position or r.get('input_token')!=expected_input_token:
        raise Refusal('raw logits belong to another input position')
    tokens=(binding.get('response') or {}).get('tokens') or []
    selected=r.get('selected_token')
    if type(selected) is not int or selected<0 or selected>=n or not tokens or tokens[0]!=selected:
        raise Refusal('raw logits not bound to first returned token')
    if any(type(v) is not int or v<0 or v>0xffffffff for v in bits):
        raise Refusal('invalid float bit patterns')
    vals=[struct.unpack('<f',struct.pack('<I',v))[0] for v in bits]
    if not all(math.isfinite(v) for v in vals): raise Refusal('non-finite raw logits')
    return {'task':binding['task'],'slot':binding['slot'],'selected_token':selected,
            'n_vocab':n,'bits':bits}


def pair_observation(guard, trace, raw_logits, first, second, first_last_token, second_last_token):
    """Validate two arm witnesses and capture raw diagnostics, never a gate verdict."""
    try:
        wa=guard.guard(trace, target=first['target'],src=first['src'],decoders=first['decoders'],prefix=first['prefix'])
        wb=guard.guard(trace, target=second['target'],src=second['src'],decoders=second['decoders'],prefix=second['prefix'])
        guard.compare(wa,wb)
        fa=first_logits(raw_logits,first['target'],*first_last_token)
        fb=first_logits(raw_logits,second['target'],*second_last_token)
        if fa['n_vocab']!=fb['n_vocab']: raise Refusal('vocabulary mismatch')
    except (ValueError,Refusal) as e:
        return {'status':'UNKNOWN','reason':str(e),'gate_verdict':None}
    return {'status':'OBSERVATION_ONLY','gate_verdict':None,
            'first_token_equal':fa['selected_token']==fb['selected_token'],
            'raw_logits_bit_identical':fa['bits']==fb['bits'],
            'n_vocab':fa['n_vocab'], 'scope':'speculation disabled; first token only'}
