#!/usr/bin/python3
"""R13 completion predicate: verify all six native units and original analysis."""
import hashlib, importlib.util, json, pathlib, sys
D=pathlib.Path('/mnt/raid0/llm/tmp/codex3-wholehost-20261031-0310'); o=D/'full'
def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
try:
 assert (o/'SUCCESS').read_text().strip()=='complete'
 assert read(o/'PARTIAL.json')['state']=='complete'
 assert list(o.glob('capture-start-*.json'))
 spec=importlib.util.spec_from_file_location('a',D/'original_analyze.py'); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 rows=[]
 for tag in ['warmup']+['sample-%02d'%i for i in range(6)]:
  c=read(o/(tag+'.completed.json')); native=o/(tag+'.json'); assert c['native_result_sha256']==digest(native)
  vals,within=mod.check_proc_a(read(native),' '.join(c['argv']),3)
  checked=read(o/(tag+'.checked.json')); assert checked['values']==vals and checked['within_cv_pct']==within
  if tag!='warmup': rows.append(checked)
 r=mod.build_a(rows); r['w5d1_tg128_process_cv_at_most_4_pct']=r['metrics']['tg128']['cv_pct']<=4.0
 assert read(o/'RESULT.json')==r and r['verdict'] in ('BASELINE_VALID','INVALID_NOISY')
except Exception as e:
 print('incomplete or invalid:',e,file=sys.stderr); sys.exit(1)
print('complete: original six-unit analysis verified')
