#!/usr/bin/env python3
"""One genuine >64k architect replay per VKQ arm; no transcript in native receipts."""
import hashlib,json,os,pathlib,signal,socket,subprocess,sys,tempfile,threading,time,urllib.request
import mode_guard
D=pathlib.Path(__file__).resolve().parent;K=pathlib.Path('/mnt/raid0/llm/kernels/builds/cpu-20261004-9a3f1392a/bin');B=pathlib.Path('/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/dsc25592');sys.path.insert(0,'/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/kpf64_replay');import adapter
MODEL='/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf';DRAFT='/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf';SMALL='/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def atom(p,o):
 fd,n=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(o,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(n,p)
 finally:os.unlink(n)
def emit(event):mode_guard.emit(D/'events.jsonl',event)
def main():
 mode=os.environ['VKQ3_MODE'];assert mode in ('qualification','full');out=D/('qualification' if mode=='qualification' else 'run');out.mkdir(exist_ok=True);plan=json.loads((D/'PLAN.json').read_text());deadline=int(os.environ['FILLER_DEADLINE'])-30;fid=os.getenv('FILLER_ID');gp=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(fid+'.grant') if fid else None;grant=gp.read_bytes() if gp and gp.is_file() else None
 if not grant or os.environ.get('FILLER_CPUS')!='0-95':raise RuntimeError('genuine whole-host grant missing')
 mode_guard.mode_check(mode,os.environ.get('FILLER_DRYRUN'))
 if mode_guard.target_allowed(mode) and mode_guard.exposure_seen(out):
  atom(out/'TERMINAL.json',{'state':'incomplete_prior_exposure_no_redraw','partial':False,'verdict':None});return 0
 stopped=False
 def handle(*_):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGTERM,handle);signal.signal(signal.SIGINT,handle)
 def stopping():return stopped or mode_guard.stopped(D/'STOP',os.environ.get('FILLER_STOPFILE'),time.time(),deadline) or (not gp.is_file() or gp.read_bytes()!=grant)
 def partial(reason):
  tmp=out/'.partial.tmp';tmp.write_text(json.dumps({'partial':True,'reason':reason})+'\n');os.replace(tmp,out/'PARTIAL.json')
 if mode_guard.target_allowed(mode):
  c=plan['context'];session=json.loads((B/'private-sessions'/(c['session']+'.json')).read_text());prompt=next(p for i,p,_ in adapter.iter_prompts(session['turns'],None,slot_holds_output=False) if i==c['turn'])
  if sha(D/'CONTEXT-METADATA.json')!=plan['context_metadata_sha256'] or hashlib.sha256(prompt.encode()).hexdigest()!=c['sha256']:raise RuntimeError('context envelope changed')
  tkenv={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(K),'OMP_NUM_THREADS':'1','HIP_VISIBLE_DEVICES':'-1','ROCR_VISIBLE_DEVICES':'-1'}
  tk=subprocess.run([str(K/'llama-tokenize'),'-m',MODEL,'--stdin','--ids','--no-escape'],input=prompt.encode(),capture_output=True,env=tkenv,timeout=120,check=True)
  actual_count=len(json.loads(tk.stdout)); del tk
  if actual_count<=65536:raise RuntimeError('architect tokenizer count mismatch')
 else:prompt='Explain one way to make a network retry safe.'
 outputs={}
 for arm in (plan['arms'] if mode=='full' else plan['arms'][:1]):
  name=arm['id'];
  if stopping() or (mode=='full' and time.time()+3000>=deadline):partial('insufficient time for fresh full arm');return 75
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  model=SMALL if mode=='smoke' else MODEL;cmd=[str(K/'llama-server'),'-m',model,'--host','127.0.0.1','--port',str(port),'-np','1','-c','2048' if mode=='qualification' else '131072','-t','96','-ub','512','-ngl','0','--flash-attn','on','-ctk','f16','-ctv','f16','--spec-type','draft-mtp','--spec-draft-n-max','4']
  if mode in ('full','qualification'):cmd=['numactl','--interleave=all',*cmd,'--no-mmap','--spec-draft-model',DRAFT,'--spec-draft-type-k','f16','--spec-draft-type-v','f16']
  env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(K),'OMP_NUM_THREADS':'1','HIP_VISIBLE_DEVICES':'-1','ROCR_VISIBLE_DEVICES':'-1'}
  if arm['GGML_FA_VKQ_F16']:env['GGML_FA_VKQ_F16']=arm['GGML_FA_VKQ_F16']
  log=(out/(name+'.server.log')).open('xb');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);birth=pathlib.Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19]
  atom(out/(name+'.server.json'),{'arm':name,'mode':mode,'argv':cmd,'pid':p.pid,'birth':birth,'grant_sha256':hashlib.sha256(grant).hexdigest() if grant else None,'grant_text':grant.decode() if grant else None,'env_knob':arm['GGML_FA_VKQ_F16'],'source_sha256':sha(D/'SOURCE-SHA256SUMS'),'plan_sha256':sha(D/'PLAN.json'),'context_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'binary_sha256':sha(K/'llama-server'),'runtime_catalog_sha256':sha(D/'RUNTIME-INPUTS.sha256'),'full_model_catalog_sha256':sha(D/'FULL-MODELS.sha256') if mode=='full' else None,'draft_head_sha256':'5ff54097406a905cf3a724c709124ceb0e3e10235ee862298969e91c96fa96e6' if mode=='full' else None,'cpu_affinity':sorted(os.sched_getaffinity(0)),'started_epoch':time.time()})
  try:
   url=f'http://127.0.0.1:{port}';ready=False;limit=time.monotonic()+1800
   while time.monotonic()<limit and p.poll() is None and not stopping():
    try:
     with urllib.request.urlopen(url+'/health',timeout=1) as r:ready=r.status==200
    except Exception:pass
    if ready:break
    time.sleep(.2)
   if stopping():partial('interrupted startup');return 75
   if not ready:atom(out/(name+'.failure.json'),{'reason':'server_not_ready','rc':p.poll()});continue
   payload={'prompt':prompt,**plan['request']};payload['n_predict']=16 if mode=='qualification' else payload['n_predict'];atom(out/((name+'.exposure.json') if mode=='full' else 'qualification.control.json'),{'arm':name,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'plan_sha256':sha(D/'PLAN.json'),'grant_sha256':hashlib.sha256(grant).hexdigest() if grant else None,'started_epoch':time.time()});state={}
   def request():
    try:
     req=urllib.request.Request(url+'/completion',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
     with urllib.request.urlopen(req,timeout=2800 if mode=='full' else 300) as r:state['http_status']=r.status;state['raw']=r.read().decode()
    except Exception as e:state['error']=repr(e)
   t=threading.Thread(target=request,daemon=True);t.start()
   while t.is_alive() and p.poll() is None and not stopping():t.join(.1)
   if stopping():partial('interrupted exposed request');return 75
   t.join(1)
   if t.is_alive() or 'error' in state:atom(out/(name+'.failure.json'),{'reason':'request_failed','error':state.get('error')});continue
   try:body=json.loads(state['raw'])
   except Exception as e:atom(out/(name+'.failure.json'),{'reason':'bad_native_json','error':repr(e)});continue
   timings=body.get('timings') or {};draft=timings.get('draft_n');accepted=timings.get('draft_n_accepted');tokens=body.get('tokens');result={'arm':name,'http_status':state['http_status'],'native_response':body,'response_sha256':hashlib.sha256(state['raw'].encode()).hexdigest(),'draft_n':draft,'draft_n_accepted':accepted,'acceptance':accepted/draft if isinstance(draft,int) and isinstance(accepted,int) and draft>0 and 0<=accepted<=draft else None,'tokens':tokens if isinstance(tokens,list) else None,'grant_sha256':hashlib.sha256(grant).hexdigest() if grant else None,'finished_epoch':time.time()};atom(out/(name+'.response.json'),result);outputs[name]=result
  finally:
   if p.poll() is None:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   log.close();atom(out/(name+'.drain.json'),{'pid':p.pid,'birth':birth,'returncode':p.returncode,'drained':p.poll() is not None,'server_log_sha256':sha(out/(name+'.server.log'))})
 if mode=='qualification':
  a=outputs.get('hybrid')
  if not a or a.get('http_status')!=200 or not isinstance(a.get('draft_n'),int) or a['draft_n']<=0:raise RuntimeError('qualification control failed or MTP count missing')
  atom(out/'QUALIFICATION.json', {'kind':'qualification_control','http_status':a['http_status'],'target_exposed':False,'draft_n':a['draft_n']});emit({'kind':'qualification_control','http_status':a['http_status'],'target_exposed':False,'draft_n':a['draft_n']})
  return 0
 a=outputs.get('hybrid');b=outputs.get('legacy');div=None
 if a and b and a['acceptance'] is not None and b['acceptance'] is not None and a['tokens'] is not None and b['tokens'] is not None:
  aa=a['tokens'];bb=b['tokens'];div=next((i for i,(x,y) in enumerate(zip(aa,bb)) if x!=y),None)
  if div is None and len(aa)!=len(bb):div=min(len(aa),len(bb))
 state='complete_raw' if len(outputs)==2 else 'incomplete_raw';atom(out/'TERMINAL.json',{'partial':False,'state':state,'first_divergence_index':div,'divergence_known':bool(a and b and a['acceptance'] is not None and b['acceptance'] is not None and a['tokens'] is not None and b['tokens'] is not None),'hybrid_acceptance':a['acceptance'] if a else None,'legacy_acceptance':b['acceptance'] if b else None,'verdict':None,'control_no_mtp':False});emit({'kind':'target_terminal','state':state,'terminal_path':str(out/'TERMINAL.json')});return 0
if __name__=='__main__':sys.exit(main())
