import contextlib,io,importlib.util,json
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/codex3-pip-head-r28-audit-20261031/inspect.py');s=importlib.util.spec_from_file_location('u',p);m=importlib.util.module_from_spec(s)
with contextlib.redirect_stdout(io.StringIO()):s.loader.exec_module(m)
data=json.loads(Path('/mnt/raid0/llm/tmp/codex3-pip-head-r28-audit-20261031/pool2-inspection.json').read_bytes());out=[]
for q in data['pages']:
 if q['region_state']!='pending':continue
 shard=q['shard'];page=next(x for x in m.plan['pages'] if x['index']==q['index']);w=m.Read([f'/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}']);j=m.j.Journal(w,m.config['campaign']);prefix='region-'+m.t.sha(m.t.canon(page))[:24]+'-';layout=w.exists(prefix+'layout.json');starts=w.glob(prefix+'*.start.json');out.append({'group':q['group'],'index':q['index'],'layout':layout,'starts':len(starts),'sent':w.exists(j.name(page,'sent'))})
print(json.dumps({'scope':'read-only pending page state','pages':out},indent=2))
