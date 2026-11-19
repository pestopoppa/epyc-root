"""Active-evidence native projection: recorded diagnostic custody, no new warrant."""
import json
from pathlib import Path

import pytest

import test_toc_ab_cf3c as base

cf, ct = base.cf, base.ct
REAL = Path('/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-active/native')
pytestmark = pytest.mark.skipif(not (REAL / 'RESULT.json').exists(), reason='native window absent')


@pytest.fixture
def fx(tmp_path, monkeypatch):
    monkeypatch.setattr(base, 'REAL', REAL)
    monkeypatch.setattr(base, 'KEEP_ARMS', ('A0', 'A1-k4', 'A1-k8', 'A1-k12', 'A2', 'A3'))
    path, window = base._fixture(tmp_path)
    (tmp_path / 'packet').symlink_to(REAL.parent / 'packet', target_is_directory=True)
    return path, window


def test_recorded_active_window_and_projection(fx):
    path, _ = fx
    unit = cf.read_unit(path)
    assert len(unit['cells']) == 18
    assert unit['profile']['producer'] == 'cf3c-active-evidence'
    assert all(d['scheduled'] == 3 for d in unit['derived'].values())
    assert len(cf.native_rows(path)) == 18
    for cell in unit['cells']:
        w = unit['activation_witnesses'][cell['unit']]['active_evidence']
        assert w['original_target_exposed'] is True
        assert w['selected_target_exposed'] == cell['target_exposed']
        assert w['native_rendered_target_exposed'] == cell['target_exposed']
        assert w['fixture']['steps'] == 10
    for n in cf.native_rows(path):
        t = cf.project(n)
        assert ct.grade(t)[:2] == ('Judged', 'Located')
        assert 'development fixtures' in t.claim and 'no adoption claim' in t.claim
        assert t.extra['producer'] == 'cf3c-active-evidence'
    assert unit['derived']['A0']['accuracy_over_scheduled'] == pytest.approx(2/3)
    assert unit['derived']['A1-k12']['accuracy_over_scheduled'] == pytest.approx(1/3)


@pytest.mark.parametrize('tamper', ['threshold', 'placement', 'render', 'exposure', 'marker', 'tokenizer'])
def test_resealed_active_semantic_refusals(fx, tamper):
    path, window = fx
    result = json.loads(path.read_text())
    cell = result['paired']['old-deep']['arms']['A1-k12']
    folder = window / f"cell-{cell['ordinal']:02d}"
    if tamper == 'threshold':
        name = 'policy.json'
        value = json.loads((folder / name).read_text())
        value['production_stubbed'] = 0
    elif tamper == 'placement':
        name = 'original-messages.json'
        value = json.loads((folder / name).read_text())
        value[0]['content'] += result['paired']['old-deep']['arms']['A0']['answer']
    elif tamper in ('render', 'marker'):
        name = 'template.response.body'
        value = json.loads((folder / name).read_text())
        value['prompt'] += (result['paired']['old-deep']['arms']['A0']['answer'] if tamper == 'render' else 'ObservationTail01')
    elif tamper == 'tokenizer':
        name = 'tokenize.request.body'
        value = json.loads((folder / name).read_text())
        value['content'] = 'different native prompt'
    else:
        name = None
        cell['target_exposed'] = True
    if name:
        (folder / name).write_text(json.dumps(value))
        cell['evidence_sha256'][name] = base._sha(folder / name)
    (folder / 'TRAJECTORY.json').write_text(json.dumps(cell))
    base._seal(path.parent, window, result)
    with pytest.raises(ct.ProjectionError):
        cf.native_rows(path)


@pytest.mark.parametrize('tamper', ['packet', 'dimensions', 'schedule'])
def test_packet_fixture_and_schedule_refusals(fx, monkeypatch, tamper):
    path, window = fx
    if tamper == 'packet':
        (path.parent.parent / 'packet').unlink()
    elif tamper == 'schedule':
        w = json.loads((window / 'WINDOW.json').read_text())
        w['schedule'][0]['seed'] += 1
        (window / 'WINDOW.json').write_text(json.dumps(w))
        base._reseal(path, window)
    else:
        load = cf._load
        def altered(p):
            value = load(p)
            if p.name == 'cases.json':
                value[0]['steps'] = 6
            return value
        monkeypatch.setattr(cf, '_load', altered)
    with pytest.raises(ct.ProjectionError):
        cf.native_rows(path)


def test_active_recipient_planning_canary(fx, tmp_path, capsys):
    path, _ = fx
    rc, ledger = base._ingest(tmp_path, path)
    report = json.loads(capsys.readouterr().out)
    assert rc == 0 and report['rows_projected'] == 18 and not report['refused']
    ev = base._prepare(tmp_path, ledger, {'model_file': base.MODEL, 'quant': 'Q8_0', 'backend': 'cpu'})
    assert ev['nonempty_target'] is True
    assert 'active-evidence development fixtures' in json.dumps(ev)
    assert 'no adoption claim' in json.dumps(ev)
    other = base._prepare(tmp_path, ledger, {'model_file': 'Other.gguf', 'backend': 'cpu'})
    assert other['tiers']['target'] == 0


def test_active_failed_cell_preserves_missing_usage_and_render(fx, tmp_path, capsys):
    path, window = fx
    result = json.loads(path.read_text())
    cell = result['paired']['old-deep']['arms']['A0']
    folder = window / f"cell-{cell['ordinal']:02d}"
    lost_tokens = cell.pop('usage')['total_tokens']
    for name in list(cell['evidence_sha256']):
        if name.startswith(('completion.', 'tokenize.')) or name == 'template.response.body':
            del cell['evidence_sha256'][name]
            (folder / name).unlink()
    cell.pop('target_exposed')
    cell.update(status='UNKNOWN', correct=None, error='native render failed', non_termination=None)
    (folder / 'TRAJECTORY.json').write_text(json.dumps(cell))
    summary = result['arms']['A0']
    summary.update(correct=1, graded=1, UNKNOWN=1, tokens_cases=2,
                   accuracy_among_graded=1.0, accuracy_over_attempted=1/3,
                   mean_total_tokens=(summary['mean_total_tokens']*3-lost_tokens)/2)
    result.update(completed=17, error='native render failed')
    base._seal(path.parent, window, result)
    d = cf.read_unit(path)['derived']['A0']
    assert (d['scheduled'], d['UNKNOWN'], d['tokens_cases'], d['wall_cases']) == (3, 1, 2, 3)
    assert d['accuracy_over_scheduled'] == pytest.approx(1/3)
    rc, ledger = base._ingest(tmp_path, path)
    assert rc == 0
    capsys.readouterr()
    ev = base._prepare(tmp_path, ledger, {'model_file': base.MODEL, 'backend': 'cpu'})
    assert ev['nonempty_target'] is True and 'UNKNOWN 1' in json.dumps(ev)


def test_unrecognized_profile_cannot_bypass_active_checks(fx):
    path, window = fx
    w = json.loads((window / 'WINDOW.json').read_text())
    w['grant'] = 'unknown-producer'
    (window / 'WINDOW.json').write_text(json.dumps(w))
    base._reseal(path, window)
    with pytest.raises(ct.ProjectionError, match='unrecognized native producer'):
        cf.native_rows(path)
