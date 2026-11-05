#!/usr/bin/env python3
"""Model-free STOP ordering qualification; synthetic evidence is never native evidence."""
import hashlib,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(pid):
 try:
  fields=Path(f'/proc/{pid}/stat').read_text().rsplit(') ',1)[1].split()
  return (int(fields[1]), fields[19], fields[0])
 except (OSError,ValueError,IndexError):return None

def capture(owned):
 # Follow parent links while processes are alive; retain birth identities across reparenting.
 changed=True
 while changed:
  changed=False
  for path in Path('/proc').iterdir():
   if not path.name.isdigit():continue
   pid=int(path.name); info=identity(pid)
   if info and info[0] in owned and pid not in owned:
    parent=identity(info[0])
    if parent and parent[1]==owned[info[0]]:
     owned[pid]=info[1];changed=True

def alive(pid,birth):
 info=identity(pid)
 return info is not None and info[1]==birth

def cleanup(proc,owned):
 capture(owned)
 for sig in (signal.SIGTERM,signal.SIGKILL):
  for pid,birth in reversed(list(owned.items())):
   if alive(pid,birth):
    try:os.kill(pid,sig)
    except ProcessLookupError:pass
  deadline=time.monotonic()+3
  while time.monotonic()<deadline:
   proc.poll()
   if not any(alive(p,b) for p,b in owned.items()):return
   time.sleep(.05)
 raise RuntimeError('captured fixture PID survives cleanup')

def main():
 sources=json.loads((D/'qualification-seal.json').read_text())
 for name,h in sources['sha256'].items():
  if digest(D/name)!=h:raise RuntimeError('sealed source changed: '+name)
 root=D/('run-'+str(time.time_ns()));root.mkdir()
 observations=[]
 for variant,stage,stopped in [(v,s,b) for v in ('patched','original') for s,b in [('startup',False),('startup',True),('postjob',False),('postjob',True),('postjob75',False)]]:
  c=root/(variant+'-'+stage+('-stop' if stopped else '-control'));c.mkdir();(c/'grants').mkdir()
  for n in ('complete.py','native_files.py'):shutil.copyfile(D/n,c/n)
  (c/'custody.py').write_text('import hashlib\nfrom pathlib import Path\ndef digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()\n')
  (c/'binding.json').write_text(json.dumps({'build':{'synthetic':True},'model':{'synthetic':True}}))
  fixture="""import hashlib,json,os,sys
from pathlib import Path
D=Path(__file__).resolve().parent
if sys.argv[1]=='stop':(D/'STOP').touch()
a=D/'out'/('attempt-'+'a'*32);a.mkdir(parents=True,exist_ok=True)
files={}
for name in ('test.log','config.json','witness.json'):
 p=a/name;p.write_text('SYNTHETIC MODEL-FREE FIXTURE '+name);files[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
r={'schema':'kpf17.oracle-test.v1','sealed':True,'smoke':False,'status':'PASS','process_verified_dead':True,'build':{'synthetic':True},'model':{'synthetic':True},'files':files}
(D/'out'/'RESULT.json').write_text(json.dumps(r))
sys.exit(75 if sys.argv[1] in ('stop','rc75') else 0)
"""
  (c/'fixture.py').write_text(fixture)
  if stage=='startup':subprocess.run([sys.executable,str(c/'fixture.py'),'stop' if stopped else 'control'],check=False)
  else:
   now=int(time.time())
   import datetime
   iso=lambda t:datetime.datetime.fromtimestamp(t,datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
   cpus=[v for v in os.sched_getaffinity(0) if v<=191]
   if not cpus:raise RuntimeError('no allowed fixture cpu')
   (c/'grants'/'fixture.grant').write_text(f'regions={cpus[0]} start={iso(now-1)} end={iso(now+600)}\n')
  env=dict(os.environ,FILLER_FLAGS_DIR=str(c),FILLER_GRANTS_DIR=str(c/'grants'),FILLER_STATE_DIR=str(c/'state'),FILLER_POLL='0.1')
  for k in ('FILLER_DRYRUN','FILLER_SMOKE','FILLER_STUB_CMD','LOOP_METRICS_LEDGER'):env.pop(k,None)
  argv=['bash',str(D/('filler_run15.sh' if variant=='patched' else 'filler_run15.original.sh')),'--id','fixture','--class','cpu','--gpu-quiet','none','--self-claim','--min-window','300','--stop',str(c/'STOP'),'--workdir',str(c),'--precond-cmd','true','--complete-cmd',f'{sys.executable} {c}/complete.py','--cmd',f'{sys.executable} {c}/fixture.py '+('stop' if stopped else 'rc75' if stage=='postjob75' else 'control')]
  expected_idle=stage=='startup' and stopped and variant=='patched'
  invalid=False; checkpoint=False
  with (c/'wrapper.log').open('w') as out:
   proc=subprocess.Popen(argv,env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
   info=identity(proc.pid)
   if info is None:raise RuntimeError('unable to capture wrapper birth')
   owned={proc.pid:info[1]}
   deadline=time.monotonic()+(1 if expected_idle else 15)
   try:
    while True:
     capture(owned)
     rc=proc.poll()
     if rc is not None:break
     if time.monotonic()>=deadline:
      checkpoint=expected_idle
      invalid=not expected_idle
      break
     time.sleep(.02)
   finally:
    cleanup(proc,owned)
    rc=proc.wait(timeout=5)
  complete=(c/'grants'/'fixture.complete').exists()
  ended=(c/'grants'/'fixture.ended')
  expected_complete=(not stopped and stage!='postjob75' if variant=='patched' else True)
  evidence=(c/'out'/'RESULT.json').exists()
  ended_text=ended.read_text() if ended.exists() else None
  valid_path=(checkpoint and evidence and ended_text is None if expected_idle else rc==0 and evidence and ended_text is not None)
  safe=not invalid and valid_path and complete==expected_complete
  observations.append({'variant':variant,'stage':stage,'stop':stopped,'wrapper_rc':rc,'complete':complete,'ended':ended_text,'expected_complete':expected_complete,'safe':safe,'invalid_timeout':invalid,'expected_idle_checkpoint':checkpoint,'captured_pids_verified_dead':True,'path':str(c)})
 result={'schema':'kpf17.wrapper-stop-qualification.v1','synthetic':True,'sources':sources,'observations':observations,'status':'PASS' if all(x['safe'] for x in observations) else 'UNSAFE','scope':'actual retained shell outer+inner and completion predicate; synthetic evidence/model-free job; no model/native/custody/race qualification'}
 (root/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');
 smoke=os.environ.get('FILLER_DRYRUN')=='1'
 result['smoke']=smoke
 target=Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
 target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(result,indent=2)+'\n')
 (D/'LAST_RESULT').write_text(str(root/'RESULT.json')+'\n')
 print(json.dumps(result,indent=2));return 0 if result['status']=='PASS' else 1
if __name__=='__main__':sys.exit(main())
