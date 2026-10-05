"""Score / config structs for MemRL two-phase retrieval.

Extracted from retriever.py during the 2026-05-22 Tranche-6 refactor. Holds
RetrievalResult, RetrievalConfig, ScoreComponents — the pure-data containers
used across the routing stack. retriever.py re-imports these so existing
callers (tests + production code) keep working unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .episodic_store import MemoryEntry


def _retr_cfg():
    """Lazy import of the project config so module load doesn't require it."""
    from src.config import get_config

    return get_config().memrl_retrieval


@dataclass
class RetrievalResult:
    """Result of a two-phase (or three-phase) retrieval."""

    memory: MemoryEntry
    similarity: float  # Cosine similarity (0-1)
    q_value: float  # Learned utility (0-1)
    combined_score: float  # Weighted combination
    q_confidence: float = 0.0  # Robust confidence estimate from top-k Q values
    selection_score: float = 0.0  # Cost-aware routing score used for ranking
    p_warm: float = 0.0  # Probability that route is warm-cache
    warm_cost_s: float = 0.0  # Estimated warm latency in seconds
    cold_cost_s: float = 0.0  # Estimated cold latency in seconds
    expected_cost_s: float = 0.0  # p_warm*warm + (1-p_warm)*cold
    normalized_cost: float = 0.0  # expected_cost_s / cold_cost_s
    routing_pref_perf: float = 0.5  # DAR-4b performance scalarization weight
    routing_pref_cost: float = 0.5  # DAR-4b cost scalarization weight
    routing_cost_tau: float = 1.0  # DAR-4b runtime cost multiplier
    routing_perf_term: float = 0.0  # scalarized quality/performance term
    routing_cost_term: float = 0.0  # scalarized cost penalty term
    routing_preference_active: bool = False
    prior_term: float = 0.0  # Heuristic-prior contribution to posterior score
    posterior_score: float = 0.0  # selection_score + prior_term

    # Graph-enhanced fields (optional)
    failure_penalty: float = 0.0  # Risk score from failure graph (0-1)
    hypothesis_confidence: float = 1.0  # Confidence from hypothesis graph (0-1)
    adjusted_score: float = 0.0  # Final score after graph adjustments
    cache_affinity: float = 0.0  # Bonus for warm KV cache on same role (0-0.15)
    warnings: List[str] = field(default_factory=list)  # Low-confidence warnings


@dataclass
class RetrievalConfig:
    """Configuration for two-phase retrieval."""

    # Phase 1: Semantic filtering
    semantic_k: int = field(default_factory=lambda: _retr_cfg().semantic_k)
    min_similarity: float = field(default_factory=lambda: _retr_cfg().min_similarity)

    # Phase 2: Q-value ranking
    min_q_value: float = field(default_factory=lambda: _retr_cfg().min_q_value)
    q_weight: float = field(default_factory=lambda: _retr_cfg().q_weight)
    cost_lambda: float = field(default_factory=lambda: _retr_cfg().cost_lambda)
    cost_tau: float = field(default_factory=lambda: _retr_cfg().cost_tau)

    # Final selection
    top_n: int = field(default_factory=lambda: _retr_cfg().top_n)

    # Confidence threshold for using learned routing
    confidence_threshold: float = field(default_factory=lambda: _retr_cfg().confidence_threshold)
    confidence_estimator: str = field(default_factory=lambda: _retr_cfg().confidence_estimator)
    confidence_trim_ratio: float = field(default_factory=lambda: _retr_cfg().confidence_trim_ratio)
    confidence_min_neighbors: int = field(default_factory=lambda: _retr_cfg().confidence_min_neighbors)
    calibrated_confidence_threshold: Optional[float] = field(
        default_factory=lambda: _retr_cfg().calibrated_confidence_threshold
    )
    conformal_margin: float = field(default_factory=lambda: _retr_cfg().conformal_margin)
    risk_control_enabled: bool = field(default_factory=lambda: _retr_cfg().risk_control_enabled)
    risk_budget_id: str = field(default_factory=lambda: _retr_cfg().risk_budget_id)
    risk_gate_min_samples: int = field(default_factory=lambda: _retr_cfg().risk_gate_min_samples)
    risk_abstain_target_role: str = field(
        default_factory=lambda: _retr_cfg().risk_abstain_target_role
    )
    risk_gate_rollout_ratio: float = field(
        default_factory=lambda: _retr_cfg().risk_gate_rollout_ratio
    )
    risk_gate_kill_switch: bool = field(default_factory=lambda: _retr_cfg().risk_gate_kill_switch)
    risk_budget_guardrail_min_events: int = field(
        default_factory=lambda: _retr_cfg().risk_budget_guardrail_min_events
    )
    risk_budget_guardrail_max_abstain_rate: float = field(
        default_factory=lambda: _retr_cfg().risk_budget_guardrail_max_abstain_rate
    )
    prior_strength: float = field(default_factory=lambda: _retr_cfg().prior_strength)

    # Cache-aware expected cost model
    warm_probability_hit: float = field(default_factory=lambda: _retr_cfg().warm_probability_hit)
    warm_probability_miss: float = field(default_factory=lambda: _retr_cfg().warm_probability_miss)
    warm_cost_fallback_s: float = field(default_factory=lambda: _retr_cfg().warm_cost_fallback_s)
    cold_cost_fallback_s: float = field(default_factory=lambda: _retr_cfg().cold_cost_fallback_s)


@dataclass
class ScoreComponents:
    """Decomposed routing score components."""

    q_confidence: float
    similarity_support: float
    expected_cost_s: float
    selection_score: float
