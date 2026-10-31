#!/usr/bin/env python3
"""Prospective LEX2 dev native capture. No scoring; exposed unknowns never replay."""
import hashlib,json,os,pathlib,signal,subprocess,sys,tempfile,time,wave
D=pathlib.Path(__file__).resolve().parent; DATA=pathlib.Path('/mnt/raid0/llm/data/contextual-earnings22-59d7f947/dev-native/MANIFEST-V2.json')
M=pathlib.Path('/mnt/raid0/llm/models/nemo-speech-nemotron35-1c8deae'); W=pathlib.Path('/mnt/raid0/llm/models/whisper-ggml/ggml-large-v3-turbo.bin'); N=D/'install/bin/nemo-speech'; WH=pathlib.Path('/mnt/raid0/llm/kernels/builds/stt-20260731-b30737922/bin/whisper-cli'); DEP='/mnt/raid0/llm/tmp/codex3-cs8-stt2-nemospeech-20261030/deps/prefix/usr/lib/x86_64-linux-gnu'
def digest(p):
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
def make_recipe(engine,alpha,wav,context,threads):
 if engine=='nemo':
  cmd=[str(N),'transcribe',str(wav),'--model',str(M/'nemotron-3.5-asr-streaming-0.6b.q8_0.gguf'),'--device','cpu','--stream','--asr.backend.threads',str(threads),'--asr.decoder.boosting_tree_alpha',str(alpha),'--no-warmup']
  if alpha and context:
   cmd+=['--speech-context-boost','1']
   for phrase in context:cmd+=['--speech-context',phrase]
  return cmd
 if engine=='whisper':
  cmd=[str(WH),'-m',str(W),'-f',str(wav),'-ng','-nfa','-t',str(threads),'-bo','1','-bs','1','-tp','0','-nf','-l','en','-nt']
  if context:cmd+=['--prompt',', '.join(context)]
  return cmd
 raise ValueError('unknown engine')

def recipe_sha(cmd):
 return hashlib.sha256(json.dumps(cmd,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def validate_cached_binding(saved,current):
 for key,value in current.items():
  if saved.get(key)!=value:raise RuntimeError('cached immutable binding drift: '+key)

def enough_time(now,deadline,timeout,cleanup=30):
 return now+timeout+cleanup < deadline

def classify_native(engine,alpha,context_count,rc,stdout,stderr):
 active='RNNT word boosting active' in stderr
 required=engine=='nemo' and bool(alpha) and context_count>0
 trace=f'effective_alpha={alpha:.6f}' if required else None
 valid=rc==0 and bool(stdout) and (not required or (active and trace in stderr)) and not (engine=='nemo' and not alpha and active)
 return {'status':'ok' if valid else 'failure','trace_required':bool(required),'trace_present':bool(required and active and trace in stderr)}

def observation():
 fid=os.getenv('FILLER_ID'); grant=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants')/(fid+'.grant') if fid else None
 raw=grant.read_bytes() if grant and grant.is_file() else None
 return {'epoch':time.time(),'loadavg':pathlib.Path('/proc/loadavg').read_text().strip(),'grant_id':fid,'grant_sha256':hashlib.sha256(raw).hexdigest() if raw else None,'grant_text':raw.decode(errors='replace') if raw else None,'co_tenant_generating':'unknown','co_tenant_basis':'not instrumented; no inference of absence'}
def main():
 mode=os.environ['LEX2_MODE']; assert mode in ('smoke','full')
 out=D/os.environ.get('LEX2_OUT','run');out.mkdir(exist_ok=True)
 plan=digest(D/'GRID-PLAN.json');catalog=digest(D/'SOURCE-SHA256SUMS'); data=json.loads(DATA.read_text()); domain=json.loads((D/'DOMAIN-LEXICON-PROPOSAL.json').read_text())['phrases']['en'];contexts=json.loads((D/'CONVERSATION-CONTEXTS.json').read_text());deadline=int(os.environ['FILLER_DEADLINE'])-30
 if contexts['dev_manifest_sha256']!=digest(DATA):raise RuntimeError('conversation contexts input drift')
 cell_timeout=100 if mode=='smoke' else 600
 if mode=='full' and (not os.getenv('FILLER_ID') or not os.getenv('FILLER_CPUS') or observation()['grant_sha256'] is None):raise RuntimeError('actual grant identity required')
 if mode=='smoke':
  wav=pathlib.Path('/mnt/raid0/llm/whisper.cpp/samples/jfk.wav'); rows=[{'file_id':'engineering-jfk','wav_path':str(wav),'wav_sha256':digest(wav),'dictionary':['Kennedy'],'annotations_sha256':None}]; cells=[('nemo','local',0.5),('whisper','none',None)]
 else:rows=data['records'];cells=[('nemo',s,a) for s in ('global','local') for a in (0,0.5,1,2,3,5)]+[('whisper',s,None) for s in ('none','global','local')]
 stopped=False
 def stop(*_):
  nonlocal stopped;stopped=True
 signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
 def partial(reason):
  p=out/'PARTIAL.json';tmp=out/'.partial.tmp';tmp.write_text(json.dumps({'partial':True,'reason':reason,'at':time.time()})+'\n');os.replace(tmp,p)
 def should_stop():return stopped or (D/'STOP').exists() or time.time()>=deadline
 counts={'ok':0,'unknown':0,'failure':0}
 for engine,scope,alpha in cells:
  for r in rows:
   if should_stop():partial('stop or deadline');return 75
   if mode=='smoke':context=r['dictionary'] if scope=='local' else []
   else:
    ap=pathlib.Path(r['annotations_path']);
    if digest(ap)!=r['annotations_sha256']:raise RuntimeError('annotation drift')
    context=contexts['calls'][r['call_id']] if scope=='local' else domain if scope=='global' else []
   context=sorted(set(str(x).strip() for x in context if str(x).strip()));raw=json.dumps(context,ensure_ascii=False,separators=(',',':')).encode();ch=hashlib.sha256(raw).hexdigest();key=hashlib.sha256(f'{engine}|{scope}|{alpha}|{r["file_id"]}'.encode()).hexdigest();exp=out/(key+'.exposure.json');result=out/(key+'.result.json');wav=pathlib.Path(r['wav_path'])
   if digest(wav)!=r['wav_sha256']:raise RuntimeError('wav drift')
   env=os.environ.copy();env.update(OMP_NUM_THREADS='1',HIP_VISIBLE_DEVICES='-1',ROCR_VISIBLE_DEVICES='-1');threads=str(min(8,len(os.sched_getaffinity(0))))
   if engine=='nemo':env.update(LD_LIBRARY_PATH=str(D/'install/lib')+':'+DEP,LEX2_SPM_PATH=str(M/'tokenizer.model'),LEX2_BOOST_TRACE='1')
   else:env['LD_LIBRARY_PATH']=str(WH.parent)
   cmd=make_recipe(engine,alpha,wav,context,threads)
   immutable={'schema':'cs8.lex2.native_attempt.v1','plan_sha256':plan,'source_catalog_sha256':catalog,'corpus_manifest_sha256':digest(DATA),'clip_id':r['file_id'],'wav_sha256':r['wav_sha256'],'annotation_sha256':r['annotations_sha256'],'engine':engine,'scope':scope,'configured_alpha':alpha,'context_sha256':ch,'context_count':len(context),'recipe_sha256':recipe_sha(cmd),'model_sha256':os.environ['LEX2_NEMO_MODEL_SHA'] if engine=='nemo' else os.environ['LEX2_WHISPER_MODEL_SHA'],'runtime_sha256':digest(N if engine=='nemo' else WH),'spm_sha256':os.environ['LEX2_SPM_SHA'] if engine=='nemo' else None}
   if result.exists():
    if not exp.exists():raise RuntimeError('result without exposure')
    v=json.loads(result.read_text());e=json.loads(exp.read_text());validate_cached_binding(e['binding'],immutable)
    so=out/(key+'.stdout');se=out/(key+'.stderr');samplefile=out/(key+'.samples.jsonl')
    if v['binding']!=e['binding'] or digest(so)!=v['stdout_sha256'] or digest(se)!=v['stderr_sha256'] or digest(samplefile)!=v['samples_sha256'] or v.get('reaped') is not True or not isinstance(v.get('rc'),int):raise RuntimeError('prior output drift')
    classified=classify_native(engine,alpha,len(context),v['rc'],so.read_bytes(),se.read_text(errors='replace'))
    if any(v.get(k)!=value for k,value in classified.items()):raise RuntimeError('cached native status drift')
    samples=[json.loads(line) for line in samplefile.read_text().splitlines()]
    if mode=='full' and not any(x.get('sampled_while_child_live') and x.get('grant_id')==e['binding'].get('grant_id') and x.get('grant_sha256') for x in samples):raise RuntimeError('cached original grant sample missing')
    counts[v['status']]+=1;continue
   if exp.exists():
    validate_cached_binding(json.loads(exp.read_text())['binding'],immutable);counts['unknown']+=1;continue
   if should_stop() or not enough_time(time.time(),deadline,cell_timeout):partial('insufficient remaining time for native cap and cleanup');return 75
   binding={**immutable,'affinity':sorted(os.sched_getaffinity(0)),'grant_id':os.getenv('FILLER_ID'),'regions':os.getenv('WS58_REGIONS') or os.getenv('FILLER_CPUS')}
   atom(exp,{'binding':binding,'argv':cmd,'started_epoch':time.time()});start=time.monotonic();so=out/(key+'.stdout');se=out/(key+'.stderr')
   with so.open('xb') as stdout,se.open('xb') as stderr:
    p=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,env=env); samplefile=out/(key+'.samples.jsonl'); samplefile.touch(exist_ok=False); last=0
    while p.poll() is None:
     if time.monotonic()-last>=5:
      sample=observation();sample['child_pid']=p.pid;sample['sampled_while_child_live']=p.poll() is None
      with samplefile.open('a') as sf:sf.write(json.dumps(sample,sort_keys=True)+'\n');sf.flush();os.fsync(sf.fileno())
      last=time.monotonic()
     if should_stop():
      p.terminate()
      try:p.wait(5)
      except subprocess.TimeoutExpired:p.kill();p.wait()
      partial('interrupted exposed attempt');return 75
     if time.monotonic()-start>cell_timeout:
      p.terminate()
      try:p.wait(5)
      except subprocess.TimeoutExpired:p.kill();p.wait()
      break
     time.sleep(.1)
   classified=classify_native(engine,alpha,len(context),p.returncode,so.read_bytes(),se.read_text(errors='replace'))
   atom(result,{'binding':binding,**classified,'rc':p.returncode,'wall_s':time.monotonic()-start,'stdout_sha256':digest(so),'stderr_sha256':digest(se),'reaped':p.poll() is not None,'samples_sha256':digest(samplefile)});counts[classified['status']]+=1
 atom(out/'TERMINAL.json',{'partial':False,'mode':mode,'counts':counts,'original_clips':len(rows),'cells':len(cells),'scored':False,'state':'complete_raw' if not counts['unknown'] and not counts['failure'] else 'incomplete_raw'});return 0
if __name__=='__main__':sys.exit(main())
