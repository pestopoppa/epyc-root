#!/usr/bin/env python3
"""Finalize only after an owned network-none build; never runs native tests."""
import hashlib,json,os,re,subprocess,sys
from pathlib import Path
import docker
from source_guard import verify_checkout
from offline_eval import digest_lines,make_offline_eval
from swebench.harness.test_spec.test_spec import make_test_spec
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not os.getenv('FILLER_ID') and not os.getenv('FILLER_DRYRUN'), 'pre-row only'
selection=json.loads((D/'selection.json').read_text());assert sha(selection['manifest_path'])==selection['manifest_sha256'], 'frozen candidate manifest changed'
case=json.loads((D/'case.json').read_text());pins=json.loads((D/'pins.json').read_text());registry=json.loads((D/'registry-pin.json').read_text())
assert sha(D/'Dockerfile')==json.loads((D/'BUILD-INPUTS.json').read_text())['Dockerfile']
receipt=json.loads((D/'build-input-receipt.json').read_text())
assert receipt['before']==receipt['after']==json.loads((D/'BUILD-INPUTS.json').read_text())
assert receipt['image_id']==(D/'derived.iid').read_text().strip()
client=docker.from_env();image=client.images.get(receipt['image_id']);assert image.id==receipt['image_id']
c=client.containers.create(image.id,command=['tail','-f','/dev/null'],network_disabled=True,cpuset_cpus='48-51',mem_limit='2g',pids_limit=128)
try:
 c.start();proof=verify_checkout(c,case['base_commit']);assert proof['image_head']==case['base_commit']
finally:
 c.remove(force=True)
 try:client.containers.get(c.id)
 except docker.errors.NotFound:pass
 else:raise RuntimeError('preparation owned container not removed')
(D/'guard-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
spec=make_test_spec(case,namespace='swebench');pins.update(preparation_ready=True,image_id=image.id,official_script_sha256=digest_lines(spec.eval_script_list),image_build_log_sha256=sha(D/'build.log'),wheel_manifest_sha256=None,build_context_seal_sha256=sha(D/'BUILD-INPUTS.json'),dockerfile_sha256=sha(D/'Dockerfile'))
make_offline_eval(spec.eval_script_list,pins['official_script_sha256'],image.id,image.id)
for path,digest in pins['scorer_sources'].items():assert sha(path)==digest,'scorer changed: '+path
(D/'pins.json').write_text(json.dumps(pins,indent=2)+'\n')
(D/'PREPARATION_READY').write_text('Image exact-base guard and offline script transform passed; no native verdict.\n')
names=sorted(x.name for x in D.iterdir() if x.is_file() and x.suffix in ('.py','.json','.sh') and x.name not in ('REVIEW.json',))
# launch embeds the manifest digest, so it is excluded from the manifest and bound in REVIEW.
names.remove('launch.sh')
manifest=''.join(sha(D/name)+'  '+name+'\n' for name in names)
(D/'SOURCE.sha256').write_text(manifest)
launch=(D/'launch.sh').read_text();launch=re.sub(r"'[a-f0-9]{64}' SOURCE.sha256", "'"+sha(D/'SOURCE.sha256')+"' SOURCE.sha256", launch)
(D/'launch.sh').write_text(launch)
review={'schema':'p5.preparation-review.v2','status':'PREPARED_NOT_EXECUTED','question':'Does a second-repository official scorer distinguish pinned gold and no-op without regressions?','selection':'selection.json','image_id':image.id,'case_base_commit':case['base_commit'],'scope':'Two controls one Sphinx case; no model inference; no full P5-2 or total-isolation claim. Native tests require authorized publisher smoke.','files':{x.name:sha(x) for x in D.iterdir() if x.is_file() and x.suffix in ('.py','.json','.sh') and x.name!='REVIEW.json'},'source_manifest_sha256':sha(D/'SOURCE.sha256'),'launch_sha256':sha(D/'launch.sh')}
(D/'REVIEW.json').write_text(json.dumps(review,indent=2)+'\n')
print(json.dumps({'ready':True,'image_id':image.id,'source_manifest_sha256':sha(D/'SOURCE.sha256')}))
