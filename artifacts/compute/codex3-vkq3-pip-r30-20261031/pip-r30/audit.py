import json,hashlib,datetime
from pathlib import Path
B=Path('/mnt/raid0/llm/tmp/codex3-pip-head-r28-audit-20261031');P=Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/english755-fresh-plan.json')
old=Path('/mnt/raid0/llm/tmp/codex3-pip02-phasec-20261029/campaigns-fresh');mic=Path('/mnt/micron/codex3-pip-split-r22-20261030/campaigns-fresh')
base=[Path('/mnt/raid0/llm/tmp/codex3-pip02-paddle-relocatable-r11-20261030/attempts'),Path('/mnt/micron/codex3-pip-split-r22-20261030/attempts')]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
can=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
plan=json.loads(P.read_bytes());known=json.loads((B/'pool2-pending-provenance-expanded.json').read_bytes())['pages'];caps=[]
for root in base:
 for cp in root.glob('*/capture.json'):
  try:
   d=json.loads(cp.read_bytes());r=cp.parent/'result.json';w=cp.parent/'worker-config.json'
   if d.get('smoke') is False and r.is_file() and w.is_file():caps.append((cp,d,json.loads(w.read_bytes()),datetime.datetime.fromisoformat(d['started_utc'].replace('Z','+00:00')).timestamp(),r.stat().st_mtime))
  except (OSError,ValueError,KeyError):continue
rows=[];evidence={}
for x in known:
 page=next(p for p in plan['pages'] if p['index']==x['index']);pos=plan['pages'].index(page);sh=pos//5;start=Path(x['page_start_path']);raw=start.read_bytes();a=json.loads(raw);assert a['page']==page
 roots=[p/f'shard-{sh:02}'/f'shard-{sh}' for p in (old,mic)];assert start.parent in roots
 key='region-'+hashlib.sha256(can(page)).hexdigest()[:24]+'-'
 assert all(not list(r.glob(key+'*')) for r in roots),x['index']
 candidates=[(cp,c,w) for cp,c,w,t0,t1 in caps if sh in c.get('shards',[]) and t0-1<=start.stat().st_mtime<=t1+1 and str(start.parent) in w.get('output_roots',[])]
 assert len(candidates)==1,(x['index'],[(str(c[0])) for c in candidates]);cp,c,w=candidates[0];assert w['capture_path']==str(cp) and w['population_sha256']==sha(P)
 campaign_sha=hashlib.sha256(can(w['campaign'])).hexdigest();assert a['campaign']==campaign_sha
 assert not (start.parent/(start.stem+'.sent')).exists()
 for p in [cp,cp.parent/'worker-config.json',cp.parent/'worker.log',cp.parent/'server.log',cp.parent/'result.json']:
  evidence[str(p)]=sha(p)
 for n in ('parallel_owner.py','parallel_worker.py','pages_driver_checkpoint.py','pipeline_worker_generic.py','region_generic.py'):
  k=str(cp.parents[2]/n);expected=c['source_pins'][k];assert sha(k)==expected;evidence[k]=expected
 for suffix in ('/journal.py','/bounded_writer.py'):
  matches=[(k,v) for k,v in c['source_pins'].items() if k.endswith(suffix)];assert len(matches)==1
  k,h=matches[0];assert sha(k)==h;evidence[k]=h
 worker=(cp.parent/'worker.log').read_text();server=(cp.parent/'server.log').read_text();assert 'Creating model:' in worker and 'SIGTERM' in worker and 'listening on' in server and 'cleaning up' in server
 assert 'POST ' not in server
 rows.append({'index':page['index'],'shard':sh,'start':str(start),'start_sha256':sha(start),'start_mtime':start.stat().st_mtime,'started_monotonic_ns':a['started_monotonic_ns'],'capture':str(cp),'capture_sha256':sha(cp),'campaign_sha256':campaign_sha,'roots':list(map(str,roots)),'region_artifacts':0})
print(json.dumps({'schema':'pip02-pool2-recovery-evidence/v1','scope':'16 native page starts, unchanged native region journal and exact output roots; capture linkage is correlated by shard/root/runtime and shared lock, not intrinsic page PID binding','limitations':'worker result has factory=null and no retained worker birth/argv witness; server no POST is supporting evidence only, not a stand-alone proof','rows':rows,'evidence_sha256':evidence},indent=2))
