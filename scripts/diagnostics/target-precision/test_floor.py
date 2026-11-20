"""Model-free original-output replay and native floor execution fixtures."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest
from test_admission import make_panel, save, reseal

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location('floor_test_producer', HERE/'floor.py')
floor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(floor)


def panel_refs(tmp_path):
    panel = make_panel(tmp_path)
    plan, records, _ = panel
    refs = records['floor']['controls'][0]['trace_outputs']
    return panel, refs


def test_reduction_counts_every_coordinate(tmp_path):
    (plan, _, _), refs = panel_refs(tmp_path)
    result = floor.summarize(plan, refs, floor._module('capture')._read)
    assert result['repetitions'] == 2 and result['coordinates'] == 200
    assert result['max_abs'] == .005 and result['rms'] == .002


@pytest.mark.parametrize('kind', ['trace', 'runtime'])
@pytest.mark.parametrize('mutation', ['edit', 'remove', 'symlink'])
def test_original_custody_refuses(tmp_path, kind, mutation):
    (plan, _, _), refs = panel_refs(tmp_path)
    path = Path(refs[0][kind]['path'])
    if mutation == 'edit':
        path.write_text('{}')
    elif mutation == 'remove':
        path.unlink()
    else:
        target = path.with_suffix('.saved')
        path.rename(target)
        path.symlink_to(target)
    with pytest.raises((ValueError, OSError)):
        floor.summarize(plan, refs, floor._module('capture')._read)


@pytest.mark.parametrize('change', [
    lambda t: t['request']['case'].update(repetition=0),
    lambda t: t['request']['case'].update(seed=99),
    lambda t: t['request'].update(prompt='edited'),
    lambda t: t['request']['settings'].update(backend='hip'),
    lambda t: t['blocks'][0]['logits'][0]['witness'].update(count=0),
    lambda t: t['blocks'].clear(),
    lambda t: t.update(status='failed', error='native failure'),
])
def test_resealed_false_trace_refuses(tmp_path, change):
    (plan, _, _), refs = panel_refs(tmp_path)
    trace = json.loads(Path(refs[1]['trace']['path']).read_text())
    change(trace)
    refs[1]['trace'] = save(Path(refs[1]['trace']['path']), trace)
    # Reseal runtime request too: refusal must inspect semantic content.
    observed = json.loads(Path(refs[1]['runtime']['path']).read_text())
    observed['request'] = trace['request']
    refs[1]['runtime'] = save(Path(refs[1]['runtime']['path']), observed)
    with pytest.raises(ValueError):
        floor.summarize(plan, refs, floor._module('capture')._read)


def test_resealed_false_aggregate_refuses_admission(tmp_path):
    panel, _ = panel_refs(tmp_path)
    control = panel[1]['floor']['controls'][0]
    control['coordinates'] = 201
    control['native_output'] = save(Path(control['native_output']['path']),
                                    {k: v for k, v in control.items() if k != 'native_output'})
    reseal(panel, 'floor')
    with pytest.raises(ValueError, match='recomputation'):
        floor._module('capture').admit_native(panel[0])


def execution_fixture(tmp_path, monkeypatch, fail=False):
    panel, refs = panel_refs(tmp_path)
    plan, records, _ = panel
    exe = tmp_path/'native-fixture'
    plan['binary_sha256'] = save(exe, {'fixture': True})['sha256']
    plan['native_worker'].update(executable=str(exe), timeout_s=10)
    records['build']['binary_sha256'] = plan['binary_sha256']
    reseal(panel, 'build')
    requests = []
    traces = [json.loads(Path(ref['trace']['path']).read_text()) for ref in refs]
    proofs = [json.loads(Path(ref['runtime']['path']).read_text()) for ref in refs]
    for trace in traces:
        request = trace['request']
        request['settings'] = {k: plan[k] for k in floor._module('capture').SHARED}
        request['runtime'] = copy.deepcopy(plan['native_worker'])
        requests.append(copy.deepcopy(request))
    calls = []

    def execute(command, env, out, err, timeout, passed_plan, request):
        index = len(calls)
        calls.append(request)
        trace = copy.deepcopy(traces[index])
        trace['request'] = request
        save(Path(command[-1]), trace)
        proof = copy.deepcopy(proofs[index])
        proof['request'] = request
        if fail:
            proof['returncode'] = 7
        return proof

    worker = floor._module('worker')
    monkeypatch.setattr(worker.runtime, 'execute', execute)
    original = floor._module
    monkeypatch.setattr(floor, '_module', lambda name: worker if name == 'worker' else original(name))
    return plan, requests, calls


def test_producer_executes_and_retains_replayable_originals(tmp_path, monkeypatch):
    plan, requests, calls = execution_fixture(tmp_path, monkeypatch)
    result = floor.produce(plan, requests, tmp_path/'out')
    assert len(calls) == 2 and result['coordinates'] == 200
    original = json.loads(Path(result['native_output']['path']).read_text())
    assert floor.summarize(plan, original['trace_outputs'], floor._module('capture')._read) == original
    with pytest.raises(FileExistsError):
        floor.produce(plan, requests, tmp_path/'out')


def test_failed_execution_retains_failure_without_control(tmp_path, monkeypatch):
    plan, requests, calls = execution_fixture(tmp_path, monkeypatch, fail=True)
    with pytest.raises(ValueError, match='observation failed'):
        floor.produce(plan, requests, tmp_path/'out')
    assert len(calls) == 1
    assert (tmp_path/'out/0-runtime.json').exists()
    assert not (tmp_path/'out/control.json').exists()


def test_bad_request_refuses_before_launch(tmp_path, monkeypatch):
    plan, requests, calls = execution_fixture(tmp_path, monkeypatch)
    requests[1]['case']['repetition'] = 0
    with pytest.raises(ValueError, match='repetition'):
        floor.produce(plan, requests, tmp_path/'out')
    assert not calls and not (tmp_path/'out').exists()


@pytest.mark.parametrize('kind', ['trace', 'runtime'])
def test_closure_reopens_floor_originals(tmp_path, kind):
    (plan, _, _), refs = panel_refs(tmp_path)
    capture = floor._module('capture')
    plan_path, opened = tmp_path/'plan.json', tmp_path/'opened.json'
    save(plan_path, plan)
    capture.open_capture(plan_path, opened)
    Path(refs[0][kind]['path']).write_text('{}')
    with pytest.raises(ValueError, match='floor original digest'):
        capture._finalized(opened, [])


@pytest.mark.parametrize('field', ['floor_producer_sha256', 'floor_worker_sha256'])
def test_closure_binds_control_reducer_bytes(tmp_path, field):
    (plan, _, _), _ = panel_refs(tmp_path)
    capture = floor._module('capture')
    plan_path, opened = tmp_path/'plan.json', tmp_path/'opened.json'
    save(plan_path, plan)
    record = capture.open_capture(plan_path, opened)
    record[field] = '0'*64
    save(opened, record)
    with pytest.raises(ValueError, match='floor .* bytes changed'):
        capture._finalized(opened, [])
