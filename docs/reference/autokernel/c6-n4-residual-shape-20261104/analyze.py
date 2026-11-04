#!/usr/bin/env python3
"""Summarize observed candidate minus CPU-sibling residual by output coordinate."""
import hashlib,json,math,os,struct
from pathlib import Path
D=Path(__file__).resolve().parent
R=Path('/mnt/raid0/llm/tmp/akagg/ended-20261104-retained/akx-c6-q4k-n4-diagnostic-r2-20261104')
RESULT_SHA='05739394acb9d6d9cbf544eef31935f9ec88c1802cc3bc646909462acabaa7cc'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check_source(data):
    if hashlib.sha256(data).hexdigest() != RESULT_SHA:
        raise ValueError('retained result changed')
    return json.loads(data)

def capture_path(root, run, name):
    if name not in ('candidate_output.bin', 'sibling_output.bin'):
        raise ValueError('unexpected capture name')
    p=Path(run)
    if p.parent.name != ('run-' + '1793821833' + '552414812') or p.name not in ('0','1'):
        raise ValueError('unexpected run path')
    runs=(root/'runs').resolve(strict=True)
    result=(runs/p.parent.name/p.name/name).resolve(strict=True)
    if not result.is_relative_to(runs):
        raise ValueError('capture escaped retained root')
    return result

def unpack_pair(candidate, sibling, cm, sm):
    if len(candidate) % 4 or len(sibling) % 4:
        raise ValueError('unaligned float32 capture')
    if len(candidate) != len(sibling):
        raise ValueError('capture byte lengths differ')
    if cm['ne'] != sm['ne'] or cm['nb'] != sm['nb']:
        raise ValueError('capture shapes or strides differ')
    shape = [int(x) for x in cm['ne'].split(',')]
    strides = [int(x) for x in cm['nb'].split(',')]
    if len(shape) != 4 or any(x <= 0 for x in shape) or len(strides) != 4:
        raise ValueError('invalid shape')
    expected = [4, 4*shape[0], 4*shape[0]*shape[1], 4*shape[0]*shape[1]*shape[2]]
    if strides != expected or math.prod(shape)*4 != len(candidate):
        raise ValueError('capture is not complete contiguous float32')
    for data, metadata in ((candidate, cm), (sibling, sm)):
        if metadata['type'] != 0 or metadata['bytes'] != len(data) or hashlib.sha256(data).hexdigest() != metadata['sha256']:
            raise ValueError('type, size or digest mismatch')
    arrays = [struct.unpack('<%df' % (len(data)//4), data) for data in (candidate, sibling)]
    if any(not math.isfinite(x) for arr in arrays for x in arr):
        raise ValueError('nonfinite capture')
    return shape, arrays

def main():
    orig=R/'RESULT.json'
    source=check_source(orig.read_bytes()); out=[]
    for rec in source['records']:
        ord=rec['ordinal']
        cm=rec['capture']['candidate_output']; sm=rec['capture']['sibling_output']
        shape, arrays=unpack_pair(capture_path(R,rec['run'],'candidate_output.bin').read_bytes(), capture_path(R,rec['run'],'sibling_output.bin').read_bytes(), cm, sm)
        groups=[[] for _ in range(shape[1])]
        for i,(a,b) in enumerate(zip(*arrays)):groups[(i//shape[0])%shape[1]].append(a-b)
        stats=[{'column':i,'count':len(g),'max_abs':max(map(abs,g)),'rms':math.sqrt(sum(x*x for x in g)/len(g)),'mean':sum(g)/len(g)} for i,g in enumerate(groups)]
        out.append({'ordinal':ord,'shape':shape,'columns':stats,'capture_sha256':[rec['capture'][x]['sha256'] for x in ('candidate_output','sibling_output')]})
    if [x['ordinal'] for x in out]!=[7686,7699]:raise ValueError('unexpected ordinal set')
    dst=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if os.environ.get('FILLER_DRYRUN')=='1' else D/'RESULT.json'
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(json.dumps({'schema':'c6.n4.residual-shape.v1','status':'COMPLETE_DIAGNOSTIC','source_result_sha256':RESULT_SHA,'records':out,'scope':'descriptive captured output difference; no cause, gate, performance, or promotion verdict'},sort_keys=True)+'\n')
if __name__=='__main__':main()
