#!/usr/bin/env python3
"""filler_run15 completion predicate: validate the current smoke/full result."""
import json, math, os, pathlib, sys
D=pathlib.Path(__file__).resolve().parent
def require(ok,msg):
 if not ok: raise ValueError(msg)
def valid_record(r,n):
 require(r.get('schema')=='akx-auto10-mmid-timing.v3' and r.get('status')=='observed','timing schema/status')
 require(r.get('shape')=='M2048' and r.get('n_threads')==n,'shape/thread arm')
 require(r.get('correctness_verdict')=='PASS' and r.get('correctness_aa_clean') is True and r.get('correctness_reps',0)>=2,'associated correctness cell')
 require(int(r.get('batch_ns',0))>0 and int(r.get('serial_ns',0))>0,'positive latency')
 require(math.isfinite(float(r.get('batch_effective_logical_gb_s',0))) and math.isfinite(float(r.get('serial_effective_logical_gb_s',0))),'finite logical rate')
 for name in ('batch_ns_raw','serial_ns_raw'):
  v=[int(x) for x in r[name].split(',')]
  require(len(v)==7 and min(v)>0,'seven positive repeated process timings')
if os.environ.get('FILLER_DRYRUN')=='1' or os.environ.get('FILLER_SMOKE')=='1':
 p=os.environ.get('FILLER_DRYRUN_RESULT_PATH')
 require(p,'publisher smoke result path is unset')
 obj=json.loads(pathlib.Path(p).read_text())
 require(obj.get('schema')=='akx-auto10-publisher-smoke.v1' and obj.get('verdict')=='PASS','publisher native smoke schema/verdict')
 require(len(obj.get('records',[]))==1,'smoke must have exactly one record')
 valid_record(obj['records'][0],4)
else:
 marker=D/'full'/'RESULT.json'
 obj=json.loads(marker.read_text())
 require(obj.get('schema')=='akx-auto10-full-result.v1' and obj.get('units')==54 and obj.get('thread_arms')==[48,96],'full completion marker')
 lines=[json.loads(x) for x in (D/'results.jsonl').read_text().splitlines() if x.strip()]
 require(len(lines)==54,'full result row count')
 keys=set()
 for r in lines:
  valid_record(r,r.get('n_threads'))
  require(r.get('n_threads') in (48,96),'undeclared thread count')
  require(r.get('mode') in ('rand','shared','disjoint') and 1<=r.get('k',0)<=9,'undeclared mode/k')
  key=(r['n_threads'],r['mode'],r['k']); require(key not in keys,'duplicate timing record'); keys.add(key)
 require(len(keys)==54,'incomplete declared cell set')
print('completion predicate PASS')
