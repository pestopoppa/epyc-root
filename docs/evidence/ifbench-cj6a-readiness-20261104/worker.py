#!/usr/bin/env python3
"""IFBench single-arm native capture and official offline score, no paired verdict."""
import hashlib,json,os,pathlib,signal,socket,subprocess,sys,tempfile,threading,time,urllib.request
import ifbench_fixture
D=pathlib.Path(__file__).resolve().parent;K=pathlib.Path('/mnt/raid0/llm/kernels/production/cpu');MODEL='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf';LINKAGE='/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh';KERNEL_STORE_SHA='4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c'
def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):
 h=hashlib.sha256()
 with pathlib.Path(p).open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
def captured_signal(p,sig,birth):
 try:
  stat=pathlib.Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19]
  if stat!=birth:return False
  os.kill(p.pid,sig);return True
 except (ProcessLookupError,FileNotFoundError):return False
def atom(p,x):
 fd,n=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(x,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(n,p)
 finally:os.unlink(n)
def main():
 mode=os.environ['IFBENCH_MODE'];assert mode in ('full','smoke');out=pathlib.Path(os.environ['IFBENCH_OUT']) if mode=='smoke' else D/'run';out.mkdir(parents=True,exist_ok=True);fid=os.getenv('FILLER_ID');gp=pathlib.Path(os.getenv('FILLER_GRANTS_DIR','/mnt/raid0/llm/tmp/compute-flags/grants'))/(fid+'.grant') if fid else None;grant=gp.read_bytes() if gp and gp.is_file() else None
 if mode=='full' and not grant:raise RuntimeError('grant missing')
 assert file_sha(MODEL)==(D/'MODEL.sha256').read_text().split()[0]
 if mode=='smoke':assert out.is_absolute() and os.getenv('FILLER_DRYRUN_RESULT_PATH')
 server_file=K/'llama-server';assert file_sha(server_file)==KERNEL_STORE_SHA,'kernel store server digest changed'
 link_env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(K),'OMP_NUM_THREADS':'1','HIP_VISIBLE_DEVICES':'-1','ROCR_VISIBLE_DEVICES':'-1'}
 link=subprocess.run([LINKAGE,str(server_file),str(K)],env=link_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 if link.returncode:raise RuntimeError('production kernel ggml linkage verification failed: '+link.stdout[-2000:])
 deadline=int(os.environ['FILLER_DEADLINE'])-20;stopped=False;stop_path=pathlib.Path(os.getenv('FILLER_STOPFILE',str(D/'STOP')))
 def handler(*_):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGTERM,handler);signal.signal(signal.SIGINT,handler)
 def stop():return stopped or stop_path.exists() or time.time()>=deadline or (mode=='full' and (not gp.is_file() or gp.read_bytes()!=grant))
 def partial(reason):
  tmp=out/'.partial.tmp';tmp.write_text(json.dumps({'partial':True,'reason':reason})+'\n');os.replace(tmp,out/'PARTIAL.json')
 if mode=='full':
  rows=ifbench_fixture.load_corpus(D/'source/data/IFBench_test.jsonl');cases=[{'id':str(x['key']),'prompt':x['prompt']} for x in rows];assert len(cases)==300
 else:cases=[{'id':'synthetic-engineering-only','prompt':'For this engineering smoke check, reply with the single word moon.'}]
 plan=sha((D/'PLAN.json').read_bytes());source=sha((D/'SOURCE-SHA256SUMS').read_bytes()) if mode=='full' else None;cohort=sha((D/'COHORT.json').read_bytes()) if mode=='full' else None;counts={'ok':0,'unknown':0,'length_finish':0};model_sha=(D/'MODEL.sha256').read_text().split()[0];kernel_inputs_sha=sha((D/'KERNEL-INPUTS.sha256').read_bytes());server_sha=file_sha(server_file);kernel_build='production-consolidated-v10@ffc1bac82eeca6f9099e1ccd9ba49703c460a115';decoding={'temperature':0,'seed':20261031,'max_tokens':4096 if mode=='full' else 24,'n':1,'reasoning':'off','ctx':8192}
 with socket.socket() as z:z.bind(('127.0.0.1',0));port=z.getsockname()[1]
 cmd=[str(server_file),'-m',MODEL,'--host','127.0.0.1','--port',str(port),'-np','1','-c','8192','-t',str(min(8,len(os.sched_getaffinity(0)))),'-ngl','0','--no-warmup','--reasoning','off'];env=link_env
 log=(out/('server-'+str(time.time_ns())+'.log')).open('xb');p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env);birth=pathlib.Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19];atom(out/('server-'+str(p.pid)+'.json'),{'pid':p.pid,'birth':birth,'argv':cmd,'mode':mode,'grant_sha256':sha(grant) if grant else None,'grant':grant.decode() if grant else None,'source_sha256':source,'plan_sha256':plan,'cohort_sha256':cohort,'model_sha256':model_sha,'model_path':MODEL,'server_binary_sha256':server_sha,'kernel_store_server_sha256':KERNEL_STORE_SHA,'ggml_linkage_verified':True,'kernel_build':kernel_build,'kernel_inputs_sha256':kernel_inputs_sha,'decoding':decoding,'cpu_affinity':sorted(os.sched_getaffinity(0))})
 try:
  url='http://127.0.0.1:'+str(port);ready=False;limit=time.monotonic()+(600 if mode=='smoke' else 1200)
  while time.monotonic()<limit and p.poll() is None and not stop():
   try:
    with urllib.request.urlopen(url+'/health',timeout=1) as r:ready=r.status==200
   except Exception:pass
   if ready:break
   time.sleep(.1)
  if stop():partial('startup interrupted');return 75
  if not ready:atom(out/'FAILURE.json',{'state':'server_not_ready','rc':p.poll()});return 1
  for i,case in enumerate(cases):
   name=f'{i:03d}';ep=out/(name+'.exposure.json');rp=out/(name+'.result.json');rawp=out/(name+'.response.json');binding={'source_sha256':source,'plan_sha256':plan,'cohort_sha256':cohort,'model_sha256':model_sha,'server_binary_sha256':server_sha,'kernel_build':kernel_build,'kernel_inputs_sha256':kernel_inputs_sha,'decoding':decoding,'id':case['id'],'prompt_sha256':sha(case['prompt'].encode())}
   if rp.exists():
    x=json.loads(rp.read_text());e=json.loads(ep.read_text());assert all(e.get(k)==v for k,v in binding.items())
    if x.get('status')=='ok':assert rawp.is_file() and sha(rawp.read_bytes())==x['response_file_sha256'];counts['ok']+=1;counts['length_finish']+=int(x.get('finish_reason')=='length')
    else:counts['unknown']+=1;partial('prior exposed attempt is UNKNOWN; stop without redraw');return 75
    continue
   if ep.exists():atom(rp,{'status':'UNKNOWN','reason':'prior exposed incomplete; no redraw','exposure_sha256':sha(ep.read_bytes())});counts['unknown']+=1;partial('prior exposed attempt unresolved; stop without redraw');return 75
   if stop() or (mode=='full' and time.time()+1230>=deadline):partial('before next request or insufficient full timeout and cleanup reserve');return 75
   payload={'model':'ifbench-local','messages':[{'role':'user','content':case['prompt']}],'temperature':0,'max_tokens':4096 if mode=='full' else 24,'seed':20261031,'stream':False,'n':1}
   atom(ep,{**binding,'payload_sha256':sha(json.dumps(payload,sort_keys=True).encode()),'grant_sha256':sha(grant) if grant else None,'grant':grant.decode() if grant else None,'actual_grant_sha256':sha(grant) if grant else None,'actual_grant':grant.decode() if grant else None,'grant_id':fid,'grant_path':str(gp) if gp else None,'grant_owner':os.getenv('FILLER_OWNER'),'grant_estimated_wall_s':os.getenv('FILLER_EST_WALL_S'),'grant_cpus':os.getenv('FILLER_CPUS'),'grant_regions':os.getenv('WS58_REGIONS'),'started_epoch':time.time()});state={}
   def request():
    try:
     req=urllib.request.Request(url+'/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
     with urllib.request.urlopen(req,timeout=1200 if mode=='full' else 120) as r:state['status']=r.status;state['raw']=r.read()
    except Exception as e:state['error']=repr(e)
   t=threading.Thread(target=request,daemon=True);t.start()
   while t.is_alive() and p.poll() is None and not stop():t.join(.05)
   if stop():atom(rp,{'status':'UNKNOWN','reason':'interrupted exposed request; no redraw','exposure_sha256':sha(ep.read_bytes())});partial('interrupted exposed request');return 75
   t.join(1)
   if t.is_alive() or 'error' in state:atom(rp,{'status':'UNKNOWN','reason':'request timeout/error or server exit','error':state.get('error'),'exposure_sha256':sha(ep.read_bytes())});counts['unknown']+=1;partial('request unresolved; stop server before continuation');return 75
   try:
    data=json.loads(state['raw']);choice=data['choices'][0];text=choice['message'].get('content');atom(rawp,{'http_status':state['status'],'native_response':data,'raw_sha256':sha(state['raw'])})
    if not isinstance(text,str) or not text.strip():raise ValueError('missing content, preserve response')
    atom(rp,{'status':'ok','response':text,'finish_reason':choice.get('finish_reason'),'response_file_sha256':sha(rawp.read_bytes()),'exposure_sha256':sha(ep.read_bytes()),'finished_epoch':time.time()});counts['ok']+=1;counts['length_finish']+=int(choice.get('finish_reason')=='length')
   except Exception as e:atom(rp,{'status':'UNKNOWN','reason':repr(e),'response_file_sha256':sha(rawp.read_bytes()) if rawp.exists() else None,'exposure_sha256':sha(ep.read_bytes())});counts['unknown']+=1;partial('response invalid; stop after unresolved exposure');return 75
 finally:
  if p.poll() is None:
   if captured_signal(p,signal.SIGTERM,birth):
    try:p.wait(10)
    except subprocess.TimeoutExpired:
     if captured_signal(p,signal.SIGKILL,birth):p.wait()
  log.close();atom(out/('server-'+str(p.pid)+'.drain.json'),{'pid':p.pid,'birth':birth,'rc':p.returncode,'drained':p.poll() is not None,'server_log_sha256':sha(pathlib.Path(log.name).read_bytes())})
 if mode=='smoke':
  if counts['ok']!=1:return 1
  native_path=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
  actual=json.loads((out/'000.response.json').read_text())
  atom(native_path,{'status':'ok','prompt_key':'synthetic-engineering-only','model_sha256':model_sha,'response_status':actual['http_status']})
  scoredir=out/'score-control';scoredir.mkdir();scorelog=out/'score-control.log';scmd=[str(D/'venv/bin/python'),str(D/'offline_exec.py'),str(D/'venv/bin/python'),str(D/'source/run_eval.py'),'--input_data='+str(D/'control/input.jsonl'),'--input_response_data='+str(D/'control/responses.jsonl'),'--output_dir='+str(scoredir)];senv={'PATH':'/usr/bin:/bin','NLTK_DATA':str(D/'nltk_data'),'OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
  with scorelog.open('xb') as sl:sp=subprocess.run(scmd,stdout=sl,stderr=subprocess.STDOUT,env=senv,timeout=100)
  assert sp.returncode==0 and 'KERNEL_NETWORK_DENY_CONFIRMED' in scorelog.read_text();files=sorted(scoredir.glob('*-eval_results_*.jsonl'));assert len(files)==2
  for f in files:
   vals=[json.loads(z)['follow_all_instructions'] for z in f.read_text().splitlines()];assert vals==[True,False]
  atom(out/'TERMINAL.json',{'state':'complete_engineering_only','expected':1,'counts':counts,'native_result':True,'synthetic_noncohort_prompt_only':True,'model_sha256':model_sha,'kernel_store_server_sha256':KERNEL_STORE_SHA,'ggml_linkage_verified':True,'official_scorer_fixture':'two synthetic positive/negative examples passed, kernel network denied','partial':False,'full_task':'UNRUN'});return 0
 if counts['unknown'] or counts['ok']!=300:atom(out/'TERMINAL.json',{'state':'capture_complete_score_unknown','expected':300,'counts':counts,'score':'UNAVAILABLE','paired_delta':'UNCOMPUTED','partial':False});return 0
 if stop() or time.time()+400>=deadline:partial('before official scorer');return 75
 responses=[{'prompt':c['prompt'],'response':json.loads((out/(f'{i:03d}.result.json')).read_text())['response']} for i,c in enumerate(cases)];ifbench_fixture.exact_response_join(rows,responses);rp=out/'official-responses.jsonl';body=''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in responses);assert not rp.exists() or rp.read_text()==body
 if not rp.exists():rp.write_text(body)
 attempt=str(time.time_ns());scoredir=out/('official-score-'+attempt);scoredir.mkdir()
 cmd=[str(D/'venv/bin/python'),str(D/'offline_exec.py'),str(D/'venv/bin/python'),str(D/'source/run_eval.py'),'--input_data='+str(D/'source/data/IFBench_test.jsonl'),'--input_response_data='+str(rp),'--output_dir='+str(scoredir)];env={'PATH':'/usr/bin:/bin','NLTK_DATA':str(D/'nltk_data'),'OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'};scorelog=out/('official-score-'+attempt+'.log');sl=scorelog.open('xb');sp=subprocess.Popen(cmd,stdout=sl,stderr=subprocess.STDOUT,env=env);sbirth=pathlib.Path('/proc',str(sp.pid),'stat').read_text().rsplit(') ',1)[1].split()[19]
 try:
  limit=time.monotonic()+300
  while sp.poll() is None and not stop() and time.monotonic()<limit:time.sleep(.1)
  if stop() or sp.poll() is None:
   if sp.poll() is None and captured_signal(sp,signal.SIGTERM,sbirth):
    try:sp.wait(10)
    except subprocess.TimeoutExpired:
     if captured_signal(sp,signal.SIGKILL,sbirth):sp.wait()
   partial('official score interrupted or timed out');return 75
  rc=sp.wait()
 finally:sl.close()
 if rc!=0 or 'KERNEL_NETWORK_DENY_CONFIRMED' not in scorelog.read_text():atom(out/'TERMINAL.json',{'state':'capture_complete_score_unknown','expected':300,'counts':counts,'scorer_rc':rc,'paired_delta':'UNCOMPUTED','partial':False});return 0
 files=sorted(scoredir.glob('*-eval_results_*.jsonl'));assert len(files)==2
 for f in files:assert len(f.read_text().splitlines())==300
 atom(out/'TERMINAL.json',{'state':'single_arm_official_score','expected':300,'counts':counts,'score_files':{f.name:sha(f.read_bytes()) for f in files},'responses_sha256':sha(rp.read_bytes()),'paired_delta':'UNCOMPUTED','adoption':'UNCLAIMED','partial':False});return 0
if __name__=='__main__':sys.exit(main())
