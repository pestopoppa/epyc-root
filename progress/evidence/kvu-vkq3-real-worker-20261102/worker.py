#!/usr/bin/env python3
"""One genuine >64k architect replay per VKQ arm; no transcript in native receipts."""
import hashlib,importlib.util,json,os,pathlib,signal,socket,subprocess,sys,tempfile,threading,time,urllib.request
import mode_guard
import port_ownership
from exposure_ledger import PairedExposure
import input_receipt
D=pathlib.Path(__file__).resolve().parent;K=pathlib.Path('/mnt/raid0/llm/kernels/builds/cpu-20261004-9a3f1392a/bin')
MODEL='/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf';DRAFT='/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf';SMALL='/mnt/raid0/llm/models/Qwen_Qwen3-0.6B-Q8_0.gguf'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read_bounded(path,limit):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  import stat
  if not stat.S_ISREG(os.fstat(fd).st_mode):raise ValueError('input is not regular')
  with os.fdopen(fd,'rb') as f:
   fd=-1;data=f.read(limit+1)
  if len(data)>limit:raise ValueError('input too large')
  return data
 finally:
  if fd!=-1:os.close(fd)
def prebuilt_input(plan,plan_bytes,receipt_path,receipt_sha256,prompt_path,model_path,catalog_path):
 """Load preflight evidence bound to the plan; caller must ensure input custody.

 The external receipt digest must originate from the reviewed launcher, not the
 receipt itself. Weight bytes are not rehashed here; their custody is separate.
 """
 raw=read_bounded(receipt_path,65536)
 if not isinstance(receipt_sha256,str) or len(receipt_sha256)!=64 or hashlib.sha256(raw).hexdigest()!=receipt_sha256:raise ValueError('receipt identity mismatch')
 def unique(pairs):
  d={}
  for k,v in pairs:
   if k in d:raise ValueError('duplicate receipt key')
   d[k]=v
  return d
 receipt=json.loads(raw,object_pairs_hook=unique)
 if not isinstance(receipt,dict):raise ValueError('bad receipt')
 catalog_bytes=read_bounded(catalog_path,1024*1024);catalog=input_receipt.parse_catalog(catalog_bytes)
 runtime_bytes=read_bounded(D/'RUNTIME-CODE.sha256',1024*1024)
 runtime_catalog=input_receipt.parse_catalog(runtime_bytes)
 tokenizer_path=receipt.get('tokenizer_path')
 if tokenizer_path not in runtime_catalog or input_receipt.digest(tokenizer_path)!=runtime_catalog[tokenizer_path]:raise ValueError('tokenizer binary does not match pinned runtime catalog')
 if str(model_path) not in catalog or DRAFT not in catalog:raise ValueError('catalog missing model or draft')
 expected={'schema':'kvu-vkq3-preflight-v1','plan_sha256':hashlib.sha256(plan_bytes).hexdigest(),'prompt_sha256':plan['context']['sha256'],
           'tokenizer_sha256':runtime_catalog[tokenizer_path],
           'model_catalog_sha256':hashlib.sha256(catalog_bytes).hexdigest(),
           'tokenizer_path':str(tokenizer_path),'model_path':str(model_path),
           'tokenizer_flags':['--stdin','--ids','--no-escape'],
           'model_shard0_sha256':catalog[str(model_path)],'draft_path':DRAFT,'draft_sha256':catalog[DRAFT]}
 if any(receipt.get(k)!=v for k,v in expected.items()):raise ValueError('receipt does not match selected inputs')
 count=receipt.get('token_count')
 input_receipt.check_count(plan,count)
 prompt_bytes=read_bounded(prompt_path,64*1024*1024)
 if hashlib.sha256(prompt_bytes).hexdigest()!=expected['prompt_sha256']:raise ValueError('prompt identity mismatch')
 return prompt_bytes.decode('utf-8'),receipt
def atom(p,o):
 fd,n=tempfile.mkstemp(dir=p.parent,prefix='.tmp-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(o,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
  os.link(n,p)
 finally:os.unlink(n)
def emit(event):mode_guard.emit(D/'events.jsonl',event)
def open_native_attempt(drydir,result):
 """Open the keeper's unique attempt without following path symlinks."""
 drydir=pathlib.Path(drydir);result=pathlib.Path(result)
 if not drydir.is_absolute() or not result.is_absolute() or '..' in drydir.parts or '..' in result.parts:raise ValueError('invalid native attempt path')
 try:rel=result.relative_to(drydir)
 except ValueError as e:raise ValueError('invalid native attempt path') from e
 if len(rel.parts)!=3 or rel.parts[0]!='native-attempts' or not rel.parts[1].startswith('attempt-') or len(rel.parts[1])<=len('attempt-') or rel.parts[2]!='native-result.json':raise ValueError('invalid native attempt path')
 flags=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW
 fd=os.open('/',flags)
 try:
  for component in (*drydir.parts[1:],*rel.parts[:2]):
   newfd=os.open(component,flags,dir_fd=fd);os.close(fd);fd=newfd
  try:os.stat('native-result.json',dir_fd=fd,follow_symlinks=False)
  except FileNotFoundError:pass
  else:raise ValueError('smoke result already exists')
  resultfd=fd;fd=-1;return resultfd
 except OSError as e:raise ValueError('invalid native attempt path') from e
 finally:
  if fd!=-1:os.close(fd)

def publish_native(drydir,result,record):
 """Atomically publish inside the verified attempt directory, without overwrite."""
 fd=open_native_attempt(drydir,result);temp='.native-'+os.urandom(16).hex()
 try:
  outfd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
  try:
   with os.fdopen(outfd,'w') as out:
    json.dump(record,out,sort_keys=True);out.write('\n');out.flush();os.fsync(out.fileno())
   os.link(temp,'native-result.json',src_dir_fd=fd,dst_dir_fd=fd,follow_symlinks=False)
   os.fsync(fd)
  finally:os.unlink(temp,dir_fd=fd)
 finally:os.close(fd)

def full_terminal(outputs):
 """Decide completeness only from two successful native arm records."""
 a=outputs.get('hybrid');b=outputs.get('legacy')
 valid=bool(a and b and a.get('http_status')==200 and b.get('http_status')==200
            and a.get('acceptance') is not None and b.get('acceptance') is not None
            and a.get('tokens') is not None and b.get('tokens') is not None)
 div=None
 if valid:
  aa=a['tokens'];bb=b['tokens']
  div=next((i for i,(x,y) in enumerate(zip(aa,bb)) if x!=y),None)
  if div is None and len(aa)!=len(bb):div=min(len(aa),len(bb))
 state='complete_raw' if valid else 'incomplete_raw'
 return {'partial':not valid,'state':state,'first_divergence_index':div,
         'divergence_known':valid,'hybrid_http_status':a.get('http_status') if a else None,
         'legacy_http_status':b.get('http_status') if b else None,
         'hybrid_acceptance':a.get('acceptance') if a else None,
         'legacy_acceptance':b.get('acceptance') if b else None,
         'verdict':None,'control_no_mtp':False}

def grant_context(env, plan):
 """Validate a real grant or keeper smoke and isolate its output path."""
 dry=env.get('FILLER_DRYRUN','0')=='1'
 grants=pathlib.Path(env.get('FILLER_GRANTS_DIR') or '/mnt/raid0/llm/tmp/compute-flags/grants')
 if not grants.is_absolute():raise ValueError('grant directory must be absolute')
 if dry:
  drydir=pathlib.Path(env['FILLER_DRYRUN_DIR'])
  result=pathlib.Path(env['FILLER_DRYRUN_RESULT_PATH'])
  if not drydir.is_absolute() or not result.is_absolute() or '..' in drydir.parts or '..' in result.parts or os.path.realpath(grants)!=os.path.realpath(drydir/'grants'):raise ValueError('invalid smoke output or grant directory')
  attemptfd=open_native_attempt(drydir,result);os.close(attemptfd)
  out=result.parent/'vkq3-control'
 else:
  result=None;out=D/'run'
  if env.get('FILLER_DRYRUN','0')!='0':raise ValueError('invalid dry-run flag')
 spec=importlib.util.spec_from_file_location('vkq3_guard',D.parent/'kvu-vkq3-guard-review-20261102'/'guard.py')
 guard_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard_module)
 guard=guard_module.GrantGuard(env,grants,D/'STOP',expected_id=plan['id'])
 if guard.mode!=('qualification' if dry else 'full'):raise ValueError('mode mismatch')
 return guard,out,result
def main():
 plan_bytes=read_bounded(D/'PLAN.json',1024*1024);plan=json.loads(plan_bytes);guard,out,native_result=grant_context(os.environ,plan);mode=guard.mode;mode_guard.mode_check(mode,os.environ.get('FILLER_DRYRUN','0'));out.mkdir(mode=0o700,exist_ok=mode=='full');os.chmod(out,0o700);grant=guard.initial;deadline=guard.deadline
 if mode_guard.target_allowed(mode) and mode_guard.exposure_seen(out):
  print('refusing prior target exposure; no redraw',file=sys.stderr);return 75
 stopped=False
 def handle(*_):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGTERM,handle);signal.signal(signal.SIGINT,handle)
 def stopping():return stopped or guard.check()
 def partial(reason):
  tmp=out/'.partial.tmp';tmp.write_text(json.dumps({'partial':True,'reason':reason})+'\n');os.replace(tmp,out/'PARTIAL.json')
 if mode_guard.target_allowed(mode):
  if stopping():partial('stop or grant lost before prepared input');return 75
  prompt,receipt=prebuilt_input(
   plan,plan_bytes,os.environ['VKQ3_INPUT_RECEIPT'],
   os.environ['VKQ3_INPUT_RECEIPT_SHA256'],os.environ['VKQ3_PREBUILT_PROMPT'],
   MODEL,D/'FULL-MODELS.sha256')
  atom(out/'tokenization.json',receipt)
 else:prompt='Explain one way to make a network retry safe.'
 full_catalog_digest=sha(D/'FULL-MODELS.sha256')
 outputs={};paired_exposure=None
 for arm in (plan['arms'] if mode=='full' else plan['arms'][:1]):
  name=arm['id'];
  if stopping() or (mode=='full' and time.time()+3000>=deadline):partial('insufficient time for fresh full arm');return 75
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  model=MODEL;cmd=[str(K/'llama-server'),'-m',model,'--host','127.0.0.1','--port',str(port),'-np','1','-c','2048' if mode=='qualification' else '131072','-t',str(len(os.sched_getaffinity(0))) if mode=='qualification' else '96','-ub','512','-ngl','0','--flash-attn','on','-ctk','f16','-ctv','f16','--spec-type','draft-mtp','--spec-draft-n-max','4']
  if mode in ('full','qualification'):cmd=['numactl','--interleave=all',*cmd,'--no-mmap','--spec-draft-model',DRAFT,'--spec-draft-type-k','f16','--spec-draft-type-v','f16']
  env={'PATH':'/usr/bin:/bin','LD_LIBRARY_PATH':str(K),'OMP_NUM_THREADS':'1','HIP_VISIBLE_DEVICES':'-1','ROCR_VISIBLE_DEVICES':'-1'}
  if arm['GGML_FA_VKQ_F16']:env['GGML_FA_VKQ_F16']=arm['GGML_FA_VKQ_F16']
  log=os.fdopen(os.open(out/(name+'.server.log'),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb');launch_cmd=[sys.executable,'-B',str(D/'pdeath_exec.py'),str(os.getpid()),*cmd]
  try:p=subprocess.Popen(launch_cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
  except BaseException:
   log.close();raise
  birth=None
  try:
   birth=pathlib.Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19]
   atom(out/(name+'.server.json'),{'arm':name,
   'mode':mode,
   'argv':cmd,
   'launch_argv':launch_cmd,
   'pid':p.pid,
   'birth':birth,
   'grant_sha256':hashlib.sha256(grant).hexdigest() if grant else None,
   'grant_text':grant.decode() if grant else None,
   'env_knob':arm['GGML_FA_VKQ_F16'],
   'source_sha256':sha(D/'SOURCE-SHA256SUMS'),
   'plan_sha256':sha(D/'PLAN.json'),
   'context_sha256':hashlib.sha256(prompt.encode()).hexdigest(),
   'binary_sha256':sha(K/'llama-server'),
   'runtime_catalog_sha256':sha(D/'RUNTIME-INPUTS.sha256'),
   'full_model_catalog_sha256':full_catalog_digest if mode=='full' else None,
   'draft_head_sha256':'5ff54097406a905cf3a724c709124ceb0e3e10235ee862298969e91c96fa96e6' if mode=='full' else None,
   'cpu_affinity':sorted(os.sched_getaffinity(0)),
   'started_epoch':time.time()})
   url=f'http://127.0.0.1:{port}';ready=False;limit=time.monotonic()+1800
   while time.monotonic()<limit and p.poll() is None and not stopping():
    try:
     with urllib.request.urlopen(url+'/health',timeout=1) as r:ready=r.status==200
    except Exception:pass
    if ready:break
    time.sleep(.2)
   if stopping():partial('interrupted startup');return 75
   if not ready:atom(out/(name+'.failure.json'),{'reason':'server_not_ready','rc':p.poll()});continue
   if p.poll() is not None or not port_ownership.owns_loopback_listener(p.pid,int(birth),port):
    raise RuntimeError('captured server does not own the loopback listener')
   payload={'prompt':prompt,**plan['request']};payload['n_predict']=16 if mode=='qualification' else payload['n_predict']
   if mode=='full':
    if paired_exposure is None:
     paired_exposure=PairedExposure('/mnt/raid0/llm/tmp/compute-flags/kvu-vkq3-exposures',hashlib.sha256(prompt.encode()).hexdigest(),hashlib.sha256(plan_bytes).hexdigest(),[a['id'] for a in plan['arms']])
    paired_exposure.reserve_arm(name)
   atom(out/((name+'.exposure.json') if mode=='full' else 'qualification.control.json'),{'arm':name,'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest(),'plan_sha256':hashlib.sha256(plan_bytes).hexdigest(),'grant_sha256':hashlib.sha256(grant).hexdigest() if grant else None,'started_epoch':time.time()});state={}
   def request():
    try:
     req=urllib.request.Request(url+'/completion',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
     with urllib.request.urlopen(req,timeout=2800 if mode=='full' else 300) as r:state['http_status']=r.status;state['raw']=r.read().decode()
    except Exception as e:state['error']=repr(e)
   t=threading.Thread(target=request,daemon=True);t.start()
   while t.is_alive() and p.poll() is None and not stopping():t.join(.1)
   if stopping():partial('interrupted exposed request');return 75
   t.join(1)
   if t.is_alive():partial('request thread failed to drain');return 75
   if 'error' in state:atom(out/(name+'.failure.json'),{'reason':'request_failed','error':state.get('error')});continue
   try:body=json.loads(state['raw'])
   except Exception as e:atom(out/(name+'.failure.json'),{'reason':'bad_native_json','error':repr(e)});continue
   timings=body.get('timings') or {};draft=timings.get('draft_n');accepted=timings.get('draft_n_accepted');tokens=body.get('tokens');result={'arm':name,'http_status':state['http_status'],'native_response':body,'response_sha256':hashlib.sha256(state['raw'].encode()).hexdigest(),'draft_n':draft,'draft_n_accepted':accepted,'acceptance':mode_guard.native_acceptance(draft,accepted),'tokens':mode_guard.token_ids(tokens),'grant_sha256':hashlib.sha256(grant).hexdigest() if grant else None,'finished_epoch':time.time()};atom(out/(name+'.response.json'),result);outputs[name]=result
  finally:
   try:
    if p.poll() is None:
     try:p.send_signal(signal.SIGTERM)
     except ProcessLookupError:pass
     try:p.wait(10)
     except subprocess.TimeoutExpired:
      try:p.kill()
      except ProcessLookupError:pass
      p.wait(10)
    if p.poll() is None:raise RuntimeError('captured server did not exit')
   finally:log.close()
   atom(out/(name+'.drain.json'),{'pid':p.pid,'birth':birth,'returncode':p.returncode,'drained':True,'server_log_sha256':sha(out/(name+'.server.log'))})
 if mode=='qualification':
  a=outputs.get('hybrid')
  if not a or a.get('http_status')!=200 or a.get('acceptance') is None or a.get('tokens') is None:raise RuntimeError('qualification control failed or native MTP counts/token IDs invalid')
  control={'kind':'qualification_control','http_status':a['http_status'],'target_exposed':False,'draft_n':a['draft_n'],'draft_n_accepted':a['draft_n_accepted'],'acceptance':a['acceptance'],'token_count':len(a['tokens']),'plan_sha256':sha(D/'PLAN.json'),'full_model_catalog_sha256':full_catalog_digest,'source_sha256':sha(D/'SOURCE-SHA256SUMS'),'grant_sha256':hashlib.sha256(grant).hexdigest()}
  atom(out/'QUALIFICATION.json',control)
  if stopping():raise RuntimeError('grant lost before native result publication')
  publish_native(os.environ['FILLER_DRYRUN_DIR'],native_result,control)
  return 0
 terminal=full_terminal(outputs);state=terminal['state']
 atom(out/'TERMINAL.json',terminal);emit({'kind':'target_terminal','state':state,'terminal_path':str(out/'TERMINAL.json')});return 0 if state=='complete_raw' else 1
if __name__=='__main__':sys.exit(main())
