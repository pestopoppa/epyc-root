"""Measured retained-tip trajectory projection and executable browser rendering."""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

from dashboard import loop_status

REPO = Path(__file__).resolve().parents[1]
PAGE = REPO / "dashboard/static/loop.html"
HARNESS = REPO / "tests/js/render_harness.js"


def _store(root: Path) -> None:
    con = sqlite3.connect(root / "experiments.db")
    con.execute("""CREATE TABLE experiments (
        attempt_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL,
        campaign_id TEXT NOT NULL, deployment TEXT, epoch_sha256 TEXT NOT NULL,
        hypothesis_id TEXT, mechanism_id TEXT, target_surface TEXT,
        target_symbol TEXT, statement TEXT, falsifier TEXT, status TEXT NOT NULL,
        effect_fraction REAL, exact_effect REAL, target_effect REAL,
        refusal_reason TEXT, result_sha256 TEXT, payload TEXT NOT NULL)""")
    for index, mechanism in enumerate(("akm-one", "akm-two", "akm-three"), 1):
        con.execute("INSERT INTO experiments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            str(index), f"2026-09-0{index}T00:00:00Z", "ak-loop", None, "e" * 64,
            None, mechanism, "tg128", "kernel", "statement", "falsifier", "kept",
            index / 100, None, None, None, None, json.dumps({"status": "kept"})))
    con.commit()
    con.close()


def _receipts(root: Path) -> None:
    (root / "accumulator-bundle.json").write_text(json.dumps({
        "schema": "epyc.autokernel.accumulator_bundle.v2",
        "champion_of_record": "a" * 40, "tip": "b" * 40,
        "keeps": ["akm-one", "akm-two", "akm-three"],
        "keeps_since_serving_gate": 1, "measurement_validity": "current_snapshot",
        "compounded_bench_pct": 3.25,
    }))
    serving = root / "serving"
    serving.mkdir()
    members = ["akm-one", "akm-two"]
    (serving / ("bundle-" + "c" * 12 + ".json")).write_text(json.dumps({
        "schema": "epyc.autokernel.serving_ab.v2", "bundled_keeps": members,
        "effect_pct": 0.4, "decisive": False, "outcome": "diverged",
        "planner_evidence": {"bundled_keeps": members,
                             "compounded_bench_pct": 2.75,
                             "serving_effect_pct": 0.4,
                             "serving_floor_pct": 6.351},
    }))


def test_backend_projects_only_measured_cumulative_checkpoints(tmp_path: Path) -> None:
    _store(tmp_path)
    _receipts(tmp_path)
    trajectory = loop_status.knowledge_snapshot(
        tmp_path, status_body=None)["improvement_trajectory"]
    assert trajectory["state"] == "available"
    assert [p["gain_pct"] for p in trajectory["bench_checkpoints"]] == [2.75, 3.25]
    assert [p["keep_count"] for p in trajectory["bench_checkpoints"]] == [2, 3]
    assert trajectory["serving_checks"][0]["evidence_state"] == "serving_inconclusive"
    assert trajectory["references"]["champion_of_record_pct"] == 0.0
    assert trajectory["references"]["production_pct"] is None
    # Marginal 1/2/3% effects exist in sqlite but are not multiplied into a
    # fabricated fourth cumulative point.
    assert len(trajectory["bench_checkpoints"]) == 2

    # The real CPU receipts carry tens of MiB of lifecycle samples before a
    # compact top-level summary tail.  A duplicate large receipt exercises the
    # bounded tail reader and exact-point deduplication without raising the
    # per-request read bound.
    members = ["akm-one", "akm-two"]
    (tmp_path / "serving/bundle-large.json").write_text(json.dumps({
        "anchor_residency": ["x" * 300_000], "decisive": False,
        "effect_pct": 0.4, "outcome": "diverged",
        "planner_evidence": {"bundled_keeps": members,
                             "compounded_bench_pct": 2.75,
                             "serving_effect_pct": 0.4,
                             "serving_floor_pct": 6.351},
        "reason": "retained duplicate", "schema": "epyc.autokernel.serving_ab.v2",
    }, indent=2))
    trajectory = loop_status.knowledge_snapshot(
        tmp_path, status_body=None)["improvement_trajectory"]
    assert len(trajectory["serving_checks"]) == 1
    assert trajectory["serving_evidence_errors"] == []


def test_backend_counts_broken_serving_evidence_instead_of_hiding_it(tmp_path: Path) -> None:
    _store(tmp_path)
    _receipts(tmp_path)
    (tmp_path / "serving/bundle-broken.json").write_text("not json")
    trajectory = loop_status.knowledge_snapshot(
        tmp_path, status_body=None)["improvement_trajectory"]
    assert len(trajectory["serving_checks"]) == 1
    assert trajectory["serving_evidence_errors"] == [{
        "evidence": str(tmp_path / "serving/bundle-broken.json"),
        "reason": "Expecting value: line 1 column 1 (char 0)",
    }]


def test_backend_keeps_missing_and_malformed_evidence_distinct(tmp_path: Path) -> None:
    _store(tmp_path)
    absent = loop_status.knowledge_snapshot(tmp_path, status_body=None)["improvement_trajectory"]
    assert absent["state"] == "absent"
    (tmp_path / "accumulator-bundle.json").write_text("not json")
    malformed = loop_status.knowledge_snapshot(tmp_path, status_body=None)["improvement_trajectory"]
    assert malformed["state"] == "malformed"


def test_backend_uses_only_exact_cor_matched_direct_production_receipt(
        tmp_path: Path) -> None:
    _store(tmp_path)
    _receipts(tmp_path)
    receipt = {
        "schema": loop_status.CHAMPION_SCHEMA,
        "baseline": {"commit": "d" * 40},
        "champion": {"commit": "a" * 40},
        "effect_fraction": 0.25,
        "metric_direction": "higher_better",
    }
    (tmp_path / "champion-vs-production.json").write_text(json.dumps(receipt))
    trajectory = loop_status.knowledge_snapshot(
        tmp_path, status_body=None)["improvement_trajectory"]
    assert trajectory["references"] == {
        "champion_of_record_pct": 0.0,
        "production_pct": pytest.approx(-20.0),
        "production_state": "direct_measurement",
        "production_detail": "derived only from the exact CoR-vs-production direct A/B",
    }

    receipt["champion"]["commit"] = "c" * 40
    (tmp_path / "champion-vs-production.json").write_text(json.dumps(receipt))
    trajectory = loop_status.knowledge_snapshot(
        tmp_path, status_body=None)["improvement_trajectory"]
    assert trajectory["references"]["production_state"] == "unavailable"
    assert trajectory["references"]["production_pct"] is None


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_draws_estimate_inconclusive_check_and_missing_production(tmp_path: Path) -> None:
    _store(tmp_path)
    _receipts(tmp_path)
    trajectory = loop_status.knowledge_snapshot(
        tmp_path, status_body=None)["improvement_trajectory"]
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                        PAGE.read_text(), re.DOTALL)
    page_js, payload = tmp_path / "page.js", tmp_path / "payload.json"
    page_js.write_text("\n".join(blocks))
    payload.write_text(json.dumps({"knowledge": {"improvement_trajectory": trajectory}}))
    proc = subprocess.run(["node", str(HARNESS), str(page_js), str(payload),
                           "renderImprovementTrajectory"], capture_output=True,
                          text=True, timeout=30, check=True)
    result = json.loads(proc.stdout)
    assert result["threw"] == []
    card = result["by_id"]["trajectory"]
    assert "cheap-screen cumulative estimate" in card
    assert "serving_inconclusive" in card
    assert "serving-unknown" in card
    assert "Production reference: unavailable" in card
    assert "akm-three" in card
