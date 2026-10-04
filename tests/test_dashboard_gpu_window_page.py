"""G1 MI210 window page (``/gpu-window``): registration, panel envelope, runtime render.

The data contract (``epyc.orchestrator.gpu_window_panel.v1``) is owned by the
orchestrator at ``:8000/dashboard/api/gpu_window``; this hub owns the page, the
registry row, the nav and a freshness envelope over the watchdog's executor-status
file. NO SERVER IS STARTED and NO NETWORK IS USED.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dashboard import panels, server  # noqa: E402

PAGE = REPO / "dashboard/static/gpu-window.html"
HARNESS = REPO / "tests/js/render_harness.js"
REGISTRY = REPO / "dashboard/registry.json"


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def _script() -> str:
    return "\n".join(re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", _html(), re.S))


def test_page_is_served_and_registered():
    assert server.HTML_ROUTES["/gpu-window"] == server.GPU_WINDOW_HTML == PAGE
    entries = json.loads(REGISTRY.read_text(encoding="utf-8"))["dashboards"]
    row = next(e for e in entries if e["id"] == "gpu-window")
    assert (row["port"], row["path"], row["title"]) == (8100, "/gpu-window", "MI210 window")
    assert row["health_path"] == "/health"
    assert "/dashboard/api/gpu_window/health" in row["blurb"]
    assert "transport-only" in row["blurb"]
    assert 'id="epyc-nav"' in _html() and 'src="/nav.js"' in _html()


def test_page_reads_the_orchestrator_contract():
    js = _script()
    assert "'/dashboard/api/gpu_window'" in js
    assert "/api/gpu_window'" not in js.replace("/dashboard/api/gpu_window'", "")


def test_panel_envelope_is_registered_with_the_declared_budget():
    src = panels.PANELS["gpu_window"]
    assert src.route == "/api/gpu_window" and src.payload_func == "gpu_window_payload"
    assert src.stale_s == 300.0 and src.watched
    assert "nothing will auto-restore the MI210 window" in src.absence_means
    assert server.API_ROUTES["/api/gpu_window"] is server.gpu_window_payload
    assert not any(panels.registry_gaps(server).values()), panels.registry_gaps(server)


def test_payload_absent_fresh_and_stale(tmp_path, monkeypatch):
    path = tmp_path / "mi210.json.executor-status.json"
    monkeypatch.setattr(server, "GPU_WINDOW_STATUS_JSON", path)
    env = server.gpu_window_payload()["_freshness"]
    assert env["artifact_present"] is False
    assert "nothing will auto-restore" in env["absence_means"]

    now = time.time()
    path.write_text(json.dumps({"generated_at_epoch": now - 10, "holder": "production",
                                "verdict": "ok", "fresh_for_s": 180}))
    env = server.gpu_window_payload()["_freshness"]
    assert env["artifact_present"] is True
    assert env["staleness_class"] == panels.CLASS_FRESH, env

    path.write_text(json.dumps({"generated_at_epoch": now - 900, "holder": "production"}))
    env = server.gpu_window_payload()["_freshness"]
    assert env["staleness_class"] == panels.CLASS_STALE, env


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
def test_render_live_window(tmp_path):
    payload = {
        "schema": "epyc.orchestrator.gpu_window_panel.v1", "generated_at": 1.0,
        "executor": {"holder": "bench-x", "grant_state": "granted", "window_id": "w-42",
                     "expected_end": "2026-10-04T12:00:00Z", "parked_ports": [8090],
                     "lease_state": "held", "overdue": False, "verdict": "window_open",
                     "fresh_for_s": 180, "last_action": "tick", "detail": ""},
        "window": {}, "watchdog_age_s": 20.0,
        "health": {"status": "ok", "reasons": []},
    }
    out = _run(payload, tmp_path, ["render"])
    assert out["threw"] == [], out["threw"]
    by_id = out["by_id"]
    assert "window_open" in by_id["gw-verdict"] and "UNKNOWN" not in by_id["gw-verdict"]
    for s in ("bench-x", "granted", "w-42", "held", "8090"):
        assert s in by_id["gw-window"], s


@needs_node
def test_dead_producer_renders_absent_not_ok(tmp_path):
    payload = {"schema": "epyc.orchestrator.gpu_window_panel.v1", "executor": None,
               "window": {"holder": "production"}, "watchdog_age_s": None,
               "health": {"status": "absent",
                          "reasons": ["watchdog not running (no executor status file)"]}}
    out = _run(payload, tmp_path, ["render"])
    assert out["threw"] == [], out["threw"]
    v = out["by_id"]["gw-verdict"]
    assert "NO WATCHDOG" in v and "watchdog not running" in v and "UNKNOWN" in v


@needs_node
def test_stale_watchdog_is_unknown_not_its_last_verdict(tmp_path):
    payload = {"executor": {"holder": "production", "verdict": "ok", "fresh_for_s": 180},
               "window": {}, "watchdog_age_s": 900.0,
               "health": {"status": "degraded", "reasons": ["watchdog stale (900s since last tick)"]}}
    out = _run(payload, tmp_path, ["render"])
    assert out["threw"] == [], out["threw"]
    v = out["by_id"]["gw-verdict"]
    assert "STALE" in v and "UNKNOWN" in v


@needs_node
def test_transport_failure_renders_unknown(tmp_path):
    out = _run({"reason": "x"}, tmp_path, ["renderDead"])
    assert out["threw"] == [], out["threw"]
    for panel in ("gw-verdict", "gw-window"):
        assert "UNKNOWN" in out["by_id"][panel], panel
