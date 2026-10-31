import sys,json,hashlib,importlib.util
from pathlib import Path
from unittest.mock import patch
H=Path('/mnt/micron/codex3-pip-pool0-merged-r35-20261031');sys.path.insert(0,str(H));from tail_guard import check
s=importlib.util.spec_from_file_location('j',H/'journal_layered.py');j=importlib.util.module_from_spec(s);s.loader.exec_module(j)
v=json.loads((H/'inventory.json').read_bytes());row=next(r for r in v['pages'] if r['kind']=='matched-layout');page=row['page'];sh=row['shard'];roots=[Path(root)/f'shard-{sh:02}'/f'shard-{sh}' for root in ('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh','/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh','/mnt/micron/codex3-pip-relocatable-r25-20261030/campaigns-fresh')]
class W:pass
w=W();w.root=Path('/tmp/nonexistent-private-r34-shard');cfg=json.loads(Path('/mnt/raid0/llm/tmp/codex3-pip02-paddle-relocatable-r11-20261030/attempts/codex3-pip02-paddle-relocatable-r11-g71-20261029-a94a922f363f40babd31928ab6f26005/worker-config.json').read_bytes());journal=j.Journal(w,cfg['campaign']);prefix='region-'+hashlib.sha256(json.dumps(page,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()[:24]+'-';assert check(page,journal,prefix,'unknown');target=Path(row['original_files'][0]);original=Path.read_bytes
with patch.object(Path,'read_bytes',lambda self: b'tampered' if self==target else original(self)):
 try:check(page,journal,prefix,'unknown');raise AssertionError('tampered input accepted')
 except RuntimeError:pass
bad=dict(page,image='wrong.png')
try:check(bad,journal,prefix,'unknown');raise AssertionError('identity drift accepted')
except RuntimeError:pass
print('matched original input tamper and page identity drift refused')
