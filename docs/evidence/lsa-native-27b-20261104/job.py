#!/usr/bin/env python3
"""One bounded native candidate request; requires reviewed pins and real keeper claim."""
import datetime,hashlib,json,os,pathlib,signal,socket,subprocess,sys,time,urllib.request
D=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,'/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/root/artifacts/lsa-screen-20261103')
import monitor,native_evidence
from classify import classify
from trace_guard import TraceGuard, valid_first_failure
subprocess.run([sys.executable,str(D/'preflight.py')],check=True)
a=json.loads((D/'approved-build.json').read_text()); plan=json.loads((D/'plan.json').read_text())
art=a['artifacts']; server_path=next(x['path'] for x in art if x['role']=='native_server')
pins={str(pathlib.Path(x['path']).resolve()):x['sha256'] for x in art if x['role'].endswith('_dso')}
assert pins and any('libggml-hip' in p for p in pins)
assert not (D/'STOP').exists(), 'final screen remains stopped pending main sign'
stop=pathlib.Path(os.environ['FILLER_STOPFILE']); deadline=int(os.environ['FILLER_DEADLINE'])
assert not stop.exists() and time.time()<deadline
attempt=D/'ATTEMPT'; attempt.mkdir() # Existing attempt is terminal, including interruptions.
trace=attempt/'native-trace.jsonl'; samples=attempt/'samples.jsonl'; response=attempt/'response.json'
signalled=False
def interrupt(*_):
 global signalled
 signalled=True
signal.signal(signal.SIGTERM,interrupt); signal.signal(signal.SIGINT,interrupt)
def guard():
 if signalled or stop.exists() or time.time()>=deadline: raise RuntimeError('stop or deadline')
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def loaded(pid):
 paths=set()
 for line in pathlib.Path(f'/proc/{pid}/maps').read_text().splitlines():
  p=line.split()[-1]
  if p.startswith('/') and ('libggml' in p or 'libllama' in p or 'libmtmd' in p): paths.add(str(pathlib.Path(p).resolve()))
 assert paths and any('libggml-hip' in p for p in paths)
 assert all(p in pins and sha(p)==pins[p] for p in paths), 'unapproved mapped DSO'
 return sorted(paths)
def terminate(p):
 if p and p.poll() is None:
  p.terminate()
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
 if p: assert p.poll() is not None, 'owned process survived'
def children(root):
 snapshot={}
 for proc in pathlib.Path('/proc').iterdir():
  if not proc.name.isdigit(): continue
  try:
   stat=(proc/'stat').read_text().rsplit(')',1)[1].split()
   snapshot[int(proc.name)]=(int(stat[1]),stat[19],stat[0])
  except (OSError,ValueError,IndexError): pass
 found={}; frontier={root}
 while frontier:
  frontier={pid for pid,(ppid,_,state) in snapshot.items() if ppid in frontier and state!='Z' and pid not in found}
  for pid in frontier: found[pid]=snapshot[pid][1]
 return found
def terminate_server(p):
 if not p or p.poll() is not None:return
 owned=children(p.pid)
 terminate(p)
 for sig in (signal.SIGTERM,signal.SIGKILL):
  for pid,birth in owned.items():
   try:
    if monitor.start_ticks(pid)==birth: os.kill(pid,sig)
   except (OSError,ValueError): pass
  if sig==signal.SIGTERM: time.sleep(.1)
 for pid,birth in owned.items():
  try:
   if monitor.start_ticks(pid)==birth:
    state=pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[0]
    assert state=='Z', f'owned child {pid} survived'
  except FileNotFoundError: pass
server=None; client=None; result={'status':'invalid','reason':'incomplete'}
try:
 guard()
 with socket.socket() as sock: sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
 argv=[server_path,'-m',plan['model'],'--host','127.0.0.1','--port',str(port),*plan['server_options']]
 env={k:v for k,v in os.environ.items() if not k.startswith('LLAMA_LSA_') and k not in ('LD_PRELOAD','LD_LIBRARY_PATH','GGML_BACKEND_PATH')}
 env.update({'LD_LIBRARY_PATH':':'.join(dict.fromkeys(str(pathlib.Path(p).parent) for p in pins))+':/opt/rocm/lib',
             'LLAMA_LSA_NATIVE_MANIFEST':str(D/'native.manifest'),'LLAMA_LSA_NATIVE_TRACE':str(trace),
             'ROCR_VISIBLE_DEVICES':'0','HIP_VISIBLE_DEVICES':'0','HSA_OVERRIDE_CPU_AFFINITY_DEBUG':'0','GGML_FUSED_DECODE_OFF':'1'})
 with (attempt/'linkage.txt').open('w') as link:
  subprocess.run(['/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',server_path,a['build_root']],env=env,stdout=link,stderr=subprocess.STDOUT,check=True)
 with (attempt/'server.log').open('wb') as log:
  server=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT)
  ticks=monitor.start_ticks(server.pid); until=time.monotonic()+180
  while True:
   guard(); assert server.poll() is None, 'server exited during startup'
   try:
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=2) as h:
     if h.status==200:break
   except Exception: pass
   if time.monotonic()>=until:raise TimeoutError('startup')
   time.sleep(.5)
  ident=monitor.identity(server.pid); assert ident['start_ticks']==str(ticks) and os.path.realpath(ident['exe'])==os.path.realpath(server_path)
  proc=pathlib.Path(f'/proc/{server.pid}'); actual=[os.fsdecode(x) for x in (proc/'cmdline').read_bytes().split(b'\0') if x]
  actual_env=dict(x.split('=',1) for x in (proc/'environ').read_bytes().decode().split('\0') if '=' in x)
  assert actual==argv and all(actual_env.get(k)==v for k,v in env.items() if k in ('LD_LIBRARY_PATH','LLAMA_LSA_NATIVE_MANIFEST','LLAMA_LSA_NATIVE_TRACE','ROCR_VISIBLE_DEVICES','HIP_VISIBLE_DEVICES'))
  before=loaded(server.pid); trace_before=trace.read_bytes(); assert not trace_before or trace_before.endswith(b'\n'); offset=len(trace_before)
  manifest=dict(line.split('=',1) for line in (D/'native.manifest').read_text().splitlines())
  startup=[json.loads(line) for line in trace_before.splitlines()]
  admitted=[x for x in startup if x.get('schema')=='lsa-native-graph-v1' and x.get('event')=='admitted']
  assert len(admitted)==1 and admitted[0].get('model_sha256')==manifest['model_sha256'] and admitted[0].get('map_sha256')==manifest['map_sha256'], 'native startup admission absent or mismatched'
  assert not any(x.get('event')=='admission_refused' for x in startup), 'native startup admission refused'
  request_launch_ns=time.monotonic_ns()
  client=subprocess.Popen([sys.executable,str(D/'request.py'),str(port),str(response)])
  seen=[]; failure=None; request_start=time.monotonic(); watch=TraceGuard(trace,offset)
  with samples.open('x',buffering=1) as sf:
   while client.poll() is None:
    guard(); assert server.poll() is None, 'server died during request'
    item=monitor.sample(server.pid); seen.append(item); sf.write(json.dumps(item)+'\n')
    failure=watch.poll()
    if failure is not None: break
    if time.monotonic()-request_start >= 360: raise TimeoutError('one request deadline')
    time.sleep(.1)
  if failure is None: failure=watch.poll()
  after=monitor.identity(server.pid)
  assert after['start_ticks']==str(ticks) and os.path.realpath(after['exe'])==os.path.realpath(server_path) and loaded(server.pid)==before, 'live process or DSO identity changed'
  if failure is not None:
   assert valid_first_failure(failure, manifest), 'missing, mismatched or cascaded first fallback reason'
   failure_seen_ns=time.monotonic_ns()
   client_already_finished=client.poll() is not None
   terminate_server(server)
   if not client_already_finished:
    try: client.wait(timeout=5)
    except subprocess.TimeoutExpired: terminate(client)
   assert any(request_launch_ns<=x['monotonic_ns']<=failure_seen_ns and x['kfd_present'] and
              any(isinstance(v,int) and v>0 for v in x['vram_bytes'].values()) for x in seen), 'no own-PID KFD/VRAM during failed request'
   trace_after=trace.read_bytes(); assert trace_after.startswith(trace_before)
   frozen=attempt/'request-trace.jsonl'; frozen.write_bytes(trace_after)
   (attempt/'first-fallback.json').write_text(json.dumps(failure,indent=2)+'\n')
   result={'status':'failure','reason':'native fallback: '+failure['failure_reason'],'score':0,
           'server_pid':server.pid,'server_start_ticks':ticks,'mapped_dsos':before,'trace_offset':offset,
           'request':str(response) if response.exists() else None,'trace':str(frozen),
           'first_fallback':str(attempt/'first-fallback.json'),'samples':str(samples),
           'intentional_stop':('client already complete when fallback observed' if client_already_finished else 'server stopped at first native fallback; client allowed to drain')}
  else:
   assert client.poll() is not None and response.exists(), 'request produced no complete record'
   req=json.loads(response.read_text()); start=req['request_start_monotonic_ns']; end=req['request_end_monotonic_ns']
   assert any(start<=x['monotonic_ns']<=end and x['kfd_present'] and
              any(isinstance(v,int) and v>0 for v in x['vram_bytes'].values()) for x in seen), 'no own-PID in-request KFD/VRAM sample'
   trace_after=trace.read_bytes(); assert trace_after.startswith(trace_before) and trace_after.endswith(b'\n')
   frozen=attempt/'request-trace.jsonl'; frozen.write_bytes(trace_after)
   verdict=subprocess.run([sys.executable,str(D/'validate_trace.py'),str(frozen),str(offset),str(response)],capture_output=True,text=True)
   (attempt/'trace-verdict.txt').write_text(verdict.stdout+verdict.stderr)
   assert verdict.returncode==0, 'native request trace malformed, incomplete or contradictory'
   mechanism=json.loads(verdict.stdout)
   assert mechanism.get('valid') is True and mechanism.get('mechanism') in ('pruned','unpruned')
   if mechanism['mechanism']=='unpruned':
    status,reason='failure','native executed without all-16 key/value pruning'
   else:
    status,reason=classify(req,True)
   result={'status':status,'reason':reason,'score':1 if status=='pass' else (0 if status in ('failure','timeout') else None),
           'server_pid':server.pid,'server_start_ticks':ticks,'mapped_dsos':before,'trace_offset':offset,
           'request':str(response),'trace':str(frozen),'trace_validation':mechanism,'samples':str(samples)}

except BaseException as e: result={'status':'invalid','reason':repr(e)}
finally:
 try: terminate(client); terminate_server(server)
 except Exception as e: result={'status':'invalid','reason':'cleanup: '+repr(e)}
 result.update({'schema':'lsa-screen-raw-v1','arm':'pca-native','item':plan['item'],'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'manifest_sha256':sha(D/'plan.json'),'binding':{'source_commit':a['source_commit'],'source_manifest_sha256':a['source_identity']},
                'scope':'one bounded 27B native screen; no population, promotion or speedup generalization'})
 result_path=attempt/'result.json'; result_path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 try:
  receipt=native_evidence.emit(result,D/'plan.json',result_path,producer_path=D/'job.py')
  (attempt/'receipt-path.txt').write_text(str(receipt)+'\n')
 except Exception as e:
  result['status']='invalid'; result['reason']='native evidence capture: '+repr(e)
  result_path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 if result['status'] in ('pass','failure','timeout'):
  (D/'results.jsonl').write_text(json.dumps({'unit':'native-27b-final-screen',**result},allow_nan=False)+'\n'); (D/'complete').touch()
sys.exit(0 if result['status'] in ('pass','failure','timeout') else 1)
