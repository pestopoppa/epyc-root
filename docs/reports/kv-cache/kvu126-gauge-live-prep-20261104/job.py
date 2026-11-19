#!/usr/bin/env python3
"""KVU-12.6 native gauge capability, not the depth/performance experiment."""
import datetime, hashlib, http.client, json, os, re, shutil, signal, subprocess, sys, threading, time, urllib.request
from pathlib import Path
D=Path(__file__).resolve().parent
SRC=Path('/mnt/raid0/llm/tmp/rtg57-kvu126-unique-cells-20261102')
HEAD='cdf1532b993fe58bd57ba53d91659f4bb4ee508f'
MODEL=Path('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf')
PORT=19896

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
 return h.hexdigest()

def command(argv, **kw):
 return subprocess.run(argv, check=True, **kw)

def atomic(path, obj):
 path.parent.mkdir(parents=True, exist_ok=True)
 tmp=path.with_name(path.name+'.tmp');tmp.write_text(json.dumps(obj,sort_keys=True)+'\n');os.replace(tmp,path)

def gauge(text):
 values=[]
 for line in text.splitlines():
  m=re.fullmatch(r'llamacpp:kv_cache_used_cells(?:\{[^}]*\})?\s+(\d+(?:\.\d+)?)\s*',line)
  if m: values.append(float(m.group(1)))
 if len(values)!=1 or values[0]<0 or not values[0].is_integer(): raise ValueError('missing or ambiguous unique-cell gauge')
 return int(values[0])

def birth(pid):
 s=Path(f'/proc/{pid}/stat').read_text();return int(s[s.rfind(')')+2:].split()[19])

def owns(pid,port):
 sockets=set()
 for fd in Path(f'/proc/{pid}/fd').iterdir():
  try: s=os.readlink(fd)
  except FileNotFoundError: continue
  if s.startswith('socket:['):sockets.add(s[8:-1])
 for proto in ('tcp','tcp6'):
  for line in Path(f'/proc/{pid}/net/{proto}').read_text().splitlines()[1:]:
   a=line.split()
   if a[3]=='0A' and int(a[1].split(':')[-1],16)==port and a[9] in sockets:return True
 return False

def get(path, payload=None):
 data=None if payload is None else json.dumps(payload).encode()
 request=urllib.request.Request(f'http://127.0.0.1:{PORT}{path}',data,{'Content-Type':'application/json'})
 with urllib.request.urlopen(request,timeout=30) as r:
  if r.status!=200: raise RuntimeError('HTTP response not 200')
  return r.read()

def now_utc():
 return datetime.datetime.now(datetime.timezone.utc).isoformat()

def check_source():
 if subprocess.check_output(['git','-C',str(SRC),'rev-parse','HEAD'],text=True).strip()!=HEAD:raise RuntimeError('source pin changed')
 if subprocess.check_output(['git','-C',str(SRC),'status','--porcelain','--untracked-files=normal'],text=True).strip():raise RuntimeError('source worktree dirty')

def maps_sample(pid,expected_birth):
 start=time.monotonic_ns()
 if birth(pid)!=expected_birth or not owns(pid,PORT):raise RuntimeError('sample process or listener identity changed')
 mapped={}
 for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
  parts=line.split(maxsplit=5)
  if len(parts)<6:continue
  name=parts[5]
  if '/libggml' not in name and '/libllama' not in name and '/libmtmd' not in name:continue
  if name.endswith(' (deleted)'):raise RuntimeError('deleted mapped library')
  actual=str(Path(name).resolve(strict=True));major,minor=(int(x,16) for x in parts[3].split(':'));inode=int(parts[4])
  item={'path':actual,'dev_major':major,'dev_minor':minor,'inode':inode}
  if actual in mapped and mapped[actual]!=item:raise RuntimeError('inconsistent mapped identity')
  mapped[actual]=item
 end=time.monotonic_ns()
 return {'pid':pid,'birth_ticks':expected_birth,'start_monotonic_ns':start,'end_monotonic_ns':end,'utc':now_utc(),'libraries':list(mapped.values())}

def require_overlap(dispatch_ns,response_ns,sample):
 if not (dispatch_ns<=sample['start_monotonic_ns']<=sample['end_monotonic_ns']<=response_ns):raise RuntimeError('maps sample misses request window')

def verify_sample(sample,files):
 mapped={}
 for item in sample['libraries']:
  path=item['path'];st=Path(path).stat()
  if (os.major(st.st_dev),os.minor(st.st_dev),st.st_ino)!=(item['dev_major'],item['dev_minor'],item['inode']):raise RuntimeError('mapped inode/device changed')
  if path not in files or sha(path)!=files[path]:raise RuntimeError('mapped library outside or different from build manifest')
  st2=Path(path).stat()
  if (st.st_dev,st.st_ino)!=(st2.st_dev,st2.st_ino):raise RuntimeError('library changed during hashing')
  mapped[path]={'sha256':files[path],'dev_major':item['dev_major'],'dev_minor':item['dev_minor'],'inode':item['inode']}
 names=[Path(x).name for x in mapped]
 if not any(n.startswith('libggml-cpu') for n in names) or not any(n.startswith('libggml-base') for n in names) or not any(n.startswith('libllama') for n in names):raise RuntimeError('required live mapped libraries missing')
 return mapped

def completion_with_sample(pid,expected_birth,req):
 state={};sent=threading.Event();done=threading.Event();raw=json.dumps(req).encode()
 def run_request():
  conn=http.client.HTTPConnection('127.0.0.1',PORT,timeout=30)
  try:
   conn.request('POST','/completion',raw,{'Content-Type':'application/json'})
   state['dispatch_monotonic_ns']=time.monotonic_ns();state['dispatch_utc']=now_utc();sent.set()
   response=conn.getresponse();body=response.read();state['response_monotonic_ns']=time.monotonic_ns();state['response_utc']=now_utc()
   if response.status!=200:raise RuntimeError('completion HTTP response not 200')
   state['response']=body
  except Exception as exc:state['error']=str(exc);sent.set()
  finally:conn.close();done.set()
 thread=threading.Thread(target=run_request,daemon=True);thread.start()
 if not sent.wait(30):raise RuntimeError('request dispatch timed out')
 if 'error' in state:raise RuntimeError('request failed: '+state['error'])
 sample=None
 while not done.is_set():
  if time.time()>=int(os.environ['FILLER_DEADLINE']) or Path(os.environ['FILLER_STOPFILE']).exists():raise RuntimeError('stop or deadline during request')
  sample=maps_sample(pid,expected_birth)
  if not done.is_set():break
  sample=None
 if not done.wait(35):raise RuntimeError('completion response timed out')
 thread.join(timeout=1)
 if thread.is_alive():raise RuntimeError('completion thread not drained')
 if 'error' in state:raise RuntimeError('request failed: '+state['error'])
 if sample is None:raise RuntimeError('no during-request library sample')
 require_overlap(state['dispatch_monotonic_ns'],state['response_monotonic_ns'],sample)
 return json.loads(state['response']),sample,{k:state[k] for k in ('dispatch_monotonic_ns','dispatch_utc','response_monotonic_ns','response_utc')}

def main():
 signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(InterruptedError('stop signal')))
 signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(InterruptedError('interrupt signal')))
 check_source()
 smoke=os.environ.get('FILLER_SMOKE')=='1';out=D/'out';out.mkdir(exist_ok=True)
 build=D/('build-smoke-'+str(os.getpid()) if smoke else 'build-full')
 if build.exists():raise RuntimeError('refuse stale/reused build directory')
 log=(out/('build-smoke.log' if smoke else 'build-full.log')).open('wb')
 with log:
  command(['cmake','-S',str(SRC),'-B',str(build),'-DCMAKE_BUILD_TYPE=Release','-DGGML_NATIVE=ON','-DGGML_HIP=OFF','-DLLAMA_BUILD_SERVER=ON','-DLLAMA_BUILD_TESTS=OFF','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON'],stdout=log,stderr=subprocess.STDOUT)
  command(['cmake','--build',str(build),'--target','ggml-base' if smoke else 'llama-server','-j',str(min(8,int(os.environ.get('FILLER_THREADS','4'))))],stdout=log,stderr=subprocess.STDOUT)
 check_source()
 bindir=build/'bin';files={str(p.resolve()):sha(p) for p in bindir.iterdir() if p.is_file()}
 if not files:raise RuntimeError('no compiled binary artifacts')
 if smoke:
  base=[p for p in files if Path(p).name.startswith('libggml-base')]
  if not base:raise RuntimeError('smoke did not compile ggml-base')
  compiled_digest=files[base[0]];compiled_bytes=Path(base[0]).stat().st_size
  if compiled_bytes<=0:raise RuntimeError('empty compiled base')
  shutil.rmtree(build)
  atomic(Path(os.environ['FILLER_DRYRUN_RESULT_PATH']),{'schema':'kvu126.gauge.build-smoke.v1','source_commit':HEAD,'compiled_base_sha256':compiled_digest,'compiled_artifact_bytes':compiled_bytes,'mode':'qualification','measurement_claim':False})
  return 75
 grant_file=Path(os.environ.get('FILLER_GRANTS_DIR','/mnt/raid0/llm/tmp/compute-flags/grants'))/os.environ['FILLER_ID']
 if not grant_file.is_file():raise RuntimeError('grant file missing')
 grant_bytes=grant_file.read_bytes();grant_sha=hashlib.sha256(grant_bytes).hexdigest();(out/'grant.bin').write_bytes(grant_bytes)
 for filename in ('CMakeCache.txt','compile_commands.json'):
  source=build/filename
  if not source.is_file():raise RuntimeError('missing build manifest input: '+filename)
  shutil.copyfile(source,out/filename)
 exe=(bindir/'llama-server').resolve(strict=True)
 if str(exe) not in files:raise RuntimeError('server missing from build manifest')
 expected=(D/'model.sha256').read_text().split()[0]
 if sha(MODEL)!=expected:raise RuntimeError('model digest changed')
 def contains_gauge(path):
  tail=b''
  with path.open('rb') as f:
   for chunk in iter(lambda:f.read(1024*1024),b''):
    data=tail+chunk
    if b'llamacpp:kv_cache_used_cells' in data:return True
    tail=data[-64:]
  return False
 if not any(contains_gauge(p) for p in bindir.iterdir() if p.is_file() and ('llama' in p.name or p.name=='llama-server')):raise RuntimeError('built server lacks gauge')
 env=dict(os.environ,LD_LIBRARY_PATH=str(bindir),GGML_IQK='1')
 link=command(['/bin/bash','/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',str(exe),str(bindir)],env=env,text=True,capture_output=True)
 (out/'linkage.txt').write_text(link.stdout+link.stderr)
 argv=[str(exe),'-m',str(MODEL),'--host','127.0.0.1','--port',str(PORT),'-np','1','-c','4096','-t',os.environ.get('FILLER_THREADS','4'),'-ngl','0','--device','none','--metrics','--slots','--kv-unified','--cache-ram','0','--no-cache-idle-slots','--spec-type','none']
 receipt={'schema':'kvu126.gauge.native.v1','source_commit':HEAD,'source_status':'clean','model_sha256':expected,'build_files':files,'cmake_flags':['CMAKE_BUILD_TYPE=Release','GGML_NATIVE=ON','GGML_HIP=OFF','LLAMA_BUILD_SERVER=ON','LLAMA_BUILD_TESTS=OFF','CMAKE_EXPORT_COMPILE_COMMANDS=ON'],'build_inputs_sha256':{k:sha(out/k) for k in ('CMakeCache.txt','compile_commands.json')},'compiler_environment':{k:os.environ.get(k) for k in ('CC','CXX')},'cmake_version':subprocess.check_output(['cmake','--version'],text=True).splitlines()[0],'argv':argv,'grant':{k:os.environ.get(k) for k in ('FILLER_ID','FILLER_CPUS','FILLER_NEEDGPU','FILLER_DEADLINE','FILLER_PIDFILE')},'grant_file':str(grant_file),'grant_sha256':grant_sha,'started_utc':now_utc(),'measurement_claim':False,'status':'incomplete'}
 (out/'build-manifest.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 proc=None;b=None
 try:
  with (out/'server.log').open('wb') as serverlog:
   proc=subprocess.Popen(argv,env=env,stdout=serverlog,stderr=subprocess.STDOUT)
   with open(os.environ['FILLER_PIDFILE'],'a') as f:f.write(str(proc.pid)+'\n')
   b=birth(proc.pid);limit=time.monotonic()+240
   while True:
    if proc.poll() is not None:raise RuntimeError('server died before health')
    if time.time()>=int(os.environ['FILLER_DEADLINE']) or Path(os.environ['FILLER_STOPFILE']).exists():raise RuntimeError('stop or deadline before health')
    try:
     if owns(proc.pid,PORT) and get('/health'):break
    except (OSError,ValueError):pass
    if time.monotonic()>=limit:raise RuntimeError('server health timeout')
    time.sleep(1)
   if birth(proc.pid)!=b or not owns(proc.pid,PORT):raise RuntimeError('listener ownership changed')
   before_raw=get('/metrics');(out/'before.metrics').write_bytes(before_raw);receipt['before_counter_utc']=now_utc();receipt['before_counter_monotonic_ns']=time.monotonic_ns();before=gauge(before_raw.decode());receipt['before_cells']=before;req={'prompt':'The current request tests a native unique KV cell gauge. '*4,'n_predict':1,'temperature':0,'seed':35,'cache_prompt':True,'id_slot':0}
   response,sample,timing=completion_with_sample(proc.pid,b,req)
   mapped=verify_sample(sample,files)
   after_raw=get('/metrics');(out/'after.metrics').write_bytes(after_raw);receipt['after_counter_utc']=now_utc();receipt['after_counter_monotonic_ns']=time.monotonic_ns();after=gauge(after_raw.decode());receipt['after_cells']=after
   if type(response.get('tokens_predicted')) is not int or response['tokens_predicted']<1 or not (0<=before<after<=4096):raise RuntimeError('missing token or gauge did not increase within context')
   if birth(proc.pid)!=b or not owns(proc.pid,PORT):raise RuntimeError('server identity changed during request')
   if sha(grant_file)!=grant_sha:raise RuntimeError('grant changed during request')
   (out/'before.metrics').write_bytes(before_raw);(out/'after.metrics').write_bytes(after_raw)
   receipt.update({'status':'observation_captured','pid':proc.pid,'birth':b,'request_timing':timing,'during_request_maps':sample,'mapped_libraries':mapped,'before_cells':before,'after_cells':after,'completed_tokens':response['tokens_predicted'],'request_sha256':hashlib.sha256(json.dumps(req).encode()).hexdigest()})
 except Exception as exc:
  receipt.update({'status':'incomplete','error_type':type(exc).__name__,'error':str(exc)[:1000]})
  raise
 finally:
  if proc is not None:
   if proc.poll() is None:
    if b is not None and birth(proc.pid)!=b:raise RuntimeError('refuse signal after PID birth change')
    proc.send_signal(signal.SIGTERM)
   try:proc.wait(timeout=20)
   except subprocess.TimeoutExpired:
    if b is not None and birth(proc.pid)!=b:raise RuntimeError('refuse kill after PID birth change')
    proc.kill();proc.wait(timeout=10)
   ps=subprocess.run(['ps','-p',str(proc.pid),'-o','pid='],capture_output=True,text=True)
   dead=ps.returncode==1 and not ps.stdout.strip() and proc.poll() is not None
   receipt['cleanup']={'pid':proc.pid,'birth_ticks':b,'reaped':proc.poll() is not None,'ps_returncode':ps.returncode,'ps_stdout':ps.stdout,'verified_dead':dead,'returncode':proc.returncode,'utc':now_utc()}
   if dead and receipt['status']=='observation_captured':receipt['status']='observed'
  atomic(out/'RESULT.json',receipt)
 if not receipt.get('cleanup',{}).get('verified_dead'):raise RuntimeError('server cleanup unverified')
 (out/'COMPLETE').write_text('observed gauge increase with native process custody; no performance claim\n')
 return 0

if __name__=='__main__':
 try:sys.exit(main())
 except Exception as exc:
  failure=D/'out/RESULT.json'
  if os.environ.get('FILLER_SMOKE')!='1' and not failure.exists():atomic(failure,{'schema':'kvu126.gauge.native.v1','source_commit':HEAD,'measurement_claim':False,'status':'incomplete','error_type':type(exc).__name__,'error':str(exc)[:1000]})
  raise
