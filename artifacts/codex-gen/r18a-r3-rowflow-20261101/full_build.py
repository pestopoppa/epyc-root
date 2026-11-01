#!/usr/bin/env python3
import argparse,hashlib,json,os,pathlib,signal,subprocess,time,sys,shutil,uuid,stat
import rowflow_unit
D=pathlib.Path(__file__).resolve().parent
P=pathlib.Path('/mnt/raid0/llm/tmp/refactor-r18a-v10-independent-symbols-r3-20261101-candidate-b7')
COMMIT='ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--scratch',required=True);p.add_argument('--mode',choices=['smoke','cutoff','configure','full'],required=True);a=p.parse_args()
S=pathlib.Path(a.source); B=pathlib.Path(a.scratch)
assert str(B).startswith(str(D/'scratch')+'/'), 'private scratch only'
assert os.environ.get('FILLER_CPUS') and os.environ.get('FILLER_DEADLINE')
B.mkdir(parents=True,exist_ok=True)
result=B/(a.mode+'-result.json'); log=B/'ws58-launcher.out'; started=time.time();started_ns=time.time_ns();peak=0;commands=[]
run_id=uuid.uuid4().hex
dryrun=os.environ.get('FILLER_DRYRUN')=='1'
dryrun_dir=pathlib.Path(os.environ['FILLER_DRYRUN_DIR']) if dryrun and os.environ.get('FILLER_DRYRUN_DIR') else None
rowflow_result_root=pathlib.Path(os.environ['R18_ROWFLOW_RESULT_ROOT']) if os.environ.get('R18_ROWFLOW_RESULT_ROOT') else None
first_cpu_unit=None;comparison_started_ns=None;comparison_returncode=None
def git(*args):return subprocess.check_output(['git','-C',str(S),*args],text=True).strip()
def source_check():
 assert git('rev-parse','HEAD')==COMMIT,'source changed'
 assert git('rev-parse','HEAD^{tree}')=='a7c564ffbac0a86ce648ef6f11c1748c81a6560d','source tree changed'
 assert git('branch','--show-current').startswith('experimental/'),'not experimental'
 assert not git('status','--porcelain','--untracked-files=all'),'source dirty'
env=dict(os.environ,PATH='/usr/bin:/bin',LD_LIBRARY_PATH='',OMP_NUM_THREADS='1',HIP_VISIBLE_DEVICES='',ROCR_VISIBLE_DEVICES='',CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
cmake='/usr/bin/cmake';tool=pathlib.Path('/usr')
recipe=json.loads((D/'production-recipe.json').read_text())
CUID=D/'CUID-RECIPES.json'; CUID_SHA='89cdaffdd58b9a8a624c5e79b7d477b82b626640876694f5fa5654a73d874aa4'
assert hashlib.sha256(CUID.read_bytes()).hexdigest()==CUID_SHA, 'CUID recipe manifest changed'
def interrupted(signum,frame):raise SystemExit(75)
signal.signal(signal.SIGTERM,interrupted)
signal.signal(signal.SIGINT,interrupted)
def digest_or_none(path):
 path=pathlib.Path(path)
 try:
  st=path.lstat()
  return hashlib.sha256(path.read_bytes()).hexdigest() if stat.S_ISREG(st.st_mode) else None
 except OSError:return None
def provenance():
 return {'source_root':str(S),'source_commit':COMMIT,'source_tree':'a7c564ffbac0a86ce648ef6f11c1748c81a6560d',
  'source_claim_sha256':digest_or_none(D/'SOURCE-CLAIM.json'),
  'source_manifest_sha256':digest_or_none(D/'SOURCE-MANIFEST.sha256'),
  'production_recipe_sha256':digest_or_none(D/'production-recipe.json'),
  'request_sha256':digest_or_none(D/'request.json'),
  'cuid_manifest_sha256':digest_or_none(CUID),
  'cuid_utility_source_sha256':digest_or_none(D/'CUID-UTILITY-SOURCE.json'),
  'verified_anchor_inputs_sha256':digest_or_none(D/'verified-anchor-inputs.json'),
  'verified_anchor_closure_sha256':digest_or_none(D/'verified-anchor-closure.json'),
  'comparator_source_sha256':digest_or_none(P/'compare_symbols.py')}
def finish(rc,reason,partial=False):
 global comparison_returncode
 source_error=None
 try:source_check()
 except Exception as exc:source_error=f'{type(exc).__name__}: {exc}'
 if source_error:
  if rc==0:rc=65
  partial=True;reason=reason+'; source_identity_check_failed: '+source_error
 comparison=rowflow_unit.comparison_outcome(B/'symbol-identity.json',comparison_started_ns,comparison_returncode) if a.mode=='full' else {'state':'not_applicable','returncode':None,'path':None,'sha256':None,'record':None}
 can_complete=(a.mode=='full' and rowflow_unit.completion_eligible(exit_code=rc,partial=partial,comparison=comparison))
 state=('complete' if can_complete else 'partial' if partial else 'failed' if rc else 'comparison_not_passed')
 record={'schema':rowflow_unit.FULL_RESULT_SCHEMA if a.mode=='full' else 'epyc.r18a.build_result.v1',
  'run_id':run_id,'source':str(S),'commit':COMMIT,'mode':a.mode,'partial':partial,'reason':reason,'exit_code':rc,
  'completion_eligible':can_complete,'terminal_state':state,'source_identity_check':{'ok':source_error is None,'error':source_error},
  'provenance':provenance(),'first_cpu_compile_unit':first_cpu_unit,'comparison':comparison,
  'peak_rss_kib':peak,'wall_s':time.time()-started,'started_at_ns':started_ns,
  'cpus':os.environ.get('FILLER_CPUS'),'gpu_visibility':{k:env[k] for k in ('HIP_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES','CUDA_VISIBLE_DEVICES')},
  'commands':commands}
 if a.mode=='full' and dryrun:
  if dryrun_dir is None or rowflow_result_root is None:raise SystemExit('dry-run directories missing; refusing unfiled rowflow output')
  terminal={'schema':'epyc.r18a.dryrun_terminal.v1','run_id':run_id,'state':state,'reason':reason,'exit_code':rc,
   'partial':partial,'comparison_state':'not_run','first_cpu_compile_unit':first_cpu_unit,'provenance':provenance()}
  rowflow_unit.write_json_atomic(dryrun_dir/'R18A-DRYRUN-TERMINAL.json',terminal)
 elif a.mode=='full':
  if rowflow_result_root is None:raise SystemExit('R18_ROWFLOW_RESULT_ROOT missing; refusing unfiled full result')
  rowflow_unit.write_json_atomic(result,record)
  filed_path=rowflow_result_root/'full'/run_id/'terminal.jsonl'
  terminal={'schema':rowflow_unit.FULL_TERMINAL_SCHEMA,'run_id':run_id,'state':state,'reason':reason,
   'partial':partial,'exit_code':rc,'completion_eligible':can_complete,'comparison':comparison,
   'first_cpu_compile_unit':first_cpu_unit,'provenance':record['provenance'],
   'full_result_path':str(result),'full_result_sha256':digest_or_none(result),'full_result':record,
   'rowflow_result_file':str(filed_path)}
  filing_ok=False
  try:
   rowflow_unit.append_jsonl(filed_path,terminal);filing_ok=True
  except Exception as exc:
   print(f'ROWFLOW_RESULT_WRITE_FAILED {type(exc).__name__}: {exc}',file=sys.stderr,flush=True)
   rc=70;partial=True;reason=reason+'; rowflow_result_write_failed'
   record.update(exit_code=rc,partial=True,reason=reason,completion_eligible=False,terminal_state='failed',rowflow_result_write_error=f'{type(exc).__name__}: {exc}')
   rowflow_unit.write_json_atomic(result,record)
  terminal.update(rowflow_result_filed=filing_ok,full_result_sha256=digest_or_none(result),full_result=record,
   exit_code=rc,partial=partial,reason=reason,completion_eligible=bool(filing_ok and can_complete),
   state='complete' if filing_ok and can_complete else 'partial' if partial else 'failed' if rc else 'comparison_not_passed')
  rowflow_unit.append_jsonl(B/'full-terminal.jsonl',terminal)
 else:
  rowflow_unit.write_json_atomic(result,record)
 raise SystemExit(rc)
try:source_check()
except Exception as exc:finish(65,f'initial_source_identity_check_failed:{type(exc).__name__}:{exc}',True)
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
def run(cmd,cutoff=False):
 global peak,comparison_returncode
 is_comparison=any('compare_symbols.py' in str(x) for x in cmd)
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
   if child.returncode:
    if is_comparison:comparison_returncode=child.returncode
    finish(child.returncode,'command_failed')
   if is_comparison:comparison_returncode=0
  finally:
   if child.poll() is None:stop(child)

def configure(kind):
 target=B/('build'+kind)
 defs=recipe[kind]['configure_definitions']
 args=[f'-D{k}:{v["type"]}={v["value"]}' for k,v in defs.items()]
 for lang,exe in [('C','cc'),('CXX','c++')]:
  args += [f'-DCMAKE_{lang}_COMPILER={tool/"bin"/exe}',f'-DCMAKE_{lang}_COMPILER_AR={tool/"bin/gcc-ar-15"}',f'-DCMAKE_{lang}_COMPILER_RANLIB={tool/"bin/gcc-ranlib-15"}']
 if kind=='gpu':
  args+=['-DCMAKE_HIP_COMPILER=/opt/rocm/lib/llvm/bin/clang++']
  launcher=['/usr/bin/python3',str(D/'replay_hip_cuid.py'),'--manifest',str(CUID),'--manifest-sha256',CUID_SHA,'--source-root',str(S),'--output-root',str(target)]
  args+=['-DCMAKE_HIP_COMPILER_LAUNCHER:STRING='+';'.join(launcher)]
 if not (target/'CMakeCache.txt').exists():run([cmake,'-S',str(S),'-B',str(target),'-G','Unix Makefiles',*args])
 return target
def compile_cpu_first_unit(cpu):
 obj=cpu/rowflow_unit.CPU_OBJECT_REL
 if obj.is_symlink():raise RuntimeError('refusing symlinked pre-existing CPU object')
 if obj.exists():
  if not obj.is_file():raise RuntimeError('refusing non-regular pre-existing CPU object')
  obj.unlink()
 makefile=cpu/rowflow_unit.CPU_MAKEFILE_REL
 target=str(rowflow_unit.CPU_OBJECT_REL)
 src=str((S/rowflow_unit.CPU_SOURCE_REL).resolve())
 rules=[line for line in makefile.read_text().splitlines() if line.startswith(target+':')]
 if not rules or src not in rules[0]:raise RuntimeError('generated make rule is not bound to pinned gguf.cpp')
 started_ns=time.time_ns()
 command=['/usr/bin/gmake','-C',str(cpu),'-f',str(rowflow_unit.CPU_MAKEFILE_REL),target,'-j1']
 run(command)
 source_check()
 return rowflow_unit.cpu_compile_record(source=S,build=cpu,scratch_root=B,recipe_path=D/'production-recipe.json',
  source_commit=git('rev-parse','HEAD'),source_tree=git('rev-parse','HEAD^{tree}'),
  compiler_path=tool/'bin/c++',started_ns=started_ns,command=command,command_returncode=0,
  output_removed_before=True)
threads=2  # R14 command-same-recipe qualification is fixed at two threads; no speed claim.
cpu=configure('cpu')
if a.mode=='full':
 try:unit=compile_cpu_first_unit(cpu)
 except Exception as exc:finish(70,f'cpu_first_unit_failed:{type(exc).__name__}:{exc}',True)
 first_cpu_unit=unit
 print('ROWFLOW_UNIT '+json.dumps(unit,sort_keys=True,separators=(',',':')),flush=True)
 if dryrun:
  if dryrun_dir is None:finish(70,'FILLER_DRYRUN_DIR missing; refusing non-isolated unit output',True)
  if rowflow_result_root is None:finish(70,'R18_ROWFLOW_RESULT_ROOT missing; refusing unfiled dry-run unit',True)
  unit_path=rowflow_result_root/'dryrun'/run_id/'cpu-unit.jsonl'
  rowflow_unit.append_jsonl(unit_path,unit)
  finish(75,'rowflow_first_cpu_compile_unit_complete',True)
 rowflow_unit.write_json_atomic(B/'cpu-first-unit.json',unit)
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
gpu=configure('gpu')
run([cmake,'--build',str(gpu),'--target','ggml-cpu','ggml-hip','-j',str(threads)])
env['R18_SYMBOL_RESULT']=str(B/'symbol-identity.json')
comparison_started_ns=time.time_ns()
run(['bash','-c','exec "$@" > "$R18_SYMBOL_RESULT"','r18-comparator','python3',str(P/'compare_symbols.py'),'--anchor-build','/mnt/raid0/llm/tmp/refactor-01a16fc3/r18a-verified-anchor-20261031/verified-v10-gpu','--anchor-cpu-build','/mnt/raid0/llm/tmp/refactor-01a16fc3/r18a-verified-anchor-20261031/verified-v10-cpu','--candidate-build',str(gpu),'--candidate-cpu-build',str(cpu)])
finish(0,'independent_cpu_hip_symbol_identity_pass')
