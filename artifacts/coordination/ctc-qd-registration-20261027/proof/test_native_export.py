"""Native Research-produced synthetic records: semantic verifier positive/negative."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
root=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ctc-qd-activation-prep/research')
packet=Path('/mnt/raid0/llm/tmp/codex-ni-20261027-ctc-qd-activation-prep/packet')
sys.path.insert(0, str(root/'scripts/kernel_rnd'))
from autokernel.loop.test_glm_frozen_requests import _canonical_launch
from autokernel.loop.test_experiment_plan import plan_dict

with tempfile.TemporaryDirectory() as directory:
    base=Path(directory)
    recipe=base/'recipe.json'; plan=base/'plan.json'
    recipe.write_text(json.dumps(_canonical_launch(18311)[1].to_dict()))
    plan.write_text(json.dumps(plan_dict()))
    command=[sys.executable, str(packet/'native_export_check.py'), '--research-root', str(root), '--recipe', str(recipe), '--anchor', str(plan)]
    first=subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert first.returncode == 0, (first.stdout, first.stderr)
    proof=json.loads(first.stdout)
    assert proof['schema']=='epyc.registration_native_validation.v1'
    assert proof['server'] is None and proof['server_custody'] is None
    server=base/'server.json'; server.write_text(json.dumps({'schema':'epyc.stack.server_launch.v1'}))
    with_server=subprocess.run(command + ['--server', str(server)], capture_output=True, text=True, timeout=20)
    assert with_server.returncode == 0, with_server.stderr
    assert json.loads(with_server.stdout)['server_custody_status'] == 'UNKNOWN'
    bad=json.loads(recipe.read_text()); bad['execution_digest']='0'*64; recipe.write_text(json.dumps(bad))
    second=subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert second.returncode != 0, second.stdout
    recipe.write_text(json.dumps(_canonical_launch(18311)[1].to_dict()))
    bad_plan=json.loads(plan.read_text()); bad_plan['metric_direction']='sideways'; plan.write_text(json.dumps(bad_plan))
    third=subprocess.run(command, capture_output=True, text=True, timeout=20)
    assert third.returncode != 0, third.stdout
    print('PASS native semantic positive and bad execution digest / plan direction negatives; synthetic artifacts; no server')
