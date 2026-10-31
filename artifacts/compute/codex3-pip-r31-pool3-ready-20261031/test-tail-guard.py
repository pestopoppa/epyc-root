import sys,json,hashlib,importlib.util,fnmatch
from pathlib import Path
H=Path('/mnt/micron/codex3-pip-pool3-tail-r31-20261031');sys.path.insert(0,str(H));from tail_guard import check
s=importlib.util.spec_from_file_location('j',H/'journal_layered.py');j=importlib.util.module_from_spec(s);s.loader.exec_module(j)
class Reader:
 def __init__(self,roots):self.originals=[Path(x) for x in roots];self.root=Path('/tmp/nonexistent-private-tail-shard');self.extra=[]
 def lookup(self,name):
  found=[p/name for p in self.originals if (p/name).is_file()];assert len(found)<=1;return found[0] if found else self.root/name
 def glob(self,pat):return [self.lookup(p.name) for root in self.originals if root.is_dir() for p in root.glob(pat)]+self.extra
 def exists(self,name):return self.lookup(name).exists()
 def read(self,name):return self.lookup(name).read_bytes()
v=json.loads((H/'inventory.json').read_bytes());cfg=json.loads(Path('/mnt/raid0/llm/tmp/codex3-pip02-paddle-relocatable-r11-20261030/attempts/codex3-pip02-paddle-relocatable-r11-g71-20261029-a94a922f363f40babd31928ab6f26005/worker-config.json').read_bytes())
for r in v['pages']:
 sh=r['shard'];p=r['page'];roots=[str(Path(x)/f'shard-{sh:02}'/f'shard-{sh}') for x in v['original_roots']];w=Reader(roots[:2]);journal=j.Journal(w,cfg['campaign']);prefix='region-'+hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()[:24]+'-';assert check(p,journal,prefix,'missing');w.extra=[Path('orphan.start.json')]
 try:check(p,journal,prefix,'missing');raise AssertionError('orphan not refused')
 except RuntimeError:pass
w=Reader([]);journal=j.Journal(w,cfg['campaign']);p=dict(v['pages'][0]['page'],index=-1)
try:check(p,journal,'region-invalid-','missing');raise AssertionError('unregistered page')
except RuntimeError:pass
print('60 exact no-start page positives, 60 orphan-region negatives, outside-scope negative passed')
