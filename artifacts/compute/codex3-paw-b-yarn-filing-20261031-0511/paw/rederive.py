import json,hashlib,glob,collections
from pathlib import Path
root=Path('/mnt/raid0/llm/tmp/codex3-paw-hsf-t1-20261030/B');run=root/'results/real-1793419627938697268';raw=(root/'PAW3-PREDECLARATION.json').read_bytes();d=json.loads(raw); ref={(i,c['source_row']):c for i,t in zip(d['task_indices'],d['tasks']) for c in t['cases']}; rows=[];errs=[]
for p in run.glob('*.complete.json'):
 j=json.loads(p.read_text());key=(j['task_index'],j['source_row']); c=ref.get(key)
 if not c:errs.append(['unplanned',key]);continue
 if j['case_sha256']!=c['case_sha256'] or j['input']!=c['input'] or j['expected']!=c['reference_output']:errs.append(['binding',key])
 actual=j['raw_output'].strip()==c['reference_output'].strip()
 if actual!=j['match']:errs.append(['match',key])
 rows.append({'task':key[0],'source_row':key[1],'case_sha256':j['case_sha256'],'complete_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'match':actual,'truncation':j['truncation']})
assert len(rows)==len(ref)==72 and len(set((x['task'],x['source_row']) for x in rows))==72 and not errs,errs
state=json.loads((root/'epoch/state.json').read_text()); programs=state['programs']; assert len(programs)==9
for k,v in programs.items():
 assert hashlib.sha256(Path(v['path']).read_bytes()).hexdigest()==v['sha256']
for p in run.glob('*.complete.json'):
 j=json.loads(p.read_text()); assert j['program_sha256']==programs[str(j['task_index'])]['sha256'] and p.with_name(p.name.replace('.complete.json','.exposed.json')).is_file()
assert hashlib.sha256((root/'SOURCES.sha256').read_bytes()).hexdigest()==state['source_manifest_sha256']
counts={str(k):{'complete':sum(x['task']==k for x in rows),'exact':sum(x['task']==k and x['match'] for x in rows)} for k in d['task_indices']}
compiles=[json.loads(p.read_text()) for p in run.glob('task-*compile*.json')]
print(json.dumps({'predeclaration_sha256':hashlib.sha256(raw).hexdigest(),'tasks':counts,'total_exact':sum(x['match'] for x in rows),'complete':len(rows),'program_hashes':{k:v['sha256'] for k,v in programs.items()},'source_manifest_sha256':state['source_manifest_sha256'],'compile_count':len(compiles),'compile_statuses':dict(collections.Counter(x['status'] for x in compiles)),'truncation':dict(collections.Counter(x['truncation'] for x in rows)),'rows':rows},indent=2))
