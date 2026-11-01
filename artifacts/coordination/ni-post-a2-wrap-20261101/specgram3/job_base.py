import os,sys,pathlib,time,subprocess,json,hashlib,signal,datetime
S=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(S))
from native_event import parse_first_native_decode
MODE=sys.argv[1]; QUAL_PHASE=os.environ.get('FILLER_QUAL_PHASE'); IS_QUAL=QUAL_PHASE in ('normal','cutoff'); IS_CAL=os.environ.get('FILLER_R11_CALIBRATION')=='1'; IS_FIXTURE=IS_QUAL or IS_CAL; OUT=(pathlib.Path(os.environ['FILLER_RESULTS_DIR'])/QUAL_PHASE if IS_QUAL else pathlib.Path(os.environ['FILLER_RESULTS_DIR']) if IS_CAL else S/'out'); OUT.mkdir(parents=True,exist_ok=True)
def write(name,obj):
 p=OUT/name;t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(obj,indent=2)+'\n');t.replace(p)
def write_path(path,obj):
 p=pathlib.Path(path);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n');t.replace(p)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
pins=json.loads((S/'PINS.json').read_text())
for p,h in pins['files'].items():
 if sha(p)!=h:raise RuntimeError('source/image pin drift '+p)
model=pathlib.Path(pins['model']['path']);h=hashlib.sha256()
with model.open('rb') as f:h.update(f.read(64*1024**2));f.seek(-64*1024**2,2);h.update(f.read())
if model.stat().st_size!=pins['model']['size'] or h.hexdigest()!=pins['model']['edge_sha256']:raise RuntimeError('model edge drift')
for path,record in pins['auxiliary_models'].items():
 pth=pathlib.Path(path);hh=hashlib.sha256()
 with pth.open('rb') as f:hh.update(f.read(64*1024**2));f.seek(max(0,pth.stat().st_size-64*1024**2));hh.update(f.read())
 if pth.stat().st_size!=record['size'] or hh.hexdigest()!=record['edge_sha256']:raise RuntimeError('auxiliary model metadata source drift '+path)
cpus=os.environ['FILLER_CPUS'];threads=os.environ['FILLER_THREADS'];qual_manifest=None;first_request=None
stop_path=pathlib.Path(os.environ.get('FILLER_STOPFILE',str(S/'STOP')))
end=float(os.environ.get('FILLER_DEADLINE',str(time.time()+285))); stop=False;captured={};peak=0;samples=0;children=[]
def sig(signum,frame):
 global stop
 stop=True
signal.signal(signal.SIGTERM,sig);signal.signal(signal.SIGINT,sig)
write('BEGIN.json',dict(mode=MODE,qual_phase=QUAL_PHASE,pins_sha=sha(S/'PINS.json'),cpus=cpus,threads=threads,deadline=end,started=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),model=pins['model'],scope='combined native teacher-forced component + independent autoregressive greedy +1.0.1 forced-token/trim replay; missing auxiliary q36 tokenizer equality remains explicit; no adoption'))
if IS_FIXTURE:
 qual_manifest=json.loads(pathlib.Path(os.environ.get('WS58_MANIFEST_PATH',str(S/'ready.json'))).read_text())
 request_manifest=json.loads((S/'request-manifest.json').read_text())
 production_recipe=json.loads(pathlib.Path(qual_manifest['production_recipe']['path']).read_text())

def owned_tree(root):
 pending=[root];seen=set()
 while pending:
  pid=pending.pop()
  if pid in seen:continue
  seen.add(pid)
  try: children=[int(x) for x in pathlib.Path('/proc',str(pid),'task',str(pid),'children').read_text().split()]
  except (OSError,ValueError):continue
  pending.extend(children)
 return seen

def native_llama_event(child_pid,command,log_path,log_text,started):
 global first_request
 if not IS_FIXTURE:return None
 try:event=parse_first_native_decode(log_text,qual_manifest['prompt_tokens_required'])
 except ValueError as e:raise RuntimeError('native first-decode event does not match the declared fixture input: '+str(e)) from e
 kind=event['kind'];script=event['script'];prompt_tokens=event['prefix_tokens'];script_tokens=event['script_tokens']
 native_pid=None;native_argv=None;native_birth=None;native_exe=None
 for pid in owned_tree(child_pid):
  try:
   exe=str(pathlib.Path('/proc',str(pid),'exe').resolve())
   if pathlib.Path(exe)!=(S/'bench-specgram3').resolve():continue
   raw=pathlib.Path('/proc',str(pid),'cmdline').read_bytes();argv=[x.decode() for x in raw.split(b'\0') if x]
   st=pathlib.Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
   native_pid=pid;native_argv=argv;native_birth=int(st[19]);native_exe=exe;break
  except (OSError,ValueError,IndexError):continue
 if native_pid is None or native_argv is None:raise RuntimeError('first native decode line had no live owned bench-specgram3 child')
 def argval(name):
  try:return native_argv[native_argv.index(name)+1]
  except (ValueError,IndexError):return None
 model_path=argval('--logits-model') or argval('--model');native_threads=argval('--threads')
 if model_path!=pins['model']['path'] or native_threads!=str(qual_manifest['rate_basis']['production_threads']):
  raise RuntimeError('native child model/thread argv differs from pinned production recipe')
 if argval('--model')!=pins['model']['path'] or pathlib.Path(native_exe)!=pathlib.Path(production_recipe['native_benchmark']['binary']).resolve() or sha(native_exe)!=production_recipe['native_benchmark']['binary_sha256']:
  raise RuntimeError('native child executable or model argv differs from pinned production recipe')
 native_cmd_sha=hashlib.sha256(json.dumps(native_argv,separators=(',',':')).encode()).hexdigest()
 event.update(native_pid=native_pid,native_birth_ticks=native_birth)
 event_log=OUT/'NATIVE-FIRST-EVENT.log'
 event_snapshot='\n'.join(line for line in log_text.splitlines() if line.startswith('vocab ') or line==event['prefix_line'] or line==event['summary_line'])+'\n'
 event_log.write_text(event_snapshot)
 maps_text=pathlib.Path('/proc',str(native_pid),'maps').read_text()
 expected_libs={pathlib.Path(path).name:(path,digest) for path,digest in pins['files'].items()
  if path.startswith('/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82/bin/') and '.so' in pathlib.Path(path).name}
 mapped={}
 for line in maps_text.splitlines():
  cols=line.split(maxsplit=5)
  if len(cols)<6 or not cols[5].startswith('/'):continue
  mapped_path=str(pathlib.Path(cols[5].removesuffix(' (deleted)')).resolve())
  name=pathlib.Path(mapped_path).name
  if name not in expected_libs:continue
  wanted,wanted_sha=expected_libs[name]
  if mapped_path!=str(pathlib.Path(wanted).resolve()) or sha(mapped_path)!=wanted_sha:
   raise RuntimeError('native benchmark mapped an unpinned '+name)
  mapped[name]={'path':mapped_path,'sha256':wanted_sha}
 required_libs=('libllama.so.0.0.10303','libggml-base.so.0.16.0','libggml-cpu.so.0.16.0','libggml.so.0.16.0')
 if any(name not in mapped for name in required_libs):raise RuntimeError('native benchmark did not map the pinned production CPU library set')
 llgpath=str((S/'wheel/llguidance/_lib.abi3.so').resolve());llgsha=sha(llgpath)
 if llgsha!=pins['files'][str(S/'wheel/llguidance/_lib.abi3.so')] or llgpath not in maps_text:
  raise RuntimeError('native benchmark did not map the pinned local LLGuidance 1.0.1 wheel')
 mapped['llguidance._lib.abi3.so']={'path':llgpath,'sha256':llgsha}
 proof={'ok':True,'scope':'TARGET_NATIVE_LLAMA','manifest_sha256':qual_manifest['request_manifest_sha256'],
  'production_recipe_sha256':qual_manifest['production_recipe']['sha256'],'work_unit':qual_manifest['rate_basis']['work_unit'],
  'n_ctx_total':production_recipe['native_benchmark']['n_ctx'],'n_ctx_per_slot':production_recipe['native_benchmark']['n_ctx'],
  'total_slots':production_recipe['native_benchmark']['n_seq_max'],'kv_cache_mode':qual_manifest['kv_cache_mode'],
  'prompt_tokens':prompt_tokens,'threads':int(native_threads),'model_path':model_path,
  'model_edge_sha256':pins['model']['edge_sha256'],'native_pid':native_pid,'native_birth_ticks':native_birth,
  'native_first_event':True,'native_result_identity':{'backend_type':'llama.cpp-in-process',
   'native_pid':native_pid,'native_birth_ticks':native_birth,'native_argv':native_argv,
   'native_binary_path':native_exe,'native_binary_sha256':sha(native_exe),'native_argv_sha256':native_cmd_sha,
   'loaded_libraries':mapped,
   'native_source_sha256':sha(S/'bench-grammar-sampler.cpp'),'context_source_commit':production_recipe['native_context_defaults']['source_commit'],
   'context_source_path':production_recipe['native_context_defaults']['source_path'],
   'context_source_sha256':production_recipe['native_context_defaults']['source_sha256'],
   'context_header_sha256':production_recipe['native_context_defaults']['header_sha256'],
   'compiled_libllama_sha256':production_recipe['native_context_defaults']['compiled_libllama_sha256'],
   'context_kv_type_k':production_recipe['native_context_defaults']['default_type_k'],
   'context_kv_type_v':production_recipe['native_context_defaults']['default_type_v'],
   'context_n_batch':production_recipe['native_benchmark']['n_batch'],'context_n_ubatch':production_recipe['native_benchmark']['n_ubatch'],
   'context_n_seq_max':production_recipe['native_benchmark']['n_seq_max'],'kv_unified':False,
   'event':event,'event_log_path':str(event_log),'event_log_sha256':sha(event_log),'event_log_snapshot':event_snapshot}}
 first_request=proof
 write('NATIVE-FIRST-EVENT.json',proof)
 return proof

def sample(pid):
 global peak,samples
 rows={}
 for d in pathlib.Path('/proc').iterdir():
  if not d.name.isdigit():continue
  try:
   st=(d/'stat').read_text();v=st[st.rfind(')')+2:].split();rows[int(d.name)]=(int(v[1]),int(v[2]),v[19],int(v[21])*os.sysconf('SC_PAGE_SIZE'),v[0])
  except (OSError,ValueError,IndexError):pass
 own={pid}
 for _ in range(10):
  new={p for p,(pp,g,b,r,st) in rows.items() if pp in own or g==pid}
  if new<=own:break
  own|=new
 for p in own:
  if p in rows:captured[p]=rows[p][2]
 rss=sum(rows[p][3] for p in own if p in rows);peak=max(peak,rss);samples+=1
 return rss
reason=None;actual=0
plans=[('component',.3),('component',.8)] if IS_FIXTURE else ([('component',.3)] if MODE!='full' else [('component',.3),('component',.8)])
if not IS_FIXTURE: plans += [('greedy',0),('replay',0),('tokenizer',0)]
replay_out=OUT/('replay-'+str(int(time.time())))
for phase,T in plans:
 if stop_path.exists() or stop or time.time()>=end-5:reason='active-cutoff-before-next-phase';break
 cmd=[str(S/'bench-specgram3'),'--model',str(model),'--logits-model',str(model),'--threads',threads,'--label','frontdoor-t'+str(T),'--grammar-file',str(S/'toolcall.gbnf'),'--schema-file',str(S/'toolcall.schema.json'),'--llguidance-file',str(S/'toolcall.lark'),'--paired','--profiles','real' if (IS_FIXTURE or MODE!='full') else 'real,peaked','--batches','1' if (IS_FIXTURE or MODE!='full') else '1,5','--kinds','toolcall-eager' if (IS_FIXTURE or MODE!='full') else 'toolcall-eager,toolcall-lazy,schema-eager','--reps','30' if (IS_FIXTURE or MODE=='full') else '1','--temp',str(T),'--step-ms','24.86','--out',str(OUT/'results.jsonl'),'--max-seconds',str(max(1,end-time.time()-7))]
 if MODE!='full' and not IS_FIXTURE:cmd+=['--max-scripts','1']
 if phase=='greedy':
  cmd=[str(S/'bench-specgram3'),'--model',str(model),'--logits-model',str(model),'--threads',threads,'--grammar-file',str(S/'toolcall.gbnf'),'--schema-file',str(S/'toolcall.schema.json'),'--llguidance-file',str(S/'toolcall.lark'),'--greedy-out',str(OUT/'greedy.jsonl'),'--greedy-cap','4' if MODE!='full' else '256']
  if MODE!='full':cmd+=['--kinds','toolcall-eager','--max-scripts','1']
 if phase=='replay':cmd=['/mnt/raid0/llm/tmp/specgram2-offline/v/bin/python','-I','-B',str(S/'replay101.py'),'1' if MODE!='full' else '5450']
 if phase=='tokenizer':cmd=['/mnt/raid0/llm/tmp/specgram2-offline/v/bin/python','-I','-B',str(S/'tokenizer_audit.py')]
 label=phase+'-t'+str(T)
 env=os.environ.copy();env['SPECGRAM3_REPLAY_OUT']=str(replay_out);env.update(LD_LIBRARY_PATH='/mnt/raid0/llm/kernels/production/cpu',OMP_NUM_THREADS='1',HIP_VISIBLE_DEVICES='',ROCR_VISIBLE_DEVICES='')
 if phase in ('component','greedy'):
  with (OUT/('ram-admit-'+label+'.log')).open('w') as admission:
   subprocess.run(['/mnt/raid0/llm/tmp/compute-flags/ram_admit.sh','56'],check=True,stdout=admission,stderr=subprocess.STDOUT)
 with (OUT/('native-'+label+'.log')).open('a') as log:
  p=subprocess.Popen(['stdbuf','-oL','taskset','-c',cpus,*cmd],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=False);children.append(p.pid);born=time.time()
  write('COMMAND-'+label+'.json',dict(argv=cmd,env={k:env[k] for k in ['LD_LIBRARY_PATH','OMP_NUM_THREADS','HIP_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES']},pid=p.pid))
  while p.poll() is None:
   rss=sample(p.pid)
   try:
    maps=pathlib.Path('/proc',str(p.pid),'maps').read_text()
    if 'libggml-cpu.so' in maps:(OUT/('mapped-'+label+'.txt')).write_text(maps)
   except OSError:pass
   event_file=pathlib.Path(os.environ.get('WS58_QUAL_CUTOFF_EVENT','/__none__'))
   if IS_FIXTURE and p.poll() is None:
    try: live_lines=(OUT/('native-'+label+'.log')).read_text().splitlines()
    except OSError: live_lines=[]
    if first_request is None and any(line.startswith('real logits computed in ') for line in live_lines):
     proof=native_llama_event(p.pid,cmd,OUT/('native-'+label+'.log'),'\n'.join(live_lines)+'\n',born)
    if IS_QUAL and QUAL_PHASE=='cutoff' and not event_file.exists() and first_request is not None:
     event={'id':qual_manifest['id'],'nonce':os.environ['WS58_QUAL_NONCE'],'phase':'cutoff',
      'native_pid':first_request['native_pid'],'native_birth_ticks':first_request['native_birth_ticks'],
      'native_first_event':True,'first_request':first_request}
     write_path(event_file,event)
   if stop_path.exists():reason='active-stopfile-cutoff'
   if samples%4==0:
    free=os.statvfs(S).f_bavail*os.statvfs(S).f_frsize;output_bytes=sum(q.stat().st_size for q in OUT.rglob('*') if q.is_file())
    with (OUT/'RESOURCE.jsonl').open('a') as guard:guard.write(json.dumps({'unix':time.time(),'owned_tree_rss_bytes':rss,'output_bytes':output_bytes,'free_bytes':free})+'\n')
    if output_bytes>=1024**3:reason='active-output-cap-cutoff'
    if free<151*1024**3:reason='active-disk-reserve-cutoff'
   if stop or time.time()>=end-5:reason='active-window-cutoff'
   if rss>48*1024**3:reason='48GiB-owned-tree-rss-cap'
   if reason:
    for sigval in [signal.SIGTERM,signal.SIGKILL]:
     for pid,birth in list(captured.items()):
      try:
       st=pathlib.Path('/proc',str(pid),'stat').read_text();v=st[st.rfind(')')+2:].split()
       if v[19]==birth and v[0]!='Z':os.kill(pid,sigval)
      except ProcessLookupError:pass
      except FileNotFoundError:pass
     time.sleep(.5)
    break
   time.sleep(.25)
  rc=p.wait();phase_wall=time.time()-born;actual+=phase_wall
  write('END-'+label+'.json',dict(phase=phase,wall_s=phase_wall,exit_code=rc,pid=p.pid))
 if reason:break
 if rc:reason='native-exit-'+str(rc);break
live=[]
for pid,birth in captured.items():
 try:
  st=pathlib.Path('/proc',str(pid),'stat').read_text();v=st[st.rfind(')')+2:].split()
  if v[19]==birth and v[0]!='Z':live.append(pid)
 except FileNotFoundError:pass
if live:raise RuntimeError('captured process did not drain '+str(live))
rows=[json.loads(l) for l in (OUT/'results.jsonl').read_text().splitlines()] if (OUT/'results.jsonl').exists() else []
expected=4 if IS_FIXTURE else (48 if MODE=='full' else 2)
greedy=[json.loads(l) for l in (OUT/'greedy.jsonl').read_text().splitlines()] if (OUT/'greedy.jsonl').exists() else []
replay_file=replay_out/('results_'+('1' if MODE!='full' else '5450')+'.json')
replay=json.loads(replay_file.read_text()) if replay_file.exists() else {}
expected_greedy=0 if IS_FIXTURE else (8 if MODE=='full' else 1)
if any(not r['valid'] for r in rows):reason='invalid-script-token'
if replay_file.exists() and len(replay)!=7:reason='invalid-replay-cell-matrix'
complete=not reason and len(rows)==expected and all(r['valid'] for r in rows) and len(greedy)==expected_greedy and (len(replay)==7 if not IS_FIXTURE else True)
partial=not complete and (reason is None or 'cutoff' in reason)
record=dict(mode=MODE,partial=partial,reason=reason,complete=complete,rows=len(rows),expected_rows=expected,first_request_ok=bool(rows),result_writer_ok=True,exit_ok=complete,captured_pids=captured,live_after=live,sampled_peak_rss_bytes=peak,samples=samples,compute_wall_s=actual,greedy_autoregressive_gate=(len(greedy)==expected_greedy and all(g['byte_identical'] and g['token_identical'] and g['complete_output'] for g in greedy)) if MODE=='full' else False,greedy_cases=len(greedy),greedy_expected_cases=expected_greedy,pinned_version_replay_collected=len(replay)==7,replay_dir=str(replay_out),pinned_version_replay_auxiliary_q36_equality_gate=False,auxiliary_q36_original_missing=True)
if complete:
 eager=[r for r in rows if r['kind']=='toolcall-eager' and r['profile']=='real' and r['arm'].startswith('llguidance')]
 record['toolcall_eager_numeric_component_gate']=all(r['grammar_delta_ms_per_token']<2 and r['grammar_share_pct']<5 for r in eager)
 record['numeric_gate_rule']='lower_better; each native toolcall-eager real T0.3/0.8 B1/B5 grammar delta<2ms AND share<5%; 24.86ms historical denominator fixed; no original parent completion'
if IS_FIXTURE: record.update(first_request=first_request,production_recipe_sha256=qual_manifest['production_recipe']['sha256'],threads=24,n_ctx=4096,observed_cpus=sorted(os.sched_getaffinity(0)))
write('RESULT.json',record)
if IS_QUAL:
 writer={'ok':True,'result_path':str(OUT/'RESULT.json'),'sha256':sha(OUT/'RESULT.json')}
 proof={'id':qual_manifest['id'],'nonce':os.environ['WS58_QUAL_NONCE'],'phase':QUAL_PHASE,'observed_cpus':sorted(os.sched_getaffinity(0)),'first_request':first_request,'result_writer':writer,'disk':{'job_floor_gib':150}}
 if QUAL_PHASE=='cutoff': proof.update(partial=True,stop_observed=stop_path.exists(),unknown_disposition='UNKNOWN')
 write_path(os.environ['WS58_QUAL_PROOF'],proof)
if IS_CAL:
 per_unit=actual/2.0 if actual>0 else None
 calibration={'kind':'epyc.raw.r11.calibration.v1','not_qualification':True,'id':qual_manifest['id'],'ran_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'work_unit':'native-real-logit-cost-cell','observed_work_units':2,'observed_wall_s_per_unit':per_unit,'production_threads':24,'production_recipe_sha256':qual_manifest['production_recipe']['sha256'],'observed_cpu_affinity':sorted(os.sched_getaffinity(0)),'model_path':pins['model']['path'],'model_size':pins['model']['size'],'model_edge_sha256':pins['model']['edge_sha256'],'n_ctx':4096,'n_parallel':1,'raw_component_result_sha256':sha(OUT/'RESULT.json'),'fixture_scope':'two actual real-logit cost cells at T=.3/.8, B1, one actual model prompt each; R11 2-CPU affinity; conservative wall-time bound, no quarter-speed extrapolation','current_actual_step_share':'UNMEASURED'}
 write_path(OUT/'R11-CALIBRATION.json',calibration)
print(json.dumps(record),flush=True)
sys.exit(0 if complete else (75 if partial else 1))
