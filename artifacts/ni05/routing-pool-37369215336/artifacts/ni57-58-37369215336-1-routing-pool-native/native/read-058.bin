"""
TwoPhaseRetriever: MemRL-style two-phase retrieval for episodic memory.

Phase 1: Semantic filtering - retrieve k candidates by embedding similarity
Phase 2: Q-value ranking - rank candidates by learned utility
Phase 3 (optional): Graph-enhanced scoring with failure penalties and hypothesis confidence

This separates "what's similar" from "what's useful" - the key insight from MemRL.
Enhanced with failure anti-memory and hypothesis tracking from Graphiti-inspired design.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import numpy as np

from .embedder import TaskEmbedder
from .episodic_store import EpisodicStore, MemoryEntry

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .failure_graph import FailureGraph
    from .hypothesis_graph import HypothesisGraph
    from .skill_retriever import SkillRetriever


def _routing_preference_weights(value: Any) -> Tuple[float, float, bool]:
    if not isinstance(value, dict):
        return 0.5, 0.5, False
    try:
        perf = float(value.get("perf", 0.5))
        cost = float(value.get("cost", 0.5))
    except (TypeError, ValueError):
        return 0.5, 0.5, False
    perf = max(0.0, perf)
    cost = max(0.0, cost)
    total = perf + cost
    if total <= 0.0:
        return 0.5, 0.5, False
    return perf / total, cost / total, True


def _scalarized_selection_score(
    *,
    q_value: float,
    normalized_cost: float,
    cost_lambda: float,
    cost_tau: float,
    pref_perf: float,
    pref_cost: float,
) -> tuple[float, float, float]:
    perf_term = 2.0 * pref_perf * q_value
    cost_term = 2.0 * pref_cost * cost_lambda * cost_tau * normalized_cost
    return perf_term - cost_term, perf_term, cost_term


# RetrievalConfig / RetrievalResult / ScoreComponents moved to retrieval_config.py
# (2026-05-22 Tranche-6 refactor). Re-exported here so existing
# `from orchestration.repl_memory.retriever import RetrievalConfig` callers
# (tests + production) keep working.
from .retrieval_config import (  # noqa: E402,F401
    RetrievalConfig,
    RetrievalResult,
    ScoreComponents,
    _retr_cfg,
)
from . import routing_fast_path as _routing_fast_path
from . import routing_risk as _routing_risk


class TwoPhaseRetriever:
    """
    Two-phase retrieval system for episodic memory.

    Phase 1 (Semantic Filtering):
    - Embed the query
    - Retrieve top-k memories by cosine similarity
    - Filter by minimum similarity threshold

    Phase 2 (Q-Value Ranking):
    - Rank candidates by learned Q-value
    - Combine similarity and Q-value scores
    - Return top-n by combined score
    """

    def __init__(
        self,
        store: EpisodicStore,
        embedder: TaskEmbedder,
        config: Optional[RetrievalConfig] = None,
    ):
        self.store = store
        self.embedder = embedder
        self.config = config or RetrievalConfig()
        self._last_role_used: Optional[str] = None
        self._risk_budget_stats: Dict[str, int] = {"events": 0, "abstains": 0}

    def _extract_role_from_memory(self, memory: MemoryEntry) -> str:
        """Best-effort role extraction from memory payload."""
        context = memory.context or {}
        role = context.get("role")
        if isinstance(role, str) and role:
            return role
        action = memory.action or ""
        first = action.split(",")[0].strip()
        if ":" in first:
            first = first.split(":", 1)[0]
        return first

    def _estimate_cost_components(self, memory: MemoryEntry) -> Tuple[float, float, float]:
        """Estimate (p_warm, warm_cost_s, cold_cost_s) for an action."""
        context = memory.context or {}
        role = self._extract_role_from_memory(memory)
        if role and self._last_role_used and role == self._last_role_used:
            p_warm = self.config.warm_probability_hit
        else:
            p_warm = self.config.warm_probability_miss

        warm_cost = float(
            context.get(
                "warm_elapsed_seconds",
                context.get(
                    "generation_seconds",
                    context.get("elapsed_seconds", self.config.warm_cost_fallback_s),
                ),
            )
        )
        cold_cost = float(
            context.get(
                "cold_elapsed_seconds",
                max(
                    context.get("elapsed_seconds", self.config.cold_cost_fallback_s),
                    self.config.cold_cost_fallback_s,
                ),
            )
        )
        warm_cost = max(1e-6, warm_cost)
        cold_cost = max(warm_cost, cold_cost)
        return p_warm, warm_cost, cold_cost

    def _compute_robust_confidence(self, q_values: List[float]) -> float:
        """Compute robust confidence from neighbor Q-values (delegates to routing_fast_path)."""
        return _routing_fast_path.compute_robust_confidence(
            q_values,
            estimator=self.config.confidence_estimator,
            trim_ratio=self.config.confidence_trim_ratio,
        )

    def _apply_confidence(self, results: List[RetrievalResult]) -> float:
        """Assign a shared robust confidence estimate across top neighbors."""
        return _routing_fast_path.apply_confidence_to_results(results, self.config)

    def get_effective_confidence_threshold(self) -> float:
        """Return the active routing threshold after calibration/risk controls."""
        return _routing_fast_path.effective_confidence_threshold(self.config)

    def retrieve_for_routing(
        self,
        task_ir: Dict[str, Any],
    ) -> List[RetrievalResult]:
        """
        Retrieve memories for task routing decision.

        Args:
            task_ir: TaskIR dictionary

        Returns:
            List of RetrievalResult sorted by combined score
        """
        embedding = self.embedder.embed_task_ir(task_ir)
        return self._retrieve(
            embedding,
            action_type="routing",
            routing_preferences=task_ir.get("routing_preferences"),
        )

    def retrieve_for_escalation(
        self,
        failure_context: Dict[str, Any],
    ) -> List[RetrievalResult]:
        """
        Retrieve memories for escalation decision.

        Args:
            failure_context: Failure context dictionary

        Returns:
            List of RetrievalResult sorted by combined score
        """
        embedding = self.embedder.embed_failure_context(failure_context)
        return self._retrieve(embedding, action_type="escalation")

    def retrieve_for_exploration(
        self,
        query: str,
        context_preview: str,
    ) -> List[RetrievalResult]:
        """
        Retrieve memories for REPL exploration strategy.

        Args:
            query: User query
            context_preview: Preview of context being explored

        Returns:
            List of RetrievalResult sorted by combined score
        """
        embedding = self.embedder.embed_exploration(query, context_preview)
        return self._retrieve(embedding, action_type="exploration")

    def retrieve_for_classification(
        self,
        prompt: str,
        classification_type: str = "routing",
    ) -> List[RetrievalResult]:
        """
        Retrieve memories for classification decision.

        Used by ClassificationRetriever to find similar classification exemplars
        and return the most confident classification based on Q-value weighted voting.

        Args:
            prompt: User prompt to classify.
            classification_type: Type of classification (routing, summarization, etc.).

        Returns:
            List of RetrievalResult sorted by combined score.
        """
        embedding = self.embedder.embed_classification_prompt(prompt, classification_type)
        return self._retrieve(embedding, action_type="classification")

    def _retrieve(
        self,
        embedding: np.ndarray,
        action_type: Optional[str] = None,
        routing_preferences: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        Execute two-phase retrieval.

        Args:
            embedding: Query embedding
            action_type: Optional filter by action type

        Returns:
            List of RetrievalResult sorted by combined score
        """
        # Phase 1: Semantic filtering
        candidates = self.store.retrieve_by_similarity(
            embedding,
            k=self.config.semantic_k,
            action_type=action_type,
            min_q_value=self.config.min_q_value,
        )

        if not candidates:
            return []

        # Compute similarities for candidates
        query_norm = embedding / (np.linalg.norm(embedding) + 1e-8)
        results = []
        pref_perf, pref_cost, pref_active = _routing_preference_weights(
            routing_preferences
        )
        cost_tau = float(getattr(self.config, "cost_tau", 1.0))

        for memory in candidates:
            if memory.embedding is None:
                similarity = memory.similarity_score
            else:
                mem_norm = memory.embedding / (np.linalg.norm(memory.embedding) + 1e-8)
                similarity = float(np.dot(query_norm, mem_norm))

            # Skip if below similarity threshold
            if similarity < self.config.min_similarity:
                continue

            # Phase 2: Legacy combined score retained for compatibility.
            combined = (
                self.config.q_weight * memory.q_value
                + (1 - self.config.q_weight) * similarity
            )
            p_warm, warm_cost, cold_cost = self._estimate_cost_components(memory)
            expected_cost = p_warm * warm_cost + (1.0 - p_warm) * cold_cost
            # Selection score is quality-cost objective.
            cost_ratio = expected_cost / max(cold_cost, 1e-6)
            selection, perf_term, cost_term = _scalarized_selection_score(
                q_value=memory.q_value,
                normalized_cost=cost_ratio,
                cost_lambda=float(self.config.cost_lambda),
                cost_tau=cost_tau,
                pref_perf=pref_perf,
                pref_cost=pref_cost,
            )

            results.append(
                RetrievalResult(
                    memory=memory,
                    similarity=similarity,
                    q_value=memory.q_value,
                    combined_score=combined,
                    selection_score=selection,
                    posterior_score=selection,
                    p_warm=p_warm,
                    warm_cost_s=warm_cost,
                    cold_cost_s=cold_cost,
                    expected_cost_s=expected_cost,
                    normalized_cost=cost_ratio,
                    routing_pref_perf=pref_perf,
                    routing_pref_cost=pref_cost,
                    routing_cost_tau=cost_tau,
                    routing_perf_term=perf_term,
                    routing_cost_term=cost_term,
                    routing_preference_active=pref_active or cost_tau != 1.0,
                )
            )

        # Sort by cost-aware selection score (descending)
        results.sort(key=lambda r: r.selection_score, reverse=True)
        self._apply_confidence(results)

        # Return top-n
        return results[: self.config.top_n]

    def get_best_action(
        self,
        results: List[RetrievalResult],
    ) -> Optional[Tuple[str, float]]:
        """
        Get the best action from retrieval results if confidence is high enough.

        Args:
            results: Retrieval results

        Returns:
            (action, confidence) tuple or None if not confident
        """
        if not results:
            return None

        best = results[0]
        if best.q_confidence >= self.get_effective_confidence_threshold():
            return (best.memory.action, best.q_confidence)

        return None

    def update_last_role(self, role: str) -> None:
        """Update the last-used role for cache affinity tracking.

        Call this after each routing decision to enable Phase 2.5
        cache affinity bonus on the next retrieval.
        """
        self._last_role_used = role

    def should_use_learned(
        self,
        results: List[RetrievalResult],
        min_samples: int = 3,
    ) -> bool:
        """
        Determine if we should use learned routing or fall back to rules.

        Criteria:
        - Have enough samples (min_samples)
        - Best result exceeds confidence threshold
        - At least some memories have been observed (Q-value != 0.5 default)

        Args:
            results: Retrieval results
            min_samples: Minimum number of similar samples

        Returns:
            True if should use learned routing
        """
        if len(results) < min_samples:
            return False

        best = results[0]
        if best.q_confidence < self.get_effective_confidence_threshold():
            return False

        # Check that Q-values are based on observations (not default 0.5)
        # Initial Q-values (0.5 + reward*0.5) are informative:
        # - Success → Q=1.0
        # - Failure → Q=0.25
        # None-safe: consolidated-store rows (2026-07-23 Q migration) may carry
        # NULL update_count/q_value; treat as unobserved rather than crashing
        # the whole routing path (72x 500s on /chat before this guard).
        observed_count = sum(
            1 for r in results
            if (r.memory.update_count or 0) > 0
            or abs((r.memory.q_value if r.memory.q_value is not None else 0.5) - 0.5) > 0.1
        )
        if observed_count < min_samples:
            return False

        return True

    def evaluate_risk_gate(
        self,
        results: List[RetrievalResult],
        route_key: str = "",
    ) -> Dict[str, Any]:
        """Evaluate strict runtime risk gate for abstain-or-escalate control."""
        threshold = self.get_effective_confidence_threshold()
        min_samples = max(int(self.config.risk_gate_min_samples), 1)

        if self.config.risk_gate_kill_switch:
            return {
                "enforced": False,
                "passed": True,
                "action": "not_enforced",
                "reason": "kill_switch_enabled",
                "confidence": 0.0,
                "threshold": threshold,
                "budget_id": self.config.risk_budget_id,
            }
        if not self.config.risk_control_enabled:
            return {
                "enforced": False,
                "passed": True,
                "action": "not_enforced",
                "reason": "risk_control_disabled",
                "confidence": 0.0,
                "threshold": threshold,
                "budget_id": self.config.risk_budget_id,
            }
        if not self._is_risk_gate_enforced_for_route(route_key):
            return {
                "enforced": False,
                "passed": True,
                "action": "not_enforced",
                "reason": "rollout_sampling_excluded",
                "confidence": 0.0 if not results else float(results[0].q_confidence),
                "threshold": threshold,
                "budget_id": self.config.risk_budget_id,
            }
        if self._guardrail_blocks_gate():
            return {
                "enforced": False,
                "passed": True,
                "action": "not_enforced",
                "reason": "budget_guardrail_abstain_rate",
                "confidence": 0.0 if not results else float(results[0].q_confidence),
                "threshold": threshold,
                "budget_id": self.config.risk_budget_id,
            }
        if len(results) < min_samples:
            return {
                "enforced": False,
                "passed": True,
                "action": "not_enforced",
                "reason": f"insufficient_samples:{len(results)}<{min_samples}",
                "confidence": 0.0 if not results else float(results[0].q_confidence),
                "threshold": threshold,
                "budget_id": self.config.risk_budget_id,
            }

        confidence = float(results[0].q_confidence)
        self._risk_budget_stats["events"] += 1
        if confidence < threshold:
            self._risk_budget_stats["abstains"] += 1
            return {
                "enforced": True,
                "passed": False,
                "action": "abstain_escalate",
                "reason": "confidence_below_threshold",
                "confidence": confidence,
                "threshold": threshold,
                "budget_id": self.config.risk_budget_id,
            }

        return {
            "enforced": True,
            "passed": True,
            "action": "accept",
            "reason": "confidence_meets_threshold",
            "confidence": confidence,
            "threshold": threshold,
            "budget_id": self.config.risk_budget_id,
        }

    def _is_risk_gate_enforced_for_route(self, route_key: str) -> bool:
        """Deterministic rollout sampler for strict gate enforcement."""
        return _routing_risk.is_risk_gate_enforced_for_route(self.config, route_key)

    def _guardrail_blocks_gate(self) -> bool:
        """Disable strict gate when abstain rate breaches configured budget guardrail."""
        return _routing_risk.guardrail_blocks_gate(self.config, self._risk_budget_stats)


# HybridRouter moved to hybrid_router.py (2026-05-22 Tranche-6 refactor).
# Re-exported so `from orchestration.repl_memory.retriever import HybridRouter`
# (test + production callers) keeps working.
from .hybrid_router import HybridRouter  # noqa: E402,F401


class RuleBasedRouter:
    """
    Rule-based router from model_registry.yaml.

    Used as fallback when learned routing is not confident.
    """

    def __init__(self, routing_hints: List[Dict[str, Any]]):
        """
        Initialize with routing hints from model_registry.yaml.

        Args:
            routing_hints: List of routing hint dictionaries
        """
        self.routing_hints = routing_hints

    def route(self, task_ir: Dict[str, Any]) -> List[str]:
        """
        Route using rule-based hints.

        Args:
            task_ir: TaskIR dictionary

        Returns:
            List of role names to use
        """
        task_type = task_ir.get("task_type", "chat")
        priority = task_ir.get("priority", "interactive")
        has_images = any(
            inp.get("type") == "image" for inp in task_ir.get("inputs", [])
        )

        # Check routing hints
        for hint in self.routing_hints:
            # Support both dict and RoutingHint dataclass
            if hasattr(hint, "condition"):
                condition = hint.condition
                use = hint.use
            else:
                condition = hint.get("if", "")
                use = hint.get("use", ["frontdoor"])
            if self._evaluate_condition(
                condition, task_type, priority, has_images, task_ir
            ):
                return use

        # Default routing
        return ["frontdoor"]

    def route_with_mode(
        self, task_ir: Dict[str, Any]
    ) -> Tuple[List[str], str]:
        """Route using rule-based hints with mode selection.

        Mode is selected based on task characteristics:
        - Large context → "repl" (needs peek/grep/summarize_chunks)
        - Tool-needing keywords → "react" (search, calculate, date)
        - Everything else → "direct" (best instruction-following quality)

        Args:
            task_ir: TaskIR dictionary

        Returns:
            (routing_list, mode) tuple
        """
        routing = self.route(task_ir)

        # Determine mode from task characteristics
        objective = task_ir.get("objective", "").lower()
        context_len = task_ir.get("context_length", 0)
        task_type = task_ir.get("task_type", "chat")

        # Large context → REPL for chunked exploration
        if context_len > 20000 or task_type == "ingest":
            return routing, "repl"

        # File operations → REPL
        file_indicators = [
            "read file", "list files", "explore", "scan",
            "write to", "save to", "open the file",
        ]
        if any(ind in objective for ind in file_indicators):
            return routing, "repl"

        # Tool-needing queries → ReAct
        react_indicators = [
            "search", "look up", "find information",
            "current date", "current time", "calculate",
            "search arxiv", "search papers", "wikipedia",
        ]
        if any(ind in objective for ind in react_indicators):
            return routing, "react"

        # Default → direct (best quality for instruction following)
        return routing, "direct"

    def _evaluate_condition(
        self,
        condition: str,
        task_type: str,
        priority: str,
        has_images: bool,
        task_ir: Dict[str, Any],
    ) -> bool:
        """Evaluate a routing condition."""
        # Simple condition parsing (from model_registry.yaml format)
        if "task_type == 'code'" in condition and task_type == "code":
            return True
        if "task_type == 'ingest'" in condition and task_type == "ingest":
            return True
        if "task_type == 'doc'" in condition and task_type == "doc":
            if "priority == 'interactive'" in condition and priority == "interactive":
                return True
            elif "priority" not in condition:
                return True
        if "task_type == 'manage'" in condition and task_type == "manage":
            return True
        if "has_images == true" in condition and has_images:
            return True
        if "needs_math_reasoning == true" in condition:
            # Check for math-related keywords in objective
            objective = task_ir.get("objective", "").lower()
            if any(kw in objective for kw in ["math", "calculate", "prove", "theorem"]):
                return True
        return False


class GraphEnhancedRetriever(TwoPhaseRetriever):
    """
    Graph-enhanced retriever with failure anti-memory and hypothesis tracking.

    Extends TwoPhaseRetriever with:
    - Failure graph penalty: Penalize actions linked to past failures
    - Hypothesis confidence: Warn on low-confidence action-task combinations
    - TTL caching: Graph lookups cached for 60s (80%+ cache hit rate expected)

    Scoring formula:
        adjusted_score = similarity × Q_value × (1 - failure_penalty) × hypothesis_confidence
    """

    def __init__(
        self,
        store: EpisodicStore,
        embedder: TaskEmbedder,
        failure_graph: Optional["FailureGraph"] = None,
        hypothesis_graph: Optional["HypothesisGraph"] = None,
        config: Optional[RetrievalConfig] = None,
        cache_ttl: int = 60,  # Cache TTL in seconds
        cache_maxsize: int = 500,  # Max cached items
    ):
        super().__init__(store, embedder, config)
        self.failure_graph = failure_graph
        self.hypothesis_graph = hypothesis_graph

        # TTL caches for graph lookups (5-20ms -> <1ms for cache hits)
        try:
            from cachetools import TTLCache
            self._failure_cache: Optional[TTLCache] = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
            self._confidence_cache: Optional[TTLCache] = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
        except ImportError:
            # cachetools not installed - fall back to no caching
            self._failure_cache = None
            self._confidence_cache = None

    def _get_failure_penalty(self, action: str) -> float:
        """Get failure penalty with caching (5-20ms -> <1ms for cache hits)."""
        if self.failure_graph is None:
            return 0.0

        # Check cache first
        if self._failure_cache is not None:
            if action in self._failure_cache:
                return self._failure_cache[action]

        # Cache miss - fetch from graph
        try:
            penalty = self.failure_graph.get_failure_risk(action)
            if self._failure_cache is not None:
                self._failure_cache[action] = penalty
            return penalty
        except Exception:
            return 0.0  # Graceful degradation

    def _get_hypothesis_confidence(self, action: str, task_type: str) -> float:
        """Get hypothesis confidence with caching (5-20ms -> <1ms for cache hits)."""
        if self.hypothesis_graph is None or not task_type:
            return 1.0

        # Check cache first (key is action|task_type)
        cache_key = f"{action}|{task_type}"
        if self._confidence_cache is not None:
            if cache_key in self._confidence_cache:
                return self._confidence_cache[cache_key]

        # Cache miss - fetch from graph
        try:
            confidence = self.hypothesis_graph.get_confidence(action, task_type)
            if self._confidence_cache is not None:
                self._confidence_cache[cache_key] = confidence
            return confidence
        except Exception:
            return 1.0  # Graceful degradation

    def _retrieve(
        self,
        embedding: np.ndarray,
        action_type: Optional[str] = None,
        task_type: Optional[str] = None,
        routing_preferences: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievalResult]:
        """
        Execute three-phase retrieval with graph enhancement.

        Args:
            embedding: Query embedding
            action_type: Optional filter by action type
            task_type: Task type for hypothesis lookup

        Returns:
            List of RetrievalResult sorted by adjusted score
        """
        # Phase 1 & 2: Standard retrieval
        candidates = self.store.retrieve_by_similarity(
            embedding,
            k=self.config.semantic_k,
            action_type=action_type,
            min_q_value=self.config.min_q_value,
        )

        if not candidates:
            return []

        # Compute similarities for candidates
        query_norm = embedding / (np.linalg.norm(embedding) + 1e-8)
        results = []
        pref_perf, pref_cost, pref_active = _routing_preference_weights(
            routing_preferences
        )
        cost_tau = float(getattr(self.config, "cost_tau", 1.0))

        for memory in candidates:
            # Handle case where embedding might be None (FAISS optimization)
            if memory.embedding is None:
                similarity = memory.similarity_score  # Use pre-computed from FAISS
            else:
                mem_norm = memory.embedding / (np.linalg.norm(memory.embedding) + 1e-8)
                similarity = float(np.dot(query_norm, mem_norm))

            # Skip if below similarity threshold
            if similarity < self.config.min_similarity:
                continue

            # Phase 2: Combine similarity and Q-value
            combined = (
                self.config.q_weight * memory.q_value
                + (1 - self.config.q_weight) * similarity
            )

            # Phase 3: Graph-enhanced scoring (with caching)
            warnings = []

            # Get failure penalty with caching
            failure_penalty = self._get_failure_penalty(memory.action)

            # Get hypothesis confidence with caching
            hypothesis_confidence = self._get_hypothesis_confidence(
                memory.action, task_type or ""
            )

            # Add warnings for low confidence (not cached - rare case)
            if hypothesis_confidence < 0.2 and self.hypothesis_graph is not None and task_type:
                try:
                    graph_warnings = self.hypothesis_graph.get_low_confidence_warnings(
                        memory.action, task_type
                    )
                    warnings.extend(graph_warnings)
                except Exception:
                    pass  # Graceful degradation

            p_warm, warm_cost, cold_cost = self._estimate_cost_components(memory)
            expected_cost = p_warm * warm_cost + (1.0 - p_warm) * cold_cost
            cost_ratio = expected_cost / max(cold_cost, 1e-6)
            selection, perf_term, cost_term = _scalarized_selection_score(
                q_value=memory.q_value,
                normalized_cost=cost_ratio,
                cost_lambda=float(self.config.cost_lambda),
                cost_tau=cost_tau,
                pref_perf=pref_perf,
                pref_cost=pref_cost,
            )
            # Calculate adjusted score
            adjusted_score = selection * (1 - failure_penalty) * hypothesis_confidence

            results.append(
                RetrievalResult(
                    memory=memory,
                    similarity=similarity,
                    q_value=memory.q_value,
                    combined_score=combined,
                    selection_score=selection,
                    p_warm=p_warm,
                    warm_cost_s=warm_cost,
                    cold_cost_s=cold_cost,
                    expected_cost_s=expected_cost,
                    normalized_cost=cost_ratio,
                    routing_pref_perf=pref_perf,
                    routing_pref_cost=pref_cost,
                    routing_cost_tau=cost_tau,
                    routing_perf_term=perf_term,
                    routing_cost_term=cost_term,
                    routing_preference_active=pref_active or cost_tau != 1.0,
                    failure_penalty=failure_penalty,
                    hypothesis_confidence=hypothesis_confidence,
                    adjusted_score=adjusted_score,
                    warnings=warnings,
                )
            )

        # Sort by adjusted score (descending)
        results.sort(key=lambda r: r.adjusted_score, reverse=True)

        top = results[: self.config.top_n]
        self._apply_confidence(top)
        return top

    def retrieve_for_routing(
        self,
        task_ir: Dict[str, Any],
    ) -> List[RetrievalResult]:
        """Retrieve with graph enhancement for routing."""
        embedding = self.embedder.embed_task_ir(task_ir)
        task_type = task_ir.get("task_type", "general")
        return self._retrieve(
            embedding,
            action_type="routing",
            task_type=task_type,
            routing_preferences=task_ir.get("routing_preferences"),
        )

    def retrieve_for_escalation(
        self,
        failure_context: Dict[str, Any],
    ) -> List[RetrievalResult]:
        """Retrieve with graph enhancement for escalation."""
        embedding = self.embedder.embed_failure_context(failure_context)
        task_type = failure_context.get("task_type", "escalation")
        return self._retrieve(embedding, action_type="escalation", task_type=task_type)

    def retrieve_for_exploration(
        self,
        query: str,
        context_preview: str,
        task_type: str = "exploration",
    ) -> List[RetrievalResult]:
        """Retrieve with graph enhancement for exploration."""
        embedding = self.embedder.embed_exploration(query, context_preview)
        return self._retrieve(embedding, action_type="exploration", task_type=task_type)

    def get_best_action(
        self,
        results: List[RetrievalResult],
    ) -> Optional[Tuple[str, float, List[str]]]:
        """
        Get the best action with warnings.

        Args:
            results: Retrieval results

        Returns:
            (action, confidence, warnings) tuple or None if not confident
        """
        if not results:
            return None

        best = results[0]
        if best.q_confidence >= self.get_effective_confidence_threshold():
            return (best.memory.action, best.q_confidence, best.warnings)

        return None


class SkillAugmentedRouter:
    """
    Wraps HybridRouter with SkillBank skill retrieval and prompt injection.

    Adds SkillRL §3.2 two-level skill retrieval on top of existing
    HybridRouter routing. The retrieved skill context is returned alongside
    routing decisions for prompt injection.

    Usage:
        router = SkillAugmentedRouter(hybrid_router, skill_retriever, embedder)
        decision, strategy, skill_context = router.route_with_skills(task_ir)
    """

    def __init__(
        self,
        hybrid_router: HybridRouter,
        skill_retriever: "SkillRetriever",
        embedder: "TaskEmbedder",
    ):
        self.hybrid_router = hybrid_router
        self.skill_retriever = skill_retriever
        self.embedder = embedder

    def route(self, task_ir: Dict[str, Any]) -> Tuple[List[str], str]:
        """Delegate to HybridRouter (unchanged interface)."""
        return self.hybrid_router.route(task_ir)

    def route_with_skills(
        self, task_ir: Dict[str, Any]
    ) -> Tuple[List[str], str, str]:
        """
        Route with skill context for prompt injection.

        Args:
            task_ir: TaskIR dictionary

        Returns:
            (routing_decision, strategy, skill_context) tuple.
            skill_context is a formatted markdown string (may be empty).
        """
        routing_decision, strategy = self.hybrid_router.route(task_ir)

        # Retrieve skills for prompt augmentation
        skill_context = ""
        try:
            embedding = self.embedder.embed_task_ir(task_ir)
            task_type = task_ir.get("task_type", "general")
            results = self.skill_retriever.retrieve_for_task(embedding, task_type)
            if results:
                skill_context = self.skill_retriever.format_for_prompt(results)
        except Exception as e:
            logger.debug("Skill retrieval failed (non-fatal): %s", e)

        return routing_decision, strategy, skill_context

    def route_with_mode(
        self, task_ir: Dict[str, Any]
    ) -> Tuple[List[str], str, str]:
        """Delegate to HybridRouter.route_with_mode (unchanged interface)."""
        return self.hybrid_router.route_with_mode(task_ir)

    @property
    def retriever(self):
        """Expose underlying retriever for protocol compatibility."""
        return self.hybrid_router.retriever

    @property
    def last_decision_meta(self) -> Dict[str, Any]:
        """Expose underlying decision metadata for telemetry."""
        return getattr(self.hybrid_router, "last_decision_meta", {})
