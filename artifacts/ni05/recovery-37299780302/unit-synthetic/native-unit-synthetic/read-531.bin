"""RTG-23: absence is not zero on ANY dominance axis, and the gate checks what it promises.

Two defects, both in `src/autopilot_core/tier_specs.py` before this change:

  * `float(row.get("quality") or 0.0)` scored a NEVER-MEASURED quality as a real 0.0.
    Measured over both journal shards: 231 of 1,372 trial rows carry falsy quality, and
    225 of those ran no eval at all (`eval_details == {}`, no question count, no wall
    clock) — their 0.0 is a writer-substituted placeholder, not a measurement. A
    zero-quality point holding the max rate is unbeatable on rate, so dominance can
    never remove it.
  * `objectives_measurable` promised "carries every axis the live dominance vector
    needs" and checked only the rate.

These tests assert the DISTINCTION (absent vs measured zero) and the gate's coverage.
They deliberately say nothing about whether axis 1 should be raw rate or goodput — that
is the operator's decision in `handoffs/active/objective-task-rate-goodput.md`.
"""
from __future__ import annotations

import types

import pytest

from src.autopilot_core.tier_specs import (
    RATE_4D_OBJECTIVE_POLICY,
    UnmeasuredObjectiveError,
    objectives_from,
    objectives_measurable,
    quality_from,
    quality_from_row,
    rate_objectives_from_row,
    spec_for,
)


def _result(*, quality=1.5, n=50, wall_s=900.0, cost=0.25, reliability=0.9, speed=50.0):
    kwargs = dict(
        tier=1,
        speed=speed,
        cost=cost,
        reliability=reliability,
        n_questions=n,
        eval_wall_s=wall_s,
        question_results=[{"qid": f"q{i}"} for i in range(n)],
        details={"total": n, "eval_wall_s": wall_s},
    )
    if quality is not _ABSENT:
        kwargs["quality"] = quality
    return types.SimpleNamespace(**kwargs)


_ABSENT = object()


def _row(*, quality=1.5, n=50, wall_s=900.0, cost=0.25, reliability=0.9, eval_details=True):
    row = {
        "trial_id": 1,
        "tier": 1,
        "speed": 50.0,
        "cost": cost,
        "reliability": reliability,
        "n_questions": n,
        "eval_wall_s": wall_s,
        "eval_details": (
            {
                "objective_policy_live": RATE_4D_OBJECTIVE_POLICY,
                "question_results": [{"qid": f"q{i}"} for i in range(n)],
                "details": {"total": n, "eval_wall_s": wall_s},
            }
            if eval_details
            else {}
        ),
    }
    if quality is not _ABSENT:
        row["quality"] = quality
    return row


# ── absent quality is not 0.0 ────────────────────────────────────────────────


def test_absent_quality_on_a_result_is_none_not_zero():
    assert quality_from(_result(quality=_ABSENT)) is None
    assert quality_from(types.SimpleNamespace(quality=None)) is None
    assert quality_from(types.SimpleNamespace(quality="")) is None
    assert quality_from(types.SimpleNamespace(quality=float("nan"))) is None


def test_absent_quality_on_a_row_is_none_not_zero():
    assert quality_from_row(_row(quality=_ABSENT)) is None
    assert quality_from_row(_row(quality=None)) is None
    # The shape that produced the 225 journal rows: a bare 0.0 on a row whose eval
    # never ran. The placeholder the writer substitutes IS 0.0, so it is absence.
    placeholder = {"trial_id": 2, "tier": 0, "quality": 0.0, "speed": 0.0,
                   "cost": 0.0, "reliability": 0.0, "eval_details": {}}
    assert quality_from_row(placeholder) is None


def test_absent_quality_never_reads_back_as_a_number():
    """The regression guard: `float(x or 0.0)` returned 0.0 for every case above."""
    for accessor, subject in (
        (quality_from, _result(quality=_ABSENT)),
        (quality_from_row, _row(quality=_ABSENT)),
    ):
        assert accessor(subject) != 0.0
        assert accessor(subject) is None


# ── a MEASURED zero is still a measured zero ─────────────────────────────────


def test_measured_zero_quality_stays_zero_and_stays_measurable():
    result = _result(quality=0.0)
    assert quality_from(result) == 0.0
    assert objectives_measurable(result) is True
    assert objectives_from(result)[0] == 0.0

    row = _row(quality=0.0)
    assert quality_from_row(row) == 0.0
    objectives = rate_objectives_from_row(row)
    assert objectives is not None and objectives[0] == 0.0


# ── objectives_measurable covers EVERY declared axis ─────────────────────────


@pytest.mark.parametrize("axis", ["quality", "cost", "reliability"])
def test_objectives_measurable_is_false_when_any_declared_axis_is_missing(axis):
    result = _result()
    delattr(result, axis)
    assert objectives_measurable(result) is False
    with pytest.raises(UnmeasuredObjectiveError):
        objectives_from(result)


def test_objectives_measurable_still_false_when_only_the_rate_is_missing():
    result = _result(n=0, wall_s=0.0)
    result.question_results = []
    assert objectives_measurable(result) is False


def test_objectives_measurable_true_only_when_all_four_axes_are_measured():
    assert objectives_measurable(_result()) is True
    assert len(objectives_from(_result())) == 4


def test_gate_and_builder_cannot_diverge():
    """Whatever the builder refuses to build, the gate must refuse to call measurable."""
    for subject in (
        _result(quality=_ABSENT),
        _result(quality=None),
        _result(n=0, wall_s=0.0),
    ):
        buildable = True
        try:
            objectives_from(subject)
        except UnmeasuredObjectiveError:
            buildable = False
        assert objectives_measurable(subject) is buildable


# ── the frontier excludes unmeasurable rows ──────────────────────────────────


def test_frontier_reconstruction_skips_rows_with_unmeasured_axes():
    from src.autopilot_core.journal_reconstruction import (
        reconstruct_archive_from_journal_rows,
    )

    measured = _row(quality=1.8)
    measured["timestamp"] = "2026-09-01T00:00:00+00:00"
    unmeasured = {
        "trial_id": 2,
        "tier": 1,
        "quality": 0.0,
        "speed": 0.0,
        "cost": 0.0,
        "reliability": 0.0,
        "eval_details": {},
        "timestamp": "2026-09-01T00:01:00+00:00",
    }
    archive = reconstruct_archive_from_journal_rows(
        [measured, unmeasured],
        None,
        objective_policy=RATE_4D_OBJECTIVE_POLICY,
    )
    assert archive is not None
    trial_ids = {entry["trial_id"] for entry in archive["all_entries"]}
    assert trial_ids == {1}
    frontier = archive["frontiers_by_tier"]["1"]
    assert [entry["trial_id"] for entry in frontier] == [1]
    assert all(entry["objectives"][0] != 0.0 for entry in frontier)


def test_row_builder_refuses_a_row_that_measured_nothing():
    unmeasured = {"trial_id": 3, "tier": 1, "quality": 0.0, "speed": 0.0,
                  "cost": 0.0, "reliability": 0.0, "eval_details": {}}
    assert spec_for(1).objectives_from_row(unmeasured) is None
    assert rate_objectives_from_row(unmeasured) is None
