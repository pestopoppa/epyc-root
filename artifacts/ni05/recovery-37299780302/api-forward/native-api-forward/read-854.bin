"""Decision-only AXA-2 integration tests for LLMPrimitives."""

from unittest.mock import Mock

from src.llm_primitives import LLMPrimitives
from src.llm_primitives.teleport import (
    TeleportInputs,
    TeleportPolicy,
    lease_weight_for_workload,
)


def _inputs(**overrides):
    values = {
        "role": "architect_general",
        "generated_tokens": 200,
        "estimated_remaining_tokens": 500,
        "cpu_tps": 20.0,
        "gpu_tps": 44.0,
        "gpu_available": True,
        "gpu_resident": True,
        "cpu_quant": "q4_k_m",
        "gpu_quant": "q4_k_m",
    }
    values.update(overrides)
    return TeleportInputs(**values)


def test_teleport_integration_is_default_off_and_does_not_touch_lease():
    lease = Mock()
    primitives = LLMPrimitives(mock_mode=True, gpu_lease_manager=lease)

    decision = primitives.evaluate_teleport_decision(_inputs(), lease_owner="request-1")

    assert decision.should_cutover is False
    assert decision.reason == "disabled"
    lease.status.assert_not_called()
    lease.acquire.assert_not_called()


def test_teleport_integration_rejects_lease_owned_by_another_request():
    lease = Mock()
    lease.status.return_value = Mock(acquired=True, owner="request-2")
    policy = TeleportPolicy(enabled=True, allowed_roles=frozenset({"architect_general"}))
    primitives = LLMPrimitives(
        mock_mode=True,
        gpu_lease_manager=lease,
        teleport_policy=policy,
    )

    decision = primitives.evaluate_teleport_decision(_inputs(), lease_owner="request-1")

    assert decision.should_cutover is False
    assert decision.reason == "gpu_unavailable"
    lease.status.assert_called_once_with()
    lease.acquire.assert_not_called()


def test_teleport_integration_only_evaluates_decision_for_available_lease():
    lease = Mock()
    lease.status.return_value = Mock(acquired=False, owner=None)
    policy = TeleportPolicy(enabled=True, allowed_roles=frozenset({"architect_general"}))
    primitives = LLMPrimitives(
        mock_mode=True,
        gpu_lease_manager=lease,
        teleport_policy=policy,
    )

    decision = primitives.evaluate_teleport_decision(_inputs(), lease_owner="request-1")

    assert decision.should_cutover is True
    assert decision.reason == "cutover"
    lease.acquire.assert_not_called()


def test_teleport_policy_requires_long_running_token_trigger():
    lease = Mock()
    lease.status.return_value = Mock(acquired=False, owner=None)
    policy = TeleportPolicy(
        enabled=True,
        allowed_roles=frozenset({"architect_general"}),
        long_running_trigger_tokens=256,
    )
    primitives = LLMPrimitives(
        mock_mode=True,
        gpu_lease_manager=lease,
        teleport_policy=policy,
    )

    decision = primitives.evaluate_teleport_decision(
        _inputs(generated_tokens=200),
        lease_owner="request-1",
    )

    assert decision.should_cutover is False
    assert decision.reason == "below_long_running_trigger"
    assert decision.long_running_trigger_tokens == 256


def test_teleport_policy_exposes_lease_weights_by_workload_class():
    policy = TeleportPolicy(
        lease_interactive_weight=1.2,
        lease_batch_weight=0.4,
        lease_eval_weight=0.1,
    )

    assert lease_weight_for_workload(policy, "interactive") == 1.2
    assert lease_weight_for_workload(policy, "batch") == 0.4
    assert lease_weight_for_workload(policy, "evaluation") == 0.1
    assert lease_weight_for_workload(policy, "unknown") == 1.2
