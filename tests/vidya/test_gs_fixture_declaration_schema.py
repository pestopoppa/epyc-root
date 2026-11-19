import json
import hashlib
from pathlib import Path

import pytest
from claim_tuple import ProjectionError, grade
from adapters import ufh12_gs_coverage as adapter
from test_ufh12_gs_frozen_negative_canary import make_capture


@pytest.mark.parametrize('declared', [True, False])
def test_fixture_declaration_is_bound_and_projected(tmp_path, declared):
    sidecar = make_capture(tmp_path, synthetic=declared)
    row = json.loads(sidecar.read_text())
    claim = adapter.project(adapter.native_rows(sidecar)[0])
    assert row['schema'] == 'epyc.vidya.ufh12_gs_frozen_coverage.v2'
    assert row['extra']['synthetic'] is declared
    assert row['extra']['synthetic_scope'] == 'producer-declared'
    assert claim.extra['synthetic'] is declared
    assert claim.extra['synthetic_scope'] == 'producer-declared'
    assert grade(claim)[:2] == ('Judged', 'Located')
    assert claim.protocol_id == ''


def test_absent_marker_refuses_before_writing_attestation(tmp_path):
    with pytest.raises(ValueError, match='legacy-unverified'):
        make_capture(tmp_path, synthetic=None)
    assert not (tmp_path/'frozen-coverage.record.json').exists()
    assert not (tmp_path/'frozen-coverage.belief_measurements.jsonl').exists()


@pytest.mark.parametrize('marker', ['true', 1, None])
def test_invalid_marker_refuses(tmp_path, marker):
    with pytest.raises((ValueError, TypeError)):
        make_capture(tmp_path, synthetic=marker)
    assert not (tmp_path/'frozen-coverage.belief_measurements.jsonl').exists()


def test_old_context_schema_is_explicitly_unverified(tmp_path):
    with pytest.raises(ValueError, match='legacy-unverified'):
        make_capture(tmp_path, synthetic=False,
                     context_schema='epyc.gs-frozen-query-native-context.v1')
    assert not (tmp_path/'frozen-coverage.record.json').exists()


def test_tampered_declaration_refuses_projection(tmp_path):
    sidecar = make_capture(tmp_path, synthetic=True)
    context_path = tmp_path/'run-context.json'
    context = json.loads(context_path.read_text())
    context['synthetic'] = False
    context_path.write_text(json.dumps(context))
    with pytest.raises(ProjectionError):
        adapter.native_rows(sidecar)


def test_legacy_frozen_projection_is_refused_without_rewrite(tmp_path):
    sidecar = make_capture(tmp_path, synthetic=True)
    rows = json.loads(sidecar.read_text())
    rows['schema'] = adapter._frozen.LEGACY_SCHEMA
    adapter._frozen.c.seal(rows)
    sidecar.write_text(json.dumps(rows)+'\n')
    before = sidecar.read_bytes()
    with pytest.raises(ProjectionError):
        adapter.native_rows(sidecar)
    assert sidecar.read_bytes() == before


def test_retained_original_unscoped_capture_is_refused_without_rewrite():
    original = Path('/mnt/raid0/llm/tmp/agentic-serving-harness-fixes/gs-frozen-query-v2/frozen-coverage.belief_measurements.jsonl')
    if not original.exists():
        pytest.skip('retained original capture is not present')
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    with pytest.raises(ProjectionError):
        adapter.native_rows(original)
    assert hashlib.sha256(original.read_bytes()).hexdigest() == before
