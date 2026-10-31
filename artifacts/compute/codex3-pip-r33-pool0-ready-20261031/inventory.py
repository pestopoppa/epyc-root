import json,hashlib,datetime
from pathlib import Path
R=Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029');planpath=R/'english755-fresh-plan.json';raw=planpath.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();assert sha(raw)=='63028e74950ba7250f33cbce13f4f0bdd165bba2a075242db4475c26f645ed68';plan=json.loads(raw);cfg=json.loads(Path('/mnt/raid0/llm/tmp/codex3-pip02-paddle-relocatable-r11-20261030/attempts/codex3-pip02-paddle-relocatable-r11-g71-20261029-a94a922f363f40babd31928ab6f26005/worker-config.json').read_bytes());can=lambda o:json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode();campaign=sha(can(cfg['campaign']));roots=[R/'campaigns-fresh',Path('/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh'),Path('/mnt/micron/codex3-pip-relocatable-r25-20261030/campaigns-fresh')];groups=[41,53,89,113,137,149];pages=[]
for group in groups:
 for sh in range(group,min(group+3,151)):
  for row in plan['pages'][sh*5:sh*5+5]:
   assert row['index'] not in plan['prior_original_page_exposures_unknown'];img=Path('/mnt/raid0/llm/datasets/omnidocbench/images')/row['image'];assert img.is_file() and img.stat().st_size==row['bytes'] and sha(img.read_bytes())==row['sha256'];key=sha(can({'campaign':campaign,'page':row}));prefix='region-'+sha(can(row))[:24]+'-'
   for root in roots:
    d=root/f'shard-{sh:02}'/f'shard-{sh}'
    if d.exists():
     x=[p.name for p in d.iterdir() if p.name.startswith((key+'.',prefix))]
     if x:raise ValueError(f'already touched page {row["index"]}: {d} {x}')
   pages.append({'group':group,'shard':sh,'page':row})
assert len(pages)==85 and len({x['page']['index'] for x in pages})==85
print(json.dumps({'schema':'pip02-pool0-never-started-inventory/v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'only groups 41,53,89,113,137,149 of original English755 plan; all 85 missing original starts at audit time','plan_sha256':sha(raw),'campaign_sha256':campaign,'original_roots':[str(x) for x in roots],'groups':groups,'pages':pages},indent=2))
