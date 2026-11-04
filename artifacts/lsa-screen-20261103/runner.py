#!/usr/bin/env python3
"""One bounded screen item per invocation; adapter reads request JSON, writes response JSON.
No inference without a reviewed runtime binding. Missing arms become invalid records.
"""
import argparse,datetime,gzip,hashlib,json,os,subprocess,sys
import monitor
from pathlib import Path
P=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,default=P/'manifest.json');p.add_argument('--binding',type=Path,required=True);p.add_argument('--id',required=True);p.add_argument('--length',type=int,required=True);p.add_argument('--arm',required=True,choices=['dense','all_keys','pca','distilled','oracle_topk','window']);p.add_argument('--phase',required=True,choices=['quality','timing']);p.add_argument('--repeat',type=int,default=1);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if not 1<=a.repeat<=7 or (a.phase=='quality' and a.repeat!=1):p.error('quality runs once; timing repetitions 1..7')
m=json.loads(a.manifest.read_text());b=json.loads(a.binding.read_text()); row=next((x for x in m['rows'] if x['id']==a.id and x['nominal']==a.length),None)
if row is None:p.error('unknown item/cell')
raw=gzip.decompress((P/row['token_ids']).read_bytes())
if hashlib.sha256(raw).hexdigest()!=row['token_ids_sha256']:raise SystemExit('token IDs digest mismatch')
ids=json.loads(raw);assert len(ids)==row['prompt_n'] and len(ids)+row['max_output_tokens']<=262144
receipt=None
try:
 receipt=json.loads((Path(b['server_receipt_dir'])/(a.arm+'.json')).read_text())
except (KeyError,OSError,ValueError,TypeError):pass
record=dict(schema='lsa-screen-raw-v1',item=row,arm=a.arm,phase=a.phase,repeat=a.repeat,time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),binding=b,status='invalid',reason=None,output=None,score=None,ttft_ms=None,tpot_ms=None,peak_memory_bytes=None,index_time_ms=None,attention_mass_recall=None,top_key_recall=None,selected_budget=None)
def proof_ok(b,m):
 try:
  proof_path=Path(b['candidate_tokenizer_proof']);proof=json.loads(proof_path.read_text());tokenizer=Path(proof['candidate_tokenizer']);root=os.path.realpath(b['candidate_build_root'])
  return (hashlib.sha256(proof_path.read_bytes()).hexdigest()==b['candidate_tokenizer_proof_sha256'] and proof['passed'] is True and proof['model_sha256']==m['model_sha256'] and proof['tokenizer_sha256']==m['tokenizer_sha256'] and os.path.commonpath((os.path.realpath(tokenizer),root))==root and hashlib.sha256(tokenizer.read_bytes()).hexdigest()==proof['candidate_tokenizer_sha256'])
 except (KeyError,ValueError,OSError,TypeError):return False
def build_ok(b):
 try:
  p=Path(b['candidate_build_manifest']);v=json.loads(p.read_text())
  return hashlib.sha256(p.read_bytes()).hexdigest()==b['candidate_build_manifest_sha256'] and all(v[k]==b[k] for k in ('source_commit','candidate_binary_sha256','candidate_patch_sha256'))
 except (KeyError,ValueError,OSError,TypeError):return False
# Adapter must be explicitly bound by owning runtime; absent controls are never substituted.
if not b.get('reviewed') or b.get('model_sha256')!=m['model_sha256'] or not b.get('effective_config') or not b.get('source_commit'):
 record['reason']='runtime binding incomplete or model mismatch'
elif b.get('source_commit')!='c72ec82f5417bb2937310326120f149b665e8400':
 record['reason']='source is not the required C5 candidate'
elif not b.get('native_evidence_ready') or not b.get('declaration_reviewed') or not proof_ok(b,m):
 record['reason']='evidence, declaration review or candidate tokenizer parity pending'
elif not receipt or receipt.get('arm')!=a.arm or receipt.get('owner_nonce')!=b.get('owner_nonce') or not b.get('owner_nonce') or receipt.get('candidate_binary_sha256')!=b.get('candidate_binary_sha256') or receipt.get('server_url')!=b['effective_config'].get('server_url') or not receipt.get('pid') or not receipt.get('start_ticks'):
 record['reason']='owned arm-specific server launch receipt missing or mismatched'
elif not b.get('candidate_patch_path') or not b.get('candidate_patch_sha256') or not Path(b['candidate_patch_path']).is_file() or hashlib.sha256(Path(b['candidate_patch_path']).read_bytes()).hexdigest()!=b['candidate_patch_sha256']:
 record['reason']='candidate patch identity missing or mismatched'
elif not build_ok(b):record['reason']='candidate build manifest missing or inconsistent'
elif not b.get('candidate_binary') or not b.get('candidate_binary_sha256') or not b.get('candidate_build_root') or not b.get('device_topology') or not b.get('kv_dtype') or not b.get('context_config') or not b.get('batch_config'):
 record['reason']='candidate binary, topology, precision or configuration missing'
elif os.path.commonpath((os.path.realpath(b['candidate_binary']),os.path.realpath(b['candidate_build_root'])))!=os.path.realpath(b['candidate_build_root']):
 record['reason']='candidate binary outside candidate build root'
elif os.path.realpath(b['candidate_binary']).startswith(('/mnt/raid0/llm/kernels/production/', '/mnt/raid0/llm/llama.cpp/')):
 record['reason']='production or frozen-tree binary forbidden'
elif not os.path.isfile(b['candidate_binary']) or hashlib.sha256(Path(b['candidate_binary']).read_bytes()).hexdigest()!=b['candidate_binary_sha256']:
 record['reason']='candidate binary absent or digest mismatch'
elif b['effective_config'].get('speculation') is not False or str(b['kv_dtype']).lower() not in ('bf16','bfloat16'):
 record['reason']='initial paired screen requires speculation off and BF16 KV'
elif a.arm not in b.get('supported_arms',[]):record['reason']='arm unsupported by bound runtime'
elif a.arm in ('pca','distilled') and not b.get('map_sha256',{}).get(a.arm):record['reason']='projection map hash missing'
elif not b.get('adapter_argv'):record['reason']='adapter missing'
else:
 request={'token_ids':ids,'max_tokens':row['max_output_tokens'],'arm':a.arm,'phase':a.phase,'seed':b.get('seed',0),'effective_config':b['effective_config']}
 try:
  result,rc,witness=monitor.run(b['adapter_argv'],json.dumps(request),b.get('timeout_s',3600),receipt['pid'],b['candidate_binary'],receipt['start_ticks'],b['device_topology'],b['candidate_build_root'],a.arm,b.get('map_sha256',{}).get(a.arm))
  record['runtime_witness']=witness;record['launch_receipt']=receipt
  if witness['errors']:
   record['status']='invalid';record['reason']='; '.join(witness['errors']);raise ValueError(record['reason'])
  if result.get('timeout'):raise subprocess.TimeoutExpired(b['adapter_argv'],b.get('timeout_s',3600))
  if rc:raise RuntimeError('adapter exited '+str(rc)+': '+result.get('err','')[-2000:])
  response=json.loads(result['out'])
  if not isinstance(response.get('output'),str):raise ValueError('adapter returned no output')
  record.update({k:response.get(k) for k in ('output','ttft_ms','tpot_ms','peak_memory_bytes','index_time_ms','attention_mass_recall','top_key_recall','selected_budget')})
  answer=response['output'].strip();record['score']=answer==row['expected'];record['status']='abstention' if not answer else ('pass' if record['score'] else 'failure');record['adapter_raw']=response
  if response.get('status') in ('invalid','timeout','failure','abstention'):
   record['status']=response['status'];record['score']=None;record['reason']=response.get('reason','runtime reported '+response['status'])
 except subprocess.TimeoutExpired:record.update(status='timeout',reason='adapter timeout')
 except Exception as exc:
  if record['status']!='invalid' or not record['reason']:record.update(status='failure',reason=f'{type(exc).__name__}: {exc}')
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('x') as f:json.dump(record,f,sort_keys=True);f.write('\n')
from native_evidence import emit
emit(record,a.manifest,a.output)
print(record['status'])
