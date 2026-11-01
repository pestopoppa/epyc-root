#!/usr/bin/env python3
"""KVU-12.5 quarter successor, control and target producer under keeper custody."""
from __future__ import annotations
import hashlib,json,os,pathlib,signal,subprocess,sys,time
from commands import command
from reducer import reduce_pair
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

def captured_dead(root):
 # Driver writes only the server pid that it captured. A reused pid is UNKNOWN, not dead.
 for f in root.rglob('server.pid'):
  try:pid=int(f.read_text().strip())
  except (ValueError,OSError):return False
  if pathlib.Path('/proc',str(pid)).exists():return False
 return True

def execute(m,arm,out,ledger=None):
 out.mkdir(parents=True,exist_ok=False);check_claim(os.environ)
 if not pathlib.Path('/sys/class/kfd/kfd/proc').is_dir():raise RuntimeError('KFD process observation unavailable')
 cmd=command(m,arm,out,ledger)+['--corpus-roots',str(D/'corpus')]
 gpu=out/'gpu_state.jsonl';log=out/'driver.log'
 with (out/'sampler.log').open('wb') as slog,log.open('wb') as lf:
  sampler=subprocess.Popen(['/usr/bin/python3','-I','-B',SAMPLER,str(gpu),str(os.getpid())],stdout=slog,stderr=subprocess.STDOUT)
  driver=None
  try:
   deadline=time.monotonic()+15
   while (not gpu.exists() or not gpu.stat().st_size) and time.monotonic()<deadline:
    if sampler.poll() is not None:raise RuntimeError('sampler failed before launch')
    time.sleep(.1)
   if not gpu.exists() or not gpu.stat().st_size:raise RuntimeError('sampler did not start')
   started=time.time()
   driver=subprocess.Popen(cmd,stdout=lf,stderr=subprocess.STDOUT,env={**os.environ,'LD_LIBRARY_PATH':'/mnt/raid0/llm/kernels/production/cpu'})
   rc=child_wait(driver);ended=time.time()
   time.sleep(1.2)  # sample beyond the end of the driver's observation window
  finally:
   if driver is not None and driver.poll() is None:
    driver.terminate()
    try:driver.wait(timeout=45)
    except subprocess.TimeoutExpired:driver.kill();driver.wait(timeout=10)
   sampler.terminate()
   try:sampler.wait(timeout=5)
   except subprocess.TimeoutExpired:sampler.kill();sampler.wait(timeout=5)
 if rc!=0 or not captured_dead(out):raise RuntimeError('driver failed or captured server not proven gone')
 rows=[json.loads(x) for x in (out/'summary.jsonl').read_text().splitlines() if x.strip()]
 if len(rows)!=1 or rows[0].get('result')!='OK' or rows[0].get('validation_problems'):raise RuntimeError('invalid native summary')
 gp=[json.loads(x) for x in gpu.read_text().splitlines() if x.strip()]
 if len(gp)<2 or gp[0].get('ts',float('inf'))>started or gp[-1].get('ts',0)<ended or any(r.get('busy_pct') is None or r['busy_pct']>=5 or r.get('foreign_kfd_pids')!=0 for r in gp):raise RuntimeError('GPU quiet observation invalid or unbracketed')
 if 'corpus sha256='+CORPUS_SHA not in log.read_text(errors='replace'):raise RuntimeError('native corpus hash mismatch')
 row=rows[0]
 if row.get('threads')!=24 or row.get('cpu_list')!='72-95,168-191' or row.get('binary_sha256')!='4483bcfc92c5c3bb0005df31e1c668cb565d49f7b40ba94f4df5a126cbbb648c':raise RuntimeError('native cpu or binary identity mismatch')
 if row.get('schema')!='epyc.vidya.np_ctx_kvu_capture.v1' or not row.get('row_sha256'):raise RuntimeError('native capture missing')
 return row,gp

def main():
 m=mode(os.environ);check_claim(os.environ)
 grant_dir=pathlib.Path(os.environ.get('FILLER_GRANTS_DIR','/mnt/raid0/llm/tmp/compute-flags/grants'))
 grant=grant_dir/(os.environ.get('FILLER_ID','')+'.grant')
 if not grant.is_file():raise RuntimeError('active grant missing')
 grant_sha=digest(grant)
 provenance={'grant_sha256':grant_sha,'mode':m,'cpu_list':os.environ['FILLER_CPUS'],'threads':24,'end':os.environ.get('FILLER_END'),'model_sha256':MODEL_SHA,'corpus_sha256':CORPUS_SHA}
 if digest(MODEL)!=MODEL_SHA or digest(D/'corpus/corpus.md')!=CORPUS_SHA:raise RuntimeError('model/corpus pin mismatch')
 out=D/('qualification' if m=='control' else 'run')
 if out.exists():raise RuntimeError('output already exists; do not redraw or reuse attempts')
 out.mkdir(mode=0o700)
 event=D/'events.jsonl'
 if m=='control':
  row,g=execute(m,'control',out/'control')
  append_native(event,{'mode':m,'native_record_complete':True,'summary':str(out/'control/summary.jsonl'),'model_sha256':MODEL_SHA,'corpus_sha256':CORPUS_SHA,'provenance':provenance})
  (out/'QUALIFICATION.json').write_text(json.dumps({'state':'complete','mode':m,'model_sha256':MODEL_SHA,'samples':len(g)})+'\n');return
 ledger=out/'aba_ledger.jsonl'
 u,ug=execute(m,'unified',out/'unified',str(ledger));append_native(event,{'mode':m,'arm':'unified','native_record_complete':True,'summary':str(out/'unified/summary.jsonl'),'provenance':provenance})
 s,sg=execute(m,'split',out/'split',str(ledger));append_native(event,{'mode':m,'arm':'split','native_record_complete':True,'summary':str(out/'split/summary.jsonl'),'provenance':provenance})
 if u.get('clients')!=8 or s.get('clients')!=8 or u.get('min_headroom_tok',-1)<0 or s.get('min_headroom_tok',-1)<0:raise RuntimeError('client or context headroom invalid')
 if u.get('kv_unified_from_log')!='true' or s.get('kv_unified_from_log')!='false':raise RuntimeError('KV mode not confirmed')
 for arm in ('unified','split'):
  captures=list((out/arm).glob('*/64k_depth/waves_capture.jsonl'))
  if len(captures)!=1:raise RuntimeError('native wave capture missing')
  captured=[json.loads(x) for x in captures[0].read_text().splitlines() if x.strip()]
  if len(captured)!=4 or any(x.get('schema')!='epyc.vidya.np_ctx_kvu_capture.v1' or not x.get('row_sha256') for x in captured):raise RuntimeError('native wave capture invalid')
 lines=[json.loads(x) for x in ledger.read_text().splitlines() if x.strip()]
 if len(lines)!=2 or lines[0]['norm_argv']!=lines[1]['norm_argv']:raise RuntimeError('paired normalized argv mismatch')
 def w(arm):
  f=list((out/arm).glob('*/64k_depth/waves.json'))
  if len(f)!=1:raise RuntimeError('missing or ambiguous native waves')
  return json.loads(f[0].read_text())
 q={x:True for x in ('same_binary','same_model','same_source','same_argv','gpu_idle_both','quarter_bound_both','both_complete','no_errors','same_clients','cleanup_verified','warrant_captured')}
 verdict=reduce_pair(u,s,w('unified'),w('split'),q)
 if verdict['verdict']=='INVALID':raise RuntimeError('predeclared result INVALID: '+verdict['reason'])
 (out/'VERDICT.json').write_text(json.dumps(verdict,indent=2)+'\n')
 append_native(event,{'mode':m,'arm':'verdict','native_record_complete':True,'verdict':verdict['verdict'],'provenance':provenance})
 (out/'COMPLETE.json').write_text(json.dumps({'state':'complete','verdict':verdict['verdict'],'provenance':provenance})+'\n')
if __name__=='__main__':main()
