"""Task-native projection: native semantic refusals, partial costs and recipient canary."""
import json
import shutil
from pathlib import Path

import pytest
import test_toc_ab_cf3c as base

cf, ct = base.cf, base.ct
REAL = Path('/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-task/native')
pytestmark = pytest.mark.skipif(not (REAL / 'RESULT.json').is_file(), reason='native task window absent')


@pytest.fixture
def fx(tmp_path):
    result = json.loads((REAL / 'RESULT.json').read_text())
    window = tmp_path / 'native' / Path(result['window']).name
    shutil.copytree(REAL / window.name, window)
    (tmp_path / 'packet').symlink_to(REAL.parent / 'packet', target_is_directory=True)
    return base._seal(window.parent, window, result), window


def _save(path, window, result, cell):
    folder = window / f"task-{cell['ordinal']:02d}"
    cell['evidence_sha256'] = {p.relative_to(folder).as_posix(): base._sha(p)
        for p in folder.rglob('*') if p.is_file() and p.name != 'TRAJECTORY.json'}
    (folder / 'TRAJECTORY.json').write_text(json.dumps(cell))
    base._seal(path.parent, window, result)


def test_native_task_projection_and_grading(fx):
    path, _ = fx
    unit = cf.read_unit(path)
    assert len(unit['cells']) == 18
    assert unit['derived']['A0']['accuracy_over_scheduled'] == pytest.approx(2/3)
    assert unit['derived']['A1-k12']['accuracy_over_scheduled'] == pytest.approx(1/3)
    assert len(cf.native_rows(path)) == 18
    for native in cf.native_rows(path):
        t = cf.project(native)
        assert ct.grade(t)[:2] == ('Judged', 'Located')
        assert t.extra['schema'] == 'epyc.cf3c.task.native.v1'
        assert t.extra['producer'] == 'cf3c-task-level'
        assert 'no adoption claim' in t.claim
        assert t.extra['cost_accounting']['complete_cost_tasks'] == 3
        assert len(t.extra['activation_witnesses']) == 3


@pytest.mark.parametrize('tamper', ['action', 'history', 'render', 'placement', 'threshold',
                                  'usage', 'oracle', 'preflight', 'request', 'evidence'])
def test_resealed_task_semantic_refusals(fx, tamper):
    path, window = fx
    result = json.loads(path.read_text())
    cell = result['paired']['archive-reasoning']['arms']['A1-k12']
    folder = window / f"task-{cell['ordinal']:02d}"
    turn = folder / 'turn-01'
    name = None
    if tamper == 'action':
        name = turn / 'ACTION.json'
        value = json.loads(name.read_text())
        value['observations'][0]['content'] = '{}'
    elif tamper in ('history', 'placement'):
        name = folder / ('turn-02' if tamper == 'history' else 'turn-01') / 'original-messages.json'
        value = json.loads(name.read_text())
        value[0]['content'] += ' mutated' if tamper == 'history' else 'e10facc8954f'
    elif tamper == 'render':
        name = turn / 'template.response.body'
        value = json.loads(name.read_text())
        value['prompt'] += 'ArchiveHead01'
    elif tamper == 'threshold':
        name = turn / 'PREFLIGHT.json'
        value = json.loads(name.read_text())
        value['policy']['production_threshold'] = 4
        cell['turns'][0]['policy']['production_threshold'] = 4
    elif tamper == 'usage':
        cell['observed_usage']['total_tokens'] += 1
    elif tamper == 'oracle':
        cell['correct'] = False
    elif tamper == 'preflight':
        cell['turns'][0]['archive_receipt_exposed'] = False
    elif tamper == 'request':
        name = turn / 'completion.request.body'
        value = json.loads(name.read_text())
        value['seed'] += 1
    else:
        cell['evidence_sha256'].pop('turn-01/ACTION.json')
        (folder / 'TRAJECTORY.json').write_text(json.dumps(cell))
        base._seal(path.parent, window, result)
    if name:
        name.write_text(json.dumps(value))
    if tamper != 'evidence':
        _save(path, window, result, cell)
    with pytest.raises(ct.ProjectionError):
        cf.native_rows(path)


@pytest.mark.parametrize('tamper', ['smoke', 'schedule', 'packet', 'summary', 'unknown-verdict'])
def test_task_custody_refusals(fx, tamper):
    path, window = fx
    result = json.loads(path.read_text())
    if tamper in ('smoke', 'schedule'):
        w = json.loads((window / 'WINDOW.json').read_text())
        if tamper == 'smoke':
            w['smoke'] = True
        else:
            w['schedule'][0]['seed'] += 1
        (window / 'WINDOW.json').write_text(json.dumps(w))
    elif tamper == 'packet':
        (path.parent.parent / 'packet').unlink()
    elif tamper == 'summary':
        result['arms']['A0']['mean_live_tokens_per_complete_cost_task'] += 1
    else:
        cell = result['paired']['archive-tail']['arms']['A0']
        cell.update(status='UNKNOWN', correct=True)
        _save(path, window, result, cell)
    base._seal(path.parent, window, result)
    with pytest.raises(ct.ProjectionError):
        cf.native_rows(path)


def test_task_recipient_planning_canary(fx, tmp_path, capsys):
    path, _ = fx
    rc, ledger = base._ingest(tmp_path, path)
    report = json.loads(capsys.readouterr().out)
    assert rc == 0 and report['rows_projected'] == 18 and not report['refused']
    evidence = base._prepare(tmp_path, ledger, {'model_file': base.MODEL, 'backend': 'cpu', 'quant': 'Q8_0'})
    assert evidence['nonempty_target'] is True
    assert 'finite multi-turn task-environment diagnostics' in json.dumps(evidence)
    assert 'no adoption claim' in json.dumps(evidence)
    other = base._prepare(tmp_path, ledger, {'model_file': 'Other.gguf', 'backend': 'cpu'})
    assert other['tiers']['target'] == 0


def test_task_ingest_refuses_atomically_and_malformed_record_is_explicit(fx, tmp_path, capsys):
    path, window = fx
    result = json.loads(path.read_text())
    cell = result['paired']['archive-tail']['arms']['A0']
    cell['turns'] = 'malformed'
    _save(path, window, result, cell)
    rc, ledger = base._ingest(tmp_path, path)
    report = json.loads(capsys.readouterr().out)
    assert rc == 0 and report['refused'] and report['rows_projected'] == 0
    assert not ledger.exists() or not ledger.read_text().strip()


def _truncate(fx, status):
    path, window = fx
    result = json.loads(path.read_text())
    cell = result['paired']['archive-reasoning']['arms']['A0']
    folder = window / f"task-{cell['ordinal']:02d}"
    # Keep the successful inspect action, then interrupt the second generation.
    for p in folder.glob('turn-*'):
        if p.name > 'turn-02':
            shutil.rmtree(p)
    for p in (folder / 'turn-02').iterdir():
        if p.name in ('ACTION.json', 'completion.response.body', 'completion.http.json'):
            p.unlink()
    cell['turns'] = cell['turns'][:2]
    for k in ('usage', 'finish_reason', 'tool_events'):
        cell['turns'][-1].pop(k, None)
    cell.update(status=status, correct=None if status == 'UNKNOWN' else False, answer=None,
        finish_reason='instrument_failure' if status == 'UNKNOWN' else 'task_wall_budget',
        non_termination=None if status == 'UNKNOWN' else 1, released=False, inspected=True,
        live_tools_executed=1, generation_turns=1, generation_requests_started=2, usage_complete=False,
        observed_usage={k: cell['turns'][0]['usage'][k] for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')})
    _save(path, window, result, cell)
    # Native summary for the altered fixture, using the producer's cohort definition.
    observed = [c for c in result['paired'].values() for c in [c['arms']['A0']]
                if c['status'] in ('graded', 'abstained', 'NA')]
    complete = [c for c in observed if c['usage_complete']]
    s = result['arms']['A0']
    s.update(graded=2, correct=2, abstained=0, UNKNOWN=int(status == 'UNKNOWN'), NA=int(status == 'NA'),
        observed=len(observed), complete_cost_tasks=2, incomplete_cost_tasks=int(status == 'NA'),
        incomplete_token_lower_bound_total=cell['observed_usage']['total_tokens'] if status == 'NA' else 0,
        mean_live_tokens_per_complete_cost_task=sum(c['observed_usage']['total_tokens'] for c in complete)/2,
        mean_live_wall_s_per_observed_task=sum(c['wall_s'] for c in observed)/len(observed),
        accuracy_over_observed=2/len(observed), non_termination=int(status == 'NA'))
    result['completed'] = 17 if status == 'UNKNOWN' else 18
    result['error'] = 'interrupted test fixture'
    return base._seal(path.parent, window, result)


@pytest.mark.parametrize('status', ['UNKNOWN', 'NA'])
def test_incomplete_task_cost_denominators_and_canary(fx, tmp_path, capsys, status):
    path = _truncate(fx, status)
    unit = cf.read_unit(path)
    d = unit['derived']['A0']
    assert (d['tokens_cases'], d['wall_cases']) == (2, 2 if status == 'UNKNOWN' else 3)
    assert d['accuracy_over_scheduled'] == pytest.approx(2/3)
    assert d['cost_accounting']['incomplete_attempted_tasks'] == 1
    assert d['cost_accounting']['incomplete_cost_tasks'] == int(status == 'NA')
    assert unit['paired_deltas']['A1-k4'][2]['total_tokens'] is None
    rc, ledger = base._ingest(tmp_path, path)
    assert rc == 0
    capsys.readouterr()
    evidence = base._prepare(tmp_path, ledger, {'model_file': base.MODEL, 'backend': 'cpu'})
    assert evidence['nonempty_target'] is True
    assert f'{status} 1' in json.dumps(evidence)


def test_unattempted_tasks_remain_in_scheduled_denominator(fx):
    path, window = fx
    result = json.loads(path.read_text())
    cell = result['paired']['archive-tail']['arms']['A0']
    shutil.rmtree(window / f"task-{cell['ordinal']:02d}")
    result['paired']['archive-tail']['arms']['A0'] = {
        **{k: cell[k] for k in ('unit', 'ordinal', 'case', 'arm', 'seed')},
        'status': 'unattempted', 'correct': None}
    # The removed cell was a correct, complete-cost task.
    s = result['arms']['A0']
    s.update(attempted=2, observed=2, graded=1, correct=1, complete_cost_tasks=2,
        accuracy_over_observed=0.5,
        mean_live_tokens_per_complete_cost_task=(s['mean_live_tokens_per_complete_cost_task']*3-cell['observed_usage']['total_tokens'])/2,
        mean_live_wall_s_per_observed_task=(s['mean_live_wall_s_per_observed_task']*3-cell['wall_s'])/2)
    result.update(recorded=17, completed=17, coverage_complete=False)
    base._seal(path.parent, window, result)
    d = cf.read_unit(path)['derived']['A0']
    assert (d['scheduled'], d['attempted'], d['unattempted']) == (3, 2, 1)
    assert d['accuracy_over_scheduled'] == pytest.approx(1/3)
