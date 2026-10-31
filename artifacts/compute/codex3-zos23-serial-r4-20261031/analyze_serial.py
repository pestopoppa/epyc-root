#!/usr/bin/env python3
"""Original GPU-ZOS-2.3 G-DET serial fallback; no speed promotion from this tier."""
import datetime,json,pathlib,hashlib
G=pathlib.Path('/mnt/raid0/llm/tmp/codex-ni-gpu-zos-build-prep-20261031/successor/gpu/serial-tier'); O=G/'out'
def responses(arm):
    waves=[json.loads(s) for s in (O/arm/'waves.jsonl').read_text().splitlines()]
    assert [w['wave'] for w in waves]==list(range(9))
    assert all(len(w['responses'])==1 and len(w.get('graph_proofs',[]))==1 for w in waves)
    return [w['responses'][0] for w in waves[1:]]
def same(a,b):
    if not all(isinstance(x.get('tokens'),list) and x['tokens'] and isinstance(x.get('content'),str) and x['content'] and all(k in x.get('timings',{}) for k in ('draft_n','draft_n_accepted')) for x in (a,b)):return False
    return all(a.get(k)==b.get(k) for k in ('tokens','content')) and all(a.get('timings',{}).get(k)==b.get('timings',{}).get(k) for k in ('draft_n','draft_n_accepted'))
a1,a2,b,o=[responses(x) for x in ('SA1','SA2','SB','SO')]
aa=all(same(x,y) for x,y in zip(a1,a2))
bo=all(same(x,y) and same(x,z) for x,y,z in zip(a1,b,o))
core=json.loads((O/'RESULT.json').read_text())
valid=core['verdict']=='INCONCLUSIVE_SERIAL_REQUIRED' and core['g_det_fallback']['within_tolerance']
result={'schema':'ni.gpu_zos2_serial_fallback.v1','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'core_sha256':hashlib.sha256((O/'RESULT.json').read_bytes()).hexdigest(),'run_intent_sha256':hashlib.sha256((O/'RUN-INTENT-serial.json').read_bytes()).hexdigest(),'m_AA':core['g_det_fallback']['m_AA'],'np4_within_tolerance':valid,'serial_AA_identical':aa,'serial_B_O_identical':bo,'correctness':'PASS' if valid and aa and bo else 'INCONCLUSIVE','ship_authorized':False,'reason':'Serial tier resolves correctness only; original speed and all other gates remain required'}
path=O/'SERIAL-RESULT.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(result,indent=2)+'\n');tmp.replace(path)
print(result['correctness'])
