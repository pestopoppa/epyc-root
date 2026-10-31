import collections, hashlib, json
from pathlib import Path
base = Path('/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245')
roots = [base/'paw-standard-a-continuation', base/'paw-repair/a-host2']
runs = [roots[0]/'results/real-1793423551766543227', roots[1]/'results/real-1793422946113892819']
hashfile = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
decls = [json.loads((p/'PAW3-PREDECLARATION.json').read_text()) for p in roots]
refs = [{(i, c['source_row']): c for i,t in zip(d['task_indices'],d['tasks']) for c in t['cases']} for d in decls]
records = [{(j['task_index'],j['source_row']):j for p in run.glob('*.complete.json') for j in [json.loads(p.read_text())]} for run in runs]
keys = set(refs[0])
assert keys == set(refs[1]) == set(records[0]) == set(records[1]) and len(keys) == 64
assert all(refs[0][k] == refs[1][k] for k in keys)
assert decls[0]['source_plan_sha256'] == decls[1]['source_plan_sha256']
assert all(a['spec_sha256'] == b['spec_sha256'] for a,b in zip(decls[0]['tasks'],decls[1]['tasks']))
assert decls[1]['paired_standard_declaration_sha256'] == hashfile(roots[0]/'PAW3-PREDECLARATION.json')
for root,run,ref,rows in zip(roots,runs,refs,records):
    state = json.loads((root/'epoch/state.json').read_text())
    assert hashfile(root/'SOURCES.sha256') == state['source_manifest_sha256']
    assert len(state['programs']) == 8
    for p in state['programs'].values(): assert hashfile(Path(p['path'])) == p['sha256']
    for k,j in rows.items():
        c=ref[k]
        assert j['case_sha256']==c['case_sha256'] and j['input']==c['input'] and j['expected']==c['reference_output']
        assert j['program_sha256']==state['programs'][str(k[0])]['sha256']
        assert j['match']==(j['raw_output'].strip()==c['reference_output'].strip())
count=collections.Counter((records[0][k]['match'],records[1][k]['match']) for k in keys)
print(json.dumps({'pairs':len(keys),'declaration_sha256':[hashfile(p/'PAW3-PREDECLARATION.json') for p in roots], 'source_manifests_sha256':[hashfile(p/'SOURCES.sha256') for p in roots], 'both':count[True,True], 'standard_only':count[True,False], 'compact_only':count[False,True], 'neither':count[False,False], 'scope':'descriptive; standard original rc1 and offline finalization separate; no full PAW-3 gate'},indent=2))
