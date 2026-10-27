#!/usr/bin/env python3
"""Synthetic producer -> registry -> planning canary; outputs never become real evidence."""
import argparse, hashlib, importlib.util, json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; HERE=ROOT/'scripts/vidya'
sys.path.insert(0,str(HERE))
import claim_tuple, ingest_sources, loop_beliefs
from ledger import Ledger

class Sync:
    def status(self,*a,**kw): return {'fresh':True,'lag_entries':0,'index_max_id':1,'synced_max_id':1,'last_sync':datetime.now(timezone.utc).isoformat()}
    def sync(self,*a,**kw): raise AssertionError('unexpected sync')

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--out',required=True); parser.add_argument('--runtime-seal',required=True); a=parser.parse_args()
    out=Path(a.out).resolve(); out.mkdir(parents=True,exist_ok=False)
    producer=HERE/'producers/ufh12_gs_capture.py'; helper=HERE/'producers/ufh12_gs_diagnostic.py'; adapter=HERE/'adapters/ufh12_gs_coverage.py'; registry=HERE/'ingest_sources.py'; carrier=HERE/'adapters/_native_sidecar.py'; seal=Path(a.runtime_seal).resolve(strict=True)
    spec=importlib.util.spec_from_file_location('canary_ufh12_producer',producer); p=importlib.util.module_from_spec(spec); spec.loader.exec_module(p); d=p.d
    ids={'episodic':[f'e-{i:04}' for i in range(489)],'strategy':[f's-{i:04}' for i in range(11)]}; selection={}
    for kind in ids:
        selection[kind]=sorted(ids[kind],key=lambda x:(hashlib.sha256((d.SEED+'\0'+kind+'\0'+x).encode()).digest(),x))
    fake_model=out/'synthetic-fixture.gguf'; fake_model.write_text('synthetic identity only, no weights')
    manifest={'seed':d.SEED,'selection':selection,'corpus_ids':ids,'counts':{k:len(v) for k,v in ids.items()},'pins':{str(fake_model):sha(fake_model)},'bge_query_prefix':'','eg2_query_prefix':d.QUERY,'eg2_document_prefix':d.DOC,'query_kind':'stored-text proxy; not observed queries or relevance labels'}
    d.save(out/'manifest.json',manifest); mh=sha(out/'manifest.json'); proof=out/'synthetic-proof.txt'; proof.write_text('synthetic canary, no model and no measurement\n')
    ctx={'region_lock_claim':'SYNTHETIC_CANARY','server_proof':{str(proof):sha(proof)},'synthetic':True,'model_path':str(fake_model),'model_sha256':sha(fake_model)}; ident=selection['episodic'][0]
    neighbours=[{'id':x,'cosine':0.5} for x in sorted(set(ids['episodic'])-{ident})[:10]]
    name='score-'+hashlib.sha256(('episodic\0'+ident).encode()).hexdigest()+'.json'
    d.save(out/name,d.seal({'manifest_sha256':mh,'store':'episodic','id':ident,'bge':neighbours,'eg2':neighbours,'captured_at':d.now(),'context':ctx}))
    d.save(out/'tokens-episodic-000000.json',d.seal({'manifest_sha256':mh,'ids':ids['episodic'][:1],'counts':[3],'contexts':[ctx],'captured_at':d.now()}))
    sidecars=[p.emit(out,facet,ctx)[1] for facet in ('scores','tokens')]
    module=ingest_sources.SOURCES['ufh12-gs-coverage'].load()
    if Path(module.__file__).resolve()!=adapter: raise RuntimeError('foreign adapter')
    ledger=out/'canary-ledger.jsonl'; asof=d.now(); reports=[]
    for side in sidecars:
        native=module.native_rows(side); claim=module.project(native[0]);
        if claim.value!=1 or claim.protocol_id!='' or claim.extra.get('synthetic') is not True or claim_tuple.grade(claim)[:2]!=('Judged','Located'): raise RuntimeError('fixture projection mismatch')
        report=ingest_sources.ingest(Ledger(ledger),'ufh12-gs-coverage',[side],as_of=asof); reports.append(report)
        if report['rows_projected']!=1 or report['refused']: raise RuntimeError('fixture ingest failed')
    cfg=out/'alarm.yaml'; cfg.write_text('backend: file\nfile:\n  path: '+str(out/'alarm.jsonl')+'\n')
    answer=loop_beliefs.prepare('test.ufh12_gs',{'backend':'cpu','model_file':'synthetic-fixture.gguf'},ledger=ledger,index_path=out/'index.yaml',as_of=asof,sync_module=Sync(),known_good=out/'known.json',alarm_state=out/'alarm-state.json',alarm_config=cfg,read_log=out/'reads.jsonl')
    claims=answer.get('evidence',{}).get('claims',[])
    visible=[x for x in claims if x.get('source_kind')=='ufh12-gs-coverage']
    (out/'planning-debug.json').write_text(json.dumps(answer,sort_keys=True,default=str))
    if answer['status']!='ready' or len(visible)!=2 or any(x.get('value')!=1 or x.get('unit')!='records' or x.get('model_file')!='synthetic-fixture.gguf' for x in visible): raise RuntimeError('planning context did not expose correct synthetic coverage values')
    evidence=out/'canary-evidence.json'; evidence.write_text(json.dumps({'synthetic':True,'reports':reports,'planning_status':answer['status'],'planning_evidence':answer['evidence']},sort_keys=True))
    receipt={'source_family':'VB-UFH12-GS','status':'passed','planning_context':'visible','synthetic':True,'installed_root':str(ROOT),'adapter_sha256':sha(adapter),'helper_sha256':sha(helper),'producer_sha256':sha(producer),'registry_sha256':sha(registry),'carrier_sha256':sha(carrier),'canary_sha256':sha(Path(__file__)),'runtime_source_seal_sha256':sha(seal),'evidence_path':str(evidence),'evidence_sha256':sha(evidence)}
    (out/'canary-receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n'); print(out/'canary-receipt.json')
if __name__=='__main__': main()
