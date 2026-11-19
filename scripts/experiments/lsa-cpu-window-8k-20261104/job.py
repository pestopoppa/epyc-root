#!/usr/bin/env python3
import datetime,hashlib,importlib.util,json,os,signal,socket,subprocess,sys,threading,time,urllib.request
from pathlib import Path
D=Path(__file__).resolve().parent; A=D; S=Path('/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103'); B=S/'build-cpu/bin'; SRC=S/'llama-champion'; MODEL=Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'); MAP=Path('/tmp/lsa-release-inspect/qwen38_27b__long-16k-1M-heavy-key-and-query-pca-step0.pt')
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,x): p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
m=json.loads((D/'manifest.json').read_text()); review=json.loads((D/'REVIEW.json').read_text())
if not review.get('approved') or review.get('manifest_sha256')!=sha(D/'manifest.json') or review.get('job_sha256')!=sha(__file__):raise SystemExit('review does not bind bytes')
cpus=sorted(os.sched_getaffinity(0))
if cpus not in [list(range(i,i+4)) for i in (0,24,48,72)]:raise SystemExit('requires allocator four-core affinity')
for path,digest in m['files'].items():
 if sha(path)!=digest:raise SystemExit('identity mismatch: '+path)
baseline=m['baseline']; baseline_path=Path(baseline['path'])
if sha(baseline_path)!=baseline['sha256']:raise SystemExit('dense baseline changed')
dense=json.loads(baseline_path.read_text())
if dense.get('status')!='pass' or dense.get('retrieval_match') is not True:raise SystemExit('dense baseline invalid')
st=MODEL.stat()
if st.st_ino!=m['model_stat']['inode'] or st.st_size!=m['model_stat']['size']:raise SystemExit('model stat changed')
native=Path(os.environ['FILLER_STATE_DIR']).parent/'native';native.mkdir(parents=True,exist_ok=True);a=native/('attempt-'+str(os.getpid()));a.mkdir(); save(a/'PENDING.json',{'status':'invalid','reason':'interrupted attempt; no rerun'})
argv=m['argv'];env=os.environ.copy()
for k in list(env):
 if k.startswith('LLAMA_LSA_') or k in ('LSA_THREADS','LD_LIBRARY_PATH'):env.pop(k)
env.update(m['environment']);env['LLAMA_LSA_TRACE']=str(a/'trace.jsonl')
def check_stop():
 if (D/'STOP').exists() or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()):raise RuntimeError('CPU STOP requested')
result={'status':'invalid','reason':'startup incomplete','output':'','checks':{}}; p=None; events=[]; raw=bytearray(); first=None; request_start=None; done=threading.Event()
def request():
 global first
 try:
  req=urllib.request.Request('http://127.0.0.1:18198/completion',data=json.dumps({'prompt':json.loads((D/'ids.json').read_text()),'n_predict':24,'temperature':0,'top_k':1,'seed':42,'cache_prompt':False,'stream':True}).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=2401) as r:
   for line in r:
    raw.extend(line)
    if line.startswith(b'data:'):
     payload=line[5:].strip()
     if payload==b'[DONE]':continue
     ev=json.loads(payload);events.append(ev)
     if first is None and ev.get('content'):first=time.monotonic()
  result['response_complete']=True
 except Exception as e: result['request_error']=repr(e)
 finally:done.set()
def terminate(signum,frame):raise RuntimeError('received signal '+str(signum))
signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
try:
 check_stop()
 with socket.socket() as s:
  s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('127.0.0.1',18198))
 with (a/'server.log').open('wb') as log:
  p=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True); start=time.monotonic();ready=False
  while time.monotonic()-start<180:
   check_stop()
   if p.poll() is not None:raise RuntimeError('server exited before ready')
   try:
    with urllib.request.urlopen('http://127.0.0.1:18198/health',timeout=1) as h:
     if h.status==200:ready=True;break
   except Exception:pass
   time.sleep(1)
  if not ready:raise TimeoutError('model initialization exceeded 180 s')
  request_start=time.monotonic();t=threading.Thread(target=request,daemon=True);t.start();samples=[];libraries={};model_seen=False
  while not done.is_set():
   now=time.monotonic()
   check_stop()
   if p.poll() is not None:raise RuntimeError('server died during request')
   if (first is None and now-request_start>1800) or now-request_start>2400:raise TimeoutError('request operational deadline; inconclusive')
   exe=os.path.realpath(os.readlink(f'/proc/{p.pid}/exe'))
   if exe!=str((B/'llama-server').resolve()):raise RuntimeError('server exe mismatch')
   maps=Path(f'/proc/{p.pid}/maps').read_text().splitlines(); mapped=[]
   for line in maps:
    bits=line.split(maxsplit=5)
    if len(bits)<6 or not bits[5].startswith('/'):continue
    path=os.path.realpath(bits[5]);
    if path==str(MODEL):
     if int(bits[4])!=MODEL.stat().st_ino:raise RuntimeError('model inode mismatch')
     model_seen=True
    if 'libggml' in path or 'libllama' in path:
     f=Path(path)
     if not f.is_relative_to(B.resolve()) or 'hip' in path.lower() or int(bits[4])!=f.stat().st_ino:raise RuntimeError('unexpected library mapping '+path)
     if path not in libraries:libraries[path]=sha(f)
     if libraries[path]!=m['files'].get(path):raise RuntimeError('library digest mismatch '+path)
     mapped.append(path)
   stat=Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split(); actual_argv=Path(f'/proc/{p.pid}/cmdline').read_bytes().split(b'\0'); actual_argv=[x.decode(errors='replace') for x in actual_argv if x]; actual_env=dict(x.split('=',1) for x in Path(f'/proc/{p.pid}/environ').read_bytes().decode(errors='replace').split('\0') if '=' in x)
   if actual_argv!=argv or any(actual_env.get(k)!=v for k,v in env.items() if k.startswith('LLAMA_LSA_') or k=='LSA_THREADS') or any(actual_env.get(k)!=env[k] for k in ('ROCR_VISIBLE_DEVICES','HIP_VISIBLE_DEVICES','CUDA_VISIBLE_DEVICES','LD_LIBRARY_PATH')):raise RuntimeError('actual process arguments or environment differ')
   sample={'pid':p.pid,'start_ticks':stat[19],'exe':exe,'argv':actual_argv,'libs':sorted(set(mapped)),'model_seen':model_seen};samples.append(sample)
   with (a/'monitor.jsonl').open('a') as witness:witness.write(json.dumps(sample)+'\n');witness.flush()
   time.sleep(1)
  save(a/'monitor.json',{'samples':samples,'libraries':libraries,'model_seen':model_seen,'pid':p.pid});(a/'response.sse').write_bytes(raw)
  final=events[-1] if events else {}; result['output']=''.join(x.get('content','') for x in events)
  trace=[json.loads(line) for line in (a/'trace.jsonl').read_text().splitlines()]
  result['checks']={'all_global_layers':{t['layer'] for t in trace}==set(range(3,64,4)),'mask_changed':{t['layer'] for t in trace if t['changed']>0}==set(range(3,64,4)),'mask_only_removes':all(t['allowed_after']<=t['allowed_before'] for t in trace),'response_complete':result.get('response_complete',False),'model_mapping':model_seen,'cpu_libraries':bool(libraries),'prompt_8204':final.get('timings',{}).get('prompt_n')==8204,'no_think_reopened':'<think>' not in result['output'].lower() and not any(e.get('reasoning_content') for e in events)}
  result['retrieval_match']=result['output'].strip()=='92-8-E75FB6'; valid=all(result['checks'].values());result['status']='pass' if valid else 'invalid';result['reason']=('completed positional exact retrieval control' if valid else 'missing validity witness or thinking reopened')

except BaseException as e:result['reason']=repr(e)
finally:
 if p and p.poll() is None:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
 if p:result['server_pid']=p.pid;result['server_exit']=p.poll();result['server_dead']=p.poll() is not None
 if raw:(a/'response.sse').write_bytes(raw)
 result.update(schema='lsa-screen-raw-v1',item=m['rows'][0],arm='window',phase='diagnostic',time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest_sha256=sha(D/'manifest.json'),score=None,binding={'source_commit':m['source_commit'],'producer_sha256':sha(__file__),'manifest_path':str(D/'manifest.json'),'monitor_path':str(a/'monitor.json'),'trace_path':str(a/'trace.jsonl'),'baseline':m['baseline'],'admission_affinity':cpus,'loaded_byte_proof':'frozen model manifest digest, current inode and size, live mapping; no fresh model hash'},scope='One CPU positional sink4 plus last4608 retrieval control on exact same 8204 token IDs versus retained dense success; no timing or population quality claim.')
 result['unit']='window-exact-retrieval-8204';out=a/'result.raw.json';save(out,result);save(a/'RESULT.json',result)
 try:
  spec=importlib.util.spec_from_file_location('native_evidence',A/'native_evidence.py'); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.emit(result,D/'manifest.json',out,producer_path=Path(__file__))
 except Exception as e:
  result.update(status='invalid',reason='native evidence capture failed: '+repr(e));save(a/'RESULT.json',result)
  (a/'EVIDENCE_ERROR').write_text(repr(e));save(a/'native-writer-status.json',{'status':'invalid','reason':repr(e),'scientific_result_preserved':True})
 else:save(a/'native-writer-status.json',{'status':'pass'})
 (a/'PENDING.json').unlink(missing_ok=True)
save(native/'RESULT.json',result)
print(json.dumps(result));sys.exit(0 if result['status']=='pass' else (75 if os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists() else 1))
