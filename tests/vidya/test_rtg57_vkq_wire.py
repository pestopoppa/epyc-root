"""Synthetic end-to-end timing capture and tamper control, no inference."""
import sys, pathlib, json, hashlib, datetime, shutil, statistics
import pytest

@pytest.mark.parametrize("threads", [48, 96])
def test_native_timing_writer_to_private_planner(tmp_path, threads):
    base=tmp_path; root=pathlib.Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'scripts/vidya'))
    import ingest_sources, loop_beliefs
    from ledger import Ledger
    src=root/f'artifacts/operator/rtg57-f32-prep/t{threads}'; case=base/f'synthetic-t{threads}'; D=case/'packet'; out=D/'out';out.mkdir(parents=True,exist_ok=False)
    for f in ('driver.py','SOURCES.sha256'): shutil.copyfile(src/f,D/f)
    shutil.copyfile(src/'PROTOCOL.md',case/'PROTOCOL.md')
    sha=lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
    source='c72ec82f5417bb2937310326120f149b665e8400'; recipe='a'*64
    model='/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf'
    (out/'identity.json').write_text(json.dumps({'source':source,'recipe_sha256':recipe,'threads':threads,'cpus':'0-95','sha256':{model:'a'*64}}))
    for n in ('linkage.txt','verdict.json'): (out/n).write_text('synthetic')
    arms=['HYBRID','F32','F32','HYBRID','HYBRID','F32'];results={}
    for i,arm in enumerate(arms,1):
     prefix=f'{i}-{arm}';rate=101 if arm=='F32' else 100
     rows=[{'n_gen':1 if n==1 else 0,'n_prompt':0 if n==1 else n,'n_depth':d,'avg_ts':rate,'autokernel_hardened':False} for n,d in [(1,8192),(5,8192),(1,32768),(5,32768)]]
     (out/f'{prefix}.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
     for ext in ('err','process.json'): (out/f'{prefix}.{ext}').write_text('synthetic')
     (out/f'{prefix}.maps').write_text('/mnt/raid0/llm/tmp/refactor-01a16fc3/c5-candidate/buildcpu/bin/libggml-cpu.so.0.16.0')
     (out/f'{prefix}.numa').write_text('PASS'); env={'GGML_FA_SPLIT_KV':'0'}
     if arm=='F32':env['GGML_FA_VKQ_F32']='1'
     (out/f'{prefix}.env.json').write_text(json.dumps(env))
    for n,d in [(1,8192),(5,8192),(1,32768),(5,32768)]:results[str((n,d))]={'effects':[.01,.01,.01],'median':.01}
    # Execute the exact approved driver's receipt-writing statements, with all inputs synthetic.
    text=(src/'driver.py').read_text(); start=text.index('    evidence = {p.name:sha(p)'); end=text.index('    with (out/\'projected-claims.json\')',start)
    import textwrap
    class Recipe:
     @staticmethod
     def recipe_sha256():return recipe
    verdict='NO_COST';exec(textwrap.dedent(text[start:end]),{'out':out,'sha':sha,'datetime':datetime,'json':json,'hashlib':hashlib,'D':D,'recipe':Recipe,'arms':arms,'results':results,'verdict':verdict,'pathlib':pathlib,'__file__':str(D/'driver.py')})
    asof=datetime.datetime.now(datetime.timezone.utc).isoformat(); ledger=case/'ledger.jsonl'
    r=ingest_sources.ingest(Ledger(ledger),'rtg57-vkq-comparison',[out/'native-receipt.json'],as_of=asof);print('INGEST',json.dumps(r));assert r['rows_projected']==4 and not r['refused']
    class Sync:
     def status(self,*args):return {'fresh':True,'lag_entries':0,'index_max_id':0,'synced_max_id':0,'last_sync':asof}
    cfg=case/'alarm.yaml';cfg.write_text('backend: file\nfile:\n  path: '+str(case/'alarms.jsonl')+'\n')
    a=loop_beliefs.prepare('rtg57.synthetic.canary',{'model_file':pathlib.Path(model).name,'quant':'UD-IQ4_XS','backend':'cpu'},ledger=ledger,index_path=case/'index',as_of=asof,sync_module=Sync(),known_good=case/'known_good.json',alarm_state=case/'alarm.json',alarm_config=cfg,read_log=case/'read.jsonl');(case/'context.json').write_text(json.dumps(a,indent=2,default=str));print('CONTEXT',json.dumps(a,default=str));assert a['status']=='ready' and len(a['evidence']['claim_ids'])==4
    (out/'1-HYBRID.jsonl').write_text('tamper');r2=ingest_sources.ingest(Ledger(case/'tamper-ledger.jsonl'),'rtg57-vkq-comparison',[out/'native-receipt.json'],as_of=asof);print('TAMPER',json.dumps(r2));assert len(r2['refused'])==1 and r2['rows_projected']==0


def test_original_oracle_ingests_without_model_scope(tmp_path):
    root = pathlib.Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "scripts/vidya"))
    import ingest_sources
    from ledger import Ledger
    import loop_beliefs
    receipt = root / "artifacts/operator/rtg57-f32-prep/oracle/out/native-receipt.json"
    ledger = Ledger(tmp_path / "ledger.jsonl")
    asof = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report = ingest_sources.ingest(ledger, "rtg57-vkq-oracle", [receipt], as_of=asof)
    assert report["rows_projected"] == 1 and not report["refused"]
    frames = [record.frame for record in ledger.read_all()]
    source = next(f for f in frames if f["frame_type"].endswith("source_observed/v1"))
    scope = source["assertion"]["applicability"]
    assert "model_file" not in scope and "device" not in scope
    evidence = next(f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1"))
    assert evidence["assertion"]["reps"] == 1 and evidence["assertion"]["protocol_id"] == ""
    assert evidence["assertion"]["grade"] == {"Q": "Judged", "T": "Located"}
