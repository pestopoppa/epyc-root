"""Regression: the cost/speed half of compute_reward must actually fire.

compute_reward gates all three cost dimensions (latency, quality-gap, memory
tier) and the teacher shaping behind a role lookup into
ScoringConfig.baseline_tps_by_role. It used to read only cost_metrics["role"],
but cost_metrics is the TASK_COMPLETED entry's data dict, which carries
"producer_role" / "final_answer_role" and has never carried a bare "role".

Measured 2026-07-21 over 20,521 production task_completed entries: "role"
present 0 times, "producer_role" present 20,521 times. The lookup therefore
resolved baseline_tps to 0, the guard failed, and reward collapsed to
base_reward -- 100% of simulated rewards landed at exactly +1.0, carrying zero
bits. With the fallback the same corpus yields ~2.46 bits.
"""

from __future__ import annotations

from orchestration.repl_memory.q_reward import compute_reward
from orchestration.repl_memory.q_scorer import ScoringConfig


class _Entry:
    def __init__(self, outcome: str, data: dict) -> None:
        self.outcome = outcome
        self.data = data
        self.event_type = None


def _slow_completion(role_key: str) -> dict:
    """A correct-but-slow completion: 100 tokens that took 20s of generation.

    architect_general baseline is ~12.19 tps, so 100 tokens should take ~8.2s.
    20s is ~2.4x slower than expected and must attract a latency penalty.
    """
    return {role_key: "architect_general", "tokens_generated": 100, "generation_ms": 20_000}


def _reward(data: dict) -> float:
    return compute_reward(
        _Entry("success", data), [], [], None, data, config=ScoringConfig()
    )


def test_producer_role_activates_the_cost_penalty():
    """producer_role must resolve baseline_tps so the cost path engages."""
    assert _reward(_slow_completion("producer_role")) < 1.0


def test_bare_role_key_still_supported_for_back_compat():
    assert _reward(_slow_completion("role")) < 1.0


def test_final_answer_role_is_a_last_resort_fallback():
    assert _reward(_slow_completion("final_answer_role")) < 1.0


def test_unknown_role_leaves_reward_at_base():
    """No resolvable role -> no baseline -> cost path stays inert (old behaviour)."""
    data = {
        "producer_role": "not_a_real_role",
        "tokens_generated": 100,
        "generation_ms": 20_000,
    }
    assert _reward(data) == 1.0


def test_cost_path_is_correctness_gated():
    """Failures already score low; no cost signal should be applied to them."""
    data = _slow_completion("producer_role")
    failed = compute_reward(
        _Entry("failure", data), [], [], None, data, config=ScoringConfig()
    )
    assert failed < 0


def test_unpriced_role_is_warned_not_silent(caplog):
    """A role with no baseline must not silently hand out the full base reward.

    This is the failure shape that disabled the whole cost/speed half of the
    reward: an unresolvable role skips every dimension and scores +1.0. The
    behaviour is preserved (we cannot price what we have no baseline for) but
    it must be visible.
    """
    import logging

    from orchestration.repl_memory import q_reward

    q_reward._warned_unpriced_roles.clear()
    data = {
        "producer_role": "brand_new_unregistered_role",
        "tokens_generated": 100,
        "generation_ms": 20_000,
    }
    with caplog.at_level(logging.WARNING):
        assert _reward(data) == 1.0
    assert any("no baseline_tps_by_role entry" in r.message for r in caplog.records)


def test_known_unpriced_roles_do_not_warn(caplog):
    """Decommissioned/test roles are expected in historical replay — no noise."""
    import logging

    from orchestration.repl_memory import q_reward

    q_reward._warned_unpriced_roles.clear()
    for role in ("architect_coding", "mock"):
        data = {"producer_role": role, "tokens_generated": 100, "generation_ms": 20_000}
        with caplog.at_level(logging.WARNING):
            _reward(data)
    assert not [r for r in caplog.records if "no baseline_tps_by_role" in r.message]
