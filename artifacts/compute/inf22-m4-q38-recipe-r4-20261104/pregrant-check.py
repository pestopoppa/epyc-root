#!/usr/bin/env python3
import hashlib,json,os,sys
from pathlib import Path
root=Path('/mnt/raid0/llm/tmp/inf22-m4-q38-recipe-r4-20261104');sys.path.insert(0,str(root/'source/scripts/benchmark'))
os.environ['FILLER_ID']='inf22-m4-q38-recipe-r4-20261104'
import m4_cpu_recipe_compare as compare
import m4_cpu_recipe_entry as entry
plan=root/'plan/PLAN.json';sha=hashlib.sha256(plan.read_bytes()).hexdigest()
bound=compare.verify(plan,sha,full_hash=True)
entry.check_enrollment(plan,sha,'inf22-m4-q38-recipe-r4-20261104',None)
sys.path.insert(0,str(root/'source/scripts/vidya'))
from adapters import m4_cpu_speed as reader
config=reader._trusted_config_for(root/'captures/run-r1/capture/future/process-captures/future.json')
assert config.producer_root==root/'source/scripts/benchmark/m4_cpu_producer' and config.diagnostic_plan_sha256==sha
receipt=json.loads((root/'inputs/custody-r2-RESULT.json').read_bytes())
assert receipt['schema']=='epyc.m4.custody.complete.v1' and receipt['measurement'] is False
assert receipt['receipt_sha256']==[i['custody_sha256'] for i in bound['plan']['inputs']]
print(json.dumps({'status':'PASS','row_id':'inf22-m4-q38-recipe-r4-20261104','plan_sha256':sha,'cells':len(bound['plan']['cells']),'custody_receipts':len(receipt['receipt_sha256']),'measurement':False},sort_keys=True))
