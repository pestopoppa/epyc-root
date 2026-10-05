"""EPD-1: `outcome` must track `q_value` across Q-updates, not just at INSERT.

Regression coverage for the label defect described in
handoffs/active/learned-routing-controller.md (EPD-1 / EPD-1-orig): the
UPDATE statement inside ``EpisodicStore.update_q_value`` used to set only
``q_value``, ``updated_at`` and ``update_count`` — ``outcome`` was frozen at
whatever ``store()`` wrote on the first observation, however many times the
row was later Q-updated. A consumer re-audit (2026-09-23) found live readers
(``src/repl_environment/state.py``, ``src/prompt_builders/builder.py``,
training-data extraction, the DAR/EP-5 probes) that all treat ``outcome`` as
the CURRENT label, so the fix re-derives it from the same ``reward`` each
Q-update already receives, via the shared ``outcome_from_reward()`` helper —
the same mapping the INSERT path (``q_scorer.py``) uses.

Uses only a tmp-path SQLite store — never the live episodic database.
"""

from __future__ import annotations

import numpy as np
import pytest

from orchestration.repl_memory.episodic_store import (
    EpisodicStore,
    outcome_from_q,
    outcome_from_reward,
)


@pytest.fixture
def tmp_store(tmp_path):
    store = EpisodicStore(db_path=tmp_path / "sessions", use_faiss=True)
    yield store
    store.close()


def _embed(seed: int) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(1024).astype(np.float32)


class TestOutcomeFromReward:
    """Unit coverage for the extracted mapping itself."""

    def test_positive_reward_is_success(self):
        assert outcome_from_reward(1.0) == "success"
        assert outcome_from_reward(0.01) == "success"

    def test_nonpositive_reward_is_failure(self):
        assert outcome_from_reward(0.0) == "failure"
        assert outcome_from_reward(-1.0) == "failure"


class TestOutcomeFromQ:
    def test_threshold_is_neutral_q(self):
        assert outcome_from_q(0.51) == "success"
        assert outcome_from_q(0.5) == "failure"
        assert outcome_from_q(0.1) == "failure"


class TestOutcomeTracksQOnUpdate:
    def test_failure_first_observation_flips_to_success(self, tmp_store):
        """A row that started as a failure should read `success` once later
        Q-updates carry a positive reward — the exact scenario EPD-1
        describes (update_count up to 7,888 while outcome never moved)."""
        mid = tmp_store.store(
            _embed(1),
            "frontdoor:direct",
            "routing",
            {"task_type": "chat"},
            outcome="failure",
            initial_q=0.2,
        )

        before = tmp_store.get_by_id(mid)
        assert before.outcome == "failure"
        assert before.update_count in (0, None)

        # Several positive-reward Q-updates, as a live rescoring would apply.
        for _ in range(3):
            tmp_store.update_q_value(mid, reward=1.0, learning_rate=0.3)

        after = tmp_store.get_by_id(mid)
        assert after.outcome == "success", (
            "outcome must track the current reward sign after a Q-update, "
            "not stay pinned to the first-observation label"
        )
        assert after.q_value > before.q_value

    def test_success_first_observation_flips_to_failure(self, tmp_store):
        """Reverse direction: a row that started as a success should read
        `failure` once later Q-updates carry a non-positive reward."""
        mid = tmp_store.store(
            _embed(2),
            "coder_escalation:repl",
            "routing",
            {"task_type": "code"},
            outcome="success",
            initial_q=0.8,
        )

        before = tmp_store.get_by_id(mid)
        assert before.outcome == "success"

        for _ in range(3):
            tmp_store.update_q_value(mid, reward=0.0, learning_rate=0.3)

        after = tmp_store.get_by_id(mid)
        assert after.outcome == "failure"
        assert after.q_value < before.q_value

    def test_update_count_and_updated_at_still_advance(self, tmp_store):
        """The outcome fix must not disturb the pre-existing update_count /
        updated_at behavior."""
        mid = tmp_store.store(
            _embed(3),
            "architect_general:direct",
            "routing",
            {"task_type": "code"},
            outcome="failure",
            initial_q=0.5,
        )
        before = tmp_store.get_by_id(mid)
        before_count = before.update_count or 0

        tmp_store.update_q_value(mid, reward=1.0, learning_rate=0.2)
        tmp_store.update_q_value(mid, reward=1.0, learning_rate=0.2)

        after = tmp_store.get_by_id(mid)
        assert (after.update_count or 0) == before_count + 2
        assert after.updated_at >= before.updated_at

    def test_single_late_failure_does_not_contradict_high_q(self, tmp_store):
        """The label follows the running Q, not the last reward: one failure
        after many successes must not produce `Q=0.9 (failure)`."""
        mid = tmp_store.store(
            _embed(4),
            "worker_explore:direct",
            "routing",
            {"task_type": "chat"},
            outcome="failure",
            initial_q=0.5,
        )

        rewards = [1.0] * 10 + [0.0]
        for r in rewards:
            tmp_store.update_q_value(mid, reward=r, learning_rate=0.1)

        after = tmp_store.get_by_id(mid)
        assert after.q_value > 0.5
        assert after.outcome == outcome_from_q(after.q_value) == "success"
        assert (after.update_count or 0) == len(rewards)
