"""W3 live-vector flip (2026-08-04): dominance axis 1 is questions/hour, not tokens/second.

These tests DERIVE the expected values from the metric definition rather than restating
literals, so they fail if the objective changes meaning — not merely if a number moves.
"""
from __future__ import annotations

import types

import pytest

from src.autopilot_core.pareto_math import dominates
from src.autopilot_core.tier_specs import (
    LEGACY_OBJECTIVE_POLICY,
    PRE_RESOURCE_LANES_RATE_4D_OBJECTIVE_POLICY,
    RATE_4D_OBJECTIVE_POLICY,
    RESOURCE_LANES_V2_RATE_4D_OBJECTIVE_POLICY,
    UnmeasuredObjectiveError,
    legacy_objectives_from,
    objectives_from,
    objectives_measurable,
    seq_task_rate_qph_from,
    spec_for,
)


def _result(*, n, wall_s, quality=1.5, cost=0.25, reliability=0.9, speed=50.0):
    """An EvalResult-like stub carrying a per-question ledger of `n` distinct qids."""
    return types.SimpleNamespace(
        tier=1,
        quality=quality,
        speed=speed,
        cost=cost,
        reliability=reliability,
        n_questions=n,
        eval_wall_s=wall_s,
        question_results=[{"qid": f"q{i}"} for i in range(n)],
        details={"total": n, "eval_wall_s": wall_s},
    )


def test_live_axis1_is_questions_per_hour_not_tokens_per_second():
    """Axis 1 must equal the rate metric, and must NOT equal the legacy speed field."""
    r = _result(n=50, wall_s=900.0)
    objs = objectives_from(r)
    expected_rate = seq_task_rate_qph_from(r)

    assert expected_rate is not None
    assert objs[1] == pytest.approx(expected_rate)
    # Derived, not asserted as a constant: n questions over wall-hours.
    assert objs[1] == pytest.approx(50 / (900.0 / 3600.0))
    # And it is a genuinely different axis from the legacy one.
    assert objs[1] != pytest.approx(legacy_objectives_from(r)[1])


def test_mixed_split_scheduler_bumps_live_rate_policy_version():
    assert PRE_RESOURCE_LANES_RATE_4D_OBJECTIVE_POLICY == "task_rate_4d_v1"
    assert RESOURCE_LANES_V2_RATE_4D_OBJECTIVE_POLICY == "task_rate_4d_v2_resource_lanes"
    assert RATE_4D_OBJECTIVE_POLICY == "task_rate_4d_v7_physical_cohort_exclusion"
    assert RATE_4D_OBJECTIVE_POLICY != RESOURCE_LANES_V2_RATE_4D_OBJECTIVE_POLICY
    assert RATE_4D_OBJECTIVE_POLICY != PRE_RESOURCE_LANES_RATE_4D_OBJECTIVE_POLICY


def test_live_vector_keeps_the_4d_shape_consumers_index_positionally():
    """safety_gate refuses len<4 and reads [2]/[3]; a 3D vector would silently block it."""
    objs = objectives_from(_result(n=50, wall_s=900.0))
    assert len(objs) == len(legacy_objectives_from(_result(n=50, wall_s=900.0)))
    assert len(objs) >= 4


def test_rate_axis_responds_to_wall_clock_not_token_speed():
    """Halving wall time doubles the objective; changing token speed alone does not."""
    fast = objectives_from(_result(n=50, wall_s=450.0))
    slow = objectives_from(_result(n=50, wall_s=900.0))
    assert fast[1] == pytest.approx(2 * slow[1])

    # Same rate, wildly different tokens/second -> identical dominance axis.
    same_a = objectives_from(_result(n=50, wall_s=900.0, speed=10.0))
    same_b = objectives_from(_result(n=50, wall_s=900.0, speed=99.0))
    assert same_a[1] == pytest.approx(same_b[1])


def test_unmeasured_rate_raises_instead_of_scoring_zero():
    """Absence must not become 0 qph — that is a real, maximally-bad throughput."""
    missing = types.SimpleNamespace(
        tier=1, quality=1.5, speed=50.0, cost=0.25, reliability=0.9,
        n_questions=None, eval_wall_s=None, question_results=[], details={},
    )
    assert objectives_measurable(missing) is False
    with pytest.raises(UnmeasuredObjectiveError):
        objectives_from(missing)


def test_aborted_batch_is_unmeasured_not_astronomically_fast():
    """A batch below the s/question validity floor scored millions of qph before."""
    aborted = _result(n=65, wall_s=0.054)
    assert objectives_measurable(aborted) is False
    with pytest.raises(UnmeasuredObjectiveError):
        objectives_from(aborted)


def test_dominates_refuses_mixed_policy_comparison():
    """zip() used to truncate, comparing qph against t/s and reliability against -cost."""
    four_d = (1.5, 200.0, -0.25, 0.9)
    three_d = (1.5, 200.0, 0.9)
    with pytest.raises(ValueError):
        dominates(three_d, four_d)
    with pytest.raises(ValueError):
        dominates(four_d, three_d)


def test_row_replay_uses_the_policy_the_row_was_recorded_under():
    """Pre-flip rows have no ledger; replaying them under the rate policy empties the archive."""
    from_row = spec_for(1).objectives_from_row

    legacy_row = {
        "quality": 1.5, "speed": 50.0, "cost": 0.25, "reliability": 0.9,
        "eval_details": {"objective_policy_live": LEGACY_OBJECTIVE_POLICY},
    }
    rebuilt = from_row(legacy_row)
    assert rebuilt is not None, "a pre-flip row must still replay"
    assert rebuilt[1] == pytest.approx(legacy_row["speed"])

    rate_row = {
        "quality": 1.5, "speed": 50.0, "cost": 0.25, "reliability": 0.9,
        "n_questions": 50, "eval_wall_s": 900.0,
        "eval_details": {
            "objective_policy_live": RATE_4D_OBJECTIVE_POLICY,
            "eval_wall_s": 900.0,
            "question_results": [{"qid": f"q{i}"} for i in range(50)],
        },
    }
    rebuilt_rate = from_row(rate_row)
    assert rebuilt_rate is not None
    assert rebuilt_rate[1] == pytest.approx(50 / (900.0 / 3600.0))
    assert rebuilt_rate[1] != pytest.approx(rate_row["speed"])

    prior_rate_row = {
        **rate_row,
        "eval_details": {
            **rate_row["eval_details"],
            "objective_policy_live": PRE_RESOURCE_LANES_RATE_4D_OBJECTIVE_POLICY,
        },
    }
    rebuilt_prior_rate = from_row(prior_rate_row)
    assert rebuilt_prior_rate is not None
    assert rebuilt_prior_rate[1] == pytest.approx(50 / (900.0 / 3600.0))


# The rate guard must gate the ARCHIVE WRITES only, never the whole post-eval branch:
# `gate.update_baseline` lives inside that branch and promotes on QUALITY, an axis that is
# measured perfectly well when the rate is missing. The first version of the guard
# swallowed the branch and silently suppressed quality baseline promotion whenever a task
# rate was unavailable — two independent axes coupled by one guard.
#
# That regression is covered behaviourally, not by scanning this source file: it was caught
# by `test_autopilot_sequential_wiring.py::
# test_run_loop_inner_forced_seq_fresh_eval_bypasses_controller_planner`, which asserts
# `baseline_update_calls == [(True, 0)]` and went to `[]` the moment the guard over-reached.
# A source-text assertion here was tried and removed: it counted `else:` tokens and matched
# unrelated `else None` ternaries, i.e. it failed for reasons unrelated to the invariant.


def test_unstamped_row_defaults_to_legacy():
    """Every row written before the flip is unstamped; it must not be read as a rate."""
    unstamped = {"quality": 1.5, "speed": 50.0, "cost": 0.25, "reliability": 0.9}
    rebuilt = spec_for(1).objectives_from_row(unstamped)
    assert rebuilt is not None
    assert rebuilt[1] == pytest.approx(unstamped["speed"])
