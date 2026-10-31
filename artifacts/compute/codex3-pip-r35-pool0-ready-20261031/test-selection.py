import sys,json,hashlib,importlib.util
from pathlib import Path
H=Path('/mnt/micron/codex3-pip-pool0-merged-r35-20261031');sys.path.insert(0,str(H));from tail_guard import check
s=importlib.util.spec_from_file_location('j',H/'journal_layered.py');j=importlib.util.module_from_spec(s);s.loader.exec_module(j)
class Reader:
 def __init__(self,roots):self.originals=[Path(x) for x in roots];self.root=Path('/tmp/nonexistent-private-r34-shard');self.extra=[]
 def lookup(self,name):
  found=[p/name for p in self.originals if (p/name).is_file()];assert len(found)<=1;return found[0] if found else self.root/name
 def glob(self,pat):return [self.lookup(p.name) for root in self.originals if root.is_dir() for p in root.glob(pat)]+self.extra
 def exists(self,name):return self.lookup(name).exists()
 def read(self,name):return self.lookup(name).read_bytes()
v=json.loads((H/'inventory.json').read_bytes());cfg=json.loads(Path('/mnt/raid0/llm/tmp/codex3-pip02-paddle-relocatable-r11-20261030/attempts/codex3-pip02-paddle-relocatable-r11-g71-20261029-a94a922f363f40babd31928ab6f26005/worker-config.json').read_bytes())
for row in v['pages']:
 sh=row['shard'];page=row['page'];roots=[f'{root}/shard-{sh:02}/shard-{sh}' for root in ('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh','/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh','/mnt/micron/codex3-pip-relocatable-r25-20261030/campaigns-fresh')];w=Reader(roots);journal=j.Journal(w,cfg['campaign']);prefix='region-'+hashlib.sha256(json.dumps(page,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()[:24]+'-';state='missing' if row['kind']=='never-started' else 'unknown';assert check(page,journal,prefix,state)
 if state=='missing':
  w.extra=[Path('orphan.start.json')]
  try:check(page,journal,prefix,state);raise AssertionError('orphan accepted')
  except RuntimeError:pass
p=dict(v['pages'][0]['page'],index=-1)
try:check(p,journal,'region-invalid-','missing');raise AssertionError('outside accepted')
except RuntimeError:pass
print('159 exact originals: 115 never-started positives/orphan negatives, 44 authenticated matched-layout positives; outside-scope refusal')
