from src.llm_primitives.teleport import (
    TeleportInputs,
    TeleportPolicy,
    decide_teleport,
)


def _inputs(**overrides):
    base = {
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
    base.update(overrides)
    return TeleportInputs(**base)


def test_teleport_policy_is_default_off():
    decision = decide_teleport(TeleportPolicy(), _inputs())

    assert decision.should_cutover is False
    assert decision.reason == "disabled"
    assert decision.catch_up_supported is False
    assert decision.catch_up_reason == "llama_server_verify_api_unavailable"


def test_teleport_policy_accepts_resident_break_even():
    policy = TeleportPolicy(enabled=True, allowed_roles=frozenset({"architect_general"}))

    decision = decide_teleport(policy, _inputs(estimated_remaining_tokens=160))

    assert decision.should_cutover is True
    assert decision.reason == "cutover"
    assert decision.threshold_tokens == 150
    assert decision.estimated_speedup == 2.2


def test_teleport_policy_rejects_unknown_mode():
    policy = TeleportPolicy(enabled=True, mode="spec_catch_up")

    decision = decide_teleport(policy, _inputs())

    assert decision.should_cutover is False
    assert decision.reason == "invalid_teleport_mode"
    assert decision.mode == "spec_catch_up"


def test_teleport_policy_rejects_catch_up_claim_in_v1():
    policy = TeleportPolicy(enabled=True)

    decision = decide_teleport(policy, _inputs(catch_up_supported=True))

    assert decision.should_cutover is False
    assert decision.reason == "catch_up_not_supported_in_v1"
    assert decision.catch_up_supported is False


def test_teleport_policy_requires_rate_window_observation():
    policy = TeleportPolicy(enabled=True, rate_window_tokens=64)

    decision = decide_teleport(policy, _inputs(rate_window_observed_tokens=32))

    assert decision.should_cutover is False
    assert decision.reason == "insufficient_rate_window"
    assert decision.rate_window_tokens == 64
    assert decision.rate_window_observed_tokens == 32


def test_teleport_policy_uses_cold_break_even():
    policy = TeleportPolicy(enabled=True)

    decision = decide_teleport(
        policy,
        _inputs(gpu_resident=False, estimated_remaining_tokens=300),
    )

    assert decision.should_cutover is False
    assert decision.reason == "below_break_even_tokens"
    assert decision.threshold_tokens == 350


def test_teleport_policy_rejects_unavailable_gpu():
    policy = TeleportPolicy(enabled=True)

    decision = decide_teleport(policy, _inputs(gpu_available=False))

    assert decision.should_cutover is False
    assert decision.reason == "gpu_unavailable"


def test_teleport_policy_rejects_missing_quant_context_when_enabled():
    policy = TeleportPolicy(enabled=True)

    decision = decide_teleport(
        policy,
        _inputs(cpu_quant=None, gpu_quant=None),
    )

    assert decision.should_cutover is False
    assert decision.reason == "missing_quant_context"
    assert decision.quant_policy == "same_quant_only"
    assert decision.quant_transition == "unknown->unknown"


def test_teleport_policy_rejects_midstream_quant_change_by_default():
    policy = TeleportPolicy(enabled=True)

    decision = decide_teleport(policy, _inputs(cpu_quant="q4_k_m", gpu_quant="iq2_m"))

    assert decision.should_cutover is False
    assert decision.reason == "quant_change_not_allowed"
    assert decision.quant_transition == "q4_k_m->iq2_m"


def test_teleport_policy_allows_operator_approved_role_quant_change():
    policy = TeleportPolicy(
        enabled=True,
        quant_policy="operator_approved_tail_roles",
        allowed_quant_change_roles=frozenset({"architect_general"}),
    )

    decision = decide_teleport(policy, _inputs(cpu_quant="q4_k_m", gpu_quant="iq2_m"))

    assert decision.should_cutover is True
    assert decision.reason == "cutover"


def test_teleport_policy_rejects_operator_policy_for_unlisted_role():
    policy = TeleportPolicy(
        enabled=True,
        quant_policy="operator_approved_tail_roles",
        allowed_quant_change_roles=frozenset({"frontdoor"}),
    )

    decision = decide_teleport(policy, _inputs(cpu_quant="q4_k_m", gpu_quant="iq2_m"))

    assert decision.should_cutover is False
    assert decision.reason == "quant_change_role_not_allowed"


def test_teleport_policy_rejects_role_not_allowed():
    policy = TeleportPolicy(enabled=True, allowed_roles=frozenset({"frontdoor"}))

    decision = decide_teleport(policy, _inputs(role="architect_general"))

    assert decision.should_cutover is False
    assert decision.reason == "role_not_allowed"


def test_teleport_policy_rejects_weak_speedup():
    policy = TeleportPolicy(enabled=True, min_speedup=1.5)

    decision = decide_teleport(policy, _inputs(cpu_tps=40.0, gpu_tps=44.0))

    assert decision.should_cutover is False
    assert decision.reason == "below_speedup_threshold"
