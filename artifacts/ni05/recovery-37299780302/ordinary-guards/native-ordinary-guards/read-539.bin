"""Tests for offline reward-oracle adoption manifests."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router.build_offline_reward_oracle_manifest import (
    ADOPTABLE_STATUS,
    MANIFEST_SCHEMA_VERSION,
    build_manifest,
    main,
)


def _decision_gate(status: str = "decision_grade") -> dict:
    blockers = [] if status == "decision_grade" else ["aggregate_spearman_below_gate"]
    return {
        "schema_version": "offline_reward_oracle_decision_gate.v1",
        "status": status,
        "blockers": blockers,
        "criteria": {
            "required_target_sources": {
                "answer_equivalence_final_label": {
                    "min_rows": 30,
                    "min_positive": 5,
                    "min_negative": 5,
                    "min_agreement_at_threshold": 0.75,
                    "min_spearman": 0.2,
                },
            },
        },
        "checks": {
            "rows": {"passed": True, "value": 120, "threshold": 100, "op": ">="},
        },
        "slice_checks": {
            "answer_equivalence_final_label": {
                "present": {"passed": True, "value": True, "op": "exists"},
                "rows": {"passed": True, "value": 50, "threshold": 30, "op": ">="},
                "target_positive": {
                    "passed": True,
                    "value": 20,
                    "threshold": 5,
                    "op": ">=",
                },
                "target_negative": {
                    "passed": True,
                    "value": 30,
                    "threshold": 5,
                    "op": ">=",
                },
                "agreement_at_threshold": {
                    "passed": True,
                    "value": 0.9,
                    "threshold": 0.75,
                    "op": ">=",
                },
                "spearman": {
                    "passed": True,
                    "value": 0.7,
                    "threshold": 0.2,
                    "op": ">=",
                },
            },
        },
    }


def _eval_summary(status: str = "decision_grade") -> dict:
    return {
        "schema_version": "offline_reward_oracle_eval.v1",
        "n": 120,
        "target_positive": 55,
        "target_negative": 65,
        "score": {
            "agreement_at_threshold": 0.91,
            "spearman": 0.72,
            "pearson": 0.74,
            "mean_abs_error": 0.11,
            "confusion": {"tp": 54, "fp": 10, "fn": 1, "tn": 55},
        },
        "calibration": {
            "best": {
                "balanced_accuracy": {
                    "threshold": 0.86,
                    "balanced_accuracy": 0.92,
                },
            },
        },
        "decision_gate": _decision_gate(status),
        "slices": {
            "target_source": {
                "answer_equivalence_final_label": {
                    "n": 50,
                    "target_positive": 20,
                    "target_negative": 30,
                    "agreement_at_threshold": 0.9,
                    "spearman": 0.7,
                    "confusion": {"tp": 19, "fp": 4, "fn": 1, "tn": 26},
                },
            },
        },
        "stress": {
            "groups_evaluated": 8,
            "paraphrase_total": 8,
            "paraphrase_penalized": 0,
            "paraphrase_penalty_rate": 0.0,
            "confound_total": 8,
            "confound_fooled": 0,
            "confound_fooled_rate": 0.0,
            "variant_counts": {"base": 8, "paraphrase": 8, "confound": 8},
        },
    }


def _score_summary(rows: int = 120) -> dict:
    return {
        "schema_version": "offline_reward_oracle_token_coverage_scores.v1",
        "model_id": "deterministic/reference-token-coverage-v1",
        "oracle_score_source": "reference_token_coverage",
        "rows": rows,
        "score_definition": "reference token overlap",
        "score_min": 0.0,
        "score_max": 1.0,
        "score_mean": 0.6,
        "stats": {"rows": rows},
    }


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def test_build_manifest_accepts_decision_grade_report(tmp_path: Path) -> None:
    eval_path = tmp_path / "eval.json"
    score_path = tmp_path / "score_summary.json"
    manifest = build_manifest(
        _eval_summary(),
        _score_summary(),
        eval_path=eval_path,
        score_summary_path=score_path,
    )

    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["status"] == ADOPTABLE_STATUS
    assert manifest["oracle"]["model_id"] == "deterministic/reference-token-coverage-v1"
    assert manifest["oracle"]["oracle_threshold"] == 0.86
    assert manifest["evidence"]["decision_gate"]["status"] == "decision_grade"
    assert manifest["evidence"]["required_target_sources"][
        "answer_equivalence_final_label"
    ]["metrics"]["n"] == 50
    assert manifest["privacy"]["commits_private_rows"] is False
    assert "live routing" in manifest["forbidden_use"]


def test_cli_writes_manifest_for_decision_grade_report(tmp_path: Path) -> None:
    eval_path = _write_json(tmp_path / "eval.json", _eval_summary())
    score_path = _write_json(tmp_path / "score_summary.json", _score_summary())
    output_path = tmp_path / "manifest.json"

    assert main(
        [
            "--eval-json",
            str(eval_path),
            "--score-summary-json",
            str(score_path),
            "--output-json",
            str(output_path),
        ]
    ) == 0

    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert manifest["status"] == ADOPTABLE_STATUS


def test_cli_rejects_blocked_report_without_writing_manifest(tmp_path: Path) -> None:
    eval_path = _write_json(tmp_path / "blocked_eval.json", _eval_summary("blocked"))
    score_path = _write_json(tmp_path / "score_summary.json", _score_summary())
    output_path = tmp_path / "blocked_manifest.json"

    assert main(
        [
            "--eval-json",
            str(eval_path),
            "--score-summary-json",
            str(score_path),
            "--output-json",
            str(output_path),
        ]
    ) == 2
    assert not output_path.exists()


def test_build_manifest_rejects_row_count_mismatch(tmp_path: Path) -> None:
    eval_path = tmp_path / "eval.json"
    score_path = tmp_path / "score_summary.json"

    try:
        build_manifest(
            _eval_summary(),
            _score_summary(rows=119),
            eval_path=eval_path,
            score_summary_path=score_path,
        )
    except ValueError as exc:
        assert "row-count mismatch" in str(exc)
    else:
        raise AssertionError("expected row-count mismatch to fail")
