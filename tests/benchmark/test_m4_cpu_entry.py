import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest

DIRECTORY = Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_cpu_ownership'
spec = importlib.util.spec_from_file_location('m4_cgroup_guard', DIRECTORY/'m4_cgroup_guard.py')
guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)


def setup_entry(tmp_path, mode='fixture', sleep=0.1):
    output = tmp_path/'output'; output.mkdir()
    marker = tmp_path/'started'
    fixture = tmp_path/'fixture.py'
    fixture.write_text(f"from pathlib import Path\nimport time\nPath({str(marker)!r}).write_text('started')\ntime.sleep({sleep})\n")
    plan = tmp_path/'plan.json'
    plan.write_text(json.dumps({'schema':'epyc.m4.cpu_entry_fixture.v1','mode':mode,'region':'q1',
                               'fixture':str(fixture),'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest()}))
    grant=tmp_path/'grant'; now=datetime.now(timezone.utc)
    grant.write_text('regions=q1 start='+ (now-timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%MZ') +' end='+ (now+timedelta(minutes=3)).strftime('%Y-%m-%dT%H:%MZ'))
    stop=tmp_path/'stop'; hold=tmp_path/'hold'; hold.mkdir()
    args=[sys.executable,str(DIRECTORY/'entry.py'),'--plan',str(plan),'--plan-sha256',hashlib.sha256(plan.read_bytes()).hexdigest(),
          '--grant',str(grant),'--stop',str(stop),'--hold',str(hold),'--deadline',str(time.time()+90),
          '--owner-pid',str(os.getpid()),'--owner-birth',str(guard.birth(os.getpid())),'--output',str(output)]
    return args, output, marker, grant, stop, hold


def test_real_entry_fixture_success(tmp_path):
    args, output, marker, *_ = setup_entry(tmp_path)
    result=subprocess.run(args,capture_output=True,text=True,timeout=15)
    assert result.returncode == 0, result.stderr
    assert marker.exists() and json.loads((output/'FIXTURE-COMPLETE.json').read_text())['fixture_only'] is True
    assert json.loads((output/'watch-result.json').read_text())['containment_empty'] is True


@pytest.mark.parametrize('block', ['stop', 'hold', 'real', 'bad_grant'])
def test_real_entry_refuses_before_effect(tmp_path, block):
    args, output, marker, grant, stop, hold = setup_entry(tmp_path,mode='real' if block=='real' else 'fixture')
    if block=='stop': stop.touch()
    if block=='hold': (hold/'HOLD_fixture').touch()
    if block=='bad_grant': grant.write_text('regions=q2 start=2000-01-01T00:00Z end=2100-01-01T00:00Z')
    result=subprocess.run(args,capture_output=True,text=True,timeout=15)
    assert result.returncode == 2 and not marker.exists()
    assert not (output/'FIXTURE-COMPLETE.json').exists()


@pytest.mark.parametrize('change', ['stop', 'hold', 'grant'])
def test_real_entry_stops_running_fixture_on_control_change(tmp_path, change):
    args, output, marker, grant, stop, hold = setup_entry(tmp_path,sleep=10)
    proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        deadline=time.monotonic()+5
        while time.monotonic()<deadline and not marker.exists():
            if proc.poll() is not None: raise AssertionError(proc.stderr.read())
            time.sleep(.02)
        assert marker.exists()
        if change=='stop': stop.touch()
        elif change=='hold': (hold/'HOLD_fixture').touch()
        else: grant.write_text('revoked')
        stdout,stderr=proc.communicate(timeout=15)
        assert proc.returncode != 0, (stdout,stderr)
        assert not (output/'FIXTURE-COMPLETE.json').exists()
        assert json.loads((output/'watch-result.json').read_text())['containment_empty'] is True
    finally:
        if proc.poll() is None:
            proc.kill();proc.wait(timeout=10)


def test_native_dispatcher_runs_without_execute_and_refuses_unbound_scope(tmp_path):
    args, output, marker, *_ = setup_entry(tmp_path)
    plan_path=Path(args[args.index('--plan')+1])
    plan=json.loads(plan_path.read_text())
    scope=tmp_path/'scope.json'; scope.write_text('{}')
    native_plan=tmp_path/'native-plan.json'; native_plan.write_text('{}')
    images=tmp_path/'images'; images.mkdir()
    plan.update(mode='native-check',scope=str(scope),scope_sha256=hashlib.sha256(scope.read_bytes()).hexdigest(),
                native_plan=str(native_plan),native_plan_sha256=hashlib.sha256(native_plan.read_bytes()).hexdigest(),
                baseline_image=str(images),candidate_image=str(images))
    plan_path.write_text(json.dumps(plan)); args[args.index('--plan-sha256')+1]=hashlib.sha256(plan_path.read_bytes()).hexdigest()
    result=subprocess.run(args,capture_output=True,text=True,timeout=15)
    assert result.returncode == 2 and not marker.exists()
    assert not (output/'FIXTURE-COMPLETE.json').exists()
    assert json.loads((output/'watch-result.json').read_text())['containment_empty'] is True


def test_real_entry_stops_running_fixture_at_deadline(tmp_path):
    args, output, marker, *_ = setup_entry(tmp_path,sleep=10)
    args[args.index('--deadline')+1] = str(time.time()+0.7)
    result = subprocess.run(args,capture_output=True,text=True,timeout=15)
    assert result.returncode == 2 and marker.exists()
    assert not (output/'FIXTURE-COMPLETE.json').exists()
    assert json.loads((output/'watch-result.json').read_text())['containment_empty'] is True
