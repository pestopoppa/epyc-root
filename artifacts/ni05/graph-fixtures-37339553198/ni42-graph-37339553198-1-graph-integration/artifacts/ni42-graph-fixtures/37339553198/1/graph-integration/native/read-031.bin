"""HybridRouter — learned + rule-based fusion for orchestrator routing.

Extracted from retriever.py during the 2026-05-22 Tranche-6 refactor. The
class combines a TwoPhaseRetriever's KNN/Q-value scores with a RuleBasedRouter
fallback, optional GraphRouterPredictor blending, classifier fast-path,
frontdoor-specialist verifier (P6.2-A2), and DAR-3 epsilon-greedy exploration.

retriever.py re-imports HybridRouter so existing `from
orchestration.repl_memory.retriever import HybridRouter` calls keep working.

GitNexus impact analysis (pre-refactor): MEDIUM risk, 14 direct callers, 44
impacted symbols. Constructor + method signatures are preserved verbatim — no
behavioral changes — to minimize regression risk in the routing path.
"""

from __future__ import annotations

import logging
import os
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import numpy as np

from .retrieval_config import RetrievalResult

if TYPE_CHECKING:
    from .graph_router_predictor import GraphRouterPredictor
    from .routing_classifier import RoutingClassifier
    # Forward-only — these classes still live in retriever.py
    from .retriever import RuleBasedRouter, TwoPhaseRetriever

logger = logging.getLogger(__name__)


class HybridRouter:
    """
    Hybrid routing that combines learned and rule-based approaches.

    Uses learned routing when confident, falls back to rules otherwise.
    This implements the cold start strategy from the plan.
    """

    def __init__(
        self,
        retriever: TwoPhaseRetriever,
        rule_based_router: "RuleBasedRouter",  # Forward reference
        graph_router: Optional["GraphRouterPredictor"] = None,
        graph_router_weight: float = 0.3,
        routing_classifier: Optional["RoutingClassifier"] = None,
        classifier_confidence_threshold: float = 0.8,
        exploration_epsilon: float = 0.0,
        frontdoor_verifier: Optional[Any] = None,
        frontdoor_verifier_threshold: float = 0.5,
    ):
        self.retriever = retriever
        self.rule_based = rule_based_router
        self.graph_router = graph_router
        self.graph_router_weight = graph_router_weight
        self.routing_classifier = routing_classifier
        self.classifier_confidence_threshold = classifier_confidence_threshold
        # P6.2-A2 — frontdoor-specialist verifier (Hypothesis C from
        # research/deep-dives/2026-05-21-recursive-reasoning-routing.md).
        # When set, fires after the classifier picks top-class=frontdoor with
        # confidence above its per-class threshold. If verifier P(success) drops
        # below frontdoor_verifier_threshold, the fast-path is BYPASSED and the
        # request falls through to the full KNN pipeline. Default-OFF in
        # production: memrl.py only constructs a verifier when
        # ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE=1.
        self.frontdoor_verifier = frontdoor_verifier
        self.frontdoor_verifier_threshold = float(
            os.environ.get("FRONTDOOR_VERIFIER_THRESHOLD", str(frontdoor_verifier_threshold))
        )
        self.frontdoor_verifier_shadow = (
            os.environ.get("FRONTDOOR_VERIFIER_SHADOW", "0") == "1"
        )
        # DAR-3: Epsilon-greedy exploration for counterfactual data collection.
        # When > 0, with probability epsilon, pick a random alternative from
        # retrieval results instead of the best. Set via SPO_PLUS_EPSILON env var.
        self.exploration_epsilon = float(
            os.environ.get("SPO_PLUS_EPSILON", str(exploration_epsilon))
        )
        self.last_decision_meta: Dict[str, Any] = {}

        # Serving routes and control-plane actions share the episodic store but
        # must never share an action namespace. Cache the realized serving
        # action set once per API process; a reload is already required when the
        # generated stack-priors contract changes.
        try:
            from src.registry.stack_priors import live_stack_role_ids

            self._live_routing_roles = set(live_stack_role_ids())
        except Exception:
            self._live_routing_roles = set()
        if not self._live_routing_roles:
            # Explicit degraded fallback: retain current serving roles while
            # excluding draft-only and retired compatibility enum members.
            from src.roles import Role

            self._live_routing_roles = {
                role.value
                for role in Role
                if role.value not in {"draft_coder", "draft_general", "thinking_reasoning"}
            }

        # DAR-4: Bilinear scorer for zero cold-start model routing.
        # Initialized lazily on first use when BILINEAR_SCORER_ENABLED=1.
        self._bilinear_scorer = None
        if os.environ.get("BILINEAR_SCORER_ENABLED", "0") == "1":
            try:
                from orchestration.repl_memory.bilinear_scorer import (
                    BilinearScorer,
                    extract_model_features,
                )
                from orchestration.repl_memory.q_scorer import ScoringConfig
                features = extract_model_features(ScoringConfig())
                self._bilinear_scorer = BilinearScorer(features)
                # Try loading saved weights
                import pathlib
                weights_path = str(pathlib.Path(__file__).parent / "bilinear_scorer_weights.npz")
                self._bilinear_scorer.load(weights_path)
                logger.info("DAR-4 bilinear scorer initialized (%d models)", len(features))
            except Exception as e:
                logger.warning("DAR-4 bilinear scorer init failed: %s", e)
                self._bilinear_scorer = None

    @staticmethod
    def _normalize_action(action: Optional[str]) -> str:
        """Defensive remap of legacy mode suffixes to current vocabulary.

        2026-05-25: React mode was unified into REPL (REPL is a superset).
        Any `<role>:react` reaching this layer is replayed legacy seed data
        — rewrite to `<role>:repl` so the routing-decision telemetry +
        the downstream dispatch agree.
        """
        if not action:
            return ""
        if action.endswith(":react"):
            return action[:-len(":react")] + ":repl"
        return action

    def _routing_cost_term(self, result: RetrievalResult) -> float:
        term = float(getattr(result, "routing_cost_term", 0.0) or 0.0)
        if term or bool(getattr(result, "routing_preference_active", False)):
            return term
        return float(self.retriever.config.cost_lambda) * (
            result.expected_cost_s / max(result.cold_cost_s, 1e-6)
        )

    @staticmethod
    def _normalized_cost(result: RetrievalResult) -> float:
        normalized = float(getattr(result, "normalized_cost", 0.0) or 0.0)
        if normalized:
            return normalized
        return float(result.expected_cost_s) / max(float(result.cold_cost_s), 1e-6)

    def _record_decision_meta(
        self,
        *,
        strategy: str,
        chosen_action: Optional[str],
        results: List[RetrievalResult],
        risk_gate: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store metadata for telemetry logging."""
        chosen_action = self._normalize_action(chosen_action)
        top = results[:5]
        self.last_decision_meta = {
            "decision_source": strategy,
            "chosen_action": chosen_action or "",
            "action_topk": [
                self._normalize_action(getattr(r.memory, "action", ""))
                for r in top
            ],
            "similarity_topk": [round(r.similarity, 4) for r in top],
            "q_topk": [round(r.q_value, 4) for r in top],
            "q_robust_confidence": round(top[0].q_confidence, 4) if top else 0.0,
            "selection_score_topk": [round(r.selection_score, 4) for r in top],
            "prior_term_topk": [round(r.prior_term, 4) for r in top],
            "posterior_score_topk": [round(r.posterior_score, 4) for r in top],
            "learned_evidence_topk": [round(r.q_value, 4) for r in top],
            "cost_term_topk": [
                round(self._routing_cost_term(r), 4) for r in top
            ],
            "normalized_cost_topk": [
                round(self._normalized_cost(r), 4) for r in top
            ],
            "routing_pref_perf": round(
                getattr(top[0], "routing_pref_perf", 0.5), 4
            ) if top else 0.5,
            "routing_pref_cost": round(
                getattr(top[0], "routing_pref_cost", 0.5), 4
            ) if top else 0.5,
            "routing_cost_tau": round(
                getattr(top[0], "routing_cost_tau", 1.0), 4
            ) if top else 1.0,
            "routing_preference_active": bool(
                getattr(top[0], "routing_preference_active", False)
            ) if top else False,
            "cache_state": (
                "warm"
                if top and top[0].p_warm >= 0.7
                else "cold"
                if top and top[0].p_warm <= 0.3
                else "mixed"
            ),
            "expected_cost_s": round(top[0].expected_cost_s, 4) if top else 0.0,
            "p_warm": round(top[0].p_warm, 4) if top else 0.0,
            "warm_cost_s": round(top[0].warm_cost_s, 4) if top else 0.0,
            "cold_cost_s": round(top[0].cold_cost_s, 4) if top else 0.0,
            "effective_confidence_threshold": round(
                self.retriever.get_effective_confidence_threshold(), 4
            ),
            "risk_gate_action": (
                str((risk_gate or {}).get("action"))
                if risk_gate
                else ("not_enforced" if not self.retriever.config.risk_control_enabled else "")
            ),
            "risk_gate_reason": str((risk_gate or {}).get("reason", "")),
            "risk_budget_id": str(
                (risk_gate or {}).get("budget_id", self.retriever.config.risk_budget_id)
            ),
            "graph_router_ready": bool(
                self.graph_router and self.graph_router.is_ready
            ) if self.graph_router else False,
            "graph_router_weight": round(
                self._get_adaptive_graph_weight(), 4
            ) if self.graph_router else 0.0,
        }

        # URE-1 (J10): shadow-log routing decision-uncertainty. Default-off flag; this NEVER
        # affects the routing decision. Fully self-contained + exception-safe so a logging
        # failure cannot break a live decision (single chokepoint — all route() paths land here).
        try:
            from src.features import features as _features
            if _features().ure_uncertainty_shadow_log:
                from src.uncertainty_shadow import emit_uncertainty_shadow
                emit_uncertainty_shadow(self.last_decision_meta)
        except Exception:
            logger.debug("URE-1 uncertainty shadow hook failed", exc_info=True)

    def _get_adaptive_graph_weight(self) -> float:
        """Compute adaptive blend weight based on episodic store size.

        Annealing schedule:
        - Below 500 memories: w=0.1 (minimal GNN trust, cold-start)
        - 500-2000 memories: linear ramp 0.1->0.3
        - Above 2000: w=0.3 (max GNN influence)

        Returns:
            Blend weight in [0.1, graph_router_weight]
        """
        try:
            store_size = self.retriever.store.count()
        except Exception:
            return 0.1

        min_w = 0.1
        max_w = self.graph_router_weight
        if store_size < 500:
            return min_w
        if store_size >= 2000:
            return max_w
        # Linear interpolation
        t = (store_size - 500) / 1500.0
        return min_w + t * (max_w - min_w)

    def _blend_graph_router_scores(
        self,
        results: List[RetrievalResult],
        task_ir: Dict[str, Any],
    ) -> None:
        """Blend GraphRouter signal into posterior scores.

        Formula: posterior = (1-w) * retriever_score + w * graph_score
        """
        if not results:
            return

        # Get query embedding (reuse from retriever)
        try:
            embedding = self.retriever.embedder.embed_task_ir(task_ir)
        except Exception:
            return

        task_type = task_ir.get("task_type", "general")
        gr_scores = self.graph_router.predict(embedding, task_type)

        if not gr_scores:
            return

        w = self._get_adaptive_graph_weight()

        for r in results:
            role = self.retriever._extract_role_from_memory(r.memory)
            if role in gr_scores:
                r.posterior_score = (1 - w) * r.posterior_score + w * gr_scores[role]

        results.sort(key=lambda r: r.posterior_score, reverse=True)

    def _action_prior_prob(self, action: str, priors: Dict[str, float]) -> float:
        """Map action string to prior probability mass."""
        first = action.split(",")[0].strip()
        if ":" in first:
            first = first.split(":", 1)[0]
        return float(priors.get(first, priors.get(action, 0.0)))

    def _apply_priors(
        self,
        results: List[RetrievalResult],
        priors: Optional[Dict[str, float]],
    ) -> List[RetrievalResult]:
        """Combine heuristic priors with learned evidence into posterior score."""
        if not results:
            return results
        if not priors:
            for r in results:
                r.prior_term = 0.0
                r.posterior_score = r.selection_score
            return sorted(results, key=lambda x: x.posterior_score, reverse=True)

        strength = float(self.retriever.config.prior_strength)
        for r in results:
            prior_prob = self._action_prior_prob(r.memory.action, priors)
            r.prior_term = strength * prior_prob
            r.posterior_score = r.selection_score + r.prior_term
        return sorted(results, key=lambda x: x.posterior_score, reverse=True)

    def _canonical_routable_role(self, role_name: str) -> Optional[str]:
        """Return a live serving role, or ``None`` for control/invalid labels."""
        from src.roles import Role

        role = Role.from_string(str(role_name).strip())
        if role is None or role.value not in self._live_routing_roles:
            return None
        return role.value

    def _filter_routable_results(
        self, results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """Exclude non-serving memories before any learned action selection."""
        filtered = [
            result
            for result in results
            if self._parse_routing_action(result.memory.action)
        ]
        rejected = len(results) - len(filtered)
        if rejected:
            logger.warning(
                "Rejected %d non-serving episodic routing candidate(s)", rejected
            )
        return filtered

    # Task types matching extract_training_data.py (order must be stable)
    _CLASSIFIER_TASK_TYPES = ["code", "chat", "architecture", "ingest", "general"]

    def _build_classifier_features(self, task_ir: Dict[str, Any]) -> Optional[np.ndarray]:
        """Build 1031-dim feature vector for classifier from task_ir.

        Returns None if embedding fails.
        """
        try:
            embedding = self.retriever.embedder.embed_task_ir(task_ir)
        except Exception:
            return None

        emb = np.asarray(embedding, dtype=np.float32)

        # Task type one-hot
        tt_vec = np.zeros(len(self._CLASSIFIER_TASK_TYPES), dtype=np.float32)
        task_type = (task_ir.get("task_type", "general") or "general").lower()
        matched = False
        for i, tt in enumerate(self._CLASSIFIER_TASK_TYPES):
            if tt in task_type:
                tt_vec[i] = 1.0
                matched = True
                break
        if not matched:
            tt_vec[self._CLASSIFIER_TASK_TYPES.index("general")] = 1.0

        # Context features
        ctx_len = task_ir.get("context_length", 0)
        norm_ctx_len = np.float32(np.log1p(ctx_len) / 12.0)
        has_images = np.float32(1.0 if task_ir.get("has_images", False) else 0.0)

        return np.concatenate([emb, tt_vec, [norm_ctx_len], [has_images]])

    def route(
        self,
        task_ir: Dict[str, Any],
        priors: Optional[Dict[str, float]] = None,
    ) -> Tuple[List[str], str]:
        """
        Route a task using hybrid strategy.

        Args:
            task_ir: TaskIR dictionary

        Returns:
            (routing_decision, strategy_used) tuple
            strategy_used is "learned" or "rules"
        """
        # Classifier fast-path: skip full retrieval if confident
        preference_override = isinstance(task_ir.get("routing_preferences"), dict)
        if self.routing_classifier is not None and not preference_override:
            features = self._build_classifier_features(task_ir)
            if features is not None:
                action, confidence = self.routing_classifier.predict_action(features)
                # Per-class thresholds: action is None when below threshold
                # Global threshold: fallback for classifiers without per-class calibration
                if action is not None and confidence >= self.classifier_confidence_threshold:
                    routing = self._parse_routing_action(action)
                    if routing:
                        # P6.2-A2 — frontdoor-specialist verifier gate. Fires
                        # only when the classifier's chosen action is frontdoor.
                        # In shadow mode, log the verifier's verdict but don't
                        # gate. In enforcing mode, if P(success) < threshold,
                        # do NOT return via fast-path — fall through to KNN.
                        verifier_p = None
                        verifier_verdict = None
                        if (
                            self.frontdoor_verifier is not None
                            and routing[0] == "frontdoor"
                        ):
                            try:
                                verifier_p = float(self.frontdoor_verifier.predict(
                                    features, action_idx=0,
                                ))
                            except Exception as exc:
                                logger.warning(
                                    "frontdoor verifier predict failed: %s", exc,
                                )
                                verifier_p = None
                            if verifier_p is not None:
                                verifier_verdict = (
                                    "accept" if verifier_p >= self.frontdoor_verifier_threshold
                                    else "reject"
                                )
                                if (
                                    verifier_verdict == "reject"
                                    and not self.frontdoor_verifier_shadow
                                ):
                                    # Enforcing mode + reject: skip fast-path,
                                    # let the normal KNN path take over below.
                                    self.last_decision_meta = {
                                        "decision_source": "classifier_verifier_reject",
                                        "chosen_action": action,
                                        "classifier_confidence": round(confidence, 4),
                                        "classifier_threshold": self.classifier_confidence_threshold,
                                        "verifier_p_success": round(verifier_p, 4),
                                        "verifier_threshold": self.frontdoor_verifier_threshold,
                                        "verifier_verdict": "reject",
                                    }
                                    # Intentionally do NOT return here — fall
                                    # through to KNN below.
                                    pass
                                else:
                                    self.retriever.update_last_role(routing[0])
                                    self.last_decision_meta = {
                                        "decision_source": "classifier",
                                        "chosen_action": action,
                                        "classifier_confidence": round(confidence, 4),
                                        "classifier_threshold": self.classifier_confidence_threshold,
                                        "verifier_p_success": round(verifier_p, 4),
                                        "verifier_threshold": self.frontdoor_verifier_threshold,
                                        "verifier_verdict": verifier_verdict,
                                        "verifier_shadow": self.frontdoor_verifier_shadow,
                                    }
                                    return (routing, "classifier")
                            else:
                                # Verifier error — fall back to classifier alone
                                self.retriever.update_last_role(routing[0])
                                self.last_decision_meta = {
                                    "decision_source": "classifier",
                                    "chosen_action": action,
                                    "classifier_confidence": round(confidence, 4),
                                    "classifier_threshold": self.classifier_confidence_threshold,
                                    "verifier_error": True,
                                }
                                return (routing, "classifier")
                        else:
                            # No verifier configured OR non-frontdoor route
                            self.retriever.update_last_role(routing[0])
                            self.last_decision_meta = {
                                "decision_source": "classifier",
                                "chosen_action": action,
                                "classifier_confidence": round(confidence, 4),
                                "classifier_threshold": self.classifier_confidence_threshold,
                            }
                            return (routing, "classifier")

        # DAR-4: Bilinear scorer provides a prior from model features.
        # Log scores for telemetry; blending into retrieval is future work.
        if self._bilinear_scorer is not None:
            try:
                from orchestration.repl_memory.bilinear_scorer import extract_prompt_features
                prompt_features = extract_prompt_features(task_ir)
                bilinear_scores = self._bilinear_scorer.predict_all(prompt_features)
                self.last_decision_meta["bilinear_scores"] = {
                    k: round(v, 4) for k, v in list(bilinear_scores.items())[:5]
                }
            except Exception:
                pass

        # Try learned routing first
        results = self.retriever.retrieve_for_routing(task_ir)
        results = self._filter_routable_results(results)
        results = self._apply_priors(results, priors)

        # Blend GraphRouter signal if available
        if self.graph_router and self.graph_router.is_ready:
            self._blend_graph_router_scores(results, task_ir)

        route_key = str(task_ir.get("task_id", task_ir.get("objective", "")))
        risk_gate = self.retriever.evaluate_risk_gate(results, route_key=route_key)

        if risk_gate.get("enforced") and not risk_gate.get("passed"):
            routing = [self.retriever.config.risk_abstain_target_role]
            self.retriever.update_last_role(routing[0])
            self._record_decision_meta(
                strategy="risk_abstain_escalate",
                chosen_action=",".join(routing),
                results=results,
                risk_gate=risk_gate,
            )
            return (routing, "risk_abstain_escalate")

        if self.retriever.should_use_learned(results):
            best_action = self.retriever.get_best_action(results)
            if best_action:
                action = best_action[0]
                confidence = best_action[1]
                strategy = "learned"

                # DAR-3: Epsilon-greedy exploration for counterfactual data.
                # With probability epsilon, pick a random alternative action.
                if (
                    self.exploration_epsilon > 0
                    and random.random() < self.exploration_epsilon
                    and len(results) > 1
                ):
                    # Collect unique alternative actions
                    alt_actions = [
                        r.memory.action for r in results[1:]
                        if r.memory.action != action
                    ]
                    if alt_actions:
                        action = random.choice(alt_actions)
                        strategy = "learned_explore"
                        logger.info(
                            "DAR-3 epsilon-greedy: exploring %s instead of best %s",
                            action, best_action[0],
                        )

                # Parse action as routing decision
                routing = self._parse_routing_action(action)
                # Track last role for cache affinity (Phase 2.5)
                if routing:
                    self.retriever.update_last_role(routing[0])
                self._record_decision_meta(
                    strategy=strategy,
                    chosen_action=action,
                    results=results,
                    risk_gate=risk_gate,
                )
                return (routing, strategy)

        # Fall back to rule-based routing
        routing = self.rule_based.route(task_ir)
        # Track last role for cache affinity (Phase 2.5)
        if routing:
            self.retriever.update_last_role(routing[0])
        self._record_decision_meta(
            strategy="rules",
            chosen_action=",".join(routing),
            results=results,
            risk_gate=risk_gate,
        )
        return (routing, "rules")

    def route_with_mode(
        self,
        task_ir: Dict[str, Any],
        priors: Optional[Dict[str, float]] = None,
    ) -> Tuple[List[str], str, str]:
        """Route a task with mode selection (direct/react/repl).

        Extends route() to also return the recommended execution mode.
        Mode is parsed from action strings in format "role:mode" (colon-separated).
        Falls back to rule-based mode selection if no mode annotation found.

        Args:
            task_ir: TaskIR dictionary

        Returns:
            (routing_decision, strategy_used, mode) tuple
            mode is "direct", "react", or "repl"
        """
        # Classifier fast-path
        preference_override = isinstance(task_ir.get("routing_preferences"), dict)
        if self.routing_classifier is not None and not preference_override:
            features = self._build_classifier_features(task_ir)
            if features is not None:
                action, confidence = self.routing_classifier.predict_action(features)
                if action is not None and confidence >= self.classifier_confidence_threshold:
                    routing, mode = self._parse_routing_action_with_mode(action)
                    if routing:
                        self.retriever.update_last_role(routing[0])
                        self.last_decision_meta = {
                            "decision_source": "classifier",
                            "chosen_action": action,
                            "classifier_confidence": round(confidence, 4),
                            "classifier_threshold": self.classifier_confidence_threshold,
                        }
                        return (routing, "classifier", mode)

        # Try learned routing first
        results = self.retriever.retrieve_for_routing(task_ir)
        results = self._filter_routable_results(results)
        results = self._apply_priors(results, priors)

        # Blend GraphRouter signal if available
        if self.graph_router and self.graph_router.is_ready:
            self._blend_graph_router_scores(results, task_ir)

        route_key = str(task_ir.get("task_id", task_ir.get("objective", "")))
        risk_gate = self.retriever.evaluate_risk_gate(results, route_key=route_key)

        if risk_gate.get("enforced") and not risk_gate.get("passed"):
            routing = [self.retriever.config.risk_abstain_target_role]
            self._record_decision_meta(
                strategy="risk_abstain_escalate",
                chosen_action=",".join(routing),
                results=results,
                risk_gate=risk_gate,
            )
            return (routing, "risk_abstain_escalate", "direct")

        if self.retriever.should_use_learned(results):
            best_action = self.retriever.get_best_action(results)
            if best_action:
                action = best_action[0]
                confidence = best_action[1]
                routing, mode = self._parse_routing_action_with_mode(action)
                self._record_decision_meta(
                    strategy="learned",
                    chosen_action=action,
                    results=results,
                    risk_gate=risk_gate,
                )
                return (routing, "learned", mode)

        # Fall back to rule-based routing (with mode)
        routing, mode = self.rule_based.route_with_mode(task_ir)
        self._record_decision_meta(
            strategy="rules",
            chosen_action=",".join(routing),
            results=results,
            risk_gate=risk_gate,
        )
        return (routing, "rules", mode)

    def _parse_routing_action(self, action: str) -> List[str]:
        """Parse a stored action only when every target is a live serving role."""
        # Actions are stored as comma-separated role names
        # Also handle "role:mode" format by stripping mode suffix
        roles = []
        for r in action.split(","):
            r = r.strip()
            if ":" in r:
                r = r.split(":")[0]  # Strip mode suffix
            role = self._canonical_routable_role(r)
            if role is None:
                return []
            roles.append(role)
        return roles

    def _parse_routing_action_with_mode(
        self, action: str
    ) -> Tuple[List[str], str]:
        """Parse stored action string to routing list and mode.

        Action format: "role1:mode,role2" — colon separates role from mode.
        Only the first role's mode is used. If no mode annotation, defaults
        to "direct".

        Args:
            action: Action string from episodic memory.

        Returns:
            (routing_list, mode) tuple.
        """
        roles = []
        mode = "direct"  # Default mode
        for i, r in enumerate(action.split(",")):
            r = r.strip()
            if ":" in r:
                role_part, mode_part = r.split(":", 1)
                role = self._canonical_routable_role(role_part)
                if role is None:
                    return ([], "direct")
                roles.append(role)
                if i == 0:  # Mode from first role
                    mode = mode_part if mode_part in ("direct", "react", "repl") else "direct"
            else:
                role = self._canonical_routable_role(r)
                if role is None:
                    return ([], "direct")
                roles.append(role)
        return roles, mode
