"""The planner's deterministic pre-dispatch guard must cost a TRIAL, not the RUN.

Origin (2026-08-04, trial 1472): the guard halted the daemon on its FIRST hit. A critic
returned 'revise' with confidence 0.94 and a substituted action equal to the draft; the
guard fired and the loop `break`-ed, ending the run. Every sibling breaker in the same
if/elif chain (critic-reject loop, consecutive meta, consecutive skip) substitutes a safe
action and only halts after a RUN — this one did not, so one ordinary planner/critic
disagreement stopped AutoPilot from ratcheting.
"""
from __future__ import annotations

import types

import pytest

import sys
from pathlib import Path

ORCH_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ORCH_ROOT / "scripts" / "autopilot"))

from autopilot import (  # noqa: E402
    MAX_CONSECUTIVE_PLANNER_DETERMINISTIC_BLOCKS,
    PLANNER_DETERMINISTIC_BLOCK_STATE_KEY,
    _planner_deterministic_block_decision,
)


def _blocked(reason="critique decision 'revise' left final action unchanged"):
    return types.SimpleNamespace(
        deterministic_block_reason=reason,
        draft_action={"type": "numeric_trial", "surface": "chat_long_context"},
    )


def test_first_block_substitutes_rather_than_halting():
    """The regression that ended trial 1472's run."""
    state: dict = {}
    decision, count = _planner_deterministic_block_decision(state, _blocked())
    assert decision == "substitute"
    assert count == 1


def test_halt_only_after_a_run_of_blocks():
    """Derived from the configured breaker limit, not a restated literal."""
    state: dict = {}
    limit = MAX_CONSECUTIVE_PLANNER_DETERMINISTIC_BLOCKS
    assert limit >= 2, "a limit of 1 would restore the halt-on-first-hit regression"

    decisions = [
        _planner_deterministic_block_decision(state, _blocked())[0] for _ in range(limit)
    ]
    assert decisions[:-1] == ["substitute"] * (limit - 1)
    assert decisions[-1] == "halt"


def test_rejected_draft_always_feeds_invalid_action_feedback():
    """A substituted trial must still teach the planner, exactly as a critic reject does."""
    state: dict = {}
    decision = _blocked(reason="some deterministic reason")
    _planner_deterministic_block_decision(state, decision)
    assert state["last_invalid_action"] == decision.draft_action
    assert state["last_invalid_reason"] == "some deterministic reason"
    assert state["last_invalid_status"] == "planner_deterministic_guard"


def test_counter_is_consecutive_so_a_clean_dispatch_clears_it():
    """Isolated blocks across unrelated trials must not accumulate into a halt."""
    state: dict = {}
    for _ in range(MAX_CONSECUTIVE_PLANNER_DETERMINISTIC_BLOCKS - 1):
        assert _planner_deterministic_block_decision(state, _blocked())[0] == "substitute"

    # The loop clears this key on any accepted draft / autonomous dispatch.
    state[PLANNER_DETERMINISTIC_BLOCK_STATE_KEY] = 0

    decision, count = _planner_deterministic_block_decision(state, _blocked())
    assert decision == "substitute"
    assert count == 1


def test_limit_is_operator_overridable_without_editing_code():
    """The breaker reads an env override, like its siblings."""
    state: dict = {}
    decision, _ = _planner_deterministic_block_decision(state, _blocked(), max_blocks=1)
    assert decision == "halt"


@pytest.mark.parametrize("stored", [None, "", "not-an-int", -3, 0, [], {}])
def test_corrupt_counter_does_not_crash_or_disable_the_breaker(stored):
    """State is operator-editable JSON and survives restarts.

    A stored -3 used to count up through -2, -1, 0 ... and never reach the limit, and a
    non-numeric value raised straight out of the trial loop. Either way the guard was gone.
    """
    state: dict = {PLANNER_DETERMINISTIC_BLOCK_STATE_KEY: stored}
    decision, count = _planner_deterministic_block_decision(state, _blocked())
    assert count == 1, f"a corrupt prior ({stored!r}) must restart the run, not offset it"
    assert decision == "substitute"

    # And the breaker must still be REACHABLE from that recovered state.
    for _ in range(MAX_CONSECUTIVE_PLANNER_DETERMINISTIC_BLOCKS - 2):
        _planner_deterministic_block_decision(state, _blocked())
    assert _planner_deterministic_block_decision(state, _blocked())[0] == "halt"
