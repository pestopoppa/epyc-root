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
