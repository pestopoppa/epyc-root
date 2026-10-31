#!/usr/bin/env python3
"""Private trace replay. Original requests are never printed or copied into results."""
import hashlib,json,os,pathlib,signal,socket,subprocess,sys,tempfile,threading,time,urllib.request
D=pathlib.Path(__file__).resolve().parent;R=pathlib.Path('/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/kpf64_replay');sys.path.insert(0,str(R));import adapter
B=pathlib.Path('/mnt/raid0/llm/kernels/production/cpu');MODEL='/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf';SMALL='/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf';TEMPLATE='/mnt/raid0/llm/models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def atom(p,obj):
 fd,n=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(obj,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(n,p)
 finally:os.unlink(n)
def atom_text(p,data):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:f.write(data);f.flush();os.fsync(f.fileno())
def main():
 mode=os.environ['DSC_MODE'];assert mode in ('smoke','full');out=D/os.environ.get('DSC_OUT','run');out.mkdir(exist_ok=True);deadline=int(os.environ['FILLER_DEADLINE'])-30;fid=os.getenv('FILLER_ID');gp=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(fid+'.grant') if fid else None;grant=gp.read_text() if gp and gp.is_file() else None
 if mode=='full' and (not grant or not os.getenv('FILLER_CPUS')):raise RuntimeError('actual grant missing')
 if mode=='full':
  plan=json.loads((D/'CASE-PLAN.json').read_text());spec=json.loads((D/'PREDECLARED.json').read_text())
  if plan['predeclared_sha256']!=sha(D/'PREDECLARED.json') or plan['token_index_sha256']!=sha(D/'TOKEN-INDEX.json') or plan['private_source_catalog_sha256']!=sha(D/'PRIVATE-SESSION-SHA256SUMS') or plan['inference_started'] is not False:raise RuntimeError('predeclared plan drift')
  sessions={}
  for p in (D/'private-sessions').glob('*.json'):
   if p.name=='manifest.json':continue
   j=json.loads(p.read_text());sessions[j['id']]=j
  cases=[]
  for group in plan['groups']:
   for item in group['chosen']:
    session=sessions[item['session']];prompts={k:prompt for k,prompt,_ in adapter.iter_prompts(session['turns'],None,slot_holds_output=False)};seq=[]
    for q in item['turns']:
     text=prompts[q['turn']]
     if hashlib.sha256(text.encode()).hexdigest()!=q['prompt_sha256']:raise RuntimeError('private prompt drift')
     seq.append({'id':q['turn'],'prompt':text,'prompt_sha256':q['prompt_sha256'],'expected_tokens':q['prompt_tokens']})
    cases.append({'id':group['store']+'-'+group['stratum']+'-'+item['session'],'store':group['store'],'stratum':group['stratum'],'session':item['session'],'seq':seq})
 else:
  def control_tokens(text):
   env=os.environ.copy();env.update(LD_LIBRARY_PATH=str(B),OMP_NUM_THREADS='1',HIP_VISIBLE_DEVICES='-1',ROCR_VISIBLE_DEVICES='-1')
   result=subprocess.run([str(B/'llama-tokenize'),'-m',SMALL,'--stdin','--ids','--no-escape'],input=text.encode(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env,timeout=60)
   if result.returncode:raise RuntimeError('engineering tokenizer failed')
   return len(json.loads(result.stdout))
  text='Explain how a retry loop should handle a transient network error in a short code review.';cases=[{'id':'engineering-control','store':'engineering','stratum':'engineering','session':'synthetic-control','seq':[{'id':0,'prompt':text,'prompt_sha256':hashlib.sha256(text.encode()).hexdigest(),'expected_tokens':control_tokens(text)},{'id':1,'prompt':text+' First check the retry limit. Then describe the next safe step.','prompt_sha256':hashlib.sha256((text+' First check the retry limit. Then describe the next safe step.').encode()).hexdigest(),'expected_tokens':control_tokens(text+' First check the retry limit. Then describe the next safe step.')}]}];plan={'unfilled_sequence_slots':None}
 stopped=False
 def handle(*_):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGTERM,handle);signal.signal(signal.SIGINT,handle)
 def stop():return stopped or (D/'STOP').exists() or time.time()>=deadline
 def partial(reason):
  p=out/'.partial.tmp';p.write_text(json.dumps({'partial':True,'reason':reason})+'\n');os.replace(p,out/'PARTIAL.json')
 completed=failures=unknown=0
 for case in cases:
  cid=case['id'];record=out/(cid+'.case.json')
  if record.exists():
   x=json.loads(record.read_text());
   if x['source_sha256']!=sha(D/'SOURCE-SHA256SUMS') or x['plan_sha256']!=(sha(D/'CASE-PLAN.json') if mode=='full' else None):raise RuntimeError('cached envelope drift')
   for name,digest in x.get('artifacts',{}).items():
    if sha(out/name)!=digest:raise RuntimeError('cached result drift: '+name)
   completed+=x['status']=='ok';failures+=x['status']=='failure';unknown+=x['status']=='unknown';continue
  exposures=list(out.glob(cid+'-*.exposure.json'))
  if exposures:
   # Fresh-server cache state cannot replay a previously exposed sequence.
   artifacts={x.name:sha(x) for x in [*out.glob(cid+'-*.exposure.json'),*out.glob(cid+'-*.response.json'),*out.glob(cid+'-*.response.raw')]}
   atom(record,{'id':cid,'status':'unknown','reason':'interrupted exposed sequence; never redraw','exposures':len(exposures),'planned_turns':[q['id'] for q in case['seq']],'artifacts':artifacts,'source_sha256':sha(D/'SOURCE-SHA256SUMS'),'plan_sha256':sha(D/'CASE-PLAN.json') if mode=='full' else None});unknown+=1;continue
  if stop() or (mode=='full' and time.time()+5460>=deadline):partial('before fresh server or insufficient complete sequence budget');return 75
  segment=cid+'-segment-'+str(time.time_ns());server_record=out/(segment+'.server.json');events_path=out/(segment+'.server.jsonl');drain=out/(segment+'.drain.json')
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  threads=2 if mode=='smoke' else min(24,len(os.sched_getaffinity(0)));model=SMALL if mode=='smoke' else MODEL
  cmd=[str(B/'llama-server'),'-m',model,'--host','127.0.0.1','--port',str(port),'-np','1' if mode=='smoke' else '4','-c','2048' if mode=='smoke' else '262144','-t',str(threads),'-ub','2048','--flash-attn','on','--jinja','-ctk','q8_0','-ctv','q8_0','-ngl','0','--spec-type','none' if mode=='smoke' else 'draft-mtp','--spec-draft-n-max','4','-lv','4']
  if mode=='full':cmd+=['--no-mmap','--mlock','--cache-ram','32768','--ctx-checkpoints','32','--chat-template-file',TEMPLATE]
  env=os.environ.copy();env.update(LD_LIBRARY_PATH=str(B),OMP_NUM_THREADS='1',HIP_VISIBLE_DEVICES='-1',ROCR_VISIBLE_DEVICES='-1');p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env,text=True,errors='replace',bufsize=1);birth=pathlib.Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19];events=[];lock=threading.Lock()
  try:
   atom(server_record,{'schema':'dsc25592.server.v1','id':cid,'pid':p.pid,'birth':birth,'argv':cmd,'mode':mode,'grant_id':fid,'grant_text':grant,'grant_sha256':hashlib.sha256(grant.encode()).hexdigest() if grant else None,'affinity':sorted(os.sched_getaffinity(0)),'binary_sha256':sha(B/'llama-server'),'model_sha256':os.environ['DSC_SMALL_SHA'] if mode=='smoke' else os.environ['DSC_MODEL_SHA'],'source_catalog_sha256':sha(D/'SOURCE-SHA256SUMS'),'plan_sha256':sha(D/'CASE-PLAN.json') if mode=='full' else None,'started_epoch':time.time()})
  except BaseException:
   if p.poll() is None:
    p.terminate()
    try:p.wait(10)
    except subprocess.TimeoutExpired:p.kill();p.wait()
   raise
  def reader():
   with events_path.open('x') as f:
    for line in p.stdout:
     item={'epoch':time.time(),'text':line.rstrip('\n')};f.write(json.dumps(item,ensure_ascii=False)+'\n');f.flush()
     if 'forcing full prompt re-processing' in line:
      os.fsync(f.fileno())
      with lock:events.append(item['epoch'])
  th=threading.Thread(target=reader,daemon=True);th.start();seq_ok=True;failure=[]
  try:
   url='http://127.0.0.1:'+str(port);ready=False;limit=time.monotonic()+(120 if mode=='smoke' else 1800)
   while time.monotonic()<limit and p.poll() is None and not stop():
    try:
     with urllib.request.urlopen(url+'/health',timeout=1) as r:ready=r.status==200
    except Exception:pass
    if ready:break
    time.sleep(.2)
   if stop():partial('server startup interrupted');return 75
   if not ready:seq_ok=False;failure.append('server_not_ready')
   if ready:
    for q in case['seq']:
     if stop() or (mode=='full' and time.time()+1240>=deadline):partial('before request or insufficient native cap');return 75
     key=cid+'-'+str(q['id']);exp=out/(key+'.exposure.json');rp=out/(key+'.response.json');payload={'prompt':q['prompt'],'n_predict':1 if mode=='full' else 8,'cache_prompt':True,'temperature':0,'stream':False,'return_tokens':False,'id_slot':0};start=time.time();atom(exp,{'schema':'dsc25592.exposure.v1','case':cid,'session':case['session'],'store':case['store'],'stratum':case['stratum'],'turn':q['id'],'prompt_sha256':q['prompt_sha256'],'expected_prompt_tokens':q['expected_tokens'],'server_record_sha256':sha(server_record),'started_epoch':start,'request_settings':{k:v for k,v in payload.items() if k!='prompt'}});state={}
     def request():
      try:
       req=urllib.request.Request(url+'/completion',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
       with urllib.request.urlopen(req,timeout=1200) as r:state['http_status']=r.status;state['raw']=r.read().decode()
      except Exception as exc:state['error']=repr(exc)
     worker=threading.Thread(target=request,daemon=True);worker.start();samples=[];last=0
     while worker.is_alive() and p.poll() is None and not stop():
      if time.monotonic()-last>=5:
       samples.append({'epoch':time.time(),'child_pid':p.pid,'child_birth':birth,'sampled_while_child_live':p.poll() is None,'grant_sha256':hashlib.sha256(grant.encode()).hexdigest() if grant else None,'loadavg':pathlib.Path('/proc/loadavg').read_text().strip()});last=time.monotonic()
      worker.join(.05)
     if stop():partial('exposed request interrupted');return 75
     worker.join(1);end=time.time()
     if worker.is_alive() or 'error' in state:seq_ok=False;failure.append({'turn':q['id'],'error':state.get('error','server exited')});continue
     try:body=json.loads(state['raw'])
     except Exception:body={}
     timings=body.get('timings') if isinstance(body,dict) else None;cache=timings.get('cache_n') if isinstance(timings,dict) else None;prompt=timings.get('prompt_n') if isinstance(timings,dict) else None;total=cache+prompt if isinstance(cache,int) and isinstance(prompt,int) else None;token_match=(total==q['expected_tokens']) if q['expected_tokens'] is not None and total is not None else None;live_sample=any(x['sampled_while_child_live'] and (mode=='smoke' or x['grant_sha256']==hashlib.sha256(grant.encode()).hexdigest()) for x in samples);valid=state['http_status']==200 and total is not None and live_sample and (q['expected_tokens'] is None or token_match)
     if not valid:seq_ok=False;failure.append({'turn':q['id'],'reason':'native_cache_or_prompt_unknown'})
     # Preserve the complete native response privately; it may echo trace text.
     rawfile=out/(key+'.response.raw');atom_text(rawfile,state['raw'])
     atom(rp,{'schema':'dsc25592.response.v1','exposure_sha256':sha(exp),'http_status':state['http_status'],'native_raw_sha256':sha(rawfile),'native_total_prompt_tokens':total,'expected_token_count_match':token_match,'native_timings':timings,'native_stop':body.get('stop') if isinstance(body,dict) else None,'native_content_sha256':hashlib.sha256(str(body.get('content','')).encode()).hexdigest() if isinstance(body,dict) else None,'samples':samples,'ended_epoch':end,'status':'ok' if valid else 'unknown'} )
  finally:
   if p.poll() is None:
    p.terminate()
    try:p.wait(10)
    except subprocess.TimeoutExpired:p.kill();p.wait()
   th.join(10)
   if th.is_alive() or p.poll() is None:raise RuntimeError('server or log reader not drained')
   atom(drain,{'pid':p.pid,'birth':birth,'rc':p.returncode,'reaped':True,'server_log_sha256':sha(events_path)})
  if stop():partial('after server');return 75
  artifacts={x.name:sha(x) for x in [server_record,events_path,drain,*out.glob(cid+'-*.exposure.json'),*out.glob(cid+'-*.response.json'),*out.glob(cid+'-*.response.raw')]}
  windows=[]
  for q in case['seq']:
   ep=out/(cid+'-'+str(q['id'])+'.exposure.json');rp=out/(cid+'-'+str(q['id'])+'.response.json')
   if ep.exists() and rp.exists():
    a=json.loads(ep.read_text())['started_epoch'];b=json.loads(rp.read_text())['ended_epoch'];windows.append({'turn':q['id'],'start':a,'end':b,'forced_events_observed_in_window':sum(a<=v<=b for v in events)})
  unassigned=[v for v in events if not any(w['start']<=v<=w['end'] for w in windows)]
  turn_states=[]
  for q in case['seq']:
   ep=out/(cid+'-'+str(q['id'])+'.exposure.json');rp=out/(cid+'-'+str(q['id'])+'.response.json')
   turn_states.append({'turn':q['id'],'status':json.loads(rp.read_text())['status'] if rp.exists() else 'unknown','exposed':ep.exists()})
  atom(record,{'id':cid,'artifacts':artifacts,'turn_states':turn_states,'status':'ok' if seq_ok else 'failure','failures':failure,'forced_event_count_in_full_server_log':len(events),'forced_event_timestamps':events,'observed_request_windows':windows,'forced_events_outside_observed_windows':unassigned,'attribution_note':'stderr line arrival times; outside-window events stay unassigned, not silently attributed or discarded','server_sha256':sha(server_record),'server_log_sha256':sha(events_path),'drain_sha256':sha(drain),'source_sha256':sha(D/'SOURCE-SHA256SUMS'),'plan_sha256':sha(D/'CASE-PLAN.json') if mode=='full' else None});completed+=seq_ok;failures+=not seq_ok
 atom(out/'TERMINAL.json',{'partial':False,'mode':mode,'sequence_count':len(cases),'counts':{'ok':completed,'failure':failures,'unknown':unknown},'unfilled_predeclared_sequences':plan['unfilled_sequence_slots'],'state':'complete_raw' if not failures and not unknown and not plan['unfilled_sequence_slots'] else 'incomplete_raw','verdict':None});return 0
if __name__=='__main__':sys.exit(main())
