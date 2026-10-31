#!/usr/bin/env python3
import hashlib,json,os,pathlib,signal,socket,subprocess,sys,tempfile,threading,time,urllib.request
D=pathlib.Path(__file__).resolve().parent;B=pathlib.Path('/mnt/raid0/llm/kernels/archive/cpu-20260810-0db32c06e/bin');M=pathlib.Path('/mnt/raid0/llm/models/sw2-stories15m-pinned-20261031')
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def atom(p,o):
 fd,t=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(o,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(t,p)
 finally:os.unlink(t)
def main():
 mode=os.environ['SW2_MODE'];assert mode in ('smoke','full');out=D/os.environ.get('SW2_OUT','run');out.mkdir(exist_ok=True);end=int(os.environ['FILLER_DEADLINE'])-20;stop=False
 fid=os.getenv('FILLER_ID');gp=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(fid+'.grant') if fid else None;grant=gp.read_text() if gp and gp.is_file() else None
 if mode=='full' and (not grant or not os.getenv('FILLER_CPUS')):raise RuntimeError('actual grant missing')
 if mode=='full' and any(out.glob('*.exposure.json')):
  # A new server would destroy the original one-slot continuity. Preserve
  # exposed requests and terminally report the abandoned sequence; never redraw.
  n=sum((out/(str(i)+'.response.json')).exists() for i in range(4))
  atom(out/'TERMINAL.json',{'partial':False,'mode':mode,'responses':n,'unknown':4-n,'verdict':None,'state':'incomplete_interrupted_slot_sequence','scope':'private v9 tiny model; no current production claim'})
  return 0
 def signal_handler(*_):
  nonlocal stop;stop=True
 signal.signal(signal.SIGINT,signal_handler);signal.signal(signal.SIGTERM,signal_handler)
 def stopped():return stop or (D/'STOP').exists() or time.time()>=end
 def partial(why):
  p=out/'PARTIAL.json';t=out/'.partial.tmp';t.write_text(json.dumps({'partial':True,'reason':why})+'\n');os.replace(t,p)
 # Distinct control prompts are disjoint from full cohort; no warm repeated prompt.
 prompts=(['The red kite moved above the','A small boat crossed the','The baker carried a warm','A quiet fox waited near the'] if mode=='smoke' else ['At sunrise the gardener opened the','A traveler found a silver key beside the','On Tuesday the little dog followed the','The painter chose a bright color for the'])
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 env=os.environ.copy();env.update(LD_LIBRARY_PATH=str(B)+':'+str(D/'runtime-libs'),OMP_NUM_THREADS='1',HIP_VISIBLE_DEVICES='-1',ROCR_VISIBLE_DEVICES='-1');cmd=[str(B/'llama-server'),'-m',str(M/'target.gguf'),'--model-draft',str(M/'draft.gguf'),'--spec-type','draft-simple','--spec-draft-n-max','8','--spec-draft-n-min','0','--host','127.0.0.1','--port',str(port),'-np','1','-c','2048','-t',str(min(8,len(os.sched_getaffinity(0)))),'-ngl','0','--no-warmup']
 session=str(time.time_ns());log=(out/('server-'+session+'.log')).open('xb');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env); birth=pathlib.Path('/proc',str(p.pid),'stat').read_text().split(') ')[1].split()[19];atom(out/('SERVER-'+session+'.json'),{'session_id':session,'grant_text':grant,'argv':cmd,'pid':p.pid,'birth':birth,'binary_sha256':sha(B/'llama-server'),'target_sha256':sha(M/'target.gguf'),'draft_sha256':sha(M/'draft.gguf'),'plan_sha256':sha(D/'PLAN.json'),'source_catalog_sha256':sha(D/'SOURCE-SHA256SUMS'),'grant_id':os.getenv('FILLER_ID'),'regions':os.getenv('WS58_REGIONS') or os.getenv('FILLER_CPUS'),'affinity':sorted(os.sched_getaffinity(0))})
 try:
  url='http://127.0.0.1:'+str(port);ready=False;limit=time.monotonic()+120
  while time.monotonic()<limit and p.poll() is None and not stopped():
   try:
    with urllib.request.urlopen(url+'/health',timeout=1) as r:ready=r.status==200
   except Exception:pass
   if ready:break
   time.sleep(.2)
  if stopped():partial('stop during startup');return 75
  if not ready:raise RuntimeError('server not ready rc='+str(p.poll()))
  cases=[0,7,12,None]
  for i,cap in enumerate(cases):
   if stopped():partial('stop before request');return 75
   e=out/(str(i)+'.exposure.json');res=out/(str(i)+'.response.json');
   if res.exists():continue
   if e.exists():continue
   payload={'prompt':prompts[i],'temperature':0.0,'top_k':1,'n_predict':16,'cache_prompt':False,'id_slot':0};
   if cap is not None:payload['speculative.n_max']=cap
   atom(e,{'request':payload,'request_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(),'epoch':time.time(),'slot_requested':0,'server_session':session}); state={}
   def request():
    try:
     req=urllib.request.Request(url+'/completion',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
     with urllib.request.urlopen(req,timeout=120) as response:state.update(http_status=response.status,raw=response.read().decode())
    except Exception as exc:state['error']=repr(exc)
   th=threading.Thread(target=request,daemon=True);th.start()
   while th.is_alive() and not stopped() and p.poll() is None:th.join(.1)
   if stopped():partial('interrupted exposed request');return 75
   th.join(1)
   if th.is_alive() or 'error' in state:atom(out/(str(i)+'.error.json'),{'status':'unknown','error':state.get('error','server exited'),'request_sha256':sha(e)});continue
   try:body=json.loads(state['raw'])
   except Exception:body=None
   atom(res,{'http_status':state['http_status'],'raw':state['raw'],'response_sha256':hashlib.sha256(state['raw'].encode()).hexdigest(),'parsed':body,'request_file_sha256':sha(e),'epoch':time.time()})
  count=sum((out/(str(i)+'.response.json')).exists() for i in range(4));atom(out/'TERMINAL.json',{'partial':False,'mode':mode,'responses':count,'unknown':4-count,'verdict':None,'scope':'private v9 tiny model; no current production claim'});return 0
 finally:
  if p.poll() is None:
   p.terminate()
   try:p.wait(5)
   except subprocess.TimeoutExpired:p.kill();p.wait()
  log.close()
  if p.poll() is None:raise RuntimeError('server did not drain')
if __name__=='__main__':sys.exit(main())
