"""Model-free prospective writer and refusal tests; no precision evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('precision_capture', Path(__file__).with_name('capture.py'))
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


def write(path, obj):
    path.write_text(json.dumps(obj))
    return path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def panel(tmp_path):
    plan = {key: 'a' * 64 for key in capture.SHARED if key.endswith('_sha256')}
    plan.update(run_id='run-1', origin='synthetic', backend='cpu', verification={'ubatch': 32, 'mode': 'block'},
                sampling={'temperature': 0, 'top_k': 1}, numerical_floor=0.01,
                decision_rule='inconclusive until matched-weight and floor controls pass',
                cells=[dict(cell_id=q, prompt_id='p1', seed=42, repetition=0,
                            target_quant=q, target_sha256='b' * 64)
                       for q in ('BF16', 'Q8_0', 'Q4_K_M')])
    pp = write(tmp_path / 'plan.json', plan)
    opened = tmp_path / 'opened.json'
    capture.open_capture(pp, opened)
    cells = []
    for i, case in enumerate(plan['cells']):
        telemetry = dict(positions=[{'position': 0, 'accepted': i, 'drafted': i + 1}],
                         accepted=i, drafted=i + 1, numerical_divergence={'max_abs': 0.002})
        raw = write(tmp_path / f'raw{i}.json', telemetry)
        native = dict(run_id=plan['run_id'], plan_sha256=sha(pp), cell_id=case['cell_id'],
                      case=case, settings={key: plan[key] for key in capture.SHARED},
                      status='ok', raw_output_path=str(raw), raw_output_sha256=sha(raw), **telemetry)
        cells.append(write(tmp_path / f'cell{i}.json', native))
    return pp, opened, cells, tmp_path / 'final.json'


def finish(panel):
    return capture.finalize_precision(panel[1], panel[2], panel[3])


def mutate(path, change):
    value = json.loads(path.read_text())
    change(value)
    write(path, value)


def test_real_writer_weighted_and_distinct_cases(panel):
    result = finish(panel)
    assert result['weighted_acceptance'] == 3 / 6  # not the mean of per-cell ratios
    assert result['counts'] == dict(ok=3, failed=0, invalid=0, abstained=0)
    assert len({v['native']['cell_id'] for v in result['cells']}) == 3
    assert result['by_quant']['Q8_0'] == {'accepted': 1, 'drafted': 2}
    assert result['causal_gate'] == 'UNRESOLVED'
    assert result['projection_ready'] is False
    with pytest.raises(FileExistsError):
        finish(panel)


@pytest.mark.parametrize('status', ['failed', 'invalid', 'abstained'])
def test_failure_is_retained_without_imputed_counts(panel, status):
    def fail(cell):
        for key in ('positions', 'accepted', 'drafted', 'numerical_divergence'):
            cell.pop(key)
        cell.update(status=status, error='native decode failed', raw_output_path=None, raw_output_sha256=None)
    mutate(panel[2][0], fail)
    result = finish(panel)
    assert result['counts'][status] == 1
    assert 'accepted' not in result['cells'][0]['native']
    assert result['weighted_acceptance'] == 3 / 5


@pytest.mark.parametrize('key,value', [
    ('drafter_sha256', 'c' * 64), ('backend', 'hip'),
    ('binary_sha256', 'c' * 64), ('verification', {'ubatch': 1}),
    ('sampling', {'temperature': 1}), ('holdout_sha256', 'c' * 64)])
def test_changed_native_settings_refuse(panel, key, value):
    mutate(panel[2][0], lambda c: c['settings'].update({key: value}))
    with pytest.raises(ValueError, match='settings mismatch'):
        finish(panel)


@pytest.mark.parametrize('change', [
    lambda c: c.pop('settings'), lambda c: c.update(plan_sha256='c' * 64),
    lambda c: c.update(run_id='other'), lambda c: c['case'].update(seed=43),
    lambda c: c.update(accepted=999), lambda c: c.update(numerical_divergence=None),
    lambda c: c.update(positions=[]), lambda c: c.update(raw_output_path=None),
    lambda c: c.update(status='failed', error=None),
])
def test_missing_or_contradictory_native_fields_refuse(panel, change):
    mutate(panel[2][0], change)
    with pytest.raises(ValueError):
        finish(panel)
    assert not panel[3].exists()


def test_raw_bytes_changed_refuse(panel):
    raw = Path(json.loads(panel[2][0].read_text())['raw_output_path'])
    raw.write_text('{}')
    with pytest.raises(ValueError, match='bytes changed'):
        finish(panel)


def test_plan_bytes_changed_refuse(panel):
    panel[0].write_text(panel[0].read_text() + '\n')
    with pytest.raises(ValueError, match='plan bytes changed'):
        finish(panel)


def test_missing_cell_refuses(panel):
    panel[2].pop()
    with pytest.raises(ValueError, match='missing planned'):
        finish(panel)


def test_duplicate_cell_refuses(panel):
    panel[2].append(panel[2][0])
    with pytest.raises(ValueError, match='duplicate cell'):
        finish(panel)


def test_duplicate_case_refuses_before_open(panel):
    plan = json.loads(panel[0].read_text())
    twin = copy.deepcopy(plan['cells'][0])
    twin['cell_id'] = 'duplicate-with-new-id'
    plan['cells'].append(twin)
    write(panel[0], plan)
    with pytest.raises(ValueError, match='duplicate cell or case'):
        capture.open_capture(panel[0], panel[3])


def test_missing_shared_setting_refuses_before_open(panel):
    mutate(panel[0], lambda p: p.pop('holdout_sha256'))
    with pytest.raises(ValueError, match='missing plan field'):
        capture.open_capture(panel[0], panel[3])


def test_symlink_raw_refuses(panel):
    raw = Path(json.loads(panel[2][0].read_text())['raw_output_path'])
    target = raw.with_suffix('.target')
    raw.rename(target)
    raw.symlink_to(target)
    with pytest.raises((ValueError, OSError)):
        finish(panel)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def integrated(panel, tmp_path):
    runner = load_module('precision_runner_test', Path(__file__).with_name('runner.py'))
    worker = tmp_path / 'worker.py'
    worker.write_text('''import argparse, hashlib, json, pathlib, sys, os
sys.path.insert(0, str(pathlib.Path.cwd()))
from scripts.vidya.qwen4exp_quality_capture import stable_bytes_identity
p=argparse.ArgumentParser()
p.add_argument('--plan'); p.add_argument('--cell-id'); p.add_argument('--output')
a=p.parse_args(); plan=json.loads(pathlib.Path(a.plan).read_text())
assert pathlib.Path(a.output).with_name('opened.json').exists()
mode=plan['runner'].get('test_mode', 'ok')
if mode == 'missing': sys.exit(2)
if mode == 'malformed': pathlib.Path(a.output).write_text('broken'); sys.exit(0)
if mode in ('failed', 'invalid', 'abstained'):
    value={'status':mode,'error':'test native failure'}
else:
    value={'status':'ok', 'positions':[{'position':0,'accepted':1,'drafted':2}],
           'accepted':1,'drafted':2,'numerical_divergence':{'max_abs':0.001}}
value['request']={'plan_sha256':hashlib.sha256(pathlib.Path(a.plan).read_bytes()).hexdigest(),
                  'case':next(c for c in plan['cells'] if c['cell_id']==a.cell_id),
                  'settings':{k:plan[k] for k in ('drafter_sha256','backend','binary_sha256','libraries_sha256',
                    'verification','sampling','prompt_manifest_sha256','holdout_sha256','protocol_sha256',
                    'source_sha256','decision_rule','numerical_floor')}, 'runtime':plan['native_worker']}
if value['status']=='ok' and mode != 'no-proof':
    libraries=plan['admission']['runtime_proof']['mapped_library_sha256']
    # Fabricated process observations for replay/refusal tests, never measurements.
    sample=dict(pid=os.getpid(),start_ticks=12,libraries={p:dict(sha256=s,device=1,inode=2) for p,s in libraries.items()},
                maps=''.join('1-2 r-xp 0 00:01 2 '+p+'\\n' for p in libraries),kfd_registered=False,vram={})
    proof=dict(schema='epyc.target-precision.runtime.v1',request=value['request'],owner_pid=os.getppid(),child_pid=os.getpid(),
               returncode=0,samples=[dict(sample,monotonic_ns=t) for t in (1,2)])
    proof_path=pathlib.Path(a.output).with_suffix('.runtime.json')
    proof_path.write_text(json.dumps(proof))
    value['runtime_proof']=stable_bytes_identity(proof_path)[1]
    value['native_artifacts']=[value['runtime_proof']]
pathlib.Path(a.output).write_text(json.dumps(value))
if mode == 'nonzero': sys.exit(3)
''')
    admission_fixture = load_module('precision_admission_fixture', Path(__file__).with_name('test_admission.py'))
    plan, _, _ = admission_fixture.make_panel(tmp_path)
    plan.update(origin='native_claimed', measurement_labels=dict(
        id_prefix='test-only', date='2026-11-20', category='CANDIDATE',
        claim='successful-cell acceptance in the declared precision panel'))
    plan['runner'] = {'argv': [sys.executable, str(worker)], 'timeout_s': 10}
    pp = write(tmp_path / 'runner-plan.json', plan)
    dest = tmp_path / 'run'
    return runner, pp, dest


def projection():
    from scripts.vidya.adapters import target_precision
    return target_precision


def test_runner_original_discovery_and_shared_grade(integrated):
    runner, plan, dest = integrated
    result = runner.run_matrix(plan, dest)
    assert result['counts']['ok'] == 3
    assert result['weighted_acceptance'] == 0.5
    adapter = projection()
    rows = adapter.native_rows(dest / 'final.json')
    assert len(rows) == 3
    from claim_tuple import grade
    for row in rows:
        claim = adapter.project(row)
        assert claim.value == 0.5
        assert claim.metric_direction == 'higher_better'
        assert claim.protocol_id == '' and claim.reps is None
        assert grade(claim)[0] == 'Judged'
        assert claim.extra['causal_gate'] == 'UNRESOLVED'
    with pytest.raises(FileExistsError):
        runner.run_matrix(plan, dest)


def test_closure_refuses_edited_runtime_original(integrated):
    runner, plan, dest = integrated
    result = runner.run_matrix(plan, dest)
    proof = result['cells'][0]['native']['runtime_proof']
    Path(proof['path']).write_text('{}')
    with pytest.raises(ValueError, match='artifact bytes changed'):
        runner.capture.read_precision(dest / 'final.json')


@pytest.mark.parametrize('mode,status', [('failed','failed'), ('invalid','invalid'),
    ('abstained','abstained'), ('missing','failed'), ('nonzero','failed'), ('malformed','invalid'), ('no-proof','invalid')])
def test_runner_retains_all_terminal_cells(integrated, mode, status):
    runner, plan, dest = integrated
    mutate(plan, lambda p: p['runner'].update(test_mode=mode))
    result = runner.run_matrix(plan, dest)
    assert result['counts'][status] == 3
    assert len(result['cells']) == 3
    assert result['weighted_acceptance'] is None
    assert projection().native_rows(dest / 'final.json') == ()
    for row in result['cells']:
        assert row['native']['error']
        assert row['native']['native_artifacts']
        assert 'accepted' not in row['native']
    capture.read_precision(dest / 'final.json')


@pytest.mark.parametrize('part', ['raw', 'cell', 'opening', 'plan', 'stdout', 'summary', 'metric'])
def test_projection_refuses_changed_originals(integrated, part):
    runner, plan, dest = integrated
    runner.run_matrix(plan, dest)
    adapter = projection()
    rows = adapter.native_rows(dest / 'final.json')
    paths = {'raw': dest/'0.raw.json', 'cell': dest/'0.cell.json',
             'opening': dest/'opened.json', 'plan': plan, 'stdout': dest/'0.stdout'}
    if part in paths:
        with paths[part].open('a') as stream:
            stream.write(' ')
    elif part == 'summary':
        mutate(dest/'final.json', lambda r: r.update(weighted_acceptance=1.0))
    else:
        mutate(dest/'final.json', lambda r: r['measurements'][0].update(value=1.0))
    with pytest.raises(ValueError):
        adapter.native_rows(dest / 'final.json')
    with pytest.raises(ValueError):
        adapter.project(rows[0])


@pytest.mark.parametrize('part', ['raw', 'cell', 'opening', 'plan'])
def test_discovery_refuses_lost_originals(integrated, part):
    runner, plan, dest = integrated
    runner.run_matrix(plan, dest)
    {'raw':dest/'0.raw.json', 'cell':dest/'0.cell.json',
     'opening':dest/'opened.json', 'plan':plan}[part].unlink()
    with pytest.raises(ValueError):
        projection().native_rows(dest / 'final.json')


def test_synthetic_origin_and_absent_labels_emit_no_rows(integrated):
    runner, plan, dest = integrated
    mutate(plan, lambda p: p.update(origin='synthetic'))
    runner.run_matrix(plan, dest)
    assert projection().native_rows(dest / 'final.json') == ()
    mutate(plan, lambda p: (p.update(origin='native_claimed'), p.pop('measurement_labels')))
    runner.run_matrix(plan, dest.with_name('unlabelled'))
    assert projection().native_rows(dest.with_name('unlabelled') / 'final.json') == ()


def test_foreign_metric_and_fabricated_values_refuse(integrated):
    runner, plan, dest = integrated
    runner.run_matrix(plan, dest)
    adapter = projection()
    row = adapter.native_rows(dest / 'final.json')[0]
    with pytest.raises(ValueError):
        adapter.project(dict(row, measurement_id='foreign'))
    with pytest.raises(ValueError):
        adapter.project(dict(row, value=100))


def test_runner_timeout_retained_and_bad_command_refused(integrated):
    runner, plan, dest = integrated
    mutate(plan, lambda p: p['runner'].update(timeout_s=0.000001))
    result = runner.run_matrix(plan, dest)
    assert result['counts']['failed'] == 3
    capture.read_precision(dest / 'final.json')
    mutate(plan, lambda p: p['runner'].update(argv='shell command'))
    with pytest.raises(ValueError, match='argv or timeout'):
        runner.run_matrix(plan, dest.with_name('bad'))
    assert not dest.with_name('bad').exists()


def test_discovery_refuses_symlink_original(integrated):
    runner, plan, dest = integrated
    runner.run_matrix(plan, dest)
    raw = dest / '0.raw.json'
    other = dest / 'saved.json'
    raw.rename(other)
    raw.symlink_to(other)
    with pytest.raises(ValueError):
        projection().native_rows(dest / 'final.json')
