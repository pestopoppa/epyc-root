"""Tests for AP-27 deterministic RLVR tier reward contracts."""

from __future__ import annotations

from types import SimpleNamespace

from src.autopilot_core.rlvr_tiers import (
    RLVR_REWARD_POLICY,
    T0_SUCCESS_ACCURACY,
    T0_SUCCESS_RELIABILITY,
    rlvr_reward_from_result,
    spec_for_rlvr_tier,
)


def _result(confidence_is_real: bool | None = True, **kw) -> SimpleNamespace:
    base = {
        "tier": 1,
        "quality": 0.0,
        "reliability": 1.0,
        "ece": 0.0,
        "auroc": 1.0,
        "question_results": [],
    }
    base.update(kw)
    ns = SimpleNamespace(**base)
    # EV-CONF: eval_tower stamps confidence provenance in details['confidence_is_real'].
    # Default True so calibration/discrimination-bearing tests represent real-confidence
    # runs; pass confidence_is_real=None to model a LEGACY row with no provenance stamp
    # (no details attribute at all), or False for an explicit stub/mixed batch.
    if confidence_is_real is not None:
        # ESC-7 Option A: calibration/discrimination are code-domain-scoped;
        # stamp fixtures as code_execution so real-confidence tests represent
        # the decision-capable domain (math is observational-only).
        ns.details = {
            "confidence_is_real": confidence_is_real,
            "scoring_method": "code_execution",
        }
    return ns


def test_t0_reward_is_binary_state_match() -> None:
    # RLVR-2: T0 saturates ~2.4/3.0, so success now keys off T0_SUCCESS_ACCURACY
    # (0.8), not exact 1.0 — otherwise the binary reward is constant-0 / gradient-free.
    assert T0_SUCCESS_ACCURACY == 0.8
    assert T0_SUCCESS_RELIABILITY == 0.9

    passed = rlvr_reward_from_result(_result(tier=0, quality=2.7, reliability=1.0))  # acc 0.9
    saturated = rlvr_reward_from_result(_result(tier=0, quality=2.5, reliability=0.9))  # acc 0.833
    failed = rlvr_reward_from_result(_result(tier=0, quality=2.1, reliability=1.0))  # acc 0.7

    assert passed.policy == RLVR_REWARD_POLICY
    assert passed.reward_signal == "binary_outcome"
    assert passed.reward == 1.0
    assert passed.ready_for_training
    # A saturated-good run (~2.5/3.0) now earns reward 1.0 instead of the old 0.
    assert saturated.reward == 1.0
    assert failed.reward == 0.0  # below the relaxed accuracy floor
    # Boundary note: quality exactly 2.4 → 2.4/3.0 == 0.7999999999999999 (FP just
    # below 0.8), so the exact saturation point sits a hair under the floor.
    assert rlvr_reward_from_result(_result(tier=0, quality=2.4, reliability=0.9)).reward == 0.0


def test_t0_reliability_floor_still_gates_success() -> None:
    # RLVR-2: accuracy alone is not enough; reliability must clear T0_SUCCESS_RELIABILITY.
    high_acc_low_rel = rlvr_reward_from_result(_result(tier=0, quality=3.0, reliability=0.85))
    assert high_acc_low_rel.reward == 0.0


def test_t0_missing_required_metrics_block_training() -> None:
    # RLVR-1: T0 required_metrics = (quality, reliability); a missing/non-finite
    # required metric must surface as a blocker instead of coercing silently to 0.0.
    missing_reliability = rlvr_reward_from_result(_result(tier=0, quality=3.0, reliability=None))
    assert "reliability_missing_or_nonfinite" in missing_reliability.blockers
    assert not missing_reliability.ready_for_training

    missing_quality = rlvr_reward_from_result(_result(tier=0, quality=None, reliability=1.0))
    assert "quality_missing_or_nonfinite" in missing_quality.blockers
    assert not missing_quality.ready_for_training


def test_t1_missing_quality_blocks_training() -> None:
    # RLVR-1: quality is a required metric for T1+ too.
    reward = rlvr_reward_from_result(
        _result(tier=1, quality=None, reliability=0.9, ece=0.1, auroc=0.8)
    )
    assert reward.blockers == ("quality_missing_or_nonfinite",)
    assert not reward.ready_for_training


def test_subchance_auroc_earns_no_discrimination_credit() -> None:
    # RLVR-3: AUROC <= 0.5 is anti-discriminative; it must earn 0 discrimination
    # credit rather than positive clamp01(auroc). Note auroc > 0 avoids the separate
    # auroc_missing_or_degenerate blocker, isolating the discrimination change.
    subchance = rlvr_reward_from_result(
        _result(tier=1, quality=2.4, reliability=0.9, ece=0.05, auroc=0.40)
    )
    at_chance = rlvr_reward_from_result(
        _result(tier=1, quality=2.4, reliability=0.9, ece=0.05, auroc=0.50)
    )
    above_chance = rlvr_reward_from_result(
        _result(tier=1, quality=2.4, reliability=0.9, ece=0.05, auroc=0.65)
    )
    assert subchance.components["discrimination"] == 0.0
    assert at_chance.components["discrimination"] == 0.0
    assert above_chance.components["discrimination"] == 0.65


def test_t1_reward_uses_calibration_and_discrimination() -> None:
    good = rlvr_reward_from_result(
        _result(tier=1, quality=2.4, reliability=0.9, ece=0.05, auroc=0.85)
    )
    poorly_calibrated = rlvr_reward_from_result(
        _result(tier=1, quality=2.4, reliability=0.9, ece=0.45, auroc=0.55)
    )

    assert good.reward_signal == "calibrated_continuous"
    assert good.ready_for_training
    assert good.reward > poorly_calibrated.reward
    assert good.components == {
        "accuracy": 0.7999999999999999,
        "reliability": 0.9,
        "calibration": 0.95,
        "discrimination": 0.85,
    }


def test_calibration_discrimination_credited_only_when_confidence_is_real() -> None:
    # EV-CONF interim: flag True + finite ece/auroc → components compute as before.
    real = rlvr_reward_from_result(
        _result(tier=1, quality=2.4, reliability=0.9, ece=0.05, auroc=0.85,
                confidence_is_real=True)
    )
    assert real.components["calibration"] == 0.95
    assert real.components["discrimination"] == 0.85
    assert "confidence_not_real" not in real.blockers
    assert real.ready_for_training


def test_legacy_row_without_confidence_provenance_zeros_calibration() -> None:
    # EV-CONF interim: a legacy row carries no details['confidence_is_real'] stamp
    # (null-safe/fail-closed) → BOTH confidence-derived components zero out and the
    # run is blocked from training with a distinct blocker.
    legacy = rlvr_reward_from_result(
        _result(tier=1, quality=2.4, reliability=0.9, ece=0.05, auroc=0.85,
                confidence_is_real=None)  # no details attribute at all
    )
    assert legacy.components["calibration"] == 0.0
    assert legacy.components["discrimination"] == 0.0
    assert "confidence_not_real" in legacy.blockers
    assert not legacy.ready_for_training


def test_confidence_flag_false_zeros_calibration_like_legacy() -> None:
    # EV-CONF interim: an explicit False (stub or mixed-provenance batch) neutralizes
    # calibration/discrimination identically to a legacy row.
    stub = rlvr_reward_from_result(
        _result(tier=1, quality=2.4, reliability=0.9, ece=0.05, auroc=0.85,
                confidence_is_real=False)
    )
    assert stub.components["calibration"] == 0.0
    assert stub.components["discrimination"] == 0.0
    assert "confidence_not_real" in stub.blockers
    assert not stub.ready_for_training


def test_t2_process_reward_also_gates_confidence_components() -> None:
    # EV-CONF interim: the process-attributed (T2) path zeros calibration/discrimination
    # under not-real confidence too, but process_integrity is unaffected.
    gated = rlvr_reward_from_result(
        _result(
            tier=2, quality=2.0, reliability=0.75, ece=0.1, auroc=0.8,
            question_results=[{"qid": "q1", "correct": True}],
            confidence_is_real=False,
        )
    )
    assert gated.components["calibration"] == 0.0
    assert gated.components["discrimination"] == 0.0
    assert gated.components["process_integrity"] == 1.0
    assert "confidence_not_real" in gated.blockers
    assert not gated.ready_for_training


def test_t0_binary_reward_unaffected_by_confidence_provenance() -> None:
    # T0 is a pure accuracy+reliability sentinel — it has no confidence-derived
    # components, so a legacy row must NOT acquire the confidence_not_real blocker.
    t0 = rlvr_reward_from_result(
        _result(tier=0, quality=2.7, reliability=1.0, confidence_is_real=None)
    )
    assert t0.reward == 1.0
    assert "confidence_not_real" not in t0.blockers
    assert t0.ready_for_training


def test_t1_reward_reports_missing_calibration_blockers() -> None:
    reward = rlvr_reward_from_result(_result(tier=1, quality=2.0, ece=float("nan"), auroc=0.0))

    assert reward.reward_signal == "calibrated_continuous"
    assert not reward.ready_for_training
    assert reward.blockers == ("ece_missing", "auroc_missing_or_degenerate")


def test_t2_reward_requires_process_rows_and_penalizes_broken_process() -> None:
    clean = rlvr_reward_from_result(
        _result(
            tier=2,
            quality=2.0,
            reliability=0.75,
            ece=0.1,
            auroc=0.8,
            question_results=[
                {"qid": "q1", "correct": True},
                {"qid": "q2", "correct": False, "partial": True},
            ],
        )
    )
    missing = rlvr_reward_from_result(
        _result(tier=2, quality=2.0, reliability=0.75, ece=0.1, auroc=0.8)
    )

    assert clean.reward_signal == "process_attributed"
    assert clean.metrics["process_integrity"] == 0.5
    assert clean.ready_for_training
    assert not missing.ready_for_training
    assert missing.blockers == ("question_results_missing",)


def test_unknown_higher_tier_uses_process_contract() -> None:
    spec = spec_for_rlvr_tier(3)
    reward = rlvr_reward_from_result(
        _result(
            tier=3,
            quality=3.0,
            reliability=1.0,
            ece=0.0,
            auroc=1.0,
            question_results=[{"qid": "q1", "correct": True}],
        )
    )

    assert spec.reward_signal == "process_attributed"
    assert reward.ready_for_training
    assert reward.reward == 1.0


def test_math_domain_confidence_earns_no_calibration_credit():
    """ESC-7 Option A: real math confidence (anti-discriminative geomean) is
    observational — zero calibration/discrimination + domain blocker."""
    r = _result(quality=0.9, ece=0.05, auroc=0.8)
    r.details["scoring_method"] = "math_verify"
    reward = rlvr_reward_from_result(r)
    assert reward.components["calibration"] == 0.0
    assert reward.components["discrimination"] == 0.0
    assert "calibration_domain_observational" in reward.blockers
