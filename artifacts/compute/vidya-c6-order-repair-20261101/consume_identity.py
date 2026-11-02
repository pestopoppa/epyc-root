#!/usr/bin/env python3
"""OUTER completion: original 30-arm GPU A/B PASS with exact raw and grant identity."""
import hashlib,json,re,sys
from pathlib import Path
from arm_order import validate_arm_order
HERE=Path(__file__).resolve().parent;ID='refactor-c6-gpu-27b-identity-r2-729599d69-20261031'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def main():
 sys.path.insert(0,str(HERE));import gpu_identity_job as job
 job.pins()
 root=Path((HERE/'LATEST-RUN').read_text().strip());require(root.parent==HERE/'runs' and root.is_dir(),'run pointer')
 pre=json.loads((root/'PRE-RUN.json').read_text());r=json.loads((root/'RESULT.json').read_text());original=json.loads((root/'ab/result.json').read_text())
 require(pre['filler_id']==ID and pre['regions']=='mi210_0,72-79' and pre['cpus']==list(range(72,80)) and pre['pairs']==15,'grant/protocol pre-run')
 require(pre['protocol_pins_sha256']==sha(HERE/'PROTOCOL-PINS.json') and pre['package_sha256']==sha(HERE/'PACKAGE-SHA256SUMS'),'source identity')
 require(r['status']=='COMPLETE_ORIGINAL_PROTOCOL' and r['partial'] is False and r['full_gate_pass'] is True and r['protocol_pass'] is True and r['identity_pass'] is True,'protocol/identity verdict')
 require(r['process']['children_drained'] is True and r['process']['rc']==0 and r['process']['reason'] is None,'native tree completion')
 require(r['pre_sha256']==sha(root/'PRE-RUN.json') and r['original_result_sha256']==sha(root/'ab/result.json'),'result source hashes')
 require(r.get('execution_order_proof')==validate_arm_order(original,root/'ab',{'P':job.P/'bin/llama-server','C':job.C/'bin/llama-server'}),'native execution order proof')
 v=original.get('verdict',{});require(v.get('PASS') is True and v.get('identity',{}).get('C_equals_P') is True and v['identity'].get('P_self_deterministic') is True,'original strict verdict')
 for item in r['raw_files']:
  path=(root/item['path']).resolve();require(path.is_relative_to(root) and path.is_file() and path.stat().st_size==item['size'] and sha(path)==item['sha256'],'raw changed: '+item['path'])
 require(len(r['raw_files'])>=30,'per-arm raw files absent')
 grant=Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(ID+'.grant');require(sha(grant)==pre['grant_sha256'],'grant identity changed')
 log=Path('/mnt/raid0/llm/tmp/compute-flags/ready')/(ID+'.launcher.out');require(log.is_file(),'actual keeper log absent')
 text=log.read_text(errors='replace');end=re.search(r'\bend=([^\s]+)',grant.read_text())
 require('RESOURCE_PASS id='+ID in text and 'job rc=0' in text and end and 'end='+end.group(1) in text,'outer grant/resource/exit proof')
 print(json.dumps({'status':'COMPLETE_ORIGINAL_GPU_IDENTITY','run':str(root),'result_sha256':sha(root/'RESULT.json'),'original_result_sha256':sha(root/'ab/result.json'),'arms':30,'identity_C_equals_P':True,'protocol_pass':True},sort_keys=True))
if __name__=='__main__':
 try:main()
 except Exception as e:print('GPU_IDENTITY_INCOMPLETE:',e,file=sys.stderr);sys.exit(1)
