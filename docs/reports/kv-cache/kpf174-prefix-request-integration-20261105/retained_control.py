#!/usr/bin/env python3
"""Prospective KPF17.4d five-cell layout diagnostic. Never regrades historical data."""
import argparse, hashlib, importlib.util, json, math, os, shutil, signal, sys, time
from pathlib import Path
from types import SimpleNamespace
from layout_witness import parse, witness, compare, Invalid
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('prior', '/mnt/raid0/llm/tmp/cal-1026/kpf174d-c1-layout-source/run.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
b,k=prior.b,prior.k
BIN=Path('/mnt/raid0/llm/tmp/kvfork/kpf174d-prospective/bin/llama-server')
ARGV=Path('/mnt/raid0/llm/worktrees/research-kpf174c-pin/scripts/benchmark/kpf13/argv.gpu-27b-dflash2.txt')
OUT=Path('/mnt/raid0/llm/tmp/kvfork/kpf174d-prospective/out')
PORT=18443
LIMIT=2*1024**3
CONFIG='kpf174d_131b_prospective'
k.CONFIGS[CONFIG]={'label':CONFIG,'mutate':None,'extra':[],'arms':('A','B'),'knob':[b'--slot-fork-min-tokens',b'LLAMA_KPF_LAYOUT_TRACE',b'LLAMA_KPF_ITEM4_TRACE'],'plain_only':False,'spec_off':True}
b.LAUNCH=CONFIG;b.CONFIG_NAME=CONFIG

class TraceServer(k.Server):
 def build_env(self):
  env,note=super().build_env();env.update({'LLAMA_KPF_LAYOUT_TRACE':'1','LLAMA_KPF_ITEM4_TRACE':'1','GGML_CUDA_DISABLE_GRAPHS':'1','HSA_OVERRIDE_CPU_AFFINITY_DEBUG':'0'})
  note['set'].update({x:env[x] for x in ('LLAMA_KPF_LAYOUT_TRACE','LLAMA_KPF_ITEM4_TRACE','GGML_CUDA_DISABLE_GRAPHS','HSA_OVERRIDE_CPU_AFFINITY_DEBUG')});return env,note

def atomic(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
 with tmp.open('w') as f:f.write(json.dumps(obj,indent=2,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)
 fd=os.open(path.parent,os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)

def digest_json(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def resume_binding(expected,proof,model,smoke):
 # Read the pinned files themselves: a manifest name alone is not source identity.
 manifest=D/'SOURCES.sha256'
 for line in manifest.read_text().splitlines():
  digest,name=line.split(None,1)
  if hashlib.sha256(Path(name.strip()).read_bytes()).hexdigest()!=digest:
   raise k.Abort('source pin mismatch: '+name)
 return {'schema':'kpf174d-cell-binding/v1','binary_sha256':expected,
         'build_proof':digest_json(proof),'sources_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
         'inputs_sha256':hashlib.sha256((D/'exact-inputs.json').read_bytes()).hexdigest(),
         'argv_sha256':hashlib.sha256(ARGV.read_bytes()).hexdigest(),'model':model,'smoke':smoke}

def cell_verdict(runs,smoke):
 if smoke:
  if [r.get('role') for r in runs]!=['fork1','control1']:raise k.Abort('bad smoke repetitions')
  for run in runs:
   response=run.get('response') or {}; probs=response.get('probs') or []
   if len(response.get('tokens') or [])!=64 or len(probs)!=64: return {'verdict':'INVALID','why':'token/logprob shape'}
   try:
    for entry in probs: validated_top2(entry)
   except (ValueError,TypeError,IndexError,KeyError,AttributeError,OverflowError): return {'verdict':'INVALID','why':'invalid top2'}
   if len(run.get('during_vram_samples') or [])<2: return {'verdict':'INVALID','why':'missing during-request residency'}
  layout=compare(runs[0]['witness'],runs[1]['witness'])
  return {'verdict':'SMOKE_ONLY','layout':layout} if layout['verdict']=='MATCHED' else {'verdict':'INVALID_LAYOUT','layout':layout}
 if [r.get('role') for r in runs]!=['fork1','control1','fork2','control2','control3']:
  return {'verdict':'INVALID','why':'repeat identity or order'}
 return judge(runs)

def accepted(verdict,smoke):
 return verdict.get('verdict')==('SMOKE_ONLY' if smoke else 'PROSPECTIVE_ONLY')

def reuse_cell(previous,cid,binding,smoke):
 if previous.get('cell')!=cid or previous.get('binding')!=binding:raise k.Abort('existing cell provenance mismatch')
 runs=previous['runs']
 if previous.get('runs_sha256')!=digest_json(runs):raise k.Abort('existing cell output digest mismatch')
 for run in runs:
  trace=Path(run['trace'])
  if trace.resolve().parent!=(OUT/'traces').resolve() or hashlib.sha256(trace.read_bytes()).hexdigest()!=run['trace_sha256']:
   raise k.Abort('existing cell trace mismatch')
 verdict=cell_verdict(runs,smoke)
 if verdict!=previous.get('verdict') or not accepted(verdict,smoke):raise k.Abort('existing cell invalid verdict')
 return verdict

def completion_allowed(status,smoke):
 return (not smoke and status.get('rc')==0 and status.get('partial') is False
         and bool(status.get('cells')) and all(accepted(v,False) for v in status['cells'].values()))

def require_qualification(proof,smoke):
 if not smoke and (proof.get('ready') is not True or proof.get('qualification')!='PASS'):
  raise SystemExit('REFUSED prospective job is not qualified')

def prepared_model_identity(model):
 # Model content verification is preparation work, never grant-time weight I/O.
 identity=json.loads((D/'MODEL-IDENTITY.json').read_text())
 digest=identity.get('sha256','')
 if (identity.get('schema')!='kpf174d-model-identity/v1' or identity.get('path')!=str(model)
     or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest)
     or not identity.get('evidence')):
  raise k.Abort('invalid prepared model identity')
 st=model.stat()
 actual={key:getattr(st,'st_'+key) for key in ('dev','ino','size','mtime_ns','ctime_ns')}
 if identity.get('stat')!=actual:raise k.Abort('prepared model metadata changed; reverify outside grant')
 return identity

def selected_slice(raw,slot):
 batches=parse(raw)
 candidates=[]
 for batch in batches:
  for row in batch['rows']:
   if row[0]==slot and row[4]=='prefill':candidates.append(row[1])
 tasks=set(candidates)
 if len(tasks)!=1:raise Invalid('request does not bind one native task to target slot')
 task=next(iter(tasks))
 if any(row[0]!=slot or row[1]!=task for batch in batches for row in batch['rows']):raise Invalid('request interval includes foreign task or slot')
 return task

class Runner(b.Runner):
 def start(self):
  super().start()
  pid=self.srv.proc.pid
  env=k.read_proc_env(pid)
  if env.get('LLAMA_KPF_LAYOUT_TRACE')!='1' or env.get('LLAMA_KPF_ITEM4_TRACE')!='1':raise k.Abort('native trace env mismatch')
  if self.srv.readback.get('runtime_threads_unpinned_count')!=0:raise k.Abort('escaped CPU affinity')
  maps=Path(f'/proc/{pid}/maps').read_text()
  if not any(str(BIN.parent) in ln and 'libggml-hip.so' in ln for ln in maps.splitlines()):raise k.Abort('native HIP mapping absent')
 def _vram_loop(self):
  pid=self.srv.proc.pid
  with open(self.vram_file,'a') as fh:
   while not self._vstop.wait(1.) and k.pid_alive(pid):
    value=k.kfd_pids().get(pid,0);fh.write(f'{time.time():.3f} {value}\n');fh.flush()
    if value>60*1024**3:self.guard_trip='own VRAM >60 GiB';os.kill(pid,signal.SIGTERM);return
    size=sum(x.stat().st_size for sub in ('logs','traces') for x in (OUT/sub).rglob('*') if x.is_file())
    if size>LIMIT:self.guard_trip='trace output >2 GiB';os.kill(pid,signal.SIGTERM);return
 def request(self, role, ids, slot, fork, n, cell, ckpt=None):
  self.ctx.check_boundary()
  if (OUT/'logs').exists() and sum(x.stat().st_size for x in (OUT/'logs').rglob('*') if x.is_file())>LIMIT:raise k.Abort('trace output limit')
  log=self.srv.log;start=log.stat().st_size
  body=k.body_for(ids,n,slot,fork=fork,cache=True,ckpt=ckpt)
  sent=time.time()
  r=self.ctx.client.complete(body,timeout=max(1,min(120,self.ctx.deadline.remaining()-5)))
  ended=time.time()
  # The pump writes asynchronously. Quiet sampling allows it to flush; strict parser rejects truncation.
  old=-1
  for _ in range(20):
   size=log.stat().st_size
   if size==old:break
   old=size;time.sleep(.1)
  with log.open('rb') as f:f.seek(start);raw=f.read()
  trace=OUT/'traces'/f'{cell}-{role}.log';trace.parent.mkdir(parents=True,exist_ok=True);trace.write_bytes(raw)
  result={'role':role,'request':body,'response':r,'trace':str(trace),'trace_sha256':hashlib.sha256(raw).hexdigest()}
  journal=OUT/'requests.jsonl'
  with journal.open('a') as fh:fh.write(json.dumps(result,sort_keys=True)+'\n');fh.flush();os.fsync(fh.fileno())
  if r.get('http')!=200 or r.get('error'):raise k.Abort(f'{role} HTTP failure')
  if n:
   samples=[]
   for line in self.vram_file.read_text().splitlines():
    try:
     t,v=line.split();t=float(t);v=int(v)
    except (ValueError,TypeError):continue
    if sent<=t<=ended and v>0:samples.append([t,v])
   result['request_window']=[sent,ended];result['during_vram_samples']=samples
   if len(samples)<2:raise k.Abort('fewer than two own-process VRAM samples during request')
   task=selected_slice(raw,slot);result['task']=task;result['witness']=witness(raw,task,slot,2048 if cell.endswith('-A') else 1984)
  return result
 def trial(self,cell,arm,i,kind):
  self.erase_all();t=cell['trunk_ids'];p=t+cell['suffix_ids'];c=cell['fork_tokens'];cid=f"g{cell['group']}-S{cell['suffix_tokens']}-{arm}"
  if kind=='fork':
   self.request(f'{kind}{i}-seed0',t[:1984],0,False,0,cid,[-1])
   if arm=='A':
    r=self.request(f'{kind}{i}-seed3',t,3,True,0,cid,[-1]);tim=r['response'].get('timings') or {}
    if tim.get('n_fork_tokens')!=1984:raise k.Abort('source3 one-hop mismatch')
   result=self.request(f'{kind}{i}',p,1,True,64,cid)
   tim=result['response'].get('timings') or {};expected_source=3 if arm=='A' else 0
   if tim.get('n_fork_tokens')!=c or tim.get('fork_src_slot')!=expected_source:raise k.Abort('fork source or length mismatch')
  else:
   self.request(f'{kind}{i}-seed2a',t[:1984],2,False,0,cid,[-1])
   if arm=='A':self.request(f'{kind}{i}-seed2b',t,2,False,0,cid,[-1])
   result=self.request(f'{kind}{i}',p,2,False,64,cid)
   tim=result['response'].get('timings') or {}
   if int(tim.get('n_fork_tokens') or 0)!=0 or tim.get('cache_n')!=c:raise k.Abort('control cache partition mismatch')
  if getattr(self,'guard_trip',None):raise k.Abort(self.guard_trip)
  if not self.vram_sample():raise k.Abort('no own KFD residency during request')
  return result

def validated_top2(entry):
 # Validate every native rank: inherited top2_kind only inspects the first rank
 # of the first token, and top2 also accepts probability-valued records.
 top=entry.get('top_logprobs')
 if not isinstance(top,list) or len(top)<2:raise ValueError('incomplete native logprobs')
 result=[]
 for item in top[:2]:
  token=item['id'];value=item['logprob']
  if type(token) is not int or token<0 or isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
   raise ValueError('invalid native logprob')
  result.append([token,value])
 if result[0][0]==result[1][0] or result[0][1]<result[1][1]:raise ValueError('invalid top2 ordering or identity')
 return result

def judge(runs):
 refs=[r for r in runs if r['role'].startswith('control')]; xs=[r for r in runs if r['role'].startswith('fork')]
 if len(refs)!=3 or len(xs)!=2:return {'verdict':'INVALID','why':'repeat count'}
 for r in runs:
  resp=r['response'];probs=resp.get('probs') or []
  if len(resp.get('tokens') or [])!=64 or len(probs)!=64:return {'verdict':'INVALID','why':'token/logprob shape'}
 comps=[compare(x['witness'],y['witness']) for x in xs for y in refs]
 if any(c['verdict']!='MATCHED' for c in comps):return {'verdict':'INVALID_LAYOUT','layout_comparisons':comps}
 tokens=[r['response']['tokens'] for r in refs]
 if len({tuple(t) for t in tokens})!=1 or xs[0]['response']['tokens']!=xs[1]['response']['tokens']:return {'verdict':'INVALID','why':'unstable repetitions'}
 try:
  all_tops=[[validated_top2(p) for p in r['response']['probs']] for r in runs]
  if any(len(v)!=2 or any(len(z)!=2 or not math.isfinite(z[1]) for z in v) for row in all_tops for v in row):
   return {'verdict':'INVALID','why':'non-finite or incomplete top2'}
  tops=[[validated_top2(p) for p in r['response']['probs']] for r in refs]
  if any([v[0] for v in a[i]]!=[v[0] for v in z[i]] for a in tops for z in tops for i in range(64)):
   return {'verdict':'INVALID','why':'unstable control top2 identities'}
  floor=max(abs(a[i][j][1]-z[i][j][1]) for a in tops for z in tops for i in range(64) for j in range(2))
 except (ValueError,TypeError,IndexError,KeyError,AttributeError,OverflowError):return {'verdict':'INVALID','why':'invalid top2'}
 outcomes=[]
 for x in xs:
  xt=x['response']['tokens'];d=next((i for i,(u,v) in enumerate(zip(xt,tokens[0])) if u!=v),None)
  if d is None:outcomes.append({'verdict':'MATCHED_TOKENS'})
  else:
   margin=abs(tops[0][d][0][1]-tops[0][d][1][1]);outcomes.append({'verdict':'RESIDUAL' if margin>max(.031567,floor) else 'UNDETERMINED_NEAR_TIE','divergence_zero_based':d,'margin':margin})
 return {'verdict':'PROSPECTIVE_ONLY','results':outcomes,'aa_floor':floor,'layout_comparisons':comps}

def main():
 global OUT
 p=argparse.ArgumentParser();p.add_argument('--job',action='store_true');p.add_argument('--smoke',action='store_true');args=p.parse_args()
 if args.job or not args.smoke:raise SystemExit('only the declared one-cell smoke is available')
 proof=json.loads((D/'BUILD-PROOF.json').read_text())
 require_qualification(proof,args.smoke)
 end=int(os.environ['FILLER_DEADLINE']);cpus=os.environ['FILLER_CPUS']
 if not cpus or not os.environ.get('FILLER_THREADS'):raise SystemExit('REFUSED missing keeper CPU assignment')
 if os.environ.get('FILLER_DRYRUN'):OUT=Path(os.environ['FILLER_DRYRUN_DIR'])/'probe'
 if time.time()>=end-120:return 75
 if not (D/'BINARY.sha256').is_file():raise SystemExit('REFUSED missing post-build binary pin')
 expected=(D/'BINARY.sha256').read_text().split()[0]
 if hashlib.sha256(BIN.read_bytes()).hexdigest()!=expected:raise SystemExit('REFUSED binary pin')
 if proof.get('binary_sha256')!=expected or proof.get('parent_source')!='84d0a31603d495377dee24e1159bbbf02f1e2f21' or proof.get('linkage_pass') is not True:raise SystemExit('REFUSED unverified build proof')
 for name,digest in proof.get('libraries',{}).items():
  file=BIN.parent/name
  if '/' in name or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise SystemExit('REFUSED library pin')
 if not all(name in proof.get('libraries',{}) for name in ('libllama-common.so','libllama-server-impl.so','libggml-hip.so','libllama.so')):raise SystemExit('REFUSED incomplete library proof')
 for marker in (b'LLAMA_KPF_LAYOUT_TRACE',b'LLAMA_KPF_ITEM4_TRACE',b'--slot-fork-min-tokens'):
  if not k.bytes_contain_any_lib(BIN,marker):raise SystemExit('REFUSED missing compiled knob')
 for path in (D,Path('/mnt/micron')):
  if shutil.disk_usage(path).free < 152*1024**3:raise SystemExit('REFUSED free-space reserve')
 model=Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
 model_identity=prepared_model_identity(model)
 argv,_=k.load_argv_file(ARGV)
 if args.smoke:
  argv=k.set_flag(argv,('-t','--threads'),os.environ['FILLER_THREADS']);argv=k.set_flag(argv,('-tb','--threads-batch'),os.environ['FILLER_THREADS'])
 a=SimpleNamespace(out=str(OUT),fork_bin=str(BIN),cpu_list=cpus,numa_membind=3,device='gpu',threads=int(os.environ['FILLER_THREADS']),port=PORT,fork_min=1024,draft_debug=False,load_timeout_s=600,card=str(k.DEFAULT_CARD),vram_free_max_gib=2.,vram_drain_timeout_s=120.,vram_drain_poll_s=2.,prefill_tok_s=25.,decode_tok_s=24.,load_s=150.,stop_file=os.environ['FILLER_STOPFILE'],window_id=os.environ['FILLER_ID'])
 ctx=k.Ctx(a,None,argv,k.Deadline(end-120));ctx.start_utc=k.now_iso();k.Server=TraceServer
 class Own(list):
  def append(self,server):
   super().append(server)
   with open(os.environ['FILLER_PIDFILE'],'a') as f:f.write(str(server.proc.pid)+'\n');f.flush()
 ctx.own_children=Own()
 original_boundary=ctx.check_boundary
 def boundary():
  if Path(os.environ['FILLER_STOPFILE']).exists():raise k.Abort('stop requested')
  original_boundary()
 ctx.check_boundary=boundary
 runner=Runner(ctx,{},None,{})
 OUT.mkdir(parents=True,exist_ok=True);data=json.loads((D/'exact-inputs.json').read_text())
 cutoff={'tripped':False}
 def interrupt(signum,frame):
  cutoff['tripped']=True
  raise k.Abort(f'cutoff signal {signum}')
 signal.signal(signal.SIGALRM,interrupt);signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
 signal.alarm(max(1,int(end-120-time.time())))
 status={'schema':'kpf174d-prospective/v1','historical_verdict_unchanged':True,'smoke':args.smoke,'binary_sha256':expected,'model':model_identity,'partial':True,'cells':{}}
 binding=resume_binding(expected,proof,status['model'],args.smoke)
 status['binding']=binding
 # A new attempt must never inherit a stale successful sentinel.
 (D/'COMPLETE').unlink(missing_ok=True)
 rc=0
 try:
  atomic(OUT/'STATE.json',status);runner.start()
  for cell in (data['cells'][:1] if args.smoke else data['cells']):
   if time.time()>=end-(160 if args.smoke else 420) or Path(os.environ['FILLER_STOPFILE']).exists():rc=75;break
   arm=cell['original_failed_arm'];cid=f"g{cell['group']}-S{cell['suffix_tokens']}-{arm}"
   claim=OUT/'cells'/f'{cid}.started';claim.parent.mkdir(parents=True,exist_ok=True)
   complete=OUT/'cells'/f'{cid}.json'
   if complete.exists():
    previous=json.loads(complete.read_text())
    status['cells'][cid]=reuse_cell(previous,cid,binding,args.smoke);continue
   try:
    with claim.open('x') as f:f.write(k.now_iso()+'\n')
   except FileExistsError:status['cells'][cid]={'verdict':'UNKNOWN_ALREADY_EXPOSED'};rc=78;break
   runs=[]
   for kind,i in ([('fork',1),('control',1)] if args.smoke else [('fork',1),('control',1),('fork',2),('control',2),('control',3)]):
    ctx.check_boundary();runs.append(runner.trial(cell,arm,i,kind))
   verdict=cell_verdict(runs,args.smoke)
   status['cells'][cid]=verdict
   atomic(complete,{'cell':cid,'binding':binding,'runs':runs,'runs_sha256':digest_json(runs),'verdict':verdict})
   atomic(OUT/'STATE.json',status)
   if not accepted(verdict,args.smoke):raise k.Abort('invalid prospective cell: '+verdict['verdict'])
  else:status['partial']=False
 except Exception as exc:
  status['error']=f'{type(exc).__name__}: {exc}';rc=75 if cutoff['tripped'] or ctx.deadline.expired() or Path(os.environ['FILLER_STOPFILE']).exists() else 1
 finally:
  try:runner.stop()
  finally:
   signal.alarm(0);status['cleanup']=getattr(runner.srv,'stop_rec',None)
   if runner.srv and not (status['cleanup'] or {}).get('verified_dead'):rc=1
   status['rc']=rc;atomic(OUT/'STATE.json',status)
   if rc==0 and not status['partial'] and len(status['cells'])==1 and all(accepted(v,True) for v in status['cells'].values()):
    atomic(Path(os.environ.get('FILLER_DRYRUN_RESULT_PATH',str(OUT/'RESULT.json'))),status)
   if completion_allowed(status,args.smoke):
    atomic(D/'COMPLETE',{'result':str(OUT/'RESULT.json'),'historical_verdict_unchanged':True})
 return rc
if __name__=='__main__':sys.exit(main())
