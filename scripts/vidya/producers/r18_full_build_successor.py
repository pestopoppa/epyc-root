#!/usr/bin/env python3
import argparse,hashlib,json,os,pathlib,signal,subprocess,time,sys,shutil
PRODUCERS=pathlib.Path(__file__).resolve().parent
INPUTS=PRODUCERS/'r18_inputs'
sys.path.insert(0, str(INPUTS))
import replay_evidence as evidence
sys.path.insert(0, str(PRODUCERS))
import r18_symbol_capture as belief
D=pathlib.Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/r18a-verified-anchor-20261031/belief-successor-20261102')
COMMIT='ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--scratch',required=True);p.add_argument('--mode',choices=['smoke','cutoff','configure','full'],required=True);a=p.parse_args()
S=pathlib.Path(a.source); B=pathlib.Path(a.scratch)
assert B.resolve().is_relative_to((D/'scratch').resolve()) and B.resolve() != (D/'scratch').resolve(), 'private scratch only'
assert os.environ.get('FILLER_CPUS') and os.environ.get('FILLER_DEADLINE')
B.mkdir(parents=True,exist_ok=True)
result=B/(a.mode+'-result.json'); log=B/'ws58-launcher.out'; started=time.time();peak=0;commands=[]
if a.mode=='full' and (log.exists() or (B/'buildcpu').exists() or (B/'buildgpu').exists() or (B/'native-units.jsonl').exists()):
 raise ValueError('full run requires fresh scratch build and witness log')
def git(*args):return subprocess.check_output(['git','-C',str(S),*args],text=True).strip()
def source_check():
 assert git('rev-parse','HEAD')==COMMIT,'source changed'
 assert git('rev-parse','HEAD^{tree}')=='a7c564ffbac0a86ce648ef6f11c1748c81a6560d','source tree changed'
 assert git('branch','--show-current').startswith('experimental/'),'not experimental'
 assert not git('status','--porcelain','--untracked-files=all'),'source dirty'
source_check()
def input_check():
 pins={'production-recipe.json':'74a2544c1b953a95df302295bdbb83fef9ccd26f37c7868989546f26e6d96496',
       'replay_evidence.py':'640540abc50af9c1024bd3296e3a1d11e6c90c3fdaa2c2204d483e243ac0c596',
       'replay_hip_cuid.py':'7544154cc8dbefd2b09de6b14a9a12efa7569407d1ad43f0df430fcd66673d01',
       'compare_symbols.py':'08a5e9e15f8ac07d573d8e0c8c38ec4aef6d78820032ec4e2eb0325a3447bf61',
       'comparator-dependencies.json':('5adb079828658d11dd393fa61f3e59712872ae635102c2543c7c9d8823c927fd','5350aac873b0b3626851912dc44c1d3579467edacb6a999e4acfd70f83a587fd')}
 for name, digest in pins.items():
  if hashlib.sha256((INPUTS/name).read_bytes()).hexdigest() not in (digest if isinstance(digest,tuple) else (digest,)): raise ValueError('pinned build input changed: '+name)
input_check()
env=dict(os.environ,PATH='/usr/bin:/bin',LD_LIBRARY_PATH='',OMP_NUM_THREADS='1',HIP_VISIBLE_DEVICES='',ROCR_VISIBLE_DEVICES='',CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
cmake='/usr/bin/cmake';tool=pathlib.Path('/usr')
recipe=json.loads((INPUTS/'production-recipe.json').read_text())
CUID=INPUTS/'CUID-RECIPES.json'; CUID_SHA='89cdaffdd58b9a8a624c5e79b7d477b82b626640876694f5fa5654a73d874aa4'
assert hashlib.sha256(CUID.read_bytes()).hexdigest()==CUID_SHA, 'CUID recipe manifest changed'
def interrupted(signum,frame):raise SystemExit(75)
signal.signal(signal.SIGTERM,interrupted)
signal.signal(signal.SIGINT,interrupted)
def finish(rc,reason,partial=False,comparison=None):
 source_check()
 result.write_text(json.dumps({'source':str(S),'commit':COMMIT,'mode':a.mode,'partial':partial,'reason':reason,'exit_code':rc,'peak_rss_kib':peak,'wall_s':time.time()-started,'cpus':os.environ['FILLER_CPUS'],'gpu_visibility':{k:env[k] for k in ('HIP_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','CUDA_VISIBLE_DEVICES')},'commands':commands,'comparison':comparison},indent=2)+'\n')
 raise SystemExit(rc)
def group_rows(pid):
 out=subprocess.check_output(['ps','-eo','pid=,pgid=,rss=,stat='],text=True)
 return [x.split() for x in out.splitlines() if len(x.split())==4 and int(x.split()[1])==pid]
def stop(child):
 for sig in (signal.SIGTERM,signal.SIGKILL):
  try:os.killpg(child.pid,sig)
  except ProcessLookupError:pass
  try:child.wait(timeout=3)
  except subprocess.TimeoutExpired:continue
  live=[x for x in group_rows(child.pid) if not x[3].startswith('Z')]
  if not live:return
 assert not [x for x in group_rows(child.pid) if not x[3].startswith('Z')], 'owned children survive'
def run(cmd,cutoff=False, allowed=(0,)):
 global peak
 commands.append(cmd)
 deadline=min(float(os.environ['FILLER_DEADLINE'])-3,time.time()+(.6 if cutoff else 900 if a.mode!='full' else 1e9))
 with log.open('ab') as f:
  f.write(('COMMAND '+json.dumps(cmd)+'\n').encode());f.flush()
  child=subprocess.Popen(['taskset','-c',os.environ['FILLER_CPUS'],*cmd],cwd=B,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  try:
   while child.poll() is None:
    rows=group_rows(child.pid);rss=sum(int(x[2]) for x in rows);peak=max(peak,rss)
    witness=[]
    for x in rows:
     try: cmdline=pathlib.Path('/proc')/x[0]/'cmdline'; witness.append({'pid':int(x[0]),'rss_kib':int(x[2]),'cmd':cmdline.read_bytes().replace(b'\0',b' ').decode(errors='replace')})
     except OSError:pass
    with (B/(a.mode+'-rss.jsonl')).open('a') as wf:wf.write(json.dumps({'time':time.time(),'rss_kib':rss,'processes':witness})+'\n')
    reason=None
    if time.time()>=deadline or os.environ.get('FILLER_STOPFILE') and pathlib.Path(os.environ['FILLER_STOPFILE']).exists():reason='window_cutoff'
    if rss>(8 if a.mode!='full' else 32)*1024*1024:reason='sampled_ram_cap'
    if log.stat().st_size>64*1024*1024:reason='log_cap'
    if shutil.disk_usage(B).free<(150+16)*1024**3:reason='disk_floor'
    usage=subprocess.run(['du','-sk',str(B)],text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,check=False).stdout.split()
    if usage and int(usage[0])>16*1024*1024:reason='output_cap'
    if reason:stop(child);finish(75,reason,True)
    time.sleep(.1 if cutoff else .5)
   if child.returncode not in allowed:finish(child.returncode,'command_failed',True)
   return child.returncode
  finally:
   if child.poll() is None or any(not x[3].startswith('Z') for x in group_rows(child.pid)):stop(child)

def configure(kind):
 target=B/('build'+kind)
 defs=recipe[kind]['configure_definitions']
 args=[f'-D{k}:{v["type"]}={v["value"]}' for k,v in defs.items()]
 for lang,exe in [('C','cc'),('CXX','c++')]:
  args += [f'-DCMAKE_{lang}_COMPILER={tool/"bin"/exe}',f'-DCMAKE_{lang}_COMPILER_AR={tool/"bin/gcc-ar-15"}',f'-DCMAKE_{lang}_COMPILER_RANLIB={tool/"bin/gcc-ranlib-15"}']
 if kind=='gpu':
  args+=['-DCMAKE_HIP_COMPILER=/opt/rocm/lib/llvm/bin/clang++']
  launcher=['/usr/bin/python3',str(INPUTS/'replay_hip_cuid.py'),'--manifest',str(CUID),'--manifest-sha256',CUID_SHA,'--source-root',str(S),'--output-root',str(target)]
  args+=['-DCMAKE_HIP_COMPILER_LAUNCHER:STRING='+';'.join(launcher)]
 if not (target/'CMakeCache.txt').exists():run([cmake,'-S',str(S),'-B',str(target),'-G','Unix Makefiles',*args])
 return target
threads=2  # R14 command-same-recipe qualification is fixed at two threads; no speed claim.
cpu=configure('cpu')
if a.mode=='configure':configure('gpu');finish(0,'cpu_hip_cache_configured_no_compile')
if a.mode=='cutoff':run([cmake,'--build',str(cpu),'--target','ggml-cpu','-j','1'],cutoff=True);finish(1,'cutoff_target_finished_unexpectedly')
if a.mode=='smoke':
 gpu=configure('gpu')
 cpu_obj=cpu/'ggml/src/CMakeFiles/ggml-base.dir/gguf.cpp.o'
 hip_relative='ggml/src/ggml-hip/CMakeFiles/ggml-hip.dir/__/ggml-cuda/acc.cu.o'
 hip_obj=gpu/hip_relative
 for obj in (cpu_obj,hip_obj):
  if obj.exists():obj.unlink()
 run([cmake,'--build',str(cpu),'--target','ggml-base','-j','1'])
 run(['/usr/bin/gmake','-C',str(gpu),'-f','ggml/src/ggml-hip/CMakeFiles/ggml-hip.dir/build.make',hip_relative,'-j1'])
 assert hip_obj.is_file() and hip_obj.stat().st_size>64,'no real HIP object'
 sections=subprocess.check_output(['readelf','-S',str(hip_obj)],text=True)
 assert '.hip_fatbin' in sections,'HIP code object container absent'
 (B/'hip-object-sections.txt').write_text(sections)
 objects=[cpu_obj,hip_obj];assert all(x.exists() for x in objects),'no real source objects'
 (B/'object-witness.json').write_text(json.dumps([{'path':str(x),'size':x.stat().st_size,'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in objects],indent=2)+'\n')
 finish(0,'real_cpu_source_and_gfx90a_hip_object')
run([cmake,'--build',str(cpu),'--target','ggml-cpu','-j',str(threads)])
cpu_lib=cpu/'bin/libggml-cpu.so'
assert cpu_lib.is_file() and cpu_lib.stat().st_size>64, 'completed CPU target has no library'
with (D/'native-units.jsonl').open('a') as f:
 f.write(json.dumps({'schema':'r18a.native-unit.v1','kind':'cpu-build-complete','artifact':str(cpu_lib),'sha256':hashlib.sha256(cpu_lib.read_bytes()).hexdigest()})+'\n'); f.flush(); os.fsync(f.fileno())
gpu=configure('gpu')
run([cmake,'--build',str(gpu),'--target','ggml-cpu','ggml-hip','-j',str(threads)])
# Every retained TU must have actually passed through the pinned launcher in this fresh build.
proof=evidence.verify_replay(log,CUID,CUID_SHA,gpu)
(B/'hip-replay-witness.json').write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
deps=json.loads((INPUTS/'comparator-dependencies.json').read_text())
before=evidence.comparison_hashes(cpu,gpu,deps)
(B/'comparison-inputs-before.json').write_text(json.dumps(before,indent=2,sort_keys=True)+'\n')
env['R18_SYMBOL_RESULT']=str(B/'symbol-identity.json')
# Start before comparator, and bind exact source, toolchain, comparator and both build arms.
capture_dir=B/'belief-symbol-finding'
inputs={'comparator':evidence.COMPARATOR,'anchor_cpu':evidence.ANCHORS/'cpu-20260921-ffc1bac82/bin/libggml-cpu.so',
 'anchor_hip':evidence.ANCHORS/'gpu-20260921-ffc1bac82/bin/libggml-hip.so','candidate_cpu':cpu/'bin/libggml-cpu.so',
 'candidate_hip':gpu/'bin/libggml-hip.so','cpu_compiler':'/usr/bin/cc','cxx_compiler':'/usr/bin/c++',
 'hip_compiler':'/opt/rocm/lib/llvm/bin/clang++','cmake':cmake,'recipe':INPUTS/'production-recipe.json',
 'cuid_manifest':CUID,'replay_witness':B/'hip-replay-witness.json','driver':__file__,
 'writer':PRODUCERS/'r18_symbol_capture.py','capture_cli':PRODUCERS/'r18_symbol_capture_cli.py',
 'set_extractor':PRODUCERS/'r18_symbol_sets.py','wrapper':PRODUCERS/'r18_run_full_successor.py',
 'evidence_checker':INPUTS/'replay_evidence.py','cuid_launcher':INPUTS/'replay_hip_cuid.py'}
input_check()
belief.begin(capture_dir, B/'symbol-identity.json', S, inputs, INPUTS/'comparator-dependencies.json', commands, build_env=env)

rc=run(['bash','-c','exec "$@" > "$R18_SYMBOL_RESULT"','r18-comparator','/usr/bin/python3',str(evidence.COMPARATOR),'--anchor-build',str(evidence.ANCHORS/'gpu-20260921-ffc1bac82'),'--anchor-cpu-build',str(evidence.ANCHORS/'cpu-20260921-ffc1bac82'),'--candidate-build',str(gpu),'--candidate-cpu-build',str(cpu)],allowed=(0,1))
after=evidence.comparison_hashes(cpu,gpu,deps)
(B/'comparison-inputs-after.json').write_text(json.dumps(after,indent=2,sort_keys=True)+'\n')
if before != after: raise ValueError('comparison inputs changed during comparator execution')
passed=evidence.validate_comparison(json.loads((B/'symbol-identity.json').read_text()),rc,after,cpu,gpu)
# Separate guarded child: deadline, STOP, process-group drain and resource caps apply.
run(['/usr/bin/python3', str(PRODUCERS/'r18_symbol_capture_cli.py'), str(capture_dir), str(rc)])
finish(rc,'independent_cpu_hip_symbol_identity_pass' if passed else 'independent_cpu_hip_symbol_identity_valid_negative',comparison={'rc':rc,'path':str(B/'symbol-identity.json'),'sha256':evidence.sha(B/'symbol-identity.json')})
