#!/usr/bin/env python3
"""Custody/lifecycle wrapper; native PB measurement and verdict code is unchanged."""
import argparse,hashlib,json,os,pathlib,signal,subprocess,sys,threading,time
D=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(D))
import pb_qcost_1_q as P
from source_seal import verify_source_seal
from attempt_state import prepare_attempt, begin_finalization
K=P.K
def write(p,v):
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(v,indent=2)+'\n');t.replace(p)
def main():
 sealed, seal_error = verify_source_seal(D)
 if not sealed: raise RuntimeError(f"source integrity refusal: {seal_error}")
 manifest=json.loads((D/'CANDIDATE-MANIFEST.json').read_text())
 manifest_sha=hashlib.sha256((D/'CANDIDATE-MANIFEST.json').read_bytes()).hexdigest()
 source_sha=manifest['source_code_manifest_sha256']
 if os.environ.get('FILLER_QUAL_PHASE') in ('normal', 'cutoff'):
  from qualification.qual_entry import run as run_qualification
  return run_qualification()
 mode=sys.argv[1] if len(sys.argv)>1 else 'full'
 assert mode in ('full','normal','cutoff')
 smoke=mode!='full'
 if smoke:
  out=D/('smoke-'+mode); run=out/'run'; run_id=None; attempt=None
 else:
  row_id=os.environ.get('FILLER_ID')
  if row_id != manifest.get('id'): raise RuntimeError('FILLER_ID does not match candidate row id')
  out=D/'out'/'attempts'/row_id
  state_path=out/'ATTEMPT.json'
  attempt=prepare_attempt(out,row_id,source_sha,manifest_sha,
   manifest['protocol_hashes']['predeclaration_sha256'],manifest['protocol_hashes']['amendment_sha256'])
  run_id=attempt['run_id']
  run=out/'run'
  if attempt.get('state') == 'FINALIZING':
   rec=subprocess.run([sys.executable,'-B',str(D/'finalize_attempt.py'),str(out)],check=False)
   return 0 if rec.returncode == 0 else 1
 out.mkdir(parents=True,exist_ok=True); run.mkdir(parents=True,exist_ok=True)
 started=time.time(); deadline=float(os.environ.get('FILLER_DEADLINE',started+270))
 cpus=os.environ['FILLER_CPUS']; port=18397
 if smoke: deadline=min(deadline,started+270)
 if not smoke and deadline-started<5700: raise RuntimeError('full unchanged protocol requires >=95 minutes to native deadline')
 sampler=subprocess.Popen([sys.executable,'-B',str(D/'sibling_sampler.py'),str(out),'88-95'])
 probe=None; rc=1;status='FAILED';err=None; verdict_path=out/'VERDICT.json'
 def halt(sig,frame):
  if probe:probe.deadline_hit.set();probe.stop_server()
  raise SystemExit(128+sig)
 signal.signal(signal.SIGTERM,halt);signal.signal(signal.SIGINT,halt)
 try:
  if smoke:
   args=argparse.Namespace(out=str(run),deadline_epoch=deadline,prompt_set=str(D/'prompt_set.jsonl'),argv_file=str(D/'argv.txt'),
    launch_prefix='env HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0 numactl --membind=3 -- taskset -c '+cpus,
    champion_bin='/mnt/raid0/llm/kernels/builds/gpu-20261020-dd3d9721c/bin/llama-server',port=port,
    card=str(K.DEFAULT_CARD),vram_ceiling_gib=60.,vram_free_max_gib=2.,load_timeout_s=240,require_hsa_knob=True)
   probe=P.Probe(args); threading.Thread(target=probe.watchdog,daemon=True).start()
   probe.phase_id='smoke-'+K.utc_tag();probe.start_server(512);probe.erase_all()
   stop,state=probe.start_feeders(1)
   try: row=probe.run_prefill(1,1,4000,state)
   finally:probe.stop_feeders(stop,state)
   assert row['http']==200 and row['n_intervals']>0 and row['feeder_tokens_during']>0, row
   write(out/'native-positive.json',{'first_request_ok':True,'interval_writer_ok':True,'native_row':row,'nonadmitted':True,'coefficient_grade':None})
   if mode=='cutoff':
    probe.args.deadline_epoch=time.time()-.01
    try:probe.check()
    except K.Abort:rc=75;status='PARTIAL'
    else:raise AssertionError('native cutoff not observed')
   else:rc=0;status='SMOKE_COMPLETE'
  else:
   args=['--deadline',P.deadline_arg_utc(deadline),
    '--champion-bin','/mnt/raid0/llm/kernels/builds/gpu-20261020-dd3d9721c/bin/llama-server',
    '--argv-file',str(D/'argv.txt'),'--prompt-set',str(D/'prompt_set.jsonl'),'--port',str(port),'--out',str(run),
    '--launch-prefix','env HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0 numactl --membind=3 -- taskset -c '+cpus,
    '--skip-done','--gpu-window-id',row_id,
    '--no-device-claim','R13 engine owns GPU flock and folded q3 exclusive GPU region-lock']
   from model_identity import verify_model_identity
   verify_model_identity()
   sys.argv=[str(D/'pb_qcost_1_q.py')]+args
   rc=P.main()
   if rc in (3,5,75):rc=75;status='PARTIAL'
   elif rc==0:status='COMPLETE'
 finally:
  if probe:
   probe.deadline_hit.set();probe.stop_server()
   assert all(s['srv'].stop_rec.get('verified_dead') for s in probe.servers),'native cleanup unverified'
  sampler.terminate()
  try:sampler.wait(timeout=8)
  except subprocess.TimeoutExpired:sampler.kill();sampler.wait(timeout=8)
  assert not pathlib.Path('/proc',str(sampler.pid)).exists()
  if not smoke and rc == 0 and status == 'COMPLETE':
   input_path=run/'pb_qcost_1.jsonl'
   begin_finalization(state_path,input_path,time.time()-started)
   subprocess.run([sys.executable,'-B',str(D/'finalize_attempt.py'),str(out)],check=True)
 return rc
if __name__=='__main__':raise SystemExit(main())
