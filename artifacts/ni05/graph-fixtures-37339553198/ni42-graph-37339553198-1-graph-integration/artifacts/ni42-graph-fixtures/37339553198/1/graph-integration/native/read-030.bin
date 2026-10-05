"""Risk-gate + budget-stats pure helpers for MemRL routing.

Extracted from retriever.py's TwoPhaseRetriever during the 2026-05-22 Tranche-6
refactor. The methods that previously read `self.config` + `self._risk_budget_stats`
are now module-level functions taking those as parameters, so they're independently
testable. TwoPhaseRetriever's `evaluate_risk_gate`, `_is_risk_gate_enforced_for_route`,
and `_guardrail_blocks_gate` delegate here.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from .retrieval_config import RetrievalConfig


def is_risk_gate_enforced_for_route(config: "RetrievalConfig", route_key: str) -> bool:
    """Deterministic rollout sampler for strict gate enforcement.

    Hashes `(risk_budget_id, route_key)` into a [0, 1) bucket; returns True when
    bucket < rollout_ratio. Returns full True/False for the boundary cases.
    """
    ratio = max(0.0, min(1.0, float(config.risk_gate_rollout_ratio)))
    if ratio >= 1.0:
        return True
    if ratio <= 0.0:
        return False
    seed = f"{config.risk_budget_id}:{route_key or 'default'}".encode("utf-8")
    digest = hashlib.md5(seed).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return bucket < ratio


def guardrail_blocks_gate(
    config: "RetrievalConfig", risk_budget_stats: Dict[str, int],
) -> bool:
    """Disable strict gate when abstain rate breaches configured budget guardrail.

    Returns False until at least `risk_budget_guardrail_min_events` events have
    been recorded; then checks abstain_rate against
    `risk_budget_guardrail_max_abstain_rate`.
    """
    events = int(risk_budget_stats.get("events", 0))
    if events < max(1, int(config.risk_budget_guardrail_min_events)):
        return False
    abstains = int(risk_budget_stats.get("abstains", 0))
    abstain_rate = abstains / max(events, 1)
    return abstain_rate > float(config.risk_budget_guardrail_max_abstain_rate)


def build_not_enforced_response(
    *,
    threshold: float,
    reason: str,
    budget_id: str,
    confidence: float = 0.0,
) -> Dict[str, Any]:
    """Construct the 'gate not enforced' dict that callers return on bypass paths.

    Centralizes the schema so all kill-switch / risk-disabled / rollout-excluded /
    guardrail-blocked / insufficient-samples bypass paths look identical.
    """
    return {
        "enforced": False,
        "passed": True,
        "action": "not_enforced",
        "reason": reason,
        "confidence": confidence,
        "threshold": threshold,
        "budget_id": budget_id,
    }


def build_abstain_response(
    *, threshold: float, confidence: float, budget_id: str,
) -> Dict[str, Any]:
    """Construct the 'enforced + abstain' dict for confidence-below-threshold cases."""
    return {
        "enforced": True,
        "passed": False,
        "action": "abstain_escalate",
        "reason": "confidence_below_threshold",
        "confidence": confidence,
        "threshold": threshold,
        "budget_id": budget_id,
    }


def build_accept_response(
    *, threshold: float, confidence: float, budget_id: str,
) -> Dict[str, Any]:
    """Construct the 'enforced + accept' dict for confidence-meets-threshold cases."""
    return {
        "enforced": True,
        "passed": True,
        "action": "accept",
        "reason": "confidence_meets_threshold",
        "confidence": confidence,
        "threshold": threshold,
        "budget_id": budget_id,
    }
