"""AP-50 decision cockpit page (``/cockpit``): registration, DOM contract, runtime render.

The data contract (``epyc.autopilot.decision_cockpit.v1``) is owned by the
orchestrator and served at ``:8000/dashboard/api/decision_cockpit``; this hub owns
only the page, the registry row and the nav. The hub never imports the producer,
so the runtime check executes the page's renderers under node against a sample
the PRODUCER generated over the real journal shards
(``tests/fixtures/decision_cockpit_contract_sample.json``), plus the two fail-closed
shapes: a builder error body and a transport failure.

NO SERVER IS STARTED and NO NETWORK IS USED.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dashboard import server  # noqa: E402

PAGE = REPO / "dashboard/static/cockpit.html"
HARNESS = REPO / "tests/js/render_harness.js"
SAMPLE = REPO / "tests/fixtures/decision_cockpit_contract_sample.json"
REGISTRY = REPO / "dashboard/registry.json"

_GET_BY_ID = re.compile(r'getElementById\(\s*[\'"]([A-Za-z0-9_-]+)[\'"]')
_SET_HTML = re.compile(r'setHtml\(\s*[\'"]([A-Za-z0-9_-]+)[\'"]')
_BADGE = re.compile(r'setBadge\(\s*[\'"]([A-Za-z0-9_-]+)[\'"]\s*,\s*[\'"]([A-Za-z0-9_-]+)[\'"]')


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def _script() -> str:
    return "\n".join(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", _html(), re.S))


def test_page_is_served_and_registered():
    assert server.HTML_ROUTES["/cockpit"] == server.COCKPIT_HTML == PAGE
    entries = json.loads(REGISTRY.read_text(encoding="utf-8"))["dashboards"]
    row = next(e for e in entries if e["id"] == "cockpit")
    assert (row["port"], row["path"], row["owner_repo"]) == (8100, "/cockpit", "epyc-root")
    assert row["health_path"] == "/health"
    # the registry row must say which probe answers DATA health, not just transport
    assert "/dashboard/api/decision_cockpit/health" in row["blurb"]
    assert 'id="epyc-nav"' in _html() and 'src="/nav.js"' in _html()


def test_page_reads_the_orchestrator_contract_not_a_hub_route():
    js = _script()
    assert "'/dashboard/api/decision_cockpit'" in js
    assert "/api/cockpit" not in js  # nothing proxied through the hub
    assert "digest" not in js.lower()


def test_every_looked_up_id_exists_in_the_markup():
    js, html = _script(), _html()
    ids = set(_GET_BY_ID.findall(js)) | set(_SET_HTML.findall(js))
    for a, b in _BADGE.findall(js):
        ids |= {a, b}
    ids |= set(re.findall(r"for \(const id of \[([^\]]+)\]\)", js)[0].replace("'", "").replace(" ", "").split(","))
    assert len(ids) >= 12, ids  # non-vacuity: the scan really found the lookups
    for i in sorted(ids):
        assert f'id="{i}"' in html, f"script looks up #{i} but the markup never defines it"


def test_fail_closed_copy_is_unknown_not_zero():
    js = _script()
    assert "UNKNOWN" in js
    assert "renderDead" in js


def _run(payload: dict, tmp_path: Path, names: list[str]) -> dict:
    page_js = "var location = {protocol: 'http:', hostname: 'localhost'};\n" + _script()
    (tmp_path / "page.js").write_text(page_js, encoding="utf-8")
    (tmp_path / "payload.json").write_text(json.dumps(payload), encoding="utf-8")
    proc = subprocess.run(["node", str(HARNESS), str(tmp_path / "page.js"),
                           str(tmp_path / "payload.json"), *names],
                          capture_output=True, text=True, timeout=60)
    assert proc.stdout.strip(), f"harness produced no output; stderr={proc.stderr[:400]}"
    return json.loads(proc.stdout)


needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not available")


@needs_node
@pytest.mark.parametrize("key", ["current_era", "e15_era"])
def test_renderers_execute_against_producer_sample(tmp_path, key):
    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))[key]
    out = _run(payload, tmp_path, ["render"])
    assert out["threw"] == [], out["threw"]
    assert out["ran"] == 1
    by_id = out["by_id"]
    assert "journal" in by_id["ck-banner"] and "OP-20" in by_id["ck-banner"]
    assert "proposed" in by_id["ck-funnel"]
    assert "hypothesis" in by_id["graph-legend"] or "tested_by" in by_id["graph-legend"]
    if key == "e15_era":
        assert "numeric:" in by_id["ck-levers"]
        assert "not comparable" in by_id["ck-deltas"]  # E15 rows vs the E16 incumbent
        assert "<svg" in by_id["ck-graph"]
    else:
        assert "No candidate" in by_id["ck-deltas"]  # current era has no trials yet


@needs_node
def test_builder_error_body_renders_unknown_everywhere(tmp_path):
    payload = {"schema": "epyc.autopilot.decision_cockpit.v1", "error": "boom",
               "health": {"status": "degraded", "reasons": ["builder failed: boom"]}}
    out = _run(payload, tmp_path, ["render"])
    assert out["threw"] == [], out["threw"]
    by_id = out["by_id"]
    assert "cockpit builder failed" in by_id["ck-banner"]
    for panel in ("ck-current", "ck-funnel", "ck-deltas", "ck-levers", "ck-graph"):
        assert "UNKNOWN" in by_id[panel], panel


@needs_node
def test_transport_failure_renders_unknown_not_stale_numbers(tmp_path):
    out = _run({"reason": "x"}, tmp_path, ["renderDead"])
    assert out["threw"] == [], out["threw"]
    for panel in ("ck-banner", "ck-current", "ck-funnel", "ck-deltas", "ck-levers", "ck-graph"):
        assert "UNKNOWN" in out["by_id"][panel], panel
