#!/usr/bin/env python3
"""P5-2 scorer instrument: pinned Sphinx gold and no-op negative arms."""
import hashlib,json,os,signal,time
from pathlib import Path
import docker
from offline_eval import make_offline_eval
from source_guard import verify_checkout
import swebench.harness.run_evaluation as ev
from swebench.harness.grading import get_logs_eval
from swebench.harness.test_spec.test_spec import make_test_spec
D=Path(__file__).resolve().parent
os.chdir(D)
pins=json.loads((D/'pins.json').read_text()); assert pins.get('preparation_ready') is True, 'image preparation not finalized'; case=json.loads((D/'case.json').read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(D/'case.json')==pins['case_sha256']
for path,digest in pins['scorer_sources'].items(): assert sha(path)==digest, 'scorer source changed: '+path
cpus=os.environ['FILLER_CPUS']; deadline=min(float(os.environ['FILLER_DEADLINE']),time.time()+270); assert cpus and deadline-time.time()>90
client=docker.from_env(); assert client.images.get(pins['image_id']).id==pins['image_id']
owned=[]
def cleanup():
 for c in owned[::-1]:
  try: c.remove(force=True)
  except docker.errors.NotFound: pass
  try: client.containers.get(c.id)
  except docker.errors.NotFound: continue
  raise RuntimeError('owned container still exists: '+c.id)
def terminate(signum,frame): raise SystemExit(75)
signal.signal(signal.SIGTERM,terminate); signal.signal(signal.SIGINT,terminate)
def container(spec,client_,run_id,logger,nocache,force_rebuild=False):
 ttl=max(1,int(deadline-time.time())-10); assert ttl>60
 c=client_.containers.create(image=pins['image_id'],user='root',detach=True,command=['timeout',str(ttl),'tail','-f','/dev/null'],cpuset_cpus=cpus,network_disabled=True,mem_limit='12g',pids_limit=1024,auto_remove=True)
 owned.append(c)
 return c
# Exact official evaluation and grading, constrained owned-container lifecycle; no remote pulls.
ev.build_container=container
checkout_proofs={}
original_copy_to_container=ev.copy_to_container
def guarded_copy_to_container(container, *args, **kwargs):
 if container.id not in checkout_proofs:
  checkout_proofs[container.id]=verify_checkout(container,case['base_commit'])
 return original_copy_to_container(container,*args,**kwargs)
ev.copy_to_container=guarded_copy_to_container
# Avoid upstream cleanup's signal-by-inspected-PID fallback; use only our captured container IDs.
def close(client_,c,logger):
 if c:
  try:c.remove(force=True)
  except docker.errors.NotFound:pass
  try:client.containers.get(c.id)
  except docker.errors.NotFound:return
  raise RuntimeError('owned container not removed')
ev.cleanup_container=close
spec=make_test_spec(case,namespace='swebench'); spec.eval_script_list, script_binding=make_offline_eval(spec.eval_script_list,pins['official_script_sha256'],client.images.get(pins['image_id']).id,pins['image_id'])
arms=[('negative',case['negative_patch']),('gold',case['patch'])]
result={'schema':'p5.gold-control.v1','producer_source_manifest_sha256':sha(D/'SOURCE.sha256'),'producer_launcher_sha256':sha(D/'launch.sh'),'instance_id':case['instance_id'],'arms':{},'image_id':pins['image_id'],'case_sha256':pins['case_sha256'],'script_binding':script_binding,'image_build_log_sha256':pins['image_build_log_sha256'],'wheel_manifest_sha256':pins['wheel_manifest_sha256'],'checkout_proofs':checkout_proofs}
try:
 for arm,patch in arms:
  remaining=int(deadline-time.time())-40
  assert remaining>60, 'insufficient deadline for full test unit'
  pred={'instance_id':case['instance_id'],'model_name_or_path':arm,'model_patch':patch}
  run_id='p5-gold-'+os.environ['FILLER_ID']+'-'+arm+'-ns'+format(time.time_ns(),'x')
  ret=ev.run_instance(spec,pred,False,False,client,run_id,timeout=remaining)
  d=D/'logs/run_evaluation'/run_id/arm/case['instance_id']; report=json.loads((d/'report.json').read_text()) if (d/'report.json').is_file() else {}
  statuses,found=get_logs_eval(spec,str(d/'test_output.txt')) if (d/'test_output.txt').is_file() else ({},False)
  fail=json.loads(case['FAIL_TO_PASS']); passing=json.loads(case['PASS_TO_PASS'])
  if not ret.get('completed') or not found or any(x not in statuses for x in fail+passing): raise RuntimeError('incomplete run / missing explicit named test statuses: '+arm)
  resolved=report[case['instance_id']]['resolved']; failstat={x:statuses[x] for x in fail}; passstat={x:statuses[x] for x in passing}
  if arm=='gold': assert resolved and all(x=='PASSED' for x in failstat.values()) and all(x=='PASSED' for x in passstat.values())
  else: assert not resolved and any(x=='FAILED' for x in failstat.values()) and all(x=='PASSED' for x in passstat.values())
  result['arms'][arm]={'resolved':resolved,'FAIL_TO_PASS':failstat,'PASS_TO_PASS':passstat,'native_report':str(d/'report.json'),'test_log':str(d/'test_output.txt')}
  if time.time()>=deadline-40: raise SystemExit(75)
 result['status']='PASS'
except BaseException as exc:
 result['status']='FAIL'; result['error']=repr(exc)
 raise
finally:
 try:
  cleanup(); result['owned_containers_removed']=True
 except BaseException as exc:
  result['status']='FAIL'; result['cleanup_error']=repr(exc)
  raise
 finally:
  output=D/'RESULT.json'
  output.write_text(json.dumps(result,indent=2)+'\n')
