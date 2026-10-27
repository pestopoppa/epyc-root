#!/usr/bin/env python3
"""Grant-owned v10 CPU scratch-server job; never used in preflight."""
import datetime,hashlib,json,os,signal,subprocess,time,urllib.request
from pathlib import Path
from verdict_check import validate_verdict
B=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ufh14-lb51-template')
K=Path('/mnt/raid0/llm/kernels/production/cpu').resolve(strict=True)
MODEL=Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
TEMPLATE=Path('/mnt/raid0/llm/models/chat-templates/sha256/1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551.jinja')
DEADLINE=int(os.environ['FILLER_DEADLINE']); STOP=Path(os.environ['FILLER_STOPFILE'])
children=[]
passed=False
failure=None
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
def artifact_hashes():
 return {name:hashlib.sha256((B/name).read_bytes()).hexdigest() for name in ('result.json','server-identity.json','maps.txt','linkage.log','server.log','audit.log') if (B/name).is_file()}
def base_record():
 return {'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_manifest_sha256':hashlib.sha256((B/'SOURCE.SHA256SUMS').read_bytes()).hexdigest(), 'roles':['architect_critic','coder_escalation','ingest_long_context'], 'request':{'endpoint':'/apply-template','enable_thinking':False,'original_fixtures':True}, 'model_sha256':'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348', 'template_sha256':'1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551','artifacts':artifact_hashes()}
def stop_signal(*_): raise RuntimeError('termination requested')
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP): signal.signal(sig,stop_signal)
def check():
 if time.time() >= DEADLINE or STOP.exists() or list(Path('/mnt/raid0/llm/tmp/compute-flags').glob('HOLD_*')): raise RuntimeError('stop, hold or deadline')
 rss=0
 for p in children:
  if p.poll() is None:
   try:
    rss+=int(next(x.split()[1] for x in Path(f'/proc/{p.pid}/status').read_text().splitlines() if x.startswith('VmRSS:')))
   except (FileNotFoundError,StopIteration): pass
 if rss>50*1024*1024: raise RuntimeError('aggregate RSS exceeds 50 GiB')
def wait(p,limit):
 end=min(time.time()+limit,DEADLINE)
 while p.poll() is None:
  check()
  if time.time()>end: raise RuntimeError('child timeout')
  time.sleep(.5)
 return p.returncode
def spawn(argv,**kw):
 p=subprocess.Popen(argv,**kw);children.append(p);return p
try:
 check(); env={'PATH':'/usr/bin:/bin','HOME':str(B),'TMPDIR':str(B),'LD_LIBRARY_PATH':str(K),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
 with (B/'linkage.log').open('wb') as f:
  p=spawn(['/bin/bash',str(B/'verify_ggml_linkage.sh'),str(K/'llama-server'),str(K)],stdout=f,stderr=subprocess.STDOUT,env=env)
  if wait(p,30)!=0: raise RuntimeError('ggml linkage verification failed')
 with (B/'model.sha256').open('w') as f:
  p=spawn(['/usr/bin/sha256sum',str(MODEL)],stdout=f,env=env)
  if wait(p,250)!=0: raise RuntimeError('model hash failed')
 if (B/'model.sha256').read_text().split()[0]!='a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348': raise RuntimeError('model digest mismatch')
 if hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()!='1443ea9ab4bb0a2663b1002a5d4baad970e9f0b2f42ca4ec12b4683838284551': raise RuntimeError('template digest mismatch')
 with (B/'server.log').open('wb') as log:
  p=spawn([str(K/'llama-server'),'-m',str(MODEL),'--host','127.0.0.1','--port','18994','-ngl','0','-t','24','-c','2048','--jinja','--chat-template-file',str(TEMPLATE)],stdout=log,stderr=subprocess.STDOUT,env=env)
  affinity=sorted(os.sched_getaffinity(p.pid))
  if affinity != list(range(24,48)): raise RuntimeError(f'unexpected server affinity {affinity}')
  (B/'server-identity.json').write_text(json.dumps({'pid':p.pid,'start_ticks':Path(f'/proc/{p.pid}/stat').read_text().rsplit(')',1)[1].split()[19],'argv':p.args,'affinity':affinity,'ld_library_path':env['LD_LIBRARY_PATH']})+'\n')
  end=min(time.time()+300,DEADLINE)
  while True:
   check()
   if p.poll() is not None: raise RuntimeError('server exited during startup')
   if time.time()>end: raise RuntimeError('server readiness timeout')
   try:
    with urllib.request.urlopen('http://127.0.0.1:18994/health',timeout=2) as resp: healthy=resp.status==200
    ss=subprocess.check_output(['ss','-ltnp','sport = :18994'],text=True)
    if healthy and f'pid={p.pid},' in ss: break
   except (OSError,ValueError): pass
   time.sleep(1)
  maps=Path(f'/proc/{p.pid}/maps').read_text(); (B/'maps.txt').write_text(maps)
  if Path(f'/proc/{p.pid}/exe').resolve(strict=True) != (K/'llama-server').resolve(strict=True): raise RuntimeError('server executable differs from sealed binary')
  mapped={line.split()[-1] for line in maps.splitlines() if '/' in line and ('libggml' in line or 'libllama' in line)}
  if not mapped or any(not x.startswith(str(K)+'/') for x in mapped) or not any('libggml-cpu' in x for x in mapped): raise RuntimeError(f'unexpected mapped libraries: {mapped}')
  sealed={str(Path(name).resolve()):digest for digest,name in (line.split('  ',1) for line in (B/'SOURCE.SHA256SUMS').read_text().splitlines())}
  for lib in mapped:
   if lib not in sealed or hashlib.sha256(Path(lib).read_bytes()).hexdigest()!=sealed[lib]: raise RuntimeError(f'unsealed or changed mapped library: {lib}')
   if not any(line.split()[-1] == lib and int(line.split()[4]) == Path(lib).stat().st_ino for line in maps.splitlines() if len(line.split()) >= 6): raise RuntimeError(f'mapped inode differs: {lib}')
  if not any(line.split()[-1] == str(MODEL) and int(line.split()[4]) == MODEL.stat().st_ino for line in maps.splitlines() if len(line.split()) >= 6):
   raise RuntimeError('model file and inode absent from live server mappings')
  with (B/'audit.log').open('wb') as out:
   a=spawn(['/usr/bin/python3','-B',str(B/'live_audit.py'),'http://127.0.0.1:18994',str(TEMPLATE),str(B/'result.json')],stdout=out,stderr=subprocess.STDOUT,env=env)
   if wait(a,300)!=0: raise RuntimeError('audit failed or divergence; see result and audit.log')
  result=json.loads((B/'result.json').read_text())
  if not validate_verdict(result.get('verdict')): raise RuntimeError('prefix verdict missing or failed')
  passed=True
except BaseException as exc:
 failure=exc
finally:
 for p in reversed(children):
  if p.poll() is None:
   p.terminate()
   try: p.wait(timeout=10)
   except subprocess.TimeoutExpired: p.kill();p.wait(timeout=5)
  if p.poll() is None: raise RuntimeError('owned child not drained')

if failure is not None:
 record=base_record();record.update({'status':'incomplete','error_type':type(failure).__name__,'error':str(failure)})
 (B/'ERROR.json').write_text(json.dumps(record,indent=2)+'\n')
 raise failure
if passed:
 receipt=base_record()
 receipt.update({'status':'complete','result':'result.json','scope':'27B terse, thinking=false; other models untested', 'fixture_sha256':{name:digest for name,digest in sealed.items() if '/fixtures/' in name}, 'kernel_binary_sha256':sealed[str((K/'llama-server').resolve())], 'mapped_library_sha256':{name:sealed[name] for name in sorted(mapped)}})
 (B/'CANDIDATE.json').write_text(json.dumps(receipt,indent=2)+'\n')
