import importlib.util
import json
import shutil
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
CMP2 = HERE.parent / 'toc-cmp-2-governance'

@pytest.fixture
def runner(tmp_path, monkeypatch):
    shutil.copy2(HERE / 'runner.py', tmp_path / 'runner.py')
    shutil.copy2(CMP2 / 'runner.py', tmp_path / 'cmp2_runner.py')
    spec = importlib.util.spec_from_file_location('cmp3_test_runner', tmp_path / 'runner.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixed_counterbalanced_matrix(runner):
    cases = json.loads((CMP2 / 'cases.json').read_text())
    trials = runner.schedule(cases)
    assert len(trials) == len({t['unit'] for t in trials}) == 36
    for case in cases:
        for arm in ('baseline_summary_only', 'contract_summary_only', 'contract_verbatim_manifest'):
            rows = [t for t in trials if t['rule_id'] == case['id'] and t['arm'] == arm]
            assert {tuple(t['order']) for t in rows} == {('sibling', 'protected'), ('protected', 'sibling')}
            assert {t['rubric'] for t in rows} == ({'X'} if arm.startswith('baseline') else {'W'})


def test_frozen_prompt_retention_mismatch_fails_closed(runner):
    case = json.loads((CMP2 / 'cases.json').read_text())[0]
    trial = runner.schedule([case])[0]
    (runner.HERE / 'renders.json').write_text(json.dumps({case['id']: {trial['arm']: case['rule'] if trial['rubric'] == 'X' else 'missing'}}))
    with pytest.raises(ValueError, match='retention mismatch'):
        runner.prior_messages(case, trial)


def test_candidate_identity_failure(runner, monkeypatch):
    monkeypatch.setattr(runner, 'original_verify', lambda manifest: [])
    monkeypatch.setattr(runner.subprocess, 'check_output', lambda *args, **kwargs: 'wrong\n')
    with pytest.raises(ValueError, match='base mismatch'):
        runner.verify_inputs({'candidate_base': 'expected'})


def test_predicates_preserve_unknown_and_sibling_headroom(runner):
    case = json.loads((CMP2 / 'cases.json').read_text())[0]
    result = runner.base.score(case, ['protected', 'sibling'], [[], []])
    assert result['outcome'] == 'no_sibling_headroom'
    assert not result['protected_attempt']


@pytest.mark.parametrize("allocated,threads,expected", [
    ({0, 1, 2, 3, 96, 97, 98, 99}, "4", [0, 1, 2, 3]),
    ({0, 1, 2, 3}, "4", [0, 1, 2, 3]),
    ({96, 97, 98, 99}, "4", [96, 97, 98, 99]),
    ({0, 1, 2, 96, 97, 98}, "4", None),
    ({0, 1, 2, 3}, "3", None),
])
def test_grant_affinity_binding(runner, monkeypatch, allocated, threads, expected):
    current = set(allocated)
    def bind(_pid, cpus):
        nonlocal current
        assert set(cpus) <= current
        current = set(cpus)
    monkeypatch.setenv("FILLER_THREADS", threads)
    monkeypatch.setattr(runner.base.os, "sched_getaffinity", lambda _: current)
    monkeypatch.setattr(runner.base.os, "sched_setaffinity", bind)
    if expected is None:
        with pytest.raises(ValueError):
            runner.base.bind_four_cores()
    else:
        assert runner.base.bind_four_cores() == expected
        assert current == set(expected)
