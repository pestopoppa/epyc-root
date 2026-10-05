"""Unit tests for EV-10 skill-efficacy gating + surrogate-verifier scoring.

Covers the negative-delta guard (SkillsBench 16/84 regression pattern), strict
aggregate-gain acceptance (SkillOpt), dev/test split discipline, and the CoEvoSkills
leak-free surrogate scoring (proxy reward + opaque-oracle-bit anti-overfit +
cross-family guard). Pure-function tests; no inference, no model loading.
"""

from __future__ import annotations


import pytest

from scripts.autopilot.skill_efficacy import (
    SurrogateFeedback,
    evaluate_skill_efficacy,
    evaluate_skill_efficacy_split,
    require_cross_family,
    surrogate_feedback,
    surrogate_proxy_reward,
)


# ── EV-10a: paired efficacy gate ───────────────────────────────────────────


def test_accept_uniform_improvement():
    v = evaluate_skill_efficacy(
        {"math": 0.50, "coder": 0.60, "web": 0.40},
        {"math": 0.60, "coder": 0.65, "web": 0.45},
    )
    assert v.accept is True
    assert v.aggregate_delta == pytest.approx((0.10 + 0.05 + 0.05) / 3)
    assert v.regressed_suites == []


def test_negative_delta_guard_rejects_despite_aggregate_gain():
    # aggregate improves (+0.30 avg) but one suite craters: SkillsBench 16/84 pattern.
    v = evaluate_skill_efficacy(
        {"math": 0.40, "coder": 0.50, "web": 0.60},
        {"math": 0.95, "coder": 0.90, "web": 0.20},  # web -0.40
        regress_threshold=0.10,
    )
    assert v.accept is False
    assert v.aggregate_delta > 0  # the trap: aggregate looks great
    assert v.regressed_suites and v.regressed_suites[0][0] == "web"
    assert v.regressed_suites[0][1] == pytest.approx(-0.40)


def test_small_regression_within_threshold_allowed():
    # -0.05 drop on one suite is within the 0.10 threshold; net positive -> accept.
    v = evaluate_skill_efficacy(
        {"math": 0.50, "coder": 0.60},
        {"math": 0.70, "coder": 0.55},  # coder -0.05 (within threshold)
        regress_threshold=0.10,
    )
    assert v.accept is True
    assert v.regressed_suites == []


def test_noop_artifact_rejected_under_strict_gain():
    v = evaluate_skill_efficacy({"math": 0.50}, {"math": 0.50})
    assert v.accept is False
    assert "no aggregate gain" in v.reason


def test_require_aggregate_gain_false_allows_neutral():
    v = evaluate_skill_efficacy(
        {"math": 0.50}, {"math": 0.50}, require_aggregate_gain=False
    )
    assert v.accept is True


def test_no_comparable_suites():
    v = evaluate_skill_efficacy({"math": 0.5}, {"coder": 0.6})
    assert v.accept is False
    assert "no comparable suites" in v.reason


def test_nan_and_missing_scores_skipped():
    v = evaluate_skill_efficacy(
        {"math": 0.50, "coder": float("nan"), "web": 0.40},
        {"math": 0.60, "coder": 0.99, "web": 0.50},
    )
    # coder dropped (NaN in 'without'); only math + web compared.
    assert set(v.per_suite_delta) == {"math", "web"}
    assert v.accept is True


def test_threshold_boundary_exactly_at_threshold_not_regressed():
    # delta == -threshold is NOT a regression (strict <).
    v = evaluate_skill_efficacy(
        {"a": 0.50, "b": 0.50},
        {"b": 0.40, "a": 0.71},  # b exactly -0.10; a +0.21 -> net positive
        regress_threshold=0.10,
    )
    assert v.regressed_suites == []
    assert v.accept is True


# ── EV-10a: dev/test split discipline ──────────────────────────────────────


def test_split_requires_both_arms():
    # dev improves, test regresses on a suite -> reject (overfit-to-dev guard).
    v = evaluate_skill_efficacy_split(
        dev_without={"math": 0.50}, dev_with={"math": 0.70},
        test_without={"math": 0.50}, test_with={"math": 0.30},
    )
    assert v.accept is False
    assert "test:" in v.reason
    assert any(s.startswith("test:") for s, _ in v.regressed_suites)


def test_split_accepts_when_both_improve():
    v = evaluate_skill_efficacy_split(
        dev_without={"math": 0.50}, dev_with={"math": 0.60},
        test_without={"math": 0.50}, test_with={"math": 0.58},
    )
    assert v.accept is True
    assert "dev:math" in v.per_suite_delta and "test:math" in v.per_suite_delta


# ── EV-10b: surrogate proxy reward ─────────────────────────────────────────


def test_proxy_reward_fraction():
    assert surrogate_proxy_reward([True, True, False, True]) == pytest.approx(0.75)


def test_proxy_reward_empty_is_zero():
    assert surrogate_proxy_reward([]) == 0.0


def test_proxy_reward_all_pass():
    assert surrogate_proxy_reward([True, True]) == 1.0


# ── EV-10b: feedback decision (anti-overfit) ───────────────────────────────


def test_feedback_dense_when_surrogate_finds_failures():
    fb = surrogate_feedback(0.5)
    assert isinstance(fb, SurrogateFeedback)
    assert fb.dense_feedback is True
    assert fb.opaque_only is False
    assert fb.accepted is False


def test_feedback_opaque_when_surrogate_passes_but_oracle_fails():
    # the CoEvoSkills anti-overfit case: no detail leaks back to the generator.
    fb = surrogate_feedback(1.0, oracle_pass=False)
    assert fb.opaque_only is True
    assert fb.dense_feedback is False
    assert fb.accepted is False


def test_feedback_accept_when_surrogate_and_oracle_agree():
    fb = surrogate_feedback(1.0, oracle_pass=True)
    assert fb.accepted is True
    assert fb.opaque_only is False


def test_feedback_accept_when_surrogate_passes_and_no_oracle():
    fb = surrogate_feedback(1.0, oracle_pass=None)
    assert fb.accepted is True


# ── EV-10b: cross-family guard (injected check) ────────────────────────────


def test_cross_family_ok():
    # injected fn returns True (different families) -> pass.
    assert require_cross_family("qwen3.6", "llama-3", lambda g, v: True) is True


def test_cross_family_same_family_raises():
    with pytest.raises(ValueError, match="same-family"):
        require_cross_family("qwen3.6", "qwen2.5", lambda g, v: False)
