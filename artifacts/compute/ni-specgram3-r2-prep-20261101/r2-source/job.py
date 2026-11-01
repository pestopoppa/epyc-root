import os,sys,pathlib,time,subprocess,json,hashlib,signal,datetime
S=pathlib.Path(__file__).resolve().parent
MODE=sys.argv[1]; OUT=S/('qualification-'+MODE if MODE!='full' else 'out'); OUT.mkdir(exist_ok=True)
def write(name,obj):
 p=OUT/name;t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(obj,indent=2)+'\n');t.replace(p)
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
cpus=os.environ['FILLER_CPUS'];threads='1' if MODE!='full' else os.environ['FILLER_THREADS']
stop_path=pathlib.Path(os.environ.get('FILLER_STOPFILE',str(OUT/'STOP' if MODE=='cutoff' else S/'STOP')))
end=float(os.environ.get('FILLER_DEADLINE',str(time.time()+285))); stop=False;captured={};peak=0;samples=0;children=[]
def sig(signum,frame):
 global stop
 stop=True
signal.signal(signal.SIGTERM,sig);signal.signal(signal.SIGINT,sig)
write('BEGIN.json',dict(mode=MODE,pins_sha=sha(S/'PINS.json'),cpus=cpus,threads=threads,deadline=end,started=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),model= pins['model'],scope='combined native teacher-forced component + independent autoregressive greedy +1.0.1 forced-token/trim replay; missing auxiliary q36 tokenizer equality remains explicit; no adoption'))
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
plans=[('component',.3)] if MODE!='full' else [('component',.3),('component',.8)]
plans += [('greedy',0),('replay',0),('tokenizer',0)]
replay_out=OUT/('replay-'+str(int(time.time())))
for phase,T in plans:
 if stop_path.exists() or stop or time.time()>=end-5:reason='active-cutoff-before-next-phase';break
 cmd=[str(S/'bench-specgram3'),'--model',str(model),'--logits-model',str(model),'--threads',threads,'--label','frontdoor-t'+str(T),'--grammar-file',str(S/'toolcall.gbnf'),'--schema-file',str(S/'toolcall.schema.json'),'--llguidance-file',str(S/'toolcall.lark'),'--paired','--profiles','real' if MODE!='full' else 'real,peaked','--batches','1' if MODE!='full' else '1,5','--kinds','toolcall-eager' if MODE!='full' else 'toolcall-eager,toolcall-lazy,schema-eager','--reps','1' if MODE!='full' else '30','--temp',str(T),'--step-ms','24.86','--out',str(OUT/'results.jsonl'),'--max-seconds',str(max(1,end-time.time()-7))]
 if MODE!='full':cmd+=['--max-scripts','1']
 if phase=='greedy':
  cmd=[str(S/'bench-specgram3'),'--model',str(model),'--logits-model',str(model),'--threads',threads,'--grammar-file',str(S/'toolcall.gbnf'),'--schema-file',str(S/'toolcall.schema.json'),'--llguidance-file',str(S/'toolcall.lark'),'--greedy-out',str(OUT/'greedy.jsonl'),'--greedy-cap','4' if MODE!='full' else '256']
  if MODE!='full':cmd+=['--kinds','toolcall-eager','--max-scripts','1']
 if phase=='replay':cmd=['/mnt/raid0/llm/tmp/specgram2-offline/v/bin/python','-I','-B',str(S/'replay101.py'),'1' if MODE!='full' else '5450']
 if phase=='tokenizer':cmd=['/mnt/raid0/llm/tmp/specgram2-offline/v/bin/python','-I','-B',str(S/'tokenizer_audit.py')]
 label=phase+'-t'+str(T)
 env=os.environ.copy();env['SPECGRAM3_REPLAY_OUT']=str(replay_out);env.update(LD_LIBRARY_PATH='/mnt/raid0/llm/kernels/production/cpu',OMP_NUM_THREADS='1',HIP_VISIBLE_DEVICES='',ROCR_VISIBLE_DEVICES='')
 with (OUT/('native-'+label+'.log')).open('a') as log:
  p=subprocess.Popen(['taskset','-c',cpus,*cmd],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);children.append(p.pid);born=time.time()
  write('COMMAND-'+label+'.json',dict(argv=cmd,env={k:env[k] for k in ['LD_LIBRARY_PATH','OMP_NUM_THREADS','HIP_VISIBLE_DEVICES','ROCR_VISIBLE_DEVICES']},pid=p.pid))
  while p.poll() is None:
   rss=sample(p.pid)
   try:
    maps=pathlib.Path('/proc',str(p.pid),'maps').read_text()
    if 'libggml-cpu.so' in maps:(OUT/('mapped-'+label+'.txt')).write_text(maps)
   except OSError:pass
   if MODE=='cutoff' and time.time()-born>2:stop_path.touch()
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
expected=48 if MODE=='full' else 2
greedy=[json.loads(l) for l in (OUT/'greedy.jsonl').read_text().splitlines()] if (OUT/'greedy.jsonl').exists() else []
replay_file=replay_out/('results_'+('1' if MODE!='full' else '5450')+'.json')
replay=json.loads(replay_file.read_text()) if replay_file.exists() else {}
expected_greedy=8 if MODE=='full' else 1
if any(not r['valid'] for r in rows):reason='invalid-script-token'
if replay_file.exists() and len(replay)!=7:reason='invalid-replay-cell-matrix'
complete=not reason and len(rows)==expected and all(r['valid'] for r in rows) and len(greedy)==expected_greedy and len(replay)==7
partial=not complete and (reason is None or 'cutoff' in reason)
record=dict(mode=MODE,partial=partial,reason=reason,complete=complete,rows=len(rows),expected_rows=expected,first_request_ok=bool(rows),result_writer_ok=True,exit_ok=complete,captured_pids=captured,live_after=live,sampled_peak_rss_bytes=peak,samples=samples,compute_wall_s=actual,greedy_autoregressive_gate=(len(greedy)==expected_greedy and all(g['byte_identical'] and g['token_identical'] and g['complete_output'] for g in greedy)) if MODE=='full' else False,greedy_cases=len(greedy),greedy_expected_cases=expected_greedy,pinned_version_replay_collected=len(replay)==7,replay_dir=str(replay_out),pinned_version_replay_auxiliary_q36_equality_gate=False,auxiliary_q36_original_missing=True)
if complete:
 eager=[r for r in rows if r['kind']=='toolcall-eager' and r['profile']=='real' and r['arm'].startswith('llguidance')]
 record['toolcall_eager_numeric_component_gate']=all(r['grammar_delta_ms_per_token']<2 and r['grammar_share_pct']<5 for r in eager)
 record['numeric_gate_rule']='lower_better; each native toolcall-eager real T0.3/0.8 B1/B5 grammar delta<2ms AND share<5%; 24.86ms historical denominator fixed; no original parent completion'
write('RESULT.json',record)
print(json.dumps(record),flush=True)
sys.exit(0 if complete else (75 if partial else 1))
