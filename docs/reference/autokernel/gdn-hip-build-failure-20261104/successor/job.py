#!/usr/bin/env python3
"""CPU-reserved build prerequisite: HIP compile smoke, then content-bound HIP test binary."""
from __future__ import annotations
import hashlib,json,os,subprocess,time,signal,threading,sys
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/autokernel-all-devices-all-dimensions/hip-build-prereq-repair-20261104')
sys.path.insert(0,str(D))
from process_guard import descendants,proc_identity,terminate_owned
ID='codex-ni-akxall31-gdn-hip-build-repair-20261104'
BASE='c72ec82f5417bb2937310326120f149b665e8400'
SRC=D/'attempt-1/source'; BUILD=D/'attempt-1/build-hip'; LOGS=D/'attempt-1/logs'
MANIFEST=D/'attempt-1/HIP-BUILD-MANIFEST.json'
STOP_REQUESTED=threading.Event()
def _on_signal(signum, frame): STOP_REQUESTED.set()
signal.signal(signal.SIGTERM,_on_signal); signal.signal(signal.SIGINT,_on_signal)
def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def run(cmd:list[str],log:Path,env=None):
 log.parent.mkdir(parents=True,exist_ok=True); deadline=int(os.environ.get('FILLER_DEADLINE','0'))
 with log.open('wb') as f:
  proc=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,close_fds=True)
  ident=proc_identity(proc.pid)
  if ident is None: raise RuntimeError('cannot capture launched subprocess birth identity')
  birth=ident[1]; owned={proc.pid:birth}; reason=None
  while proc.poll() is None:
   descendants(proc.pid,birth,owned)
   if STOP_REQUESTED.is_set() or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()): reason='STOP requested'
   elif deadline and time.time()>=deadline: reason='FILLER_DEADLINE reached'
   if reason: break
   time.sleep(.1)
  if reason:
   descendants(proc.pid,birth,owned); terminate_owned(owned,proc.pid,proc)
   raise RuntimeError(f'{reason}; interrupted command: {cmd}; owned process births verified dead')
  rc=proc.wait()
  descendants(proc.pid,birth,owned)
  if any(proc_identity(pid) is not None and proc_identity(pid)[1]==b for pid,b in owned.items()):
   terminate_owned(owned,proc.pid,proc)
 if rc: raise RuntimeError(f'rc={rc} command={cmd}; log={log}')
def verify_prepared_source():
 prep=json.loads((D/'inputs/prepared-source.json').read_text())
 ov=json.loads((D/'inputs/source-overlay.json').read_text())
 if prep.get('base_commit')!=BASE or prep.get('prepared_before_publication') is not True: raise RuntimeError('prepared source pin/phase invalid')
 if prep.get('source_tree')!=str(SRC) or prep.get('patch_sha256')!=ov.get('patch_sha256'): raise RuntimeError('prepared source location/patch binding mismatch')
 head=subprocess.check_output(['git','-C',str(SRC),'rev-parse','HEAD'],text=True).strip()
 delta=subprocess.check_output(['git','-C',str(SRC),'diff','--name-only'],text=True).splitlines()
 staged=subprocess.check_output(['git','-C',str(SRC),'diff','--cached','--name-only'],text=True).splitlines()
 if head!=BASE or delta!=['tests/test-backend-ops.cpp'] or staged: raise RuntimeError(f'champion source identity or overlay delta mismatch; unstaged={delta!r} staged={staged!r}')
 if sha(SRC/'tests/test-backend-ops.cpp')!=prep.get('patched_test_sha256'): raise RuntimeError('patched test source digest mismatch')
 if sha(Path(ov['patch_path']))!=ov['patch_sha256']: raise RuntimeError('overlay patch changed')
 diff=subprocess.check_output(['git','-C',str(SRC),'diff','--','tests/test-backend-ops.cpp'])
 if hashlib.sha256(diff).hexdigest()!=ov['patch_sha256']: raise RuntimeError('actual source diff differs from sealed overlay')
 if subprocess.check_output(['git','-C',str(SRC),'ls-files','--others','--exclude-standard'],text=True).strip(): raise RuntimeError('untracked source files')
 return prep,ov
def verify_affinity():
 cpus=os.environ.get('FILLER_CPUS',''); allowed={int(x) for part in cpus.split(',') if part for x in (range(int(part.split('-')[0]),int(part.split('-')[1])+1) if '-' in part else [part])}; actual=set(os.sched_getaffinity(0))
 if len(allowed)!=4 or actual!=allowed: raise RuntimeError(f'job must inherit exactly four FILLER_CPUS; got affinity={sorted(actual)} grant={sorted(allowed)}')
def smoke():
 verify_affinity(); prep,ov=verify_prepared_source()
 syntax=json.loads((D/'inputs/cxx-syntax-smoke-input.json').read_text())
 if sha(Path(syntax['command'][0]))!=syntax['compiler_sha256'] or sha(D/syntax['configured_flags_origin'])!=syntax['configured_flags_sha256']: raise RuntimeError('C++ syntax compile input changed')
 run(syntax['command'],LOGS/'smoke-test-backend-ops-syntax.log')
 inp=json.loads((D/'inputs/hip-object-smoke-input.json').read_text())
 obj=Path(inp['object_path']); obj.parent.mkdir(parents=True,exist_ok=True)
 if sha(SRC/'ggml/src/ggml-cuda/gated_delta_net.cu')!=inp['kernel_source_sha256']: raise RuntimeError('HIP source differs from pinned smoke input')
 cmd=inp['command']
 if inp['prepared_source']!=str(SRC) or cmd[-1]!=str(SRC/'ggml/src/ggml-cuda/gated_delta_net.cu'): raise RuntimeError('smoke source does not belong to this packet')
 if sha(Path(cmd[0]))!=inp['compiler_sha256']: raise RuntimeError('HIP compiler changed')
 obj.unlink(missing_ok=True)
 run(cmd,LOGS/'smoke-gated-delta-hip-object.log')
 if not obj.is_file() or obj.stat().st_size==0: raise RuntimeError('HIP compiler produced no substantive object')
 receipt={'schema':'akx-all-31-gdn.hip-object-native-smoke.v1','status':'compiled_object','cxx_syntax_checked':True,'cxx_syntax_command':syntax['command'],'cxx_compiler_sha256':syntax['compiler_sha256'],'cxx_syntax_log_sha256':sha(LOGS/'smoke-test-backend-ops-syntax.log'),'unit':'gfx90a-gated-delta-net-hip-object','source_commit':BASE,'patched_test_sha256':prep['patched_test_sha256'],'kernel_source_sha256':sha(SRC/'ggml/src/ggml-cuda/gated_delta_net.cu'),'compiler_command':cmd,'compiler_sha256':sha(Path(cmd[0])),'source_tree':str(SRC),'source_overlay_patch_sha256':ov['patch_sha256'],'object_path':str(obj),'object_bytes':obj.stat().st_size,'object_sha256':sha(obj),'compiler_log_sha256':sha(LOGS/'smoke-gated-delta-hip-object.log'),'cpu_affinity':sorted(os.sched_getaffinity(0)),'filler_cpus':os.environ.get('FILLER_CPUS'),'gpu_required':False,'native_op_executed':False,'auto_kernel_runtime_invoked':False}
 out=os.environ.get('FILLER_DRYRUN_RESULT_PATH')
 if not out: raise RuntimeError('rowflow dryrun result path missing')
 Path(out).write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
def configure_args():
 recipes=json.loads((D/'inputs/C5-RECIPES.json').read_text()); rec=recipes['gpu']; oldsrc=rec['source_root']; oldbuild=rec['root']; args=[]
 for key,item in rec['definitions'].items():
  typ,val=item['type'],str(item['value'])
  if typ in {'INTERNAL','STATIC'} or key in {'CMAKE_CACHEFILE_DIR','CMAKE_HOME_DIRECTORY'}: continue
  val=val.replace(oldsrc,str(SRC)).replace(oldbuild,str(BUILD))
  args.append(f'-D{key}:{typ}={val}')
 return args
def full_build():
 verify_affinity()
 compiler=json.loads((D/'inputs/hip-object-smoke-input.json').read_text())
 if sha(Path(compiler['command'][0]))!=compiler['compiler_sha256']: raise RuntimeError('HIP compiler changed')
 prep,ov=verify_prepared_source(); BUILD.mkdir(parents=True,exist_ok=True); LOGS.mkdir(parents=True,exist_ok=True)
 run(['cmake','-S',str(SRC),'-B',str(BUILD),*configure_args()],LOGS/'configure-hip.log')
 run(['cmake','--build',str(BUILD),'--target','test-backend-ops','ggml-hip','-j','4'],LOGS/'build-test-backend-ops-hip.log')
 binary=BUILD/'bin/test-backend-ops'
 if not binary.is_file(): raise RuntimeError('HIP test-backend-ops binary missing')
 strings=subprocess.check_output(['strings',str(binary)],text=True,errors='replace')
 if 'GDN_ONEHOT_V1' not in strings: raise RuntimeError('binary lacks GDN overlay receipt marker')
 libs={str(x):sha(x) for x in sorted((BUILD/'bin').glob('libggml*.so*')) if x.is_file()}
 if not any('libggml-hip.so' in p for p in libs): raise RuntimeError('HIP shared library missing from build manifest')
 env=os.environ.copy(); env['LD_LIBRARY_PATH']=f'{BUILD / "bin"}:/opt/rocm/lib:/opt/rocm/lib64'
 run([str(D/'inputs/verify_ggml_linkage.sh'),str(binary),str(BUILD/'bin')],LOGS/'verify-ggml-linkage.log',env)
 obj=BUILD/'ggml/src/ggml-hip/CMakeFiles/ggml-hip.dir/__/ggml-cuda/gated_delta_net.cu.o'
 if not obj.is_file(): raise RuntimeError('full HIP build has no GDN kernel object')
 verify_prepared_source()
 m={'schema':'akx-all-31-gdn.hip-build-manifest.v1','source_commit':BASE,'source_tree':str(SRC),'source_overlay_patch_sha256':ov['patch_sha256'],'patched_test_sha256':sha(SRC/'tests/test-backend-ops.cpp'),'gdn_kernel_source_sha256':sha(SRC/'ggml/src/ggml-cuda/gated_delta_net.cu'),'compiler_sha256':sha(Path(json.loads((D/'inputs/hip-object-smoke-input.json').read_text())['command'][0])),'cpu_affinity':sorted(os.sched_getaffinity(0)),'build_targets':['test-backend-ops','ggml-hip'],'build_log_sha256':sha(LOGS/'build-test-backend-ops-hip.log'),'configure_log_sha256':sha(LOGS/'configure-hip.log'),'packet_pin':os.environ['AKX_PACKET_PIN'],'cmake_recipe_sha256':sha(D/'inputs/C5-RECIPES.json'),'cmake_cache_sha256':sha(BUILD/'CMakeCache.txt'),'hip_object':{'path':str(obj),'sha256':sha(obj),'bytes':obj.stat().st_size},'binary':{'path':str(binary),'sha256':sha(binary),'bytes':binary.stat().st_size},'libraries':libs,'linkage_log_sha256':sha(LOGS/'verify-ggml-linkage.log'),'native_op_executed':False,'auto_kernel_runtime_invoked':False,'production_tree_modified':False,'created_at_monotonic_ns':time.monotonic_ns()}
 MANIFEST.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
 (D/'attempt-1/RESULT.json').write_text(json.dumps({'schema':'akx-all-31-gdn.hip-build-result.v1','status':'built','manifest_path':str(MANIFEST),'manifest_sha256':sha(MANIFEST),'native_op_executed':False,'auto_kernel_runtime_invoked':False},indent=2)+'\n')
def verify_seal():
 pin=os.environ.get('AKX_PACKET_PIN')
 if not pin: raise RuntimeError('launcher did not pass the pinned packet seal')
 subprocess.run(['python3',str(D/'verify_seal.py'),'--pin',pin],check=True)
def main():
 if os.environ.get('FILLER_ID') not in (None,ID): raise RuntimeError('FILLER_ID mismatch')
 verify_seal()
 if os.environ.get('FILLER_DRYRUN')=='1': smoke()
 else: full_build()
if __name__=='__main__':
 try: main()
 except Exception as exc:
  if os.environ.get('FILLER_DRYRUN')!='1':
   (D/'attempt-1/RESULT.json').write_text(json.dumps({'schema':'akx-all-31-gdn.hip-build-result.v1','status':'failed','error':str(exc),'native_op_executed':False},indent=2)+'\n')
  raise
