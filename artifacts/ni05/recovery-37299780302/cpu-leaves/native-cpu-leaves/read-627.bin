"""RTG-09: wall-clock task-duration speed dimension in compute_reward.

Precondition for DAR-5 (decision-aware-routing.md): the reward must carry a
speed axis that prices orchestration/tool overhead, not just tokens/sec (which
is gameable through tool calls and blind to it -- DAR handoff measured median
wall/model-compute overhead 1.60x, p90 9.09x over 19,433 tasks).

LANDED DEFAULT-OFF, RATIFIED 2026-09-24 as era E18-routing-reward-duration-axis: a change to compute_reward's
output distribution is a routing_reward instrument-era boundary
(orchestration/instrument_eras.yaml, human-amendment-only) because rewards
feed Q-updates continuously, so the behaviour flip and the era boundary must
land together, by operator ratification
(scripts/operator/ratify_rtg09_duration_reward_20260924.sh, epyc-root repo).
`ScoringConfig.cost_lambda_duration` therefore defaults to 0.0 and
`cost_penalty_lambda` stays at its pre-RTG-09 default (0.15). Every test below
that exercises the duration dimension itself sets `cost_lambda_duration`
explicitly -- there is no helper default that turns it on, so a test can never
accidentally rely on it being live.

These tests exercise `compute_reward`'s new `task_duration_s` parameter and
`ScoringConfig.baseline_duration_by_role` in isolation, mirroring the shape of
`test_q_reward_role_key.py` (the sibling regression suite for the tokens/sec
axis's own "silent miss" defect).
"""

from __future__ import annotations

import pytest

import logging

from orchestration.repl_memory.q_reward import compute_reward
from orchestration.repl_memory.q_scorer import ScoringConfig


class _Entry:
    def __init__(self, outcome: str, data: dict) -> None:
        self.outcome = outcome
        self.data = data
        self.event_type = None


_DURATION_BASELINE = {
    "worker_general": {"p50_s": 10.0, "p90_s": 50.0},
}


def _config(cost_lambda_duration: float, **overrides) -> ScoringConfig:
    """Config that isolates the duration dimension.

    `cost_lambda_duration` has NO default here on purpose -- every caller must
    say explicitly what it wants, since the production default is 0.0
    (inert) and a helper default would hide that from tests meaning to
    exercise the dimension.
    """
    overrides.setdefault("baseline_duration_by_role", _DURATION_BASELINE)
    # Isolate the duration dimension: zero every other cost dimension so the
    # reward delta is attributable to duration alone.
    overrides.setdefault("cost_penalty_lambda", 0.0)
    overrides.setdefault("cost_lambda_quality_gap", 0.0)
    overrides.setdefault("cost_lambda_memory", 0.0)
    overrides.setdefault("baseline_tps_by_role", {})
    return ScoringConfig(cost_lambda_duration=cost_lambda_duration, **overrides)


def _reward(task_duration_s, config, role="worker_general"):
    data = {"producer_role": role}
    return compute_reward(
        _Entry("success", data), [], [], None, data,
        config=config, task_duration_s=task_duration_s,
    )


def test_at_p50_no_duration_penalty():
    """Wall-clock exactly at the role's measured p50 -> zero duration penalty."""
    cfg = _config(cost_lambda_duration=0.20)
    assert _reward(10.0, cfg) == 1.0


def test_faster_than_p50_no_duration_penalty():
    cfg = _config(cost_lambda_duration=0.20)
    assert _reward(2.0, cfg) == 1.0


def test_between_p50_and_p90_graded_penalty():
    """Halfway between p50 (10s) and p90 (50s) -> half of cost_lambda_duration."""
    cfg = _config(cost_lambda_duration=0.20)
    r = _reward(30.0, cfg)  # (30-10)/(50-10) = 0.5
    assert r == 1.0 - 0.5 * 0.20


def test_at_p90_full_weight_penalty():
    cfg = _config(cost_lambda_duration=0.20)
    r = _reward(50.0, cfg)
    assert abs(r - (1.0 - 0.20)) < 1e-9


def test_beyond_p90_saturates_does_not_exceed_full_weight():
    """Far past p90 must not exceed the dimension's own weight (graded, capped)."""
    cfg = _config(cost_lambda_duration=0.20)
    r_at_p90 = _reward(50.0, cfg)
    r_way_past = _reward(5000.0, cfg)
    assert r_way_past == r_at_p90


def test_correctness_gated_no_penalty_on_failure():
    cfg = _config(cost_lambda_duration=0.20)
    data = {"producer_role": "worker_general"}
    r = compute_reward(
        _Entry("failure", data), [], [], None, data,
        config=cfg, task_duration_s=5000.0,
    )
    assert r == -0.5  # failure_reward, no cost dimension applied at all


def test_missing_task_duration_arg_skips_dimension_and_warns(caplog):
    """Caller not wiring task_duration_s must not silently vanish the axis
    (while the axis is actually turned on -- cost_lambda_duration > 0)."""
    from orchestration.repl_memory import q_reward

    q_reward._warned_missing_duration_arg = False
    cfg = _config(cost_lambda_duration=0.20)
    with caplog.at_level(logging.WARNING):
        r = _reward(None, cfg)
    assert r == 1.0  # dimension skipped, not defaulted to a penalty
    assert any("did not pass task_duration_s" in rec.message for rec in caplog.records)


def test_missing_task_duration_arg_silent_when_axis_off(caplog):
    """The default-off axis (cost_lambda_duration == 0.0) must NOT warn about
    a missing task_duration_s -- warning about an inert dimension nobody has
    turned on yet is pure noise."""
    from orchestration.repl_memory import q_reward

    q_reward._warned_missing_duration_arg = False
    cfg = _config(cost_lambda_duration=0.0)
    with caplog.at_level(logging.WARNING):
        r = _reward(None, cfg)
    assert r == 1.0
    assert not [
        rec for rec in caplog.records if "did not pass task_duration_s" in rec.message
    ]


def test_role_missing_duration_baseline_skips_and_warns_not_silent(caplog):
    """A role absent from baseline_duration_by_role must warn, not silently
    award full reward on the duration axis -- the same defect shape as the
    role-key/baseline_tps miss this file's sibling regresses against.
    (Axis turned on for this test.)"""
    from orchestration.repl_memory import q_reward

    q_reward._warned_unpriced_duration_roles.clear()
    cfg = _config(cost_lambda_duration=0.20)
    with caplog.at_level(logging.WARNING):
        r = _reward(5000.0, cfg, role="brand_new_unregistered_role")
    assert r == 1.0
    assert any(
        "no baseline_duration_by_role entry" in rec.message for rec in caplog.records
    )


def test_role_missing_duration_baseline_silent_when_axis_off(caplog):
    """Same coverage gap, but with the axis at its production default (off)
    -- must not warn either, for the same "no noise from an inert axis"
    reason as the missing-arg case above."""
    from orchestration.repl_memory import q_reward

    q_reward._warned_unpriced_duration_roles.clear()
    cfg = _config(cost_lambda_duration=0.0)
    with caplog.at_level(logging.WARNING):
        r = _reward(5000.0, cfg, role="brand_new_unregistered_role")
    assert r == 1.0
    assert not [
        rec for rec in caplog.records if "no baseline_duration_by_role" in rec.message
    ]


def test_known_unpriced_roles_do_not_warn_on_duration(caplog):
    from orchestration.repl_memory import q_reward

    q_reward._warned_unpriced_duration_roles.clear()
    cfg = _config(cost_lambda_duration=0.20)
    with caplog.at_level(logging.WARNING):
        _reward(5000.0, cfg, role="mock")
    assert not [
        r for r in caplog.records if "no baseline_duration_by_role" in r.message
    ]


def test_degenerate_baseline_p90_equals_p50_falls_back_to_ratio():
    """A low-n role whose p50/p90 collapsed to the same value must not divide
    by zero -- falls back to a plain ratio-past-p50 formula."""
    cfg = _config(
        cost_lambda_duration=0.20,
        baseline_duration_by_role={"worker_general": {"p50_s": 10.0, "p90_s": 10.0}},
    )
    # 2x the baseline -> ratio 1.0 past p50, capped at full weight.
    r = _reward(20.0, cfg)
    assert abs(r - (1.0 - 0.20)) < 1e-9


# ---------------------------------------------------------------------------
# DEFAULT-OFF contract (coordinator review, 2026-09-24)
# ---------------------------------------------------------------------------

def test_scoring_config_defaults_are_ratified():
    """Era E18 (RTG-09 ratified 2026-09-24): duration primary at 0.20,
    tokens/sec demoted to 0.05."""
    cfg = ScoringConfig()
    assert cfg.cost_lambda_duration == 0.20
    assert cfg.cost_penalty_lambda == 0.05


def test_pre_e18_config_reward_is_byte_identical_with_and_without_duration():
    """With the pre-E18 weights (duration 0.0, tokens/sec 0.15) compute_reward
    returns the EXACT SAME value whether or not a caller passes
    task_duration_s -- the axis is fully inert when its weight is 0, so the
    pre-boundary reward stays reproducible for replay/rescore across E18.
    """
    cfg = ScoringConfig(cost_lambda_duration=0.0, cost_penalty_lambda=0.15)
    cases = [
        # (outcome, data)
        ("success", {
            "producer_role": "architect_general",
            "tokens_generated": 100,
            "generation_ms": 20_000,
        }),
        ("success", {
            "producer_role": "worker_general",
            "tokens_generated": 500,
            "generation_ms": 5_000,
        }),
        ("failure", {
            "producer_role": "architect_general",
            "tokens_generated": 100,
            "generation_ms": 20_000,
        }),
        ("success", {"producer_role": "brand_new_unregistered_role"}),
    ]
    for outcome, data in cases:
        r_without = compute_reward(
            _Entry(outcome, data), [], [], None, data, config=cfg,
        )
        r_with = compute_reward(
            _Entry(outcome, data), [], [], None, data, config=cfg,
            task_duration_s=99_999.0,
        )
        assert r_without == r_with, (outcome, data, r_without, r_with)
        r_with_none_explicit = compute_reward(
            _Entry(outcome, data), [], [], None, data, config=cfg,
            task_duration_s=None,
        )
        assert r_without == r_with_none_explicit


def test_ratified_defaults_price_a_slow_task():
    """At the ratified defaults a correct task slower than its role's p90 loses
    the full duration weight; one at or under p50 loses nothing on this axis."""
    cfg = ScoringConfig()
    role = next(iter(cfg.baseline_duration_by_role))
    base = cfg.baseline_duration_by_role[role]
    data = {"producer_role": role}
    fast = compute_reward(_Entry("success", data), [], [], None, data, config=cfg,
                          task_duration_s=base["p50_s"])
    slow = compute_reward(_Entry("success", data), [], [], None, data, config=cfg,
                          task_duration_s=base["p90_s"] * 10)
    assert fast - slow == pytest.approx(cfg.cost_lambda_duration)
