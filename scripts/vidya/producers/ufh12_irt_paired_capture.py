"""Prospective paired IRT correlations: capture and rederive, no new ladder."""
import hashlib, importlib.util, json, uuid
from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path
import numpy as np
CARRIER=Path(__file__).resolve().parents[1]/'adapters/_native_sidecar.py'
s=importlib.util.spec_from_file_location('irt_native',CARRIER); c=importlib.util.module_from_spec(s); s.loader.exec_module(c)
SCHEMA='epyc.vidya.irt_paired.v1'
def sha(p): return c.file_sha256(Path(p))
def ranks(v):
 order=np.argsort(v,kind='stable'); r=np.empty(len(v)); i=0
 while i<len(v):
  j=i+1
  while j<len(v) and v[order[j]]==v[order[i]]: j+=1
  r[order[i:j]]=(i+j-1)/2; i=j
 return r
def rho(a,b):
 a=ranks(a); b=ranks(b); a-=a.mean(); b-=b.mean(); den=np.linalg.norm(a)*np.linalg.norm(b)
 if not den: raise ValueError('undefined rho')
 return float(np.dot(a,b)/den)
def rederive(record):
 report_path=Path(record['report_path']); frozen=Path(record['frozen_path']); artifact=report_path.with_suffix('.npz')
 if sha(report_path)!=record['report_sha256'] or sha(frozen/'manifest.json')!=record['manifest_sha256']: raise ValueError('input changed')
 report=json.loads(report_path.read_text()); manifest=json.loads((frozen/'manifest.json').read_text())
 if report['schema']!='epyc.graph_router.irt_eg2_paired.v1' or report['manifest_sha256']!=sha(frozen/'manifest.json') or report['artifact_sha256']!=sha(artifact): raise ValueError('report binding')
 runtime_path=report_path.parent/'runtime.json'
 if sha(runtime_path)!=report['runtime_sha256'] or json.loads(runtime_path.read_text())!=report['runtime']: raise ValueError('runtime binding')
 if type(record['synthetic']) is not bool: raise ValueError('synthetic scope missing')
 if record['synthetic']:
  if report['runtime'].get('synthetic') is not True or not report['source_scope'].startswith('SYNTHETIC fixture;'): raise ValueError('fixture identity mismatch')
 else:
  if report['runtime'].get('synthetic') is not None or 'SYNTHETIC' in report['source_scope'].upper(): raise ValueError('fixture presented as real')
 if not record['synthetic']:
  runtime=report['runtime']
  if runtime.get('binary_sha256')!='a2e62037e37ff0391017bd68fec421f271f94c2dfb1df3e767ff45abeeb4c01b' or runtime.get('model_sha256')!='68bae29d62fb8c7d23e98d21fd4662753ddd636e6b62b8a70dfe059a9844f216' or not runtime.get('mapped_libraries_sha256'): raise ValueError('runtime identity missing')
 for name in ('dataset.npz','prompts.jsonl'):
  if manifest['artifacts_sha256'][name]!=sha(frozen/name) or report['input_artifacts'][name]!=sha(frozen/name): raise ValueError('frozen input changed')
 d=np.load(frozen/'dataset.npz',allow_pickle=False); a=np.load(artifact,allow_pickle=False)
 q=d['qids'].tolist(); tr=d['train_indices']; te=d['heldout_indices']; mask=d['observed_mask']; y=np.asarray(d['correctness'],dtype=np.float64)
 if mask.dtype!=bool or mask.shape!=y.shape or not np.all(mask.any(axis=1)) or sorted(np.r_[tr,te].tolist())!=list(range(len(q))) or len(set(q))!=len(q): raise ValueError('bad mask or split')
 if [q[i] for i in tr]!=manifest['train_qids'] or [q[i] for i in te]!=manifest['heldout_qids']: raise ValueError('qid mismatch')
 if not record['synthetic'] and sha(frozen/'manifest.json')!='23c6ac61b13220e9c6e5622f2ff5815f826c900c88234b0b1329e23e1fbad91b': raise ValueError('real cohort manifest not pinned')
 if not record['synthetic'] and (len(q)!=510 or len(tr)!=408 or len(te)!=102 or manifest['source_sha256']['soft_labels_embedded.npz']!='eb456857e6e667bb87aaa791ba55e765ca231e0fdee58976006d7673a12351cd'): raise ValueError('real scope mismatch')
 if not record['synthetic'] and report['source_scope']!=manifest['scope']: raise ValueError('source scope mismatch')
 if not record['synthetic']:
  perm=np.random.default_rng(42).permutation(len(q)); nval=int(len(q)*.2)
  if not np.array_equal(te,perm[:nval]) or not np.array_equal(tr,perm[nval:]): raise ValueError('split does not match declared seed')
 if report['train_count']!=len(tr) or report['heldout_count']!=len(te): raise ValueError('counts mismatch')
 w=mask[te].astype(float); n=w.sum(axis=1); z=y[te]; ability=a['action_abilities_train']
 if not record['synthetic']:
  tw=mask[tr].astype(float); action_success=np.where(tw,y[tr],0).sum(axis=0)/np.maximum(tw.sum(axis=0),1e-8); action_success=np.clip(action_success,1e-4,1-1e-4); expected=np.log(action_success/(1-action_success)); expected-=expected.mean()
  if not np.allclose(ability,expected,rtol=1e-6,atol=1e-6): raise ValueError('training-only ability mismatch')
 success=np.where(w,z,0).sum(axis=1)/n; p=np.clip(success,1e-4,1-1e-4); diff=-np.log(p/(1-p)); mean=(w*ability).sum(axis=1)/n; delta=np.where(w,ability-mean[:,None],0); discr=np.abs((delta*np.where(w,z-success[:,None],0)).sum(axis=1)/n/np.maximum((delta*delta).sum(axis=1)/n,1e-8)); truth=np.column_stack((diff,discr))
 if not np.allclose(truth,a['heldout_targets'],rtol=1e-6,atol=1e-6): raise ValueError('target mismatch')
 metrics={}
 for arm in ('bge','eg2'):
  pred=a[arm+'_prediction'];
  if pred.shape!=truth.shape or not np.isfinite(pred).all(): raise ValueError('invalid predictions')
  for k in ('feature_mean','feature_scale','weights','target_mean','target_scale'):
   if not np.isfinite(a[arm+'_'+k]).all(): raise ValueError('invalid fit')
  x=d['bge'][te] if arm=='bge' else a['eg2'][te]
  training_x=d['bge'][tr] if arm=='bge' else a['eg2'][tr]
  if not np.allclose(a[arm+'_feature_mean'],np.asarray(training_x,dtype=np.float64).mean(axis=0),rtol=1e-5,atol=1e-6): raise ValueError('feature mean not fitted to train split')
  design=(np.asarray(x,dtype=np.float64)-a[arm+'_feature_mean'])/a[arm+'_feature_scale']; design=np.column_stack((design,np.ones(len(te))))
  calculated=(design@a[arm+'_weights'])*a[arm+'_target_scale']+a[arm+'_target_mean']; calculated[:,1]=np.maximum(calculated[:,1],0)
  if not np.allclose(pred,calculated,rtol=1e-5,atol=1e-5): raise ValueError('prediction does not match fit')
  for j,metric in enumerate(('difficulty_spearman','discrimination_spearman')):
   v=rho(truth[:,j],pred[:,j]);
   if not np.isclose(v,report['metrics'][arm][metric],atol=1e-12): raise ValueError('rho mismatch')
   metrics[arm+'_'+metric]=v
 passed=all(metrics['eg2_'+k]>=metrics['bge_'+k] for k in ('difficulty_spearman','discrimination_spearman'))
 if report['passed'] is not passed or report['metric_direction']!='higher_is_better': raise ValueError('comparison mismatch')
 return report,metrics

def emit(report_path,frozen_path,synthetic=False):
 report_path=Path(report_path).resolve(); frozen_path=Path(frozen_path).resolve(); rid='irt-'+uuid.uuid4().hex
 record={'schema':'epyc.irt.paired.record.v1','report_path':str(report_path),'report_sha256':sha(report_path),'frozen_path':str(frozen_path),'manifest_sha256':sha(frozen_path/'manifest.json'),'synthetic':synthetic}
 report,metrics=rederive(record); record_path=report_path.parent/(rid+'.record.json'); record_path.write_text(json.dumps(record,sort_keys=True)+'\n')
 date=datetime.now(timezone.utc).isoformat(); rows=[]
 for key,value in metrics.items():
  arm=key.split('_',1)[0]; row={'schema':SCHEMA,'run_id':rid,'producer':'irt-paired','measurement_id':'irt_'+hashlib.sha256((rid+'\0'+key).encode()).hexdigest()[:24],'metric':key,'value':value,'unit':'spearman_rho','metric_direction':'higher_better','category':'BASELINE' if arm=='bge' else 'CANDIDATE','claim':f'{key} held-out paired IRT rho'+(' (synthetic fixture)' if synthetic else ''),'protocol_id':'','reps':1,'reps_basis':'one-paired-fit-on-fixed-heldout-cohort','results_path':str(record_path),'results_sha256':sha(record_path),'date':date,'emitted_at':date,'extra':{'synthetic':synthetic,'scope':report['source_scope'],'model_file': 'synthetic-fixture.gguf' if synthetic else 'embeddinggemma-2-BF16.gguf','comparison_passed':report['passed'],'runtime_warrant':'record-bound; runtime artifacts and grant not independently reopened'}}
  c.seal(row); rows.append(row)
 side=report_path.parent/(rid+'.belief_measurements.jsonl'); c.write_rows_atomic(side,rows); return side

def validate(row):
 errors=c.common_problems(row,schema=SCHEMA,optional_text=('protocol_id',))+c.self_hash_problems(row)
 try:
  if errors or not c.results_present(row): return errors+['missing or changed record']
  record=json.loads(Path(row['results_path']).read_text()); report,metrics=rederive(record); key=row['metric']; arm=key.split('_',1)[0]
  expected_model='synthetic-fixture.gguf' if record['synthetic'] else 'embeddinggemma-2-BF16.gguf'
  expected_claim=f'{key} held-out paired IRT rho'+(' (synthetic fixture)' if record['synthetic'] else '')
  if row['reps']!=1 or row['reps_basis']!='one-paired-fit-on-fixed-heldout-cohort' or row['value']!=metrics[key] or row['unit']!='spearman_rho' or row['metric_direction']!='higher_better' or row['protocol_id']!='' or row['category']!=('BASELINE' if arm=='bge' else 'CANDIDATE') or row['claim']!=expected_claim or row['extra']['model_file']!=expected_model or row['extra']['synthetic'] is not record['synthetic'] or row['extra']['scope']!=report['source_scope'] or row['extra']['runtime_warrant']!='record-bound; runtime artifacts and grant not independently reopened' or row['extra']['comparison_passed'] is not report['passed'] or row['measurement_id']!='irt_'+hashlib.sha256((row['run_id']+'\0'+key).encode()).hexdigest()[:24]: return ['metric mismatch']
  return []
 except (KeyError,ValueError,TypeError,OSError,IndexError): return ['invalid IRT capture']
def project(row):
 problems=validate(row)
 if problems: raise ValueError(str(problems))
 return replace(c.to_claim_tuple(row,source_kind='ufh12-irt-paired',locator=row['results_path']),applicability={'model_file':row['extra']['model_file'],'backend':'cpu'},observation={'outcome_native':'paired_comparison_passed' if row['extra']['comparison_passed'] else 'paired_comparison_failed'})
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(); p.add_argument('--report',required=True); p.add_argument('--frozen',required=True); p.add_argument('--synthetic',action='store_true'); x=p.parse_args(); print(emit(x.report,x.frozen,x.synthetic))
