#!/usr/bin/env python3
"""SEQ-A — stickiness of the `refuted` label, as an explicit policy choice.

`EProcessState.state_name()` is a pure function of CURRENT state, so a candidate
whose wealth climbs back over `futility_e`/`budget_min_e` reads `accumulating`
again — the function does not remember having refuted. The persisted labels are
never recomputed and stay `refuted`. The two disagree for exactly 3 `core_v1`
candidates, which are thereby excluded from promotion and positive strategy
distillation by a condition they no longer meet.

Which side gives is **SEQ-A1, an operator decision, human-amendment-only per
MEASUREMENT.md** — it changes which candidates are promotable. These tests pin
the mechanism and, crucially, that **declaring it changes nothing by default**:
`sticky_refuted` is False, so seq-v1 semantics are byte-for-byte preserved until
an operator ratifies otherwise.
"""

from __future__ import annotations

from dataclasses import replace

from src.autopilot_core.sequential_verdict import (
    DEFAULT_POLICY,
    STATE_ACCUMULATING,
    STATE_CONFIRMED,
    STATE_REFUTED,
    EProcessState,
    SequentialPolicy,
)

STICKY = SequentialPolicy(sticky_refuted=True)


def test_default_policy_is_not_sticky():
    """The whole point of the default: no semantic change on landing."""
    assert DEFAULT_POLICY.sticky_refuted is False


def test_recovered_candidate_reads_accumulating_under_default():
    """seq-v1 semantics, unchanged: a recovered e-process un-refutes."""
    # Below budget_min_e at/after budget -> refuted.
    stopped = EProcessState(wealth=1.0, k=10)
    assert stopped.state_name(DEFAULT_POLICY) == STATE_REFUTED

    recovered = replace(stopped, wealth=11.55, first_refuted_k=8)
    assert recovered.state_name(DEFAULT_POLICY) == STATE_ACCUMULATING, (
        "default must preserve the pure-function semantics exactly"
    )


def test_recovered_candidate_stays_refuted_under_sticky():
    recovered = EProcessState(wealth=11.55, k=40, first_refuted_k=8)
    assert recovered.state_name(STICKY) == STATE_REFUTED


def test_sticky_needs_an_actual_prior_stop():
    """Stickiness must not invent a refutation that never happened."""
    never_stopped = EProcessState(wealth=11.55, k=40, first_refuted_k=None)
    assert never_stopped.state_name(STICKY) == STATE_ACCUMULATING


def test_confirmed_outranks_stickiness():
    """A confirmed e-process is confirmed; stickiness must not mask it."""
    confirmed = EProcessState(wealth=25.0, k=40, first_refuted_k=8)
    assert confirmed.state_name(STICKY) == STATE_CONFIRMED
    assert confirmed.state_name(DEFAULT_POLICY) == STATE_CONFIRMED


def test_first_refuted_k_is_recorded_even_when_not_sticky():
    """Observing the stop is free; acting on it is the operator's choice.

    Recording unconditionally is what lets SEQ-A1 be decided later from data
    rather than re-run — and it is why the flag can default off without
    losing the information it would need.
    """
    state = EProcessState(wealth=1.0, k=7)
    # One more trial takes k to 8 (== budget) with wealth still < budget_min_e.
    state, update = state.update(-0.5, policy=DEFAULT_POLICY)
    assert state.k == 8
    assert update.state == STATE_REFUTED
    assert state.first_refuted_k == 8


def test_first_stop_wins_and_survives_recovery():
    state = EProcessState(wealth=1.0, k=7)
    state, _ = state.update(-0.5, policy=DEFAULT_POLICY)
    stop_k = state.first_refuted_k
    assert stop_k == 8

    # Feed positive evidence until wealth clears the kill line but stays under
    # confirm_e — the band where the two horns actually disagree. (Overshooting
    # into `confirmed` would make this test pass for the wrong reason.)
    while state.wealth <= DEFAULT_POLICY.budget_min_e:
        state, _ = state.update(1.0, policy=DEFAULT_POLICY)

    assert state.first_refuted_k == stop_k, "a later recovery must not erase the stop"
    assert DEFAULT_POLICY.budget_min_e < state.wealth < DEFAULT_POLICY.confirm_e
    # The two horns of SEQ-A1, side by side on identical state:
    assert state.state_name(DEFAULT_POLICY) == STATE_ACCUMULATING
    assert state.state_name(STICKY) == STATE_REFUTED


def test_state_reconstructed_without_the_field_behaves_as_before():
    """Old persisted records cannot carry first_refuted_k; they must not break."""
    legacy = EProcessState(wealth=11.55, k=40)
    assert legacy.first_refuted_k is None
    assert legacy.state_name(DEFAULT_POLICY) == STATE_ACCUMULATING
    assert legacy.state_name(STICKY) == STATE_ACCUMULATING
