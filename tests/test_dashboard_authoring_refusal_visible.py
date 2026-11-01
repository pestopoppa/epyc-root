"""Refusal dispositions and actionable detail reach the surviving loop page."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

import pytest
from dashboard import loop_status, server

ROOT = Path(__file__).resolve().parents[1]


def _render(tmp_path, monkeypatch, status, reason=''):
    body = json.loads((ROOT / 'tests/fixtures/autokernel_loop_status_sample.json').read_text())
    body.update(generated_at=datetime.now(timezone.utc).isoformat(),
                recent=[{'status': status, 'reason': reason, 'mechanism_id': 'fixture'}])
    (tmp_path / 'loop-status.json').write_text(json.dumps(body))
    monkeypatch.setenv(loop_status.STORE_ROOT_ENV, str(tmp_path))
    payload = server.loop_payload()
    assert payload['loop']['recent'][0]['status'] == status
    page = (ROOT / 'dashboard/static/loop.html').read_text()
    (tmp_path / 'page.js').write_text('\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', page, re.S)))
    (tmp_path / 'payload.json').write_text(json.dumps(payload))
    p = subprocess.run(['node', str(ROOT / 'tests/js/render_harness.js'),
                        str(tmp_path / 'page.js'), str(tmp_path / 'payload.json'), 'renderRecent'],
                       check=True, capture_output=True, text=True, timeout=30)
    rendered = json.loads(p.stdout)
    assert rendered['threw'] == [] and rendered['ran'] == 1
    return rendered['by_id']['recent']


def test_authoring_refused_is_detected(tmp_path, monkeypatch):
    assert 'authoring_refused' in _render(tmp_path, monkeypatch, 'authoring_refused')


@pytest.mark.parametrize('status', ['authorization_refused', 'candidate_semantic_repeat_refused', 'portfolio_dnr_refused'])
def test_other_controller_refusal_statuses_are_detected(tmp_path, monkeypatch, status):
    html = _render(tmp_path, monkeypatch, status)
    assert status in html and 'rowstat lose' in html


@pytest.mark.parametrize('status', ['critic_revise', 'candidate', 'kept'])
def test_non_refusal_statuses_stay_undetected(tmp_path, monkeypatch, status):
    html = _render(tmp_path, monkeypatch, status)
    assert status in html and '_refused' not in html
    assert ('rowstat win' in html) == (status == 'kept')


def test_the_refusal_detail_reaches_the_operator(tmp_path, monkeypatch):
    html = _render(tmp_path, monkeypatch, 'authoring_refused', 'vecdotq: undeclared <file-scope>')
    assert 'vecdotq' in html and '&lt;file-scope&gt;' in html
    assert '<file-scope>' not in html
