import sys,json,hashlib,datetime
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/codex3-pip-pool0-partial-20261031-0644');A=Path('/mnt/raid0/llm/tmp/codex3-pip-pool0-recovery-20261031-0638');R=Path('/mnt/raid0/llm/artifacts/pip02-scorer/12b17baca/pkg');sys.path=[x for x in sys.path if x not in ('',str(D))];sys.path.insert(0,str(R));import tests_native as t
from odl_bench import pip02_records as rec
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();data=json.loads((A/'INSPECTION.json').read_bytes())['pages'];layout=json.loads((A/'LAYOUT-AUDIT.json').read_bytes())['rows'];verified={r['index']:r for r in layout if r['verified_request_origins']};groups=[5,17,29,65,77,101,125];pages=[];pins={}
for r in data:
 if r['group'] not in groups:continue
 index=r['index'];kind='matched-layout' if index in verified else 'never-started' if r['journal_state']=='missing' and r['region_state']=='pending' else None
 if kind is None:continue
 page=next(p for p in t.plan['pages'] if p['index']==index);d=t.layers(r['shard']);prefix='region-'+rec.sha(rec.canon(page))[:24]+'-';key=rec.sha(rec.canon({'campaign':rec.sha(rec.canon(t.campaign)),'page':page}));files=[]
 for root in d.roots:
  if not root.is_dir():continue
  for p in root.iterdir():
   if p.name.startswith((prefix,key+'.')) and p.is_file():files.append(str(p));pins[str(p)]=sha(p)
 if kind=='never-started':assert not files
 else:
  assert verified[index]['requests']>0
  for p in verified[index]['selected_captures']:
   p=Path(p);pins[str(p)]=sha(p)
 image=Path('/mnt/raid0/llm/datasets/omnidocbench/images')/page['image'];assert sha(image)==page['sha256'];pins[str(image)]=page['sha256'];pages.append({'group':r['group'],'shard':r['shard'],'page':page,'kind':kind,'original_files':sorted(files)})
assert len(pages)==74 and sum(x['kind']=='matched-layout' for x in pages)==44 and len({x['page']['index'] for x in pages})==74
for p in (A/'LAYOUT-AUDIT.json',A/'audit-layouts.py',A/'INSPECTION.json',A/'inspect.py'):pins[str(p)]=sha(p)
out={'schema':'pip02-pool0-partial-selected/v1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'44 strictly authenticated saved-layout pages and 30 original no-start pages only; all other cases excluded','groups':groups,'campaign_sha256':rec.sha(rec.canon(t.campaign)),'pages':pages,'original_input_sha256':pins};(D/'INVENTORY.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print('selected',len(pages),'pins',len(pins))
