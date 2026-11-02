#!/usr/bin/env python3
"""Calendar-only exact restored 15-pair GPU identity producer."""
import hashlib,json,os,re,signal,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'instruments'))
import produce
from arm_order import validate_arm_order
ID='refactor-c6-gpu-27b-identity-r2-729599d69-20261031'
P=Path('/mnt/raid0/llm/kernels/builds/gpu-20261024-c72ec82f5-c5')
C=Path('/mnt/raid0/llm/kernels/builds/gpu-20261030-729599d69-c6')
ATTEMPT_ROOT=None
class PartialWindow(RuntimeError):pass

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def partial(path):
 p=Path(path);s=p.stat()
 if p.suffix!='.gguf':return {'path':str(p),'size':s.st_size,'mtime_ns':s.st_mtime_ns,'whole_file_sha256':sha(p)}
 edge=64*1024**2
 with p.open('rb') as f:
  head=f.read(min(s.st_size,edge));f.seek(max(0,s.st_size-edge));tail=f.read(edge)
 return {'path':str(p),'size':s.st_size,'mtime_ns':s.st_mtime_ns,'edge_bytes':edge,'first_edge_sha256':hashlib.sha256(head).hexdigest(),'last_edge_sha256':hashlib.sha256(tail).hexdigest()}
def pins():
 proto=json.loads((HERE/'PROTOCOL-PINS.json').read_text())
 for name,want in proto['source_pins'].items():
  if sha(HERE/name)!=want:raise RuntimeError('original protocol source changed: '+name)
 for name,want in proto['external_source_pins'].items():
  if sha(name)!=want:raise RuntimeError('external original dependency changed: '+name)
 if sha(HERE/'C5-RECIPES.json')!=proto['c5_recipe_sha256']:raise RuntimeError('C5 recipe changed')
 for row in proto['models_partial_identity']:
  if partial(row['path'])!={k:v for k,v in row.items() if k!='role'}:raise RuntimeError('model partial identity changed')
 profiles=json.loads((HERE/'C5-RECIPES.json').read_text());baseline=profiles['gpu']
 if baseline['root']!=str(P) or baseline['source']!=proto['P']['source']:raise RuntimeError('C5 baseline recipe/source mismatch')
 produce.verify_c5(baseline)
 for root,source in ((C,proto['C']['source']),):
  if json.loads((root/'BUILD-IDENTITY.json').read_text())['source_sha']!=source:raise RuntimeError('store source mismatch')
  produce.verify_aliases(root/'bin')
  for line in (root/'SHA256SUMS').read_text().splitlines():
   digest,name=line.split(None,1);path=root/name.strip()
   if sha(path)!=digest:raise RuntimeError('signed store file changed: '+str(path))
 return proto

def main():
 global ATTEMPT_ROOT
 if os.environ.get('FILLER_ID')!=ID or os.environ.get('WS58_REGIONS')!='mi210_0,72-79' or os.environ.get('FILLER_CPUS')!='72-79' or set(os.sched_getaffinity(0))!=set(range(72,80)):
  raise RuntimeError('actual reviewed GPU grant/affinity absent')
 deadline=float(os.environ['FILLER_DEADLINE']);stop=Path(os.environ['FILLER_STOPFILE'])
 proto=pins();tag=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+str(os.getpid());root=HERE/'runs'/tag
 if root.exists():raise RuntimeError('attempt collision')
 root.mkdir(parents=True);ATTEMPT_ROOT=root;(HERE/'LATEST-RUN').write_text(str(root)+'\n')
 pre={'schema':'c6.gpu27b_identity_pre.v1','filler_id':ID,'grant_sha256':sha(Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(ID+'.grant')),'regions':os.environ['WS58_REGIONS'],'cpus':sorted(os.sched_getaffinity(0)),'deadline':deadline,'source_p':proto['P']['source'],'source_c':proto['C']['source'],'protocol_pins_sha256':sha(HERE/'PROTOCOL-PINS.json'),'original_source_manifest_sha256':sha(HERE/'ORIGINAL-SHA256SUMS'),'package_sha256':sha(HERE/'PACKAGE-SHA256SUMS'),'store_manifests':{'P':sha(P/'SHA256SUMS'),'C':sha(C/'SHA256SUMS')},'models':proto['models_partial_identity'],'pairs':15,'arm_order':'P C repeated15','probe_args':proto['probe_args'],'full_gate_pass':None,'started_at':time.time()}
 (root/'PRE-RUN.json').write_text(json.dumps(pre,indent=2,sort_keys=True)+'\n')
 if stop.exists():raise PartialWindow('calendar STOP before original pair sequence')
 if time.time()+3000>=deadline:raise PartialWindow('insufficient remaining calendar window for original pair sequence')
 argv=['/bin/bash',str(HERE/'original/gpu_champion_ab.sh'),'--p-build',str(P),'--p-tip',proto['P']['source'],'--p-buildno',str(proto['P']['buildno']),'--c-build',str(C),'--c-tip',proto['C']['source'],'--c-buildno',str(proto['C']['buildno']),'--run',str(root/'ab'),'--pairs','15','--args-file',str(HERE/'original/server_args.27b-dflash2-20261004.bin'),'--execute']
 env={**os.environ,'AB_INSIDE_CLAIM':'1','ARM_CPUSET':'72-79','ARM_MEMBIND':'3','HIP_VISIBLE_DEVICES':'0','ROCR_VISIBLE_DEVICES':'0','CUDA_VISIBLE_DEVICES':'0'}
 def check():
  if stop.exists():return
  if os.environ['FILLER_ID']!=ID or set(os.sched_getaffinity(0))!=set(range(72,80)):raise RuntimeError('allocation changed')
  for name,want in proto['source_pins'].items():
   if sha(HERE/name)!=want:raise RuntimeError('original source changed during run')
  for name,want in proto['external_source_pins'].items():
   if sha(name)!=want:raise RuntimeError('external source changed during run')
 def sig(_s,_f):produce.STOP=True
 signal.signal(signal.SIGTERM,sig);signal.signal(signal.SIGINT,sig)
 monitor=produce.OwnedStep(root/'outer-raw.log',128*1024**3,check,stop,root)
 row=monitor.run(argv,root,env,deadline-time.time()-30)
 result={'schema':'c6.gpu27b_identity_result.v1','status':'PARTIAL' if row['reason'] else 'STARTED','partial':bool(row['reason']),'process':row,'original_result_sha256':None,'protocol_pass':None,'identity_pass':None,'full_gate_pass':None}
 if row['reason']:
  (root/'RESULT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');return 75
 original=root/'ab/result.json'
 if not original.exists():raise RuntimeError('original full protocol omitted result')
 data=json.loads(original.read_text());arms=data.get('arms');v=data.get('verdict',{})
 order_proof=validate_arm_order(data,root/'ab',{'P':P/'bin/llama-server','C':C/'bin/llama-server'})
 result['execution_order_proof']=order_proof;identity=v.get('identity',{});result['original_result_sha256']=sha(original);result['identity_pass']=identity.get('C_equals_P') is True and identity.get('P_self_deterministic') is True;result['protocol_pass']=v.get('PASS') is True;result['status']='COMPLETE_ORIGINAL_PROTOCOL' if row['rc']==0 else 'NATIVE_FAILED'
 raw=[]
 for f in sorted((root/'ab').rglob('*')):
  if f.is_file():raw.append({'path':str(f.relative_to(root)),'sha256':sha(f),'size':f.stat().st_size})
 result['raw_files']=raw;result['pre_sha256']=sha(root/'PRE-RUN.json');result['full_gate_pass']=bool(row['rc']==0 and result['protocol_pass'] and result['identity_pass'])
 (root/'RESULT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 return 0 if result['full_gate_pass'] else 2
if __name__=='__main__':
 try:sys.exit(main())
 except Exception as e:
  partial=isinstance(e,PartialWindow)
  if ATTEMPT_ROOT:
   row={'schema':'c6.gpu27b_identity_result.v1','status':'PARTIAL_WINDOW' if partial else 'REFUSED','partial':partial,'reason':str(e) if partial else 'unexpected_failure','error':repr(e),'protocol_pass':None,'identity_pass':None,'full_gate_pass':None,'recorded_at':time.time()}
   (ATTEMPT_ROOT/'RESULT.json').write_text(json.dumps(row,indent=2,sort_keys=True)+'\n')
  print('GPU_IDENTITY_PARTIAL:' if partial else 'GPU_IDENTITY_REFUSED:',repr(e),file=sys.stderr)
  sys.exit(75 if partial else 2)
