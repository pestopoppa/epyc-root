import datetime,hashlib,json,math,os,pathlib,re,resource,subprocess,sys,time,uuid
D=pathlib.Path('/mnt/raid0/llm/tmp/df2/cafe4-native-rewind-20261104'); INPUT=D/'INPUTS.json'
MARKER=re.compile(r'^CAFE4_MTP_ROLLBACK width=(\d+) accepted=(\d+) selected=(\d+) faulted=(\d+) off_error=([^ ]+) observe_error=([^ ]+) fault_error=([^ ]+) off_observe=([^ ]+) fault_observe=([^ ]+) tolerance=([^\s]+)$',re.M)
RS1=re.compile(r'^CAFE4_TARGET_RS .* mode=1$',re.M);RS2=re.compile(r'^CAFE4_TARGET_RS .* mode=2$',re.M)
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def atomic(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);q=p.with_name(p.name+'.'+uuid.uuid4().hex);q.write_text(json.dumps(d,sort_keys=True)+'\n');os.replace(q,p)
def out():return pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if os.environ.get('FILLER_DRYRUN')=='1' else D/'RESULT.json'
def check_input():
 m=json.loads(INPUT.read_text())
 for p,h in m['artifacts'].items():assert digest(p)==h
 s=pathlib.Path(m['model']['path']).stat();assert {'dev':s.st_dev,'ino':s.st_ino,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}==m['model']['stat']
 return m
def parse(text):
 mm=MARKER.findall(text)
 if len(mm)!=1:return None
 try:
  w,a,sel,fault=map(int,mm[0][:4]);e0,e1,ef,eo,delta,tol=map(float,mm[0][4:]);nums=(e0,e1,ef,eo,delta,tol)
  if not all(math.isfinite(x) and x>=0 for x in nums):return None
  if not (1<w<=3 and 0<a<w and sel>0 and fault>0 and tol>0 and e0<=tol and e1<=tol and eo<=tol and ef>10*tol and delta>10*tol):return None
  if not RS1.search(text) or not RS2.search(text) or 'RESULT PASS nonfault rollback agrees; target snapshot fault demonstrably diverges' not in text:return None
  return dict(width=w,accepted=a,selected=sel,faulted=fault,off_error=e0,observe_error=e1,fault_error=ef,off_observe=eo,fault_observe=delta,tolerance=tol)
 except (ValueError,OverflowError):return None
if sys.argv[1]=='selftest':
 good='CAFE4_TARGET_RS memory=0x1 seq=0 selected=1 used=1 mode=1\nCAFE4_TARGET_RS memory=0x2 seq=0 selected=1 used=0 mode=2\nCAFE4_MTP_ROLLBACK width=3 accepted=1 selected=1 faulted=1 off_error=0 observe_error=0 fault_error=1 off_observe=0 fault_observe=1 tolerance=0.001\nRESULT PASS nonfault rollback agrees; target snapshot fault demonstrably diverges\n'
 assert parse(good) and parse(good.replace('fault_error=1','fault_error=nan')) is None and parse(good.replace('mode=2','mode=1')) is None and parse(good.replace('accepted=1','accepted=0')) is None
 print('parser controls PASS');sys.exit(0)
if sys.argv[1]=='predicate':
 try:
  p=out();r=json.loads(p.read_text());assert r['mode']=='qualification' and r['model_mapped'] is True and r['all_libraries_mapped'] is True and r['pid']>0 and p.stat().st_mtime>=int(os.environ['FILLER_SMOKE_T0']);assert r['status']=='NATIVE_MODEL_MAPPED' or (r['status']=='PASS' and r['child_reaped'] is True and r['controls']);check_input()
 except Exception:sys.exit(1)
 sys.exit(0)
if sys.argv[1]=='check':
 try:
  r=json.loads((D/'RESULT.json').read_text());assert r['status']=='PASS' and r['child_reaped'] is True and r['controls'];check_input()
 except Exception:sys.exit(1)
 sys.exit(0)
m=check_input();attempt=uuid.uuid4().hex;run=D/'runs'/attempt;run.mkdir(parents=True);log=run/'native.log';stop=pathlib.Path(os.environ['FILLER_STOPFILE']);deadline=float(os.environ['FILLER_DEADLINE']);qualification=os.environ.get('FILLER_DRYRUN')=='1';expected={p for p in m['artifacts'] if '/libggml' in p or '/libllama' in p};seen={};proc=None;cutoff=None;rc=None;start=datetime.datetime.now(datetime.timezone.utc).isoformat();progress=False
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
try:
 with log.open('w') as stream:
  proc=subprocess.Popen([str(D/'bin/cafe4-mtp-rollback'),m['model']['path']],stdout=stream,stderr=subprocess.STDOUT,env=dict(os.environ,LD_LIBRARY_PATH=str(D/'bin'),OMP_NUM_THREADS='1'),start_new_session=True)
  while proc.poll() is None:
   try:
    raw=pathlib.Path(f'/proc/{proc.pid}/maps').read_text();lines=[x.split() for x in raw.splitlines()];paths={str(pathlib.Path(x[-1]).resolve()) for x in lines if len(x)>=6 and ('/libggml' in x[-1] or '/libllama' in x[-1])};assert paths<=set(m['artifacts']),'foreign ggml or llama mapping';seen.update({p:m['artifacts'][p] for p in paths});mapped=any(len(x)>=6 and x[-1]==m['model']['path'] for x in lines)
    if mapped and expected<=set(seen) and not progress:
     record={'schema':'cafe4.native.progress.v1','status':'NATIVE_MODEL_MAPPED','mode':'qualification' if qualification else 'scheduled','attempt':attempt,'pid':proc.pid,'model_mapped':True,'all_libraries_mapped':True,'artifact_ids':seen,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'native_log':str(log)};atomic(out(),record);atomic(run/'progress.json',record);progress=True
   except FileNotFoundError:pass
   if stop.exists() or time.time()>=deadline:cutoff='STOP' if stop.exists() else 'deadline';proc.terminate();break
   time.sleep(.05)
  try:rc=proc.wait(timeout=10)
  except subprocess.TimeoutExpired:proc.kill();rc=proc.wait(timeout=10)
finally:
 if proc is not None and proc.poll() is None:proc.kill();rc=proc.wait(timeout=10)
text=log.read_text(errors='replace') if log.exists() else '';controls=parse(text);ok=cutoff is None and rc==0 and controls is not None and progress and expected<=set(seen) and 'CAFE4_MTP_LOAD_ENABLED' in text
result={'schema':'cafe4.native.result.v1','status':'PASS' if ok else 'UNKNOWN','scope':'one-prompt CPU MTP rollback/fault diagnostic; no throughput or full CAFE-4 closure','mode':'qualification' if qualification else 'scheduled','attempt':attempt,'start':start,'end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'model':m['model'],'input_sha256':digest(INPUT),'child_rc':rc,'child_reaped':proc is not None and proc.poll() is not None,'pid':proc.pid if proc else None,'model_mapped':progress,'all_libraries_mapped':expected<=set(seen),'cutoff':cutoff,'controls':controls,'mapped_libraries':seen,'expected_libraries':sorted(expected),'affinity':sorted(os.sched_getaffinity(0)),'run':str(run),'raw_log_sha256':digest(log),'limitations':['one fixed prompt and diagnostic cap, not sampled acceptance','candidate has no -ngl or arbitrary verify-width CLI; full CAFE-4 remains open','baseline+1e-5 and 10x fault thresholds are predeclared diagnostic conventions']}
check_input();atomic(run/'terminal.json',result)
if qualification and cutoff=='STOP' and progress:sys.exit(75)
atomic(out(),result);sys.exit(0 if ok else 2)
