#!/usr/bin/env python3
"""CAFE-1 native one-window capture; control uses a small model with no MTP."""
import hashlib,json,os,pathlib,signal,socket,subprocess,sys,tempfile,threading,time,urllib.request
D=pathlib.Path(__file__).resolve().parent;B=pathlib.Path('/mnt/raid0/llm/kernels/production/cpu');TARGET='/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf';SMALL='/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf';TEMPLATE='/mnt/raid0/llm/models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja'
def sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def atom(p,o):
 fd,n=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(o,f,sort_keys=True,ensure_ascii=False);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(n,p)
 finally:os.unlink(n)
def main():
 mode=os.environ['CAFE_MODE'];assert mode in ('smoke','full');out=D/os.environ.get('CAFE_OUT','run');out.mkdir(exist_ok=True);deadline=int(os.environ['FILLER_DEADLINE'])-30; stopped=False
 fid=os.getenv('FILLER_ID');gp=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(fid+'.grant') if fid else None;grant=gp.read_text() if gp and gp.is_file() else None
 if mode=='full' and (not grant or not os.getenv('FILLER_CPUS')):raise RuntimeError('actual grant missing')
 if mode=='full' and list(out.glob('*.exposure.json')):
  n=len(list(out.glob('*.response.json')));atom(out/'TERMINAL.json',{'partial':False,'state':'incomplete_interrupted_single_window','response_count':n,'unknown':75-n,'verdict':None});return 0
 def handler(*_):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGTERM,handler);signal.signal(signal.SIGINT,handler)
 def stopping():return stopped or (D/'STOP').exists() or time.time()>=deadline
 def partial(reason):
  q=out/'PARTIAL.json';t=out/'.partial.tmp';t.write_text(json.dumps({'partial':True,'reason':reason})+'\n');os.replace(t,q)
 prompts={x['id']:x for x in json.loads((D/'PROMPTS.json').read_text())['prompts']};arms=[('A0',0),('P05',.5),('P075',.75),('P09',.9),('A0_repeat',0)];nblocks=1 if mode=='smoke' else 5;completed=0;failures=[]
 for block in range(nblocks):
  order=arms[block:]+arms[:block]
  if mode=='smoke':order=order[:2]
  for arm,pmin in order:
   if stopping() or (mode=='full' and time.time()+2440>=deadline):partial('insufficient budget for fresh server and one request');return 75
   session=f'{block}-{arm}';logpath=out/(session+'.server.log')
   with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
   threads=2 if mode=='smoke' else 96;model=SMALL if mode=='smoke' else TARGET;ctx='2048' if mode=='smoke' else '262144';slots='1' if mode=='smoke' else '4'
   cmd=[str(B/'llama-server'),'-m',model,'--host','127.0.0.1','--port',str(port),'-np',slots,'-c',ctx,'-t',str(threads),'-ub','2048','--flash-attn','on','--jinja','-ctk','q8_0','-ctv','q8_0','-ngl','0','--spec-type','none' if mode=='smoke' else 'draft-mtp','--spec-draft-n-max','4','--spec-draft-p-min',str(pmin)]
   if mode=='full':cmd=['numactl','--interleave=all',*cmd,'--no-mmap','--mlock','--cache-ram','32768','--ctx-checkpoints','32','--chat-template-file',TEMPLATE]
   env=os.environ.copy();env.update(LD_LIBRARY_PATH=str(B),OMP_NUM_THREADS='1',HIP_VISIBLE_DEVICES='-1',ROCR_VISIBLE_DEVICES='-1');log=logpath.open('xb');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env);birth=pathlib.Path('/proc',str(p.pid),'stat').read_text().split(') ')[1].split()[19];serverfile=out/(session+'.server.json');atom(serverfile,{'schema':'cafe1.server.v1','mode':mode,'block':block,'arm':arm,'p_min':pmin,'argv':cmd,'pid':p.pid,'birth':birth,'grant_text':grant,'grant_id':fid,'regions':os.getenv('WS58_REGIONS') or os.getenv('FILLER_CPUS'),'affinity':sorted(os.sched_getaffinity(0)),'source_catalog_sha256':sha(D/'SOURCE-SHA256SUMS'),'plan_sha256':sha(D/'PLAN.json'),'model_sha256':os.environ['CAFE_SMALL_SHA'] if mode=='smoke' else os.environ['CAFE_FULL_SHA'],'binary_sha256':sha(B/'llama-server'),'control_no_mtp':mode=='smoke','started_epoch':time.time()})
   try:
    url='http://127.0.0.1:'+str(port);ready=False;limit=time.monotonic()+(120 if mode=='smoke' else 1800)
    while time.monotonic()<limit and p.poll() is None and not stopping():
     try:
      with urllib.request.urlopen(url+'/health',timeout=1) as r:ready=r.status==200
     except Exception:pass
     if ready:break
     time.sleep(.2)
    if stopping():partial('startup interrupted');return 75
    if not ready:failures.append({'block':block,'arm':arm,'reason':'server_not_ready','returncode':p.poll()});continue
    proof={}
    for name,path in [('status',f'/proc/{p.pid}/status'),('numa_maps',f'/proc/{p.pid}/numa_maps'),('locks','/proc/locks')]:
     try:
      data=pathlib.Path(path).read_text(); target=out/(session+'.'+name+'.txt');target.write_text(data);proof[name]={'sha256':sha(target),'path':target.name}
     except OSError as exc:proof[name]={'unknown':repr(exc)}
    atom(out/(session+'.residency.json'),{'pid':p.pid,'birth':birth,'epoch':time.time(),'evidence':proof})
    # Query the server's actual template. The small control uses its own native template.
    ids=[f'code-{block}',f'rag-{block}',f'prose-{block}'] if mode=='full' else ['code-0']
    for ident in ids:
     if stopping() or (mode=='full' and time.time()+640>=deadline):partial('insufficient budget for full native request and cleanup');return 75
     item=prompts[ident];prefix=out/(session+'-'+ident);exp=pathlib.Path(str(prefix)+'.exposure.json');res=pathlib.Path(str(prefix)+'.response.json')
     if exp.exists() or res.exists():raise RuntimeError('attempt already exposed')
     def post(path,payload):
      req=urllib.request.Request(url+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
      with urllib.request.urlopen(req,timeout=10 if path=='/apply-template' else 600) as r:return r.status,r.read().decode()
     try:
      _,template=post('/apply-template',{'messages':[{'role':'user','content':item['prompt']}],'chat_template_kwargs':{'enable_thinking':False}});formatted=json.loads(template)['prompt']
     except Exception as exc:failures.append({'block':block,'arm':arm,'prompt_id':ident,'reason':'template_error','error':repr(exc)});continue
     payload={'prompt':formatted,'temperature':0,'top_k':1,'seed':42,'n_predict':16 if mode=='smoke' else 128,'cache_prompt':False,'return_tokens':True};atom(exp,{'schema':'cafe1.native_exposure.v1','block':block,'arm':arm,'p_min':pmin,'prompt_id':ident,'prompt_class':item['class'],'prompt_sha256':item['prompt_sha256'],'formatted_prompt_sha256':hashlib.sha256(formatted.encode()).hexdigest(),'request':payload,'server_record_sha256':sha(serverfile),'epoch':time.time()});state={}
     def request():
      try:state['http_status'],state['raw']=post('/completion',payload)
      except Exception as exc:state['error']=repr(exc)
     th=threading.Thread(target=request,daemon=True);th.start();samples=[];last=0
     while th.is_alive() and p.poll() is None and not stopping():
      if time.monotonic()-last>=1:
       try:status=pathlib.Path('/proc',str(p.pid),'status').read_text()
       except FileNotFoundError:status='unavailable'
       samples.append({'epoch':time.time(),'server_alive':p.poll() is None,'loadavg':pathlib.Path('/proc/loadavg').read_text().strip(),'server_status_sha256':hashlib.sha256(status.encode()).hexdigest(),'grant_sha256':hashlib.sha256(grant.encode()).hexdigest() if grant else None});last=time.monotonic()
      th.join(.05)
     if stopping():partial('interrupted exposed request');return 75
     th.join(1)
     if th.is_alive() or 'error' in state:failures.append({'block':block,'arm':arm,'prompt_id':ident,'reason':'request_error','error':state.get('error','server exited')});continue
     try:body=json.loads(state['raw'])
     except Exception:body=None
     atom(res,{'schema':'cafe1.native_response.v1','exposure_sha256':sha(exp),'http_status':state['http_status'],'raw':state['raw'],'raw_sha256':hashlib.sha256(state['raw'].encode()).hexdigest(),'parsed':body,'samples':samples,'finished_epoch':time.time()});completed+=1
   finally:
    if p.poll() is None:
     p.terminate()
     try:p.wait(10)
     except subprocess.TimeoutExpired:p.kill();p.wait()
    log.close()
    if p.poll() is None:raise RuntimeError('server not drained')
    atom(out/(session+'.drain.json'),{'pid':p.pid,'birth':birth,'rc':p.returncode,'reaped':True,'server_log_sha256':sha(logpath)})
 expected=2 if mode=='smoke' else 75;atom(out/'TERMINAL.json',{'partial':False,'mode':mode,'responses':completed,'expected':expected,'failures':failures,'unknown':expected-completed,'state':'complete_raw' if completed==expected and not failures else 'incomplete_raw','verdict':None,'control_no_mtp':mode=='smoke'});return 0
if __name__=='__main__':sys.exit(main())
