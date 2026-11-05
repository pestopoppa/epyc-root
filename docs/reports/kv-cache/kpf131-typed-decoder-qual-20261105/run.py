import hashlib,json,os,pathlib,select,signal,subprocess,sys,time,uuid
D=pathlib.Path(__file__).resolve().parent
ROW='kpf131-typed-decoder-qual-20261105'
invocation=os.environ['KPF131_INVOCATION']
if os.environ.get('FILLER_ID')!=ROW:raise SystemExit('wrong row identity')
end=float(os.environ['FILLER_END'])
soft=float(os.environ.get('FILLER_DEADLINE',end))
stopfile=pathlib.Path(os.environ['FILLER_STOPFILE'])
mode='smoke' if os.environ.get('FILLER_SMOKE')=='1' else 'full'
receipt=pathlib.Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH',str(D/'out'/'RESULT.json')))
if mode=='smoke' and 'FILLER_DRYRUN_RESULT_PATH' not in os.environ:raise SystemExit('smoke requires isolated receipt')
if receipt.exists():raise SystemExit('refuse existing receipt')
if len(os.sched_getaffinity(0))!=(4 if mode=='smoke' else 24):raise SystemExit('wrong CPU count')
out=D/'out'/mode/str(uuid.uuid4());out.mkdir(parents=True,exist_ok=False)
start=time.monotonic();child=None;identity=None
result=dict(row_id=ROW,invocation=invocation,status='INCOMPLETE',mode=mode,records=[],native_binding='UNKNOWN',historical_control='UNKNOWN',output=str(out),cleanup_verified=False)
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def seals():
 for manifest in ['SHA256SUMS','RUNTIME.sha256']:
  for line in (D/manifest).read_text().splitlines():
   h,name=line.split('  ',1);path=pathlib.Path(name)
   if not path.is_absolute():path=D/path
   if digest(path)!=h:raise RuntimeError('seal drift '+name)
def birth(pid):return pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19]
def snapshot():
 if birth(child.pid)!=identity:raise RuntimeError('child birth drift')
 root=pathlib.Path('/proc',str(child.pid));exe=os.readlink(root/'exe');maps=(root/'maps').read_text()
 paths={l.split(None,5)[5] for l in maps.splitlines() if len(l.split(None,5))==6 and l.split(None,5)[5].startswith('/')}
 return dict(pid=child.pid,birth=identity,exe=exe,exe_sha256=digest(root/'exe'),maps=maps,file_backed_maps=[l for l in maps.splitlines() if len(l.split(None,5))==6 and l.split(None,5)[5].startswith('/')],images={p:digest(p) for p in sorted(paths)})
def guard():
 if stopfile.exists() or (D/'STOP').exists():raise RuntimeError('STOP')
 if time.monotonic()-start>=300 or time.time()>=min(end,soft):raise RuntimeError('DEADLINE')
def line():
 buf=b''
 while True:
  guard()
  if select.select([child.stdout],[],[],0.1)[0]:
   b=os.read(child.stdout.fileno(),1)
   if not b:raise RuntimeError('premature child EOF')
   if b==b'\n':return buf.decode()
   buf+=b
   if len(buf)>1048576:raise RuntimeError('child output cap')
def interrupted(sig,frame):raise RuntimeError('signal '+str(sig))
for sig in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP]:signal.signal(sig,interrupted)
try:
 guard();seals();result['input_sha256']=digest(D/'inputs.json');result['source_manifest_sha256']=digest(D/'source.json')
 with (out/'stderr.txt').open('wb') as err:
  child=subprocess.Popen(['/usr/bin/python3','-B','-I',str(D/'worker.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,bufsize=0)
  identity=birth(child.pid);result.update(child_pid=child.pid,child_birth=identity)
  if line()!='READY':raise RuntimeError('missing READY')
  before=snapshot();(out/'before.json').write_text(json.dumps(before,indent=2))
  child.stdin.write(b'GO\n');child.stdin.flush()
  raw=line();(out/'native.json').write_text(raw+'\n');records=json.loads(raw)
  after=snapshot();(out/'after.json').write_text(json.dumps(after,indent=2))
  # Python allocation may grow anonymous heap; image custody covers exact file-backed mappings.
  if {k:v for k,v in before.items() if k!='maps'}!={k:v for k,v in after.items() if k!='maps'}:raise RuntimeError('child image/maps identity drift')
  child.stdin.write(b'ACK\n');child.stdin.flush()
  while child.poll() is None:guard();time.sleep(.05)
  result['child_exit']=child.returncode
  if child.returncode!=0:raise RuntimeError('child failed')
  if len(records)!=8 or [r['case'] for r in records]!=[c['case'] for c in json.loads((D/'inputs.json').read_text())] or not all(r['passed'] for r in records):raise RuntimeError('control coverage/failure')
  result['records']=records
  seals();guard();result['status']='SYNTHETIC_CONTROLS_PASS'
except Exception as e:result['reason']=str(e)
finally:
 if child is not None:
  if child.poll() is None:
   if birth(child.pid)==identity:child.terminate()
   try:child.wait(timeout=3)
   except subprocess.TimeoutExpired:
    if birth(child.pid)==identity:child.kill()
    child.wait(timeout=3)
  result['child_exit']=child.returncode
  result['cleanup_verified']=not pathlib.Path('/proc',str(child.pid)).exists()
 else:result['cleanup_verified']=True
 if not result['cleanup_verified']:result['status']='INCOMPLETE'
 result['elapsed_s']=time.monotonic()-start
 result['raw_sha256']={p.name:digest(p) for p in out.iterdir() if p.is_file()}
 (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
 receipt.parent.mkdir(parents=True,exist_ok=True)
 # Exclusive creation refuses any concurrent/stale publisher receipt.
 with receipt.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
sys.exit(0 if result['status']=='SYNTHETIC_CONTROLS_PASS' else 75 if result.get('reason') in ['STOP','DEADLINE'] else 1)
