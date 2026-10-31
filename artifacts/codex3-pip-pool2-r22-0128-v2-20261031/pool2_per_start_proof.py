import contextlib,io,importlib.util,json
from pathlib import Path
p=Path('/mnt/raid0/llm/tmp/codex3-pip-head-r28-audit-20261031/inspect.py');s=importlib.util.spec_from_file_location('u',p);m=importlib.util.module_from_spec(s)
with contextlib.redirect_stdout(io.StringIO()):s.loader.exec_module(m)
root=Path('/mnt/micron/codex3-pip-split-r22-20261030/attempts');captures=list(root.glob('*/capture.json'))+[Path('/mnt/raid0/llm/tmp/codex3-pip02-paddle-relocatable-r11-20261030/attempts/codex3-pip02-paddle-relocatable-r11-g119-20261029-d3da7c994c8f488282ee28a363a78822/capture.json')];proof=m.t.NativeProof(captures,m.config['campaign'],m.raw);rows=[]
for shard in range(119,122):
 w=m.Read([f'/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh/shard-{shard:02d}/shard-{shard}',f'/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh/shard-{shard:02d}/shard-{shard}']);j=m.j.Journal(w,m.config['campaign'])
 for page in m.plan['pages'][5*shard:5*shard+5]:
  prefix='region-'+m.t.sha(m.t.canon(page))[:24]+'-'
  for sp in w.glob(prefix+'*.start.json'):
   if w.exists(sp.name.replace('.start.json','.result.json')):continue
   rec=json.loads(w.read(sp.name));rows.append({'index':page['index'],'start':str(sp),'capture':rec['provenance']['origin_capture_sha256'],'capture_valid':proof.unknown(rec['provenance'],j,page)})
print(json.dumps({'scope':'individual unmatched region original capture proofs','rows':rows},indent=2))
