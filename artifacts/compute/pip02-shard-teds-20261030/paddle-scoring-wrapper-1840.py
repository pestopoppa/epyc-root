import sys,json,hashlib,importlib.metadata
from pathlib import Path
sys.path.insert(0,'/mnt/micron/codex3-lanes/research/scripts/benchmark')
from odl_bench import pip02_records as rec,pip02_lineage as lin,pip02_compare as compare
from odl_bench.pip02_native_score import evaluate
from src.dataset.end2end_dataset import End2EndDataset
R=Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029');O=R/'scoring-shards-20261030/paddle-split-v3';O.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
pin=json.loads((R/'scoring-prep/pins_v1.json').read_text());assert sys.version==pin['python'];assert sorted(d.metadata['Name']+'=='+d.version for d in importlib.metadata.distributions())==pin['packages']
for p,h in pin['files'].items():assert sha(p.replace('/home/node/','/home/daniele/'))==h,p
source=Path('/mnt/micron/codex3-lanes/research/scripts/benchmark/odl_bench'); hashes={n:sha(source/n) for n in ['pip02_records.py','pip02_lineage.py','pip02_compare.py','pip02_native_score.py']}
assert hashes=={'pip02_records.py':'2d364d7a7ef1d47b21fb8f3352ff4ffe98e93c682da3996f6e1270c8193c81cd','pip02_lineage.py':'6dea759fe4fa7adc5c78d34fe7b01aea1d44ab98bc3103ccacbb3f36efb831fa','pip02_compare.py':'37e9d673ba46ac16c5f8169db97290933b3c63fb48ef133b825d5db3a9ba995e','pip02_native_score.py':'27f0b630b6812aecad35d1c65329841a5011e421326e81f9f14c8c66a6fdbe5e'}
config=Path('/mnt/raid0/llm/tmp/pip02-pipeline-prep-20261029/paddle-cpu-campaign-config-v3.json');assert sha(config)==compare.CONFIG
plan=json.loads(Path(pin['plan']).read_text());gt=json.loads(Path(pin['gt']).read_text());campaign=compare.campaign(json.loads(config.read_text()));pins={}
for version,(root,h) in lin.PADDLE_ROOTS.items():
 p=root/'source-pins.json';assert sha(p)==h;pins[str(p.resolve())]=h
 for k,v in json.loads(p.read_text()).items():pins[str(Path(k).resolve())]=v
roots=[R/'campaigns-fresh',Path('/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh'),Path('/mnt/micron/codex3-pip-relocatable-r25-20261030/campaigns-fresh'),Path('/mnt/micron/codex3-pip-head-r26-20261030/campaigns-fresh')]
for sh in map(int,sys.argv[1:]):
 dest=O/f's{sh:03}.json'
 if dest.exists():raise ValueError('refuse overwrite: '+str(dest))
 d=rec.LayeredPaths([p/f'shard-{sh:02}'/f'shard-{sh}' for p in roots]);pages=[]
 for pos in range(sh*5,min(sh*5+5,len(plan['pages']))):
  row=plan['pages'][pos];g=gt[row['index']];assert g['page_info']['image_path']==row['image'] and g['page_info']['page_attribute']['language']=='english';assert len(End2EndDataset.get_page_elements(None,g).get('table',[]))==row['table_count']
  x={'position':pos,'image':row['image'],'gt_index':row['index'],'gt_tables':row['table_count'],'status':'unknown','reason':None,'tables':None}
  try:
   key=rec.sha(rec.canon({'campaign':rec.sha(rec.canon(campaign)),'page':row}));prefix='region-'+rec.sha(rec.canon(row))[:24]+'-'
   def snapshot():
    paths=d.glob(key+'.*')+d.glob(prefix+'*')
    return {str(p):sha(p) for p in paths}
   before=snapshot()
   text=rec.paddle(d,row,campaign)
   if text is None:x['reason']='no durable completed page'
   else:
    v=lin.paddle_lineage(d,row,campaign,sh,pins);x['source_lineage']=v;x['prediction_sha256']=hashlib.sha256(text.encode()).hexdigest()
    if not v.get('verified'):x.update(status='unverified',reason=v['basis'])
    else:
     assert sha('/mnt/raid0/llm/datasets/omnidocbench/images/'+row['image'])==row['sha256'];vals=evaluate(g,text);assert len(vals)==row['table_count'];x.update(status='complete',reason='native finish and request origins verified',tables=vals)
  except Exception as e:x.update(status='error',reason=f'{type(e).__name__}: {e}')
  else:
   try:
    if snapshot()!=before:raise ValueError('captured page input changed during scoring')
    x['input_sha256']=before
   except Exception as e:x.update(status='error',reason=f'{type(e).__name__}: {e}',tables=None)
  pages.append(x)
 vals=[t for p in pages if p['tables'] is not None for t in p['tables']];out={'arm':'paddle','cohort':'pip02-english-fresh-20261029','shard':sh,'plan_sha256':sha(pin['plan']),'gt_sha256':sha(pin['gt']),'config_sha256':sha(config),'scoring_sources_sha256':hashes,'pages':pages,'coverage':{'pages_complete':sum(p['status']=='complete' for p in pages),'pages_total':len(pages),'gt_tables_scored':len(vals),'gt_tables_total':sum(p['gt_tables'] for p in pages)},'means':{k:sum(t[k] for t in vals)/len(vals) if vals else None for k in ['teds','teds_structure_only']}}
 with dest.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
 print(sh,out['coverage'],out['means'],flush=True)
