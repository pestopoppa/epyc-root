#!/usr/bin/env python3
"""Source-shaped typed snapshot decoder; no guessed STL offsets or live reads.

A qualified native writer must export private vector/bitset data using exact
historical DWARF or compiler-generated accessors. This preparation validates its
output and preserves UNKNOWN until that writer is independently qualified.
"""
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parent
COMMIT='a1f0c8cf9bd7102415a72577474f307b8ba94db9'
class Bad(ValueError): pass
class Missing(ValueError): pass
def integer(v, lo=0):
    if type(v) is not int or v<lo: raise Bad('noninteger or out-of-range value')
    return v
def field(obj,key):
    if not isinstance(obj,dict) or key not in obj or obj[key] is None: raise Missing('missing '+key)
    return obj[key]
def decode(s):
    result={'status':'UNKNOWN','native_binding':'UNKNOWN','historical_control':'UNKNOWN'}
    try:
        manifest=json.loads((ROOT/'source.json').read_text())
        for f,h in manifest['files'].items():
            if hashlib.sha256((ROOT/'source'/f).read_bytes()).hexdigest()!=h: raise Bad('source seal drift')
        if field(s,'source_commit')!=COMMIT: raise Bad('wrong historical source')
        if field(s,'schema')!='kpf131.typed-native-snapshot.v1': raise Bad('unknown schema')
        stream=integer(field(s,'stream')); slots=field(s,'slots'); cells=field(s,'cells'); batch=field(s,'ubatch')
        if not isinstance(cells,list) or not 0<len(cells)<=262144: raise Bad('unsupported cells shape')
        if not isinstance(slots,list) or not isinstance(batch,list) or not slots or not batch: raise Bad('empty binding arrays')
        ids={}; requests=set()
        for slot in slots:
            sid=integer(field(slot,'id')); task=integer(field(slot,'task_id')); request=field(slot,'request_id')
            if not isinstance(request,str) or not request: raise Bad('invalid request identity')
            if sid in ids or request in requests: raise Bad('duplicate slot/request')
            ids[sid]=(task,request); requests.add(request)
        rows=[]
        for i,c in enumerate(cells):
            pos=integer(field(c,'pos'),-1); seq=field(c,'seq_ids')
            if not isinstance(seq,list) or any(type(x) is not int or x<0 for x in seq) or len(set(seq))!=len(seq): raise Bad('malformed cell sequence set')
            if (pos==-1)!= (len(seq)==0): raise Bad('cell occupancy contradiction')
            rows.append({'physical_index':i,'position':pos,'seq_ids':seq})
        for token in batch:
            pos=integer(field(token,'pos')); seq=field(token,'seq_ids')
            if not isinstance(seq,list) or not seq or any(type(x) is not int or x<0 for x in seq) or len(set(seq))!=len(seq): raise Bad('malformed ubatch membership')
            task_bindings=field(token,'tasks')
            if not isinstance(task_bindings,list) or len(task_bindings)!=len(seq): raise Bad('task membership shape mismatch')
            seen=set()
            for b in task_bindings:
                sid=integer(field(b,'slot')); task=integer(field(b,'task_id')); req=field(b,'request_id')
                if sid in seen or sid not in seq or ids.get(sid)!=(task,req): raise Bad('slot/task/request mismatch')
                seen.add(sid)
            if seen!=set(seq): raise Bad('ubatch task coverage mismatch')
        result.update(structural_status='CONSISTENT',stream=stream,cells=rows,ubatch=batch)
        # Caller claims and invented offsets can never upgrade native qualification.
        result['reason']='Native writer/ABI offsets, stream ownership and event/request attribution require independent historical-image qualification; typed JSON alone is not that witness.'
    except Missing as e: result['reason']=str(e)
    except (Bad,TypeError,KeyError) as e: result.update(status='INVALID',reason=str(e))
    return result
if __name__=='__main__':
    obj=json.loads(pathlib.Path(sys.argv[1]).read_text())
    print(json.dumps(decode(obj),indent=2))
