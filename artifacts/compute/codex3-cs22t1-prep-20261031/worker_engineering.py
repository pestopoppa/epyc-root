#!/usr/bin/env python3
"""Noncohort model/server format control; no actual T1 scored data."""
import hashlib,json,os,pathlib,resource,signal,socket,subprocess,sys,threading,time,urllib.request
import smoke_admission
D=pathlib.Path(__file__).resolve().parent;out=D/os.environ.get('CS22_OUT','engineering-normal');out.mkdir(exist_ok=True)
smoke_admission.check(sorted(os.sched_getaffinity(0)));resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024**2,8*1024**2))
stop=False
def sig(*_):
 global stop;stop=True
signal.signal(signal.SIGTERM,sig);signal.signal(signal.SIGINT,sig)
def stopped():return stop or (D/'STOP').exists()
def write(name,obj):
 p=out/name;tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(obj,sort_keys=True)+'\n');os.replace(tmp,p)
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close();server='/mnt/raid0/llm/kernels/production/cpu/llama-server';model='/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf';cmd=[server,'--host','127.0.0.1','--port',str(port),'-m',model,'-ngl','0','-c','512','-t','2','-np','1','--no-warmup'];env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':'/mnt/raid0/llm/kernels/production/cpu','OMP_NUM_THREADS':'1','HIP_VISIBLE_DEVICES':'-1','ROCR_VISIBLE_DEVICES':'-1'}
log=(out/'server.log').open('xb');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);birth=pathlib.Path(f'/proc/{p.pid}/stat').read_text().rsplit(') ',1)[1].split()[19];write('SERVER.json',{'pid':p.pid,'birth':birth,'argv':cmd,'port':port});started=time.monotonic();reason=None;result={}
try:
 while time.monotonic()-started<80 and not stopped():
  if p.poll() is not None:raise RuntimeError('server exited during startup')
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=.3) as r:
    if r.status==200:break
  except Exception:time.sleep(.05)
 else:raise RuntimeError('startup interrupted or timeout')
 prompt='Classify whether the speaker is done: I can tell you more after lunch. Answer finished, unfinished, or wait. Answer: '
 payload={'prompt':prompt,'n_predict':1,'temperature':0,'cache_prompt':False,'seed':0,'grammar':'root ::= "finished" | "unfinished" | "wait"'}
 write('EXPOSURE.json',{'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'request':payload,'model':'Qwen3-0.6B-Q8_0','scope':'noncohort engineering only'})
 def request():
  try:
   q=urllib.request.Request(f'http://127.0.0.1:{port}/completion',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(q,timeout=60) as r:result['http']=r.status;result['raw']=r.read().decode()
  except Exception as e:result['error']=repr(e)
 t=threading.Thread(target=request,daemon=True);t.start()
 while t.is_alive() and not stopped():t.join(.02)
 if stopped():reason='interrupted exposed engineering request'
 else:
  t.join();assert 'raw' in result and result['http']==200,result;raw=json.loads(result['raw']);text=raw.get('content');assert text in ('finished','unfinished','wait'),repr(text);assert raw.get('tokens_predicted')==1,raw
  write('RESULT.json',{'scope':'noncohort engineering only','raw':raw,'http':result['http'],'status':'ok','model_class':'small-control','no_full_T1_claim':True})
except Exception as e:reason=reason or repr(e)
finally:
 if p.poll() is None:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=8)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
 log.close()
 if reason:write('PARTIAL.json',{'partial':True,'reason':reason,'server_rc':p.returncode});print(reason);sys.exit(75 if stopped() else 1)
 write('TERMINAL.json',{'state':'complete_engineering_only','server_rc':p.returncode,'partial':False,'full_task':'UNRUN'});sys.exit(0)
