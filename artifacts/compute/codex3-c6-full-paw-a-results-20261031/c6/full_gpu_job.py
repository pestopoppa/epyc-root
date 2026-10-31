#!/usr/bin/env python3
"""Actual-calendar C5/C6 full GPU native op component; original worker math untouched."""
import hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ID='refactor-c6-gpu-gak-full-729599d69-20261031'
CPU=Path('/mnt/raid0/llm/kernels/builds/cpu-20261030-729599d69-c6')
GPU=Path('/mnt/raid0/llm/kernels/builds/gpu-20261030-729599d69-c6')
C5=Path('/mnt/raid0/llm/kernels/builds/gpu-20261024-c72ec82f5-c5')
EXPECTED=[f'{image}-{op}' for image in ('C5','C6') for op in ('MUL_MAT','MUL_MAT_ID','FLASH_ATTN_EXT')]+['C6-G10']
class PartialWindow(RuntimeError):pass
ATTEMPT_ROOT=None

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate_native(out,rc):
 native=json.loads((out/'result.json').read_text());assert rc==0 and native['status']=='NATIVE_COMPLETE' and native['process']['children_drained'] and native['process']['reason'] is None and native['process']['rc']==0 and native['qualification_only'] is False
 records=json.loads((out/'native-records.json').read_text())['records'];assert len(records)==15 and len({r['raw_log'] for r in records})==15
 phases=[r for r in records if r['name'] in EXPECTED];assert [r['name'] for r in phases]==EXPECTED
 checks=[];ids={}
 for r in records:
  for key,digest in [('raw_log','raw_sha256'),('stderr_log','stderr_sha256')]:
   p=Path(r[key]);assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(out.resolve()) and sha(p)==r[digest]
 for r in phases:
  name=r['name'];image=C5 if name.startswith('C5-') else GPU;cases=r.get('native_cases',[]);sampler=r.get('sampler') or {};maps=r.get('gpu_maps_during',{})
  assert r['native_rc']==0 and r['confirmed_dead'] and cases and sampler.get('own_pid_kfd_reads',0)>=2 and sampler.get('own_pid_peak_vram_bytes',0)>0 and maps
  assert all(v['inside_selected_image'] and Path(v['resolved']).is_relative_to((image/'bin').resolve()) and sha(v['resolved'])==v['sha256'] for v in maps.values())
  statuses={c['status'] for c in cases};assert statuses<={'ok','not_supported'} and 'ok' in statuses
  if name=='C6-G10':assert len(cases)==25 and all(c['status']=='ok' and 'g10=' in c['params'] for c in cases)
  ids[name]=sorted({(c['op'],c['params'],str(c.get('layout')),c.get('interleaved','')) for c in cases if c['status']=='ok'})
  checks.append({'name':name,'image':str(image),'case_count':len(cases),'ok_count':sum(c['status']=='ok' for c in cases),'unsupported_count':sum(c['status']=='not_supported' for c in cases),'own_peak_vram_bytes':sampler['own_pid_peak_vram_bytes'],'own_kfd_reads':sampler['own_pid_kfd_reads'],'raw_sha256':r['raw_sha256'],'stderr_sha256':r['stderr_sha256']})
 intersections={}
 for op in ('MUL_MAT','MUL_MAT_ID','FLASH_ATTN_EXT'):
  a=set(map(tuple,ids['C5-'+op]));b=set(map(tuple,ids['C6-'+op]));intersections[op]={'intersecting_case_ids':len(a&b),'c5_only':len(a-b),'c6_only':len(b-a),'seeded_input_byte_identity':'UNKNOWN: ordinary native carrier emits no input-byte hashes; no matched numeric comparison claimed'}
 return {'native_result_sha256':sha(out/'result.json'),'native_records_sha256':sha(out/'native-records.json'),'records':len(records),'phases':checks,'case_id_intersections':intersections,'all_phase_native_reference_ok':True,'gpu_execution':True,'full_gak_pass':None}

def main():
 global ATTEMPT_ROOT
 if os.environ.get('FILLER_ID')!=ID or os.environ.get('WS58_REGIONS')!='mi210_0,184-191' or set(os.sched_getaffinity(0))!=set(range(184,192)) or not os.environ.get('FILLER_STOPFILE'):raise RuntimeError('actual GPU calendar grant/affinity missing')
 deadline=float(os.environ['FILLER_DEADLINE']);stop=Path(os.environ['FILLER_STOPFILE']);tag=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+str(os.getpid());root=HERE/'runs'/tag
 if root.exists():raise RuntimeError('attempt collision')
 root.mkdir(parents=True);ATTEMPT_ROOT=root;(HERE/'LATEST-FULL').write_text(str(root)+'\n')
 pre={'schema':'c6.gpu_gak_full_component_pre.v1','id':ID,'grant_sha256':sha(Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(ID+'.grant')),'regions':os.environ['WS58_REGIONS'],'cpus':sorted(os.sched_getaffinity(0)),'deadline':deadline,'source':'729599d69871181d67af715a4c2f9162d5153a2e','runtime_closure_sha256':sha(HERE/'RUNTIME-CLOSURE.sha256'),'package_closure_sha256':sha(HERE/'FULL-CLOSURE.sha256'),'image_manifests':{'C5':sha(C5/'SHA256SUMS'),'C6_CPU':sha(CPU/'SHA256SUMS'),'C6_GPU':sha(GPU/'SHA256SUMS')},'suite_seed':71,'threads':int(os.environ['FILLER_THREADS']),'both_arms_f32_knob':'GGML_FA_VKQ_F32=1','expected_phases':EXPECTED,'original_input_byte_hashes':'UNKNOWN','recorded_at':time.time()}
 (root/'PRE-RUN.json').write_text(json.dumps(pre,indent=2,sort_keys=True)+'\n')
 if stop.exists() or deadline-time.time()<100:raise PartialWindow('STOP or insufficient remaining full GPU window before native')
 out=root/'native';argv=[sys.executable,'-B',str(HERE/'run_gate.py'),'--action','gpu-ops','--cpu-store',str(CPU),'--gpu-store',str(GPU),'--run-dir',str(out)]
 with (root/'native-launch.log').open('wb') as f:
  p=subprocess.Popen(argv,stdout=f,stderr=subprocess.STDOUT,env=os.environ.copy());fd=os.pidfd_open(p.pid)
  try:
   try:rc=p.wait(timeout=max(20,deadline-time.time()-20))
   except subprocess.TimeoutExpired:
    signal.pidfd_send_signal(fd,signal.SIGTERM)
    try:p.wait(timeout=20)
    except subprocess.TimeoutExpired:raise RuntimeError('owned run_gate did not drain at calendar deadline')
    raise PartialWindow('calendar deadline during full GPU native')
  finally:os.close(fd)
 if stop.exists() or rc==75 and deadline-time.time()<100:raise PartialWindow('calendar STOP/deadline during full GPU native')
 body=validate_native(out,rc)
 result={'schema':'c6.gpu_gak_full_component_result.v1','status':'COMPLETE_GPU_COMPONENT_ONLY','partial':False,'pre_sha256':sha(root/'PRE-RUN.json'),'native':body,'full_gak_pass':None,'gpu_execution':True}
 (root/'RESULT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({'status':result['status'],'run':str(root),'phases':len(body['phases'])}),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as e:
  partial=isinstance(e,PartialWindow)
  if ATTEMPT_ROOT:
   row={'schema':'c6.gpu_gak_full_component_result.v1','status':'PARTIAL_WINDOW' if partial else 'REFUSED','partial':partial,'reason':str(e) if partial else 'unexpected_failure','error':repr(e),'full_gak_pass':None,'recorded_at':time.time()}
   (ATTEMPT_ROOT/'RESULT.json').write_text(json.dumps(row,indent=2,sort_keys=True)+'\n')
  print('GPU_FULL_PARTIAL:' if partial else 'GPU_FULL_REFUSED:',repr(e),file=sys.stderr);sys.exit(75 if partial else 2)
