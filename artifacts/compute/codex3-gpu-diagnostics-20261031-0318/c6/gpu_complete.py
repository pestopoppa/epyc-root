#!/usr/bin/env python3
"""OUTER calendar completion for one GPU diagnostic; never a full G-AK grade."""
import hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ID='refactor-c6-gpu-gak-diag-729599d69-20261031'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def main():
 root=Path((HERE/'LATEST-GPU-DIAG').read_text().strip());require(root.parent==HERE/'runs' and root.is_dir(),'run pointer')
 prepath=root/'PRE-RUN.json';resultpath=root/'RESULT.json';pre=json.loads(prepath.read_text());r=json.loads(resultpath.read_text())
 require(pre['filler_id']==ID and pre['source']=='729599d69871181d67af715a4c2f9162d5153a2e' and 'mi210_0' in pre['regions'],'pre-run identity')
 require(pre['runtime_closure_sha256']==sha(HERE/'RUNTIME-CLOSURE.sha256') and pre['gpu_closure_sha256']==sha(HERE/'GPU-CLOSURE.sha256'),'instrument changed')
 require(pre['cpu_manifest_sha256']==sha(Path('/mnt/raid0/llm/kernels/builds/cpu-20261030-729599d69-c6/SHA256SUMS')) and pre['gpu_manifest_sha256']==sha(Path('/mnt/raid0/llm/kernels/builds/gpu-20261030-729599d69-c6/SHA256SUMS')),'image manifests changed')
 require(pre['grant_sha256']==sha(Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(ID+'.grant')),'grant changed')
 require(r['status']=='COMPLETE_QUALIFICATION_ONLY' and r['full_gak_pass'] is None and r['pre_sha256']==sha(prepath) and r['gpu_execution'] is True,'result/purpose')
 normal=root/'normal';cutoff=root/'cutoff';n=json.loads((normal/'result.json').read_text());c=json.loads((cutoff/'result.json').read_text())
 require(n['status']=='NATIVE_COMPLETE' and n['qualification_only'] is True and n['process']['children_drained'] and n['process']['rc']==0,'normal native')
 require(c['status']=='PARTIAL' and c['qualification_only'] is True and c['process']['children_drained'] and c['process']['reason']=='stop_requested','cutoff native')
 for rel,key in [('normal/result.json','result_sha256'),('normal/native-records.json','native_sha256'),('normal/qualification.json','qualification_sha256')]:require(sha(root/rel)==r['normal'][key],rel+' hash')
 require(sha(cutoff/'result.json')==r['cutoff']['result_sha256'] and sha(cutoff/'raw.log')==r['cutoff']['raw_sha256'],'cutoff raw hash')
 require(r['normal']['native_cases']>0 and r['normal']['kfd_reads']>=2 and r['normal']['own_peak_vram_bytes']>0,'normal HIP residency')
 records=json.loads((normal/'native-records.json').read_text())['records']
 for item in records:
  require(sha(item['raw_log'])==item['raw_sha256'] and sha(item['stderr_log'])==item['stderr_sha256'],'normal native raw changed')
 require(r['cutoff']['child_rc']==75 and len([x for x in r['cutoff']['witness'] if x['own_vram_bytes'] is not None and x['own_vram_bytes']>0 and x['maps']])>=2,'active GPU cutoff witness')
 log=Path('/mnt/raid0/llm/tmp/compute-flags/ready')/(ID+'.launcher.out');require(log.is_file(),'actual keeper log absent')
 text=log.read_text(errors='replace');require('RESOURCE_PASS id='+ID in text and 'job rc=0' in text,'outer resource/native exit proof')
 grant=Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(ID+'.grant');end=re.search(r'\bend=([^\s]+)',grant.read_text());require(end and 'end='+end.group(1) in text,'matching grant end')
 print(json.dumps({'status':'COMPLETE_QUALIFICATION_ONLY','run':str(root),'result_sha256':sha(resultpath),'normal_native_cases':r['normal']['native_cases'],'gpu_execution':True,'full_gak_pass':None},sort_keys=True))
if __name__=='__main__':
 try:main()
 except Exception as e:print('GPU_DIAG_INCOMPLETE:',e,file=sys.stderr);sys.exit(1)
