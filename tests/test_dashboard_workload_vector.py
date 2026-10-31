"""Workload identities travel with each source cell; legacy gaps stay unknown."""
import json
import re
import shutil
import subprocess

import pytest
from pathlib import Path

from dashboard.loop_status import _champion_workload_vector, _champion_legacy_reference
from dashboard.server import _operator_workload_vector, _operator_legacy_reference

ROOT = Path(__file__).resolve().parents[1]


def test_champion_per_leg_protocol_and_legacy_unknown():
    body = {'metrics': {'tg': {'surface': 'decode', 'effect_fraction': .1},
                        'pp': {'surface': 'prefill', 'effect_fraction': -.02}},
            'protocols': {'tg': {'model': 'M', 'argv': ['tg']}}, 'evidence': 'e'}
    rows = _champion_workload_vector(body)
    assert [r['workload'] for r in rows] == ['decode', 'prefill']
    assert all(r['scope'] == 'workload_cell' and r['whole_champion'] is False for r in rows)
    assert rows[0]['recipe'] == body['protocols']['tg']
    assert rows[1]['recipe'] is None
    legacy = _champion_workload_vector({'effect_fraction': 0.0, 'surface': 'tg128'})
    assert legacy[0]['effect_fraction'] == 0 and legacy[0]['recipe'] is None
    assert _champion_workload_vector(None) == []


def test_operator_cells_preserve_artifact_and_unknowns():
    rows = _operator_workload_vector([
        {'gate': 'anchor', 'artifact': 'a', 'artifact_sha256': 'h',
         'surfaces': [{'surface': 'pp', 'delta_pct': 1, 'anchor': 20, 'champion': 21}]},
        {'gate': 'spec', 'points': [{'in_flight': 2, 'delta_pct': 3}]}, None])
    assert rows[0]['workload'] == 'pp' and rows[0]['artifact_sha256'] == 'h'
    assert rows[0]['recipe'] is None
    assert all(r['scope'] == 'workload_cell' and r['whole_champion'] is False for r in rows)
    assert rows[0]['anchor'] == 20 and rows[0]['champion'] == 21
    assert rows[1]['workload'] is None and rows[1]['recipe'] is None
    assert rows[1]['in_flight'] == 2


@pytest.mark.skipif(shutil.which("node") is None, reason="node is unavailable")
def test_vector_render_keeps_subject_freshness_and_escapes(tmp_path):
    page = (ROOT / 'dashboard/static/loop.html').read_text()
    (tmp_path / 'page.js').write_text('\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', page, re.S)))
    payload = {'champion_vs_production': {'workload_vector': [
        {'workload': '<img onerror=x>', 'recipe': None, 'effect_fraction': .1}],
        'freshness': {'state': 'stale'}, 'baseline_check': 'superseded', 'capabilities': {}},
        'operator_gates': {'available': True, 'freshness': {'state': 'relevant', 'age_s': 2},
        'headline': {}, 'gates': [], 'workload_vector': [
            {'gate': 'spec', 'in_flight': 2, 'delta_pct': 12.3}]}}
    (tmp_path / 'payload.json').write_text(json.dumps(payload))
    result = subprocess.run(['node', str(ROOT / 'tests/js/render_harness.js'),
        str(tmp_path / 'page.js'), str(tmp_path / 'payload.json'),
        'renderChampion', 'renderOperatorGate'], capture_output=True, text=True,
        timeout=20, check=True)
    out = json.loads(result.stdout)
    assert out['threw'] == []
    champion = out['by_id']['champion-capabilities']
    assert '&lt;img onerror=x&gt;' in champion and '<img' not in champion
    assert 'recipe: UNKNOWN' in champion and 'baseline: superseded' in champion
    assert 'freshness: stale' in champion
    assert 'in-flight 2' in out['by_id']['opgate']
    assert 'workload: UNKNOWN' in out['by_id']['opgate']
    assert out['class_by_id']['opgate-badge'] == 'badge relevant'


def test_legacy_scalars_are_scoped_references():
    c = _champion_legacy_reference({'surface': 'tg128', 'model': 'M',
                                    'protocol': {'argv': ['recorded']}})
    assert c['scope'] == 'reference_cell_only' and c['whole_champion'] is False
    assert c['workload'] == 'tg128' and c['recipe'] == {'argv': ['recorded']}
    o = _operator_legacy_reference({'at_in_flight': 2, 'metric': 'tok_s'})
    assert o['whole_champion'] is False and o['in_flight'] == 2
    assert o['workload'] is None and o['recipe'] is None


def test_operator_projection_keeps_native_identity_and_two_recipes():
    recipe = {'anchor': {'server_argv': ['base']}, 'champion': {'server_argv': ['candidate']}}
    row = _operator_workload_vector([{'gate': 'spec', 'points': [{'in_flight': 1,
        'workload': 'W', 'model': 'M', 'recipe': recipe, 'delta_pct': 1}]}])[0]
    assert row['workload'] == 'W' and row['model'] == 'M' and row['recipe'] == recipe
