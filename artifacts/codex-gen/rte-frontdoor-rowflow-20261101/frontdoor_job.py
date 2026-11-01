#!/usr/bin/env python3
"""One granted frontdoor, one production-owner acceptance request, own PID cleanup."""
import hashlib,json,os,pathlib,signal,socket,subprocess,sys,time,urllib.request,datetime
import process_guard as guard
D=pathlib.Path(__file__).resolve().parent
STOP=pathlib.Path(os.environ.get('FILLER_STOPFILE',str(D/'STOP')))
R=json.loads((D/'RECIPE.json').read_text()); stopped=False;owned={};handles=[];resource_samples=[];boundary_reason=None;output_dir=None
def stop(*_):
 global stopped;stopped=True
def ident(pid):
 try:
  x=pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(') ',1)[1].split()
  return int(x[19]),x[0]
 except (OSError,ValueError):return None
def capture(p):
 owned[p.pid]=ident(p.pid)[0];handles.append(p);guard.register_session(p,owned[p.pid]);return p
def alive(pid):
 x=ident(pid);return x is not None and x[0]==owned[pid] and x[1]!='Z'
def endnow():
 global boundary_reason
 guard.discover(owned)
 if stopped or STOP.exists():boundary_reason='FILLER_STOPFILE/signal';return True
 if time.time()>=float(os.environ.get('FILLER_DEADLINE',time.time()+1800)):boundary_reason='window deadline';return True
 grant=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants/codex-ni-rte-frontdoor-quarter-20261031.grant')
 try:
  fields=dict(x.split('=',1) for x in grant.read_text().split() if '=' in x)
  end=datetime.datetime.fromisoformat(fields['end'].replace('Z','+00:00')).timestamp()
  start=datetime.datetime.fromisoformat(fields['start'].replace('Z','+00:00')).timestamp()
  if not start<=time.time()<end:boundary_reason='actual grant window';return True
 except (OSError,ValueError,KeyError):boundary_reason='actual grant unavailable';return True
 sample=guard.resource_sample(owned,output_dir);resource_samples.append(sample)
 if sample['boundary']:boundary_reason='resource boundary (80GiB RSS or1GiB output)';return True
 return False
def main():
 global output_dir
 for s in [signal.SIGTERM,signal.SIGINT]:signal.signal(s,stop)
 cpus=os.environ.get('FILLER_CPUS'); assert cpus,'keeper CPU list required'
 out=D/os.environ.get('RTE_OUTPUT','run');out.mkdir(exist_ok=True);output_dir=out;result={'partial':False,'status':'failure','captured_PID_birth':owned};rc=1;server=None
 try:
  assert os.environ.get('FILLER_ID')=='codex-ni-rte-frontdoor-quarter-20261031','rowflow engine identity required'
  grant=pathlib.Path('/mnt/raid0/llm/tmp/compute-flags/grants/codex-ni-rte-frontdoor-quarter-20261031.grant')
  assert grant.is_file(),'rowflow/keeper grant required in both qualification and production mode'
  grant_sha=hashlib.sha256(grant.read_bytes()).hexdigest()
  attempt_mode='dryrun' if os.environ.get('FILLER_DRYRUN')=='1' else 'production'
  if endnow():
   result.update(partial=True,status='partial',reason='window/STOP before launch');return 75
  from native_preflight import run as preflight
  if not preflight(out,R,capture,endnow,owned,alive,os.environ.get('RTE_NATIVE_CUTOFF')=='1'):
   result.update(partial=True,status='partial',reason='active native preflight cutoff');return 75
  # SO_REUSEADDR permits old TIME_WAIT sockets; never SO_REUSEPORT or steal a listener.
  with socket.socket() as sock:
   sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',8070))
  for key in ['owner_checker','live_checker']:
   assert hashlib.sha256(pathlib.Path(R[key]).read_bytes()).hexdigest()==R[key+'_sha256'],key+' changed'
  env={k:v for k,v in os.environ.items() if not k.startswith(('GGML_','LLAMA_ARG_')) and k not in ['LD_PRELOAD','SHIM_NPROCS','OMP_NUM_THREADS']};env.update(R['env'])
  binary=R['argv'][0];assert pathlib.Path(binary).resolve()==pathlib.Path('/mnt/raid0/llm/kernels/production/cpu/llama-server').resolve()
  assert hashlib.sha256(pathlib.Path(binary).read_bytes()).hexdigest()==R['server_sha256'],'production server binary digest drift'
  assert hashlib.sha256(pathlib.Path(R['linkage_checker']).read_bytes()).hexdigest()==R['linkage_checker_sha256'],'ggml linkage checker digest drift'
  linkage=subprocess.run(['/bin/bash',R['linkage_checker'],binary,str(pathlib.Path(binary).parent)],env=env,text=True,capture_output=True)
  (out/'linkage.log').write_text(linkage.stdout+linkage.stderr);assert linkage.returncode==0,'linkage failed'
  cmd=['taskset','-c',cpus,'numactl','--interleave=all']+R['argv'];result['argv']=cmd
  with (out/'frontdoor.log').open('a') as log:
   server=capture(subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT));result['server_pid']=server.pid
   (out/'spawn.json').write_text(json.dumps({'pid':server.pid,'birth':owned[server.pid],'argv':cmd,'env':R['env']},indent=2))
   if os.environ.get('FILLER_PIDFILE'):
    with open(os.environ['FILLER_PIDFILE'],'a') as f:f.write(str(server.pid)+'\n')
   until=time.monotonic()+900
   while time.monotonic()<until and not endnow():
    assert server.poll() is None,'frontdoor exited'
    try:
     with urllib.request.urlopen('http://127.0.0.1:8070/health',timeout=2) as h:
      if h.status==200:
       witness=guard.listener_witness(server.pid,owned[server.pid]);(out/'listener-witness.json').write_text(json.dumps(witness,indent=2));break
    except OSError:pass
    time.sleep(.5)
   else:result.update(partial=True,status='partial',reason='window/STOP before health');return 75
   # Native maps, executable and per-thread affinity prove the actual process.
   maps=pathlib.Path(f'/proc/{server.pid}/maps').read_text();(out/'native-maps.txt').write_text(maps)
   assert '/libggml-cpu.so' in maps and '/libggml-hip.so' not in maps,'native CPU backend proof failed'
   assert str(pathlib.Path(binary).resolve())==os.readlink(f'/proc/{server.pid}/exe')
   (out/'native-status.txt').write_text(pathlib.Path(f'/proc/{server.pid}/status').read_text())
   allowed=set(os.sched_getaffinity(0));affinity={str(t.name):sorted(os.sched_getaffinity(int(t.name))) for t in pathlib.Path(f'/proc/{server.pid}/task').iterdir()}
   (out/'native-affinity.json').write_text(json.dumps(affinity,indent=2));assert all(set(v)<=allowed for v in affinity.values()),'native thread escaped granted CPUs'
   if endnow():result.update(partial=True,status='partial',reason='window/STOP before request');return 75
   witness=guard.listener_witness(server.pid,owned[server.pid]);(out/'listener-witness-before-chat.json').write_text(json.dumps(witness,indent=2))
   output=out/('owner-'+str(time.time_ns()))
   argv=['/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python','-B',R['owner_checker'],'--api-url','http://127.0.0.1:8000','--log-dir',R['api_log_dir'],'--expect-source',R['source_commit'],'--output',str(output)]
   with (out/'owner-check.log').open('a') as checklog:
    checker=capture(subprocess.Popen(argv,stdout=checklog,stderr=subprocess.STDOUT,start_new_session=True))
    while checker.poll() is None and not endnow():time.sleep(.1)
    if endnow():result.update(partial=True,status='partial',reason='window/STOP during request');return 75
    assert checker.returncode==0,'production owner check failed'
   owner_result=output/'RESULT.json'
   owner_record=json.loads(owner_result.read_text())
   assert owner_record.get('status')=='pass' and owner_record.get('request_completed') is True and owner_record.get('committed_live_checker_rc')==0 and owner_record.get('expected_source')==R['source_commit'],'owner checker receipt incomplete'
   review_sha=hashlib.sha256((D/'SOURCE-REVIEW.sha256').read_bytes()).hexdigest()
   unit={'schema':'rte.rowflow.unit.v1','row_id':'codex-ni-rte-frontdoor-quarter-20261031','unit_kind':'dryrun_owner_acceptance' if attempt_mode=='dryrun' else 'production_owner_acceptance','acceptance':attempt_mode=='production','qualification_only':attempt_mode=='dryrun','attempt_mode':attempt_mode,'attempt_id':out.name,'grant_sha256':grant_sha,'source_review_sha256':review_sha,'owner_result_path':str(owner_result),'owner_result_sha256':hashlib.sha256(owner_result.read_bytes()).hexdigest(),'request_id':owner_record['request_id'],'expected_source':owner_record['expected_source'],'committed_live_checker_rc':owner_record['committed_live_checker_rc']}
   (out/'ROWFLOW-UNIT.json').write_text(json.dumps(unit,indent=2)+'\n')
   result.update(status='pass',owner_result=str(owner_result));rc=0
  return rc
 except BaseException as exc:
  result['error']=repr(exc);return 1
 finally:
  result['survivors']=guard.drain(owned,handles);result['drained']=not result['survivors'];result['ended_at']=time.time();result['boundary_reason']=boundary_reason
  result['captured_returncodes']={str(p.pid):p.returncode for p in handles}
  (out/'resource-samples.json').write_text(json.dumps(resource_samples,indent=2))
  if result['survivors']:result.update(status='failure',error='owned process identity survived cleanup')
  (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
  if result['survivors']:return 1
if __name__=='__main__':sys.exit(main())
