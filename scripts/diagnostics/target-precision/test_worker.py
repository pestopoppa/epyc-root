"""Model-free native trace fixtures. They are not evidence of DFlash execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

spec = importlib.util.spec_from_file_location('precision_worker_test', Path(__file__).with_name('worker.py'))
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


def write(path, value):
    path.write_text(json.dumps(value))
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def native(tmp_path):
    prompts = write(tmp_path / 'prompts.json', {'prompts': {'heldout': 'A fixed untouched prompt.'}})
    executable = tmp_path / 'native-fixture'
    # A process fixture, deliberately not a native DFlash implementation.
    executable.write_text(f'''#!{sys.executable}
import argparse, json, pathlib
p=argparse.ArgumentParser(); p.add_argument('--request'); p.add_argument('--output'); a=p.parse_args()
r=json.loads(pathlib.Path(a.request).read_text())
assert r['prompt']=='A fixed untouched prompt.' and r['case']['seed']==42
assert r['settings']['verification']=={{'ubatch':32,'mode':'block'}}
v={{'request':r,'status':'ok','spec_type':'draft-dflash','blocks':[
{{'block':0,'draft_tokens':[1,0],'accepted':1,'logits':[
{{'verify_prefix':[2,1], 'serial_prefix':[2,1], 'verify':[0.,2.,1.], 'serial':[0.,1.5,1.]}},
{{'verify_prefix':[2,1,1], 'serial_prefix':[2,1,1], 'verify':[0.,2.,1.], 'serial':[0.,2.,1.]}},
{{'verify_prefix':[2,1,1,0], 'serial_prefix':[2,1,1,0], 'verify':[2.,0.,1.], 'serial':[2.,0.,1.]}}
]}}]}}
pathlib.Path(a.output).write_text(json.dumps(v))
''')
    executable.chmod(0o755)
    plan = {k: 'a' * 64 for k in worker.capture.SHARED if k.endswith('_sha256')}
    plan.update(run_id='test', origin='synthetic', backend='cpu',
                binary_sha256=digest(executable), prompt_manifest_sha256=digest(prompts),
                verification={'ubatch': 32, 'mode': 'block'}, sampling={'temperature': 0, 'top_k': 1},
                numerical_floor=0.01, decision_rule='inconclusive pending scientific controls',
                cells=[dict(cell_id='q8', prompt_id='heldout', seed=42, repetition=0,
                            target_quant='Q8_0', target_sha256='b'*64)],
                runner={'argv': [sys.executable, str(Path(worker.__file__).resolve())], 'timeout_s': 10},
                native_worker={'executable': str(executable), 'env': {'LD_LIBRARY_PATH': str(tmp_path)},
                               'prompt_manifest': str(prompts), 'targets': {'Q8_0': '/prepared/target.gguf'},
                               'drafter': '/prepared/drafter.gguf', 'timeout_s': 5})
    path = write(tmp_path / 'plan.json', plan)
    return path, tmp_path / 'cell.json'


def test_native_process_request_denominators_and_divergence(native):
    plan, out = native
    value = worker.run_cell(plan, 'q8', out)
    assert value['status'] == 'ok'
    assert value['accepted'] == 1 and value['drafted'] == 2
    assert value['positions'] == [dict(position=0, accepted=1, drafted=1),
                                  dict(position=1, accepted=0, drafted=1)]
    assert value['numerical_divergence'] == {'max_abs': 0.5, 'rms': pytest.approx(1/6)}
    assert value['request']['case']['seed'] == 42
    assert len(value['native_artifacts']) == 4
    with pytest.raises(FileExistsError):
        worker.run_cell(plan, 'q8', out)


def test_end_to_end_runner_retains_and_replays_native_trace(native):
    spec = importlib.util.spec_from_file_location('precision_worker_runner', Path(worker.__file__).with_name('runner.py'))
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    plan, out = native
    final = runner.run_matrix(plan, out.parent / 'matrix')
    assert final['counts']['ok'] == 1
    assert final['weighted_acceptance'] == 0.5
    assert final['causal_gate'] == 'UNRESOLVED'
    worker.capture.read_precision(out.parent / 'matrix/final.json')
    trace_path = out.parent / 'matrix/0.raw.native/trace.json'
    trace_path.write_text('{}')
    with pytest.raises(ValueError, match='artifact bytes changed'):
        worker.capture.read_precision(out.parent / 'matrix/final.json')


@pytest.fixture
def traced(native):
    plan, out = native
    worker.run_cell(plan, 'q8', out)
    trace = json.loads(out.with_suffix('.native').joinpath('trace.json').read_text())
    return trace, trace['request']


@pytest.mark.parametrize('change', [
    lambda t: t.update(request={}),
    lambda t: t.update(spec_type='draft-mtp'),
    lambda t: t.update(blocks=[]),
    lambda t: t['blocks'].append(copy.deepcopy(t['blocks'][0])),
    lambda t: t['blocks'][0].update(accepted=3),
    lambda t: t['blocks'][0].update(accepted=True),
    lambda t: t['blocks'][0].update(accepted=0),
    lambda t: t['blocks'][0].update(logits=[]),
    lambda t: t['blocks'][0]['logits'][0].update(serial_prefix=[99]),
    lambda t: t['blocks'][0]['logits'][1].update(verify_prefix=[8], serial_prefix=[8]),
    lambda t: t['blocks'][0]['logits'][0].update(serial=[0]),
    lambda t: t['blocks'][0]['logits'][0]['verify'].__setitem__(0, float('nan')),
    lambda t: t['blocks'][0]['logits'][0]['verify'].__setitem__(0, True),
])
def test_trace_refuses_missing_or_contradictory_native_evidence(traced, change):
    trace, request = traced
    request = copy.deepcopy(request)
    change(trace)
    with pytest.raises(ValueError):
        worker.reduce_trace(trace, request)


def test_stochastic_equality_cannot_stand_for_acceptance(traced):
    trace, request = traced
    request['settings']['sampling']['temperature'] = 1
    with pytest.raises(ValueError, match='greedy'):
        worker.reduce_trace(trace, request)


def test_variable_width_blocks_use_real_position_denominators(traced):
    trace, request = traced
    block = copy.deepcopy(trace['blocks'][0])
    block.update(block=1, draft_tokens=[1], accepted=1)
    block['logits'] = block['logits'][:2]
    for i, row in enumerate(block['logits']):
        row['verify_prefix'] = row['serial_prefix'] = [2, 1, 1, 1] + [1] * i
    trace['blocks'].append(block)
    result = worker.reduce_trace(trace, request)
    assert result['accepted'] == 2 and result['drafted'] == 3
    assert result['positions'] == [dict(position=0, accepted=2, drafted=2),
                                   dict(position=1, accepted=0, drafted=1)]
    block['logits'][0]['verify_prefix'] = block['logits'][0]['serial_prefix'] = [99]
    with pytest.raises(ValueError, match='accepted continuation'):
        worker.reduce_trace(trace, request)


def test_seed_drift_and_missing_numerical_control_refused(traced):
    trace, request = traced
    changed = copy.deepcopy(request)
    changed['case']['seed'] += 1
    with pytest.raises(ValueError, match='echo mismatch'):
        worker.reduce_trace(trace, changed)
    trace['blocks'][0]['logits'][0].pop('serial')
    with pytest.raises(KeyError):
        worker.reduce_trace(trace, request)


@pytest.mark.parametrize('status', ['failed', 'invalid', 'abstained'])
def test_native_terminal_status_retained(traced, status):
    trace, request = traced
    trace.update(status=status, error='explicit native reason')
    value = worker.reduce_trace(trace, request)
    assert value == {'status': status, 'error': 'explicit native reason'}


@pytest.mark.parametrize('change', [
    lambda p: p.update(prompt_manifest_sha256='c'*64),
    lambda p: p.update(binary_sha256='c'*64),
    lambda p: p['native_worker'].update(env={}),
    lambda p: p['native_worker'].update(executable='relative/path'),
    lambda p: p['native_worker'].update(timeout_s=-1),
    lambda p: p['native_worker'].update(extra_flags=['--override']),
])
def test_admission_binding_refused_before_execution(native, change):
    plan, out = native
    value = json.loads(plan.read_text())
    change(value)
    write(plan, value)
    result = worker.run_cell(plan, 'q8', out)
    assert result['status'] == 'invalid'
    assert not out.with_suffix('.native').exists()


@pytest.mark.parametrize('mode', ['nonzero', 'malformed', 'missing'])
def test_failed_native_process_retains_original_bytes(native, mode):
    plan, out = native
    p = json.loads(plan.read_text())
    executable = Path(p['native_worker']['executable'])
    source = f'#!{sys.executable}\nimport sys, pathlib\n'
    if mode == 'malformed':
        source += "pathlib.Path(sys.argv[-1]).write_text('malformed native bytes')\n"
    elif mode == 'nonzero':
        source += 'sys.exit(7)\n'
    executable.write_text(source)
    p['binary_sha256'] = digest(executable)
    write(plan, p)
    result = worker.run_cell(plan, 'q8', out)
    assert result['status'] == ('failed' if mode == 'nonzero' else 'invalid')
    assert result['native_artifacts']
    if mode == 'malformed':
        assert out.with_suffix('.native').joinpath('trace.json').read_text() == 'malformed native bytes'
