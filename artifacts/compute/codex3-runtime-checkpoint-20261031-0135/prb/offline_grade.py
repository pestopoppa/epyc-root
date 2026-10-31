#!/usr/bin/env python3
"""Prospective PRB full-cohort auditor; refuses incomplete or invalid cells."""
import ast,hashlib,json,random,statistics,sys,os,time
from datetime import datetime,timezone
import eval_metrics
import tale_budget_capture
from pathlib import Path
D=Path(__file__).resolve().parent
sample=json.loads((D/'SAMPLE.json').read_text());root=Path(sys.argv[1]);out=Path(sys.argv[2]);rows=[];counts={};caps={};bad=[];starts=[];ends=[];mtp_segments={}
for idx,item in enumerate(sample['ids']):
 for arm in ('estimate','baseline','static','tale'):
  path=root/f'{idx:04d}'/(arm+'.json');key=item['suite']+'/'+arm;counts[key]=counts.get(key,0)+1
  if not path.is_file():bad.append((idx,arm,'missing'));continue
  rec=json.loads(path.read_text());r=rec.get('result') or {}
  claim=rec.get('record_sha256');binding={k:v for k,v in rec.items() if k!='record_sha256'}
  if hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()!=claim:bad.append((idx,arm,'record_digest_mismatch'));continue
  warrant=rec.get('write_warrant') or {}; ep=Path(warrant.get('envelope_path','/nonexistent'))
  try:
   eb=ep.read_bytes(); envelope=json.loads(eb)
   valid_warrant=(hashlib.sha256(eb).hexdigest()==warrant.get('envelope_sha256') and envelope.get('source_catalog_sha256')==os.environ['PRB_SOURCE_SHA'] and envelope.get('model_sha256')=='a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348' and envelope.get('gpu_resident') is True and bool(envelope.get('grant')) and rec.get('writer_pid') and envelope.get('sample_sha256')==hashlib.sha256((D/'SAMPLE.json').read_bytes()).hexdigest() and envelope.get('launcher_sha256')==hashlib.sha256((D/'launch.sh').read_bytes()).hexdigest() and envelope.get('predeclared_sha256')==hashlib.sha256((D/'PREDECLARED.md').read_bytes()).hexdigest() and envelope.get('server_pid') and envelope.get('server_birth_ticks') and envelope.get('server_uid')==os.getuid() and envelope['observed_unix']<=rec['started']<=rec['finished']<=envelope['deadline_epoch'] and (rec.get('http') or {}).get('status')==200)
  except (OSError,ValueError,KeyError):valid_warrant=False
  if not valid_warrant:bad.append((idx,arm,'missing_native_warrant'));continue
  usage=(rec.get('http',{}).get('response',{}).get('usage') or {}).get('completion_tokens')
  if rec.get('status')!='complete' or rec.get('finish_reason') not in ('stop','length') or rec.get('cap_reached') != (rec.get('finish_reason')=='length') or not isinstance(usage,int) or isinstance(usage,bool) or usage<0:bad.append((idx,arm,'unknown_or_invalid_native_cost'));continue
  if rec['cap_reached']:caps[key]=caps.get(key,0)+1
  starts.append(rec['started']);ends.append(rec['finished'])
  segment=mtp_segments.setdefault(warrant['envelope_sha256'],{'envelope':str(ep),'mtp_log_evidence':bool(envelope.get('mtp_log_evidence')),'mtp_unavailable_evidence':bool(envelope.get('mtp_unavailable_evidence')),'native_draft_tokens':0,'responses_with_counter':0})
  timing=(rec.get('http',{}).get('response',{}).get('timings') or {})
  if isinstance(timing.get('draft_n'),int):segment['native_draft_tokens']+=timing['draft_n'];segment['responses_with_counter']+=1
  if arm=='estimate':continue
  if arm=='tale':
   er=json.loads((root/f'{idx:04d}'/'estimate.json').read_text()).get('result') or {}
   if r.get('estimator_tokens')!=er.get('tokens') or r.get('total_tokens_incl_estimator')!=r.get('total_tokens',0)+er.get('tokens',-1) or r.get('tale_budget')!=er.get('budget'):bad.append((idx,arm,'estimator_binding_mismatch'));continue
  if item['suite']=='livecodebench':
   witness=rec.get('scorer_witness') or {}
   if not witness.get('pid') or not witness.get('birth_ticks') or witness.get('returncode')!=0 or not witness.get('cgroup_drained'):bad.append((idx,arm,'scorer_warrant_missing'));continue
  if r.get('question_id')!=item['id'] or r.get('suite')!=item['suite'] or r.get('condition')!=arm or not isinstance(r.get('correct'),bool):bad.append((idx,arm,'identity_or_oracle_unknown'));continue
  rows.append(r)
if bad or len(rows)!=4800 or not (root/'COLLECTION_COMPLETE.json').is_file():
 out.write_text(json.dumps({'status':'INCOMPLETE','decision':None,'planned_questions':1600,'planned_arm_rows':4800,'valid_arm_rows':len(rows),'invalid_count':len(bad),'invalid_examples':bad[:40],'counts':counts,'cap_counts':caps},indent=2)+'\n');sys.exit(2)
source=(D/'prb_reference.py').read_text();tree=ast.parse(source);wanted={'boot_ci','analyse','decide'};nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
if {n.name for n in nodes}!=wanted:raise RuntimeError('reference analysis functions missing')
ns={'statistics':statistics,'random':random};exec(compile(ast.Module(body=nodes,type_ignores=[]),'pinned-reference','exec'),ns)
summary=ns['analyse'](rows)
if set(summary)!={'math','olympiadbench','mmlu_pro','livecodebench'}:raise RuntimeError('wrong suite set')
for suite in summary.values():
 for name in ('baseline','static','tale'):
  if suite['arms'][name]['n']!=400 or suite['arms'][name]['n_scored']!=400:raise RuntimeError('incomplete arm')
verdict=ns['decide'](summary)
for suite in summary:
 for name in ('baseline','static','tale'):
  subset=[r for r in rows if r['suite']==suite and r['condition']==name]
  summary[suite]['arms'][name]['oaa_alpha_0_5']=eval_metrics.compute_batch_oaa(subset,alpha=.5)
results=root/'canonical-results.jsonl'; tmp=results.with_suffix('.tmp')
with tmp.open('w') as f:
 for row in rows:f.write(json.dumps(row,sort_keys=True)+'\n')
 f.flush();os.fsync(f.fileno())
os.replace(tmp,results)
meta=root/'canonical-results.meta.json'
meta_record={'started_at':datetime.fromtimestamp(min(starts),timezone.utc).isoformat(),'finished_at':datetime.fromtimestamp(max(ends),timezone.utc).isoformat(),'budget_unit':'tokens','temperature':.1,'seed':42,'max_tokens':8192,'estimator_max_tokens':32,'chat_template_kwargs':{'enable_thinking':False},'served_models_seen':[envelope['model_path']],'serving':{'base_url':'http://127.0.0.1:18979','model_id':envelope['model_path'],'model_id_source':'props','gguf_path':envelope['model_path'],'gguf_path_source':'props','gguf':{'size_bytes':envelope['model_attestation']['identity']['st_size'],'sha256':envelope['model_sha256']},'props':{'model_path':envelope['model_path'],'build_info':envelope['props'].get('build_info')}}}
meta.write_text(json.dumps(meta_record,sort_keys=True,indent=2)+'\n')
side=tale_budget_capture.write_belief_measurements(results,run_id='codex3-prbt4-r1-20261031',producer='codex3-prbt4-native',kernel={'binary_path':envelope['binary_path'],'binary_sha256':envelope['binary_sha256']},meta_path=meta)
verdict['write_sidecar']=str(side)
out.write_text(json.dumps({'sample_sha256':hashlib.sha256((D/'SAMPLE.json').read_bytes()).hexdigest(),'reference_sha256':hashlib.sha256(source.encode()).hexdigest(),'cohort_complete':True,'cap_counts':caps,'effective_mtp_evidence':mtp_segments,'summary':summary,'decision':verdict},indent=2)+'\n')
