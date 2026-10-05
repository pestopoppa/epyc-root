"""WP-12 fleet layer — fleet-aware fallback: same-fleet edges are no-ops.

Acceptance plan coverage (wp12-fleet-layer-design.md §6):
  * case 5 — forced worker_math with the fleet down: no same-fleet candidate,
    the request fails fast, fallback churn stays 0 (regression bound for the
    ~90x forced_role_fallback churn)
  * case 6 — cross-fleet fallback stays real: architect_general falls back to
    the distinct fleet its declared fallback target rides (architect_critic's
    :8074 CPU fleet since the 2026-08-01 W1 cutover) and succeeds

Plus flag-off byte-identity of get_fallback_roles and the fail-safe when the
fleet build is unavailable. All offline.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import src.features
import src.fleet as fleet_mod
from src.roles import Role, get_fallback_roles, _FALLBACK_MAP

FD_PORTS = [8080, 8180, 8280, 8380]
WG_PORTS = [8082, 8182, 8282, 8382]

SERVER_MODE = {
    "frontdoor": {
        "port": 8070,
        "model_role": "qwen36_q8_0",
        "shared_with": ["coder_escalation", "worker_summarize"],
    },
    "worker": {
        "port": 8072,
        "model_role": "worker_general",
        "shared_with": ["worker_math", "toolrunner"],
    },
    "architect_general": {"port": 8083, "model_role": "qwen36_27b_mtp_q8_local"},
    # 2026-08-01 W1 cutover: architect_critic is its OWN fleet — the 122B on a
    # separate CPU process, registry server_mode.architect_critic.port == 8074.
    # It must be bound here, not merely named: compiled_fleet_fallback_map keeps
    # edges "involving unbound roles ... verbatim", so an unbound architect_critic
    # would let the case-6 assertions pass through the UNBOUND branch and stop
    # testing cross-fleet retention at all.
    "architect_critic": {"port": 8074, "model_role": "qwen35_122b_q4km"},
    "ingest_long_context": {"port": 8085, "model_role": "ingest_long_context"},
}


def _fleet_state(tmp_path: Path):
    payload = {
        "roles": {
            role: {
                "deployment_status": "live_stack",
                "serving": {"ports": list(ports)},
            }
            for role, ports in {
                "frontdoor": FD_PORTS,
                "coder_escalation": FD_PORTS,
                "worker_summarize": FD_PORTS,
                "worker_general": WG_PORTS,
                "worker_math": WG_PORTS,
                "toolrunner": WG_PORTS,
                "architect_general": [8083],
                "architect_critic": [8074],
                "ingest_long_context": [8185, 8285, 8385, 8485],
            }.items()
        }
    }
    priors = tmp_path / "stack_priors.yaml"
    priors.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return fleet_mod.build_fleets_and_bindings(
        registry_server_mode=SERVER_MODE,
        priors_path=priors,
    )


@pytest.fixture()
def same_fleet_edge(monkeypatch):
    """Inject the historical same-fleet edge worker_math -> worker_general.

    Case 5 exercises the compiler's same-fleet elision. The live map carried this
    edge until 2026-09-26, when it was replaced by a cross-process fallback because
    a same-process fallback is useless (the class this compiler exists to remove).
    The live map therefore has no same-fleet edge left to elide, so the mechanism
    is tested on an injected one.
    """
    monkeypatch.setitem(_FALLBACK_MAP, Role.WORKER_MATH, [Role.WORKER_GENERAL])


@pytest.fixture()
def fleet_on(monkeypatch, tmp_path):
    state = _fleet_state(tmp_path)
    monkeypatch.setattr(fleet_mod, "get_fleets_and_bindings", lambda: state)
    monkeypatch.setenv("ORCHESTRATOR_FLEET_LAYER", "1")
    return state


# ── Map-level semantics ─────────────────────────────────────────────────────


def test_flag_off_fallback_map_unchanged(monkeypatch):
    """Flag off, get_fallback_roles is a pure pass-through of the legacy map.

    Asserted against ``_FALLBACK_MAP`` itself rather than an inline copy of its
    contents: this test's contract is the PASS-THROUGH, and re-encoding the map
    made a legitimate topology edit (architect_general -> architect_critic after
    the W1 cutover) look like a failure of the flag-off path.
    """
    monkeypatch.delenv("ORCHESTRATOR_FLEET_LAYER", raising=False)
    assert _FALLBACK_MAP, "legacy fallback map is empty — test is vacuous"
    for role, targets in _FALLBACK_MAP.items():
        assert get_fallback_roles(role) == list(targets)
    # Returned list is a copy, not the live table (mutating it must not poison it).
    returned = get_fallback_roles(Role.WORKER_MATH)
    returned.clear()
    assert get_fallback_roles(Role.WORKER_MATH) == list(_FALLBACK_MAP[Role.WORKER_MATH])
    # String input and unknown-role input behave as before.
    assert get_fallback_roles("worker_math") == list(_FALLBACK_MAP[Role.WORKER_MATH])
    assert get_fallback_roles("not_a_role") == []


def test_case5_same_fleet_edges_compiled_to_noops(same_fleet_edge, fleet_on):
    # worker_math → worker_general: same gemma4 fleet → elided.
    assert get_fallback_roles(Role.WORKER_MATH) == []
    # coder_escalation → frontdoor: same Qwen fleet → elided.
    assert get_fallback_roles(Role.CODER_ESCALATION) == []
    # Roles with no fallback stay empty.
    assert get_fallback_roles(Role.FRONTDOOR) == []
    assert get_fallback_roles(Role.WORKER_VISION) == []


def _assert_cross_fleet_edges_kept(role, bindings):
    """The role's DECLARED fallback targets all ride a different fleet and survive
    compilation.

    Every target is asserted BOUND first: an unbound target is kept verbatim by
    ``compiled_fleet_fallback_map``, so without this guard the retention assertion
    could pass through the unbound branch and case 6 would test nothing.
    """
    declared = list(_FALLBACK_MAP[role])
    assert declared, f"{role.value} declares no fallback — nothing to keep"

    source = fleet_mod.resolve_binding(role.value, bindings)
    assert source is not None, f"{role.value} is unbound in the fixture topology"
    for target in declared:
        target_binding = fleet_mod.resolve_binding(target.value, bindings)
        assert target_binding is not None, (
            f"{target.value} is unbound — the edge would be kept verbatim, not "
            f"because it crosses fleets"
        )
        assert target_binding.fleet_id != source.fleet_id, (
            f"{role.value} -> {target.value} is same-fleet ({source.fleet_id})"
        )

    assert get_fallback_roles(role) == declared


def test_case6_cross_fleet_edges_stay_real(fleet_on):
    _, bindings = fleet_on
    # architect_general fleet (:8083) → architect_critic fleet (:8074): distinct → kept.
    _assert_cross_fleet_edges_kept(Role.ARCHITECT_GENERAL, bindings)
    # …and the reverse edge, which the W1 cutover also declares.
    _assert_cross_fleet_edges_kept(Role.ARCHITECT_CRITIC, bindings)
    # ingest fleet → its declared cross-process target: distinct → kept.
    _assert_cross_fleet_edges_kept(Role.INGEST_LONG_CONTEXT, bindings)
    # worker_math's live edge (a different process since 2026-09-26) survives too.
    _assert_cross_fleet_edges_kept(Role.WORKER_MATH, bindings)


def test_fleet_build_unavailable_falls_back_to_legacy_map(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_FLEET_LAYER", "1")
    monkeypatch.setattr(fleet_mod, "get_fleets_and_bindings", lambda: None)
    assert _FALLBACK_MAP[Role.WORKER_MATH], "worker_math declares no fallback — vacuous"
    assert get_fallback_roles(Role.WORKER_MATH) == list(_FALLBACK_MAP[Role.WORKER_MATH])


# ── Inference-level: fail fast, churn 0 / cross-fleet succeeds ──────────────


class _FeaturesWithFallback:
    """Real features object with model_fallback forced on."""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        if name == "model_fallback":
            return True
        return getattr(self._inner, name)


@pytest.fixture()
def prims(monkeypatch):
    real = src.features.features()
    monkeypatch.setattr(src.features, "features", lambda: _FeaturesWithFallback(real))
    from src.llm_primitives import LLMPrimitives

    return LLMPrimitives(mock_mode=False)


def test_case5_forced_worker_math_fails_fast_zero_churn(
    same_fleet_edge, fleet_on, prims, monkeypatch
):
    """Fleet circuit open on the shared gemma4 fleet: worker_math gets NO
    worker_general retry (identical physical backend + identical open
    circuit). One attempt, zero fallback churn — the 90x class is dead at
    the root."""
    calls: list[str] = []

    def _failing_single(prompt, role, *args, **kwargs):
        calls.append(role)
        raise RuntimeError(
            "Backend unavailable (circuit open): all endpoints for fleet worker_general"
        )

    monkeypatch.setattr(prims, "_real_call_single", _failing_single)

    with pytest.raises(RuntimeError, match="circuit open"):
        prims._real_call_impl("prompt", "worker_math")
    assert calls == ["worker_math"]  # no same-fleet retry → churn counter 0


def test_case5_flag_off_control_shows_legacy_churn(same_fleet_edge, prims, monkeypatch):
    """Flag-off control for the same scenario: the legacy map DOES retry
    worker_general (the churn the fleet layer removes)."""
    monkeypatch.delenv("ORCHESTRATOR_FLEET_LAYER", raising=False)
    calls: list[str] = []

    def _failing_single(prompt, role, *args, **kwargs):
        calls.append(role)
        raise RuntimeError("Backend unavailable (circuit open): http://localhost:8082")

    monkeypatch.setattr(prims, "_real_call_single", _failing_single)

    with pytest.raises(RuntimeError):
        prims._real_call_impl("prompt", "worker_math")
    assert calls == ["worker_math", "worker_general"]


def test_case6_cross_fleet_fallback_succeeds(fleet_on, prims, monkeypatch):
    """architect_general with its (distinct) fleet down falls back to its declared
    cross-fleet target and the request SUCCEEDS."""
    _, bindings = fleet_on
    # Derive the target instead of naming it, and prove it is a real cross-fleet
    # hop in this topology before asserting the retry lands on it.
    _assert_cross_fleet_edges_kept(Role.ARCHITECT_GENERAL, bindings)
    fallback_target = _FALLBACK_MAP[Role.ARCHITECT_GENERAL][0].value

    calls: list[str] = []

    def _single(prompt, role, *args, **kwargs):
        calls.append(role)
        if role == "architect_general":
            raise RuntimeError(
                "Backend unavailable (circuit open): all endpoints for fleet architect_general"
            )
        return "cross-fleet-ok"

    monkeypatch.setattr(prims, "_real_call_single", _single)

    result = prims._real_call_impl("prompt", "architect_general")
    assert result == "cross-fleet-ok"
    assert calls == ["architect_general", fallback_target]
