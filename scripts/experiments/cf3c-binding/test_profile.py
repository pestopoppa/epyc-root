"""Refusal controls for the binding profile's separate fixed schedule."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('binding_prepare', Path(__file__).with_name('prepare.py'))
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def test_cohort_is_exactly_four_paired_six_arm_tasks():
    data = profile.cohort()
    assert len(data['cases']) == 4
    assert len(data['schedule']) == 24
    assert {r['case'] for r in data['schedule']} == set(profile.COVERAGE_CASES)
    for case in profile.COVERAGE_CASES:
        rows = [r for r in data['schedule'] if r['case'] == case]
        assert {r['arm'] for r in rows} == set(profile.ARMS)
        assert len({r['seed'] for r in rows}) == 1


def test_cohort_refuses_changed_archive_even_with_retained_digest(tmp_path, monkeypatch):
    data = profile.cohort()
    data['cases'][0]['initial_history'][0]['output'] += ' altered'
    path = tmp_path / 'cohort.json'
    path.write_text(json.dumps(data))
    monkeypatch.setattr(profile, 'COHORT', path)
    with pytest.raises(ValueError, match='cohort changed'):
        profile.cohort()


def test_cohort_refuses_recomputed_unregistered_digest(tmp_path, monkeypatch):
    data = profile.cohort()
    data['cohort_sha256'] = '0' * 64
    path = tmp_path / 'cohort.json'
    path.write_text(json.dumps(data))
    monkeypatch.setattr(profile, 'COHORT', path)
    with pytest.raises(ValueError, match='cohort changed'):
        profile.cohort()


def test_sealed_profile_refuses_tampered_schedule(tmp_path, monkeypatch):
    packet = profile.SCRATCH / 'packet'
    inputs = json.loads((packet / 'inputs.json').read_text())
    # Small test fixtures only; no source, model or log copies.
    for name in ('inputs.json', 'cases.json', 'inventory.json'):
        (tmp_path / name).write_text((packet / name).read_text())
    (tmp_path / 'schedule.json').write_text('{"coverage": []}')
    # Pin verification must reject before trying to launch any native process.
    inputs['packet_sha256'] = {name: profile.digest(tmp_path / name)
                               for name in ('cases.json', 'inventory.json', 'schedule.json')}
    monkeypatch.setattr(profile, 'FILES', tuple(inputs['packet_sha256']))
    (tmp_path / 'inputs.json').write_text(json.dumps(inputs))
    with pytest.raises(ValueError, match='schedule changed'):
        profile.verify_packet(tmp_path)
