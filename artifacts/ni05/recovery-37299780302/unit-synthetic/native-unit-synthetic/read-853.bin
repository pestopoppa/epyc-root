"""TD-21.11..21.14 acceptance: report the per-arm parse-failure rate beside
every accuracy (2026-07-20 standing rule, architect-model-selection-bench.md).

``EvalTower._aggregate`` recovers the SAME ``eval_batch_id`` that
``_score_generation`` stamps into ``scoring_config["_eval_batch_id"]`` before
scoring (from the ``QuestionResult.eval_batch_id`` field, additive), and
reads debug_scorer's arm-keyed parse-failure counters with it, so two arms
scoring CONCURRENTLY in one process (each with its own ``eval_batch_id``)
never mix counts even though the underlying counter dict is module-global —
see debug_scorer.py's ``_PARSE_FAILURE_COUNTS`` module comment for why a
contextvar/thread-local would NOT be safe here (the scoring pool is a plain
``ThreadPoolExecutor``, which does not propagate context to worker threads).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))

from eval_tower import (  # noqa: E402
    DISPOSITION_SCORED,
    EvalTower,
    QuestionResult,
    _load_orchestrator_debug_scorer,
    score_answer_or_error,
)

_scorer = _load_orchestrator_debug_scorer()


def _row(qid: str, *, correct: bool, eval_batch_id: str = "") -> QuestionResult:
    return QuestionResult(
        question_id=qid,
        suite="unit",
        prompt="p",
        expected="e",
        qid=qid,
        answer="a",
        correct=correct,
        disposition=DISPOSITION_SCORED,
        tokens_generated=10,
        elapsed_s=1.0,
        eval_wall_s=10.0,
        eval_batch_id=eval_batch_id,
    )


def _score_unparseable(arm_key: str) -> None:
    """Drive one real model-side parse failure through debug_scorer, bucketed
    under `arm_key` — exactly what `_score_generation` does in production via
    `scoring_config["_eval_batch_id"]`, through the same `score_answer_or_error`
    wrapper. With the ratified EXCLUDE_UNPARSEABLE_ANSWERS=True (E19, re-enabled
    15e1b35a) the scorer RAISES AnswerParseError after recording the failure and
    the wrapper turns that into an EXCLUDED row; with the flag off it is scored
    wrong. The counter must be bumped either way."""
    verdict, reason = score_answer_or_error(
        answer="no letter anywhere in this reply",
        expected="B",
        scoring_method="multiple_choice",
        scoring_config={"_eval_batch_id": arm_key},
    )
    if _scorer.EXCLUDE_UNPARSEABLE_ANSWERS:
        assert verdict is None
        assert reason is not None and "answer_parse_failed[multiple_choice]" in reason
    else:
        assert verdict is False and reason is None


_ARM_KEYS = ("td21-arm-one", "td21-arm-two", None)


def setup_function(_fn) -> None:
    # Isolate from any other test file's arm keys, AND from the unscoped
    # (None) bucket — `_load_orchestrator_debug_scorer()` caches by a fixed
    # sys.modules key shared across every seeding_scoring instance and
    # eval_tower.py in this process, so another test file's un-reset
    # `arm_key=None` call (e.g. a bare `scoring_config={}`) would otherwise
    # leak into `_row(...)`'s default `eval_batch_id=""` here.
    for key in _ARM_KEYS:
        _scorer.reset_parse_failure_stats(arm_key=key)


def teardown_function(_fn) -> None:
    for key in _ARM_KEYS:
        _scorer.reset_parse_failure_stats(arm_key=key)


def test_parse_failure_fields_are_additive_and_present() -> None:
    tower = EvalTower()
    results = [_row("q1", correct=True), _row("q2", correct=False)]
    agg = tower._aggregate(results, tier=1)
    assert "parse_failure_count" in agg.details
    assert "parse_failure_by_method" in agg.details
    assert "parse_failure_rate" in agg.details
    assert agg.details["parse_failure_count"] == 0
    assert agg.details["parse_failure_by_method"] == {}
    assert agg.details["parse_failure_rate"] == 0.0


def test_parse_failure_rate_reported_beside_accuracy_for_one_arm() -> None:
    arm = "td21-arm-one"
    _score_unparseable(arm)
    _score_unparseable(arm)
    results = [_row("q1", correct=True, eval_batch_id=arm) for _ in range(3)] + [
        _row("q2", correct=False, eval_batch_id=arm) for _ in range(1)
    ]
    tower = EvalTower()
    agg = tower._aggregate(results, tier=1)

    # accuracy/quality over the rows handed to _aggregate is unaffected — the
    # parse-failure rate is reported additively beside it, not folded into it.
    assert agg.quality == (3 / 4) * 3.0
    # ...and the rate is reported right beside it.
    assert agg.details["parse_failure_count"] == 2
    assert agg.details["parse_failure_by_method"] == {"multiple_choice": 2}
    assert agg.details["parse_failure_rate"] == 2 / 4


def test_concurrent_arms_do_not_mix_parse_failure_counts() -> None:
    """The coordinator's exact concern: two arms scoring concurrently in one
    process must not have their parse-failure counts mixed."""
    arm_a, arm_b = "td21-arm-one", "td21-arm-two"
    _score_unparseable(arm_a)
    _score_unparseable(arm_a)
    _score_unparseable(arm_a)
    _score_unparseable(arm_b)

    tower = EvalTower()
    agg_a = tower._aggregate([_row("qa", correct=True, eval_batch_id=arm_a)], tier=1)
    assert agg_a.details["parse_failure_count"] == 3

    agg_b = tower._aggregate([_row("qb", correct=True, eval_batch_id=arm_b)], tier=1)
    assert agg_b.details["parse_failure_count"] == 1


def test_aggregate_clears_its_arm_bucket_after_reading() -> None:
    """Reading via _aggregate resets that arm's counters — a long-running
    process must not accumulate one entry per trial forever, and a SECOND
    aggregate call for the same (now-stale) batch id must not double-count."""
    arm = "td21-arm-one"
    _score_unparseable(arm)
    tower = EvalTower()
    first = tower._aggregate([_row("q1", correct=True, eval_batch_id=arm)], tier=1)
    assert first.details["parse_failure_count"] == 1

    second = tower._aggregate([_row("q2", correct=True, eval_batch_id=arm)], tier=1)
    assert second.details["parse_failure_count"] == 0


def test_rows_with_no_eval_batch_id_fall_back_to_default_bucket() -> None:
    # Recovery/replay rows (eval_batch_id="") must not crash _aggregate, and
    # must not accidentally read another arm's counters.
    tower = EvalTower()
    agg = tower._aggregate([_row("q1", correct=True, eval_batch_id="")], tier=1)
    assert agg.details["parse_failure_count"] == 0


def test_empty_results_list_does_not_touch_parse_failure_stats() -> None:
    tower = EvalTower()
    agg = tower._aggregate([], tier=1)
    assert "parse_failure_count" not in agg.details  # matches the existing
    # early-return shape (no `details` dict at all when results is empty) —
    # readers must use .get(), which the empty-results EvalResult already
    # requires for every OTHER details key too.
