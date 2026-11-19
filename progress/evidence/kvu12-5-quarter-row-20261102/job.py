#!/usr/bin/env python3
"""KVU-12.5 quarter successor, control and target producer under keeper custody."""
from __future__ import annotations
import hashlib,json,os,pathlib,signal,statistics,subprocess,sys,time
from commands import command
from reducer import reduce_pair
from sampler import Monitor
D=pathlib.Path(__file__).resolve().parent
MODEL=pathlib.Path('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf')
MODEL_SHA='c1283d8b80c3e38b2735ddbc9766d3b3126f44d6c484be419d4e101d09a76131'
CORPUS_SHA='476c08ab215e9c852159124ce2c17c574c3efeb304b6f66a3f2cfb72abdf657b'
SAMPLER='/mnt/raid0/llm/tmp/kvu12-redo-20261021/gpu_sampler.py'

def mode(env):
 raw=env.get('FILLER_DRYRUN')
 if raw not in ('0','1'):raise ValueError('explicit FILLER_DRYRUN=0|1 required')
 return 'control' if raw=='1' else 'target'

def check_claim(env):
 if env.get('FILLER_CPUS') not in ('72-95','72-95,168-191'):raise ValueError('q3 CPU grant required')
 if env.get('FILLER_THREADS')!='24' or env.get('FILLER_NEEDGPU')!='0':raise ValueError('CPU quarter with 24 physical threads required')
 stop=env.get('FILLER_STOPFILE');deadline=env.get('FILLER_DEADLINE')
 if not stop or not deadline:raise ValueError('stop and deadline required')
 if pathlib.Path(stop).exists() or int(deadline)<=int(time.time()):raise ValueError('stop/deadline reached')

def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while True:
   b=f.read(8*1024*1024)
   if not b:break
   h.update(b)
   check_claim(os.environ)
 return h.hexdigest()

def append_native(path,record):
 if record.get('mode') not in ('control','target') or record.get('native_record_complete') is not True:raise ValueError('only completed native records')
 path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('a') as f:f.write(json.dumps(record,allow_nan=False,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno())

def child_wait(p):
 while p.poll() is None:
  try:check_claim(os.environ)
  except Exception:
   p.terminate()
   try:p.wait(timeout=45)
   except subprocess.TimeoutExpired:p.kill();p.wait(timeout=10)
   raise
  time.sleep(1)
 return p.returncode

def row_valid(row):
 if not isinstance(row,dict) or row.get('schema')!='epyc.vidya.np_ctx_kvu_capture.v1':return False
 actual=hashlib.sha256(json.dumps({k:v for k,v in row.items() if k!='row_sha256'},sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
 return row.get('row_sha256')==actual and row.get('kv_unified_from_log') in ('true','false') and all(row.get(k) not in (None,'') for k in ('binary_sha256','binary_realpath','n_ctx_slot','c','np','prompt_mode','ts','cpu_list','loadavg_start'))

def observe_server(root):
 files=list(root.rglob('server.pid'))
 if not files:return None
 if len(files)!=1:raise RuntimeError('ambiguous server PID custody')
 try:
  pid=int(files[0].read_text().strip());proc=pathlib.Path('/proc',str(pid))
  target=os.path.realpath(proc/'exe')
  if target!=os.path.realpath('/mnt/raid0/llm/kernels/production/cpu/llama-server'):return None
  birth=(proc/'stat').read_text().rpartition(') ')[2].split()[19]
  allowed=set(range(72,96))|set(range(168,192));thread_masks=[];thread_affinities={}
  for task in (proc/'task').iterdir():
   if not task.name.isdigit():continue
   try:mask=set(os.sched_getaffinity(int(task.name)))
   except ProcessLookupError:continue
   if not mask or not mask<=allowed:raise RuntimeError('server worker thread CPU placement mismatch')
   thread_masks.append(mask)
   thread_affinities[task.name]=sorted(mask)
  union=set().union(*thread_masks) if thread_masks else set()
  if {x%96 for x in union}!=set(range(72,96)):raise RuntimeError('server CPU placement lacks full quarter')
  return {'pid':pid,'birth':birth,'physical_cpu_union':sorted({x%96 for x in union}),'threads_sampled':len(thread_masks),'thread_affinities':thread_affinities}
 except (ProcessLookupError,FileNotFoundError):return None

def captured_dead(root, observations):
 files=list(root.rglob('server.pid'))
 if len(files)!=1 or len(observations)<2:return False
 try:pid=int(files[0].read_text().strip())
 except (ValueError,OSError):return False
 identities={(x['pid'],x['birth']) for x in observations}
 if len(identities)!=1 or next(iter(identities))[0]!=pid:return False
 try:birth=pathlib.Path('/proc',str(pid),'stat').read_text().rpartition(') ')[2].split()[19]
 except FileNotFoundError:return True
 return birth!=next(iter(identities))[1]

def validate_waves(out,row,cell,waves,clients,depth):
 paths=list(out.glob('*/'+cell+'/waves.json'))
 captures=list(out.glob('*/'+cell+'/waves_capture.jsonl'))
 if len(paths)!=1 or len(captures)!=1:raise RuntimeError('native wave artifacts missing or ambiguous')
 raw=json.loads(paths[0].read_text())
 captured=[json.loads(x) for x in captures[0].read_text().splitlines() if x.strip()]
 if len(raw)!=waves or len(captured)!=waves or any(not row_valid(x) for x in captured):raise RuntimeError('native wave capture invalid')
 for i,(c,w) in enumerate(zip(captured,raw)):
  if w.get('wave')!=i or w.get('n_ok')!=clients or w.get('n_err')!=0 or w.get('errors'):raise RuntimeError('native wave requests failed')
  if c['wave']!=w['wave'] or any(c[k]!=w[k] for k in ('decode_tps_sum','decode_tps_per_stream','ttft_s')):raise RuntimeError('native wave data mismatch')
  if len(w['decode_tps_per_stream'])!=clients or len(w['ttft_s'])!=clients:raise RuntimeError('native wave stream count mismatch')
 vals=raw[1:] if depth else raw
 derived={'decode_tps_sum_med':statistics.median(w['decode_tps_sum'] for w in vals),'decode_tps_stream_med':statistics.median(v for w in vals for v in w['decode_tps_per_stream']),'ttft_s_med':statistics.median(raw[0]['ttft_s'] if depth else [v for w in raw for v in w['ttft_s']])}
 if any(abs(row[k]-v)>.0051 for k,v in derived.items()):raise RuntimeError('summary does not match native wave values')
 return raw

def execute(m,arm,out,ledger=None):
 out.mkdir(parents=True,exist_ok=False);check_claim(os.environ)
 if not pathlib.Path('/sys/class/kfd/kfd/proc').is_dir():raise RuntimeError('KFD process observation unavailable')
 cmd=command(m,arm,out,ledger)+['--corpus-roots',str(D/'corpus')]
 gpu=out/'gpu_state.jsonl';log=out/'driver.log'
 with log.open('wb') as lf:
  sampler=Monitor(gpu,observer=lambda:observe_server(out))
  driver=None
  try:
   sampler.start()
   started=time.monotonic_ns()
   driver=subprocess.Popen(cmd,stdout=lf,stderr=subprocess.STDOUT,env={**os.environ,'LD_LIBRARY_PATH':'/mnt/raid0/llm/kernels/production/cpu'})
   rc=child_wait(driver);ended=time.monotonic_ns()
  finally:
   if driver is not None and driver.poll() is None:
    driver.terminate()
    try:driver.wait(timeout=45)
    except subprocess.TimeoutExpired:driver.kill();driver.wait(timeout=10)
   sampler.close()
 observations=[x['server'] for x in sampler.samples if x.get('server')]
 if rc!=0 or not captured_dead(out,observations):raise RuntimeError('driver failed or captured server not proven gone')
 rows=[json.loads(x) for x in (out/'summary.jsonl').read_text().splitlines() if x.strip()]
 if len(rows)!=1 or rows[0].get('result')!='OK' or rows[0].get('validation_problems'):raise RuntimeError('invalid native summary')
 gp=sampler.samples
 if not sampler.quiet(started,ended):raise RuntimeError('GPU quiet observation invalid or unbracketed')
 if 'corpus sha256='+CORPUS_SHA not in log.read_text(errors='replace'):raise RuntimeError('native corpus hash mismatch')
 row=rows[0]
 if row.get('threads')!=24 or row.get('cpu_list')!='72-95,168-191' or row.get('binary_sha256')!='4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c':raise RuntimeError('native cpu or binary identity mismatch')
 if not row_valid(row):raise RuntimeError('native capture invalid')
 if arm=='control':cell,nw,clients,depth='8k_independent',1,1,False
 elif arm=='anchor':cell,nw,clients,depth='t8short_independent',3,8,False
 else:cell,nw,clients,depth='64k_depth',4,8,True
 if row.get('clients')!=clients:raise RuntimeError('native client count mismatch')
 raw=validate_waves(out,row,cell,nw,clients,depth)
 return row,gp,raw

def main():
 m=mode(os.environ)
 if m=='control':
  from smoke import run
  run();return
 check_claim(os.environ)
 grant_dir=pathlib.Path(os.environ.get('FILLER_GRANTS_DIR','/mnt/raid0/llm/tmp/compute-flags/grants'))
 grant=grant_dir/(os.environ.get('FILLER_ID','')+'.grant')
 if not grant.is_file():raise RuntimeError('active grant missing')
 grant_sha=digest(grant)
 provenance={'grant_sha256':grant_sha,'mode':m,'cpu_list':os.environ['FILLER_CPUS'],'threads':24,'end':os.environ.get('FILLER_END'),'model_sha256':MODEL_SHA,'corpus_sha256':CORPUS_SHA}
 from smoke import verify_model
 if verify_model(MODEL)!=MODEL_SHA or digest(D/'corpus/corpus.md')!=CORPUS_SHA:raise RuntimeError('model/corpus pin mismatch')
 out=D/('qualification' if m=='control' else 'run')
 if out.exists():raise RuntimeError('output already exists; do not redraw or reuse attempts')
 out.mkdir(mode=0o700)
 event=D/'events.jsonl'
 if m=='control':
  row,g,_=execute(m,'control',out/'control')
  append_native(event,{'mode':m,'native_record_complete':True,'summary':str(out/'control/summary.jsonl'),'model_sha256':MODEL_SHA,'corpus_sha256':CORPUS_SHA,'provenance':provenance})
  (out/'QUALIFICATION.json').write_text(json.dumps({'state':'complete','mode':m,'model_sha256':MODEL_SHA,'samples':len(g)})+'\n');return
 ledger=out/'aba_ledger.jsonl'
 anchors=[]
 def anchor(label):
  row,_,_=execute(m,'anchor',out/label);anchors.append(row)
  append_native(event,{'mode':m,'arm':label,'native_record_complete':True,'summary':str(out/label/'summary.jsonl'),'provenance':provenance})
 anchor('anchor-start')
 u,ug,uw=execute(m,'unified',out/'unified',str(ledger));append_native(event,{'mode':m,'arm':'unified','native_record_complete':True,'summary':str(out/'unified/summary.jsonl'),'provenance':provenance})
 anchor('anchor-mid')
 s,sg,sw=execute(m,'split',out/'split',str(ledger));append_native(event,{'mode':m,'arm':'split','native_record_complete':True,'summary':str(out/'split/summary.jsonl'),'provenance':provenance})
 anchor('anchor-end')
 if u.get('clients')!=8 or s.get('clients')!=8 or u.get('min_headroom_tok',-1)<0 or s.get('min_headroom_tok',-1)<0:raise RuntimeError('client or context headroom invalid')
 if u.get('kv_unified_from_log')!='true' or s.get('kv_unified_from_log')!='false':raise RuntimeError('KV mode not confirmed')
 lines=[json.loads(x) for x in ledger.read_text().splitlines() if x.strip()]
 if len(lines)!=2 or lines[0]['norm_argv']!=lines[1]['norm_argv']:raise RuntimeError('paired normalized argv mismatch')
 q={x:True for x in ('same_binary','same_model','same_source','same_argv','gpu_idle_both','quarter_bound_both','both_complete','no_errors','same_clients','cleanup_verified','warrant_captured')}
 verdict=reduce_pair(u,s,uw,sw,q,anchors)
 if verdict['verdict']=='INVALID':raise RuntimeError('predeclared result INVALID: '+verdict['reason'])
 (out/'VERDICT.json').write_text(json.dumps(verdict,indent=2)+'\n')
 append_native(event,{'mode':m,'arm':'verdict','native_record_complete':True,'verdict':verdict['verdict'],'provenance':provenance})
 (out/'COMPLETE.json').write_text(json.dumps({'state':'complete','verdict':verdict['verdict'],'provenance':provenance})+'\n')
if __name__=='__main__':main()
