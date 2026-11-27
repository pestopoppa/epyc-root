"""Fresh exact-stock worker test replay without any model session/prompt."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
FROZEN=HERE.parent.parent/'ws58-a3b-frozen-revalidation-20261126'
V4=FROZEN/'quality-v4'
CASE=V4/'packets/DS41-W-66'
UNITS=FROZEN/'quality-runs/cache-safe-01/units'
sys.path[:0]=[str(V4)]
from cases import write_git_config
from opencode_derived.sandbox import Assets,Sandbox

TARGET=Path('scripts/kernel_rnd/autokernel/loop/test_runtime_keep_source_continuity.py')
LOOP='scripts/kernel_rnd/autokernel/loop'
RUNTIME=LOOP+'/test_runtime_keep_source_continuity.py::test_runtime_keep_then_source_reuses_actual_recipe_and_fresh_source_floor'
SERIAL=LOOP+'/test_serial_run.py::test_actual_cpu_post_keep_resume_rebinds_original_launch_without_recalibration'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')

def stage(label,source_unit,source_candidate):
    root=HERE/'runs'/label
    refs=root/'refs';refs.mkdir(parents=True)
    box=Sandbox(root/'sandbox',1,'84-87',assets=Assets(FROZEN/'stock/opencode',FROZEN/'stock/py312-deps',HERE/'s'),ctx=131072,cap=32768,transport_wall_s=1800,refs=refs,public_web=True)
    write_git_config(box)
    case=json.loads((CASE/'case.json').read_text())
    for name,record in case['baseline_files'].items():
        src=CASE/'baseline'/name;assert sha(src)==record['sha256']
        parts=Path(name).parts
        dest=refs.joinpath(*parts[1:]) if parts[0]=='.taskflow-refs' else box.workspace/name
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
        if parts[0]=='.taskflow-refs':dest.chmod(0o444)
    # Preserve actual canonical Git setup without invoking git add/commit or touching
    # any original index. Tests create their own isolated fixture repositories.
    shutil.copytree(source_unit/'sandbox/work/.git',box.workspace/'.git',symlinks=True)
    if source_candidate:
        raw=json.loads((source_unit/'RESULT.json').read_text());candidate=source_unit/'independent/work'/TARGET
        assert sha(candidate)==raw['changed_files'][str(TARGET)]['sha256']
        shutil.copy2(candidate,box.workspace/TARGET)
    return box,root

def main():
    modes=[('baseline','gpu-DS41-W-66-off-common-on-sampling',False),
           ('off-common-final','gpu-DS41-W-66-off-common-on-sampling',True),
           ('off-recommended-final','gpu-DS41-W-66-off-recommended',True)]
    source_paths=[CASE/'case.json',CASE/'oracle.py',CASE/'baseline'/TARGET]
    for _,name,_ in modes:
        source_paths += [UNITS/name/'RESULT.json',UNITS/name/'OPEN-CODE-SESSION.json',UNITS/name/'independent/work'/TARGET]
    before={str(p):sha(p) for p in source_paths}
    summary=[]
    case=json.loads((CASE/'case.json').read_text())
    for label,name,candidate in modes:
        box,root=stage(label,UNITS/name,candidate);target_before=sha(box.workspace/TARGET)
        commands=[('original-acceptance',case['worker_task']['acceptance']),
                  ('runtime-call-untruncated','python3 -m pytest -xvs '+RUNTIME),
                  ('serial-call-untruncated','python3 -m pytest -xvs '+SERIAL)]
        results=[]
        with box.running():
            for title,command in commands:
                start=time.monotonic()
                q=box.command(['/usr/bin/nice','-n','19','/bin/bash','-lc',command],capture_output=True,timeout=120)
                (root/(title+'.stdout.log')).write_bytes(q.stdout);(root/(title+'.stderr.log')).write_bytes(q.stderr)
                results.append({'kind':title,'command':command,'rc':q.returncode,'wall_s':time.monotonic()-start,
                                'stdout_sha256':hashlib.sha256(q.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(q.stderr).hexdigest()})
            # Same independent checker and injection method as canonical grade().
            checker=box.refs/'.independent-oracle.py';shutil.copy2(CASE/'oracle.py',checker);checker.chmod(0o444)
            command='export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1; exec python3 /case/.taskflow-refs/.independent-oracle.py --pytest /tmp/independent-pytest'
            q=box.command(['/usr/bin/nice','-n','19','/bin/bash','-lc',command],capture_output=True,timeout=120)
            (root/'independent.stdout.log').write_bytes(q.stdout);(root/'independent.stderr.log').write_bytes(q.stderr)
            results.append({'kind':'canonical-independent-oracle','command':command,'rc':q.returncode,
                            'stdout_sha256':hashlib.sha256(q.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(q.stderr).hexdigest()})
            assert sha(box.workspace/TARGET)==target_before
            container=box.container
        check=subprocess.run(['docker','inspect',container],capture_output=True)
        assert check.returncode!=0,'owned replay container survived cleanup'
        record={'label':label,'source_unit':name,'source_candidate':candidate,'candidate_sha256':target_before,
                'checks':results,'stock_container':str(root/'sandbox/CONTAINER.json'),'owned_container_removed':True,
                'provider_upstream_port':1,'no_model_endpoint_supplied':True,'model_prompt_or_session_calls':0,
                'actual_stock_readonly_refs_and_gitsetup':True}
        write(root/'RESULT.json',record);summary.append(record);print(label,[(r['kind'],r['rc']) for r in results],flush=True)
    assert all(sha(Path(p))==s for p,s in before.items())
    write(HERE/'REPLAY.json',{'runs':summary,'original_inputs_sha256':before,'source_unchanged':True,'model_calls':0,'canonical_or_live_edits':False})

if __name__=='__main__':main()
