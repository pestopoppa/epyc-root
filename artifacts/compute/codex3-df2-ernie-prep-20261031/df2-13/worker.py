#!/usr/bin/env python3
import hashlib,json,os,pathlib,signal,socket,subprocess,sys,tempfile,threading,time,urllib.request
D=pathlib.Path(__file__).resolve().parent
K=pathlib.Path('/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin')
MODEL='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'; DRAFT='/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf'; SMALL='/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf'
def sha(b):return hashlib.sha256(b).hexdigest()
def atom(p,o):
 fd,n=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(o,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(n,p)
 finally:os.unlink(n)
def main():
 mode=os.environ['DF2_MODE']; assert mode in ('smoke','full');out=D/os.getenv('DF2_OUT','run');out.mkdir(exist_ok=True);plan=json.loads((D/'PLAN.json').read_text());deadline=int(os.environ['FILLER_DEADLINE'])-30;fid=os.getenv('FILLER_ID');gp=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(fid+'.grant') if fid else None;grant=gp.read_bytes() if gp and gp.is_file() else None
 if mode=='full' and not grant:raise RuntimeError('genuine grant missing')
 if mode=='full' and list(out.glob('*.exposure.json')):
  atom(out/'TERMINAL.json',{'state':'incomplete_prior_exposure_no_redraw','verdict':None});return 0
 stopped=False
 def handle(*_):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGTERM,handle);signal.signal(signal.SIGINT,handle)
 def stopping():return stopped or (D/'STOP').exists() or time.time()>=deadline or (mode=='full' and (not gp.is_file() or gp.read_bytes()!=grant))
 def partial(why):
  p=out/'PARTIAL.json';p.write_text(json.dumps({'partial':True,'reason':why})+'\n')
 outputs={};p=None;log=None
 def start(name):
  nonlocal p,log
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  cmd=[str(K/'llama-server'),'-m',SMALL if mode=='smoke' else MODEL,'--host','127.0.0.1','--port',str(port),'-np','1','-c','4096','-t',str(len(os.sched_getaffinity(0))),'-ngl','0','--ctx-checkpoints','32','--cache-ram','512','--spec-type','none' if mode=='smoke' else 'draft-dflash','--spec-draft-n-max','7','--log-verbosity','4']
  if mode=='full':cmd+=['--spec-draft-model',DRAFT,'--spec-draft-ngl','0']
  env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(K),'OMP_NUM_THREADS':'1','HIP_VISIBLE_DEVICES':'-1','ROCR_VISIBLE_DEVICES':'-1'}
  log=(out/(name+'.server.log')).open('xb');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);birth=pathlib.Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19]
  atom(out/(name+'.server.json'),{'argv':cmd,'pid':p.pid,'birth':birth,'mode':mode,'grant_sha256':sha(grant) if grant else None,'grant':grant.decode() if grant else None,'source_sha256':sha((D/'SOURCE-SHA256SUMS').read_bytes()),'plan_sha256':sha((D/'PLAN.json').read_bytes()),'cpu_affinity':sorted(os.sched_getaffinity(0))})
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
 def request(url,name,prompt,n):
  if stopping() or (mode=='full' and time.time()+600>=deadline):raise InterruptedError('insufficient time before exposure')
  payload={'prompt':prompt,'n_predict':n,'temperature':0,'top_k':1,'seed':42,'cache_prompt':True,'return_tokens':True}
  atom(out/(name+'.exposure.json'),{'prompt_sha256':sha(prompt.encode()),'grant_sha256':sha(grant) if grant else None,'started':time.time(),'payload':payload});state={}
  def run():
   try:
    req=urllib.request.Request(url+'/completion',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=1500 if mode=='full' else 120) as r:state['raw']=r.read().decode();state['status']=r.status
   except Exception as e:state['error']=repr(e)
  t=threading.Thread(target=run,daemon=True);t.start()
  while t.is_alive() and p.poll() is None and not stopping():t.join(.05)
  if stopping():raise InterruptedError('interrupted exposed request')
  t.join(1)
  if t.is_alive() or 'error' in state:raise RuntimeError('request failed '+repr(state.get('error')))
  body=json.loads(state['raw']); atom(out/(name+'.response.json'),{'http_status':state['status'],'native_response':body,'response_sha256':sha(state['raw'].encode()),'finished':time.time()});return body
 try:
  url=start('warm');a=request(url,'A',plan['A_prompt'],plan['A_n_predict']);outputs['A']=a
  if not isinstance(a.get('content'),str):raise RuntimeError('missing A content')
  prompt=plan['A_prompt']+a['content']+plan['B_suffix'];outputs['B_warm']=request(url,'B_warm',prompt,plan['B_n_predict']);drain('warm')
  url=start('cold');outputs['B_cold']=request(url,'B_cold',prompt,plan['B_n_predict']);drain('cold')
 except InterruptedError as e:partial(str(e));return 75
 except Exception as e:atom(out/'FAILURE.json',{'reason':repr(e),'verdict':None});return 1
 finally:
  if p is not None:drain('warm' if not (out/'warm.drain.json').exists() else 'cold')
 x=outputs['B_warm'];y=outputs['B_cold'];tx=x.get('tokens');ty=y.get('tokens');same=tx==ty if isinstance(tx,list) and isinstance(ty,list) else None
 logs=(out/'warm.server.log').read_text(errors='replace');trace='restored context checkpoint' in logs.lower();drafts=[(z.get('timings') or {}).get('draft_n') for z in (x,y)]
 atom(out/'TERMINAL.json',{'state':'complete_raw','warm_cold_token_equal':same,'warm_cache_n':(x.get('timings') or {}).get('cache_n'),'cold_cache_n':(y.get('timings') or {}).get('cache_n'),'draft_n':drafts,'checkpoint_restore_observed':trace,'checkpoint_route': 'observed' if trace else 'UNKNOWN','dflash_qualified':mode=='full' and all(isinstance(v,int) and v>0 for v in drafts),'control_no_dflash':mode=='smoke','verdict':None});return 0
if __name__=='__main__':sys.exit(main())
