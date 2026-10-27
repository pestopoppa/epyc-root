#!/usr/bin/env python3
"""Owner-granted /chat live proof. Missing attribution is inconclusive."""
import hashlib, json, os, re, subprocess, sys, threading, time, urllib.request, uuid
from datetime import datetime, timezone
from pathlib import Path
D=Path(__file__).resolve().parent; x=json.loads(Path(sys.argv[1]).read_text()); flags=Path('/mnt/raid0/llm/tmp/compute-flags'); grant=flags/'grants/rte-log-chat-live.grant'
logs=Path('/mnt/raid0/llm/epyc-orchestrator/logs'); paths=[logs/'serving_calls/serving_calls.jsonl',logs/'dispatch/dispatch.jsonl']
def birth(pid): return Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def get(path,body=None):
 req=urllib.request.Request('http://127.0.0.1:8000'+path, data=None if body is None else json.dumps(body).encode(), headers={'Content-Type':'application/json','Connection':'close'})
 with urllib.request.urlopen(req,timeout=3 if body is None else 180) as r: return r.status,r.read()
def check(reserve=300):
 if (D/'STOP').exists() or list(flags.glob('HOLD_*')): raise RuntimeError('stop/hold')
 m=re.fullmatch(r'regions=0-95 start=(\d{4}-\d\d-\d\dT\d\d:\d\dZ) end=(\d{4}-\d\d-\d\dT\d\d:\d\dZ)\n?',grant.read_text())
 if not m: raise RuntimeError('missing whole-host grant')
 matching=[line.split('|') for line in (flags/'FILLERS.md').read_text().splitlines() if line.startswith('| rte-log-chat-live |')]
 if len(matching)!=1 or float(matching[0][6].strip())!=float(x['reservation_gib']): raise RuntimeError('owner reservation differs from canonical row')
 start,end=[datetime.strptime(s,'%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc).timestamp() for s in m.groups()]
 if not start<=time.time()<end-reserve or int(end)!=int(os.environ['FILLER_END']): raise RuntimeError('grant expired or insufficient deadline reserve')
 if sha(x['budget_evidence'])!=x['budget_evidence_sha256']: raise RuntimeError('budget evidence changed')
 if subprocess.run(['git','-C',x['source_tree'],'merge-base','--is-ancestor','b67f1581f6f9f4e4e63cdff2e7d1927f38dcb5fa',x['source_commit']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode: raise RuntimeError('source lacks bridge')
 if subprocess.check_output(['git','-C',x['source_tree'],'rev-parse','HEAD'],text=True).strip()!=x['source_commit']: raise RuntimeError('source tree identity mismatch')
 rel=[str(Path(p).relative_to(x['source_tree'])) for p in x['source_files']]
 if subprocess.run(['git','-C',x['source_tree'],'diff','--quiet','HEAD','--',*rel]).returncode: raise RuntimeError('source files differ from committed identity')
 for path,digest in x['source_files'].items():
  if sha(path)!=digest: raise RuntimeError('source file changed')
 for pid,b in x['births'].items():
  if birth(pid)!=b or os.readlink(f'/proc/{pid}/exe')!=x['executables'][pid]: raise RuntimeError('process replaced')
 for model in x['models']:
  if Path(model['path']).stat().st_size!=model['size']: raise RuntimeError('model changed')
 rss=0; mapped=set(); declared=set(map(int,x['resident_processes']))
 for pid in declared:
  status=Path(f'/proc/{pid}/status').read_text(); match=re.search(r'^VmRSS:\s+(\d+)\s+kB$',status,re.M)
  if not match: raise RuntimeError('missing RSS')
  rss+=int(match.group(1))*1024
  for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
   path=line.split(maxsplit=5)[-1]
   if path.endswith('.gguf'): mapped.add(str(Path(path).resolve()))
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit(): continue
  try:
   pid=int(proc.name); name=(proc/'cmdline').read_bytes().split(b'\0')[0].decode(errors='replace'); status=(proc/'status').read_text(); parent=re.search(r'^PPid:\s+(\d+)',status,re.M)
   if (Path(name).name in ('llama-server','whisper-server','qwen-tts-server') or (parent and int(parent.group(1)) in declared)) and pid not in declared: raise RuntimeError('unaccounted serving process')
  except (FileNotFoundError,ProcessLookupError): continue
  except PermissionError: raise RuntimeError('process inventory unreadable')
 models={m['path'] for m in x['models']}
 if not mapped.issubset(models): raise RuntimeError('unaccounted weights')
 total=rss+sum(m['size'] for m in x['models'])+int(x['future_kv_state_gib']*1024**3)+4*1024**3
 if total>x['reservation_gib']*1024**3: raise RuntimeError('owner reservation insufficient')
 for pid in x['api_workers']:
  boot=int(next(line.split()[1] for line in Path('/proc/stat').read_text().splitlines() if line.startswith('btime ')))
  started=boot+int(x['births'][str(pid)])/os.sysconf('SC_CLK_TCK')
  if any(Path(path).stat().st_mtime>started for path in x['source_files']): raise RuntimeError('source file newer than API worker')
  env=dict(z.decode(errors='replace').split('=',1) for z in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if b'=' in z)
  if env.get('ORCHESTRATOR_REQUEST_SOURCE','').strip().lower()!='benchmark': raise RuntimeError('owner-controlled benchmark source missing')
  if any(env.get(k,'').lower() not in ('1','true','yes','on') for k in ('ORCHESTRATOR_PER_REGION_LOCKS','ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT')): raise RuntimeError('native lock flags absent')
  if env.get('ORCHESTRATOR_PROMPT_LAYOUT_LOG','').lower() in ('off','0','false','none','disabled'): raise RuntimeError('layout disabled')
 return {'grant':grant.read_text(),'accounted_bytes':total,'time':time.time()}
check(); out=D/'out'; out.mkdir(exist_ok=False); health={}
for i in range(32):
 try:
  _,raw=get('/health/serving-calls'); r=json.loads(raw); health[r['pid']]=r
 except Exception: pass
 if set(map(int,x['api_workers'])).issubset(health): break
for pid in x['api_workers']:
 r=health.get(int(pid),{}); p=r.get('provenance',{})
 if p.get('pid')!=int(pid) or p.get('orch_commit')!=x['source_commit']: raise SystemExit('worker health identity mismatch')
snap=check(); files=[p.open('rb') for p in paths]; identities=[os.fstat(f.fileno()).st_ino for f in files]
(out/'pre-request.json').write_text(json.dumps({'binding':x,'health':health,'admission':snap},sort_keys=True,indent=2)+'\n')
for f in files: f.seek(0,2)
offsets=[f.tell() for f in files]; session='rte_'+uuid.uuid4().hex
deadline=time.time()+120
if deadline>int(os.environ['FILLER_END'])-120: raise SystemExit('insufficient server deadline reserve')
body={'prompt':'What is 2 plus 2? Reply briefly.','context':'','mock_mode':False,'real_mode':True,'force_mode':'direct','role':'frontdoor','max_turns':1,'max_tokens':64,'request_id':session,'timeout_s':120,'client_deadline_unix_s':deadline}
stop=threading.Event(); samples=[]
def sample():
 while not stop.is_set():
  try:
   entries=json.loads(Path('/mnt/raid0/llm/tmp/cpu_region.occupancy.json').read_text())['entries']; locks=Path('/proc/locks').read_text().splitlines()
   for e in entries:
    pid=e.get('pid'); role=e.get('role'); regions=e.get('regions',[])
    if pid not in x['api_workers'] or e.get('shared') or not regions: continue
    owned=[]
    for region in regions:
     fs=[Path(f'/mnt/raid0/llm/tmp/cpu_region.{role}.{region}.lock'),Path(f'/mnt/raid0/llm/tmp/cpu_region.GLOBAL.{region}.lock')]
     def held(f):
      from paircheck import holds_inode
      st=f.stat()
      return any(holds_inode(line,pid,st.st_dev,st.st_ino) for line in locks)
     if all(held(f) for f in fs): owned.append(region)
    if set(owned)==set(regions): samples.append({'time':time.time(),'entry':e,'owned':owned})
  except (OSError,ValueError,KeyError,TypeError): pass
  stop.wait(.05)
t=threading.Thread(target=sample); t.start(); started=time.time()
try: status,_=get('/chat',body)
finally: stop.set(); t.join()
ended=time.time()
(out/'request-observation.json').write_text(json.dumps({'session':session,'start':started,'end':ended,'status':status,'lock_samples':samples},sort_keys=True,indent=2)+'\n')
check(30)
if status!=200: raise SystemExit('request failed')
for _ in range(20):
 time.sleep(.5)
 if all(p.stat().st_size>offset for p,offset in zip(paths,offsets)): break
for p,inode in zip(paths,identities):
 if p.stat().st_ino!=inode: raise SystemExit('log rotation')
if sum(p.stat().st_size-o for p,o in zip(paths,offsets))>256*1024*1024: raise SystemExit('INCONCLUSIVE: log window exceeds output budget')
rows=[]
for f,off in zip(files,offsets):
 f.seek(off); rows.append([json.loads(line) for line in f if line.strip()])
for name,rs in [('raw-serving.jsonl',rows[0]),('raw-dispatch.jsonl',rows[1])]: (out/name).write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rs))
from paircheck import validate
try: serving,dispatch=validate(rows[0],rows[1],session,x['api_workers'],x['backend_port'],samples)
except ValueError as exc: raise SystemExit('INCONCLUSIVE: '+str(exc))
(out/'snapshot.json').write_text(json.dumps({'binding':x,'health':health,'admission':snap,'session':session,'start':started,'end':ended,'lock_samples':samples},sort_keys=True,indent=2)+'\n')
for name,rs in [('serving.jsonl',serving),('dispatch.jsonl',dispatch)]: (out/name).write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rs))
checker=Path(x['source_tree'])/'scripts/analysis/prompt_layout_live_check.py'
result=subprocess.run([sys.executable,str(checker),'--json',str(out/'serving.jsonl'),str(out/'dispatch.jsonl')],capture_output=True,text=True)
(out/'checker.json').write_text(result.stdout); (out/'checker.stderr').write_text(result.stderr)
if result.returncode: raise SystemExit('INCONCLUSIVE: native checker')
(out/'COMPLETE').write_text('paired live layout proof; no cache-reuse or quality verdict\n')
