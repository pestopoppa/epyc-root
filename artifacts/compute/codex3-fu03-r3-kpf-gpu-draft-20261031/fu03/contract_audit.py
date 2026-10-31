import json,pathlib,shutil,subprocess,sys
D=pathlib.Path('/mnt/raid0/llm/tmp/codex3-next-backlog-20261031-0255/r3'); source=(D/'launch.sh').read_text(); engine=pathlib.Path('/mnt/raid0/llm/tmp/codex3-kpf-item4-control-20261030/engine/filler_run13.sh').read_text();normal=next(x for x in source.splitlines() if '--complete-cmd' in x)
assert normal.count('--complete-cmd')==1 and '--complete-cmd "/usr/bin/python3 -B $D/check_complete.py full"' in normal and '--cmd "taskset -c \\${FILLER_CPUS} /bin/bash $D/launch.sh --job"' in normal
assert '--complete-cmd) COMPLETE_CMD=$2' in engine and 'is_complete() { [ -n "$COMPLETE_CMD" ] || return 1;' in engine
out={}; runner=[sys.executable,str(D/'check_complete.py')]
def call(tag): return subprocess.run(runner+[tag],capture_output=True,text=True).returncode
assert call('normal-r2')==0
for kind in ['missing','partial','arm_count','argv','model_sha','log_bytes']:
 tag='audit-'+kind; target=D/tag
 if target.exists(): raise RuntimeError('fixture exists')
 if kind=='missing': target.mkdir()
 else:
  shutil.copytree(D/'normal-r2',target); p=target/'RESULT.json';r=json.loads(p.read_text())
  for a in r['arms']: a['log']=str(target/pathlib.Path(a['log']).name)
  if kind=='partial':r['partial']=True
  if kind=='arm_count':r['arms'].pop()
  if kind=='argv':r['arms'][2]['argv'][-1]='off'
  if kind=='model_sha':r['models_verified'][0]['sha256']='0'*64
  if kind=='log_bytes':(target/'baseline-1.log').write_bytes(b'tampered')
  p.write_text(json.dumps(r))
 rc=call(tag);assert rc!=0,(kind,rc);out[kind]=rc
print(json.dumps({'structural_assembly':'PASS','engine_parser_and_predicate':'PASS','native_normal_checker':'PASS','negative_refusals':out},indent=2))
