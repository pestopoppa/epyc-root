import contextlib,io,importlib.util,json,collections
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/codex3-pip-head-r28-audit-20261031/inspect.py');s=importlib.util.spec_from_file_location('u',p);m=importlib.util.module_from_spec(s)
with contextlib.redirect_stdout(io.StringIO()):s.loader.exec_module(m)
out=[]
for group in range(11,144,12):
 for shard in range(group,min(group+3,151)):
  roots=[f'/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}'];w=m.Read(roots);j=m.j.Journal(w,m.config['campaign'])
  for page in m.plan['pages'][5*shard:5*shard+5]:
   state=j.state(page)
   if page['index'] in m.plan['prior_original_page_exposures_unknown']: detail={'state':'prior-plan-unknown'}
   else:
    try:detail=m.t.classify(j,page,lambda *_:True,lambda *_:True)
    except Exception as e:detail={'state':'INELIGIBLE','error':repr(e)}
   out.append({'group':group,'shard':shard,'index':page['index'],'journal_state':state,'region_state':detail['state'],'unknown_region_count':len(detail.get('regions',[])),'error':detail.get('error')})
summary={}
for group in range(11,144,12):
 rows=[x for x in out if x['group']==group];summary[str(group)]={'journal':dict(collections.Counter(x['journal_state'] for x in rows)),'native_region_unverified':dict(collections.Counter(x['region_state'] for x in rows)),'unmatched_regions':sum(x['unknown_region_count'] for x in rows)}
print(json.dumps({'scope':'read-only native region structural classifier; capture callbacks are exploratory and not provenance proof','summary':summary,'pages':out},indent=2))
