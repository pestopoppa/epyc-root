#!/usr/bin/env python3
"""Publish this worker's GPU packet only after its exact R7 proof exists."""
import datetime,fcntl,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240/gpu-leg-v3');F=Path('/mnt/raid0/llm/tmp/compute-flags');R=F/'ready';ID='codex3-kpf181-27b-gpu-r3-20261031'
LAUNCH='b717421f7205e92406671aefb887ee7f2ab37b5c6c846322c4c9d60171bc0726';SOURCE='96ca5e50911a1dc0838ecef538986904e0ff077d741f40e0b5100f7083855dee'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def emit(name,obj):
 p=D/('PUBLISH-'+name+'.json');t=p.with_suffix('.tmp');t.write_text(json.dumps(obj,indent=2)+'\n');os.replace(t,p)
 if name in ('DONE','HALT','EXPIRED'):(D/('PUBLISH-'+name+'.flag')).touch()
def publish():
 q=D/'QUALIFIER-QUALIFIED.json'; proof=json.loads(q.read_text())
 if proof['launcher_sha256']!=LAUNCH or proof['source_sha256']!=SOURCE or sha(D/'launch.sh')!=LAUNCH or sha(D/'SOURCES.sha256')!=SOURCE:raise RuntimeError('launcher/source mismatch')
 if time.time()-q.stat().st_mtime>=24*3600:raise RuntimeError('qualification stale')
 n=proof['proof']['normal'];s=proof['proof']['stop'];sup=n['supervisor'];st=s['supervisor'];partial=json.loads(Path(s['partial']).read_text())
 if n['rc']!=0 or s['rc']!=75 or not partial.get('partial') or not sup['children_drained'] or not st['children_drained'] or sup.get('failure') or st.get('failure'):raise RuntimeError('normal/stop proof incomplete')
 consumer=Path(n['consumer_result']); consumed=json.loads(consumer.read_text())
 if consumed.get('active_fork_control',{}).get('status')!='observed' or not consumed.get('comparator',{}).get('target_parameters_match'):raise RuntimeError('consumer result missing active fork/comparator')
 rec=[json.loads(Path(p).read_text()) for p in n['records']]
 if len(rec)!=4:raise RuntimeError('record count mismatch')
 for r in rec:
  residency=r.get('residency',{});v=residency.get('vram') or {}
  if not residency.get('hip_mapped') or not (residency.get('linkage') or {}).get('pass') or v.get('own_vram_nonzero_samples',0)<2 or v.get('kfd_process_count_max',0)<1 or v.get('own_vram_peak_gib',999)>48 or v.get('abort') or not (residency.get('stop') or {}).get('verified_dead'):raise RuntimeError('resident GPU proof mismatch')
 children=[c for r in rec if r.get('arm')=='A_ckpt' for c in r.get('cells',[]) if c.get('role')=='sibling']
 if len(children)!=1:raise RuntimeError('no unique fork child')
 c=children[0];active=c.get('active_slot_evidence') or {}
 if (not isinstance(c.get('n_fork_tokens'),int) or c['n_fork_tokens']<=0 or active.get('status')!='observed' or active.get('n_fork_tokens')!=c['n_fork_tokens'] or active.get('matched_active_samples',0)<1 or not isinstance(active.get('final_task_id'),int) or active.get('final_slot_id')!=c.get('slot') or not Path(active.get('path','/nonexistent')).is_file() or sha(Path(active['path']))!=active.get('sha256')):raise RuntimeError('active matched fork proof absent')
 cmp=[json.loads(Path(p).read_text()) for p in n['comparator_records']]
 if len(cmp)!=2 or {r.get('arm') for r in cmp}!={'champion','fork_off'}:raise RuntimeError('comparator proof absent')
 if {r.get('binary_sha256') for r in cmp}!={'8a3710ad9f0bea535dd9cbd84ff49d8b8af9e2783979077fb109db13a5620b7b','2be7a16ed6d3712d82a36c668417b4dcec8d9cadd13a682e069cb4d57b9d0635'}:raise RuntimeError('comparator binary mismatch')
 def normalized(argv):
  out=[];i=1
  while i<len(argv):
   if argv[i] in ('--slot-save-path','--slot-fork-min-tokens','--port'):i+=2;continue
   out.append(argv[i]);i+=1
  return out
 if normalized(cmp[0].get('argv') or [])!=normalized(cmp[1].get('argv') or []) or cmp[0].get('prompt_set_sha256')!=cmp[1].get('prompt_set_sha256'):raise RuntimeError('comparator target configuration mismatch')
 for r in cmp:
  v=r.get('residency',{});w=v.get('vram') or {}
  if not v.get('hip_mapped') or not (v.get('linkage') or {}).get('pass') or w.get('own_vram_nonzero_samples',0)<2 or w.get('kfd_process_count_max',0)<1 or w.get('own_vram_peak_gib',999)>48 or w.get('abort') or not (v.get('stop') or {}).get('verified_dead'):raise RuntimeError('comparator residency incomplete')
 check=subprocess.run(['sha256sum','--strict','--quiet','-c','SOURCES.sha256'],cwd=D,capture_output=True,text=True)
 if check.returncode:raise RuntimeError('source inputs changed')
 valid=subprocess.run(['python3',str(F/'validate_fillers.py'),'--file',str(D/'READY-ROW.md'),'--row',ID],capture_output=True,text=True)
 if valid.returncode:raise RuntimeError('row validator refusal: '+valid.stdout+valid.stderr)
 for loc in (R,R/'armed',R/'refused'):
  if (loc/(ID+'.json')).exists():raise RuntimeError('packet already present; no duplicate')
 local_log=D/'ws58-launcher.out';ready_log=R/(ID+'.launcher.out');local_log.touch(exist_ok=True)
 try:os.link(local_log,ready_log)
 except FileExistsError:
  if os.stat(local_log).st_ino!=os.stat(ready_log).st_ino:raise RuntimeError('launcher log collision')
 pdecl=D/'PREDECLARED.json';job=D/'job.sh'
 m={'status':'READY','id':ID,'owner':'codex3','priority_rank':2,'regions':'mi210_0,184-191','class':'diagnostic','booking_class':'block-correctness','min_window_s':1800,'window_s':14400,'gib':64,'launcher':{'path':str(D/'launch.sh'),'sha256':LAUNCH},'job':{'path':str(job),'sha256':sha(job)},'result_path':str(D/'full/RESULT.json'),'launcher_log':str(local_log),'scratch_root':str(D),'est_output_GiB':2,'keep':['KEEP','*.sh','*.py','*.json','*.sha256','*.md','*.log','full/**/*.json','full/**/*.jsonl','full/**/*.log','full/**/*.txt','control-normal*/**/*.json','control-normal*/**/*.jsonl','control-stop*/**/*.json','scripts/benchmark/kpf18/*.py'],'decision_rule':'KPF-18.1 GPU 27B Q8/DFlash2 A/B/C/D, fixed 16-length C on/off and same-binary fork-off. D includes DFlash2 and no-drafter with held-out position; observed errors and missing native fields count as unknown. Original S1 outcomes remain distinct. Exact e332 GPU versus fork-off comparison uses the same 27B target, DFlash2 argv and frozen prompts; CPU MTP is separate. No cross-model pooling or full-gate closure.','min_effect':'n/a (correctness diagnostic; full gate remains open)','enrollment':'n/a: diagnostic','hold':None,'source_manifest':{'path':str(D/'SOURCES.sha256'),'sha256':SOURCE},'predeclaration':{'path':str(pdecl),'sha256':sha(pdecl)},'full_target_tested':False,'full_model':'/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf','draft_model':'/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf','feasibility':'Conservative planning estimate: C <=802816 prefill and 24576 decode tokens; reserve 1000000 prefill and 8192 decode for A/B/D, e332 and controls. Historical 27B rates 487 prompt tok/s and 18.7 decode tok/s give ~5454s; 2x plus 360s loads <=14400s. Different run/placement; estimate not a guarantee. STOP/deadline rc75 preserves partial.','smoke':{'ran_at':datetime.datetime.fromtimestamp(q.stat().st_mtime,datetime.timezone.utc).isoformat(),'regions':'mi210_0 exclusive, CPUs 184-185','model':'Qwen3.5-0.8B-Q8_0 public control only','first_request_ok':True,'result_writer_ok':True,'exit_ok':True,'wall_s':sup['elapsed_s'],'log':n['log'],'launcher_sha256':LAUNCH,'residency':'nonzero KFD VRAM during model request, HIP mapped and linkage verified'},'stop_smoke':{'rc':75,'partial':s['partial'],'children_drained':True,'wall_s':st['elapsed_s'],'log':s['log']},'log_consumer':str(D/'finish.py'),'log_consumer_sha256':sha(D/'finish.py')}
 proposal=D/'READY-PROPOSAL.json';proposal.write_text(json.dumps(m,indent=2)+'\n')
 rowtmp=R/('.'+ID+'.row.tmp');rowtmp.write_text((D/'READY-ROW.md').read_text());os.replace(rowtmp,R/(ID+'.row.md'))
 tmp=R/('.'+ID+'.json.tmp');tmp.write_text(json.dumps(m,indent=2)+'\n');os.replace(tmp,R/(ID+'.json'))
 emit('DONE',{'id':ID,'manifest':str(R/(ID+'.json')),'launcher_sha256':LAUNCH,'source_sha256':SOURCE,'proof':str(q),'published':datetime.datetime.now(datetime.timezone.utc).isoformat()})
start=time.time();birth=int(Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split()[19]);emit('RUNNING',{'pid':os.getpid(),'birth':birth,'started':start,'max_wait_s':7500})
try:
 while time.time()<start+7500:
  if (D/'QUALIFIER-HALT.flag').exists() or (D/'QUALIFIER-EXPIRED.flag').exists():raise RuntimeError('qualifier halted or expired')
  if (D/'QUALIFIER-QUALIFIED.flag').exists():publish();break
  time.sleep(5)
 else:emit('EXPIRED',{'reason':'no qualification within bounded wait'})
except Exception as exc:
 emit('HALT',{'error':repr(exc)});raise
