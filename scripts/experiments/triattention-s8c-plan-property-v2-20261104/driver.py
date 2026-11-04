#!/usr/bin/env python3
import hashlib,json,os,pathlib,signal,subprocess,sys,time
R=pathlib.Path('/mnt/raid0/llm/tmp/triattention-s8c-plan-property-v2-20261104');out=R/'results.jsonl';complete=R/'complete';stopped=False
def stop(*_):
 global stopped;stopped=True
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
rows=[json.loads(x) for x in out.read_text().splitlines()] if out.exists() else []
groups=[10]+list(range(0,10))+list(range(11,65))
for i,r in enumerate(rows):
 if i>=len(groups) or r.get('unit') != f'size-{groups[i]}' or r.get('n')!=groups[i] or r.get('status')!='pass':raise SystemExit('invalid previous checkpoint')
for n in groups[len(rows):]:
 if stopped or pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or int(time.time())>=int(os.environ['FILLER_DEADLINE']):sys.exit(75)
 p=subprocess.run([str(R/'output/property'),str(n)],text=True,capture_output=True,timeout=30)
 if p.returncode not in (0,1):raise SystemExit('property harness crashed: '+p.stderr[-2000:])
 d=json.loads(p.stdout);assert d['n']==n and (d['status']=='pass')==(p.returncode==0)
 d.update(unit=f'size-{n}',candidate_sha256=hashlib.sha256((R/'include/llama-kv-compress-plan.h').read_bytes()).hexdigest(),binary_sha256=hashlib.sha256((R/'output/property').read_bytes()).hexdigest(),scope='synthetic header planner; no real eviction, model, server, quality or speed claim')
 with out.open('a') as f:f.write(json.dumps(d,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
 if d['status']=='fail':complete.write_text('counterexample\n');sys.exit(0)
complete.write_text('bounded sweep complete\n')
