import hashlib,json,os
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/codex3-cs26-lid1-20261030'); R=Path('/mnt/raid0/llm/tmp/compute-flags/ready')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(D/'CRISP-SOURCE-SHA256SUMS')=='f27472bdcdc4a06cadba978476c3b9a5e9964772fb64fdbc1536d27a06a7134f'
for model in ('silero','firered'):
 case=[json.loads(x) for x in (D/f'crisp-{model}-smoke.jsonl').read_text().splitlines()]; assert len(case)==2 and case[1]['status']=='ok'
 ident=f'codex3-cs26-lid1-{model}-20261030'; log=R/f'{ident}.smoke.log'
 if log.exists(): log.unlink()
 os.link(D/'crisp-r11-final-normal.log',log)
 assert log.stat().st_ino==(D/'crisp-r11-final-normal.log').stat().st_ino
 stoplog=R/f'{ident}.stop-smoke.log'
 if stoplog.exists(): stoplog.unlink()
 os.link(D/'crisp-r11-final-stop.log',stoplog)
 (D/'results'/model).mkdir(parents=True,exist_ok=True)
 launch=D/f'launch-{model}.sh'; job=D/'crisp_job.py'; source=D/'CRISP-SOURCE-SHA256SUMS'
 keep=['KEEP','PLAN.md','CRISP-SOURCE-SHA256SUMS','crops.jsonl','cases-*.jsonl','*.py','*.cpp','*.so','*.sh','smoke-*.jsonl','smoke-all.log','crisp-r11-final-normal.log','crisp-r11-final-stop.log','crisp-r11-final-normal/results/*/*.json','crisp-r11-final-normal/results/*/*.jsonl','crisp-r11-final-stop/results/*/*.json','crisp-r11-final-stop/results/*/*.jsonl','job-normal.log','job-stop.log','smoke-job-normal/results/*/*.json','smoke-job-normal/results/*/*.jsonl','smoke-job-stop/results/*/*.json','smoke-job-stop/results/*/*.jsonl','results/*/*.json','results/*/*.jsonl','results/*/*.log','ws58-*.out']
 raw=['results/*/*.jsonl']
 m={'id':ident,'owner':'codex3','priority_rank':100,'regions':'any-cpu-quarter','min_window_s':900,'window_s':36000,'gib':8,'booking_class':'block-correctness','class':'cpu','decision_rule':'CS-26.LID1 four-language masked paired comparison; baseline collection remains open until all 9150 outcomes','enrollment':'native Speech family prospective source enrollment','launcher':{'path':str(launch),'sha256':sha(launch)},'job':{'path':str(job),'sha256':sha(job)},'source_manifest':{'path':str(source),'sha256':sha(source)},'scratch_root':str(D),'keep':keep,'raw_globs':raw,'result_path':str(D/'results'/model),'est_output_GiB':1,'smoke':{'regions':'R11 unlocked 124,125; one pinned core per worker','first_request_ok':True,'result_writer_ok':True,'exit_ok':True,'ran_at':__import__('datetime').datetime.fromtimestamp((D/'crisp-r11-final-normal.log').stat().st_mtime,__import__('datetime').timezone.utc).isoformat(),'model':model,'log':str(log),'log_sha256':sha(log),'peak_sampled_tree_rss_bytes':json.loads((D/'crisp-r11-final-normal.log').read_text().splitlines()[-1])['sampled_peak_tree_rss_bytes'],'wall_s':json.loads((D/'crisp-r11-final-normal.log').read_text().splitlines()[-1])['elapsed_s'],'launcher_sha256':sha(launch)},'hold':None,'log_consumer':str(D/'log_consumer.py'),'completion':'9150 results; interrupted exposure is unknown and never redrawn; cutoff rc75, multi-window resume only unexposed cases','status':'READY'}
 notes=f'requested_window_s=36000; est_output_GiB=1; scratch_root={D}; launcher_path={launch}; launcher_sha256={sha(launch)}; job_path={job}; job_sha256={sha(job)}; source_manifest={source}; source_manifest_sha256={sha(source)}; result_path={D}/results/{model}; launcher_log={D}/ws58-{model}.out; log_consumer={D}/log_consumer.py; enrollment=native Speech family prospective; keep_globs={",".join(keep)}; raw_globs={",".join(raw)}; retention_v2=1'
 row=[ident,'codex3',str(launch),'any-cpu-quarter','900','8',str(D/f'STOP-{model}'),'BACKLOG','block-correctness','36000','900','n','y','/workspace/handoffs/active/conversation-stack.md',f'CS-26.LID1 full FLEURS 9150 crop native Crisp {model} CPU arm','per PLAN.md four-language masked comparison','cpu',notes]
 assert len(row)==18
 (R/f'{ident}.json').write_text(json.dumps(m,indent=2)+'\n')
 (R/f'{ident}.row.md').write_text('| '+' | '.join(row)+' |\n')
 print(ident)
