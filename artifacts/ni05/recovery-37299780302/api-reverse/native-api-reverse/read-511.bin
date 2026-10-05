from __future__ import annotations

import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
OPERATOR_CANDIDATES = REPO_ROOT / "scripts/autopilot/operator_candidates"
sys.path.insert(0, str(OPERATOR_CANDIDATES))

import ratify_and_apply_model_judge_tail_v3 as ratifier  # noqa: E402


def test_v3_ratifier_appends_both_backend_drain_eras() -> None:
    raw = (REPO_ROOT / "orchestration/instrument_eras.yaml").read_bytes()
    candidate = ratifier._append_eras(raw, "2026-08-06T12:00:00Z")
    registry = yaml.safe_load(candidate)
    rows = {
        row["id"]: row
        for row in registry["eras"]
        if row["id"] in {ratifier.QUALITY_ERA, ratifier.SPEED_ERA}
    }

    assert set(rows) == {ratifier.QUALITY_ERA, ratifier.SPEED_ERA}
    assert all(
        row["scoring_schedule_id"] == ratifier.SCORING_ID
        for row in rows.values()
    )
    assert rows[ratifier.QUALITY_ERA]["scope"] == "eval_quality"
    assert rows[ratifier.SPEED_ERA]["scope"] == "autopilot_speed"
