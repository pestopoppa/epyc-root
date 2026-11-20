"""Model-free native matrix admission/refusal tests; no model measurements."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('admission_capture_test', Path(__file__).with_name('capture.py'))
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True))
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def make_panel(tmp_path):
    libraries = {'/prepared/libllama.so': '1' * 64}
    plan = {k: 'a' * 64 for k in capture.SHARED if k.endswith('_sha256')}
    plan.update(origin='native_claimed', run_id='test', backend='cpu',
                verification={'replay': 'fresh-block-serial-v1', 'mode': 'block', 'blocks': 1},
                sampling={'temperature': 0, 'top_k': 1}, numerical_floor=.01,
                decision_rule='inconclusive unless all controls pass',
                libraries_sha256=hashlib.sha256(json.dumps(libraries, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                cells=[dict(cell_id=q, prompt_id='held', seed=42, repetition=0,
                            target_quant=q, target_sha256=str(i)*64)
                       for i, q in enumerate(('BF16', 'Q8_0', 'Q4_K_M'), 1)])
    base = {'repo': 'test/model', 'revision': 'b' * 40}
    weights = {'base': base, 'targets': {c['target_quant']: dict(
        sha256=c['target_sha256'], base=base, tensor_correspondence='verified',
        conversion_sha256='c'*64, catalog_sha256='d'*64, path='/prepared/'+c['target_quant']+'.gguf') for c in plan['cells']},
        'drafter': dict(sha256=plan['drafter_sha256'], target_base=base, training_dtype='BF16', path='/prepared/draft.gguf')}
    plan['prompt_manifest_sha256'] = save(tmp_path/'prompts.json', {'prompts': {'calibration': 'calibration prompt'}})['sha256']
    plan['native_worker'] = dict(prompt_manifest=str(tmp_path/'prompts.json'), targets={q: v['path'] for q, v in weights['targets'].items()},
                                 drafter=weights['drafter']['path'], env={'LD_LIBRARY_PATH': '/prepared/libs'})
    build = {k: plan[k] for k in ('backend', 'binary_sha256', 'source_sha256', 'libraries_sha256')}
    build.update(source_commit='e'*40, libraries=libraries, ld_library_path='/prepared/libs')
    holdout = dict(schema='epyc.target-precision.holdout.v1',
                   evaluation=[['held', 42]], calibration=[['calibration', 3]],
                   prompt_manifest_sha256=plan['prompt_manifest_sha256'], protocol_sha256=plan['protocol_sha256'])
    plan['holdout_sha256'] = save(tmp_path/'holdout.json', holdout)['sha256']
    floor = {k: plan[k] for k in ('backend', 'binary_sha256', 'source_sha256', 'libraries_sha256', 'drafter_sha256', 'verification', 'sampling')}
    floor['controls'] = []
    for c in plan['cells']:
        control = dict(target_quant=c['target_quant'], target_sha256=c['target_sha256'],
                       comparison='fresh-block-vs-serial-same-prefix', repetitions=2, coordinates=200,
                       max_abs=.005, rms=.002)
        control['trace_outputs'] = []
        for repetition in range(2):
            case = dict(c, prompt_id='calibration', seed=3, repetition=repetition)
            request = dict(schema='epyc.target-precision.native-trace.v1', case=case,
                           settings={k: plan[k] for k in capture.SHARED}, prompt='calibration prompt',
                           runtime=plan['native_worker'],
                           trace_semantics='greedy_prefix_acceptance_and_same_prefix_verify_vs_serial_logits')
            rows = [dict(verify_prefix=prefix, serial_prefix=prefix,
                         witness=dict(count=50, verify_argmax=1, max_abs=.005, sum_squared=.0002))
                    for prefix in ([2], [2, 1])]
            trace = dict(request=request, status='ok', spec_type='draft-dflash',
                         numerical_encoding='full-vocabulary-moments-v1',
                         blocks=[dict(block=0, draft_tokens=[1], accepted=1, logits=rows)])
            samples = [dict(pid=2, start_ticks=1, monotonic_ns=t,
                            libraries={p: dict(sha256=h, device=0, inode=1) for p, h in libraries.items()},
                            maps='0-1 r-xp 00000000 00:00 1 /prepared/libllama.so') for t in (1, 2)]
            observed = dict(schema='epyc.target-precision.runtime.v1', request=request,
                            owner_pid=1, child_pid=2, returncode=0, samples=samples)
            control['trace_outputs'].append(dict(
                trace=save(tmp_path/f'{c["target_quant"]}-{repetition}-trace.json', trace),
                runtime=save(tmp_path/f'{c["target_quant"]}-{repetition}-runtime.json', observed)))
        control['native_output'] = save(tmp_path/(c['target_quant']+'.json'), control)
        floor['controls'].append(control)
    holdout = dict(evaluation=[['held', 42]], calibration=[['calibration', 3]],
                   prompt_manifest_sha256=plan['prompt_manifest_sha256'], protocol_sha256=plan['protocol_sha256'])
    records = dict(weights=weights, build=build, floor=floor, holdout=holdout)
    plan['admission'] = {'runtime_proof': dict(sampling_window='during-each-cell',
                                              mapped_library_sha256=libraries, own_pid=True)}
    for key, value in records.items():
        value['schema'] = 'epyc.target-precision.'+key+'.v1'
        plan['admission'][key] = save(tmp_path/(key+'.json'), value)
    plan['holdout_sha256'] = plan['admission']['holdout']['sha256']
    return plan, records, tmp_path


@pytest.fixture
def panel(tmp_path):
    return make_panel(tmp_path)


def reseal(panel, key):
    plan, records, directory = panel
    plan['admission'][key] = save(directory/(key+'.json'), records[key])
    if key == 'holdout':
        plan['holdout_sha256'] = plan['admission'][key]['sha256']


def test_complete_declarations_admit_without_model_reads(panel):
    capture._plan(panel[0])
    capture.admit_native(panel[0])  # /prepared models do not exist; never read/hashed


@pytest.mark.parametrize('key', ['weights', 'build', 'floor', 'holdout', 'runtime_proof'])
def test_missing_receipts_refuse(panel, key):
    panel[0]['admission'].pop(key)
    with pytest.raises(ValueError, match='native admission'):
        capture.admit_native(panel[0])


@pytest.mark.parametrize('key,change', [
    ('weights', lambda r: r['targets']['Q8_0'].update(base={'repo': 'other', 'revision': 'f'*40})),
    ('weights', lambda r: r['targets']['Q4_K_M'].update(tensor_correspondence='unknown')),
    ('weights', lambda r: r['drafter'].update(training_dtype='Q8_0')),
    ('weights', lambda r: r['drafter'].update(sha256='f'*64)),
    ('weights', lambda r: r['targets']['BF16'].pop('conversion_sha256')),
    ('build', lambda r: r.update(backend='hip')),
    ('build', lambda r: r.update(source_commit='main')),
    ('build', lambda r: r.update(binary_sha256='f'*64)),
    ('build', lambda r: r['libraries'].update({'/prepared/foreign.so': 'f'*64})),
    ('build', lambda r: r.update(ld_library_path='/foreign')),
    ('floor', lambda r: r.update(verification={'mode': 'serial'})),
    ('floor', lambda r: r.update(backend='hip')),
    ('floor', lambda r: r['controls'].pop()),
    ('floor', lambda r: r['controls'][0].update(comparison='unmatched-prefix')),
    ('floor', lambda r: r['controls'][0].update(repetitions=1)),
    ('floor', lambda r: r['controls'][0].update(coordinates=0)),
    ('floor', lambda r: r['controls'][0].update(max_abs=.02)),
    ('floor', lambda r: r['controls'][0].update(rms=float('nan'))),
    ('floor', lambda r: r['controls'][0].update(rms=.009)),
    ('floor', lambda r: r['controls'][0].update(target_sha256='f'*64)),
    ('floor', lambda r: r['controls'][0].pop('native_output')),
    ('floor', lambda r: r['controls'][0].update(max_abs=.004)),
    ('holdout', lambda r: r.update(calibration=[['held', 42]])),
    ('holdout', lambda r: r.update(evaluation=[])),
])
def test_bound_but_inadequate_controls_refuse(panel, key, change):
    change(panel[1][key])
    reseal(panel, key)
    with pytest.raises(ValueError):
        capture.admit_native(panel[0])


def test_tampered_original_floor_refuses(panel):
    Path(panel[1]['floor']['controls'][0]['native_output']['path']).write_text('{}')
    with pytest.raises(ValueError, match='original digest'):
        capture.admit_native(panel[0])


def test_native_matrix_refuses_before_directory_or_subprocess(panel, monkeypatch):
    plan, _, directory = panel
    plan.pop('admission')
    path = directory/'plan.json'
    save(path, plan)
    runner_spec = importlib.util.spec_from_file_location('admission_runner_test', Path(__file__).with_name('runner.py'))
    runner = importlib.util.module_from_spec(runner_spec)
    runner_spec.loader.exec_module(runner)
    monkeypatch.setattr(runner.subprocess, 'run', lambda *a, **k: pytest.fail('must not execute'))
    with pytest.raises(ValueError, match='missing admission'):
        runner.run_matrix(path, directory/'matrix')
    assert not (directory/'matrix').exists()


@pytest.mark.parametrize('change', [
    lambda p: p['cells'].pop(),
    lambda p: p['cells'][1].update(seed=43),
    lambda p: p['native_worker']['targets'].update(Q8_0='/other.gguf'),
    lambda p: p['admission']['runtime_proof'].update(sampling_window='after'),
    lambda p: p['admission']['runtime_proof'].update(own_pid=False),
])
def test_matrix_and_runtime_binding_refusals(panel, change):
    change(panel[0])
    with pytest.raises(ValueError, match='native admission'):
        capture.admit_native(panel[0])


def test_hip_requires_own_process_vram_and_kfd_plan(panel):
    plan, records, _ = panel
    plan['backend'] = 'hip'
    for key in ('build', 'floor'):
        records[key]['backend'] = 'hip'
        reseal(panel, key)
    with pytest.raises(ValueError, match='HIP residency'):
        capture.admit_native(plan)
    plan['admission']['runtime_proof'].update(kfd_process=True, nonzero_vram=True)
    with pytest.raises(ValueError, match='floor plan setting mismatch: backend'):
        capture.admit_native(plan)  # CPU originals cannot qualify HIP controls


def test_worker_refuses_unadmitted_native_before_subprocess(panel, monkeypatch):
    plan, _, directory = panel
    plan.pop('admission')
    path = directory/'plan.json'
    save(path, plan)
    spec = importlib.util.spec_from_file_location('admission_worker_test', Path(__file__).with_name('worker.py'))
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    monkeypatch.setattr(worker.subprocess, 'run', lambda *a, **k: pytest.fail('must not execute'))
    result = worker.run_cell(path, 'BF16', directory/'output.json')
    assert result['status'] == 'invalid'
    assert 'missing admission' in result['error']
    assert not (directory/'output.native').exists()


def test_grouped_precision_arms_refuse(panel):
    plan, _, _ = panel
    import copy
    second = copy.deepcopy(plan['cells'])
    for c in second:
        c.update(cell_id=c['cell_id']+'-2', repetition=1)
    plan['cells'] += second
    plan['cells'].sort(key=lambda c: c['target_quant'])
    with pytest.raises(ValueError, match='interleaved'):
        capture.admit_native(plan)
