#!/usr/bin/env python3
"""PAW own-slice job: bounded compile checkpoints, case exposure and native capture."""
import datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
from urllib.request import urlopen
import psutil
import owned_drain, real_admission, smoke_admission, socket_owner, write_capture
D=Path(__file__).resolve().parent
PYTHON=D/'.venv/bin/python'
STORE=Path('/mnt/raid0/llm/models/PAW-programs')
MODEL=Path('/mnt/raid0/llm/models/PAW-Qwen3-0.6B-Q6K-acb0cea5/qwen3-0.6b-q6_k.gguf')
DECL=D/'PAW3-PREDECLARATION.json'
ID='codex3-paw-standard-a-resume-20261031'
class Cutoff(Exception): pass

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def put(path,obj):
 path=Path(path);tmp=path.with_name(path.name+f'.tmp-{os.getpid()}')
 with tmp.open('x') as f:json.dump(obj,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path);fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)

def main(mode):
 if mode not in ('real','smoke'): raise ValueError('mode')
 decl_path=D/'SMOKE-DECLARATION.json' if mode=='smoke' else DECL
 subprocess.run(['/usr/bin/sha256sum','-c',str(D/'SOURCES.sha256')],check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['/usr/bin/sha256sum','-c',str(D/'RUNTIME-SOURCES.sha256')],check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['/usr/bin/sha256sum','-c',str(D/'HOST-INTERPRETER.sha256')],check=True,stdout=subprocess.DEVNULL)
 initial_sources_sha=digest(D/'SOURCES.sha256')
 cpus=os.sched_getaffinity(0);check=real_admission.capture() if mode=='real' else lambda:smoke_admission.check(cpus)
 if not check() or owned_drain.children(): raise RuntimeError('admission or child custody refused')
 owned_drain.enable();stopped=[False]
 for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,lambda *_:stopped.__setitem__(0,True))
 deadline=int(os.environ['FILLER_DEADLINE'] if mode=='real' else os.environ['PAW_SMOKE_DEADLINE'])
 port=int(os.environ.get('FILLER_PORTS','19953')); started=time.monotonic()
 epoch=D/('epoch' if mode=='real' else 'smoke-epoch-'+os.environ.get('PAW_SMOKE_NAME','default'));epoch.mkdir(exist_ok=True)
 state_path=epoch/'state.json'
 if mode=='real' and not state_path.exists():
  origin=D/'ORIGINAL-STATE.json'
  if digest(origin)!='473a87778c5780082996e386ad5c2a4bed1617f28563515bd3e00f198b80fc57':raise ValueError('origin checkpoint mismatch')
  saved=json.loads(origin.read_text());original_result=json.loads(Path('/mnt/raid0/llm/tmp/codex3-paw-hsf-t1-20261030/A/results/real-1793419509204324996/job-result.json').read_text())
  if digest(Path('/mnt/raid0/llm/tmp/codex3-paw-hsf-t1-20261030/A/results/real-1793419509204324996/job-result.json'))!='4be4abc81e074f2d17e055c50c285c8b8c00d8e3f93508a747925460fe4f22f6':raise ValueError('origin result mismatch')
  if saved['declaration_sha256']!=digest(DECL) or saved['source_manifest_sha256']!=digest(D/'ORIGINAL-SOURCES.sha256'):raise ValueError('origin envelope mismatch')
  if set(saved['programs'])!={'0','1','2','3','7','8','9'} or any(x['disposition']!='not_exposed' for x in original_result['case_dispositions']) or len(original_result['case_dispositions'])!=64:raise ValueError('origin exposure mismatch')
  state={'schema':'paw3-checkpoint/v1','programs':saved['programs'],'origin_checkpoint_sha256':digest(origin),'origin_source_manifest_sha256':saved['source_manifest_sha256'],'origin_run':saved['run'],'origin_result_sha256':digest(Path('/mnt/raid0/llm/tmp/codex3-paw-hsf-t1-20261030/A/results/real-1793419509204324996/job-result.json'))}
 else:state=json.loads(state_path.read_text()) if state_path.exists() else {'schema':'paw3-checkpoint/v1','programs':{}}
 decl_sha=digest(decl_path)
 if state.get('declaration_sha256',decl_sha)!=decl_sha: raise ValueError('declaration changed')
 state['declaration_sha256']=decl_sha
 if state.get('source_manifest_sha256',initial_sources_sha)!=initial_sources_sha:raise ValueError('source manifest changed')
 state['source_manifest_sha256']=initial_sources_sha
 if not state_path.exists():put(state_path,state)
 for arm,item in state['programs'].items():
  if arm not in {str(i) for i in json.loads(decl_path.read_text())['task_indices']} or digest(item['path'])!=item['sha256']:raise ValueError('checkpoint program mismatch')
 run_root=D/'results';run_root.mkdir(exist_ok=True)
 if mode=='real':
  if 'run' not in state:
   run=run_root/('real-'+str(time.time_ns()));run.mkdir();state['run']=str(run);put(state_path,state)
  else:run=Path(state['run']).resolve(strict=True)
  if not run.is_relative_to(run_root):raise ValueError('invalid run path')
 else:
  run=D/'smoke-results'/('job-'+str(time.time_ns()));run.mkdir(parents=True)
 env={k:v for k,v in os.environ.items() if k in ('HOME','PATH','LANG','LC_ALL','TZ')}
 st=os.statvfs(STORE)
 if st.f_bavail*st.f_frsize < 166*1024**3:raise RuntimeError('insufficient disk for 16 GiB workspace and 150 GiB floor')
 scratch=os.statvfs(D)
 if scratch.f_bavail*scratch.f_frsize < 166*1024**3:raise RuntimeError('insufficient scratch disk for 16 GiB output and 150 GiB floor')
 store=STORE/('codex3-paw3-'+mode+'-'+str(time.time_ns()));store.mkdir()
 env.update(PAW_PROGRESS_LOG=str(run/'generation-progress.jsonl'),PAW_SMOKE_PSEUDO='1' if mode=='smoke' else '0',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',LD_LIBRARY_PATH=str((D/'.venv/lib/python3.13/site-packages/llama_cpp/lib').resolve()),PAW_OFFLOAD_DIR=str(store/'offload'),PAW_CACHE_DIR='/mnt/raid0/llm/models/PAW-runtime-cache')
 proc=psutil.Process();peak=0;samples=0;server=None;active_case=None
 def tick():
  nonlocal peak,samples
  if stopped[0] or time.time()>=deadline or Path('/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/paw-standard-a-continuation/STOP').exists():raise Cutoff('window cutoff')
  if not check():raise RuntimeError('admission lost')
  disk=os.statvfs(STORE)
  if disk.f_bavail*disk.f_frsize < 150*1024**3:raise RuntimeError('disk floor crossed')
  scratch=os.statvfs(D)
  if scratch.f_bavail*scratch.f_frsize < 150*1024**3:raise RuntimeError('scratch disk floor crossed')
  total=0
  for child in [proc]+proc.children(recursive=True):
   try:total+=child.memory_info().rss
   except psutil.NoSuchProcess:pass
  peak=max(peak,total);samples+=1
  if mode=='smoke' and total>8*1024**3:raise RuntimeError('8 GiB smoke limit exceeded')
 def wait(child):
  while child.poll() is None:
   tick()
   if server is not None and server.poll() is not None:raise RuntimeError('server exited')
   time.sleep(.1)
  if child.returncode:raise RuntimeError(f'child rc={child.returncode}')
 try:
  decl=json.loads(decl_path.read_text())
  if len(state['programs'])<len(decl['tasks']):
   with (run/('server-'+str(time.time_ns())+'.log')).open('xb') as log:
    server=subprocess.Popen([str(PYTHON),str(D/'pinned_server.py'),'--host','127.0.0.1','--port',str(port),'--data-dir',str(store)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   while True:
    tick()
    if server.poll() is not None:raise RuntimeError('server startup failed')
    if socket_owner.owns_loopback(server.pid,port):
     try:
      with urlopen(f'http://127.0.0.1:{port}/health',timeout=1) as response:
       if json.load(response).get('status')=='ok':break
     except OSError:pass
    time.sleep(.2)
   for index,task in zip(decl['task_indices'],decl['tasks'],strict=True):
    arm=str(index)
    if arm in state['programs']:continue
    tick();response_path=run/('task-'+arm+'-compile-'+str(time.time_ns())+'.json')
    with response_path.open('xb') as log:child=subprocess.Popen([str(PYTHON),str(D/'compile_request.py'),str(port),task['spec']],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    wait(child); response=json.loads(response_path.read_text());ident=response['program_id']
    if len(ident)!=20 or any(c not in '0123456789abcdef' for c in ident):raise ValueError('bad program id')
    while response.get('status')=='compiling':
     tick()
     with urlopen(f'http://127.0.0.1:{port}/api/v1/programs/{ident}',timeout=2) as stream:response=json.load(stream)
     time.sleep(.2)
    if response.get('status')!='compiled':raise RuntimeError('compiler failed')
    bundle=store/'programs'/ident/'bundle.paw'
    if not bundle.is_file():raise RuntimeError('missing bundle')
    state['programs'][arm]={'path':str(bundle),'sha256':digest(bundle)};put(state_path,state)
    if mode=='smoke':raise Cutoff('real first compile checkpoint')
  if mode=='smoke':raise Cutoff('checkpoint already present')
  for index,task in zip(decl['task_indices'],decl['tasks'],strict=True):
   for case in task['cases']:
    tick();key=write_capture.key(index,case);done=run/f'{key}.complete.json';exposed=run/f'{key}.exposed.json'
    if done.exists() or exposed.exists():continue
    grant=Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(ID+'.grant');raw=grant.read_bytes()
    grant_path=run/f'{key}.{time.time_ns()}.grant.snapshot'
    with grant_path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    grant_hash=hashlib.sha256(raw).hexdigest();write_capture.expose(run,index,case,grant_path,grant_hash);active_case=(index,case)
    case_path=run/f'{key}.case.json';put(case_path,case);output=run/f'{key}.output.log'
    with output.open('xb') as log:child=subprocess.Popen([str(PYTHON),str(D/'evaluate_standard.py'),state['programs'][str(index)]['path'],str(case_path)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    wait(child);lines=[x for x in output.read_text().splitlines() if x.startswith('{')]
    if len(lines)!=1:raise RuntimeError('missing native result')
    tick()
    if grant.read_bytes()!=raw:raise RuntimeError('case grant changed during evaluation')
    row=json.loads(lines[0]);row.update(measured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),cpu_affinity=sorted(cpus),grant_snapshot_path=str(grant_path),grant_sha256=grant_hash);write_capture.save_case(run,index,case,row);active_case=None
  manifest=D/'SOURCES.sha256'
  meta={'completed_at':state.setdefault('finalized_at',datetime.datetime.now(datetime.timezone.utc).isoformat()),'cpu_affinity':sorted(cpus),'source_manifest_path':str(manifest),'source_manifest_sha256':initial_sources_sha,'model_path':str(MODEL),'model_sha256':digest(MODEL),'programs':state['programs'],'origin_checkpoint_sha256':state.get('origin_checkpoint_sha256'),'origin_source_manifest_sha256':state.get('origin_source_manifest_sha256'),'origin_result_sha256':state.get('origin_result_sha256'),'origin_run':state.get('origin_run')};put(state_path,state)
  write_capture.finish(run,meta);put(D/'DONE',{'run':str(run)});result={'partial':False,'status':'finalized','run':str(run)};rc=0
 except Cutoff as e:
  if mode=='smoke' and os.environ.get('PAW_CONTROL_NORMAL')=='1' and str(e)=='real first compile checkpoint':result={'partial':False,'status':'engineering_control_complete','reason':str(e),'state':str(state_path),'run':str(run),'noncohort':True};rc=0
  else:result={'partial':True,'status':'partial','reason':str(e),'state':str(state_path),'run':str(run)};rc=75
 except Exception as e:
  if active_case is not None:
   index,case=active_case;failure=run/(write_capture.key(index,case)+'.failed.json')
   if not failure.exists():write_capture.write_once(failure,{'task_index':index,'source_row':case['source_row'],'case_sha256':case['case_sha256'],'disposition':'invalid_or_failed_no_redraw','reason':repr(e)})
  result={'partial':True,'status':'failed','reason':repr(e),'state':str(state_path),'run':str(run)};rc=1
 finally:owned_drain.drain()
 if result['partial']:
  declaration=json.loads(decl_path.read_text());result['case_dispositions']=[{'task_index':i,'source_row':c['source_row'],'case_sha256':c['case_sha256'],'disposition':('complete' if (run/(write_capture.key(i,c)+'.complete.json')).exists() else 'invalid_or_failed_no_redraw' if (run/(write_capture.key(i,c)+'.failed.json')).exists() else 'exposed_unknown_no_redraw' if (run/(write_capture.key(i,c)+'.exposed.json')).exists() else 'not_exposed')} for i,t in zip(declaration['task_indices'],declaration['tasks'],strict=True) for c in t['cases']]
 result.update(wall_s=time.monotonic()-started,sampled_peak_rss_bytes=peak,rss_samples=samples,children_drained=True)
 write_capture.write_once(run/('job-result-'+str(time.time_ns())+'.json'),result);put(run/'job-result.json',result);print(json.dumps(result),flush=True);return rc
if __name__=='__main__':
 if len(sys.argv)!=4 or sys.argv[2]!='--epyc-root':raise SystemExit('usage: job.py MODE --epyc-root ROOT')
 if Path(sys.argv[3]).resolve(strict=True)!=Path(os.environ['EPYC_ROOT']).resolve(strict=True):raise SystemExit('epyc-root identity mismatch')
 sys.exit(main(sys.argv[1]))
