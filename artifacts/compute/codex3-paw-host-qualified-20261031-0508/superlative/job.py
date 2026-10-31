#!/usr/bin/env python3
import datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
import psutil,owned_drain,real_admission,smoke_admission,write_capture
D=Path(__file__).resolve().parent; PYTHON=D/'.venv/bin/python'; DECL=D/'PREDECLARATION.json'; MODEL=Path('/mnt/raid0/llm/models/PAW-Qwen3-0.6B-Q6K-acb0cea5/qwen3-0.6b-q6_k.gguf');ID='codex3-paw-superlative-hostfix2-20261031';STOP=Path('/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/paw-repair/super-host2/STOP')
class Cutoff(Exception):pass
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
 if mode not in ('real','smoke'):raise ValueError('mode')
 subprocess.run(['/usr/bin/sha256sum','-c',str(D/'SOURCES.sha256')],cwd=D,check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['/usr/bin/sha256sum','-c',str(D/'RUNTIME-SOURCES.sha256')],cwd=D,check=True,stdout=subprocess.DEVNULL)
 cpus=os.sched_getaffinity(0);check=real_admission.capture() if mode=='real' else lambda:smoke_admission.check(cpus)
 if not check() or owned_drain.children():raise RuntimeError('admission or child custody refused')
 owned_drain.enable();stopped=[False]
 for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,lambda *_:stopped.__setitem__(0,True))
 deadline=int(os.environ['FILLER_DEADLINE'] if mode=='real' else os.environ['PAW_SMOKE_DEADLINE']);started=time.monotonic()
 epoch=D/('epoch' if mode=='real' else 'smoke-epoch-'+os.environ.get('PAW_SMOKE_NAME','default'));epoch.mkdir(exist_ok=True);state_path=epoch/'state.json';decl=json.loads(DECL.read_text());ds=digest(DECL);ms=digest(D/'SOURCES.sha256')
 state=json.loads(state_path.read_text()) if state_path.exists() else {'schema':'paw-scope-checkpoint/v1','programs':decl['programs'],'declaration_sha256':ds,'source_manifest_sha256':ms}
 if state.get('declaration_sha256')!=ds or state.get('source_manifest_sha256')!=ms or state.get('programs')!=decl['programs']:raise ValueError('checkpoint identity changed')
 for item in state['programs'].values():
  if digest(item['path'])!=item['sha256']:raise ValueError('program pin mismatch')
 if not state_path.exists():put(state_path,state)
 run_root=D/'results';run_root.mkdir(exist_ok=True)
 if mode=='real':
  if 'run' not in state:run=run_root/('real-'+str(time.time_ns()));run.mkdir();state['run']=str(run);put(state_path,state)
  else:run=Path(state['run']).resolve(strict=True)
  if not run.is_relative_to(run_root):raise ValueError('invalid run path')
 else:run=D/'smoke-results'/('job-'+str(time.time_ns()));run.mkdir(parents=True)
 env={k:v for k,v in os.environ.items() if k in ('HOME','PATH','LANG','LC_ALL','TZ')};env.update(PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='',HIP_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',LD_LIBRARY_PATH=str((D/'.venv/lib/python3.13/site-packages/llama_cpp/lib').resolve()))
 for path in (D,MODEL):
  st=os.statvfs(path)
  if st.f_bavail*st.f_frsize<151*1024**3:raise RuntimeError('disk reservation not available')
 proc=psutil.Process();peak=0;samples=0
 def tick():
  nonlocal peak,samples
  if stopped[0] or time.time()>=deadline or STOP.exists():raise Cutoff('window cutoff')
  if not check():raise RuntimeError('admission lost')
  for path in (D,MODEL):
   st=os.statvfs(path)
   if st.f_bavail*st.f_frsize<150*1024**3:raise RuntimeError('disk floor crossed')
  total=0
  for c in [proc]+proc.children(recursive=True):
   try:total+=c.memory_info().rss
   except psutil.NoSuchProcess:pass
  peak=max(peak,total);samples+=1
  if mode=='smoke' and total>8*1024**3:raise RuntimeError('8 GiB smoke limit exceeded')
 def wait(child):
  while child.poll() is None:tick();time.sleep(.1)
  if child.returncode:raise RuntimeError(f'child rc={child.returncode}')
 def evaluate(case,path):
  with path.open('xb') as log:child=subprocess.Popen([str(PYTHON),str(D/'evaluate_pair.py'),state['programs']['binary']['path'],state['programs']['semantic']['path'],str(case)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  wait(child);lines=[x for x in path.read_text().splitlines() if x.startswith('{')]
  if len(lines)!=1:raise RuntimeError('missing paired output')
  return json.loads(lines[0])
 try:
  if mode=='smoke':
   row=evaluate(D/'SMOKE-CASE.json',run/'control.output.log');put(run/'control-result.json',row);raise Cutoff('noncohort pair completed')
  for case in decl['cases']:
   tick();key=str(case['source_row']);done=run/f'{key}.complete.json';exposed=run/f'{key}.exposed.json'
   if done.exists():continue
   if exposed.exists():continue  # retained exposed-unknown: never redraw, advance other cases
   grant=Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(ID+'.grant');raw=grant.read_bytes();grant_path=run/f'{key}.{time.time_ns()}.grant.snapshot'
   with grant_path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
   grant_hash=hashlib.sha256(raw).hexdigest();write_capture.expose(run,key,grant_path,grant_hash);case_path=run/f'{key}.case.json';put(case_path,case);row=evaluate(case_path,run/f'{key}.output.log');tick()
   if grant.read_bytes()!=raw:raise RuntimeError('case grant changed')
   row.update(measured_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),cpu_affinity=sorted(cpus),grant_snapshot_path=str(grant_path),grant_sha256=grant_hash);write_capture.save_case(run,row)
  missing=[c for c in decl['cases'] if not (run/f"{c['source_row']}.complete.json").exists()]
  if missing:
   dispositions=[{'source_row':c['source_row'],'case_sha256':c['case_sha256'],'disposition':'complete' if (run/f"{c['source_row']}.complete.json").exists() else 'exposed_unknown_no_redraw' if (run/f"{c['source_row']}.exposed.json").exists() else 'not_exposed'} for c in decl['cases']]
   incomplete={'status':'INCOMPLETE','reason':'one or more cases exposed without completed paired output; no redraw','run':str(run),'declaration_sha256':ds,'source_manifest_sha256':ms,'case_dispositions':dispositions}
   incomplete_path=run/'native-incomplete.json'
   if incomplete_path.exists():
    if json.loads(incomplete_path.read_text())!=incomplete:raise ValueError('incomplete record changed on resume')
   else:write_capture.write_once(incomplete_path,incomplete)
   put(D/'TERMINAL-INCOMPLETE.json',{'run':str(run),'status':'INCOMPLETE'});result={'partial':True,'status':'INCOMPLETE','run':str(run)};rc=75
   raise Cutoff('terminal incomplete; no redraw')
  grant=Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(ID+'.grant');snapshot=run/'grant.snapshot'
  with snapshot.open('xb') as f:f.write(grant.read_bytes());f.flush();os.fsync(f.fileno())
  meta={'completed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cpu_affinity':sorted(cpus),'source_manifest_path':str(D/'SOURCES.sha256'),'source_manifest_sha256':digest(D/'SOURCES.sha256'),'grant_snapshot_path':str(snapshot),'grant_sha256':digest(snapshot),'model_path':str(MODEL),'model_sha256':digest(MODEL),'program_paths':{k:v['path'] for k,v in state['programs'].items()},'program_sha256':{k:v['sha256'] for k,v in state['programs'].items()}}
  write_capture.finish(run,meta);put(D/'DONE',{'run':str(run)});result={'partial':False,'status':'complete','run':str(run)};rc=0
 except Cutoff as e:
  if mode=='smoke' and os.environ.get('PAW_CONTROL_NORMAL')=='1' and str(e)=='noncohort pair completed':result={'partial':False,'status':'engineering_control_complete','reason':str(e),'state':str(state_path),'run':str(run),'noncohort':True};rc=0
  elif (D/'TERMINAL-INCOMPLETE.json').exists():result={'partial':True,'status':'INCOMPLETE','reason':str(e),'state':str(state_path),'run':str(run)};rc=75
  else:result={'partial':True,'status':'partial','reason':str(e),'state':str(state_path),'run':str(run)};rc=75
 except Exception as e:result={'partial':True,'status':'failed','reason':repr(e),'state':str(state_path),'run':str(run)};rc=1
 finally:owned_drain.drain()
 result.update(wall_s=time.monotonic()-started,sampled_peak_rss_bytes=peak,rss_samples=samples,children_drained=True);put(run/'job-result.json',result);print(json.dumps(result),flush=True);return rc
if __name__=='__main__':
 if len(sys.argv)!=4 or sys.argv[2]!='--epyc-root':raise SystemExit('usage: job.py MODE --epyc-root ROOT')
 if Path(sys.argv[3]).resolve(strict=True)!=Path(os.environ['EPYC_ROOT']).resolve(strict=True):raise SystemExit('epyc-root identity mismatch')
 sys.exit(main(sys.argv[1]))
