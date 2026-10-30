from pathlib import Path
import json,hashlib,os,datetime
D=Path('/mnt/raid0/llm/tmp/codex3-cs26-lid1-20261030');R=Path('/mnt/raid0/llm/tmp/compute-flags/ready');V=D/'v1-qualified'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
models={'tiny':16,'base':16,'large-v3-turbo':64,'silero':8,'firered':40}
for model,gib in models.items():
 ident=f'codex3-cs26-lid1-{model}-20261030';m=json.loads((V/f'{ident}.json').read_text());launcher=D/f'launch-{model}.sh';job=D/('crisp_job.py' if model in ('silero','firered') else 'job.py');catalog=D/('CRISP-SOURCE-SHA256SUMS' if model in ('silero','firered') else 'SOURCE-SHA256SUMS')
 log=R/f'{ident}.smoke.log';stoplog=R/f'{ident}.stop-smoke.log'
 for dst,src in ((log,D/'v2-smoke.log'),(stoplog,D/'v2-stop.log')):
  assert not dst.exists();os.link(src,dst)
 keep=set(m['keep']);keep.update(['v2-smoke.log','v2-stop.log','v2-rollover.log','v2-smoke-normal/results/*/*.json','v2-smoke-normal/results/*/*.jsonl','v2-smoke-stop-*/results/*/*.json','v2-smoke-stop-*/results/*/*.jsonl','results/*/window-*/*.jsonl','results/*/window-*/*.active','results/*/*.active','v1-qualified/*.json','v1-qualified/*.md','v1-qualified/*.py','v1-qualified/*SHA256SUMS']);keep=sorted(keep);raw=['results/*/worker-*.jsonl','results/*/window-*/*.jsonl']
 m.update(gib=gib,launcher={'path':str(launcher),'sha256':sha(launcher)},job={'path':str(job),'sha256':sha(job)},source_manifest={'path':str(catalog),'sha256':sha(catalog)},keep=keep,raw_globs=raw)
 m['execution_profile']='Up to 24 distinct physical granted cores, one worker/thread each; 620s admission reserve; 600s per-case stop; descriptive co-tenancy; unknown not redrawn.'
 m['smoke'].update(ran_at=datetime.datetime.fromtimestamp((D/'v2-smoke.log').stat().st_mtime,datetime.timezone.utc).isoformat(),regions='R11 unlocked 124,125; one core per worker',log=str(log),log_sha256=sha(log),launcher_sha256=sha(launcher),peak_sampled_tree_rss_bytes=3867656192,wall_s=64.15177,first_request_ok=True,result_writer_ok=True,exit_ok=True)
 m['completion']='All 9150 case outcomes; interrupted or timeout exposure is unknown and never redrawn; cutoff rc75 and resume only unexposed cases.'
 notes=f'requested_window_s=36000; est_output_GiB=1; scratch_root={D}; launcher_path={launcher}; launcher_sha256={sha(launcher)}; job_path={job}; job_sha256={sha(job)}; source_manifest={catalog}; source_manifest_sha256={sha(catalog)}; result_path={D}/results/{model}; launcher_log={D}/ws58-{model}.out; log_consumer={D}/log_consumer.py; enrollment=native Speech family prospective; keep_globs={",".join(keep)}; raw_globs={",".join(raw)}; retention_v2=1'
 row=[ident,'codex3',str(launcher),'any-cpu-quarter','900',str(gib),str(D/f'STOP-{model}'),'BACKLOG','block-correctness','36000','900','n','y','/workspace/handoffs/active/conversation-stack.md',f'CS-26.LID1 full FLEURS 9150 crop native {model} CPU LID','per PLAN.md four-language masked comparison','cpu',notes]
 (R/f'{ident}.row.md').write_text('| '+' | '.join(row)+' |\n');tmp=R/f'.{ident}.tmp';tmp.write_text(json.dumps(m,indent=2)+'\n');os.replace(tmp,R/f'{ident}.json');print(ident,gib)
