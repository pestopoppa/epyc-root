"""Model-free request preparation; never executes a producer or opens weights."""
import copy
import json

import pytest

from prepare_floor import prepare
from test_admission import make_panel, reseal, save
from test_floor import floor


def prepared_panel(tmp_path):
    panel = make_panel(tmp_path)
    plan, _, _ = panel
    # No floor exists yet: preparation must not introduce a circular dependency.
    plan['admission'].pop('floor')
    path = tmp_path/'plan.json'
    save(path, plan)
    return panel, path


@pytest.mark.parametrize('quant', ['BF16', 'Q8_0', 'Q4_K_M'])
def test_prepare_binds_plan_and_replays_without_floor(tmp_path, quant):
    (plan, _, _), path = prepared_panel(tmp_path)
    original = copy.deepcopy(plan)
    result = prepare(path, quant, 'calibration', 3, 3)
    requests = result['requests']
    assert len(requests) == 3
    assert len({r['case']['cell_id'] for r in requests}) == 3
    for i, request in enumerate(requests):
        assert request['plan_sha256'] == save(tmp_path/'same-plan.json', plan)['sha256']
        assert request['run_id'] == plan['run_id']
        assert request['case']['target_quant'] == quant
        assert request['case']['repetition'] == i
        assert request['prompt'] == 'calibration prompt'
    floor.validate_requests(plan, json.loads(json.dumps(requests)), floor._module('capture')._read)
    assert plan == original
    assert result == prepare(path, quant, 'calibration', 3, 3)


@pytest.mark.parametrize('quant,prompt,seed,repetitions', [
    ('unknown', 'calibration', 3, 2), ('BF16', 'held', 42, 2),
    ('BF16', 'calibration', 99, 2), ('BF16', 'calibration', True, 2),
    ('BF16', 'calibration', -1, 2), ('BF16', 'calibration', 2**32, 2),
    ('BF16', 'calibration', 3, 1), ('BF16', 'calibration', 3, True),
    ('BF16', 'calibration', 3, 101),
])
def test_refuses_undeclared_or_unbounded_cases(tmp_path, quant, prompt, seed, repetitions):
    _, path = prepared_panel(tmp_path)
    with pytest.raises(ValueError):
        prepare(path, quant, prompt, seed, repetitions)


def test_refuses_evaluation_overlap_even_with_resealed_receipt(tmp_path):
    panel, path = prepared_panel(tmp_path)
    panel[1]['holdout']['calibration'].append(['held', 42])
    reseal(panel, 'holdout')
    save(path, panel[0])
    with pytest.raises(ValueError):
        prepare(path, 'BF16', 'held', 42, 2)


@pytest.mark.parametrize('receipt', ['weights', 'build', 'holdout'])
def test_refuses_changed_prerequisite_before_output(tmp_path, receipt):
    (plan, _, _), path = prepared_panel(tmp_path)
    from pathlib import Path
    Path(plan['admission'][receipt]['path']).write_text('{}')
    with pytest.raises(ValueError):
        prepare(path, 'BF16', 'calibration', 3, 2)
