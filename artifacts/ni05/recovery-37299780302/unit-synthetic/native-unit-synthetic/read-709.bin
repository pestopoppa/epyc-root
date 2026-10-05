"""Tests for AP-27 prompt-free RLVR environment export."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.autopilot.export_rlvr_environment import (
    ROW_SCHEMA_VERSION,
    SUMMARY_SCHEMA_VERSION,
    export_environment_rows,
    main,
    write_jsonl,
)


def _fail_on_bare_constant(token: str):  # pragma: no cover - only hit on failure
    raise AssertionError(f"bare non-finite JSON constant present: {token!r}")


def test_export_environment_rows_strips_private_question_text() -> None:
    rows, summary = export_environment_rows(
        [
            {
                "trial_id": 42,
                "action_type": "deep_eval",
                "tier": 2,
                "quality": 2.4,
                "reliability": 0.9,
                "eval_details": {
                    "ece": 0.05,
                    "auroc": 0.8,
                    "question_results": [
                        {
                            "qid": "q1",
                            "suite": "math",
                            "correct": True,
                            "answer_hash": "sha256:abc",
                            "prompt": "private prompt",
                            "answer": "private answer",
                            "expected": "private expected",
                        }
                    ],
                },
            }
        ],
        source_label="unit",
    )

    assert summary["schema_version"] == SUMMARY_SCHEMA_VERSION
    assert summary["rows"] == 1
    # EV-CONF interim: calibration/discrimination now require a real confidence
    # provenance stamp (details['confidence_is_real']). The exporter builds its
    # result namespace without a details attribute, so exported rows are treated as
    # not-real confidence and carry the confidence_not_real blocker (fail-closed) —
    # the row is therefore blocked from training regardless of its good metrics.
    assert summary["ready_for_training"] == 0
    assert rows[0]["schema_version"] == ROW_SCHEMA_VERSION
    assert rows[0]["reward_policy"] == "ap27_rlvr_tier_reward_v1"
    assert rows[0]["tier"] == 2
    assert rows[0]["ready_for_training"] is False
    assert "confidence_not_real" in rows[0]["blockers"]
    assert rows[0]["suite_counts"] == {"math": 1}
    assert rows[0]["question_results"] == [
        {
            "answer_hash": "sha256:abc",
            "correct": True,
            "qid": "q1",
            "suite": "math",
        }
    ]


def test_export_environment_rows_records_training_blockers() -> None:
    rows, summary = export_environment_rows(
        [
            {
                "eval_result": {
                    "tier": 1,
                    "quality": 2.0,
                    "reliability": 0.8,
                    "eval_details": {"ece": None, "auroc": 0.0},
                }
            }
        ]
    )

    assert rows[0]["ready_for_training"] is False
    # EV-CONF interim: exported rows lack a confidence provenance stamp, so the
    # confidence_not_real blocker is appended after the metric blockers.
    assert rows[0]["blockers"] == [
        "ece_missing",
        "auroc_missing_or_degenerate",
        "confidence_not_real",
    ]
    assert summary["blocked"] == 1
    assert summary["blocker_counts"] == {
        "auroc_missing_or_degenerate": 1,
        "confidence_not_real": 1,
        "ece_missing": 1,
    }


def test_export_threads_real_confidence_provenance_to_ready_for_training() -> None:
    # F2 (safetygate-rlvr-provenance-audit): a T1 row carrying REAL completion-
    # probability confidence (details['confidence_is_real']=True) with finite
    # ece + discriminating auroc must export ready_for_training=True — the
    # confidence_not_real blocker must NOT be appended. Before the fix the export
    # dropped the flag (SimpleNamespace had no details), blocking every row.
    rows, summary = export_environment_rows(
        [
            {
                "tier": 1,
                "quality": 2.4,
                "reliability": 0.95,
                "eval_details": {
                    "ece": 0.05,
                    "auroc": 0.8,
                    "confidence_is_real": True,
                    "scoring_method": "code_execution",
                    "confidence_source_counts": {"completion_probabilities_geomean": 50},
                },
            }
        ],
        source_label="unit",
    )

    assert rows[0]["ready_for_training"] is True
    assert "confidence_not_real" not in rows[0]["blockers"]
    assert rows[0]["blockers"] == []
    assert summary["ready_for_training"] == 1


def test_export_confidence_provenance_from_nested_details() -> None:
    # The flag also rides in the doubly-nested eval_details.details shape — the
    # exporter must recover it there too (fail-closed only when truly absent).
    rows, _ = export_environment_rows(
        [
            {
                "eval_result": {
                    "tier": 1,
                    "quality": 2.2,
                    "reliability": 0.9,
                    "eval_details": {
                        "details": {
                            "ece": 0.04,
                            "auroc": 0.75,
                            "confidence_is_real": True,
                            "scoring_method": "code_execution",
                        }
                    },
                }
            }
        ]
    )
    assert rows[0]["ready_for_training"] is True
    assert "confidence_not_real" not in rows[0]["blockers"]


def test_export_absent_confidence_provenance_stays_fail_closed() -> None:
    # No stamp ⇒ NOT real (fail-closed): the row keeps the confidence_not_real
    # blocker even with otherwise-good metrics.
    rows, _ = export_environment_rows(
        [
            {
                "tier": 1,
                "quality": 2.4,
                "reliability": 0.95,
                "eval_details": {"ece": 0.05, "auroc": 0.8},
            }
        ]
    )
    assert rows[0]["ready_for_training"] is False
    assert "confidence_not_real" in rows[0]["blockers"]


def test_cli_writes_jsonl_and_summary(tmp_path: Path) -> None:
    source = tmp_path / "eval.json"
    output = tmp_path / "rlvr.jsonl"
    summary = tmp_path / "summary.json"
    source.write_text(
        json.dumps(
            {
                "tier": 0,
                "quality": 3.0,
                "reliability": 1.0,
                "question_results": [{"question_id": "q1", "suite": "general", "correct": True}],
            }
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                str(source),
                "--output-jsonl",
                str(output),
                "--summary-json",
                str(summary),
                "--source-label",
                "fixture",
            ]
        )
        == 0
    )

    exported = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert exported[0]["source_label"] == "fixture"
    assert exported[0]["reward_signal"] == "binary_outcome"
    assert json.loads(summary.read_text(encoding="utf-8"))["tier_counts"] == {"0": 1}


def test_nonfinite_metric_flagged_and_written_as_strict_json(tmp_path: Path) -> None:
    # ece=None is coerced to NaN by rlvr_tiers; the exporter must record which
    # metric was non-finite (D2) and still emit strict, jq-parseable JSON.
    rows, summary = export_environment_rows(
        [
            {
                "trial_id": 7,
                "action_type": "deep_eval",
                "tier": 2,
                "quality": 2.4,
                "reliability": 0.9,
                "eval_details": {
                    "ece": None,
                    "auroc": 0.8,
                    "question_results": [
                        {
                            "qid": "q1",
                            "suite": "math",
                            "correct": True,
                            "answer_hash": "sha256:abc",
                        }
                    ],
                },
            }
        ],
        source_label="unit",
    )

    assert rows[0]["metrics_nonfinite"] == ["ece"]
    assert summary["rows_with_nonfinite_metrics"] == 1

    output = tmp_path / "rlvr.jsonl"
    write_jsonl(output, rows)
    raw = output.read_text(encoding="utf-8")
    assert "NaN" not in raw
    assert "Infinity" not in raw

    parsed = [
        json.loads(line, parse_constant=_fail_on_bare_constant)
        for line in raw.splitlines()
        if line.strip()
    ]
    assert parsed[0]["metrics"]["ece"] is None
    assert parsed[0]["metrics_nonfinite"] == ["ece"]


def test_cli_fail_on_blockers_returns_one_after_writing_outputs(tmp_path: Path) -> None:
    source = tmp_path / "eval.json"
    output = tmp_path / "rlvr.jsonl"
    source.write_text(
        json.dumps({"tier": 1, "quality": 1.0, "reliability": 0.5}),
        encoding="utf-8",
    )

    assert main([str(source), "--output-jsonl", str(output), "--fail-on-blockers"]) == 1
    assert output.exists()
