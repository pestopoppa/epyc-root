from types import SimpleNamespace

from src.autopilot_core.multitier_decision import (
    build_tier_baseline_evidence,
    evaluate_tier_validation,
)


def _result(*, tier=2, outcomes, core="core-t2", dataset="sha", profile="profile"):
    rows = [{"qid": qid, "correct": correct} for qid, correct in outcomes.items()]
    return SimpleNamespace(
        tier=tier,
        quality=3.0 * sum(outcomes.values()) / len(outcomes),
        reliability=1.0,
        core_id=core,
        dataset_content_sha256=dataset,
        test_profile=profile,
        question_results=rows,
        details={},
    )


def test_identical_candidate_passes_with_zero_width_interval():
    outcomes = {f"q{i}": i % 2 == 0 for i in range(100)}
    incumbent = _result(outcomes=outcomes)
    baseline = build_tier_baseline_evidence(incumbent)

    verdict = evaluate_tier_validation([_result(outcomes=outcomes)], baseline, tier=2)

    assert verdict.status == "pass"
    assert verdict.delta_quality == 0.0
    assert verdict.instrument_match is True


def test_clear_paired_regression_is_terminal():
    incumbent = _result(outcomes={f"q{i}": True for i in range(100)})
    candidate = _result(outcomes={f"q{i}": i >= 30 for i in range(100)})

    verdict = evaluate_tier_validation([candidate], build_tier_baseline_evidence(incumbent), tier=2)

    assert verdict.status == "regression"
    assert verdict.terminal_regression is True


def test_candidate_improvement_breaks_t1_tie():
    incumbent = _result(outcomes={f"q{i}": i >= 20 for i in range(100)})
    candidate = _result(outcomes={f"q{i}": True for i in range(100)})

    verdict = evaluate_tier_validation([candidate], build_tier_baseline_evidence(incumbent), tier=2)

    assert verdict.status == "pass"
    assert verdict.improvement is True
    assert verdict.lower_bound_quality > 0


def test_instrument_mismatch_fails_closed():
    incumbent = _result(outcomes={"q1": True}, dataset="old")
    candidate = _result(outcomes={"q1": True}, dataset="new")

    verdict = evaluate_tier_validation([candidate], build_tier_baseline_evidence(incumbent), tier=2)

    assert verdict.status == "instrument_mismatch"
    assert verdict.instrument_match is False


def test_test_profile_mapping_identity_is_order_independent():
    outcomes = {f"q{i}": i % 2 == 0 for i in range(100)}
    incumbent = _result(tier=2, outcomes=outcomes)
    candidate = _result(tier=2, outcomes=outcomes)
    incumbent.test_profile = {"tier": 2, "seed": 42}
    candidate.test_profile = {"seed": 42, "tier": 2}

    verdict = evaluate_tier_validation(
        [candidate], build_tier_baseline_evidence(incumbent), tier=2
    )

    assert verdict.status == "pass"
    assert verdict.instrument_match is True


def test_low_qid_overlap_is_not_accepted():
    incumbent = _result(outcomes={f"q{i}": True for i in range(100)})
    candidate = _result(outcomes={f"q{i}": True for i in range(20)})

    verdict = evaluate_tier_validation([candidate], build_tier_baseline_evidence(incumbent), tier=2)

    assert verdict.status == "insufficient_overlap"


def test_missing_baseline_fails_closed():
    verdict = evaluate_tier_validation([_result(outcomes={"q1": True})], None, tier=2)
    assert verdict.status == "baseline_missing"
