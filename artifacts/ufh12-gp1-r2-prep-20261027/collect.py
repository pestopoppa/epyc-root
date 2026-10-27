#!/usr/bin/env python3
"""G-P1: exact four-element requests, pinned input/reference, native gate and writer."""
import hashlib, json, os, shutil, sys, time, urllib.request
from pathlib import Path
import numpy as np

BASE = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ufh12-shipped-parity/successor')
ORCH = BASE / 'orch'
ROOT = Path('/mnt/raid0/llm/worktrees/ufh12-shipped-parity-root')
REF = Path('/mnt/raid0/llm/tmp/repl-emb-25-26-20261020/out25/gate-probe45')
sys.path.insert(0, str(ORCH / 'scripts/benchmark'))
import repl_emb_arms as arms
import repl_emb_parity_gate as gate
PINS = {'items.json':'0b372c2b0a761f9f82161d30ac12c412c2808a90e123df1c72a41c5a2d4d6912', 'vec-st-fp32-full.npz':'88497cc276bb91fd4b58717e8f440f004197944082fe70ba398a8aa70887eb3a','lane-st-fp32-full.json':'6290e9c4027b11444db90fb697e82cb81bad286b8469d403b3729c599266c2eb'}
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(cond, msg):
    if not cond: raise ValueError(msg)
def run(url, out, meta):
    out = Path(out)
    require(not out.exists(), 'stale output directory')
    for name, sha in PINS.items(): require(digest(REF/name)==sha, 'reference digest mismatch: '+name)
    items=json.loads((REF/'items.json').read_text())
    reference=json.loads((REF/'lane-st-fp32-full.json').read_text())
    spec=gate._spec('st-fp32-full')
    require(reference['index_identity']==spec.index_identity(), 'reference identity/prefix mismatch')
    require(items['n_chunks']==211 and len(items['doc_texts'])==211 and len(items['chunks'])==211 and len(items['queries'])==45 and items['query_set_is_ufh07'], 'wrong item scope')
    for text, chunk in zip(items['doc_texts'],items['chunks']): require(hashlib.sha256(text.encode()).hexdigest()==chunk['text_sha256'], 'chunk hash mismatch')
    ref=np.load(REF/'vec-st-fp32-full.npz')
    require(ref['docs'].shape==(211,768) and ref['queries'].shape==(45,768) and np.isfinite(ref['docs']).all() and np.isfinite(ref['queries']).all(), 'invalid reference')
    adapter=arms.LlamaServerAdapter(gate._spec('gguf-bf16'),url)
    inputs=adapter._prefixed(items['doc_texts'],'document')
    for q in items['queries']:
        with adapter.query_intent(q['code_intent']): inputs.extend(adapter._prefixed([q['text']],'query'))
    require(len(inputs)==256 and all(isinstance(x,str) and x for x in inputs), 'invalid inputs')
    outputs=[]
    for i in range(0,256,4):
        group=inputs[i:i+4]; require(len(group)==4,'batch size')
        body=json.dumps({'input':group,'encoding_format':'float'}).encode()
        request=urllib.request.Request(url.rstrip('/')+'/v1/embeddings', data=body, headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=120) as response: payload=json.load(response)
        rows=payload['data']
        require(isinstance(rows,list) and len(rows)==4 and sorted(r['index'] for r in rows)==[0,1,2,3], 'response indices')
        rows=sorted(rows,key=lambda x:x['index'])
        raw=np.asarray([r['embedding'] for r in rows],dtype=np.float32)
        require(raw.shape==(4,768), 'response shape')
        outputs.extend(raw)
    matrix=np.asarray(outputs,dtype=np.float32)
    require(matrix.shape==(256,768),'matrix shape')
    out.mkdir(parents=True)
    for name in PINS: shutil.copyfile(REF/name,out/name)
    np.savez(out/'vec-gguf-bf16.npz',docs=matrix[:211],queries=matrix[211:])
    lane={'lane':'gguf-bf16','arm_id':adapter.spec.arm_id,'index_identity':adapter.spec.index_identity(),'threads':4,'n_docs':211,'n_queries':45,'raw_dim':768}
    (out/'lane-gguf-bf16.json').write_text(json.dumps(lane,indent=2))
    result=gate.compare(out,{k:v for k,v in items.items() if k!='doc_texts'})
    (out/'parity.json').write_text(json.dumps(result,indent=2))
    gate.belief_capture(out,out/'belief',meta,run_id='ufh12-gp1-shipped-argv',epyc_root=str(ROOT))
    decision=result['lanes']['gguf-bf16']
    require(result['scope_complete'], 'scope incomplete')
    require(decision['verdict']=='PASS', 'G-P1 FAIL')
    (out/'RESULT.json').write_text(json.dumps({'status':'PASS','min_cosine':decision['cos_min_all_items'],'nonfinite':decision['nonfinite_vectors_total'],'requests':64,'request_size':4},indent=2))
if __name__=='__main__':
    run(sys.argv[1],sys.argv[2],Path(sys.argv[3]))
