import importlib.util,json,os,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;sys.path.insert(0,str(D/'source-proposal'));import lock_witness as new
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('old',str(D/'legacy-v33/lock_witness.py'));old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
row=next(r for r in new.ancestors() if new.is_transport(r));new.authenticate_cli(row)
assigned=os.environ.get('FILLER_CPUS','')
region='q'+str(int(assigned.split('-')[0])//24) if assigned else 'q'+str(min(os.sched_getaffinity(0))//24)
paths={n:root/('cpu_region.'+n+'.'+region+'.lock') for n in ['GLOBAL','build']}
start=new.held(row,paths);churn=out/'private-churn';churn.mkdir();p=subprocess.Popen([sys.executable,'-B',str(D/'churn_locks.py'),str(churn)])
count=0;failures=[];deadline=time.monotonic()+8
try:
 while count<4096 and time.monotonic()<deadline:
  count+=1
  try:owner,identity=old.capture(paths['GLOBAL']);old.verify(owner,identity,paths['GLOBAL'])
  except RuntimeError as exc:
   witness=new.held(row,paths)
   failures.append({'iteration':count,'old_refusal':str(exc),'actual_owner_fd_locks_after_refusal':witness})
   if str(exc)=='lock lost':break
finally:
 (churn/'STOP').touch();p.wait(timeout=3)
 assert p.poll() is not None
record={'scope':'ACTUAL_UNCHANGED_V33_PREDICATE_PRIVATE_FLOCK_CHURN','physical_claim':False,'grant':None,'owner':row,'start_fd_rows':start,'iterations':count,'failures_with_still_held_real_fd_rows':failures,'churn_rc':p.returncode,'churn_drained':True,'target_owner_held_after':new.held(row,paths)}
(out/'RESULT.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'iterations':count,'failures':len(failures),'old_messages':[f['old_refusal'] for f in failures]}))
