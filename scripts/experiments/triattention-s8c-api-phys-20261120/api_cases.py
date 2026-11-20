"""Read serialized occupied cells and K/V bytes, then check bounded continuation."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from api_support import PROMPT, populate, request, require_owned_listener


def read_state(path):
    data = Path(path).read_bytes()
    offset = 0
    def take(fmt):
        nonlocal offset
        size = struct.calcsize('<' + fmt)
        if offset + size > len(data):
            raise ValueError('truncated state')
        result = struct.unpack_from('<' + fmt, data, offset)
        offset += size
        return result[0] if len(result) == 1 else result
    magic, version, nt = take('III')
    if magic != 0x67677371 or version != 3 or nt > 512:
        raise ValueError('unsupported sequence header')
    tokens = [take('i') for _ in range(nt)]
    if take('I') != 1:
        raise ValueError('expected one dense stream')
    count = take('I')
    if not 0 < count <= 512:
        raise ValueError('invalid occupancy')
    positions = []
    for _ in range(count):
        pos, nseq = take('iI')
        # Pinned Qwen3 dense layout has no cell extensions.
        if nseq != 1 or take('i') != 0:
            raise ValueError('unexpected sequence/layout')
        positions.append(pos)
    if len(set(positions)) != count:
        raise ValueError('duplicate cell positions')
    trans, layers = take('II')
    if trans != 0 or layers != 28:
        raise ValueError('expected Qwen3-1.7B nontransposed K/V, 28 layers')
    rows = {}
    for kind in ('K', 'V'):
        for layer in range(layers):
            dtype, width = take('iQ')
            if dtype != 1 or width != 2048:  # F16: 8 KV heads * 128 head dim
                raise ValueError(f'unexpected {kind} tensor type/width: {dtype}/{width}')
            for pos in positions:
                if offset + width > len(data):
                    raise ValueError('truncated tensor')
                rows[f'{kind}:{layer}:{pos}'] = hashlib.sha256(data[offset:offset+width]).hexdigest()
                offset += width
    if offset != len(data):
        raise ValueError('unparsed state suffix')
    return dict(positions=positions, tokens=tokens, rows=rows,
                sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))


def compare(before, after, response):
    b, a = set(before['positions']), set(after['positions'])
    recent = set(sorted(b)[-16:])
    return {
        'dense_before': sorted(b) == list(range(128)),
        'physical_eviction_count': len(b)-len(a) == response.get('n_evicted') and len(a) < len(b),
        'retained_positions_subset': a < b,
        'sink4_preserved': set(range(4)) <= a,
        'recent16_preserved': recent <= a,
        'retained_rows_identical': all(before['rows'].get(k) == v for k,v in after['rows'].items()),
        'response_max_matches': max(a) == response.get('pos_max_after'),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port',type=int,required=True)
    ap.add_argument('--server-pid',type=int,required=True)
    ap.add_argument('--server-sha256',required=True)
    ap.add_argument('--dso-hashes',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--slots',type=Path,required=True)
    args=ap.parse_args()
    result={'status':'invalid','cases':[]}
    def call(path, body):
        status,payload,raw=request(args.port,path,json.dumps(body).encode(),60)
        if status != 200 or not isinstance(payload,dict):
            raise RuntimeError(f'{path}: HTTP {status} {raw}')
        return payload
    def save(name):
        response=call('/slots/0?action=save',{'filename':name+'.bin'})
        state=read_state(args.slots/(name+'.bin'))
        result.setdefault('snapshots',{})[name]={k:v for k,v in state.items() if k!='rows'}
        result['snapshots'][name]['response']=response
        return state
    def continuation():
        # Forced single prefill token is appended so cached final logits need not
        # survive slot save/idle; the eight output IDs are unforced.
        return call('/completion',{'id_slot':0,'prompt':PROMPT+[23811],
                    'n_predict':8,'cache_prompt':True,'temperature':0,'seed':42,
                    'ignore_eos':True,'return_tokens':True})
    def record(name, checks, **extra):
        item=dict(case=name,pass_=all(checks.values()),checks=checks,**extra)
        item['pass']=item.pop('pass_')
        result['cases'].append(item)
        # Incremental observation; the full result remains the smoke predicate.
        with args.output.with_suffix('.jsonl').open('a') as out:
            out.write(json.dumps(item)+'\n')
        return item['pass']
    try:
        result['witness']=require_owned_listener(args.server_pid,args.port,args.server_sha256,
                                               json.loads(args.dso_hashes.read_text()))
        populate(args.port,60)
        control_before=save('control-before')
        control=continuation()
        control_after=save('control-after')
        populate(args.port,60)
        before=save('compact-before')
        compact=call('/slots/0?action=compact',{'keep_recent':16})
        after=save('compact-after')
        checks=compare(before,after,compact)
        checks['control_prefill_identical']=before['rows']==control_before['rows']
        if record('physical_compaction',checks,response=compact):
            candidate=continuation()
            final=save('compact-continuation')
            ct,xt=control.get('tokens'),candidate.get('tokens')
            valid_tokens=(isinstance(ct,list) and isinstance(xt,list) and len(ct)==len(xt)==8
                          and all(type(x) is int for x in ct+xt))
            continuation_checks={'eight_token_ids':valid_tokens,
                'finite_completion':candidate.get('tokens_predicted')==8 and control.get('tokens_predicted')==8,
                'final_position_comparable':max(final['positions'])==max(control_after['positions'])}
            record('continuation',continuation_checks,control=control,candidate=candidate,
                   equal_token_ids=ct==xt if valid_tokens else None)
            # Re-population of evicted prompt positions is observable and cannot
            # substantiate continuing from the compacted cache.
            removed=set(before['positions'])-set(after['positions'])
            replenished=sorted(removed & set(final['positions']))
            result['replenished_positions']=replenished
            result['status']=('fail' if not all(c['pass'] for c in result['cases']) else
                              'inconclusive' if replenished else 'pass')
        else:
            result['status']='fail'
    except Exception as exc:
        result['reason']=f'{type(exc).__name__}: {exc}'
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'cases':len(result['cases'])}))
    return 0 if result['status'] in ('pass','inconclusive') else 1

if __name__=='__main__':
    raise SystemExit(main())
