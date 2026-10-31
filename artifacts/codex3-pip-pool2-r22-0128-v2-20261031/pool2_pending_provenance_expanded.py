import contextlib,io,importlib.util,json,datetime
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/codex3-pip-head-r28-audit-20261031/inspect.py');s=importlib.util.spec_from_file_location('u',p);m=importlib.util.module_from_spec(s)
with contextlib.redirect_stdout(io.StringIO()):s.loader.exec_module(m)
pending=json.loads(Path('/mnt/raid0/llm/tmp/codex3-pip-head-r28-audit-20261031/pool2-pending.json').read_bytes())['pages'];attempts=Path('/mnt/micron/codex3-pip-split-r22-20261030/attempts');caps=[]
for p in list(attempts.glob('*/capture.json'))+list(Path('/mnt/raid0/llm/tmp/codex3-pip02-paddle-relocatable-r11-20261030/attempts').glob('*/capture.json')):
 try:
  c=json.loads(p.read_bytes());res=p.parent/'result.json';start=datetime.datetime.fromisoformat(c['started_utc'].replace('Z','+00:00')).timestamp()
  if c.get('smoke') is False and res.is_file():caps.append((start,res.stat().st_mtime,c.get('shards',[]),str(p),c.get('id')))
 except (OSError,ValueError,KeyError,TypeError):continue
out=[]
for row in pending:
 shard=next(i//5 for i,x in enumerate(m.plan['pages']) if x['index']==row['index']);page=next(x for x in m.plan['pages'] if x['index']==row['index']);w=m.Read([f'/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}']);j=m.j.Journal(w,m.config['campaign']);path=w.lookup(j.name(page,'start'));mtime=path.stat().st_mtime;matches=[{'capture':c[3],'id':c[4]} for c in caps if c[0]-1<=mtime<=c[1]+1 and shard in c[2]];out.append({'index':row['index'],'shard':shard,'page_start_path':str(path),'page_start_mtime':mtime,'r22_capture_window_candidates':matches})
print(json.dumps({'scope':'read-only timestamp correlation, not provenance proof; only r22 capture corpus searched','pages':out},indent=2))
