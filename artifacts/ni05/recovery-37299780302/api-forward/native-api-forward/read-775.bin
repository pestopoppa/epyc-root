from __future__ import annotations

import math

from src.autopilot_core.sequential_verdict import (
    DEFAULT_POLICY,
    STATE_ACCUMULATING,
    STATE_CONFIRMED,
    EProcessState,
    baseline_profile_from_trials,
    empirical_ville_false_positive_rate,
    journal_seq_block,
    quality_trial_statistic,
    rate_noninferiority_z,
    rebuild_candidate_view,
)


def test_first_update_uses_prior_lambda() -> None:
    state, update = EProcessState().update(1.0)

    assert update.k == 1
    assert update.lambda_t == 0.1
    assert round(update.wealth, 6) == 1.1
    assert state.mean_z == 1.0


def test_package_exports_sequential_verdict_symbols() -> None:
    from src.autopilot_core import EProcessState as ExportedState

    assert ExportedState is EProcessState


def test_second_update_uses_only_past_observations() -> None:
    state, _ = EProcessState().update(1.0)
    state, update = state.update(1.0)

    assert update.lambda_t == DEFAULT_POLICY.lambda_cap
    assert round(update.wealth, 6) == 1.65
    assert state.k == 2


def test_quality_statistic_uses_discordant_capable_baseline_profile() -> None:
    baseline = {
        "q_stable_right": 1.0,
        "q_stable_wrong": 0.0,
        "q_variable": 0.5,
    }
    stat = quality_trial_statistic(
        {
            "q_stable_right": True,
            "q_stable_wrong": True,
            "q_variable": True,
        },
        baseline,
    )

    assert stat.r_eff == 2
    assert stat.s == 1.5
    assert stat.z == 0.75
    assert stat.qids == ("q_stable_wrong", "q_variable")


def test_baseline_profile_from_trials_means_correctness_by_qid() -> None:
    profile = baseline_profile_from_trials([
        {"q1": True, "q2": False},
        {"q1": True, "q2": True},
        {"q1": False, "q2": True},
    ])

    assert profile == {"q1": 2 / 3, "q2": 2 / 3}


def test_baseline_profile_accepts_numeric_probabilities() -> None:
    profile = baseline_profile_from_trials([
        {"q1": 0.25},
        {"q1": 0.75},
        {"q1": 2.0},
    ])

    assert profile == {"q1": (0.25 + 0.75 + 1.0) / 3}


def test_sustained_positive_evidence_eventually_confirms() -> None:
    state = EProcessState()
    updates = []
    for trial_id in range(1, 10):
        state, update = state.update(1.0, trial_id=trial_id)
        updates.append(update)

    assert updates[7].state == STATE_ACCUMULATING
    assert state.state_name() == STATE_CONFIRMED
    assert state.wealth >= DEFAULT_POLICY.confirm_e
    assert state.wealth_history[-1][0] == 9


def test_rebuild_candidate_view_folds_journal_seq_rows() -> None:
    rows = [
        {"trial_id": 1, "seq": {"candidate": "cand", "core_id": "core_v2", "z": 1.0}},
        {"trial_id": 2, "seq": {"candidate": "other", "core_id": "core_v2", "z": 1.0}},
        {"trial_id": 3, "seq": {"candidate": "cand", "core_id": "core_v1", "z": 1.0}},
        {"trial_id": 4, "seq": {"candidate": "cand", "core_id": "core_v2", "z": 1.0}},
    ]

    view = rebuild_candidate_view(
        candidate="cand",
        core_id="core_v2",
        observations=rows,
    )

    assert view.fingerprint == "cand"
    assert view.trials == (1, 4)
    assert view.quality_state.k == 2
    assert round(view.quality_state.wealth, 6) == 1.65
    assert view.quality_updates[-1].lambda_t == DEFAULT_POLICY.lambda_cap
    assert view.state == STATE_ACCUMULATING


def test_rebuild_candidate_view_accepts_direct_observations() -> None:
    view = rebuild_candidate_view(
        candidate="cand",
        core_id="core_v2",
        observations=[(10, 0.5), (11, 1.0)],
    )

    assert view.trials == (10, 11)
    assert view.quality_state.k == 2
    assert view.policy_version == "seq-v1"


def test_rate_noninferiority_z_has_zero_boundary_at_margin() -> None:
    assert rate_noninferiority_z(95.0, 100.0) == 0.0
    assert rate_noninferiority_z(100.0, 100.0) == 0.1
    assert round(rate_noninferiority_z(110.0, 100.0), 6) == 0.3


def test_journal_seq_block_is_json_ready() -> None:
    state, update = EProcessState().update(0.75, trial_id=781)

    block = journal_seq_block(
        candidate="abc123",
        core_id="core_v2",
        quality_update=update,
        quality_state=state,
    )

    assert block == {
        "candidate": "abc123",
        "core_id": "core_v2",
        "k": 1,
        "z": 0.75,
        "lambda": 0.1,
        "E_quality": 1.075,
        "state": STATE_ACCUMULATING,
        "policy_version": "seq-v1",
    }


def test_empirical_ville_bound_over_100k_null_runs() -> None:
    rate = empirical_ville_false_positive_rate(runs=100_000, horizon=12)

    assert rate <= DEFAULT_POLICY.alpha


# ---------------------------------------------------------------------------
# SEQ-3a: journal-derived z guard at the public rebuild entry point. The guard is
# floor-only: it rejects non-finite / below-floor (z < -1/lambda_cap) values — the
# ONLY values that would drive 1 + lambda*z negative and raise in update() — while
# leaving large-positive z untouched (legitimate strong evidence).
# ---------------------------------------------------------------------------

_Z_FLOOR = -1.0 / DEFAULT_POLICY.lambda_cap  # = -2.0 for the default policy.


def test_rebuild_candidate_view_skips_below_floor_negative_z_without_raising() -> None:
    # z below -1/lambda_cap would drive 1 + lambda*z negative in EProcessState.update
    # and raise ValueError. The guard must skip it instead of letting the rebuild crash.
    view = rebuild_candidate_view(
        candidate="cand",
        core_id="core_v2",
        observations=[(1, _Z_FLOOR - 1.0), (2, 1.0)],
    )

    assert view.trials == (2,)
    assert view.quality_state.k == 1
    assert view.out_of_range_skipped == 1
    # the surviving valid row folded normally (first update uses first_lambda=0.1).
    assert round(view.quality_state.wealth, 6) == 1.1


def test_rebuild_candidate_view_allows_z_at_and_above_floor() -> None:
    # z exactly at the floor gives factor == 0 (not < 0), so update() does not raise
    # and it is KEPT. A large-positive z keeps the factor >= 0 and is legitimate
    # evidence — it must NOT be skipped (no upper bound).
    view = rebuild_candidate_view(
        candidate="cand",
        core_id="core_v2",
        observations=[(1, _Z_FLOOR), (2, 5.0)],
    )

    assert view.out_of_range_skipped == 0
    assert view.quality_state.k == 2
    assert math.isfinite(view.quality_state.wealth)


def test_rebuild_candidate_view_keeps_synthetic_above_natural_domain_z() -> None:
    # The gate drives confirmation with synthetic z=1.2 (above the natural quality
    # domain of [-1, 1] but well above the factor floor). Floor-only guarding must keep
    # these — rejecting them would break legitimate accumulation.
    view = rebuild_candidate_view(
        candidate="cand",
        core_id="core_v2",
        observations=[(i, 1.2) for i in range(10)],
    )

    assert view.out_of_range_skipped == 0
    assert view.quality_state.k == 10
    assert view.state == STATE_CONFIRMED


def test_rebuild_candidate_view_skips_non_finite_z() -> None:
    view = rebuild_candidate_view(
        candidate="cand",
        core_id="core_v2",
        observations=[(1, float("nan")), (2, float("inf")), (3, float("-inf")), (4, 0.5)],
    )

    assert view.trials == (4,)
    assert view.out_of_range_skipped == 3
