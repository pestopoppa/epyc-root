from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router import summarize_offline_reward_verifier_decision as decision


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _calibration_summary(path: Path, *, status: str = "not_promotion_grade") -> Path:
    return _write_json(
        path,
        {
            "schema_version": "verifier_calibration_robustness.v1",
            "data_path": "data-a.npz",
            "aggregate": {
                "decision": {"status": status, "blockers": ["calibration_failed"]},
                "methods": {
                    "temperature_bias": {
                        "calibrated_pass_count": 0,
                        "calibrated_pass_rate": 0.0,
                        "calibrated_auc": {"mean": 0.71},
                        "calibrated_ece": {"mean": 0.12},
                        "calibrated_brier": {"mean": 0.21},
                    },
                    "isotonic": {
                        "calibrated_pass_count": 1,
                        "calibrated_pass_rate": 0.1,
                        "calibrated_auc": {"mean": 0.81},
                        "calibrated_ece": {"mean": 0.09},
                        "calibrated_brier": {"mean": 0.18},
                    },
                },
            },
        },
    )


def _model_family_summary(path: Path, *, status: str = "not_promotion_grade") -> Path:
    return _write_json(
        path,
        {
            "schema_version": "offline_reward_verifier_model_family_robustness.v1",
            "data_path": "data-b.npz",
            "aggregate": {
                "decision": {"status": status, "blockers": ["families_failed"]},
                "families": {
                    "logistic_l2": {
                        "methods": {
                            "raw": {
                                "pass_count": 0,
                                "pass_rate": 0.0,
                                "auc": {"mean": 0.75},
                                "ece": {"mean": 0.11},
                                "brier": {"mean": 0.19},
                            }
                        }
                    },
                    "random_forest": {
                        "methods": {
                            "isotonic": {
                                "pass_count": 0,
                                "pass_rate": 0.0,
                                "auc": {"mean": 0.86},
                                "ece": {"mean": 0.08},
                                "brier": {"mean": 0.15},
                            }
                        }
                    },
                },
            },
        },
    )


def test_decision_stops_current_family_after_repeated_failed_sweeps(tmp_path: Path) -> None:
    cal_a = _calibration_summary(tmp_path / "cal-a.json")
    cal_b = _calibration_summary(tmp_path / "cal-b.json")
    model = _model_family_summary(tmp_path / "model.json")

    summary = decision.build_decision(
        [decision.parse_attempt(path) for path in [cal_a, cal_b, model]],
        min_failed_artifacts=3,
        generated_at="2026-06-21T00:00:00+00:00",
    )

    assert summary["decision"]["status"] == "stop_current_verifier_family"
    assert summary["decision"]["runtime_gate_change_allowed"] is False
    assert summary["artifact_counts"]["failed"] == 3
    assert summary["best_attempt"]["best_label"] == "isotonic"
    assert "model_family_sweeps_failed" in summary["decision"]["blockers"]


def test_promotion_candidate_allows_human_review_but_not_silent_enable(tmp_path: Path) -> None:
    cal = _calibration_summary(tmp_path / "cal.json", status="promotion_grade")
    summary = decision.build_decision(
        [decision.parse_attempt(cal)],
        min_failed_artifacts=3,
        generated_at="2026-06-21T00:00:00+00:00",
    )

    assert summary["decision"]["status"] == "promotion_candidate"
    assert summary["decision"]["runtime_gate_change_allowed"] is True
    assert summary["decision"]["recommended_next"] == "review_promotion_artifact_before_runtime_gate"


def test_run_writes_json_and_markdown(tmp_path: Path) -> None:
    cal_a = _calibration_summary(tmp_path / "cal-a.json")
    cal_b = _calibration_summary(tmp_path / "cal-b.json")
    model = _model_family_summary(tmp_path / "model.json")
    out_json = tmp_path / "out" / "summary.json"
    out_md = tmp_path / "out" / "summary.md"

    summary = decision.run(
        decision.build_parser().parse_args(
            [
                "--summary",
                str(cal_a),
                "--summary",
                str(cal_b),
                "--summary",
                str(model),
                "--output-json",
                str(out_json),
                "--output-md",
                str(out_md),
                "--generated-at",
                "2026-06-21T00:00:00+00:00",
            ]
        )
    )

    assert summary["decision"]["status"] == "stop_current_verifier_family"
    assert json.loads(out_json.read_text())["schema_version"] == decision.SCHEMA_VERSION
    assert "# Offline Reward Verifier Decision" in out_md.read_text()
