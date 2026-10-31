#!/usr/bin/env python3
"""Unqualified held-out capture draft. Does no work without actual dev selection."""
import hashlib,importlib.util,json,os,pathlib,signal,subprocess,sys,time
D=pathlib.Path(__file__).resolve().parent;L=D.parent/'lex2';sys.path.insert(0,str(L));import grid_job as g
P=pathlib.Path('/mnt/raid0/llm/data/contextual-earnings22-59d7f947/test-native/MANIFEST-V2.json')
def main():
 mode=os.getenv('LEX2_TEST_MODE','full');assert mode in ('full','smoke');catalog=D/'SOURCE-SHA256SUMS'
 if not catalog.is_file():raise SystemExit('HELD: future held-out source catalog and qualified launcher absent')
 cp=D/'TEST-CONVERSATION-CONTEXTS.json';fp=D/'FLEURS-CONTEXT-POLICY.json';selection=L/'DEV-SELECTION.json';plan=L/'HELDOUT-PLAN.json'
 if mode=='smoke':
  # Engineering probe only. It neither reads a test row nor writes a selection.
  alpha=.5;scope='local';selection_hash=None;plan_hash=None;instance_hash=None;domain=['Kennedy'];wav='/mnt/raid0/llm/whisper.cpp/samples/jfk.wav';rows=[{'id':'engineering-jfk','corpus':'engineering','wav':wav,'wav_sha256':g.digest(wav),'local':['Kennedy'],'aa_overlap_status':None}]
 else:
  if not plan.exists() or not (D/'INSTANCE-PLAN.json').exists():raise SystemExit('HELD: actual dev selection and pre-test heldout instance absent')
  contract=json.loads(plan.read_text());instance=json.loads((D/'INSTANCE-PLAN.json').read_text())
  if contract['selection_sha256']!=g.digest(selection) or contract['test_inference_started'] is not False:raise RuntimeError('selection/plan drift')
  selected=contract['selection'];frozen=json.loads(selection.read_text())
  if selected!=frozen['selection'] or frozen.get('test_opened') is not False or frozen.get('nonlist_noise_floor_state')!='known_lexical' or frozen['raw_terminal_sha256']!=g.digest(L/'run/TERMINAL.json'):raise RuntimeError('unfrozen selection or dev evidence drift')
  alpha=selected['alpha'];scope=selected['scope'];selection_hash=g.digest(selection);plan_hash=g.digest(plan);instance_hash=g.digest(D/'INSTANCE-PLAN.json')
  for key,value in {'selection_sha256':selection_hash,'base_heldout_plan_sha256':plan_hash,'source_catalog_sha256':g.digest(catalog),'contexts_sha256':g.digest(cp),'policy_sha256':g.digest(fp),'contract_sha256':g.digest(D/'HELDOUT-CONTRACT.md'),'selected_alpha':alpha,'selected_scope':scope,'native_attempts_planned':25095,'test_inference_started':False,'test_scoring_started':False}.items():
   if instance.get(key)!=value:raise RuntimeError('pre-test instance drift: '+key)
  if alpha not in (0,.5,1,2,3,5) or scope not in ('local','global'):raise RuntimeError('unrecognized frozen selection')
  original=[['nemo','none',0],['nemo','global',alpha],['nemo','local',alpha],['whisper','none',None],['whisper','global',None],['whisper','local',None]];aux=[['whisper','none-auto',None],['whisper','global-auto',None],['whisper','local-auto',None]]
  if instance.get('original_cells')!=original or instance.get('contextual_auto_language_whisper_auxiliary_cells')!=aux:raise RuntimeError('pre-test cell plan drift')
  ctx=json.loads(cp.read_text());fleur=json.loads(fp.read_text());calls=ctx['calls'];domain=fleur['global_context'];data=json.loads(P.read_text());rows=[]
  if g.digest(P)!=ctx['test_manifest_sha256'] or g.digest(cp)!=fleur['test_contexts_sha256']:raise RuntimeError('cohort/context drift')
  for r in data['records']:
   if r['eligibility']=='heldout':rows.append({'id':r['file_id'],'corpus':'contextual','wav':r['wav_path'],'wav_sha256':r['wav_sha256'],'annotation_path':r['annotations_path'],'annotation_sha256':r['annotations_sha256'],'local':calls[r['call_id']],'aa_overlap_status':r['aa_overlap_status']})
  for r in fleur['rows']:rows.append({'id':r['clip_id'],'corpus':'fleurs','wav':r['wav_path'],'wav_sha256':r['wav_sha256'],'local':calls[r['assigned_call_id']],'language':r['language'],'aa_overlap_status':None})
  if len(rows)!=3805:raise RuntimeError('wrong original denominator')
  if not os.getenv('FILLER_ID') or not os.getenv('FILLER_CPUS') or not g.observation()['grant_sha256']:raise RuntimeError('missing actual grant')
 out=D/os.getenv('LEX2_OUT','run');out.mkdir(exist_ok=True);deadline=int(os.environ['FILLER_DEADLINE'])-30;stop=False
 def onstop(*_):
  nonlocal stop;stop=True
 signal.signal(signal.SIGINT,onstop);signal.signal(signal.SIGTERM,onstop)
 def stopping():return stop or (D/'STOP').exists() or time.time()>=deadline
 def partial(reason):
  p=out/'.partial.tmp';p.write_text(json.dumps({'partial':True,'reason':reason})+'\n');os.replace(p,out/'PARTIAL.json')
 cells=[('nemo','local',.5),('whisper','none',None),('whisper','none-auto',None)] if mode=='smoke' else [('nemo','none',0),('nemo','global',alpha),('nemo','local',alpha),('whisper','none',None),('whisper','global',None),('whisper','local',None),('whisper','none-auto',None),('whisper','global-auto',None),('whisper','local-auto',None)];cell_timeout=100 if mode=='smoke' else 600;counts={'ok':0,'failure':0,'unknown':0};n=0
 for engine,kind,a in cells:
  for r in rows:
   if kind.endswith('-auto') and r['corpus']=='fleurs':continue
   if stopping():partial('before attempt');return 75
   basekind=kind.removesuffix('-auto');context=[] if basekind=='none' else domain if basekind=='global' else r['local'];context=sorted(set(x.strip() for x in context if x.strip()));wav=pathlib.Path(r['wav']);wavsha=g.digest(wav)
   if wavsha!=r['wav_sha256'] or (r.get('annotation_path') and g.digest(r['annotation_path'])!=r['annotation_sha256']):raise RuntimeError('heldout clip or annotations drift')
   cmd=g.make_recipe(engine,a,wav,context,str(min(8,len(os.sched_getaffinity(0)))))
   if engine=='whisper' and (r['corpus']=='fleurs' or kind.endswith('-auto')):cmd[cmd.index('-l')+1]='auto'
   key=hashlib.sha256(f"{engine}|{kind}|{a}|{r['corpus']}|{r['id']}".encode()).hexdigest();exp=out/(key+'.exposure.json');res=out/(key+'.result.json');so=out/(key+'.stdout');se=out/(key+'.stderr');samples=out/(key+'.samples.jsonl')
   base={'schema':'cs8.lex2.heldout-attempt.v1','source_catalog_sha256':g.digest(catalog),'instance_plan_sha256':instance_hash,'selection_sha256':selection_hash,'heldout_plan_sha256':plan_hash,'contexts_sha256':g.digest(cp),'fleurs_policy_sha256':g.digest(fp),'contract_sha256':g.digest(D/'HELDOUT-CONTRACT.md'),'corpus':r['corpus'],'clip_id':r['id'],'wav_sha256':wavsha,'annotation_sha256':r.get('annotation_sha256'),'engine':engine,'scope':kind,'alpha':a,'selected_scope':scope,'context_sha256':hashlib.sha256(json.dumps(context,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),'context_count':len(context),'recipe_sha256':g.recipe_sha(cmd),'model_sha256':os.environ['LEX2_NEMO_MODEL_SHA'] if engine=='nemo' else os.environ['LEX2_WHISPER_MODEL_SHA'],'runtime_sha256':g.digest(g.N if engine=='nemo' else g.WH),'spm_sha256':os.environ['LEX2_SPM_SHA'] if engine=='nemo' else None,'aa_overlap_status':r['aa_overlap_status'],'language':r.get('language')}
   if res.exists():
    e=json.loads(exp.read_text());v=json.loads(res.read_text());g.validate_cached_binding(e['binding'],base)
    if v['binding']!=e['binding'] or any(g.digest(p)!=v[k] for p,k in [(so,'stdout_sha256'),(se,'stderr_sha256'),(samples,'samples_sha256')]):raise RuntimeError('cached result drift')
    status=g.classify_native(engine,a,len(context),v['rc'],so.read_bytes(),se.read_text(errors='replace'))
    if any(v.get(k)!=value for k,value in status.items()) or not v.get('reaped'):raise RuntimeError('cached status/drain drift')
    sample_rows=[json.loads(line) for line in samples.read_text().splitlines()]
    if mode=='full':
     old=e['binding'];raw=old.get('grant_text')
     if not raw or hashlib.sha256(raw.encode()).hexdigest()!=old.get('grant_sha256'):raise RuntimeError('original grant binding missing')
     if v['status']=='ok' and not any(x.get('sampled_while_child_live') and x.get('grant_id')==old.get('grant_id') and x.get('grant_sha256')==old.get('grant_sha256') and x.get('child_pid')==v.get('child_pid') and x.get('child_birth') is not None and x.get('child_birth')==v.get('child_birth') for x in sample_rows):raise RuntimeError('original live grant sample missing')
    counts[v['status']]+=1;continue
   if exp.exists():g.validate_cached_binding(json.loads(exp.read_text())['binding'],base);counts['unknown']+=1;continue
   if stopping() or not g.enough_time(time.time(),deadline,cell_timeout):partial('insufficient full native request and drain budget');return 75
   obs=g.observation()
   if mode=='full' and (not obs['grant_sha256'] or not obs['grant_text']):raise RuntimeError('actual grant vanished before exposure')
   binding={**base,'affinity':sorted(os.sched_getaffinity(0)),'grant_id':os.getenv('FILLER_ID'),'grant_sha256':obs['grant_sha256'],'grant_text':obs['grant_text'],'regions':os.getenv('WS58_REGIONS') or os.getenv('FILLER_CPUS')};g.atom(exp,{'binding':binding,'argv':cmd,'started_epoch':time.time()});env=os.environ.copy();env.update(OMP_NUM_THREADS='1',HIP_VISIBLE_DEVICES='-1',ROCR_VISIBLE_DEVICES='-1')
   if engine=='nemo':env.update(LD_LIBRARY_PATH=str(L/'install/lib')+':'+g.DEP,LEX2_SPM_PATH=str(g.M/'tokenizer.model'),LEX2_BOOST_TRACE='1')
   else:env['LD_LIBRARY_PATH']=str(g.WH.parent)
   start=time.monotonic()
   with so.open('xb') as stdout,se.open('xb') as stderr,samples.open('x') as sf:
    p=subprocess.Popen(cmd,stdout=stdout,stderr=stderr,env=env);last=0
    try:child_birth=pathlib.Path('/proc',str(p.pid),'stat').read_text().rsplit(') ',1)[1].split()[19]
    except (OSError,IndexError):child_birth=None
    while p.poll() is None:
     if time.monotonic()-last>=5:
      sample=g.observation();sample.update(child_pid=p.pid,child_birth=child_birth,sampled_while_child_live=p.poll() is None);sf.write(json.dumps(sample,sort_keys=True)+'\n');sf.flush();os.fsync(sf.fileno());last=time.monotonic()
     if stopping() or time.monotonic()-start>cell_timeout:
      p.terminate()
      try:p.wait(5)
      except subprocess.TimeoutExpired:p.kill();p.wait()
      if stopping():partial('interrupted exposed attempt');return 75
      break
     time.sleep(.1)
   v=g.classify_native(engine,a,len(context),p.returncode,so.read_bytes(),se.read_text(errors='replace'));g.atom(res,{'binding':binding,**v,'child_pid':p.pid,'child_birth':child_birth,'rc':p.returncode,'wall_s':time.monotonic()-start,'stdout_sha256':g.digest(so),'stderr_sha256':g.digest(se),'samples_sha256':g.digest(samples),'reaped':p.poll() is not None});counts[v['status']]+=1;n+=1
 g.atom(out/'TERMINAL.json',{'partial':False,'state':'complete_raw' if counts['failure']==counts['unknown']==0 else 'incomplete_raw','mode':mode,'corpus_counts':{'engineering':1} if mode=='smoke' else {'contextual':755,'fleurs':3050},'cells':len(cells),'counts':counts,'selection_sha256':selection_hash,'quality_verdict':None});return 0
if __name__=='__main__':sys.exit(main())
