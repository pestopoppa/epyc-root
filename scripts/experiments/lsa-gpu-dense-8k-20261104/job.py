#!/usr/bin/env python3
"""One development dense BF16-KV MI210 retrieval item; smoke uses identical request."""
import datetime, hashlib, importlib.util, json, os, signal, socket, subprocess, sys, threading, time, urllib.request
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0, '/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/root/artifacts/lsa-screen-20261103')
import monitor, native_evidence
plan=json.loads((D/'plan.json').read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
ids=(D/'ids.json').read_bytes(); assert sha(D/'ids.json')==plan['ids_sha256'] and len(json.loads(ids))==plan['prompt_n']
model=Path(plan['model']); stat=model.stat(); assert (stat.st_ino,stat.st_size)==(plan['model_inode'],plan['model_size'])
for a in plan['artifacts']: assert sha(a['path'])==a['sha256'], a['path']
art={x['role']:x for x in plan['artifacts']}; server_path=Path(art['native_server']['path']); pins={str(Path(v['path']).resolve()):v['sha256'] for k,v in art.items() if k.endswith('_dso')}
root=Path(os.environ['FILLER_STATE_DIR']).parent/'native'; root.mkdir(parents=True,exist_ok=True); a=root/('attempt-'+str(os.getpid())); a.mkdir()
stop=Path(os.environ['FILLER_STOPFILE']); deadline=int(os.environ['FILLER_DEADLINE']); interrupted=False; server=None; result={'status':'invalid','reason':'incomplete'}
def sig(*_):
 global interrupted; interrupted=True
signal.signal(signal.SIGTERM,sig);signal.signal(signal.SIGINT,sig)
def guard():
 if interrupted or stop.exists() or time.time()>=deadline:raise InterruptedError('stop or deadline')
def mapped(pid):
 paths={str(Path(line.split()[-1]).resolve()) for line in Path(f'/proc/{pid}/maps').read_text().splitlines() if line.split()[-1].startswith('/') and any(s in line.split()[-1] for s in ('libllama','libggml','libmtmd'))}
 assert any('libggml-hip' in p for p in paths) and all(p in pins and sha(p)==pins[p] for p in paths), 'unapproved mapped libraries'
 return sorted(paths)
response={}; complete=threading.Event(); start_ns=None
def request(port):
 global start_ns
 try:
  body={'prompt':json.loads(ids),**plan['request']};req=urllib.request.Request(f'http://127.0.0.1:{port}/completion',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'});start_ns=time.monotonic_ns();events=[]
  with urllib.request.urlopen(req,timeout=360) as f:
   for line in f:
    if not line.startswith(b'data:'):continue
    payload=line[5:].strip()
    if payload==b'[DONE]':continue
    e=json.loads(payload);events.append(e)
    if e.get('content') and not (a/'first-token.json').exists(): (a/'first-token.json').write_text(json.dumps({'unit':'dense-first-token','monotonic_ns':time.monotonic_ns()})+'\n')
    if '<think>' in ''.join(x.get('content','') for x in events).lower() or e.get('reasoning_content'):raise ValueError('thinking reopened')
  end=time.monotonic_ns();final=events[-1] if events else {};text=''.join(x.get('content','') for x in events);response.update(events=events,output=text,end_ns=end,complete=final.get('stop') is True,prompt_n=final.get('timings',{}).get('prompt_n'),predicted=final.get('tokens_predicted'),retrieval_match=text.strip()==plan['expected'])
 except BaseException as exc:response['error']=repr(exc)
 finally:complete.set()
try:
 guard()
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 argv=[str(server_path),'-m',plan['model'],'--host','127.0.0.1','--port',str(port),*plan['server_options']]
 env={k:v for k,v in os.environ.items() if not k.startswith('LLAMA_LSA_') and k not in ('LD_PRELOAD','LD_LIBRARY_PATH','GGML_BACKEND_PATH')};env.update(LD_LIBRARY_PATH=str(server_path.parent)+':/opt/rocm/lib',ROCR_VISIBLE_DEVICES='0',HIP_VISIBLE_DEVICES='0',GGML_FUSED_DECODE_OFF='1')
 with (a/'linkage.txt').open('w') as link:subprocess.run(['/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',str(server_path),plan['build_root']],env=env,stdout=link,stderr=subprocess.STDOUT,check=True)
 with (a/'server.log').open('wb') as log:
  server=subprocess.Popen(argv,env=env,stdout=log,stderr=subprocess.STDOUT); ticks=monitor.start_ticks(server.pid); until=time.monotonic()+180
  while True:
   guard();assert server.poll() is None, 'startup exited'
   try:
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=1) as h:
     if h.status==200:break
   except Exception:pass
   if time.monotonic()>=until:raise TimeoutError('startup deadline')
   time.sleep(.5)
  before=monitor.identity(server.pid);assert before['start_ticks']==str(ticks) and os.path.realpath(before['exe'])==str(server_path.resolve()); dsos=mapped(server.pid)
  proc=Path(f'/proc/{server.pid}'); actual=[os.fsdecode(x) for x in (proc/'cmdline').read_bytes().split(b'\0') if x]; assert actual==argv
  actual_env=dict(x.split('=',1) for x in (proc/'environ').read_bytes().decode(errors='replace').split('\0') if '=' in x); assert not any(k.startswith('LLAMA_LSA_') for k in actual_env) and actual_env.get('LD_LIBRARY_PATH')==env['LD_LIBRARY_PATH']
  thread=threading.Thread(target=request,args=(port,),daemon=True);thread.start(); samples=[]; start=time.monotonic()
  while not complete.is_set():
   guard();assert server.poll() is None,'server exited during request';samples.append(monitor.sample(server.pid))
   if time.monotonic()-start>360 or (time.monotonic()-start>300 and not (a/'first-token.json').exists()):raise TimeoutError('request deadline')
   time.sleep(.5)
  after=monitor.identity(server.pid); assert after['start_ticks']==str(ticks) and mapped(server.pid)==dsos
  (a/'samples.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in samples));(a/'response.json').write_text(json.dumps(response,indent=2)+'\n')
  assert start_ns is not None and any(start_ns<=x['monotonic_ns']<=response.get('end_ns',0) and x['kfd_present'] and any(isinstance(v,int) and v>0 for v in x['vram_bytes'].values()) for x in samples),'no own PID in-window KFD/VRAM'
  assert not response.get('error') and response.get('complete') and response.get('prompt_n')==plan['prompt_n'] and 1<=response.get('predicted',0)<=24,'invalid response'
  result={'status':'pass' if response['retrieval_match'] else 'failure','reason':'dense exact gold' if response['retrieval_match'] else 'dense wrong answer; stop development stage','score':int(response['retrieval_match']),'retrieval_match':response['retrieval_match'],'mapped_dsos':dsos,'server_pid':server.pid,'samples':str(a/'samples.jsonl'),'response':str(a/'response.json')}
except BaseException as exc:result={'status':'invalid','reason':repr(exc)}
finally:
 if server and server.poll() is None:
  server.terminate()
  try:server.wait(timeout=10)
  except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
 if server and server.poll() is None:result={'status':'invalid','reason':'owned server survived cleanup'}
 result.update(schema='lsa-screen-raw-v1',arm='dense-bf16',item=plan['item'],time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),manifest_sha256=sha(D/'plan.json'),binding={'source_commit':plan['source_commit'],'source_manifest_sha256':plan['source_identity']},scope=plan['scope'])
 out=a/'result.raw.json';out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 try:receipt=native_evidence.emit(result,D/'plan.json',out,producer_path=Path(__file__));result['receipt']=str(receipt)
 except Exception as exc:result.update(status='invalid',reason='native evidence: '+repr(exc))
 result['unit']='dense-bf16-dev-8204';(root/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));sys.exit(0 if result['status'] in ('pass','failure') else (75 if stop.exists() or interrupted else 1))
