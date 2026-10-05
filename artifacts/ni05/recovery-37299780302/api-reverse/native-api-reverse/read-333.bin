"""Decision-metric partition filtering for EvalTower."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import eval_tower  # noqa: E402
from eval_tower import EvalTower, QuestionResult  # noqa: E402


def _result_for_question(q: dict, *, correct: bool) -> QuestionResult:
    return QuestionResult(
        question_id=q["id"],
        suite=q["suite"],
        prompt=q["prompt"],
        expected=q["expected"],
        correct=correct,
        tokens_generated=100,
        elapsed_s=1.0,
        eval_concurrency=2,
        eval_wall_s=10.0,
        eval_partition=q.get("eval_partition", "core"),
    )


def test_t1_excludes_tool_sentinel_from_decision_metrics(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPILOT_T1_CORE_ID", raising=False)
    monkeypatch.delenv("AUTOPILOT_T1_CORE_PATH", raising=False)
    tower = EvalTower()
    tower._pool = {
        "math": [
            {
                "id": "core",
                "suite": "math",
                # Every production pool row carries a difficulty tier; the T1 draw is
                # tier-stratified, so an untiered fixture row satisfies no tier target.
                "tier": 1,
                "prompt": "2+2?",
                "expected": "4",
            }
        ]
    }
    monkeypatch.setattr(
        EvalTower,
        "_load_tool_sentinels",
        lambda self: [
            {
                "id": "tool",
                "suite": "tool_use",
                "prompt": "Use the secret tool.",
                "expected": "secret",
            }
        ],
    )

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        return [
            _result_for_question(q, correct=q.get("eval_partition") == "core")
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    result = tower.eval_t1(n=1, seed=7)

    assert result.quality == 3.0
    assert result.n_questions == 1
    assert len(result.question_results) == 2
    assert result.details["tool_sentinel_decision_excluded"] is True
    assert result.details["decision_excluded_partitions"] == ["tool_sentinel"]
    assert result.details["partition_total_counts"] == {"core": 1, "tool_sentinel": 1}
    assert result.speed_metric_mode == "median_request_tps_partition_filtered"
    assert result.speed == result.median_request_speed == 100.0
    assert result.details["test_profile"]["n_questions"] == 1
    assert result.details["test_profile"]["full_batch_n_questions"] == 2
    assert result.details["dataset_content_sha256"] != result.details[
        "full_batch_dataset_content_sha256"
    ]


def test_t1_audit_shadow_keeps_decision_dataset_identity(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPILOT_T1_CORE_ID", raising=False)
    monkeypatch.delenv("AUTOPILOT_T1_CORE_PATH", raising=False)
    monkeypatch.setenv("AUTOPILOT_W6_AUDIT_BLOCK", "1")
    monkeypatch.setenv("AUTOPILOT_W6_AUDIT_N", "1")
    tower = EvalTower()
    tower._pool = {
        "math": [
            {
                "id": "core",
                "suite": "math",
                # Every production pool row carries a difficulty tier; the T1 draw is
                # tier-stratified, so an untiered fixture row satisfies no tier target.
                "tier": 1,
                "prompt": "2+2?",
                "expected": "4",
            }
        ]
    }
    monkeypatch.setattr(EvalTower, "_load_tool_sentinels", lambda self: [])
    monkeypatch.setattr(
        EvalTower,
        "_load_audit_block",
        lambda self, core_questions, audit_n, trial_id, core_id: (
            [
                {
                    "id": "audit",
                    "suite": "math",
                    "prompt": "3+3?",
                    "expected": "6",
                }
            ],
            123,
        ),
    )

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        return [
            _result_for_question(q, correct=q.get("eval_partition") == "core")
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    audit_result = tower.eval_t1(n=1, seed=7, trial_id=10)

    tower_no_audit = EvalTower()
    tower_no_audit._pool = tower._pool
    monkeypatch.setenv("AUTOPILOT_W6_AUDIT_BLOCK", "0")
    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)
    no_audit_result = tower_no_audit.eval_t1(n=1, seed=7, trial_id=10)

    assert audit_result.quality == no_audit_result.quality == 3.0
    assert audit_result.details["dataset_content_sha256"] == no_audit_result.details[
        "dataset_content_sha256"
    ]
    assert audit_result.details["audit_shadow_excluded_partitions"] == ["audit"]
    assert audit_result.details["test_profile"]["n_questions"] == 1
    assert audit_result.details["test_profile"]["full_batch_n_questions"] == 2


def test_t2_excludes_tool_sentinel_from_decision_metrics(monkeypatch) -> None:
    tower = EvalTower()
    tower._pool = {
        "math": [
            {
                "id": "core",
                "suite": "math",
                # Every production pool row carries a difficulty tier; the T1 draw is
                # tier-stratified, so an untiered fixture row satisfies no tier target.
                "tier": 1,
                "prompt": "2+2?",
                "expected": "4",
            }
        ]
    }
    monkeypatch.setattr(
        EvalTower,
        "_load_tool_sentinels",
        lambda self: [
            {
                "id": "tool",
                "suite": "tool_use",
                "prompt": "Use the secret tool.",
                "expected": "secret",
            }
        ],
    )
    monkeypatch.setattr(
        eval_tower,
        "_sample_scoreable_eval_questions",
        lambda pool, n, rng, **_kwargs: list(pool["math"]),
    )

    def _fake_eval_batch(self, questions, client, **_kwargs):  # noqa: ANN001, ARG001
        return [
            _result_for_question(q, correct=q.get("eval_partition") == "core")
            for q in questions
        ]

    monkeypatch.setattr(EvalTower, "_eval_batch", _fake_eval_batch)

    result = tower.eval_t2(n=1, seed=7)

    assert result.quality == 3.0
    assert result.n_questions == 1
    assert len(result.question_results) == 2
    assert result.details["tool_sentinel_decision_excluded"] is True
    assert result.speed_metric_mode == "median_request_tps_partition_filtered"
