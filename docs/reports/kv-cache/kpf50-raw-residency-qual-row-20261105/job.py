#!/usr/bin/env python3
"""Bounded retained-validator qualification; synthetic inputs only."""
import hashlib,json,os,pathlib,subprocess,sys,time,signal
D=pathlib.Path(__file__).resolve().parent
FULL=D/'out/RESULT.json'
def verify():
 for name,digest in json.loads((D/'seals.json').read_text()).items():
  if hashlib.sha256((D/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('seal drift: '+name)
def atomic(p,obj):
 p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix('.tmp');q.write_text(json.dumps(obj,indent=2)+'\n');q.replace(p)
if '--check' in sys.argv:verify();sys.exit(0)
smoke=os.environ.get('FILLER_DRYRUN')=='1' or os.environ.get('FILLER_SMOKE')=='1'
if smoke:
 result=pathlib.Path(os.environ['FILLER_DRYRUN_RESULT_PATH']).resolve()
 if result==FULL or D/'out' in result.parents:raise SystemExit('dry-run result must be outside full out tree')
else:result=FULL
if result.exists():raise SystemExit('existing result; preserve attempt')
if os.environ.get('FILLER_ID')!='kpf50-raw-residency-qual-20261105':raise SystemExit('rowflow grant required')
stop=pathlib.Path(os.environ['FILLER_STOPFILE']);end=min(float(os.environ['FILLER_END'])-15,time.time()+180)
run=result.parent/('attempt-'+str(time.time_ns()));run.mkdir(parents=True,exist_ok=False)
r={'schema':'epyc.kpf50.residency-qualification.v1','status':'INVALID','synthetic_only':True,'native_binding':'UNKNOWN','gate_verdict':'UNRESOLVED','partial':smoke,'scan_complete':False,'mode':'smoke' if smoke else 'full','id':'kpf50-raw-residency-qual-20261105','cases':[],'cleanup_confirmed':True}
p=None
try:
 verify();cases=json.loads((D/'cases.json').read_text())
 if smoke:cases=[x for x in cases if x['name'] in ('positive','wrong-birth','untrusted-native')]
 for c in cases:
  if stop.exists() or time.time()>=min(end,float(os.environ.get('FILLER_DEADLINE',end))):raise RuntimeError('STOP/deadline before case')
  bundle=D/'cases'/c['name']
  cmd=[sys.executable,'-I','-B',str(D/'retained/verify_residency.py'),str(bundle)]
  with (run/(c['name']+'.stdout')).open('w') as out,(run/(c['name']+'.stderr')).open('w') as err:
   p=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True)
   captured=p.pid
   try:p.wait(timeout=max(.1,min(5,end-time.time())))
   except subprocess.TimeoutExpired:
    p.terminate()
    try:p.wait(timeout=2)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)
    raise RuntimeError('validator timeout')
   rc=p.returncode
  try:os.kill(captured,0)
  except ProcessLookupError:pass
  else:raise RuntimeError('captured child remains')
  p=None
  payload=json.loads((run/(c['name']+'.stdout')).read_text())
  matched=rc==3 and payload.get('status')=='UNKNOWN' and payload.get('native_verified') is False and payload.get('gate_verdict')=='UNRESOLVED'
  if c['refusal']:
   matched=matched and payload.get('reason')==('missing, malformed or unsupported evidence: '+('PID reused or birth mismatch' if c['name']=='wrong-birth' else 'sample clock mismatch')) and 'samples' not in payload
  else:
   matched=matched and payload.get('two_disjoint_during_step_candidate_samples') is c['candidate'] and payload.get('synthetic') is c['synthetic']
   samples=payload.get('samples',[])
   matched=matched and len(samples)==(1 if c['name']=='missing-sample' else 2)
   if c['name']=='positive' or c['name']=='untrusted-native':
    matched=matched and all(s['during_step'] and s['pid_birth_stable'] and s['kfd_fd_open'] and s['drm_vram_bytes']==1048576 for s in samples)
   if c['name'] in ('after-step','straddle-step'):matched=matched and samples[1]['during_step'] is False
   if c['name']=='missing-kfd':matched=matched and samples[1]['kfd_fd_open'] is False
   if c['name']=='wrong-bdf':matched=matched and all(s['drm_vram_bytes'] is None for s in samples)
  r['cases'].append(dict(c,actual_rc=rc,pid=captured,matched=matched,payload=payload))
  if not matched:raise RuntimeError('unexpected validator result: '+c['name'])
 verify();r.update(status='PARTIAL_SMOKE_ONLY' if smoke else 'SYNTHETIC_RESIDENCY_QUALIFIED',scan_complete=not smoke)
except Exception as e:r['reason']=str(e)
finally:
 if p is not None and p.returncode is None:
  p.terminate()
  try:p.wait(timeout=2)
  except subprocess.TimeoutExpired:
   p.kill()
   try:p.wait(timeout=2)
   except subprocess.TimeoutExpired:r['cleanup_confirmed']=False
  try:os.kill(p.pid,0)
  except ProcessLookupError:pass
  else:r['cleanup_confirmed']=False
 r['attempt']=str(run);atomic(result,r)
sys.exit(0 if r['status'] in ('PARTIAL_SMOKE_ONLY','SYNTHETIC_RESIDENCY_QUALIFIED') and r['cleanup_confirmed'] else 2)
