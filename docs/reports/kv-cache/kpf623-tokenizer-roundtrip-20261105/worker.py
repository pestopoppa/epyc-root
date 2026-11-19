import hashlib,json,os,pathlib,signal,subprocess,sys,time,resource
D=pathlib.Path(__file__).resolve().parent; S=json.loads((D/'inputs.json').read_text()); smoke=os.getenv('FILLER_DRYRUN')=='1' or os.getenv('FILLER_SMOKE')=='1'
out=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
if len(sys.argv)>1:
 try:r=json.loads(out.read_text());ok=r.get('status')==('SMOKE_ONLY' if smoke else 'OBSERVED') and r.get('cleanup_verified') and r.get('row_id')=='kpf623-tokenizer-roundtrip-20261105'
 except Exception:ok=False
 raise SystemExit(0 if ok else 1)
if smoke and D/'out' in out.resolve().parents:raise SystemExit('smoke/full alias')
out.parent.mkdir(parents=True,exist_ok=True)
if out.exists():raise SystemExit('existing result')
a=out.parent/('attempt-'+str(time.time_ns()));a.mkdir(); owned=[]
r={'status':'UNKNOWN','row_id':'kpf623-tokenizer-roundtrip-20261105','mode':'smoke' if smoke else 'full','affinity':sorted(os.sched_getaffinity(0)),'compatibility':'UNKNOWN','attempt':str(a)}
def check():
 if pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>float(os.environ['FILLER_END'])-10:raise RuntimeError('STOP/deadline')
def stats():
 x=[]
 for m in S['vocabs']:
  q=pathlib.Path(m['path']).stat(); z={'dev':q.st_dev,'ino':q.st_ino,'size':q.st_size,'mtime_ns':q.st_mtime_ns,'ctime_ns':q.st_ctime_ns}
  if z!=m['stat']:raise RuntimeError('model stat drift')
  x.append(z)
 return x
def verify():
 if subprocess.check_output(['git','-C',S['source'],'rev-parse','HEAD'],text=True).strip()!=S['source_commit']:raise RuntimeError('source drift')
 for p,h in S['files'].items():
  if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=h:raise RuntimeError('file drift '+p)
 stats()
def limits():resource.setrlimit(resource.RLIMIT_FSIZE,(67108864,67108864))
def run(argv,name):
 check()
 with (a/(name+'.stdout')).open('w') as o,(a/(name+'.stderr')).open('w') as e:
  p=subprocess.Popen(argv,stdout=o,stderr=e,env=dict(os.environ,LD_LIBRARY_PATH=S['libdir']),preexec_fn=limits);fd=os.pidfd_open(p.pid);owned.append((p,fd))
  until=min(time.time()+110,float(os.environ['FILLER_END'])-10)
  while p.poll() is None:
   check()
   if time.time()>until:raise TimeoutError(name)
   if any(q.is_file() and q.stat().st_size>67108864 for q in a.iterdir()):raise RuntimeError('output bound')
   try:p.wait(timeout=.2)
   except subprocess.TimeoutExpired:pass
  if p.returncode:raise RuntimeError(name+' rc '+str(p.returncode))
try:
 r['model_stats_before']=stats();verify();check()
 if smoke and len(os.sched_getaffinity(0))!=4:raise RuntimeError('smoke requires exactly four CPUs')
 if not smoke and len(os.sched_getaffinity(0))<24:raise RuntimeError('quarter required')
 run([S['compiler'],'-std=c++17','-O1','-I'+S['source']+'/include','-I'+S['source']+'/ggml/include',str(D/'roundtrip.cpp'),'-L'+S['libdir'],'-Wl,-rpath,'+S['libdir'],'-lllama','-o',str(a/'roundtrip')],'build')
 r['native_executable_sha256']=hashlib.sha256((a/'roundtrip').read_bytes()).hexdigest()
 if smoke:
  r['case_count']=1
  run([str(a/'roundtrip'),'--smoke'],'smoke')
  if (a/'smoke.stdout').read_text().strip()!='SMOKE_COMPILED':raise RuntimeError('smoke')
 else:
  target=a/'observations.tsv';run([str(a/'roundtrip'),S['vocabs'][1]['path'],str(D/'cases.tsv'),str(target)],'roundtrip')
  lines=target.read_text().splitlines();cases=(D/'cases.tsv').read_text().splitlines()
  if (a/'roundtrip.stdout').read_text().strip()!='ROUNDTRIP_COMPLETE 256' or len(lines)!=256:raise RuntimeError('incomplete')
  counts={k:0 for k in ('EXACT','DIFFERENT_IDS','DIFFERENT_BYTES','UNKNOWN')}
  for line,case in zip(lines,cases):
   f=line.split('\t');c=case.split('\t')
   if f[0]!=c[0] or f[1] not in counts:raise RuntimeError('case mismatch')
   counts[f[1]]+=1
  r['counts']=counts;r['observations_sha256']=hashlib.sha256(target.read_bytes()).hexdigest();r['observations_path']=str(target);r['case_count']=256
 r['model_stats_after']=stats();verify();r['status']='SMOKE_ONLY' if smoke else 'OBSERVED'
except BaseException as e:r['error']=repr(e)
finally:
 for p,fd in owned:
  if p.poll() is None:
   for sig in (signal.SIGTERM,signal.SIGKILL):
    if p.poll() is not None:break
    signal.pidfd_send_signal(fd,sig)
    try:p.wait(timeout=2)
    except subprocess.TimeoutExpired:pass
  os.close(fd)
 r['cleanup_verified']=all(p.poll() is not None and not pathlib.Path('/proc/'+str(p.pid)).exists() for p,_ in owned)
 if not r['cleanup_verified']:r['status']='UNKNOWN'
 with out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
raise SystemExit(0 if r['status'] in ('SMOKE_ONLY','OBSERVED') else 75)
