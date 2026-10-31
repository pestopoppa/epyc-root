#!/usr/bin/python3
"""Prospective RTG57 native-record projector; no grading ladder here."""
import hashlib, json, math, pathlib, statistics, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from claim_tuple import ClaimTuple, grade

def digest(data): return hashlib.sha256(data).hexdigest()
def project(receipt_path):
    path=pathlib.Path(receipt_path).resolve(); out=path.parent
    record=json.loads(path.read_text()); native_hash=record.pop('content_sha256')
    if native_hash != digest(json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False).encode()): raise ValueError('receipt hash')
    if record.get('schema') != 'epyc.rtg57.vkq_comparison.native.v1' or record.get('source_commit') != 'c72ec82f5417bb2937310326120f149b665e8400' or record.get('protocol_id') is not None or record.get('n_process_pairs') != 3 or record.get('arm_order') != ['HYBRID','F32','F32','HYBRID','HYBRID','F32']: raise ValueError('scope')
    for name, want in record['evidence_sha256'].items():
        p=out/name
        if pathlib.PurePath(name).name != name or not p.is_file() or p.is_symlink() or digest(p.read_bytes()) != want: raise ValueError('evidence hash')
    producer=pathlib.Path(__file__).resolve().parent
    protocol=producer/'PROTOCOL.md'
    if digest(protocol.read_bytes()) != record['predeclared_rule_sha256']: raise ValueError('rule hash')
    if digest((producer/'SOURCES.sha256').read_bytes()) != record['source_manifest_sha256'] or digest((producer/'driver.py').read_bytes()) != record['producer_script_sha256']: raise ValueError('producer binding')
    if not {'identity.json','linkage.txt','verdict.json'} <= set(record['evidence_sha256']): raise ValueError('missing identity or linkage')
    identity=json.loads((out/'identity.json').read_text())
    if identity.get('source') != record['source_commit'] or identity.get('recipe_sha256') != record['recipe_sha256'] or identity.get('threads') != 96 or identity.get('cpus') != '0-95': raise ValueError('identity mismatch')
    arms=record['arm_order']; units=[]
    for i,arm in enumerate(arms,1):
        name=f'{i}-{arm}.jsonl'
        required={name,*[f'{i}-{arm}.{suffix}' for suffix in ('err','env.json','maps','numa','process.json')]}
        if not required <= set(record['evidence_sha256']): raise ValueError('missing raw arm or process evidence')
        env=json.loads((out/f'{i}-{arm}.env.json').read_text())
        if 'GGML_FA_VKQ_F16' in env or env.get('GGML_FA_VKQ_F32') != ('1' if arm=='F32' else None) or env.get('GGML_FA_SPLIT_KV') != '0': raise ValueError('arm env')
        if '/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/buildcpu/bin/libggml-cpu.so.0.16.0' not in (out/f'{i}-{arm}.maps').read_text(): raise ValueError('mapped library')
        if 'ADVISORY' in (out/f'{i}-{arm}.numa').read_text(): raise ValueError('unproven placement')
        rows=[json.loads(s) for s in (out/name).read_text().splitlines() if s.startswith('{')]
        if len(rows)!=4 or any(r.get('autokernel_hardened') is not False for r in rows): raise ValueError('invalid raw arms')
        unit={(1 if r['n_gen'] else r['n_prompt'],r['n_depth']):r['avg_ts'] for r in rows}
        if set(unit)!={(1,8192),(5,8192),(1,32768),(5,32768)} or any(not math.isfinite(x) or x<=0 for x in unit.values()): raise ValueError('invalid cells')
        units.append(unit)
    claims=[]
    for key in units[0]:
        effects=[(units[b][key]-units[a][key])/units[a][key] for a,b in ((0,1),(3,2),(4,5))]
        value=statistics.median(effects); native=record['cells'][str(key)]
        if not math.isclose(native['median'],value,rel_tol=1e-12,abs_tol=1e-12) or len(native['effects'])!=3 or any(not math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12) for a,b in zip(native['effects'],effects)): raise ValueError('effect drift')
        tup=ClaimTuple(measurement_id=f'rtg57-{native_hash[:16]}-{key[0]}-{key[1]}',metric='vkq_f32_relative_throughput',value=value,date=record['completed_utc'],category='CANDIDATE',claim=f'C5 T96 CPU F32 vs hybrid relative throughput, N={key[0]}, depth={key[1]}; indicative, no correctness acceptance',metric_direction='higher_better',protocol_id='',reps=3,reps_basis='scored:3 paired process launches',unit='fraction',attestation_locator=str(path),attestation_sha256=digest(path.read_bytes()),attestation_present=True,attestation_verified=True,source_kind='measurement',extra={'native_receipt_content_sha256':native_hash,'rule_sha256':record['predeclared_rule_sha256']})
        level,tier,reasons=grade(tup)
        claims.append({'measurement_id':tup.measurement_id,'metric':tup.metric,'value':tup.value,'unit':tup.unit,'direction':tup.metric_direction,'protocol_id':tup.protocol_id,'reps':tup.reps,'date':tup.date,'claim':tup.claim,'grade':[level,tier,reasons],'attestation_sha256':tup.attestation_sha256})
    return claims
if __name__=='__main__':
    print(json.dumps(project(sys.argv[1]),sort_keys=True,indent=2))
