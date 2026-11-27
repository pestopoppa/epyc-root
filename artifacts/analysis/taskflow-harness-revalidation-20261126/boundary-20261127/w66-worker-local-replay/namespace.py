import json,subprocess
from replay import stage,HERE,UNITS,write
box,root=stage('namespace-probe',UNITS/'gpu-DS41-W-66-off-recommended',True)
code='import sys,json;sys.path[:0]=["/case/scripts/kernel_rnd","/case"];import scripts.kernel_rnd.autokernel.loop.phase_journal as a;import autokernel.loop.phase_journal as b;print(json.dumps({"scripts_name":a.__name__,"pytest_name":b.__name__,"scripts_file":a.__file__,"pytest_file":b.__file__,"same_module":a is b,"same_class":a.PhaseJournal is b.PhaseJournal}))'
with box.running():
    q=box.command(['/usr/bin/nice','-n','19','python3','-c',code],capture_output=True,timeout=30)
    (root/'stdout.log').write_bytes(q.stdout);(root/'stderr.log').write_bytes(q.stderr)
    assert q.returncode==0,q.stderr
    data=json.loads(q.stdout);assert not data['same_module'] and not data['same_class']
    container=box.container
assert subprocess.run(['docker','inspect',container],capture_output=True).returncode!=0
write(root/'RESULT.json',{'probe':data,'owned_container_removed':True,'model_calls':0,'no_pytest_or_candidate_edit':True})
print(data)
