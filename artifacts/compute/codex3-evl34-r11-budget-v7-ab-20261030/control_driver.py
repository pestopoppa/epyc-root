#!/usr/bin/env python3
"""EVL44 normal GPU control: gated single disjoint case, never cohort.

Runs only under the approved external R11 GPU supervisor and explicit root
review. Incomplete attempts remain journalled/partial and cannot be retried.
"""
import hashlib,json,os,resource,signal,socket,subprocess,sys,threading,time,urllib.request
from pathlib import Path
from src.repl_environment.exec_sandbox import wrap,Policy,credential_paths
from paired_journal import create
from sealed_journal import invoke_cell,DECL
from request_policy import RequestPolicy
from native_usage import UsageLedger
from broker_protocol import serve_one,recv,send
from browse_backend import BrowseBackend
from stream_broker import serve_stream
from request_capture import RequestCapture
from evl34_upstream import Upstream
from repl_upstream_adapter import REPLUpstream
from native_projection import project_redel
from prompt_projection import project
from server_peer import birth
from gpu_witness import witness
D=Path(__file__).resolve().parent
MODEL=Path('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf')
BIN=Path('/mnt/raid0/llm/kernels/production/gpu/llama-server')
PORT=None
FLOOR=150*1024**3
OWN_RESERVE=256*1024**2
OUTPUT_STOP=224*1024**2
END=time.monotonic()+240
stopping=False

def sig(*_):
 global stopping
 stopping=True
for signo in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(signo,sig)
def stopped():return stopping or time.monotonic()>=END or (D/'STOP').exists()
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def headroom(other):
 import split_storage
 try:split_storage.check(other=other);return True
 except RuntimeError:return False
def output_bytes(root):
 total=0
 for directory,_,files in os.walk(root,followlinks=False):
  for name in files:
   path=Path(directory)/name
   if path.is_symlink():continue
   try:total+=path.stat().st_size
   except FileNotFoundError:continue
 return total

def stop_child(child):
 if child is not None and child.poll() is None:
  child.terminate()
  try:child.wait(timeout=3)
  except subprocess.TimeoutExpired:
   child.kill();child.wait(timeout=3)
 if child is not None and child.poll() is None:raise RuntimeError('captured child survived escalation')

def listening(pid,port):
 inodes=set()
 for line in Path('/proc/net/tcp').read_text().splitlines():
  p=line.split()
  if len(p)>=10 and p[3]=='0A' and int(p[1].split(':')[1],16)==port:inodes.add(p[9])
 for f in Path('/proc',str(pid),'fd').iterdir():
  try:target=os.readlink(f)
  except FileNotFoundError:continue
  if target.startswith('socket:[') and target[8:-1] in inodes:return True
 return False

def child_env(root,extra):
 env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':'/mnt/micron/codex3-lanes/orchestrator:/mnt/raid0/llm/epyc-orchestrator/.venv/lib/python3.11/site-packages','TIKTOKEN_CACHE_DIR':'/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/tiktoken-cache','HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
 if 'HOME' in os.environ: env['HOME']=os.environ['HOME']
 env.update(TMPDIR=str(root),XDG_CACHE_HOME=str(root/'cache'),HF_HOME=str(root/'hf'),REDEL_HOME=str(root/'redel-home'),REDEL_CACHE=str(root/'redel-cache'))
 env.update(extra);return env

def record_broker_error(root,phase,exc,errors,guard):
 with guard:
  errors.append(repr(exc))
  create(root/('broker-error-'+str(len(errors))+'.json'),{'phase':phase,'exception_type':type(exc).__name__,'message':str(exc)[:2048]})

def run_arm(arm,prompt,attempt,server,server_birth,other,capture_request=False,milestone=False):
 root=attempt/arm;root.mkdir();create(root/'prompt.json',{'prompt':prompt})
 observer=RequestCapture(root/'outbound-requests') if capture_request and arm=='redel_delegate_wait' else None
 from entry_gate import EntryGate,DrainGate
 entry_gate=EntryGate() if milestone and arm=='production_repl' else None
 drain_gate=DrainGate() if milestone and arm=='redel_delegate_wait' else None
 browse=BrowseBackend(root/'browse-calls.jsonl')
 pairs=[socket.socketpair() for _ in range(3)];fds=[b.fileno() for a,b in pairs];policy=RequestPolicy('pinned');usage=UsageLedger();depths=[];evidence=[];errors=[];quiescent_resets=[];guard=threading.Lock();repl_response=entry_gate.ready if entry_gate else threading.Event()
 upstream=Upstream(PORT,server.pid,server_birth,END,stopped,lambda:witness(server.pid,server_birth));repl=REPLUpstream(upstream,usage)
 def call(path,body):
  result=repl(path,body)
  with guard:evidence.append(upstream.local.evidence)
  return result
 def admit(req,res):
  with guard:depths.append(req['depth'])
 def broker(sock):
  phase='receive'
  try:
   while not stopped():
    phase='receive';req=recv(sock);phase='dispatch'
    def dispatch_one():
     if isinstance(req,dict) and req.get('path') in ('/tool/search','/tool/visit'):
      if set(req)!={'path','body'} or not isinstance(req['body'],dict) or set(req['body'])!={'value','max_results'}:raise ValueError('invalid tool request')
      send(sock,{'tool_result':browse.invoke(req['path'].rsplit('/',1)[1],req['body']['value'],req['body']['max_results'])})
     elif arm=='production_repl':serve_one(sock,policy,call,admit,req)
     else:
      serve_stream(sock,policy,upstream,usage,observer,req)
      with guard:evidence.append(upstream.local.evidence)
    if drain_gate is not None:
     if not drain_gate.begin():break
     try:dispatch_one()
     except BaseException:
      drain_gate.end();raise
     if isinstance(req,dict) and req.get('path')=='/v1/chat/completions':
      begin=time.monotonic();drain_gate.finish_first_and_drain(stopped)
      create(root/'entry-quiesce.json',{'schema':'evl34-entry-quiescence/v1','all_inflight_drained':True,'acknowledged':True,'wait_seconds':time.monotonic()-begin})
      drain_gate.ready.set()
     else:drain_gate.end()
    elif entry_gate is None:
     dispatch_one()
    elif not entry_gate.dispatch(dispatch_one,first_model_response=isinstance(req,dict) and req.get('path')=='/v1/chat/completions'):
     break
  except EOFError as exc:
   if phase!='receive':record_broker_error(root,phase,exc,errors,guard)
  except ConnectionResetError as exc:
   if phase=='receive' and drain_gate is not None and drain_gate.is_acknowledged():
    with guard:quiescent_resets.append({'phase':phase,'exception_type':type(exc).__name__,'after_ack':True})
   else:record_broker_error(root,phase,exc,errors,guard)
  except BaseException as exc:
   record_broker_error(root,phase,exc,errors,guard)
   sock.close()
 threads=[threading.Thread(target=broker,args=(a,)) for a,b in pairs]
 for t in threads:t.start()
 py='/mnt/micron/codex3-evl34-deepdive-r9-20261030/bin/python3.11'
 entry=D/('repl_live_entry.py' if arm=='production_repl' else 'redel_live_entry.py')
 deny=credential_paths()+['/mnt/raid0/llm/tmp/codex3-evl34-deepdive-prep-20261030/qa_rl.parquet','/mnt/raid0/llm/tmp/codex3-evl34-deepdive-prep-20261030/COHORT-PRIVATE.json',str(D/'PILOT-PRIVATE.json'),str(D/'CONTROL-PRIVATE.json'),'/mnt/raid0/llm/datasets','/mnt/raid0/llm/hf-home/datasets','/mnt/raid0/llm/tmp/evl34-real-natural-delegation-20261029','/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/hotpot-validation-first10.json']
 entry_args=[py,str(entry),str(root),','.join(map(str,fds))]
 cmd,extra=wrap(entry_args,policy=Policy(),extra_allow=[str(root)],deny_paths=deny)
 env=child_env(root,extra)
 if arm=='redel_delegate_wait':env['PYTHONPATH']='/mnt/raid0/llm/tmp/codex-evl34-delegation-20261029/venv/lib/python3.11/site-packages'
 def filecap():resource.setrlimit(resource.RLIMIT_FSIZE,(16*1024**2,16*1024**2))
 child=None;beg=time.monotonic();stopped_at_entry=False
 try:
  with (root/'child.log').open('xb') as log:
   child=subprocess.Popen(cmd,pass_fds=fds,env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=filecap)
   for a,b in pairs:b.close()
   while child.poll() is None:
    if milestone and ((arm=='production_repl' and repl_response.is_set()) or (arm=='redel_delegate_wait' and drain_gate.ready.is_set())):
     stopped_at_entry=True;stop_child(child);break
    if stopped() or not headroom(other) or server.poll() is not None or output_bytes(attempt)>OUTPUT_STOP:raise RuntimeError('stop, disk reservation, output budget or server lost')
    time.sleep(.05)
   if milestone and arm=='redel_delegate_wait' and drain_gate.ready.is_set():stopped_at_entry=True
   if child.returncode!=0 and not stopped_at_entry:raise RuntimeError('native child failed; broker errors='+str(len(errors)))
  for t in threads:t.join(5)
  if any(t.is_alive() for t in threads) or errors:raise RuntimeError('broker not clean: '+repr(errors))
  if len(evidence)!=len(usage.records) or not evidence:raise RuntimeError('capture incomplete')
  total=usage.totals()
  if total is None:raise RuntimeError('server usage unavailable')
  if arm=='production_repl' and stopped_at_entry:
   native={'status':'partial_entry_repl','flat_server_bound_attested':True}
  elif arm=='production_repl':
   raw=json.loads((root/'response.json').read_bytes());events=raw.get('delegation_events')
   if raw.get('mode')!='repl' or not isinstance(events,list):raise RuntimeError('bad native response')
   native={'status':'complete','answer':raw['answer'],'delegations':sum(x==1 for x in depths),'max_depth':max(depths,default=0),'flat_server_bound_attested':True,'depth_basis':'child-attributed tracked REPL calls; not whole-graph depth','graph_delegation_events':events,'response':raw}
  elif milestone and stopped_at_entry:
   native={'status':'partial_entry_redel','flat_server_bound_attested':True}
  else:native=project_redel(json.loads((root/'events.json').read_bytes()),total,True)
  native.update(browse_records=browse.records,server_usage=total,wall_seconds=time.monotonic()-beg,broker_depths=depths,request_evidence=evidence,quiescent_resets=quiescent_resets)
  return native
 finally:
  for a,b in pairs:
   try:b.close()
   except OSError:pass
  try:
   stop_child(child)
  finally:
   for a,b in pairs:
    try:a.shutdown(socket.SHUT_RDWR)
    except OSError:pass
    a.close()
   for t in threads:t.join(3)
  if any(t.is_alive() for t in threads):raise RuntimeError('owned broker thread not drained')

