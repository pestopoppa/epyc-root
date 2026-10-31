import json,hashlib,collections
from pathlib import Path
r=Path('/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/paw-repair/super-host2');q=r/'results/real-1793424296647452148';decl=json.loads((r/'PREDECLARATION.json').read_text()); native=json.loads((q/'native-record.json').read_text()); tup=json.loads((q/'claim-tuples.json').read_text()); ref={x['source_row']:x for x in decl['cases']}; counts=collections.Counter();rows=[];assert len(ref)==8
assert hashlib.sha256((r/'PREDECLARATION.json').read_bytes()).hexdigest()==native['declaration_sha256'] and hashlib.sha256((r/'SOURCES.sha256').read_bytes()).hexdigest()==native['source_manifest_sha256']
assert hashlib.sha256((q/'native-record.json').read_bytes()).hexdigest()==tup['native_sha256']
for k,p in native['program_paths'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==native['program_sha256'][k]
for f in sorted(q.glob('*.complete.json')):
 j=json.loads(f.read_text());case=ref[j['source_row']];assert j['input']==case['input'] and j['expected']==case['reference_output'] and j['program_sha256']==native['program_sha256'];assert hashlib.sha256(Path(j['grant_snapshot_path']).read_bytes()).hexdigest()==j['grant_sha256']==native['grant_sha256'];assert f.with_name(f.name.replace('.complete.json','.exposed.json')).exists()
 for arm in ['binary','semantic']:
  x=j[arm+'_prediction'];status='unsure' if x=='UNSURE' else 'correct' if x==case['reference_output'] else 'incorrect' if x in ('CONTRADICTION','NO_CONTRADICTION') else 'invalid';counts[(case['category'],arm,status)]+=1
 rows.append({'source_row':j['source_row'],'category':case['category'],'case_sha256':case['case_sha256'],'complete_sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
assert len(rows)==8 and len(tup['tuples'])==1
print(json.dumps({'records':len(rows),'completed_cells':16,'counts':[{'category':a,'arm':b,'status':c,'count':n} for (a,b,c),n in sorted(counts.items())],'native_sha256':tup['native_sha256'],'projection_sha256':hashlib.sha256((q/'claim-tuples.json').read_bytes()).hexdigest(),'source_manifest_sha256':native['source_manifest_sha256'],'rows':rows},indent=2))
