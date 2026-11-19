#!/usr/bin/env python3
"""Keeper entry for KPF181 item6 public controls; refuses absent custody/rate.

This does not issue nonces or receipts. The custody hook is deliberately
unbound: a point-in-time PID scan is not an all-writer exclusion proof.
"""
import hashlib,json,os,pathlib,signal,subprocess,sys,time
from native_event_bridge import Refused,load_canonical,write_exclusive
from model_receipt import verify as verify_model_receipt
D=pathlib.Path(__file__).resolve().parent
OLD=pathlib.Path('/mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240/gpu-leg-v3')
TARGET='/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf'
DRAFT='/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf'
EXPECTED_MODELS={TARGET:'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348',DRAFT:'7f1c9a31a6ed40044c69f6508b50fd63b87abd8e1fb7fe4290303df549153751'}
# Review gate: receipt bytes do not yet exist; bind the actual digest in source
# after out-of-grant prepare, before this candidate can ever be enabled.
RECEIPT_PATH = pathlib.Path('/mnt/raid0/llm/tmp/kvu/kpf181-model-receipt-20261105.json')
RECEIPT_SHA256 = None
CUSTODY_PROVIDER=None  # no existing all-writer participant: cannot claim one
HALT=False

def on_signal(*_):
 global HALT;HALT=True

def sha(path):
 h=hashlib.sha256()
 with pathlib.Path(path).open('rb') as f:
  for b in iter(lambda:f.read(4<<20),b''):h.update(b)
 return h.hexdigest()

def require_context(env):
 if env.get('WS58_QUAL')!='1' or env.get('WS58_QUAL_GPU_HELD')!='1' or env.get('FILLER_QUAL_PHASE') not in ('normal','cutoff'):
  raise Refused('keeper GPU qualification context required')
 for k in ('WS58_MANIFEST_PATH','WS58_QUALIFIER_PATH','WS58_QUAL_NONCE','FILLER_RESULTS_DIR','FILLER_STOPFILE','FILLER_DEADLINE','FILLER_CPUS','WS58_QUAL_PROOF'):
  if not env.get(k):raise Refused('keeper field missing: '+k)
 if env['FILLER_QUAL_PHASE']=='cutoff' and not env.get('WS58_QUAL_CUTOFF_EVENT'):raise Refused('cutoff event path missing')

def require_admission(manifest,qualifier):
 # Existing legacy writers do not participate in a shared lock. No variable,
 # sentinel, filename or caller assertion may be treated as a custody proof.
 if CUSTODY_PROVIDER is None:raise Refused('all-writer predecessor custody provider not bound')
 CUSTODY_PROVIDER.verify(manifest)
 basis=manifest.get('rate_basis',{})
 if basis.get('scope')!='calibrated-work-unit' or basis.get('production_threads')!=8 or basis.get('work_unit')!='KPF181 item6 full two-binary groups 0,2,4,7':raise Refused('exact full-unit production rate absent')
 qualifier.bound_files(manifest)
 rate=qualifier.feasible_rate(manifest,{})
 if rate is None or not qualifier.feasible_window(manifest,rate):raise Refused('full-unit rate infeasible or unknown')

def make_command(manifest,phase,out,cpus):
 if manifest.get('id')!='codex3-kpf181-27b-gpu-r4-v14-20261101':raise Refused('wrong row')
 if not cpus or any(c not in '0123456789,-' for c in cpus):raise Refused('invalid qualification CPUs')
 cmd=['/usr/bin/python3','-B',str(D/'kpf18_gate_qual.REVIEW.py'),'item6','--fork-bin','/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin/llama-server','--champion-bin','/mnt/micron/codex3-lanes/kpf181-e332-hip-build/bin/llama-server','--argv-file',str(OLD/'full-argv.txt'),'--prompt-set',str(OLD/'public-control-prompts.jsonl'),'--out',str(out),'--launch-prefix','taskset -c '+cpus,'--port','19639','--allow-shape-drift','--fork-min','1024','--item6-groups','0','--n-predict','128' if phase=='cutoff' else '8','--budget-min','240','--gpu-window-id',manifest['id'],'--no-device-claim','exclusive gpu-quiet held by enclosing launcher','--vram-ceiling-gib','60','--public-control']
 if phase=='cutoff':cmd+=['--control-single-arm','champion']
 return cmd

def validate_native_records(records):
 expected={'champion':'8a3710ad9f0bea535dd9cbd84ff49d8b8af9e2783979077fb109db13a5620b7b','fork_off':'2be7a16ed6d3712d82a36c668417b4dcec8d9cadd13a682e069cb4d57b9d0635'}
 if len(records)!=2:raise Refused('expected two native control records')
 seen=set()
 for path in records:
  rec=json.loads(path.read_text());arm=rec.get('arm');claimed=rec.get('record_sha256');payload={k:v for k,v in rec.items() if k!='record_sha256'}
  digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  if arm not in expected or arm in seen or claimed!=digest or rec.get('schema')!='epyc.kpf.run.v1' or rec.get('partial') or rec.get('binary_sha256')!=expected[arm] or rec.get('prompt_set_sha256')!='30d66fdb3cf9e03891e526d675bf64f206338833c2cfa70779aa696cc5aa3b68':raise Refused('native comparator record identity mismatch')
  argv=rec.get('argv') or []
  for flag,value in (('-m',TARGET),('-md',DRAFT),('-c','393216'),('-np','4'),('-t','8')):
   if argv.count(flag)!=1 or argv[argv.index(flag)+1]!=value:raise Refused('native comparator geometry mismatch')
  residency=rec.get('residency') or {};stop=residency.get('stop') or {}
  if residency.get('hip_mapped') is not True or stop.get('verified_dead') is not True:raise Refused('native GPU residency or drain missing')
  seen.add(arm)
 return records[0]

def run(env=os.environ):
 require_context(env)
 # Load and revalidate actual canonical qualifier code, not a caller substitute.
 m,validate=load_canonical(env['WS58_MANIFEST_PATH'],env['WS58_QUALIFIER_PATH'])
 import importlib.util
 path=pathlib.Path(env['WS58_QUALIFIER_PATH']);spec=importlib.util.spec_from_file_location('_kpf181_admission',path);q=importlib.util.module_from_spec(spec)
 sys.path.insert(0,str(path.parent))
 try:spec.loader.exec_module(q)
 finally:sys.path.pop(0)
 m=q.load_manifest(pathlib.Path(env['WS58_MANIFEST_PATH']))
 require_admission(m,q)
 if RECEIPT_SHA256 is None:raise Refused('pre-grant receipt digest has not been source-pinned')
 try:verify_model_receipt(RECEIPT_PATH, RECEIPT_SHA256)
 except (OSError,ValueError,KeyError,TypeError) as e:raise Refused('pre-grant model receipt failed: '+str(e))
 out=pathlib.Path(env['FILLER_RESULTS_DIR']);out.mkdir(parents=True,exist_ok=True)
 # qdir is chosen by the keeper; require result files to be new within it.
 phase=env['FILLER_QUAL_PHASE'];runout=out/('kpf181-'+phase)
 runout.mkdir(mode=0o700)
 for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,on_signal)
 command=make_command(m,phase,runout,env['FILLER_CPUS'])
 with (out/(phase+'.gate.log')).open('xb') as log:
  child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=dict(env))
  try:
   while child.poll() is None:
    if HALT:
     child.terminate()
     try:child.wait(timeout=8)
     except subprocess.TimeoutExpired:child.kill();child.wait(timeout=8)
     raise Refused('qualification interrupted; owned gate drained')
    time.sleep(.05)
  finally:
   if child.poll() is None:
    child.terminate()
    try:child.wait(timeout=8)
    except subprocess.TimeoutExpired:child.kill();child.wait(timeout=8)
 try:verify_model_receipt(RECEIPT_PATH, RECEIPT_SHA256)
 except (OSError,ValueError,KeyError,TypeError) as e:raise Refused('post-run model identity failed: '+str(e))
 rc=child.returncode;first=json.loads((out/('first-'+phase+'.json')).read_text())
 if not validate(m,first):raise Refused('first request no longer validates')
 proof={'id':m['id'],'nonce':env['WS58_QUAL_NONCE'],'phase':phase,'first_request':first,'observed_cpus':sorted(os.sched_getaffinity(0)),'disk':{'job_floor_gib':m['job_floor_gib']}}
 if phase=='normal':
  records=sorted((runout/'records').glob('*.json'))
  if rc!=0:raise Refused('actual two-arm native comparator control incomplete')
  # Native records are produced only after server cleanup; keep exact native bytes.
  rec=validate_native_records(records);proof['result_writer']={'ok':True,'result_path':str(rec),'sha256':sha(rec)}
 else:
  stop=pathlib.Path(env['FILLER_STOPFILE']).exists();expired=time.time()>=float(env['FILLER_DEADLINE'])
  if rc!=75 or not (stop or expired):raise Refused('active cutoff did not exit 75')
  proof.update(partial=True,stop_observed=stop,deadline_reached=expired,unknown_disposition='UNKNOWN')
 write_exclusive(env['WS58_QUAL_PROOF'],proof)
 return 0 if phase=='normal' else 75

if __name__=='__main__':
 print('REFUSED: isolated receipt integration is disabled pending writer custody and qualification',file=sys.stderr)
 sys.exit(78)
 try:sys.exit(run())
 except (Refused,OSError,KeyError,ValueError,TypeError) as e:print('REFUSED: '+str(e),file=sys.stderr);sys.exit(78)
