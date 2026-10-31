"""Private Oolong job-side path; no scheduler state or grant mutation."""
import sys
if __name__=='__main__':
 print('disabled: scheduler lifecycle and output auxiliary-write confinement not verified',file=sys.stderr)
 sys.exit(78)
import datetime,hashlib,json,os,re,time
from pathlib import Path
from resource_budget import ResourcePause,check as budget_check
import accounting,cohort_status,exposure,lock_witness,owned_window,pincheck,server_bind,window_policy,retained_readset
from calendar_guard import Calendar,WindowPause
ROOT=Path(__file__).resolve().parent
BASE=Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/heavy-yarn-quarter-ready')
PLAN=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch/prospective-power-input/plan')
PRIVATE_PY=Path('/mnt/micron/yarn-python313-host-closure-20261030/bin/python3')
FLAGS=Path('/mnt/raid0/llm/tmp/compute-flags')
def assigned_region():
 value=os.environ.get('FILLER_CPUS','')
 if value not in ('0-23','24-47','48-71','72-95'):raise ValueError('assigned CPU quarter')
 lo,hi=map(int,value.split('-'))
 return value,set(range(lo,hi+1))
def grant_valid(raw,end):
 try:
  text=raw.decode('ascii')
  if not re.fullmatch(r'regions=[0-9]+-[0-9]+ start=\d{4}-\d\d-\d\dT\d\d:\d\dZ end=\d{4}-\d\d-\d\dT\d\d:\d\dZ\n',text):return False
  f=dict(x.split('=',1) for x in text.split())
  parse=lambda v:datetime.datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()
  return f['regions']==assigned_region()[0] and parse(f['start'])<=time.time()<parse(f['end']) and int(parse(f['end']))==end
 except (ValueError,UnicodeError,KeyError):return False
def total(root):
 count=0
 for base,dirs,files in os.walk(root,followlinks=False):
  for n in dirs+files:
   p=Path(base)/n
   if p.is_symlink():
    if p.name=='plan' and p.resolve()==PLAN:continue
    raise ValueError("unexpected symlink")
   if p.is_file():count+=p.stat().st_size
 return count
def job(arm,port,manifest_sha):
 if arm not in ('A0','A1') or type(port)!=int:raise ValueError("scope")
 retained_readset.verify()
 prior=cohort_status.read(ROOT/'SCOPE-s0-conservative.json',PLAN/'items.jsonl',ROOT/'cohort')
 import eligible_gate
 scope=json.loads((ROOT/"SCOPE-s0-conservative.json").read_bytes())
 if not eligible_gate.eligible(scope,prior,arm):return {"state":"needs_review","reason":"no eligible matched items for arm","accounting":prior}
 env=os.environ
 fid=env.get('FILLER_ID','')
 if fid!='yarn-oolong-s0-host256-eligible28-v33-20261031':raise ValueError("private filler identity")
 assigned,assigned_cpus=assigned_region()
 if env.get('FILLER_THREADS')!='24' or set(os.sched_getaffinity(0))!=assigned_cpus:raise ValueError("affinity")
 end=int(env['FILLER_END']);deadline=int(env['FILLER_DEADLINE'])
 if deadline!=end-90:raise ValueError("deadline")
 stop=Path(env['FILLER_STOPFILE']);grant=FLAGS/'grants'/(fid+'.grant')
 if stop!=Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/yarn-s0-v33-20261031/STOP') or stop.is_symlink() or grant.is_symlink():raise ValueError("stop/grant path")
 lock_path=Path('/mnt/raid0/llm/tmp/cpu_region.GLOBAL.q%d.lock'%(min(assigned_cpus)//24))
 owner,identity=lock_witness.capture(lock_path);source_snapshot={}
 cohort=ROOT/'cohort';cohort.mkdir(mode=0o700,exist_ok=True)
 if cohort.is_symlink():raise ValueError("cohort symlink")
 for name in ('results','exposures'):
  d=cohort/name;d.mkdir(mode=0o700,exist_ok=True)
  if d.is_symlink():raise ValueError('output symlink')
 env_snapshot={k:env.get(k) for k in ('FILLER_ID','FILLER_CPUS','FILLER_THREADS','FILLER_END','FILLER_DEADLINE','FILLER_STOPFILE')}
 def static_identity():
  if any(env.get(k)!=v for k,v in env_snapshot.items()):raise ValueError('own grant environment changed')
 def static_source():
  retained_readset.verify()
  if not pincheck.unchanged(source_snapshot):raise ValueError('source changed during native window')
 def static_lock():
  if not lock_witness.verify(owner,identity,lock_path):raise ValueError('own CPU quarter lock identity changed')
 calendar=Calendar(grant,assigned,end,deadline,stop,static_identity,static_source,static_lock)
 def active():
  calendar.live()
  budget_check(cohort)
  if any(FLAGS.glob('HOLD_*')) or Path('/mnt/raid0/llm/tmp/HOLD_GPU_FOR_QUIET_20261024').exists():raise WindowPause('owner HOLD')
  st=os.statvfs(cohort)
  if st.f_bavail*st.f_frsize<window_policy.FLOOR+window_policy.FOUR_SHARD_RESERVE+128*1024**2 or total(cohort)>=256*1024**2:raise ResourcePause('native output/disk reserve')
  return True
 active()
 source_snapshot.update(pincheck.verify(ROOT,ROOT/"SOURCE-MANIFEST-v33.json",manifest_sha,active)["source_identities"])
 partition=json.loads((BASE/'partition-proposal.json').read_bytes())
 if Path(partition['original_plan']).resolve()!=PLAN or hashlib.sha256((PLAN/'items.jsonl').read_bytes()).hexdigest()!=partition['original_items_file_sha256']:raise ValueError("plan identity")
 link=cohort/'plan'
 if not link.exists():os.symlink(PLAN,link,target_is_directory=True)
 if link.resolve()!=PLAN:raise ValueError("wrong plan")
 window=window_policy.new_window(cohort)
 argv,ready=server_bind.prepare(arm,port,active)
 procenv={k:v for k,v in env.items() if k in ('PATH','LANG','LC_ALL','TZ','FILLER_ID','FILLER_CPUS','FILLER_THREADS','FILLER_END','FILLER_DEADLINE','FILLER_STOPFILE')}
 procenv.update({'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(SERVER_BUILD),'GGML_IQK':'1','OMP_NUM_THREADS':'24','OMP_PROC_BIND':'spread','OMP_PLACES':'cores','OMP_DYNAMIC':'false','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','WINDOW_CONFIRMED':'1','TMPDIR':str(window)})
 def worker(server,server_id):
  path=window/'server.argv'
  with path.open('x') as f:f.write('\n'.join(argv)+'\n');f.flush();os.fsync(f.fileno())
  return ['/usr/bin/python3','-B','-I',str(ROOT/'write_fence.py'),str(cohort/'results'),str(cohort/'exposures'),'--',str(PRIVATE_PY),'-B',str(ROOT/'worker.py'),'0',arm,str(cohort),str(port),str(deadline),str(server.pid),str(path),'cohort']
 result=None;failure=None;pause=None
 try:
  result=owned_window.run(['/usr/bin/python3','-B','-I',str(ROOT/'write_fence.py'),'--','/usr/bin/numactl','--interleave=all',*argv],worker,procenv,window,active,ready,time.monotonic()+max(0,deadline-time.time()))
 except (ResourcePause,owned_window.WindowDeadline) as exc:pause=type(exc).__name__+': '+str(exc)
 except (TimeoutError,RuntimeError,OSError,ValueError) as exc:failure=type(exc).__name__+': '+str(exc)
 calendar.static();retained_readset.verify()
 summary=cohort_status.read(ROOT/'SCOPE-s0-conservative.json',PLAN/'items.jsonl',cohort)
 counts=summary['counts']
 if pause is not None:return {'state':'partial','partial':True,'reason':pause,'accounting':summary,'window':result}
 if (result and result.get('worker_rc')==75):return {'state':'partial','partial':True,'reason':'native worker resource/window pause','accounting':summary,'window':result}
 if failure and failure.startswith('ResourcePause:'):return {'state':'partial','partial':True,'reason':failure,'accounting':summary,'window':result}
 if summary['cells']==prior['cells']:return {'state':'needs_review','reason':'no newly captured exposure; no partial rearm','failure':failure,'window':result,'accounting':summary}
 state='partial' if counts['unexposed'] else 'needs_review'
 return {'state':state,'failure':failure,'window':result,'accounting':summary}
def choose_arm(summary):
 import eligible_gate
 scope=json.loads((ROOT/'SCOPE-s0-conservative.json').read_bytes())
 return eligible_gate.choose(scope,summary)
def job_auto(port,manifest_sha):
 summary=cohort_status.read(ROOT/'SCOPE-s0-conservative.json',PLAN/'items.jsonl',ROOT/'cohort')
 arm=choose_arm(summary)
 if arm is None:return {'state':'needs_review','reason':'eligible subset exhausted; full 120-item denominator remains incomplete','accounting':summary}
 return job(arm,port,manifest_sha)
def smoke(mode,manifest_sha):
 import smoke_admission,socket,urllib.request
 if mode not in ("normal","cutoff"):raise ValueError("smoke mode")
 start=time.monotonic();hard=start+(50 if mode=="cutoff" else 60)
 cpus=os.sched_getaffinity(0);smoke_admission.check(cpus);source_snapshot={}
 out=Path(os.environ["YARN_SMOKE_OUTPUT_ROOT"])
 if out.is_symlink() or not out.is_dir() or out.parent!=ROOT or not out.name.startswith("smoke-"+mode+"-"):raise ValueError("confined smoke output root")
 if any(p.name not in ("ws58-launcher.out","plan") for p in out.iterdir()):raise ValueError("smoke root already exposed")
 if not (out/"plan").is_symlink() or (out/"plan").resolve()!=PLAN:raise ValueError("smoke input plan link")
 budget={"sampled_output_bytes":0,"sampled_free_bytes":0,"remaining_reserved_bytes":window_policy.SMOKE_RESERVE}
 def active():
  smoke_admission.check(cpus)
  budget.update(window_policy.smoke_budget(out,PLAN))
  if not pincheck.unchanged(source_snapshot):raise ValueError('smoke frozen source identity changed')
  return time.monotonic()<hard
 source_snapshot.update(pincheck.verify(ROOT,ROOT/"SOURCE-MANIFEST-v33.json",manifest_sha,active)["source_identities"])
 for n in ('results','exposures'):(out/n).mkdir(mode=0o700)
 window=window_policy.new_smoke_window(out,PLAN)
 sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
 argv,ready=server_bind.prepare_smoke(port,active)
 procenv={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(SERVER_BUILD),'OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','WINDOW_CONFIRMED':'1','TMPDIR':str(window)}
 procenv['YARN_SMOKE_CASE']=mode
 deadline=time.time()+(220 if mode=="cutoff" else max(0,hard-time.monotonic()))
 def worker(server,identity):
  path=window/'server.argv'
  with path.open('x') as f:f.write('\n'.join(argv)+'\n');f.flush();os.fsync(f.fileno())
  return ['/usr/bin/python3','-B','-I',str(ROOT/'write_fence.py'),str(out/'results'),str(out/'exposures'),'--',str(PRIVATE_PY),'-B',str(ROOT/'worker.py'),'0','A0',str(out),str(port),str(deadline),str(server.pid),str(path),'smoke']
 result=None;failure=None;window_deadline=False;cutoff_witness={"active":False,"sample_monotonic":None}
 def witness_cutoff(server,identity):
  while time.monotonic()<hard:
   try:
    state,parent,birth=server_bind.server_witness.procstat(server.pid)
    if state in ("Z","X") or parent!=os.getpid() or birth!=identity["birth"]:return
    server_bind.server_witness.listener(server.pid,port)
    with urllib.request.urlopen("http://127.0.0.1:%d/slots"%port,timeout=min(1.0,max(.05,hard-time.monotonic()))) as response:
     raw=response.read(1024*1024+1)
     if len(raw)>1024*1024:return
    slots=json.loads(raw)
    sampled=time.monotonic()
    if isinstance(slots,list) and len(slots)==1 and slots[0].get("is_processing") is True and 0<=hard-sampled<=5.0:
     cutoff_witness.update(active=True,sample_monotonic=sampled);return
   except Exception:pass
   time.sleep(.05)
 try:result=owned_window.run(['/usr/bin/python3','-B','-I',str(ROOT/'write_fence.py'),'--',*argv],worker,procenv,window,active,ready,hard,on_cutoff=witness_cutoff)
 except (TimeoutError,RuntimeError,OSError,ValueError) as exc:
  failure=type(exc).__name__+': '+str(exc);window_deadline=isinstance(exc,owned_window.WindowDeadline)
 elapsed=time.monotonic()-start
 file=out/'results'/'A0.jsonl'
 rows=[json.loads(x) for x in file.read_bytes().splitlines() if x] if file.exists() else []
 starts=list((out/'exposures').glob('*.start'))
 unknown=[x.name for x in starts if not x.with_name(x.name[:-6]+'.response').exists()]
 valid_normal=mode=="normal" and failure is None and result is not None and result["worker_rc"]==0 and len(rows)>0 and not unknown
 valid_cutoff=mode=="cutoff" and window_deadline and time.monotonic()>=hard and len(rows)>0 and bool(unknown) and cutoff_witness["active"]
 data={"schema":"private.yarn.r11_smoke.v1","mode":mode,"partial":bool(valid_cutoff),"scope":"small model; 4000-character Oolong prompt prefixes; no cohort result","completed":len(rows),"unknown":unknown,"elapsed_s":elapsed,"failure":failure,"owned_descendants_drained":True,"normal_pass":valid_normal,"cutoff_pass":valid_cutoff,"cutoff_due_to_window":window_deadline,"native_slot_active_near_cutoff":cutoff_witness["active"],"sampled_output_budget":budget,"slot_sample_lead_s":None if cutoff_witness["sample_monotonic"] is None else hard-cutoff_witness["sample_monotonic"]}
 exposure.put(out/'smoke-result.json',data)
 return 0 if valid_normal else 75 if valid_cutoff else 78
SERVER_BUILD=Path('/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin')
if __name__=='__main__':
 print('disabled: scheduler lifecycle and output auxiliary-write confinement not verified',file=sys.stderr)
 sys.exit(78)
