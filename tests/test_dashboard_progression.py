"""Existing producer bytes through the real reader and surviving /loop renderer."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

from dashboard import kernel_progression as reader, panels, server

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/kernel_progression_recorded.json'
NOW = 1_800_000_000.0


def document():
    return json.loads(FIXTURE.read_bytes())


def snapshot(tmp_path, body, *, now=NOW):
    path = tmp_path / 'progression.json'
    if body is not None:
        path.write_text(body if isinstance(body, str) else json.dumps(body))
    return reader.snapshot(path=path, now=now)[0]


def run_renderer(tmp_path, payload, name='renderDiscoveryProgression', extra_js=''):
    page = (ROOT / 'dashboard/static/loop.html').read_text()
    assert 'id="discovery-progression"' in page
    js = '\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', page, re.S))
    (tmp_path / 'page.js').write_text(js + '\n' + extra_js)
    (tmp_path / 'payload.json').write_text(json.dumps(payload))
    proc = subprocess.run(['node', str(ROOT / 'tests/js/render_harness.js'),
                           str(tmp_path / 'page.js'), str(tmp_path / 'payload.json'), name],
                          capture_output=True, text=True, timeout=30, check=True)
    output = json.loads(proc.stdout)
    assert not output.get('load_error') and output['threw'] == [], output
    assert output['ran'] == 1
    return output['by_id']['discovery-progression']


def test_recorded_fixture_is_original_producer_bytes():
    origin = json.loads(FIXTURE.with_suffix('.source.json').read_text())
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == origin['source_sha256']
    assert document()['authority'] == 'presentation_projection_only'
    assert document()['observed_through'] != document()['generated_at']


def test_historical_record_is_shown_as_stale_despite_reexport(tmp_path):
    body = document()
    body['generated_at'] = datetime.fromtimestamp(NOW, timezone.utc).isoformat()
    view = snapshot(tmp_path, body)
    assert view['state'] == 'stale'
    assert view['_freshness']['source'] == 'observed_through'
    assert view['_freshness']['age_s'] > 14 * 86400
    html = run_renderer(tmp_path, {'progression': view})
    assert 'STALE' in html and 'LAST OBSERVATIONS' in html
    assert 'CPU latest observation' in html and 'GPU latest observation' in html
    assert 'strict keep: <strong>1</strong>' in html
    assert 'no promotion authority' in html


def test_current_record_renders_both_lanes_and_funnel(tmp_path):
    body = document()
    observed = datetime.fromisoformat(body['observed_through'].replace('Z', '+00:00')).timestamp()
    view = snapshot(tmp_path, body, now=observed + 60)
    assert view['state'] == 'fresh'
    html = run_renderer(tmp_path, {'progression': view})
    assert 'FRESH' in html and 'LAST OBSERVATIONS' not in html
    assert 'candidate: <strong>38</strong>' in html
    assert 'CPU latest observation' in html and 'GPU latest observation' in html
    assert 'GGML_IQK' in html


@pytest.mark.parametrize('body,state,word', [(None, 'absent', 'ABSENT'),
                                           ('{broken', 'malformed', 'MALFORMED')])
def test_missing_and_corrupt_producer_are_visible(tmp_path, body, state, word):
    view = snapshot(tmp_path, body)
    assert view['state'] == state and view['data'] is None
    html = run_renderer(tmp_path, {'progression': view})
    assert word in html and 'data-discovery-funnel' not in html
    assert 'CPU latest observation' not in html


@pytest.mark.parametrize('timestamp', [None, 'not a timestamp', '2050-01-01T00:00:00Z'])
def test_unknown_and_future_horizons_never_read_fresh(tmp_path, timestamp):
    body = document()
    body['observed_through'] = timestamp
    view = snapshot(tmp_path, body)
    assert view['state'] == 'unknown'
    html = run_renderer(tmp_path, {'progression': view})
    assert 'UNKNOWN' in html and 'LAST OBSERVATIONS' in html


def test_all_negative_observations_remain_visible_without_a_winner(tmp_path):
    body = document()
    for row in body['candidates']:
        row.update(stage='screened_out', effect_fraction=-.1, champion=False, promotable=False)
    body['funnel'] = dict.fromkeys(body['funnel'], 0)
    view = snapshot(tmp_path, body)
    html = run_renderer(tmp_path, {'progression': view})
    assert 'screened_out' in html and '-10.00%' in html
    assert 'strict keep: <strong>0</strong>' in html
    assert 'CPU latest observation' in html and 'GPU latest observation' in html
    assert 'winner' not in html.lower()


def test_empty_report_is_distinct_from_missing(tmp_path):
    body = document()
    body.update(candidates=[], unexplored=[], funnel=dict.fromkeys(body['funnel'], 0))
    view = snapshot(tmp_path, body)
    assert view['available'] is True
    assert view['_freshness']['content'] == panels.CONTENT_EMPTY
    html = run_renderer(tmp_path, {'progression': view})
    assert 'reported no candidate observations' in html
    assert 'CPU latest observation' in html and 'no observation reported' in html
    assert 'strict keep: <strong>0</strong>' in html


def test_producer_text_is_escaped_in_every_card(tmp_path):
    body = document()
    poison = '<img src=x onerror=alert(1)>'
    for row in body['candidates']:
        row.update(candidate=poison, workload=poison)
        row['evidence'] = [{'path': poison}]
    body['unexplored'] = [{'lane': 'CPU', 'hypothesis': poison, 'state': poison}]
    html = run_renderer(tmp_path, {'progression': snapshot(tmp_path, body)})
    assert poison not in html and '&lt;img' in html
    assert html.count('&lt;img') > 5


@pytest.mark.parametrize('mutate', [
    lambda d: d.update(schema='unknown'),
    lambda d: d.update(promotion_claim=True),
    lambda d: d.update(authority='promotion_authority'),
    lambda d: d['funnel'].update(strict_keep=999),
    lambda d: d['funnel'].update(champion=False),
    lambda d: d['candidates'][0].update(effect_fraction=float('nan')),
    lambda d: d['candidates'][0].update(effect_fraction=True),
    lambda d: d['candidates'][0].update(stage='invented'),
    lambda d: d['candidates'][0].update(metric_direction='lower_better'),
    lambda d: d['candidates'][0].update(evidence='not a list'),
    lambda d: d['candidates'][0].update(evidence=[None]),
    lambda d: d['candidates'][0].update(workload={}),
    lambda d: d.update(candidates={}),
])
def test_malformed_authority_and_data_are_refused(tmp_path, mutate):
    body = document()
    mutate(body)
    view = snapshot(tmp_path, body)
    assert view['state'] == 'malformed' and view['data'] is None
    html = run_renderer(tmp_path, {'progression': view})
    assert 'MALFORMED' in html and 'strict keep:' not in html


def test_read_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(reader, 'MAX_BYTES', 10)
    assert snapshot(tmp_path, document())['state'] == 'malformed'


def test_surviving_render_calls_the_funnel_even_when_loop_is_absent(tmp_path, monkeypatch):
    path = tmp_path / 'progression.json'
    path.write_bytes(FIXTURE.read_bytes())
    monkeypatch.setattr(reader, 'PATH', path)
    payload = server.loop_payload()
    assert payload['loop'] is None
    html = run_renderer(tmp_path, payload, name='render')
    assert 'data-discovery-funnel' in html and 'STALE' in html


@pytest.mark.parametrize('body,expected', [(None, 'absent'), ('{broken', 'degraded')])
def test_separate_probe_reports_missing_and_malformed(tmp_path, monkeypatch, body, expected):
    path = tmp_path / 'health.json'
    if body is not None:
        path.write_text(body)
    monkeypatch.setattr(reader, 'PATH', path)
    code, payload = reader.health()
    assert (code, payload['status']) == (503, expected)


def test_card_cannot_change_loop_or_operator_gate_health(tmp_path, monkeypatch):
    before = server.loop_data_health()
    monkeypatch.setattr(reader, 'PATH', FIXTURE)
    after = server.loop_data_health()
    assert (before[0], before[1]['status']) == (after[0], after[1]['status'])
    assert panels.source('kernel_progression').gates_health is False
    assert server.API_ROUTES['/api/loop/progression'] is server.progression_payload
    assert server.PANEL_HEALTH_ROUTES['/api/loop/progression/health'] is server.progression_health


def test_failed_refresh_clears_previously_rendered_fresh_data(tmp_path):
    body = document()
    observed = datetime.fromisoformat(body['observed_through'].replace('Z', '+00:00')).timestamp()
    view = snapshot(tmp_path, body, now=observed + 60)
    assert view['state'] == 'fresh'
    html = run_renderer(tmp_path, {'progression': view}, name='renderThenFail', extra_js='''
function renderThenFail(d){renderDiscoveryProgression(d);renderFetchFailure("fixture offline");}
''')
    assert 'UNKNOWN' in html and 'hub unreachable' in html
    assert 'data-discovery-funnel' not in html and 'FRESH' not in html


@pytest.mark.parametrize('depth', [reader.MAX_DEPTH + 1, 2000])
def test_deep_optional_json_is_malformed_without_breaking_the_loop(tmp_path, monkeypatch, depth):
    path = tmp_path / 'deep-progression.json'
    # The first case parses successfully and would otherwise be forwarded; the
    # second exhausts the JSON parser. Both remain an optional-card failure.
    body = document()
    nested = '[' * depth + '0' + ']' * depth
    raw = json.dumps(body)[:-1] + ', "additive_field": ' + nested + '}'
    path.write_text(raw)
    assert path.stat().st_size < reader.MAX_BYTES
    before = server.loop_data_health()
    monkeypatch.setattr(reader, 'PATH', path)
    payload = server.loop_payload()
    assert payload['progression']['state'] == 'malformed'
    assert payload['progression']['data'] is None
    code, own_probe = reader.health()
    assert (code, own_probe['status'], own_probe['state']) == (503, 'degraded', 'malformed')
    after = server.loop_data_health()
    assert (before[0], before[1]['status']) == (after[0], after[1]['status'])
    assert run_renderer(tmp_path, payload).count('MALFORMED') == 1


def test_fifo_refuses_without_blocking_the_served_loop(tmp_path):
    path = tmp_path / 'producer.fifo'
    os.mkfifo(path)
    # A regression must time out this owned child, not hang the entire test job.
    code = '''
import json, sys
from pathlib import Path
from dashboard import kernel_progression as reader, panels, server
reader.PATH = Path(sys.argv[1])
server.loop_status.snapshot = lambda: ({"loop": None}, panels.Observation(artifact_present=False))
server._read_operator_gate_bundle = lambda: {"freshness": {"state": "relevant"}}
payload = server.loop_payload()
status, probe = reader.health()
print(json.dumps([payload["progression"]["state"], payload["progression"]["data"], status, probe["status"]]))
'''
    result = subprocess.run([sys.executable, '-c', code, str(path)],
                            capture_output=True, text=True, timeout=5, check=True)
    assert json.loads(result.stdout) == ['malformed', None, 503, 'degraded']


@pytest.mark.parametrize('kind', ['regular', 'symlink', 'hardlink'])
def test_regular_export_and_link_policy(tmp_path, kind):
    path = tmp_path / 'producer.json'
    if kind == 'regular':
        path.write_bytes(FIXTURE.read_bytes())
    elif kind == 'symlink':
        path.symlink_to(FIXTURE)
    else:
        # os.link cannot cross filesystems (EXDEV): the repo checkout and pytest's
        # tmp_path are routinely on different mounts. Link a same-fs copy instead;
        # the policy under test is st_nlink > 1, not which inode the fixture has.
        source = tmp_path / 'producer-source.json'
        source.write_bytes(FIXTURE.read_bytes())
        os.link(source, path)
    view = reader.snapshot(path=path, now=NOW)[0]
    assert view['artifact_present'] is True
    assert view['state'] == ('malformed' if kind == 'symlink' else 'stale')
    assert view['_freshness']['evidence'] == str(path)


@pytest.mark.parametrize('timed', [True, False])
def test_lane_latest_uses_instants_and_never_dates_unknown_rows(tmp_path, timed):
    body = document()
    for row in body['candidates']:
        row['observed_at'] = None
    cpu = [row for row in body['candidates'] if row['lane'] == 'CPU']
    assert len(cpu) >= 2
    cpu[0].update(candidate='earlier-offset', observed_at='2026-01-01T13:00:00+02:00' if timed else None)
    cpu[1].update(candidate='later-utc', observed_at='2026-01-01T12:30:00Z' if timed else None)
    html = run_renderer(tmp_path, {'progression': snapshot(tmp_path, body)})
    hero = re.search(r'data-discovery-lane="CPU">(.*?)</div>', html, re.S).group(1)
    if timed:
        assert 'later-utc' in hero and 'earlier-offset' not in hero
        assert 'latest observation' in hero
    else:
        assert 'time unknown' in hero and 'latest observation' not in hero
