import json,hashlib,importlib.util,fnmatch
from pathlib import Path
P=Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/english755-fresh-plan.json');raw=P.read_bytes();plan=json.loads(raw);a=Path('/mnt/micron/codex3-pip-head-r26-20261030/attempts/codex3-pip02-paddle-relocatable-r28-head-20261031-b663efb46b8540fd8d539af009a759d5/worker-config.json');config=json.loads(a.read_bytes())
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
j=load('journal','/mnt/micron/codex3-pip-head-r26-20261030/journal_layered.py');t=load('terminal','/mnt/raid0/llm/tmp/codex3-pip-terminal-future-20261030/terminal.py')
class Read:
 def __init__(self,roots):self.roots=list(map(Path,roots));self.root=self.roots[-1]
 def lookup(self,name):
  found=[x/name for x in self.roots if (x/name).is_file()]
  if len(found)>1:raise RuntimeError('duplicate '+name)
  return found[0] if found else None
 def glob(self,pattern):
  names={x.name for root in self.roots if root.is_dir() for x in root.iterdir() if fnmatch.fnmatchcase(x.name,pattern)}
  return [self.lookup(n) for n in sorted(names)]
 def exists(self,name):
  p=self.lookup(name)
  if not p:return False
  if name.endswith(('.result','.result.json')) and str(p).startswith('/mnt/micron/'):
   mark=self.lookup(name+'.durable');return bool(mark and mark.read_text()==hashlib.sha256(p.read_bytes()).hexdigest())
  return True
 def read(self,name):
  if not self.exists(name):raise FileNotFoundError(name)
  return self.lookup(name).read_bytes()
out=[]
for shard in range(5):
 roots=[f'/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-head-r26-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}'];journal=j.Journal(Read(roots),config['campaign'])
 for page in plan['pages'][5*shard:5*shard+5]:
  state=journal.state(page)
  try:detail=t.classify(journal,page,lambda *_:True,lambda *_:True)
  except Exception as e:detail={'state':'INELIGIBLE','error':repr(e)}
  out.append({'shard':shard,'index':page['index'],'journal_state':state,'region_state_unverified':detail})
print(json.dumps(out,indent=2))
print('DETAILS')
for shard in (3,4):
 roots=[f'/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-head-r26-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}'];w=Read(roots);journal=j.Journal(w,config['campaign'])
 for page in plan['pages'][5*shard:5*shard+5]:
  prefix='region-'+t.sha(t.canon(page))[:24]+'-';layout=json.loads(w.read(prefix+'layout.json'));starts=w.glob(prefix+'*.start.json');results=w.glob(prefix+'*.result.json');sent=w.exists(journal.name(page,'sent'))
  print(json.dumps({'index':page['index'],'boxes':layout['count'],'region_starts':len(starts),'region_results':len(results),'sent':sent,'layout_sha256':t.sha(w.read(prefix+'layout.json'))}))
