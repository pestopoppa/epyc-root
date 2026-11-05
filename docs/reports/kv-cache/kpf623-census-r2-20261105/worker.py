import hashlib,json,os,pathlib,signal,subprocess,sys,time,resource,re
D=pathlib.Path(__file__).resolve().parent
S=json.loads((D/'inputs.json').read_text());smoke=os.getenv('FILLER_DRYRUN')=='1' or os.getenv('FILLER_SMOKE')=='1'
out=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D/'out/RESULT.json'
if smoke and D/'out' in out.resolve().parents:raise SystemExit('smoke/full alias')
if len(sys.argv)>1:
 r=json.loads(out.read_text());raise SystemExit(0 if r.get('status')==('SMOKE_ONLY' if smoke else 'CENSUS_COMPLETE') and r.get('cleanup_verified') and r.get('row_id')=='kpf623-census-r2-20261105' else 1)
out.parent.mkdir(parents=True,exist_ok=True)
if out.exists():raise SystemExit('existing result')
a=out.parent/('attempt-'+str(time.time_ns()));a.mkdir()
r={'status':'UNKNOWN','row_id':'kpf623-census-r2-20261105','mode':'smoke' if smoke else 'full','alignment_verdict':'UNKNOWN','attempt':str(a),'affinity':sorted(os.sched_getaffinity(0))};owned=[]
def check():
 if pathlib.Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>float(os.environ['FILLER_END'])-10:raise RuntimeError('STOP/deadline')
def model_stats():
 result=[]
 for m in S['vocabs']:
  q=pathlib.Path(m['path']).stat();actual={'dev':q.st_dev,'ino':q.st_ino,'size':q.st_size,'mtime_ns':q.st_mtime_ns,'ctime_ns':q.st_ctime_ns}
  if actual!=m['stat']:raise RuntimeError('model stat drift '+m['path'])
  result.append({'path':m['path'],'stat':actual})
 return result
def limits():
 resource.setrlimit(resource.RLIMIT_FSIZE,(67108864,67108864))
def verify():
 if subprocess.check_output(['git','-C',S['source'],'rev-parse','HEAD'],text=True).strip()!=S['source_commit']:raise RuntimeError('source drift')
 for p,h in S['files'].items():
  if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=h:raise RuntimeError('file drift '+p)
 model_stats()
def run(argv,name):
 check()
 with (a/(name+'.stdout')).open('w') as o,(a/(name+'.stderr')).open('w') as e:
  p=subprocess.Popen(argv,stdout=o,stderr=e,env=dict(os.environ,LD_LIBRARY_PATH=S['libdir']),preexec_fn=limits)
  fd=os.pidfd_open(p.pid);owned.append((p,fd))
  until=min(time.time()+110,float(os.environ['FILLER_END'])-10)
  while p.poll() is None:
   check()
   for output in a.iterdir():
    if output.is_file() and output.stat().st_size>67108864:raise RuntimeError('live output bound')
   if time.time()>until:raise TimeoutError(name)
   try:p.wait(timeout=.2)
   except subprocess.TimeoutExpired:pass
  if p.returncode:raise RuntimeError(name+' rc '+str(p.returncode))
try:
 r['model_stats_before']=model_stats();verify();check()
 if smoke and len(os.sched_getaffinity(0))!=4:raise RuntimeError('smoke requires exactly four CPUs')
 if not smoke and len(os.sched_getaffinity(0))<24:raise RuntimeError('quarter required')
 run([S['compiler'],'-std=c++17','-O1','-I'+S['source']+'/include','-I'+S['source']+'/ggml/include',str(D/'census.cpp'),'-L'+S['libdir'],'-Wl,-rpath,'+S['libdir'],'-lllama','-o',str(a/'census')],'build')
 r['native_executable_sha256']=hashlib.sha256((a/'census').read_bytes()).hexdigest();r['pieces']=[]
 for i,m in enumerate(S['vocabs']):
  target=a/('vocab-'+str(i)+'.tsv');run([str(a/'census'),m['path'],str(target),'256' if smoke else '0'],'vocab-'+str(i))
  if target.stat().st_size>67108864:raise RuntimeError('output bound')
  data=target.read_bytes();rows=data.splitlines()
  marker=re.fullmatch(r'PIECES_COMPLETE ([0-9]+) N_VOCAB ([0-9]+)\s*',(a/('vocab-'+str(i)+'.stdout')).read_text())
  if not marker or int(marker[1])!=len(rows) or not rows or int(marker[2])<len(rows) or (not smoke and int(marker[2])!=len(rows)):raise RuntimeError('native count incomplete')
  if any(row.split(b'\t',1)[0]!=str(j).encode() for j,row in enumerate(rows)):raise RuntimeError('piece ID coverage')
  mapped=set()
  for line in target.with_suffix('.tsv.maps').read_text().splitlines():
   fields=line.split(maxsplit=5)
   if len(fields)==6 and ('/libggml' in fields[5] or '/libllama' in fields[5]):
    path=fields[5]
    if path not in S['expected_native_dsos']:raise RuntimeError('unsupported linked file '+path)
    q=pathlib.Path(path).stat();dev=tuple(int(x,16) for x in fields[3].split(':'))
    if (os.major(q.st_dev),os.minor(q.st_dev))!=dev or q.st_ino!=int(fields[4]):raise RuntimeError('mapping file identity')
    if hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()!=S['files'][path]:raise RuntimeError('linked file drift')
    mapped.add(path)
  if mapped!=set(S['expected_native_dsos']):raise RuntimeError('expected linked files absent; linkage UNKNOWN')
  r['pieces'].append({'path':str(target),'sha256':hashlib.sha256(data).hexdigest(),'rows':len(data.splitlines()),'bytes':len(data),'native_n_vocab':int(marker[2]),'native_count':int(marker[1]),'linked_files':sorted(mapped)})
 r['model_stats_after']=model_stats();verify();r['status']='SMOKE_ONLY' if smoke else 'CENSUS_COMPLETE'
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
raise SystemExit(0 if r['status'] in ('SMOKE_ONLY','CENSUS_COMPLETE') else 75)
