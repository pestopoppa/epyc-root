"""Production-anchored improvement history and secondary CoR drill-down."""
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
PRODUCTION = {"resolved": True, "commit": "d" * 40,
              "label": "production-consolidated-v9"}


def _store(root: Path) -> None:
    con = sqlite3.connect(root / "experiments.db")
    con.execute("""CREATE TABLE experiments (
        attempt_id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL,
        campaign_id TEXT NOT NULL, deployment TEXT, epoch_sha256 TEXT NOT NULL,
        hypothesis_id TEXT, mechanism_id TEXT, target_surface TEXT,
        target_symbol TEXT, statement TEXT, falsifier TEXT, status TEXT NOT NULL,
        effect_fraction REAL, exact_effect REAL, target_effect REAL,
        refusal_reason TEXT, result_sha256 TEXT, payload TEXT NOT NULL)""")
    con.commit()
    con.close()


def _insert(root: Path, attempt: str, recorded_at: str, mechanism: str,
            status: str, payload: dict, reason: str | None = None) -> None:
    con = sqlite3.connect(root / "experiments.db")
    con.execute("INSERT INTO experiments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        attempt, recorded_at, "ak-loop", None, "e" * 64, None, mechanism,
        "tg128", "kernel", "statement", "falsifier", status, None, None,
        None, reason, None, json.dumps(payload)))
    con.commit()
    con.close()


def _accumulator(root: Path) -> None:
    (root / "accumulator-bundle.json").write_text(json.dumps({
        "schema": "epyc.autokernel.accumulator_bundle.v2",
        "champion_of_record": "a" * 40, "tip": "b" * 40,
        "keeps": ["akm-one", "akm-two", "akm-three"],
        "measurement_validity": "current_snapshot", "compounded_bench_pct": 3.25,
    }))


def _comparison(effect: float = 12.5) -> dict:
    return {"effect_pct": effect, "noise_floor_pct": 1.0, "pairs": 20,
            "surface": "tg128", "model": "/models/Qwen3.8-27B-Q8_0.gguf"}


def test_backend_admits_only_exact_three_way_production_history_join(tmp_path: Path) -> None:
    _store(tmp_path)
    head = "a" * 40
    comparison = _comparison()
    _insert(tmp_path, "keep", "2026-09-01T00:00:01Z", "akm-one", "kept",
            {"champion_head": head, "comparison": {"marginal": "not composed"}})
    reason = ("champion aaaaaaaaaaaa measures +12.500% against frozen production "
              "dddddddddddd (production-consolidated-v9) over 20 tg128 pairs, floor 1.0%")
    _insert(tmp_path, "refresh", "2026-09-01T00:00:00Z",
            "champion-vs-production", "champion_vs_production",
            {"mechanism_id": "champion-vs-production", "reason": reason}, reason)
    (tmp_path / "champion-vs-production.aaaaaaaaaaaa.json").write_text(
        json.dumps(comparison))

    rows = loop_status.read_knowledge(tmp_path)["body"]["trajectory_rows"]
    result = loop_status.improvement_trajectory(tmp_path, rows, PRODUCTION)
    headline = result["production_headline"]
    assert headline["state"] == "available"
    assert headline["curves"][0]["id"] == "Qwen3.8-27B-Q8_0.gguf::tg128"
    assert headline["curves"][0]["points"][0]["gain_pct"] == 12.5
    assert "comparison" not in headline["curves"][0]["points"][0]

    comparison["effect_pct"] = 99.0
    (tmp_path / "champion-vs-production.aaaaaaaaaaaa.json").write_text(
        json.dumps(comparison))
    result = loop_status.improvement_trajectory(tmp_path, rows, PRODUCTION)
    assert result["production_headline"]["state"] == "unavailable"
    assert len(result["production_headline"]["evidence_errors"]) == 1


def test_backend_keeps_glm_cor_measurement_secondary(tmp_path: Path) -> None:
    _store(tmp_path)
    _accumulator(tmp_path)
    result = loop_status.improvement_trajectory(tmp_path, [], PRODUCTION)
    assert result["production_headline"]["state"] == "unavailable"
    local = result["campaign_drilldown"]
    assert local["state"] == "available"
    assert local["basis"] == "gain_pct_vs_campaign_cor"
    assert local["bench_checkpoints"] == [{
        "keep_count": 3, "gain_pct": 3.25,
        "evidence_state": "cheap_screen_estimate",
    }]


def test_backend_distinguishes_absent_and_malformed_local_evidence(tmp_path: Path) -> None:
    _store(tmp_path)
    result = loop_status.improvement_trajectory(tmp_path, [], PRODUCTION)
    assert result["campaign_drilldown"]["state"] == "absent"
    (tmp_path / "accumulator-bundle.json").write_text("not json")
    result = loop_status.improvement_trajectory(tmp_path, [], PRODUCTION)
    assert result["campaign_drilldown"]["state"] == "malformed"


@pytest.mark.skipif(shutil.which("node") is None, reason="node unavailable")
def test_browser_leads_with_production_curves_and_demotes_cor(tmp_path: Path) -> None:
    payload = {"knowledge": {"improvement_trajectory": {
        "schema": loop_status.TRAJECTORY_SCHEMA,
        "production_headline": {
            "state": "available", "detail": "direct only",
            "baseline": {"commit": "d" * 40, "label": "production-consolidated-v9"},
            "evidence_errors": [{"evidence": "broken.json", "reason": "unjoined"}],
            "curves": [{"id": "qwen::tg128", "model": "Qwen3.8-27B-Q8_0.gguf",
                        "surface": "tg128", "points": [
                            {"commit": "a" * 40, "recorded_at": "2026-09-01T00:00:00Z",
                             "gain_pct": 5.6, "pairs": 20},
                            {"commit": "b" * 40, "recorded_at": "2026-09-02T00:00:00Z",
                             "gain_pct": 7.2, "pairs": 20}]}]},
        "campaign_drilldown": {"state": "available", "keeps": [{}, {}, {}],
                               "bench_checkpoints": [{"gain_pct": .83}],
                               "serving_checks": [{"keep_count": 2, "gain_pct": .33,
                                                   "evidence_state": "serving_inconclusive"}]},
    }}}
    blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                        PAGE.read_text(), re.DOTALL)
    page_js, data = tmp_path / "page.js", tmp_path / "payload.json"
    page_js.write_text("\n".join(blocks))
    data.write_text(json.dumps(payload))
    proc = subprocess.run(["node", str(HARNESS), str(page_js), str(data),
                           "renderImprovementTrajectory"], capture_output=True,
                          text=True, timeout=30, check=True)
    card = json.loads(proc.stdout)["by_id"]["trajectory"]
    assert "frozen production 0%" in card
    assert "Qwen3.8-27B-Q8_0.gguf" in card
    assert "+7.200% vs frozen production" in card
    assert "Campaign-local CoR drill-down" in card
    assert "not production-relative" in card
    assert "1 unjoinable production receipt" in card
