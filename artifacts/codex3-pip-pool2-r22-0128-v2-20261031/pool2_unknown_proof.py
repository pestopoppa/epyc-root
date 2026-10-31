import contextlib,io,importlib.util,json
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/codex3-pip-head-r28-audit-20261031/inspect.py');s=importlib.util.spec_from_file_location('u',p);m=importlib.util.module_from_spec(s)
with contextlib.redirect_stdout(io.StringIO()):s.loader.exec_module(m)
root=Path('/mnt/micron/codex3-pip-split-r22-20261030/attempts');captures=list(root.glob('*/capture.json'));proof=m.t.NativeProof(captures,m.config['campaign'],m.raw);rows=[]
for group in (47,119):
 for shard in range(group,group+3):
  w=m.Read([f'/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}']);j=m.j.Journal(w,m.config['campaign'])
  for page in m.plan['pages'][5*shard:5*shard+5]:
   if j.state(page)!='unknown':continue
   try:d=m.t.classify(j,page,proof.unknown,lambda *_:True);rows.append({'group':group,'index':page['index'],'state':d['state'],'unknown_regions':len(d.get('regions',[]))})
   except Exception as e:rows.append({'group':group,'index':page['index'],'state':'ineligible','reason':repr(e)})
print(json.dumps({'scope':'original r22 capture corpus with NativeProof unknown region verifier; no inference','rows':rows},indent=2))
