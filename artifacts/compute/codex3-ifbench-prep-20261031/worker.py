#!/usr/bin/env python3
"""IFBench single-arm native capture and official offline score, no paired verdict."""
import hashlib,json,os,pathlib,signal,socket,subprocess,sys,tempfile,threading,time,urllib.request
import ifbench_fixture
D=pathlib.Path(__file__).resolve().parent;K=pathlib.Path('/mnt/raid0/llm/kernels/production/cpu');MODEL='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf';SMALL='/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf'
def sha(b):return hashlib.sha256(b).hexdigest()
def atom(p,x):
 fd,n=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(x,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(n,p)
 finally:os.unlink(n)
def main():
 mode=os.environ['IFBENCH_MODE'];assert mode in ('full','smoke');out=D/os.getenv('IFBENCH_OUT','run');out.mkdir(exist_ok=True);fid=os.getenv('FILLER_ID');gp=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(fid+'.grant') if fid else None;grant=gp.read_bytes() if gp and gp.is_file() else None
 if mode=='full' and not grant:raise RuntimeError('grant missing')
 deadline=int(os.environ['FILLER_DEADLINE'])-20;stopped=False
 def handler(*_):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGTERM,handler);signal.signal(signal.SIGINT,handler)
 def stop():return stopped or (D/'STOP').exists() or time.time()>=deadline or (mode=='full' and (not gp.is_file() or gp.read_bytes()!=grant))
 def partial(reason):
  tmp=out/'.partial.tmp';tmp.write_text(json.dumps({'partial':True,'reason':reason})+'\n');os.replace(tmp,out/'PARTIAL.json')
 if mode=='full':
  rows=ifbench_fixture.load_corpus(D/'source/data/IFBench_test.jsonl');cases=[{'id':str(x['key']),'prompt':x['prompt']} for x in rows];assert len(cases)==300
 else:cases=[{'id':'engineering','prompt':'Reply with the word moon.'}]
 plan=sha((D/'PLAN.json').read_bytes());source=sha((D/'SOURCE-SHA256SUMS').read_bytes());cohort=sha((D/'COHORT.json').read_bytes());counts={'ok':0,'unknown':0,'length_finish':0}
 with socket.socket() as z:z.bind(('127.0.0.1',0));port=z.getsockname()[1]
 cmd=[str(K/'llama-server'),'-m',MODEL if mode=='full' else SMALL,'--host','127.0.0.1','--port',str(port),'-np','1','-c','8192' if mode=='full' else '1024','-t',str(min(8,len(os.sched_getaffinity(0)))),'-ngl','0','--no-warmup','--reasoning','off'];env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(K),'OMP_NUM_THREADS':'1','HIP_VISIBLE_DEVICES':'-1','ROCR_VISIBLE_DEVICES':'-1'}
 log=(out/('server-'+str(time.time_ns())+'.log')).open('xb');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);birth=pathlib.Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19];atom(out/('server-'+str(p.pid)+'.json'),{'pid':p.pid,'birth':birth,'argv':cmd,'mode':mode,'grant_sha256':sha(grant) if grant else None,'grant':grant.decode() if grant else None,'source_sha256':source,'plan_sha256':plan,'cohort_sha256':cohort,'cpu_affinity':sorted(os.sched_getaffinity(0))})
 try:
  url='http://127.0.0.1:'+str(port);ready=False;limit=time.monotonic()+(120 if mode=='smoke' else 1200)
  while time.monotonic()<limit and p.poll() is None and not stop():
   try:
    with urllib.request.urlopen(url+'/health',timeout=1) as r:ready=r.status==200
   except Exception:pass
   if ready:break
   time.sleep(.1)
  if stop():partial('startup interrupted');return 75
  if not ready:atom(out/'FAILURE.json',{'state':'server_not_ready','rc':p.poll()});return 1
  for i,case in enumerate(cases):
   name=f'{i:03d}';ep=out/(name+'.exposure.json');rp=out/(name+'.result.json');rawp=out/(name+'.response.json');binding={'source_sha256':source,'plan_sha256':plan,'cohort_sha256':cohort,'id':case['id'],'prompt_sha256':sha(case['prompt'].encode())}
   if rp.exists():
    x=json.loads(rp.read_text());e=json.loads(ep.read_text());assert all(e.get(k)==v for k,v in binding.items())
    if x.get('status')=='ok':assert rawp.is_file() and sha(rawp.read_bytes())==x['response_file_sha256'];counts['ok']+=1;counts['length_finish']+=int(x.get('finish_reason')=='length')
    else:counts['unknown']+=1
    continue
   if ep.exists():atom(rp,{'status':'UNKNOWN','reason':'prior exposed incomplete; no redraw','exposure_sha256':sha(ep.read_bytes())});counts['unknown']+=1;continue
   if stop() or (mode=='full' and time.time()+1230>=deadline):partial('before next request or insufficient full timeout and cleanup reserve');return 75
   payload={'model':'ifbench-local','messages':[{'role':'user','content':case['prompt']}],'temperature':0,'max_tokens':4096 if mode=='full' else 24,'seed':20261031,'stream':False,'n':1}
   atom(ep,{**binding,'payload_sha256':sha(json.dumps(payload,sort_keys=True).encode()),'grant_sha256':sha(grant) if grant else None,'grant':grant.decode() if grant else None,'started_epoch':time.time()});state={}
   def request():
    try:
     req=urllib.request.Request(url+'/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
     with urllib.request.urlopen(req,timeout=1200 if mode=='full' else 120) as r:state['status']=r.status;state['raw']=r.read()
    except Exception as e:state['error']=repr(e)
   t=threading.Thread(target=request,daemon=True);t.start()
   while t.is_alive() and p.poll() is None and not stop():t.join(.05)
   if stop():partial('interrupted exposed request');return 75
   t.join(1)
   if t.is_alive() or 'error' in state:atom(rp,{'status':'UNKNOWN','reason':'request timeout/error or server exit','error':state.get('error'),'exposure_sha256':sha(ep.read_bytes())});counts['unknown']+=1;partial('request unresolved; stop server before continuation');return 75
   try:
    data=json.loads(state['raw']);choice=data['choices'][0];text=choice['message'].get('content');atom(rawp,{'http_status':state['status'],'native_response':data,'raw_sha256':sha(state['raw'])})
    if not isinstance(text,str) or not text.strip():raise ValueError('missing content, preserve response')
    atom(rp,{'status':'ok','response':text,'finish_reason':choice.get('finish_reason'),'response_file_sha256':sha(rawp.read_bytes()),'exposure_sha256':sha(ep.read_bytes()),'finished_epoch':time.time()});counts['ok']+=1;counts['length_finish']+=int(choice.get('finish_reason')=='length')
   except Exception as e:atom(rp,{'status':'UNKNOWN','reason':repr(e),'response_file_sha256':sha(rawp.read_bytes()) if rawp.exists() else None,'exposure_sha256':sha(ep.read_bytes())});counts['unknown']+=1
 finally:
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  log.close();atom(out/('server-'+str(p.pid)+'.drain.json'),{'pid':p.pid,'birth':birth,'rc':p.returncode,'drained':p.poll() is not None,'server_log_sha256':sha(pathlib.Path(log.name).read_bytes())})
 if mode=='smoke':
  if counts['ok']!=1:return 1
  scoredir=out/'score-control';scoredir.mkdir();scorelog=out/'score-control.log';scmd=[str(D/'venv/bin/python'),str(D/'offline_exec.py'),str(D/'venv/bin/python'),str(D/'source/run_eval.py'),'--input_data='+str(D/'control/input.jsonl'),'--input_response_data='+str(D/'control/responses.jsonl'),'--output_dir='+str(scoredir)];senv={'PATH':'/usr/bin:/bin','NLTK_DATA':str(D/'nltk_data'),'OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
  with scorelog.open('xb') as sl:sp=subprocess.run(scmd,stdout=sl,stderr=subprocess.STDOUT,env=senv,timeout=100)
  assert sp.returncode==0 and 'KERNEL_NETWORK_DENY_CONFIRMED' in scorelog.read_text();files=sorted(scoredir.glob('*-eval_results_*.jsonl'));assert len(files)==2
  for f in files:
   vals=[json.loads(z)['follow_all_instructions'] for z in f.read_text().splitlines()];assert vals==[True,False]
  atom(out/'TERMINAL.json',{'state':'complete_engineering_only','expected':1,'counts':counts,'official_scorer_fixture':'two synthetic positive/negative examples passed, kernel network denied','partial':False,'full_task':'UNRUN'});return 0
 if counts['unknown'] or counts['ok']!=300:atom(out/'TERMINAL.json',{'state':'capture_complete_score_unknown','expected':300,'counts':counts,'score':'UNAVAILABLE','paired_delta':'UNCOMPUTED','partial':False});return 0
 if stop() or time.time()+400>=deadline:partial('before official scorer');return 75
 responses=[{'prompt':c['prompt'],'response':json.loads((out/(f'{i:03d}.result.json')).read_text())['response']} for i,c in enumerate(cases)];ifbench_fixture.exact_response_join(rows,responses);rp=out/'official-responses.jsonl';body=''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in responses);assert not rp.exists() or rp.read_text()==body
 if not rp.exists():rp.write_text(body)
 attempt=str(time.time_ns());scoredir=out/('official-score-'+attempt);scoredir.mkdir()
 cmd=[str(D/'venv/bin/python'),str(D/'offline_exec.py'),str(D/'venv/bin/python'),str(D/'source/run_eval.py'),'--input_data='+str(D/'source/data/IFBench_test.jsonl'),'--input_response_data='+str(rp),'--output_dir='+str(scoredir)];env={'PATH':'/usr/bin:/bin','NLTK_DATA':str(D/'nltk_data'),'OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'};scorelog=out/('official-score-'+attempt+'.log');sl=scorelog.open('xb');sp=subprocess.Popen(cmd,stdout=sl,stderr=subprocess.STDOUT,env=env,start_new_session=True)
 try:
  limit=time.monotonic()+300
  while sp.poll() is None and not stop() and time.monotonic()<limit:time.sleep(.1)
  if stop() or sp.poll() is None:
   if sp.poll() is None:os.killpg(sp.pid,signal.SIGTERM);sp.wait(10)
   partial('official score interrupted or timed out');return 75
  rc=sp.wait()
 finally:sl.close()
 if rc!=0 or 'KERNEL_NETWORK_DENY_CONFIRMED' not in scorelog.read_text():atom(out/'TERMINAL.json',{'state':'capture_complete_score_unknown','expected':300,'counts':counts,'scorer_rc':rc,'paired_delta':'UNCOMPUTED','partial':False});return 0
 files=sorted(scoredir.glob('*-eval_results_*.jsonl'));assert len(files)==2
 for f in files:assert len(f.read_text().splitlines())==300
 atom(out/'TERMINAL.json',{'state':'single_arm_official_score','expected':300,'counts':counts,'score_files':{f.name:sha(f.read_bytes()) for f in files},'responses_sha256':sha(rp.read_bytes()),'paired_delta':'UNCOMPUTED','adoption':'UNCLAIMED','partial':False});return 0
if __name__=='__main__':sys.exit(main())
