import sys,json,hashlib,importlib.util,fnmatch
from pathlib import Path
H=Path('/mnt/micron/codex3-pip-pool1-r32-20261031');sys.path.insert(0,str(H));from safe_no_layout import allow
spec=importlib.util.spec_from_file_location('journal',H/'journal_layered.py');j=importlib.util.module_from_spec(spec);spec.loader.exec_module(j)
class Reader:
 def __init__(self,roots):self.roots=[Path(x) for x in roots];self.extra=[];self.root=self.roots[-1]
 def lookup(self,name):
  found=[p/name for p in self.roots if (p/name).is_file()];assert len(found)<=1;return found[0] if found else self.root/name
 def glob(self,pat):return [self.lookup(p.name) for root in self.roots if root.is_dir() for p in root.glob(pat)]+self.extra
 def exists(self,name):return self.lookup(name).exists()
 def read(self,name):return self.lookup(name).read_bytes()
a=json.loads((H/'original-evidence.json').read_bytes());plan=json.loads(Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/english755-fresh-plan.json').read_bytes())
for r in a['rows']:
 page=next(p for p in plan['pages'] if p['index']==r['index']);capture=json.loads((Path(r['capture']).parent/'worker-config.json').read_bytes());w=Reader(r['roots']);journal=j.Journal(w,capture['campaign']);prefix='region-'+hashlib.sha256(json.dumps(page,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()[:24]+'-';assert allow(page,journal,prefix)
 w.extra=[Path('intrusion.start.json')]
 try:allow(page,journal,prefix);raise AssertionError('start not rejected')
 except RuntimeError:pass
print('16 original start/capture/source positives and 16 stray-region negative controls passed')
