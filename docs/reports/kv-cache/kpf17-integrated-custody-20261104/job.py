#!/usr/bin/env python3
"""Run existing Test 6 under in-test GDB mapping witnesses; correctness only."""
import hashlib,json,os,re,signal,subprocess,sys,time
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/kvfork/kpf17-integrated-custody-20261104');B=Path('/mnt/micron/rtg58-integrated-c5-a58b513ba-20261102')
SRC='/mnt/raid0/llm/tmp/kv-prefix-fork/rtg58-integrated-c5-20261102';HEAD='8952a0f693fb923918157eb25117641b74766230'
SOURCE_SHA='528e020b682b0dba1c251b2519d68033a01cd314a73b92f5778976cb56586612';TEST_SHA='2f30b4837ca838f7a974153542676fede2949f635cae648077409ccfb9e53856';MANIFEST_SHA='18b5468cf9b4865baf071e1dc7f2867130baa7bf57f33f23492e75d0ff5a0dfd'
MODEL=Path('/mnt/raid0/llm/lmstudio/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf');MODEL_SHA='0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');os.replace(t,p)
def birth(pid):return int(Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()[19])
def alive(pid,start):
 try:return birth(pid)==start
 except (FileNotFoundError,ProcessLookupError):return False
def ps_check(pid,start):
 p=subprocess.run(['/bin/ps','-p',str(pid),'-o','pid=,stat='],capture_output=True,text=True)
 return {'pid':pid,'birth_ticks':start,'ps_rc':p.returncode,'ps_stdout':p.stdout.strip(),'dead':p.returncode==1 and not p.stdout.strip()}

def preflight():
 nspid=[int(x) for x in next(line for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('NSpid:')).split()[1:]]
 if nspid!=[os.getpid()] or os.readlink('/proc/self')!=str(os.getpid()):raise ValueError('supervisor/proc PID namespace mismatch')
 if subprocess.check_output(['git','-C',SRC,'rev-parse','HEAD'],text=True).strip()!=HEAD:raise ValueError('source HEAD mismatch')
 if subprocess.check_output(['git','-C',SRC,'status','--porcelain','--untracked-files=no'],text=True):raise ValueError('source dirty')
 if hashlib.sha256(subprocess.check_output(['git','-C',SRC,'show',HEAD+':tests/test-save-load-state.cpp'])).hexdigest()!=SOURCE_SHA:raise ValueError('test source mismatch')
 if (B/'SOURCE-COMMIT').read_text().strip()!=HEAD or sha(B/'BINARIES.sha256')!=MANIFEST_SHA:raise ValueError('build seal mismatch')
 if sha(B/'bin/test-save-load-state')!=TEST_SHA or sha(MODEL)!=MODEL_SHA:raise ValueError('test binary or model mismatch')
 if sha('/usr/bin/gdb')!='3832cc070ae1716e322105d3b39fb398695e5f031c9d39224cf227a8c2b889f6':raise ValueError('GDB digest mismatch')
 if subprocess.run(['/usr/bin/gdb','--batch','-nx','-ex','set debuginfod enabled off','-ex','python import gdb,hashlib,json'],capture_output=True).returncode:raise ValueError('GDB Python unavailable')

def test6_smoke_unit(w,child):
 """Accept only the pinned witness emitted from inside the n_rs_seq=0 case."""
 if not isinstance(w,dict) or not child or w.get('error') is not None:return None
 if (w.get('pid'),w.get('birth_ticks'))!=child or w.get('nspid')!=[child[0]]:return None
 if w.get('exe')!=str((B/'bin/test-save-load-state').resolve()):return None
 entries=[x for x in w.get('entries',[]) if x.get('mode')==0]
 for sample in w.get('samples',[]):
  if sample.get('mode')!=0 or sample.get('point')!='decode_entry':continue
  if (sample.get('pid'),sample.get('birth_ticks'))!=child:continue
  if sample.get('model_path')!=str(MODEL.resolve()):continue
  raw=sample.get('maps_text')
  if not isinstance(raw,str) or hashlib.sha256(raw.encode()).hexdigest()!=sample.get('maps_sha256'):continue
  if not any(isinstance(e.get('monotonic_ns'),int) and e['monotonic_ns']<=sample.get('monotonic_ns',-1) for e in entries):continue
  libs=sample.get('libraries',{})
  required={'libggml.so.0.16.0','libggml-base.so.0.16.0','libggml-cpu.so.0.16.0','libllama.so.0.0.10448','libllama-common.so.0.0.10448'}
  if not isinstance(libs,dict) or not required.issubset({Path(x).name for x in libs}):continue
  return {'type':'native_test6_decode_entry','scope':'one observed Test-6 decode entry; not a full Test-6 result','test6_decode_entry_witnessed':1,'n_rs_seq':0,'pid':child[0],'birth_ticks':child[1],'source_commit':HEAD,'source_sha256':SOURCE_SHA,'test_sha256':TEST_SHA,'model_sha256':MODEL_SHA,'sample':sample}
 return None

def main():
 smoke=os.environ.get('FILLER_DRYRUN')=='1' or os.environ.get('FILLER_SMOKE')=='1';D.mkdir(parents=True,exist_ok=True)
 result={'schema':'epyc.kpf17.partial-custody.v1','status':'INVALID','qualification_only':smoke,'grant_id':os.environ.get('FILLER_ID'),'cpus':os.environ.get('FILLER_CPUS'),'source_commit':HEAD,'source_sha256':SOURCE_SHA,'test_sha256':TEST_SHA,'model_sha256':MODEL_SHA,'manifest_sha256':MANIFEST_SHA,'test_id':'test-save-load-state/Test-6','historical_run_retroactively_bound':False,'scope':'sequential live source advances before and after destination restore; no simultaneous in-flight operation','instrumentation':'GDB breakpoints on exact compiled Test-6 helper, decode and restore lambdas; correctness only','started_utc':time.time()}
 p=None;child=None;children={};log=D/('smoke.log' if smoke else 'test.log');interrupted=False;progress=False;stop_requested=False
 def on_signal(_s,_f):
  nonlocal interrupted
  interrupted=True
 signal.signal(signal.SIGTERM,on_signal);signal.signal(signal.SIGINT,on_signal)
 try:
  preflight()
  producer_pins={name:sha(D/name) for name in ('job.py','witness.py','complete.py')}
  result['producer_pins']=producer_pins
  result['supervisor_namespace']={'pid':os.getpid(),'nspid':[int(x) for x in next(line for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('NSpid:')).split()[1:]],'proc_self':os.readlink('/proc/self')}
  if not smoke:
   grant=Path(os.environ.get('FILLER_GRANTS_DIR','/mnt/raid0/llm/tmp/compute-flags/grants'))/(os.environ['FILLER_ID']+'.grant')
   data=grant.read_bytes()
   if not data or len(data)>1048576:raise ValueError('missing/invalid own grant receipt')
   (D/'grant.receipt').write_bytes(data);result['grant_sha256']=hashlib.sha256(data).hexdigest();result['grant_end']=os.environ['FILLER_END'];result['grant_deadline']=os.environ['FILLER_DEADLINE']
  for f in ['witness.json']:
   (D/f).unlink(missing_ok=True)
  env=dict(os.environ,LD_LIBRARY_PATH=str(B/'bin'),LD_DEBUG='libs')
  cmd=['/usr/bin/gdb','--batch','-nx','-ex','set confirm off','-ex','set startup-with-shell off','-ex','set auto-load python-scripts off','-ex','set disable-randomization off','-ex','set debuginfod enabled off','-ex','handle SIGTERM nostop noprint pass','-ex','source '+str(D/'witness.py'),'-ex','run','-ex','quit $_exitcode','--args',str(B/'bin/test-save-load-state'),'-m',str(MODEL),'-ngl','0','-t',str(min(4,len(os.sched_getaffinity(0)))),'-b','32','-c','1024','-n','8','--seed','1234']
  result.update(argv=cmd,gdb_sha256=sha('/usr/bin/gdb'),witness_source_sha256=sha(D/'witness.py'))
  with log.open('wb') as f:
   p=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,cwd=D);result['supervisor_pid']=p.pid;result['supervisor_birth_ticks']=birth(p.pid)
   with open(os.environ['FILLER_PIDFILE'],'a') as pf:pf.write(str(p.pid)+'\n')
   while p.poll() is None:
    for task in Path('/proc/%d/task'%p.pid).glob('*/children'):
     try:
      for item in task.read_text().split():
       pid=int(item)
       if pid not in children:
        children[pid]=birth(pid)
        with open(os.environ['FILLER_PIDFILE'],'a') as pf:pf.write(str(pid)+'\n')
     except (OSError,ProcessLookupError,ValueError):pass
    try:
     w=json.loads((D/'witness.json').read_text());pid=w.get('pid');bt=w.get('birth_ticks')
     if pid and bt:child=(int(pid),int(bt))
     if smoke and not progress and child and alive(*child):
      unit=test6_smoke_unit(w,child)
      if unit is not None:
       save(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']),unit);progress=True
    except (OSError,ValueError,KeyError,json.JSONDecodeError):pass
    if interrupted or Path(os.environ['FILLER_STOPFILE']).exists():
     stop_requested=True;raise RuntimeError('stopped by signal or stop file')
    if time.time()>=float(os.environ['FILLER_DEADLINE']):raise RuntimeError('deadline')
    time.sleep(.05)
   result['exit_code']=p.returncode
  text=log.read_text(errors='replace');w=json.loads((D/'witness.json').read_text());child=(w['pid'],w['birth_ticks'])
  if smoke and not progress:
   unit=test6_smoke_unit(w,child)
   if unit is not None:save(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']),unit);progress=True
  matches=re.findall(r'Test 6 PASS n_rs_seq=(\d+) restored=([^ ]+) A/A=([^ ]+) source=([^ ]+) source_A/A=([^ ]+) mutation=detected',text)
  if p.returncode!=0 or 'Test 6 SKIP' in text or 'All tests passed.' not in text or {m[0] for m in matches}!={'0','8'} or len(matches)!=2:raise ValueError('test markers invalid or missing')
  if w['error'] or [x['mode'] for x in w['entries']]!=[0,8] or {(x['mode'],x['point']) for x in w['samples']}!={(m,p) for m in (0,8) for p in ('decode_entry','restore_dst_1','restore_dst_2')}:raise ValueError('in-Test-6 mapped-library witness incomplete')
  if alive(*child) or any(alive(pid,bt) for pid,bt in children.items()):raise ValueError('captured child still live after GDB exit')
  initialized=re.findall(r'calling init:\s+(/\S*libggml\S*)',text)
  observed={path for sample in w['samples'] for path in sample['libraries']}
  if not initialized or any(str(Path(x).resolve(strict=True)) not in observed for x in initialized):raise ValueError('loader initialization not fully witnessed in sampled maps')
  for m in matches:
   values=[float(x) for x in m[1:]]
   if not all(__import__('math').isfinite(x) and x>=0 for x in values) or values[0]>values[1] or values[2]>values[3]:raise ValueError('invalid calibrated comparison')
  checks=[ps_check(pid,bt) for pid,bt in {**children,child[0]:child[1],p.pid:result['supervisor_birth_ticks']}.items()]
  if not all(x['dead'] for x in checks):raise ValueError('ps could not confirm every captured PID dead')
  preflight()
  if any(sha(D/name)!=digest for name,digest in producer_pins.items()):raise ValueError('producer changed during run')
  result.update(status='PASS',markers=matches,witness=w,loader_initialized_ggml=initialized,captured_children=children,cleanup_checks=checks,child_reaped=True,mutation_scope='The test reports mutation=detected and the captured restore returns are descriptive; no same-destination valid-restore control proves stale-specific non-vacuity.')
 except BaseException as e:
  result['error']=type(e).__name__+': '+str(e)
  # Freeze the captured GDB parent before enumerating children: it cannot
  # create a new inferior between enumeration and teardown.
  if p is not None and p.poll() is None:
   try:os.kill(p.pid,signal.SIGSTOP)
   except ProcessLookupError:pass
   for _ in range(200):
    try:
     state=Path('/proc/%d/stat'%p.pid).read_text().rsplit(')',1)[1].split()[0]
     if state in ('T','t'):break
    except FileNotFoundError:break
    time.sleep(.01)
   for task in Path('/proc/%d/task'%p.pid).glob('*/children'):
    try:
     for item in task.read_text().split():
      pid=int(item)
      if pid not in children:
       children[pid]=birth(pid)
       with open(os.environ['FILLER_PIDFILE'],'a') as pf:pf.write(str(pid)+'\n')
    except (OSError,ProcessLookupError,ValueError):pass
  if child: children[child[0]]=child[1]
  for pid,bt in children.items():
   if alive(pid,bt):
    try:os.kill(pid,signal.SIGTERM)
    except ProcessLookupError:pass
  if p is not None and p.poll() is None:
   try:os.kill(p.pid,signal.SIGCONT)
   except ProcessLookupError:pass
   try:p.wait(timeout=3)
   except subprocess.TimeoutExpired:
    for pid,bt in children.items():
     if alive(pid,bt):
      try:os.kill(pid,signal.SIGKILL)
      except ProcessLookupError:pass
    try:p.wait(timeout=3)
    except subprocess.TimeoutExpired:
     p.terminate()
     try:p.wait(timeout=3)
     except subprocess.TimeoutExpired:p.kill();p.wait(timeout=3)
  result['captured_children']=children
  checks=[ps_check(pid,bt) for pid,bt in {**children,**({p.pid:result['supervisor_birth_ticks']} if p is not None else {})}.items()]
  result['cleanup_checks']=checks
  result['child_reaped']=all(x['dead'] for x in checks) and (p is None or bool(children) or child is not None)
  if not result['child_reaped']:result['cleanup_unverified']=True
 finally:
  result['finished_utc']=time.time()
  if log.exists():result['raw_log_sha256']=sha(log)
  if not smoke:save(D/'RESULT.json',result)
  elif progress:
   if (D/'witness.json').exists():os.replace(D/'witness.json',D/'smoke-witness.json')
   save(D/'smoke-cleanup.json',{'qualification_only':True,'child':child,'captured_children':children,'child_reaped':result.get('child_reaped',False)})
 if smoke:return 75 if progress and result.get('child_reaped') and (stop_requested or result['status']=='PASS') else 1
 return 0 if result['status']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
