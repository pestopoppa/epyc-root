#!/usr/bin/env python3
import hashlib,json,os,pathlib,signal,socket,subprocess,sys,tempfile,threading,time,urllib.request,re
D=pathlib.Path(__file__).resolve().parent; K=pathlib.Path('/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin');MODEL='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf';DRAFT='/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf';SMALL='/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf'
def sha(b):return hashlib.sha256(b).hexdigest()
def atom(p,o):
 fd,n=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(o,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(n,p)
 finally:os.unlink(n)
def main():
 mode=os.environ['DF2_MODE'];assert mode in ('full','smoke');out=D/os.getenv('DF2_OUT','run');out.mkdir(exist_ok=True);plan=json.loads((D/'PLAN.json').read_text());deadline=int(os.environ['FILLER_DEADLINE'])-30;fid=os.getenv('FILLER_ID');gp=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(fid+'.grant') if fid else None;grant=gp.read_bytes() if gp and gp.is_file() else None
 if mode=='full' and not grant:raise RuntimeError('genuine grant missing')
 if mode=='full' and list(out.glob('*.exposure.json')):atom(out/'TERMINAL.json',{'state':'incomplete_prior_exposure_no_redraw','verdict':None});return 0
 stopped=False
 def handle(*_):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGTERM,handle);signal.signal(signal.SIGINT,handle)
 def stopping():return stopped or (D/'STOP').exists() or time.time()>=deadline or (mode=='full' and (not gp.is_file() or gp.read_bytes()!=grant))
 def partial(reason):(out/'PARTIAL.json').write_text(json.dumps({'partial':True,'reason':reason})+'\n')
 p=None;log=None
 def start(name,slots):
  nonlocal p,log
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  cmd=[str(K/'llama-server'),'-m',SMALL if mode=='smoke' else MODEL,'--host','127.0.0.1','--port',str(port),'-np',str(slots),'-c',str(slots*2048),'-t',str(len(os.sched_getaffinity(0))),'-ngl','0','--cache-ram','0','--spec-type','none' if mode=='smoke' else 'draft-dflash','--spec-draft-n-max','7','--log-verbosity','5']
  if mode=='full':cmd+=['--spec-draft-model',DRAFT,'--spec-draft-ngl','0']
  env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(K),'OMP_NUM_THREADS':'1','HIP_VISIBLE_DEVICES':'-1','ROCR_VISIBLE_DEVICES':'-1'};log=(out/(name+'.server.log')).open('xb');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);birth=pathlib.Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19];atom(out/(name+'.server.json'),{'argv':cmd,'pid':p.pid,'birth':birth,'mode':mode,'grant_sha256':sha(grant) if grant else None,'grant':grant.decode() if grant else None,'source_sha256':sha((D/'SOURCE-SHA256SUMS').read_bytes()),'plan_sha256':sha((D/'PLAN.json').read_bytes()),'cpu_affinity':sorted(os.sched_getaffinity(0))})
  url='http://127.0.0.1:'+str(port);limit=time.monotonic()+(120 if mode=='smoke' else 1200)
  while time.monotonic()<limit and p.poll() is None and not stopping():
   try:
    with urllib.request.urlopen(url+'/health',timeout=1) as r:
     if r.status==200:return url
   except Exception:pass
   time.sleep(.2)
  if stopping():raise InterruptedError('startup interrupted')
  raise RuntimeError('server not ready')
 def drain(name):
  nonlocal p,log
  if p is None:return
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  log.close();atom(out/(name+'.drain.json'),{'pid':p.pid,'rc':p.returncode,'drained':p.poll() is not None,'log_sha256':sha((out/(name+'.server.log')).read_bytes())});p=None
 def request(url,name,case,cap,barrier=None):
  payload={'prompt':case['prompt'],'n_predict':plan['n_predict'],'temperature':0,'top_k':1,'seed':42,'n_probs':2,'post_sampling_probs':False,'cache_prompt':False,'return_tokens':True,'speculative.n_max':cap};atom(out/(name+'.exposure.json'),{'case':case['id'],'payload':payload,'grant_sha256':sha(grant) if grant else None,'started':time.time()})
  if barrier:barrier.wait(timeout=10)
  started=time.time()
  try:
   req=urllib.request.Request(url+'/completion',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
   with urllib.request.urlopen(req,timeout=1500 if mode=='full' else 180) as r:raw=r.read().decode();status=r.status
   body=json.loads(raw);atom(out/(name+'.response.json'),{'http_status':status,'started':started,'finished':time.time(),'native_response':body,'response_sha256':sha(raw.encode())})
  except Exception as e:atom(out/(name+'.failure.json'),{'reason':repr(e),'started':started,'finished':time.time()})
 cases=plan['prompts'];name='mixed';threads=[]
 try:
  if stopping() or (mode=='full' and time.time()+3000>=deadline):raise InterruptedError('insufficient time before mixed exposure')
  url=start(name,4);bar=threading.Barrier(4)
  threads=[threading.Thread(target=request,args=(url,'mixed-'+c['id'],c,c['mixed_draft_cap'],bar),daemon=True) for c in cases]
  for t in threads:t.start()
  while any(t.is_alive() for t in threads) and p.poll() is None and not stopping():time.sleep(.1)
  if stopping():raise InterruptedError('interrupted mixed exposure')
  for t in threads:t.join(1)
  if any(t.is_alive() for t in threads):raise RuntimeError('mixed request did not drain')
  drain(name)
  for c in cases:
   if stopping() or (mode=='full' and time.time()+600>=deadline):raise InterruptedError('insufficient time before baseline exposure')
   name='baseline-'+c['id'];url=start(name,1);t=threading.Thread(target=request,args=(url,name,c,0),daemon=True);threads.append(t);t.start()
   while t.is_alive() and p.poll() is None and not stopping():t.join(.1)
   if stopping():raise InterruptedError('interrupted baseline exposure')
   t.join(1)
   if t.is_alive():raise RuntimeError('baseline request did not drain')
   drain(name)
 except InterruptedError as e:partial(str(e));return 75
 except Exception as e:atom(out/'FAILURE.json',{'reason':repr(e),'verdict':None});return 1
 finally:
  if p is not None:drain(name)
  for t in threads:t.join(1)
 pairs=[]
 for c in cases:
  a=out/('mixed-'+c['id']+'.response.json');b=out/('baseline-'+c['id']+'.response.json')
  if not a.exists() or not b.exists():pairs.append({'case':c['id'],'classification':'UNKNOWN','reason':'missing response'});continue
  x=json.loads(a.read_text())['native_response'];y=json.loads(b.read_text())['native_response'];tx=x.get('tokens');ty=y.get('tokens');div=None
  if isinstance(tx,list) and isinstance(ty,list):
   div=next((i for i,(u,v) in enumerate(zip(tx,ty)) if u!=v),None)
   if div is None and len(tx)!=len(ty):div=min(len(tx),len(ty))
  probs=y.get('completion_probabilities');margin=None
  if div is not None and isinstance(probs,list) and div<len(probs):
   tops=probs[div].get('top_logprobs',[])
   if len(tops)>=2 and all(isinstance(v.get('logprob'),(int,float)) for v in tops[:2]):margin=tops[0]['logprob']-tops[1]['logprob']
  pairs.append({'case':c['id'],'draft_cap':c['mixed_draft_cap'],'native_draft_n':(x.get('timings') or {}).get('draft_n'),'effective_draft_cap':(x.get('generation_settings') or {}).get('speculative.n_max'),'first_divergence':div,'tokens_comparable':isinstance(tx,list) and isinstance(ty,list),'baseline_top2_log_margin':margin,'inherited_cpu_band_nats':0.001,'near_tie_by_inherited_band':(margin<=0.001) if margin is not None and margin>=0 else None,'classification':'UNKNOWN','reason':'trace and degeneration review required'})
 slot_caps={}
 for c in cases:
  rp=out/('mixed-'+c['id']+'.response.json')
  if rp.exists():
   z=json.loads(rp.read_text())['native_response'];sl=z.get('id_slot');eff=(z.get('generation_settings') or {}).get('speculative.n_max')
   if isinstance(sl,int) and eff==c['mixed_draft_cap']:slot_caps[sl]=eff
 events=[]
 for line in (out/'mixed.server.log').read_text(errors='replace').splitlines():
  m=re.search(r'slot\s+\S+: id\s*(\d+) \| task\s*\d+ \| (.*)',line)
  if not m:continue
  slot=int(m.group(1));body=m.group(2)
  if slot_caps.get(slot)==7 and re.search(r'accepted\s+\d+/\d+ draft tokens',body):events.append(('spec_accept',slot))
  elif slot_caps.get(slot)==0 and 'n_decoded =' in body:events.append(('no_spec_decode',slot))
 interleaved=any(events[i][0]=='spec_accept' and events[i+1][0]=='no_spec_decode' and events[i+2][0]=='spec_accept' for i in range(len(events)-2))
 atom(out/'TERMINAL.json',{'state':'complete_raw','pairs':pairs,'slot_caps':slot_caps,'trace_event_count':len(events),'slot_interleaving':'observed_spec_accept_nonspec_decode_spec_accept' if interleaved else 'UNKNOWN','control_no_dflash':mode=='smoke','verdict':None});return 0
if __name__=='__main__':sys.exit(main())
