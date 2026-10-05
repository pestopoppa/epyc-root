"""ETR-1: agent/config-caused (`task_failed`) rows score 0 and stay in the
quality denominator; platform-caused (`infra_failed`/`scoring_failed`) rows
stay excluded; legacy rows (no `disposition`) keep their pre-ETR-1 accounting
exactly.

Ruling: handoffs/active/eval-tower-loop-robustness-audit-2026-07-20.md (ETR-1),
operator ruling 2026-09-23.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from eval_tower import (  # noqa: E402
    DISPOSITION_INFRA_FAILED,
    DISPOSITION_SCORED,
    DISPOSITION_TASK_FAILED,
    EvalTower,
    QUALITY_DENOMINATOR_POLICY,
    QuestionResult,
)


def _row(
    qid: str,
    *,
    correct: bool,
    disposition: str = DISPOSITION_SCORED,
    error: str | None = None,
    suite: str = "unit",
) -> QuestionResult:
    return QuestionResult(
        question_id=qid,
        suite=suite,
        prompt="p",
        expected="e",
        qid=qid,
        answer="a",
        correct=correct,
        error=error,
        disposition=disposition,
        tokens_generated=10,
        elapsed_s=1.0,
        eval_wall_s=10.0,
    )


def test_mixed_scored_task_failed_infra_failed_denominator() -> None:
    """6 scored-correct, 2 task_failed, 2 infra_failed → quality = 6/8 * 3.0."""
    tower = EvalTower()
    results = [_row(f"ok{i}", correct=True) for i in range(6)]
    results += [
        _row(
            f"tf{i}",
            correct=False,
            disposition=DISPOSITION_TASK_FAILED,
            error="agent_produced_error",
        )
        for i in range(2)
    ]
    results += [
        _row(
            f"if{i}",
            correct=False,
            disposition=DISPOSITION_INFRA_FAILED,
            error="connect_error",
        )
        for i in range(2)
    ]

    agg = tower._aggregate(results, tier=1)

    assert agg.n_questions == 10
    assert agg.details["n_scored"] == 8
    assert agg.details["quality_denominator"] == 8
    assert agg.quality == (6 / 8) * 3.0
    assert agg.details["task_failed"] == 2
    assert agg.details["infra_failed"] == 2
    assert agg.task_failed_count == 2
    assert agg.infra_failed_count == 2
    assert agg.quality_measured is True


def test_all_task_failed_scores_zero_but_is_measured() -> None:
    """A batch that is entirely task_failed has quality=0.0 AND quality_measured=True —
    0.0 is a real measurement here, not the "nothing was scored" placeholder."""
    tower = EvalTower()
    results = [
        _row(f"tf{i}", correct=False, disposition=DISPOSITION_TASK_FAILED, error="boom")
        for i in range(5)
    ]

    agg = tower._aggregate(results, tier=1)

    assert agg.quality == 0.0
    assert agg.quality_measured is True
    assert agg.quality_unmeasured_reason == ""
    assert agg.details["n_scored"] == 5
    assert agg.details["task_failed"] == 5


def test_all_infra_failed_leaves_quality_unmeasured() -> None:
    """Unchanged behaviour: a batch that is entirely infra_failed still reports
    quality_measured=False — nothing was ever scored."""
    tower = EvalTower()
    results = [
        _row(f"if{i}", correct=False, disposition=DISPOSITION_INFRA_FAILED, error="down")
        for i in range(4)
    ]

    agg = tower._aggregate(results, tier=1)

    assert agg.quality_measured is False
    assert agg.quality_unmeasured_reason == "all_rows_infra_failed"
    assert agg.details["n_scored"] == 0
    assert agg.details["task_failed"] == 0
    assert agg.details["infra_failed"] == 4


def test_legacy_rows_without_disposition_keep_old_accounting() -> None:
    """A row built with no explicit `disposition` (the dataclass default,
    `scored`) that nonetheless carries an `error` is NOT reinterpreted as
    task_failed — it keeps exactly the pre-ETR-1 accounting: excluded
    because `r.error` is truthy."""
    tower = EvalTower()
    results = [
        _row("ok1", correct=True),
        _row("ok2", correct=False),
        QuestionResult(
            question_id="legacy_err",
            suite="unit",
            prompt="p",
            expected="e",
            qid="legacy_err",
            answer="",
            correct=False,
            error="scorer_unavailable",
            # disposition intentionally omitted — uses the dataclass default
            elapsed_s=1.0,
            eval_wall_s=10.0,
        ),
    ]

    agg = tower._aggregate(results, tier=1)

    assert agg.details["n_scored"] == 2
    assert agg.details["quality_denominator"] == 2
    assert agg.quality == 1.5
    assert agg.details["task_failed"] == 0
    assert agg.details["errors"] == 1
    assert agg.details["scoring_errors"] == 1


def test_policy_constant_appears_in_details() -> None:
    tower = EvalTower()
    results = [_row("ok1", correct=True)]

    agg = tower._aggregate(results, tier=1)

    assert agg.details["quality_denominator_policy"] == QUALITY_DENOMINATOR_POLICY
    assert QUALITY_DENOMINATOR_POLICY == "task_failed_scores_zero_v1"
