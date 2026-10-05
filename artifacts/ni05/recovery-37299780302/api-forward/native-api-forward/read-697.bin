"""Tests for the retrieval_config + routing_risk + routing_fast_path extractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest


# ----- retrieval_config re-exports -----


def test_retriever_re_exports_retrieval_config_dataclasses() -> None:
    """Tranche-6 contract: retriever.py must keep RetrievalConfig/Result/ScoreComponents callable."""
    from orchestration.repl_memory.retriever import (
        RetrievalConfig, RetrievalResult, ScoreComponents,
    )
    assert RetrievalConfig is not None
    assert RetrievalResult is not None
    assert ScoreComponents is not None


def test_retrieval_config_can_be_imported_directly() -> None:
    """The new module path should also work."""
    from orchestration.repl_memory.retrieval_config import (
        RetrievalConfig,
    )
    assert RetrievalConfig is RetrievalConfig  # sanity


def test_hybrid_router_reexported() -> None:
    from orchestration.repl_memory.retriever import HybridRouter
    from orchestration.repl_memory.hybrid_router import HybridRouter as HR2
    assert HybridRouter is HR2


# ----- routing_fast_path -----


@dataclass
class _StubConfig:
    confidence_threshold: float = 0.6
    confidence_estimator: str = "median"
    confidence_trim_ratio: float = 0.2
    confidence_min_neighbors: int = 3
    calibrated_confidence_threshold: Optional[float] = None
    conformal_margin: float = 0.0
    risk_control_enabled: bool = False
    risk_budget_id: str = "test"
    risk_gate_min_samples: int = 3
    risk_abstain_target_role: str = "fallback"
    risk_gate_rollout_ratio: float = 1.0
    risk_gate_kill_switch: bool = False
    risk_budget_guardrail_min_events: int = 100
    risk_budget_guardrail_max_abstain_rate: float = 0.5


def test_compute_robust_confidence_empty_returns_zero() -> None:
    from orchestration.repl_memory.routing_fast_path import compute_robust_confidence
    assert compute_robust_confidence([]) == 0.0


def test_compute_robust_confidence_median_default() -> None:
    from orchestration.repl_memory.routing_fast_path import compute_robust_confidence
    # median of [0.1, 0.5, 0.9] = 0.5
    assert compute_robust_confidence([0.1, 0.5, 0.9]) == pytest.approx(0.5, abs=1e-5)


def test_compute_robust_confidence_trimmed_mean() -> None:
    from orchestration.repl_memory.routing_fast_path import compute_robust_confidence
    # 5 values, trim_ratio=0.2 → trim 1 from each end → mean of middle 3
    result = compute_robust_confidence(
        [0.0, 0.4, 0.5, 0.6, 1.0], estimator="trimmed_mean", trim_ratio=0.2,
    )
    assert result == pytest.approx((0.4 + 0.5 + 0.6) / 3, abs=1e-5)


def test_compute_robust_confidence_trimmed_mean_falls_back_for_short_input() -> None:
    """With <3 values, trimmed_mean falls back to median."""
    from orchestration.repl_memory.routing_fast_path import compute_robust_confidence
    result = compute_robust_confidence(
        [0.2, 0.8], estimator="trimmed_mean", trim_ratio=0.5,
    )
    # 2 values, can't trim; median = 0.5
    assert result == pytest.approx(0.5, abs=1e-5)


def test_effective_confidence_threshold_no_calibration() -> None:
    from orchestration.repl_memory.routing_fast_path import effective_confidence_threshold
    cfg = _StubConfig(confidence_threshold=0.7, conformal_margin=0.0)
    assert effective_confidence_threshold(cfg) == pytest.approx(0.7)


def test_effective_confidence_threshold_with_calibration_when_risk_on() -> None:
    from orchestration.repl_memory.routing_fast_path import effective_confidence_threshold
    cfg = _StubConfig(
        confidence_threshold=0.7,
        risk_control_enabled=True,
        calibrated_confidence_threshold=0.85,
        conformal_margin=0.05,
    )
    # Calibrated wins, + conformal_margin
    assert effective_confidence_threshold(cfg) == pytest.approx(0.90)


def test_effective_confidence_threshold_clamps_to_unit_interval() -> None:
    from orchestration.repl_memory.routing_fast_path import effective_confidence_threshold
    cfg = _StubConfig(confidence_threshold=0.95, conformal_margin=0.5)
    # 0.95 + 0.5 = 1.45 → clamps to 1.0
    assert effective_confidence_threshold(cfg) == pytest.approx(1.0)


def test_action_prior_prob_returns_value_when_present() -> None:
    from orchestration.repl_memory.routing_fast_path import action_prior_prob
    assert action_prior_prob("frontdoor", {"frontdoor": 0.7, "architect": 0.3}) == 0.7


def test_action_prior_prob_returns_zero_when_missing() -> None:
    from orchestration.repl_memory.routing_fast_path import action_prior_prob
    assert action_prior_prob("unknown", {"frontdoor": 0.7}) == 0.0


def test_action_prior_prob_empty_priors() -> None:
    from orchestration.repl_memory.routing_fast_path import action_prior_prob
    assert action_prior_prob("frontdoor", {}) == 0.0


# ----- routing_risk -----


def test_is_risk_gate_enforced_rollout_ratio_one() -> None:
    from orchestration.repl_memory.routing_risk import is_risk_gate_enforced_for_route
    cfg = _StubConfig(risk_gate_rollout_ratio=1.0)
    assert is_risk_gate_enforced_for_route(cfg, "any_route") is True


def test_is_risk_gate_enforced_rollout_ratio_zero() -> None:
    from orchestration.repl_memory.routing_risk import is_risk_gate_enforced_for_route
    cfg = _StubConfig(risk_gate_rollout_ratio=0.0)
    assert is_risk_gate_enforced_for_route(cfg, "any_route") is False


def test_is_risk_gate_enforced_partial_rollout_is_deterministic() -> None:
    """Same route_key always returns the same answer (hash-based)."""
    from orchestration.repl_memory.routing_risk import is_risk_gate_enforced_for_route
    cfg = _StubConfig(risk_gate_rollout_ratio=0.5)
    a = is_risk_gate_enforced_for_route(cfg, "consistent_key")
    b = is_risk_gate_enforced_for_route(cfg, "consistent_key")
    assert a == b


def test_guardrail_blocks_gate_below_min_events_returns_false() -> None:
    from orchestration.repl_memory.routing_risk import guardrail_blocks_gate
    cfg = _StubConfig(
        risk_budget_guardrail_min_events=100,
        risk_budget_guardrail_max_abstain_rate=0.5,
    )
    # Only 10 events, below the 100-event guardrail threshold
    assert guardrail_blocks_gate(cfg, {"events": 10, "abstains": 10}) is False


def test_guardrail_blocks_gate_abstain_rate_exceeds_max() -> None:
    from orchestration.repl_memory.routing_risk import guardrail_blocks_gate
    cfg = _StubConfig(
        risk_budget_guardrail_min_events=10,
        risk_budget_guardrail_max_abstain_rate=0.5,
    )
    # 100 events, 80 abstains = 80% rate, exceeds 50% guardrail
    assert guardrail_blocks_gate(cfg, {"events": 100, "abstains": 80}) is True


def test_guardrail_blocks_gate_abstain_rate_within_budget() -> None:
    from orchestration.repl_memory.routing_risk import guardrail_blocks_gate
    cfg = _StubConfig(
        risk_budget_guardrail_min_events=10,
        risk_budget_guardrail_max_abstain_rate=0.5,
    )
    # 100 events, 30 abstains = 30% rate, within 50% guardrail
    assert guardrail_blocks_gate(cfg, {"events": 100, "abstains": 30}) is False


def test_build_not_enforced_response_shape() -> None:
    from orchestration.repl_memory.routing_risk import build_not_enforced_response
    out = build_not_enforced_response(
        threshold=0.7, reason="test_reason", budget_id="bid", confidence=0.42,
    )
    assert out == {
        "enforced": False,
        "passed": True,
        "action": "not_enforced",
        "reason": "test_reason",
        "confidence": 0.42,
        "threshold": 0.7,
        "budget_id": "bid",
    }


def test_build_abstain_response_shape() -> None:
    from orchestration.repl_memory.routing_risk import build_abstain_response
    out = build_abstain_response(threshold=0.7, confidence=0.5, budget_id="bid")
    assert out["action"] == "abstain_escalate"
    assert out["passed"] is False
    assert out["enforced"] is True


def test_build_accept_response_shape() -> None:
    from orchestration.repl_memory.routing_risk import build_accept_response
    out = build_accept_response(threshold=0.7, confidence=0.85, budget_id="bid")
    assert out["action"] == "accept"
    assert out["passed"] is True
    assert out["enforced"] is True
