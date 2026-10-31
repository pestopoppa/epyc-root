#!/usr/bin/env python3
"""Original KPF18.3 item-3 disjoint attribution cases; smoke uses public controls."""
import hashlib,json,os,signal,subprocess,sys,time,urllib.request
from pathlib import Path
D=Path('/mnt/raid0/llm/tmp/codex3-kpf183-chat-full-20261031')
B=Path('/mnt/raid0/llm/tmp/codex3-kpf183-chat-impl-20261031')
C=Path('/mnt/raid0/llm/tmp/codex3-kpf183-e332-build-r2-20261030')
FORK=Path('/mnt/micron/codex3-lanes/kpf183-chat-build/bin/llama-server')
CHAMP=Path('/mnt/micron/codex3-lanes/kpf-e332-build/bin/llama-server')
SMALL=Path('/mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf')
FULL=Path('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf')
if sys.argv[1:] not in (['smoke'],['full']):raise SystemExit('mode required')
smoke=sys.argv[1]=='smoke';model=SMALL if smoke else FULL
out=D/('smoke-final' if smoke else 'run');out.mkdir(exist_ok=True)
if smoke and any(out.iterdir()):raise RuntimeError('smoke output exists; preserve and use new attempt')
stop=False
def handler(sig,frame):
 global stop
 stop=True
 raise InterruptedError('signal '+str(sig))
signal.signal(signal.SIGTERM,handler);signal.signal(signal.SIGINT,handler)
def check():
 if stop or Path(os.environ['FILLER_STOPFILE']).exists() or time.time()>=float(os.environ['FILLER_DEADLINE']):raise InterruptedError('STOP or deadline')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()
def syncdir(p):
 fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def write(name,obj):
 tmp=out/(name+'.tmp')
 with tmp.open('w') as f:json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,out/name);syncdir(out)
def pending(obj):
 p=out/'pending.json'
 with p.open('x') as f:json.dump(obj,f);f.write('\n');f.flush();os.fsync(f.fileno())
 syncdir(out)
def unpending():
 (out/'pending.json').unlink();syncdir(out)
def call(path,body=None):
 data=None if body is None else json.dumps(body).encode()
 req=urllib.request.Request('http://127.0.0.1:19584'+path,data=data,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=120) as r:return {'status':r.status,'body':json.load(r)}
def req(path,body):
 try:return {'ok':True,**call(path,body)}
 except (InterruptedError,KeyboardInterrupt):raise
 except Exception as e:return {'ok':False,'error':repr(e)}
def responses(rec):
 def shape(r):
  c=r['body']['choices'][0]
  return {'message':c['message'],'finish_reason':c.get('finish_reason'),'ids':[p['id'] for p in c.get('logprobs',{}).get('content',[])]}
 return shape(rec['first']),shape(rec['second'])
def checkpoints(slots):
 return [[{k:c[k] for k in ('n_tokens','pos_min','pos_max','pinned')} for c in s.get('checkpoints',[])] for s in slots]
try:
 if not (B/'BUILD-SUCCESS').exists() or not (C/'BUILD-SUCCESS').exists():raise RuntimeError('both builds required')
 if sha(B/'BUILD-DIGESTS.txt')!='e7aeb3936c63064ccb1a67dafc5b20e1067e616eb9d97bd6662f3cd31004b2c8' or sha(C/'BUILD-DIGESTS.txt')!='2663270480b493df3e6f7e9e4d326f1b1b0216a1bbe11ff4fdd365ac4c5762ca':raise RuntimeError('build digest catalog changed')
 for d in (B,C):subprocess.run(['sha256sum','--strict','--quiet','-c',str(d/'BUILD-DIGESTS.txt')],check=True)
 if b'KPF183_TRACE' not in (FORK.parent/'libllama-server-impl.so').read_bytes():raise RuntimeError('trace absent')
 if smoke:
  if model.stat().st_size!=811843840 or sha(model)!='0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c':raise RuntimeError('control model changed')
  cases=json.loads((D/'PUBLIC-CONTROLS.json').read_text())['cases']
 else:
  with model.open('rb') as f:
   n=os.fstat(f.fileno()).st_size;a=hashlib.sha256(f.read(64*1024**2)).hexdigest();f.seek(n-64*1024**2);b=hashlib.sha256(f.read()).hexdigest()
  if (n,a,b)!=(37801097504,'3711c69305b6d77a3a8bc69abff096cda9f90238887f29ce3e83ec5f3cd348eb','d90af8cf5c5047a758c11a6fd64f4902708f55cb96bee73201814f4755954bfa'):raise RuntimeError('full model identity changed')
  if sha(D/'PREDECLARED.json')!='0ab013c8c7057ed2987589e98cf47295e01e4c16dd784f966e92be84c24f3f89':raise RuntimeError('predeclaration changed')
  cases=json.loads((D/'PREDECLARED.json').read_text())['cases']
 if (out/'pending.json').exists():raise RuntimeError('unknown prior exposure: pending retained; no redraw')
 if not smoke and (out/'RESULT.json').exists():raise SystemExit(0)
 records=json.loads((out/'records.json').read_text()) if (out/'records.json').exists() else []
 arms=[('champion',CHAMP,None,0),('fork-off',FORK,0,1),('fork-on',FORK,1,1)]
 if smoke:arms.append(('trace-off',FORK,1,0))
 invocation=str(time.time_ns());trace_events={}
 for arm,bin,minimum,trace in arms:
  if all(any(r['arm']==arm and r['case']['id']==c['id'] for r in records) for c in cases):continue
  check();threads='2' if smoke else '24'
  argv=[str(bin),'-m',str(model),'--host','127.0.0.1','--port','19584','-t',threads,'-tb',threads,'--slots','--no-warmup','-np','4','-c','4096','-b','512','-ub','512','--kv-unified','--ctx-checkpoints','8','--no-cache-idle-slots']
  if minimum is not None:argv+=['--slot-fork-min-tokens',str(minimum)]
  env=dict(os.environ,LD_LIBRARY_PATH=str(bin.parent),OMP_NUM_THREADS='1',KPF183_TRACE=str(trace))
  path=out/(invocation+'-'+arm+'.server.log')
  with path.open('x') as log:
   p=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,env=env)
   try:
    for _ in range(600):
     check()
     if p.poll() is not None:raise RuntimeError('server exited before ready')
     try:
      if call('/health')['body'].get('status')=='ok' and ('pid='+str(p.pid)+',') in subprocess.run(['ss','-ltnp','sport = :19584'],capture_output=True,text=True,check=True).stdout:break
     except (OSError,ValueError):pass
     time.sleep(.5)
    else:raise RuntimeError('server health timeout')
    for case in cases:
     check()
     if any(r['arm']==arm and r['case']['id']==case['id'] for r in records):continue
     pending({'arm':arm,'case':case['id'],'state':'exposure may occur; do not redraw'})
     base={'model':'local','temperature':0,'max_tokens':32,'cache_prompt':True,'logprobs':True,'top_logprobs':5,'chat_template_kwargs':{'enable_thinking':False},'id_slot':0,'checkpoint_at':[-1]}
     msg=[{'role':'user','content':case['turn1']}]
     first=req('/v1/chat/completions',dict(base,messages=msg,cache_prompt=False))
     r={'arm':arm,'case':case,'argv':argv,'binary_sha256':sha(bin),'model':str(model),'trace':trace,'server_log':str(path),'first':first,'status':'incomplete'}
     if first['ok']:
      response=first['body']['choices'][0]['message'];r['first_assistant_message']=response;r['slots_first']=call('/slots')['body']
      if response.get('content') and not response.get('reasoning_content'):
       check()
       r['resent_assistant_message']=dict(response)
       r['second']=req('/v1/chat/completions',dict(base,messages=msg+[r['resent_assistant_message'],{'role':'user','content':case['turn2']}]))
       if r['second']['ok']:r['slots_second']=call('/slots')['body'];r['status']='complete'
      else:r['unknown_reason']='empty content or nonempty reasoning_content; no continuation or redraw'
     else:r['unknown_reason']='first request failed; no continuation or redraw'
     records.append(r);write('records.json',records);unpending()
   finally:
    if p.poll() is None:
     p.terminate()
     try:p.wait(timeout=10)
     except subprocess.TimeoutExpired:p.kill();p.wait(timeout=10)
    log.flush();os.fsync(log.fileno())
    if p.poll() is None:raise RuntimeError('server survived')
  events=[]
  for line in path.read_text(errors='replace').splitlines():
   if 'KPF183_TRACE ' in line:events.append(json.loads(line.split('KPF183_TRACE ',1)[1]))
  trace_events[arm]=events
  write(invocation+'-'+arm+'.trace.json',events)
 # Join actual retained trace lines to each request using response task ID, or
 # its immediate slot snapshot when that response omits the ID (e.g. fork-off).
 for r in records:
  capture={}
  for label,slotkey in (('first','slots_first'),('second','slots_second')):
   if label not in r or not r[label].get('ok'):
    capture[label]={'status':'unknown','reason':'request not successfully recorded'};continue
   tid=r[label]['body'].get('timings',{}).get('id_task')
   if tid is None:
    slots=r.get(slotkey,[])
    matches=[x for x in slots if x.get('id')==0]
    tid=matches[0].get('id_task') if len(matches)==1 else None
   if not r['trace'] or tid is None:
    capture[label]={'status':'unknown','reason':'trace disabled or task ID not exposed','task_id':tid};continue
   path=Path(r['server_log']);events=[]
   for line in path.read_text(errors='replace').splitlines():
    if 'KPF183_TRACE ' in line:
     e=json.loads(line.split('KPF183_TRACE ',1)[1])
     if e.get('task_id')==tid:events.append(e)
   spans=[e for e in events if e.get('event')=='spans']
   decisions=[e for e in events if e.get('event')=='checkpoint_decision']
   capture[label]={'status':'observed' if len(spans)==1 and decisions else 'unknown','task_id':tid,'spans_events':spans,'checkpoint_decisions':decisions}
  r['trace_capture']=capture
 write('records.json',records)
 if smoke:
  if any(r['status']!='complete' for r in records):raise RuntimeError('control continuation incomplete')
  for c in cases:
   off=next(r for r in records if r['arm']=='trace-off' and r['case']['id']==c['id']);on=next(r for r in records if r['arm']=='fork-on' and r['case']['id']==c['id'])
   if responses(off)!=responses(on):raise RuntimeError('trace response mismatch')
   if any(checkpoints(off[k])!=checkpoints(on[k]) for k in ('slots_first','slots_second')):raise RuntimeError('trace checkpoint mismatch')
  if trace_events.get('trace-off'):raise RuntimeError('trace unexpectedly emitted while off')
  for r in records:
   if r['arm'] in ('fork-on','fork-off') and any(r['trace_capture'][k]['status']!='observed' for k in ('first','second')):raise RuntimeError('missing per-request native trace')
  on=trace_events.get('fork-on',[])
  if not any(e.get('event')=='spans' and e.get('input_message_delimiters_present') is True and e.get('spans') for e in on):raise RuntimeError('missing runtime spans')
  if not any(e.get('event')=='checkpoint_decision' and e.get('is_user_start') and 'n_tokens_cur' in e and 'after' in e for e in on):raise RuntimeError('missing user-start trace')
 write('RESULT.json',{'complete':True,'smoke':smoke,'records':records,'unavailable_count':sum(r['status']!='complete' for r in records),'unknown_trace_requests':sum(r['trace_capture'][k]['status']!='observed' for r in records if r['arm'] in ('fork-on','fork-off') for k in ('first','second')),'scope':'diagnostic counts; no quality or performance claim'})
except InterruptedError as e:
 write('PARTIAL.json',{'partial':True,'reason':str(e),'pending_exposure_unknown':(out/'pending.json').exists()});raise SystemExit(75)
except Exception as e:
 write('ERROR.json',{'complete':False,'error':repr(e),'pending_exposure_unknown':(out/'pending.json').exists()});raise
