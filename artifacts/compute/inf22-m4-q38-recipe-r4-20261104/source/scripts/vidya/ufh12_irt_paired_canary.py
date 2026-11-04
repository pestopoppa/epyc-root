#!/usr/bin/env python3
"""Synthetic native producer -> registry -> planning-context canary."""
import argparse,hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; HERE=ROOT/'scripts/vidya'; sys.path.insert(0,str(HERE))
import claim_tuple,ingest_sources,loop_beliefs
from ledger import Ledger
class Sync:
 def status(self,*a,**kw): return {'fresh':True,'lag_entries':0,'index_max_id':1,'synced_max_id':1,'last_sync':datetime.now(timezone.utc).isoformat()}
 def sync(self,*a,**kw): raise AssertionError('unexpected sync')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--out',required=True); parser.add_argument('--runtime-seal',required=True); args=parser.parse_args(); out=Path(args.out).resolve(); out.mkdir(parents=True,exist_ok=False)
 module=ingest_sources.SOURCES['ufh12-irt-paired'].load(); producer=module.p
 n=20; rng=np.random.default_rng(74); q=[f'fake-{i}' for i in range(n)]; tr=np.arange(16); te=np.arange(16,20); y=rng.random((n,3)); mask=np.ones_like(y,dtype=bool); bge=rng.normal(size=(n,1024)); eg2=rng.normal(size=(n,256)); ability=np.array([-1.,0.,1.]); z=y[te]; count=mask[te].sum(axis=1); success=z.mean(axis=1); clip=np.clip(success,1e-4,1-1e-4); diff=-np.log(clip/(1-clip)); delta=ability-ability.mean(); discr=np.abs(((z-success[:,None])*delta).sum(axis=1)/count/np.mean(delta**2)); truth=np.column_stack((diff,discr))
 np.savez_compressed(out/'dataset.npz',qids=q,bge=bge,correctness=y,observed_mask=mask,roles=['a','b','c'],train_indices=tr,heldout_indices=te)
 (out/'prompts.jsonl').write_text(''.join(json.dumps({'qid':x,'prompt':x})+'\n' for x in q)); manifest={'schema':'epyc.irt.p45_frozen_input.v1','artifacts_sha256':{name:sha(out/name) for name in ('dataset.npz','prompts.jsonl')},'train_qids':q[:16],'heldout_qids':q[16:]}; (out/'manifest.json').write_text(json.dumps(manifest))
 arrays={'eg2':eg2,'heldout_targets':truth,'action_abilities_train':ability}; metrics={}
 for arm,x,dim in [('bge',bge,1024),('eg2',eg2,256)]:
  weight=rng.normal(size=(dim+1,2)); mean=x[tr].mean(axis=0); pred=np.column_stack((x[te]-mean,np.ones(len(te))))@weight; pred[:,1]=np.maximum(pred[:,1],0); arrays.update({arm+'_prediction':pred,arm+'_feature_mean':mean,arm+'_feature_scale':np.ones(dim),arm+'_weights':weight,arm+'_target_mean':np.zeros(2),arm+'_target_scale':np.ones(2)}); metrics[arm]={k:producer.rho(truth[:,i],pred[:,i]) for i,k in enumerate(('difficulty_spearman','discrimination_spearman'))}
 np.savez_compressed(out/'result.npz',**arrays); runtime={'schema':'epyc.graph_router.irt_runtime.v1','synthetic':True}; (out/'runtime.json').write_text(json.dumps(runtime)); report={'schema':'epyc.graph_router.irt_eg2_paired.v1','source_scope':'SYNTHETIC fixture; not model measurement','manifest_sha256':sha(out/'manifest.json'),'artifact_sha256':sha(out/'result.npz'),'runtime':runtime,'runtime_sha256':sha(out/'runtime.json'),'input_artifacts':manifest['artifacts_sha256'],'train_count':16,'heldout_count':4,'metric_direction':'higher_is_better','metrics':metrics,'passed':all(metrics['eg2'][k]>=metrics['bge'][k] for k in metrics['bge'])}; (out/'result.json').write_text(json.dumps(report))
 side=producer.emit(out/'result.json',out,True); rows=module.native_rows(side); ledger=out/'canary-ledger.jsonl'; asof=datetime.now(timezone.utc).isoformat()
 for row in rows:
  claim=module.project(row)
  if claim.extra.get('synthetic') is not True or claim.protocol_id!='' or claim_tuple.grade(claim)[:2]!=('Judged','Located'): raise RuntimeError('invalid observation projection')
 record=json.loads(next(out.glob('*.record.json')).read_text()); record['synthetic']=False
 try: producer.rederive(record)
 except ValueError: pass
 else: raise RuntimeError('fixture accepted as real')
 artifact=out/'result.npz'; original=artifact.read_bytes(); artifact.write_bytes(original+b'tamper')
 try:
  try: module.native_rows(side)
  except Exception: pass
  else: raise RuntimeError('changed artifact accepted')
 finally: artifact.write_bytes(original)
 rep=json.loads(subprocess.run([sys.executable,str(HERE/'cli.py'),'--ledger',str(ledger),'--json','ingest','ufh12-irt-paired','--path',str(side),'--as-of',asof],check=True,capture_output=True,text=True).stdout)
 if rep['rows_projected']!=4 or rep['refused']: raise RuntimeError('ingest failed')
 cfg=out/'alarm.yaml'; cfg.write_text('backend: file\nfile:\n  path: '+str(out/'alarm.jsonl')+'\n'); answer=loop_beliefs.prepare('test.ufh12_irt',{'backend':'cpu','model_file':'synthetic-fixture.gguf'},ledger=ledger,index_path=out/'index.yaml',as_of=asof,sync_module=Sync(),known_good=out/'known.json',alarm_state=out/'alarm-state.json',alarm_config=cfg,read_log=out/'reads.jsonl'); visible=[x for x in answer.get('evidence',{}).get('claims',[]) if x.get('source_kind')=='ufh12-irt-paired']
 real=loop_beliefs.prepare('test.ufh12_irt',{'backend':'cpu','model_file':'embeddinggemma-2-BF16.gguf'},ledger=ledger,index_path=out/'index.yaml',as_of=asof,sync_module=Sync(),known_good=out/'known-real.json',alarm_state=out/'alarm-state-real.json',alarm_config=cfg,read_log=out/'reads-real.jsonl')
 real_fixture=[x for x in real.get('evidence',{}).get('claims',[]) if x.get('source_kind')=='ufh12-irt-paired']
 if real_fixture: raise RuntimeError('fixture leaked into real model planning context')
 (out/'planning-debug.json').write_text(json.dumps(answer,sort_keys=True,default=str))
 if answer['status']!='ready' or len(visible)!=4 or not np.allclose(sorted(x['value'] for x in visible),sorted(v for arm in metrics.values() for v in arm.values())): raise RuntimeError('planning context mismatch')
 evidence=out/'evidence.json'; evidence.write_text(json.dumps({'synthetic':True,'metrics':metrics,'report':rep,'planning_evidence':answer['evidence']},sort_keys=True)); files=[HERE/'adapters/ufh12_irt_paired.py',HERE/'producers/ufh12_irt_paired_capture.py',HERE/'ingest_sources.py',HERE/'cli.py',HERE/'adapters/_native_sidecar.py',Path(__file__),Path(args.runtime_seal)]; receipt={'status':'passed','synthetic':True,'planning_context':'visible','real_model_fixture_claims':0,'installed_root':str(ROOT),'pins':{str(p):sha(p) for p in files},'evidence_path':str(evidence),'evidence_sha256':sha(evidence)}; (out/'canary-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)); print(out/'canary-receipt.json')
if __name__=='__main__': main()
