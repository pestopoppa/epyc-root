#!/usr/bin/env python3
"""Fail-closed completion; no claims about serving or production floors."""
import hashlib,json,os,pathlib,sys
D=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(D/'native'))
from evidence_custody import read_receipt
from source_census import validate as validate_census
from ring_archive import verify as verify_archive
smoke=os.getenv('FILLER_DRYRUN')=='1'
p=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'RESULT.json'
r=json.loads(p.read_text()); n=1 if smoke else 24; cpus=r['cpus']
assert len(cpus)==len(set(cpus)) and all(type(c) is int and c>=0 for c in cpus)
assert (len(cpus)==4 if smoke else cpus==list(range(96)))
assert r['status']=='diagnostic_complete' and r['measurement_admission']=='none' and r['floor_claim']=='none'
assert r['pair_count']==n and r['cpus']==cpus and len(r['units'])==2*n
for i in range(n):
 units=[x for x in r['units'] if x['pair']==i]
 assert len(units)==2 and [x['arm'] for x in units]==(['off','on'] if i%2==0 else ['on','off'])
 for x in units:
  assert x['target']['count']>0 and x['target']['wall_ns']>0
  budget=int(r['seconds_cpu']*1e9); cpu=x['target']['cpu_ns']
  assert .99*budget<=cpu<=budget+max(25_000_000,.05*budget)
  assert x['child_cleanup']=={'pid':x['target_identity']['pid'],'returncode':0,'reaped':True}
  if x['arm']=='on':
   obs=x['observer'];assert obs['measurement_admission']=='none'
   assert obs['target_identity']==x['target_identity']
   assert x['worker_cleanup']['pid']>0 and x['worker_cleanup']['returncode']==0 and x['worker_cleanup']['reaped'] is True
   assert obs['request_context']=={'launch_ordinal':i,'phase':'synthetic-overhead','slot_index':0,'prompt_id':'cpu-time-controlled','request_sha256':hashlib.sha256(__import__('job').CHILD.encode()).hexdigest()}
   ev=pathlib.Path(obs['evidence_path']);assert ev.is_absolute() and ev.parent==p.parent/(p.stem+'-evidence')
   raw,_=read_receipt(str(ev),obs['evidence_sha256']); body=json.loads(raw)
   validate_census(body,set(cpus))
   prov={v['event_id']:v for v in body['source_provenance']}
   verify_archive(str(ev)+'.rings',body['archive_receipt'],max_bytes=256*1024*1024,expected_sources=set(prov),source_provenance=prov,expected_terminals={v['event_id']:(v['ring']['head'],v['ring']['tail']) for v in body['rings']})

  else:assert x['observer'] is None and x['worker_cleanup'] is None
print('completed synthetic-only observer overhead diagnostic')
