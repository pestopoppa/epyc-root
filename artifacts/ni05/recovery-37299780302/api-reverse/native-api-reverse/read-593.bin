"""Tests for chat_pipeline/routing.py - Stage 1-3 and 5 pipeline stages."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.models import ChatRequest
from src.api.routes.chat_pipeline.routing import (
    _init_primitives,
    _plan_review_gate,
    _preprocess,
    _route_request,
    _server_urls_with_eval_batch_frontdoor,
)
from src.api.routes.chat_pipeline.routing_decision import (
    fence_nonserving_route,
    normalize_ingress_role,
    resolve_timeout,
    routing_meta,
)
from src.api.routes.chat_utils import RoutingResult
from src.config import reset_config
from src.proactive_delegation.types import PlanReviewResult
from src.roles import Role

_RETIRED_ARCHITECT_ROLE = "architect_coding"


class TestRouteRequest:
    """Tests for _route_request (Stage 1)."""

    @pytest.fixture(autouse=True)
    def _pin_skillbank_off(self):
        """Route these MagicMock-router tests through ``hybrid_router.route()``.

        ``select_initial_route`` takes the ``route_with_skills`` branch when
        ``features().skillbank`` is on; on a MagicMock router that returns a
        MagicMock which unpacks to zero values (``ValueError``). Stacks that
        enable skillbank via the runtime-flags file (not env) would therefore
        break these tests, which were written against the default (skillbank
        off). Pin it off deterministically while preserving every other real
        feature flag; restore on teardown.
        """
        import dataclasses

        from src.features import get_features, reset_features, set_features

        set_features(dataclasses.replace(get_features(), skillbank=False))
        try:
            yield
        finally:
            reset_features()

    def test_mock_mode_uses_frontdoor(self):
        """Mock mode routes to frontdoor by default."""
        request = ChatRequest(prompt="test", mock_mode=True, real_mode=False)
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None
        state.progress_logger = None

        result = _route_request(request, state)

        assert result.use_mock is True
        assert result.routing_strategy == "mock"
        assert str(Role.FRONTDOOR) in [str(r) for r in result.routing_decision]

    def test_mock_mode_with_explicit_role(self):
        """Mock mode uses explicit role when provided."""
        request = ChatRequest(
            prompt="test", mock_mode=True, real_mode=False, role="coder_escalation"
        )
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None
        state.progress_logger = None

        result = _route_request(request, state)

        assert result.routing_strategy == "mock"
        assert "coder_escalation" in [str(r) for r in result.routing_decision]

    def test_mock_mode_normalizes_legacy_explicit_role(self):
        """Mock-mode explicit roles should use the same ingress aliases as real mode."""
        request = ChatRequest(prompt="test", mock_mode=True, real_mode=False, role="coder")
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None
        state.progress_logger = None

        result = _route_request(request, state)

        assert result.routing_strategy == "mock"
        assert result.routing_decision == ["coder_escalation"]

    def test_force_role_overrides_routing(self):
        """force_role bypasses all routing logic."""
        request = ChatRequest(prompt="test", real_mode=True, force_role="architect_general")
        state = MagicMock()
        state.hybrid_router = MagicMock()
        state.failure_graph = None
        state.progress_logger = None

        result = _route_request(request, state)

        assert result.routing_strategy == "forced"
        assert result.routing_decision == ["architect_general"]
        # hybrid_router should NOT be called
        state.hybrid_router.route.assert_not_called()

    def test_long_prompt_bypasses_learned_router_for_ingest(self):
        # 2026-09-24: the guard routes by the frontdoor's per-request n_ctx
        # (65536 from the compiled stack priors in this suite), not 20k chars:
        # ~66,667 prompt tokens + the 4096 decode reserve cannot fit it.
        request = ChatRequest(prompt="x" * 200_000, real_mode=True)
        state = MagicMock()
        state.hybrid_router = MagicMock()
        state.failure_graph = None
        state.progress_logger = None

        result = _route_request(request, state)

        assert result.routing_strategy == "long_context_guard"
        assert result.routing_decision == ["ingest_long_context"]
        state.hybrid_router.route.assert_not_called()

    def test_explicit_role_bypasses_long_context_guard(self):
        request = ChatRequest(
            prompt="x" * 20_001,
            real_mode=True,
            role="worker_general",
        )
        state = MagicMock()
        state.hybrid_router = MagicMock()
        state.failure_graph = None
        state.progress_logger = None

        result = _route_request(request, state)

        assert result.routing_strategy == "explicit"
        assert result.routing_decision == ["worker_general"]
        state.hybrid_router.route.assert_not_called()

    def test_force_role_normalizes_legacy_ingress_alias(self):
        """force_role should not route legacy labels into stale config endpoints."""
        request = ChatRequest(prompt="test", real_mode=True, force_role="worker_fast")
        state = MagicMock()
        state.hybrid_router = MagicMock()
        state.failure_graph = None
        state.progress_logger = None

        result = _route_request(request, state)

        assert result.routing_strategy == "forced"
        assert result.routing_decision == ["worker_general"]
        state.hybrid_router.route.assert_not_called()

    def test_explicit_role_routes_directly(self):
        """Explicit role (non-frontdoor) routes directly."""
        request = ChatRequest(prompt="test", real_mode=True, role="coder_escalation")
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None
        state.progress_logger = None

        result = _route_request(request, state)

        assert result.routing_strategy == "explicit"
        assert result.routing_decision == ["coder_escalation"]

    def test_explicit_role_normalizes_coder_alias(self):
        """Explicit coder ingress should route to live coder_escalation."""
        request = ChatRequest(prompt="test", real_mode=True, role="coder")
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None
        state.progress_logger = None

        result = _route_request(request, state)

        assert result.routing_strategy == "explicit"
        assert result.routing_decision == ["coder_escalation"]

    def test_explicit_frontdoor_falls_through(self):
        """Explicit 'frontdoor' role falls through to classifier."""
        request = ChatRequest(prompt="test", real_mode=True, role="frontdoor")
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None
        state.progress_logger = None

        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            mock_classify.return_value = (str(Role.FRONTDOOR), "rules")
            result = _route_request(request, state)

        mock_classify.assert_called_once()
        assert result.routing_strategy == "rules"

    def test_hybrid_router_used_when_available(self):
        """HybridRouter is used for real_mode requests."""
        request = ChatRequest(prompt="test", real_mode=True)
        state = MagicMock()
        state.hybrid_router.route.return_value = (["coder_escalation"], "learned")
        state.failure_graph = None
        state.progress_logger = None

        result = _route_request(request, state)

        state.hybrid_router.route.assert_called_once()
        assert result.routing_strategy == "learned"
        assert result.routing_decision == ["coder_escalation"]

    def test_classifier_fallback_when_no_router(self):
        """Classifier used when no hybrid_router."""
        request = ChatRequest(prompt="test", real_mode=True)
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None
        state.progress_logger = None

        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            mock_classify.return_value = (str(Role.CODER_ESCALATION), "classified")
            result = _route_request(request, state)

        mock_classify.assert_called_once()
        assert result.routing_strategy == "classified"

    def test_failure_graph_veto_high_risk(self):
        """High-risk specialist reverted to frontdoor.

        RI-5: Veto threshold is modulated by factual-risk band.
        The "low" band sets threshold=0.7, so risk must exceed 0.7.
        """
        request = ChatRequest(prompt="test", real_mode=True)
        state = MagicMock()
        state.hybrid_router.route.return_value = (["coder_escalation"], "learned")
        state.failure_graph.get_failure_risk.return_value = 0.85  # > 0.7 (low-risk threshold)
        state.progress_logger = None

        result = _route_request(request, state)

        assert result.routing_strategy == "failure_vetoed"
        assert str(Role.FRONTDOOR) in result.routing_decision

    def test_failure_graph_allows_low_risk(self):
        """Low-risk specialist not reverted."""
        request = ChatRequest(prompt="test", real_mode=True)
        state = MagicMock()
        state.hybrid_router.route.return_value = (["coder_escalation"], "learned")
        state.failure_graph.get_failure_risk.return_value = 0.2  # < 0.5
        state.progress_logger = None

        result = _route_request(request, state)

        assert result.routing_strategy == "learned"
        assert result.routing_decision == ["coder_escalation"]

    def test_failure_graph_skips_mock_mode(self):
        """Failure veto skipped for mock mode."""
        request = ChatRequest(
            prompt="test", mock_mode=True, real_mode=False, role="coder_escalation"
        )
        state = MagicMock()
        state.failure_graph.get_failure_risk.return_value = 0.9
        state.progress_logger = None

        _route_request(request, state)

        # Failure graph should NOT be checked for mock mode
        state.failure_graph.get_failure_risk.assert_not_called()

    def test_failure_graph_skips_forced_role(self):
        """Failure veto skipped for forced role."""
        request = ChatRequest(prompt="test", real_mode=True, force_role="coder_escalation")
        state = MagicMock()
        state.failure_graph.get_failure_risk.return_value = 0.9
        state.progress_logger = None

        _route_request(request, state)

        # Failure graph should NOT be checked for forced role
        state.failure_graph.get_failure_risk.assert_not_called()

    def test_failure_graph_exception_handled(self):
        """Failure graph exception doesn't break routing."""
        request = ChatRequest(prompt="test", real_mode=True)
        state = MagicMock()
        state.hybrid_router.route.return_value = (["coder_escalation"], "learned")
        state.failure_graph.get_failure_risk.side_effect = RuntimeError("DB error")
        state.progress_logger = None

        result = _route_request(request, state)

        # Should continue with original routing despite error
        assert result.routing_strategy == "learned"
        assert result.routing_decision == ["coder_escalation"]

    # ── Modality fence (bidirectional) ──────────────────────────────────

    _VISION_ONLY = frozenset({"worker_vision", "vision_escalation"})

    def test_text_request_fenced_off_vision_only_role(self):
        """A TEXT request the learned router sends to a vision-only role is
        fenced to the frontdoor — a VL server rejects text /completion (400)."""
        request = ChatRequest(prompt="summarize this long document", real_mode=True)
        state = MagicMock()
        state.hybrid_router.route.return_value = (["worker_vision"], "learned")
        state.failure_graph = None
        state.progress_logger = None

        with patch(
            "src.api.routes.chat_pipeline.routing_decision._vision_only_roles",
            return_value=self._VISION_ONLY,
        ):
            result = _route_request(request, state)

        assert "worker_vision" not in [str(r) for r in result.routing_decision]
        assert str(Role.FRONTDOOR) in [str(r) for r in result.routing_decision]
        assert result.routing_strategy == "learned:vision_fenced"

    def test_text_request_non_vision_route_unchanged(self):
        """The fence only touches vision-only roles — normal routes pass through."""
        request = ChatRequest(prompt="write a function", real_mode=True)
        state = MagicMock()
        state.hybrid_router.route.return_value = (["coder_escalation"], "learned")
        state.failure_graph = None
        state.progress_logger = None

        with patch(
            "src.api.routes.chat_pipeline.routing_decision._vision_only_roles",
            return_value=self._VISION_ONLY,
        ):
            result = _route_request(request, state)

        assert result.routing_decision == ["coder_escalation"]
        assert result.routing_strategy == "learned"

    def test_forced_vision_role_bypasses_fence(self):
        """A forced vision role is the caller's responsibility — never fenced."""
        request = ChatRequest(prompt="describe", real_mode=True, force_role="worker_vision")
        state = MagicMock()
        state.hybrid_router = MagicMock()
        state.failure_graph = None
        state.progress_logger = None

        with patch(
            "src.api.routes.chat_pipeline.routing_decision._vision_only_roles",
            return_value=self._VISION_ONLY,
        ):
            result = _route_request(request, state)

        assert result.routing_decision == ["worker_vision"]
        assert result.routing_strategy == "forced"
        state.hybrid_router.route.assert_not_called()

    def test_image_request_routes_to_vision_role(self):
        """An image-carrying request is REQUIRED to route to the vision role."""
        request = ChatRequest(
            prompt="what is in this chart?", real_mode=True, image_path="/some/chart.png"
        )
        state = MagicMock()
        state.hybrid_router = MagicMock()
        state.failure_graph = None
        state.progress_logger = None

        result = _route_request(request, state)

        assert result.routing_decision == ["worker_vision"]
        assert result.routing_strategy == "vision_input"
        state.hybrid_router.route.assert_not_called()

    def test_image_request_exempt_from_failure_veto(self):
        """An image request on a vision-only role is EXEMPT from the failure veto —
        reverting to a text frontdoor would make the VL model answer blind."""
        request = ChatRequest(
            prompt="what is in this chart?", real_mode=True, image_path="/some/chart.png"
        )
        state = MagicMock()
        state.hybrid_router = MagicMock()
        state.failure_graph.get_failure_risk.return_value = 0.99  # would normally veto
        state.progress_logger = None

        with patch(
            "src.api.routes.chat_pipeline.routing_decision._vision_only_roles",
            return_value=self._VISION_ONLY,
        ):
            result = _route_request(request, state)

        assert result.routing_decision == ["worker_vision"]
        assert result.routing_strategy == "vision_input"
        state.failure_graph.get_failure_risk.assert_not_called()

    def test_progress_logger_called(self):
        """Progress logger logs task start."""
        request = ChatRequest(prompt="test", real_mode=True)
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None

        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            mock_classify.return_value = (str(Role.FRONTDOOR), "rules")
            result = _route_request(request, state)

        state.progress_logger.log_task_started.assert_called_once()
        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert call_kwargs["task_id"] == result.task_id
        assert "routing_decision" in call_kwargs

    def test_xmas_off_mode_omits_routing_metadata(self, monkeypatch):
        """Explicitly disabled X-MAS telemetry should not alter progress metadata."""
        from src.classifiers.config_loader import reset_classifier_config

        monkeypatch.setenv("ORCHESTRATOR_XMAS_ROUTING_MODE", "off")
        monkeypatch.delenv("ORCHESTRATOR_XMAS_WINNER_TABLE_PATH", raising=False)
        reset_classifier_config()
        request = ChatRequest(prompt="Refactor this Python function.", real_mode=True)
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None

        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            mock_classify.return_value = (str(Role.CODER_ESCALATION), "rules")
            _route_request(request, state)

        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert "xmas" not in call_kwargs["routing_meta"]

    def test_xmas_shadow_metadata_is_logged_without_route_change(self):
        """X-MAS shadow telemetry logs suggestions without changing routing."""
        request = ChatRequest(prompt="Refactor this Python function.", real_mode=True)
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None

        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            mock_classify.return_value = (str(Role.FRONTDOOR), "rules")
            with patch("src.classifiers.xmas_routing.build_xmas_routing_metadata") as mock_xmas:
                mock_xmas.return_value = {
                    "mode": "shadow",
                    "cell": "code:refine",
                    "suggested_role": "coder_escalation",
                    "applied": False,
                }
                result = _route_request(request, state)

        assert result.routing_decision == [str(Role.FRONTDOOR)]
        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert call_kwargs["routing_meta"]["xmas"] == {
            "mode": "shadow",
            "cell": "code:refine",
            "suggested_role": "coder_escalation",
            "applied": False,
        }

    def test_xmas_shadow_failure_does_not_break_routing(self):
        """X-MAS telemetry is advisory; classifier failures are ignored."""
        request = ChatRequest(prompt="Refactor this Python function.", real_mode=True)
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None

        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            mock_classify.return_value = (str(Role.FRONTDOOR), "rules")
            with patch(
                "src.classifiers.xmas_routing.build_xmas_routing_metadata",
                side_effect=RuntimeError("boom"),
            ):
                result = _route_request(request, state)

        assert result.routing_decision == [str(Role.FRONTDOOR)]
        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert "xmas" not in call_kwargs["routing_meta"]

    def test_xmas_enforce_rewrites_loaded_confident_suggestion(self):
        """X-MAS enforce can rewrite the initial route when table/confidence gates pass."""
        request = ChatRequest(prompt="Refactor this Python function.", real_mode=True)
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None

        xmas_meta = {
            "mode": "enforce",
            "cell": "code:refine",
            "is_confident": True,
            "winner_table_status": "loaded",
            "suggested_role": "coder_escalation",
            "candidate_metrics": {
                "frontdoor": {"correct": 2, "accuracy": 0.4, "wall_mean_s": 9.0},
                "coder_escalation": {"correct": 5, "accuracy": 1.0, "wall_mean_s": 8.0},
            },
            "applied": False,
        }
        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            mock_classify.return_value = (str(Role.FRONTDOOR), "rules")
            with patch(
                "src.classifiers.xmas_routing.build_xmas_routing_metadata",
                return_value=xmas_meta,
            ):
                result = _route_request(request, state)

        assert result.routing_decision == ["coder_escalation"]
        assert result.routing_strategy == "xmas_enforce:rules"
        assert result.xmas_meta is xmas_meta
        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert call_kwargs["routing_meta"]["xmas"]["applied"] is True
        assert call_kwargs["routing_meta"]["xmas"]["apply_reason"] == "evidence_quality_lift"
        assert call_kwargs["routing_meta"]["xmas"]["previous_role"] == "frontdoor"
        assert call_kwargs["routing_meta"]["xmas"]["incumbent_role"] == "frontdoor"

    def test_xmas_enforce_keeps_incumbent_when_not_evaluated(self):
        """X-MAS enforce must not replace an incumbent absent from cell evidence."""
        request = ChatRequest(prompt="Refactor this Python function.", real_mode=True)
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None

        xmas_meta = {
            "mode": "enforce",
            "cell": "code:refine",
            "is_confident": True,
            "winner_table_status": "loaded",
            "suggested_role": "worker_general",
            "candidate_metrics": {
                "frontdoor": {"correct": 3, "accuracy": 0.6, "wall_mean_s": 10.0},
                "worker_general": {"correct": 5, "accuracy": 1.0, "wall_mean_s": 8.0},
            },
            "applied": False,
        }
        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            mock_classify.return_value = (str(Role.CODER_ESCALATION), "learned")
            with patch(
                "src.classifiers.xmas_routing.build_xmas_routing_metadata",
                return_value=xmas_meta,
            ):
                result = _route_request(request, state)

        assert result.routing_decision == [str(Role.CODER_ESCALATION)]
        assert result.routing_strategy == "learned"
        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert call_kwargs["routing_meta"]["xmas"]["applied"] is False
        assert call_kwargs["routing_meta"]["xmas"]["apply_reason"] == "incumbent_role_not_evaluated"
        assert call_kwargs["routing_meta"]["xmas"]["incumbent_role"] == "coder_escalation"

    def test_xmas_enforce_keeps_incumbent_without_evidence_lift(self):
        """Equal-quality table evidence is not enough unless X-MAS is faster."""
        request = ChatRequest(prompt="Solve this arithmetic problem.", real_mode=True)
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None

        xmas_meta = {
            "mode": "enforce",
            "cell": "math:solve",
            "is_confident": True,
            "winner_table_status": "loaded",
            "suggested_role": "worker_general",
            "candidate_metrics": {
                "frontdoor": {"correct": 5, "accuracy": 1.0, "wall_mean_s": 5.0},
                "worker_general": {"correct": 5, "accuracy": 1.0, "wall_mean_s": 5.1},
            },
            "applied": False,
        }
        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            mock_classify.return_value = (str(Role.FRONTDOOR), "rules")
            with patch(
                "src.classifiers.xmas_routing.build_xmas_routing_metadata",
                return_value=xmas_meta,
            ):
                result = _route_request(request, state)

        assert result.routing_decision == [str(Role.FRONTDOOR)]
        assert result.routing_strategy == "rules"
        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert call_kwargs["routing_meta"]["xmas"]["applied"] is False
        assert (
            call_kwargs["routing_meta"]["xmas"]["apply_reason"] == "evidence_no_lift_over_incumbent"
        )

    def test_xmas_enforce_low_confidence_does_not_rewrite(self):
        """X-MAS enforce remains advisory for low-confidence cells."""
        request = ChatRequest(prompt="hello there", real_mode=True)
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None

        xmas_meta = {
            "mode": "enforce",
            "cell": "knowledge:solve",
            "is_confident": False,
            "winner_table_status": "loaded",
            "suggested_role": "coder_escalation",
            "applied": False,
        }
        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            mock_classify.return_value = (str(Role.FRONTDOOR), "rules")
            with patch(
                "src.classifiers.xmas_routing.build_xmas_routing_metadata",
                return_value=xmas_meta,
            ):
                result = _route_request(request, state)

        assert result.routing_decision == [str(Role.FRONTDOOR)]
        assert result.routing_strategy == "rules"
        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert call_kwargs["routing_meta"]["xmas"]["applied"] is False
        assert call_kwargs["routing_meta"]["xmas"]["apply_reason"] == "low_confidence"

    def test_xmas_enforce_missing_table_does_not_rewrite(self):
        """X-MAS enforce fails open when a complete winner table is not loaded."""
        request = ChatRequest(prompt="Refactor this Python function.", real_mode=True)
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph = None

        xmas_meta = {
            "mode": "enforce",
            "cell": "code:refine",
            "is_confident": True,
            "winner_table_status": "missing",
            "suggested_role": None,
            "applied": False,
        }
        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            mock_classify.return_value = (str(Role.FRONTDOOR), "rules")
            with patch(
                "src.classifiers.xmas_routing.build_xmas_routing_metadata",
                return_value=xmas_meta,
            ):
                result = _route_request(request, state)

        assert result.routing_decision == [str(Role.FRONTDOOR)]
        assert result.routing_strategy == "rules"
        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert call_kwargs["routing_meta"]["xmas"]["apply_reason"] == "winner_table_not_loaded"

    def test_xmas_enforce_respects_forced_role(self):
        """Explicit force_role remains stronger than X-MAS enforce metadata."""
        request = ChatRequest(
            prompt="Refactor this Python function.",
            real_mode=True,
            force_role="architect_general",
        )
        state = MagicMock()
        state.failure_graph = None

        xmas_meta = {
            "mode": "enforce",
            "cell": "code:refine",
            "is_confident": True,
            "winner_table_status": "loaded",
            "suggested_role": "coder_escalation",
            "candidate_metrics": {
                "frontdoor": {"correct": 2, "accuracy": 0.4, "wall_mean_s": 9.0},
                "coder_escalation": {"correct": 5, "accuracy": 1.0, "wall_mean_s": 8.0},
            },
            "applied": False,
        }
        with patch(
            "src.classifiers.xmas_routing.build_xmas_routing_metadata",
            return_value=xmas_meta,
        ):
            result = _route_request(request, state)

        assert result.routing_decision == ["architect_general"]
        assert result.routing_strategy == "forced"
        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert call_kwargs["routing_meta"]["xmas"]["apply_reason"] == "forced_role"

    def test_xmas_enforce_still_yields_to_failure_veto(self):
        """Failure-veto remains after X-MAS override in the routing pipeline."""
        request = ChatRequest(prompt="Refactor this Python function.", real_mode=True)
        state = MagicMock()
        state.hybrid_router = None
        state.failure_graph.get_failure_risk.return_value = 0.95

        xmas_meta = {
            "mode": "enforce",
            "cell": "code:refine",
            "is_confident": True,
            "winner_table_status": "loaded",
            "suggested_role": "coder_escalation",
            "candidate_metrics": {
                "frontdoor": {"correct": 2, "accuracy": 0.4, "wall_mean_s": 9.0},
                "coder_escalation": {"correct": 5, "accuracy": 1.0, "wall_mean_s": 8.0},
            },
            "applied": False,
        }
        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            mock_classify.return_value = (str(Role.FRONTDOOR), "rules")
            with patch(
                "src.classifiers.xmas_routing.build_xmas_routing_metadata",
                return_value=xmas_meta,
            ):
                result = _route_request(request, state)

        assert result.routing_decision == [str(Role.FRONTDOOR)]
        assert result.routing_strategy == "failure_vetoed"
        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert call_kwargs["routing_meta"]["xmas"]["applied"] is True
        assert call_kwargs["routing_meta"]["xmas"]["apply_reason"] == "evidence_quality_lift"

    def test_task_id_generated(self):
        """Task ID is generated with chat prefix."""
        request = ChatRequest(prompt="test", mock_mode=True)
        state = MagicMock()
        state.progress_logger = None
        state.failure_graph = None

        result = _route_request(request, state)

        assert result.task_id.startswith("chat-")
        assert len(result.task_id) == 13  # "chat-" + 8 hex chars

    def test_role_specific_timeout(self):
        """Role-specific timeout is computed."""
        request = ChatRequest(prompt="test", real_mode=True)
        state = MagicMock()
        state.hybrid_router.route.return_value = (["architect_general"], "learned")
        state.failure_graph = None
        state.progress_logger = None

        result = _route_request(request, state)

        # architect_general has longer timeout (300s in ROLE_TIMEOUTS)
        assert result.timeout_s >= 120  # At least default

    def test_resolve_timeout_uses_current_config_after_reset(self):
        """Live routing timeout lookup must not freeze an import-time dict."""
        request = ChatRequest(prompt="test")
        with patch.dict(os.environ, {"ORCHESTRATOR_TIMEOUTS_FRONTDOOR": "77"}):
            reset_config()
            try:
                assert resolve_timeout(request, [str(Role.FRONTDOOR)]) == 77
            finally:
                reset_config()

    def test_resolve_timeout_eval_batch_extends_beyond_sla(self):
        """2026-07-21 EV-11c: eval_batch may EXTEND its budget past the role SLA."""
        with patch.dict(os.environ, {"ORCHESTRATOR_TIMEOUTS_FRONTDOOR": "60"}):
            reset_config()
            try:
                extend = ChatRequest(
                    prompt="hard MATH tail", workload_class="eval_batch", timeout_s=300
                )
                assert resolve_timeout(extend, [str(Role.FRONTDOOR)]) == 300
                # Interactive traffic with the same long timeout_s still clamps DOWN.
                interactive = ChatRequest(prompt="q", workload_class="interactive", timeout_s=300)
                assert resolve_timeout(interactive, [str(Role.FRONTDOOR)]) == 60
                # Unset workload_class == legacy DOWN-only clamp.
                legacy = ChatRequest(prompt="q", timeout_s=300)
                assert resolve_timeout(legacy, [str(Role.FRONTDOOR)]) == 60
            finally:
                reset_config()

    def test_image_path_bypasses_learned_text_routing(self):
        """Unforced image requests route to vision before the learned router."""
        request = ChatRequest(prompt="describe", real_mode=True, image_path="/path/to/img.png")
        state = MagicMock()
        state.hybrid_router.route.return_value = ([str(Role.FRONTDOOR)], "learned")
        state.failure_graph = None
        state.progress_logger = None

        with patch("src.api.routes.chat_pipeline.routing._classify_and_route") as mock_classify:
            result = _route_request(request, state)

        state.hybrid_router.route.assert_not_called()
        mock_classify.assert_not_called()
        assert result.routing_strategy == "vision_input"
        assert result.routing_decision == ["worker_vision"]

    def test_memrl_initialized_for_real_mode(self):
        """MemRL initialized early for real_mode requests."""
        request = ChatRequest(prompt="test", real_mode=True)
        state = MagicMock()
        state.hybrid_router.route.return_value = ([str(Role.FRONTDOOR)], "learned")
        state.failure_graph = None
        state.progress_logger = None

        with patch("src.api.routes.chat_pipeline.routing.ensure_memrl_initialized") as mock_init:
            _route_request(request, state)

        mock_init.assert_called_once_with(state)


def test_normalize_ingress_role_legacy_aliases() -> None:
    assert normalize_ingress_role(_RETIRED_ARCHITECT_ROLE) == "architect_general"
    assert normalize_ingress_role("coder") == "coder_escalation"
    assert normalize_ingress_role("worker_coder") == "worker_general"
    assert normalize_ingress_role("worker_code") == "worker_general"
    assert normalize_ingress_role("worker_fast") == "worker_general"
    assert normalize_ingress_role("architect_general") == "architect_general"


def test_normalize_ingress_role_returns_canonical_worker_general_enum() -> None:
    assert normalize_ingress_role("worker_coder") == Role.WORKER_GENERAL
    assert normalize_ingress_role("worker_code") == Role.WORKER_GENERAL


def test_nonserving_route_is_fenced_to_frontdoor(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.registry.stack_priors.live_stack_role_ids",
        lambda: ["frontdoor", "worker_general"],
    )

    route, strategy = fence_nonserving_route(["plan_review"], "learned")

    assert route == ["frontdoor"]
    assert strategy == "learned:nonserving_fenced"


def test_serving_route_is_canonicalized(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.registry.stack_priors.live_stack_role_ids",
        lambda: ["frontdoor", "worker_general"],
    )

    route, strategy = fence_nonserving_route(["worker_fast"], "learned")

    assert route == ["worker_general"]
    assert strategy == "learned"


def test_missing_live_serving_contract_fails_closed_to_frontdoor(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.registry.stack_priors.live_stack_role_ids",
        lambda: [],
    )

    route, strategy = fence_nonserving_route(["worker_general"], "learned")

    assert route == ["frontdoor"]
    assert strategy == "learned:nonserving_fenced"


def test_route_request_fences_nonserving_learned_action(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.registry.stack_priors.live_stack_role_ids",
        lambda: ["frontdoor", "worker_general"],
    )
    request = ChatRequest(prompt="test", real_mode=True)
    state = MagicMock()
    state.hybrid_router.route.return_value = (["plan_review"], "learned")
    state.failure_graph = None
    state.progress_logger = None

    result = _route_request(request, state)

    assert result.routing_decision == ["frontdoor"]
    assert result.routing_strategy == "learned:nonserving_fenced"


class TestPreprocess:
    """Tests for _preprocess (Stage 2)."""

    def test_formalization_disabled_by_feature(self):
        """Formalization skipped when feature disabled."""
        request = ChatRequest(prompt="test", real_mode=True)
        routing = RoutingResult(
            task_id="test-123",
            task_ir={},
            use_mock=False,
            routing_decision=[str(Role.FRONTDOOR)],
            routing_strategy="rules",
            timeout_s=120,
        )
        state = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.input_formalizer = False
            _preprocess(request, state, routing)

        # No formalization applied (attribute should not be set)
        assert not getattr(routing, "formalization_applied", False)

    def test_formalization_skipped_for_mock_mode(self):
        """Formalization skipped for mock mode."""
        request = ChatRequest(prompt="test", real_mode=False)
        routing = RoutingResult(
            task_id="test-123",
            task_ir={},
            use_mock=True,
            routing_decision=[str(Role.FRONTDOOR)],
            routing_strategy="mock",
            timeout_s=120,
        )
        state = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.input_formalizer = True
            _preprocess(request, state, routing)

        # Should not reach formalization check
        assert not getattr(routing, "formalization_applied", False)

    def test_formalization_applied_when_needed(self):
        """Formalization applied when should_formalize returns True."""
        request = ChatRequest(prompt="solve x^2 + 2x + 1 = 0", real_mode=True, context="")
        routing = RoutingResult(
            task_id="test-123",
            task_ir={},
            use_mock=False,
            routing_decision=[str(Role.FRONTDOOR)],
            routing_strategy="rules",
            timeout_s=120,
        )
        state = MagicMock()
        state.registry = MagicMock()

        mock_fml_result = MagicMock()
        mock_fml_result.success = True
        mock_fml_result.ir_json = '{"type": "polynomial"}'
        mock_fml_result.elapsed_seconds = 0.5
        mock_fml_result.model_role = "math_formalizer"

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.input_formalizer = True
            with patch("src.formalizer.should_formalize_input") as mock_should:
                mock_should.return_value = (True, "polynomial")
                with patch("src.formalizer.formalize_prompt") as mock_fml:
                    mock_fml.return_value = mock_fml_result
                    with patch("src.formalizer.inject_formalization") as mock_inject:
                        mock_inject.return_value = "formalized context"
                        _preprocess(request, state, routing)

        assert routing.formalization_applied is True
        mock_fml.assert_called_once()
        mock_inject.assert_called_once()

    def test_formalization_skipped_when_not_needed(self):
        """Formalization skipped when should_formalize returns False."""
        request = ChatRequest(prompt="hello", real_mode=True)
        routing = RoutingResult(
            task_id="test-123",
            task_ir={},
            use_mock=False,
            routing_decision=[str(Role.FRONTDOOR)],
            routing_strategy="rules",
            timeout_s=120,
        )
        state = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.input_formalizer = True
            with patch("src.formalizer.should_formalize_input") as mock_should:
                mock_should.return_value = (False, None)
                _preprocess(request, state, routing)

        # formalization_applied should not be set
        assert not getattr(routing, "formalization_applied", False)


class TestInitPrimitives:
    """Tests for _init_primitives (Stage 3)."""

    def test_real_mode_creates_primitives(self):
        """Real mode creates LLMPrimitives."""
        request = ChatRequest(prompt="test", real_mode=True)
        state = MagicMock()
        state._real_primitives = None
        state.registry = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.LLMPrimitives") as mock_primitives_cls:
            mock_primitives = MagicMock()
            mock_primitives._backends = {"port8080": MagicMock()}
            mock_primitives_cls.return_value = mock_primitives

            result = _init_primitives(request, state)

        assert result is mock_primitives
        mock_primitives_cls.assert_called_once()

    def test_real_mode_reuses_cached_primitives(self):
        """Real mode reuses cached _real_primitives."""
        request = ChatRequest(prompt="test", real_mode=True)
        cached_primitives = MagicMock()
        cached_primitives._backends = {"port8080": MagicMock()}
        state = MagicMock()
        state._real_primitives = cached_primitives
        state.registry = MagicMock()

        result = _init_primitives(request, state)

        assert result is cached_primitives
        cached_primitives.reset_counters.assert_called_once()

    def test_real_mode_no_cache_with_custom_urls(self):
        """Custom server_urls bypass cache."""
        request = ChatRequest(
            prompt="test",
            real_mode=True,
            server_urls={"custom": "http://localhost:9000"},
        )
        cached_primitives = MagicMock()
        state = MagicMock()
        state._real_primitives = cached_primitives
        state.registry = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.LLMPrimitives") as mock_primitives_cls:
            mock_primitives = MagicMock()
            mock_primitives._backends = {"custom": MagicMock()}
            mock_primitives_cls.return_value = mock_primitives

            _init_primitives(request, state)

        # Should create NEW primitives, not reuse cache
        mock_primitives_cls.assert_called_once()
        # Cache should NOT be updated (custom URLs)
        assert state._real_primitives is cached_primitives

    def test_eval_batch_serving_rewrites_frontdoor_urls_when_enabled(self, monkeypatch):
        request = ChatRequest(prompt="test", real_mode=True, workload_class="eval_batch")
        monkeypatch.setenv("ORCHESTRATOR_EVAL_BATCH_FRONTDOOR_URL", "http://localhost:18070")
        monkeypatch.setattr(
            "src.api.routes.chat_pipeline.routing.features",
            lambda: SimpleNamespace(eval_batch_serving=True),
        )
        monkeypatch.setattr(
            "src.api.routes.chat_pipeline.routing._eval_batch_frontdoor_healthy",
            lambda _url: True,
        )

        urls, changed = _server_urls_with_eval_batch_frontdoor(
            request,
            {
                "frontdoor": "full:http://localhost:8070,http://localhost:8080",
                "coder_escalation": "http://localhost:8070",
                "worker_general": "http://localhost:8072",
            },
        )

        assert changed is True
        assert urls["frontdoor"] == "http://localhost:18070"
        assert urls["coder_escalation"] == "http://localhost:18070"
        assert urls["worker_general"] == "http://localhost:8072"

    def test_eval_batch_serving_does_not_poison_cached_primitives(self, monkeypatch):
        request = ChatRequest(prompt="test", real_mode=True, workload_class="eval_batch")
        cached_primitives = MagicMock()
        state = MagicMock()
        state._real_primitives = cached_primitives
        state.registry = MagicMock()
        monkeypatch.setenv("ORCHESTRATOR_EVAL_BATCH_FRONTDOOR_URL", "http://localhost:18070")
        monkeypatch.setattr(
            "src.api.routes.chat_pipeline.routing.features",
            lambda: SimpleNamespace(eval_batch_serving=True),
        )
        monkeypatch.setattr(
            "src.api.routes.chat_pipeline.routing._eval_batch_frontdoor_healthy",
            lambda _url: True,
        )

        with patch("src.api.routes.chat_pipeline.routing.LLMPrimitives") as mock_primitives_cls:
            mock_primitives = MagicMock()
            mock_primitives._backends = {"frontdoor": MagicMock()}
            mock_primitives_cls.return_value = mock_primitives

            _init_primitives(request, state)

        mock_primitives_cls.assert_called_once()
        kwargs = mock_primitives_cls.call_args.kwargs
        assert kwargs["server_urls"]["frontdoor"] == "http://localhost:18070"
        assert state._real_primitives is cached_primitives

    def test_eval_batch_serving_keeps_long_prompt_on_primary_split_fleet(
        self, monkeypatch
    ):
        request = ChatRequest(
            prompt="x" * 60_000,
            real_mode=True,
            workload_class="eval_batch",
            max_tokens=4096,
        )
        monkeypatch.setattr(
            "src.api.routes.chat_pipeline.routing.features",
            lambda: SimpleNamespace(eval_batch_serving=True),
        )

        original = {
            "frontdoor": "full:http://localhost:8070,http://localhost:8080",
            "worker_general": "http://localhost:8072",
        }
        urls, changed = _server_urls_with_eval_batch_frontdoor(request, original)

        assert changed is False
        assert urls == original

    def test_real_mode_raises_on_init_failure(self):
        """Real mode raises HTTPException on init failure."""
        request = ChatRequest(prompt="test", real_mode=True)
        state = MagicMock()
        state._real_primitives = None
        state.registry = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.LLMPrimitives") as mock_primitives_cls:
            mock_primitives_cls.side_effect = RuntimeError("Connection failed")

            with pytest.raises(HTTPException) as exc_info:
                _init_primitives(request, state)

        assert exc_info.value.status_code == 503
        assert "Failed to initialize" in exc_info.value.detail

    def test_real_mode_raises_on_no_backends(self):
        """Real mode raises HTTPException when no backends available."""
        request = ChatRequest(prompt="test", real_mode=True)
        state = MagicMock()
        state._real_primitives = None
        state.registry = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.LLMPrimitives") as mock_primitives_cls:
            mock_primitives = MagicMock()
            mock_primitives._backends = {}  # No backends
            mock_primitives_cls.return_value = mock_primitives

            with pytest.raises(HTTPException) as exc_info:
                _init_primitives(request, state)

        assert exc_info.value.status_code == 503
        assert "No backends available" in exc_info.value.detail

    def test_non_real_mode_creates_primitives(self):
        """Non-real mode creates primitives without server URLs."""
        request = ChatRequest(prompt="test", real_mode=False)
        state = MagicMock()
        state.registry = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.LLMPrimitives") as mock_primitives_cls:
            mock_primitives = MagicMock()
            mock_primitives.model_server = MagicMock()
            mock_primitives_cls.return_value = mock_primitives

            result = _init_primitives(request, state)

        assert result is mock_primitives

    def test_non_real_mode_raises_on_no_model_server(self):
        """Non-real mode raises HTTPException when no model server."""
        request = ChatRequest(prompt="test", real_mode=False)
        state = MagicMock()
        state.registry = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.LLMPrimitives") as mock_primitives_cls:
            mock_primitives = MagicMock()
            mock_primitives.model_server = None  # No model server
            mock_primitives_cls.return_value = mock_primitives

            with pytest.raises(HTTPException) as exc_info:
                _init_primitives(request, state)

        assert exc_info.value.status_code == 503
        assert "no model server" in exc_info.value.detail

    def test_cache_prompt_propagated(self):
        """cache_prompt flag propagated to primitives."""
        request = ChatRequest(prompt="test", real_mode=True, cache_prompt=True)
        state = MagicMock()
        state._real_primitives = None
        state.registry = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.LLMPrimitives") as mock_primitives_cls:
            mock_primitives = MagicMock()
            mock_primitives._backends = {"port8080": MagicMock()}
            mock_primitives_cls.return_value = mock_primitives

            _init_primitives(request, state)

        assert mock_primitives.cache_prompt is True


class TestPlanReviewGate:
    """Tests for _plan_review_gate (Stage 5)."""

    def test_plan_review_skipped_when_disabled(self):
        """Plan review skipped when feature disabled."""
        request = ChatRequest(prompt="test", real_mode=True)
        routing = MagicMock()
        primitives = MagicMock()
        state = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.plan_review = False
            result = _plan_review_gate(request, routing, primitives, state)

        assert result is None

    def test_plan_review_skipped_for_non_real_mode(self):
        """Plan review skipped for non-real mode."""
        request = ChatRequest(prompt="test", real_mode=False)
        routing = MagicMock()
        primitives = MagicMock()
        state = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.plan_review = True
            result = _plan_review_gate(request, routing, primitives, state)

        assert result is None

    def test_plan_review_skipped_when_not_needed(self):
        """Plan review skipped when _needs_plan_review returns False."""
        request = ChatRequest(prompt="test", real_mode=True)
        routing = MagicMock()
        primitives = MagicMock()
        state = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.plan_review = True
            with patch("src.api.routes.chat_pipeline.routing._needs_plan_review") as mock_needs:
                mock_needs.return_value = False
                result = _plan_review_gate(request, routing, primitives, state)

        assert result is None

    def test_plan_review_uses_persisted_factual_risk_mode_without_resampling(self):
        request = ChatRequest(prompt="Verify this claim.", real_mode=True)
        routing = RoutingResult(
            task_id="test-123",
            task_ir={"task_type": "qa"},
            use_mock=False,
            routing_decision=["worker_general"],
            factual_risk_band="high",
            factual_risk_mode="enforce",
        )
        primitives = MagicMock()
        state = MagicMock()
        mock_review_result = MagicMock()
        mock_review_result.decision = "ok"

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.plan_review = True
            with patch("src.api.routes.chat_pipeline.routing._needs_plan_review") as mock_needs:
                mock_needs.return_value = False
                with patch(
                    "src.api.routes.chat_pipeline.routing._architect_plan_review"
                ) as mock_review:
                    mock_review.return_value = mock_review_result
                    with patch("src.api.routes.chat_pipeline.routing._store_plan_review_episode"):
                        with patch("src.classifiers.factual_risk.get_mode") as mock_get_mode:
                            result = _plan_review_gate(request, routing, primitives, state)

        assert result is mock_review_result
        mock_review.assert_called_once()
        mock_get_mode.assert_not_called()

    def test_plan_review_runs_when_needed(self):
        """Plan review runs when all conditions met."""
        request = ChatRequest(prompt="test", real_mode=True)
        routing = MagicMock()
        routing.task_ir = {"task_type": "code"}
        routing.routing_decision = ["coder_escalation"]
        routing.task_id = "test-123"
        primitives = MagicMock()
        state = MagicMock()

        mock_review_result = MagicMock()
        mock_review_result.decision = "ok"

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.plan_review = True
            with patch("src.api.routes.chat_pipeline.routing._needs_plan_review") as mock_needs:
                mock_needs.return_value = True
                with patch(
                    "src.api.routes.chat_pipeline.routing._architect_plan_review"
                ) as mock_review:
                    mock_review.return_value = mock_review_result
                    with patch("src.api.routes.chat_pipeline.routing._store_plan_review_episode"):
                        result = _plan_review_gate(request, routing, primitives, state)

        assert result is mock_review_result
        mock_review.assert_called_once()

    def test_plan_review_applies_changes(self):
        """Plan review applies routing changes when decision != ok."""
        request = ChatRequest(prompt="test", real_mode=True)
        routing = MagicMock()
        routing.task_ir = {"task_type": "code"}
        routing.routing_decision = ["coder_escalation"]
        routing.task_id = "test-123"
        primitives = MagicMock()
        state = MagicMock()

        mock_review_result = MagicMock()
        mock_review_result.decision = "escalate"

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.plan_review = True
            with patch("src.api.routes.chat_pipeline.routing._needs_plan_review") as mock_needs:
                mock_needs.return_value = True
                with patch(
                    "src.api.routes.chat_pipeline.routing._architect_plan_review"
                ) as mock_review:
                    mock_review.return_value = mock_review_result
                    with patch(
                        "src.api.routes.chat_pipeline.routing._apply_plan_review"
                    ) as mock_apply:
                        mock_apply.return_value = ["architect_general"]
                        with patch(
                            "src.api.routes.chat_pipeline.routing._store_plan_review_episode"
                        ):
                            _plan_review_gate(request, routing, primitives, state)

        mock_apply.assert_called_once()
        assert routing.routing_decision == ["architect_general"]

    def test_plan_review_drop_discards_plan_and_keeps_default_route(self):
        """Drop means no-plan fallback, not a terminal task rejection."""
        request = ChatRequest(prompt="test", real_mode=True)
        routing = MagicMock()
        routing.task_ir = {
            "task_type": "code",
            "plan": {"steps": [{"id": "S1", "action": "bad"}]},
        }
        routing.routing_decision = ["worker_general"]
        routing.task_id = "test-123"
        primitives = MagicMock()
        state = MagicMock()

        review_result = PlanReviewResult(
            decision="drop",
            score=0.9,
            feedback="Plan incomplete",
            patches=[],
        )

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.plan_review = True
            with patch("src.api.routes.chat_pipeline.routing._needs_plan_review") as mock_needs:
                mock_needs.return_value = True
                with patch(
                    "src.api.routes.chat_pipeline.routing._architect_plan_review"
                ) as mock_review:
                    mock_review.return_value = review_result
                    with patch(
                        "src.api.routes.chat_pipeline.routing._apply_plan_review"
                    ) as mock_apply:
                        with patch(
                            "src.api.routes.chat_pipeline.routing._store_plan_review_episode"
                        ) as mock_store:
                            result = _plan_review_gate(request, routing, primitives, state)

        assert result is review_result
        assert routing.routing_decision == ["worker_general"]
        assert "plan" not in routing.task_ir
        mock_apply.assert_not_called()
        mock_store.assert_called_once()

    def test_plan_review_stores_episode(self):
        """Plan review stores episode when result exists."""
        request = ChatRequest(prompt="test", real_mode=True)
        routing = MagicMock()
        routing.task_ir = {"task_type": "code"}
        routing.routing_decision = ["coder_escalation"]
        routing.task_id = "test-123"
        primitives = MagicMock()
        state = MagicMock()

        mock_review_result = MagicMock()
        mock_review_result.decision = "ok"

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.plan_review = True
            with patch("src.api.routes.chat_pipeline.routing._needs_plan_review") as mock_needs:
                mock_needs.return_value = True
                with patch(
                    "src.api.routes.chat_pipeline.routing._architect_plan_review"
                ) as mock_review:
                    mock_review.return_value = mock_review_result
                    with patch(
                        "src.api.routes.chat_pipeline.routing._store_plan_review_episode"
                    ) as mock_store:
                        _plan_review_gate(request, routing, primitives, state)

        mock_store.assert_called_once_with(state, "test-123", routing.task_ir, mock_review_result)

    def test_plan_review_no_store_when_none(self):
        """Plan review doesn't store when result is None."""
        request = ChatRequest(prompt="test", real_mode=True)
        routing = MagicMock()
        routing.task_ir = {"task_type": "code"}
        routing.routing_decision = ["coder_escalation"]
        primitives = MagicMock()
        state = MagicMock()

        with patch("src.api.routes.chat_pipeline.routing.features") as mock_features:
            mock_features.return_value.plan_review = True
            with patch("src.api.routes.chat_pipeline.routing._needs_plan_review") as mock_needs:
                mock_needs.return_value = True
                with patch(
                    "src.api.routes.chat_pipeline.routing._architect_plan_review"
                ) as mock_review:
                    mock_review.return_value = None
                    with patch(
                        "src.api.routes.chat_pipeline.routing._store_plan_review_episode"
                    ) as mock_store:
                        _plan_review_gate(request, routing, primitives, state)

        mock_store.assert_not_called()


class TestTrinityRoleShadow:
    """TR-3.2: classifier wires through _route_request and populates
    RoutingResult.assigned_role in shadow mode (no flag check).
    """

    def _state(self):
        s = MagicMock()
        s.hybrid_router = None
        s.failure_graph = None
        s.progress_logger = None
        return s

    def test_assigned_role_default_worker(self):
        request = ChatRequest(prompt="Write hello world.", mock_mode=True, real_mode=False)
        result = _route_request(request, self._state())
        assert result.assigned_role == "worker"

    def test_assigned_role_thinker_on_plan_keyword(self):
        request = ChatRequest(
            prompt="Plan how to migrate the database to Postgres.",
            mock_mode=True,
            real_mode=False,
        )
        result = _route_request(request, self._state())
        assert result.assigned_role == "thinker"

    def test_assigned_role_verifier_on_review_with_prior_content(self):
        request = ChatRequest(
            prompt="Review my answer above and verify it is correct.",
            mock_mode=True,
            real_mode=False,
        )
        result = _route_request(request, self._state())
        assert result.assigned_role == "verifier"

    def test_assigned_role_thinker_on_architect_force_role(self):
        request = ChatRequest(
            prompt="Quick task.",
            real_mode=True,
            force_role="architect_general",
        )
        result = _route_request(request, self._state())
        assert result.assigned_role == "thinker"

    def test_assigned_role_thinker_on_thinking_budget(self):
        request = ChatRequest(
            prompt="Quick task.",
            mock_mode=True,
            real_mode=False,
            thinking_budget=2048,
        )
        result = _route_request(request, self._state())
        assert result.assigned_role == "thinker"

    def test_assigned_role_populated_when_flag_off(self, monkeypatch):
        # Shadow mode: flag is OFF but field is still populated.
        monkeypatch.delenv("ORCHESTRATOR_ROLE_AWARE_ROUTING", raising=False)
        request = ChatRequest(prompt="Plan a migration.", mock_mode=True, real_mode=False)
        result = _route_request(request, self._state())
        assert result.assigned_role == "thinker"  # Always populated.

    def test_classifier_failure_falls_back_to_worker(self):
        """If the classifier import or call raises, _route_request must not
        crash — it falls back to "worker" (the safe default).
        """
        request = ChatRequest(prompt="anything.", mock_mode=True, real_mode=False)
        with patch(
            "src.classifiers.role_classifier.classify_role",
            side_effect=RuntimeError("synthetic failure"),
        ):
            result = _route_request(request, self._state())
        assert result.assigned_role == "worker"

    def test_shadow_role_persisted_in_progress_metadata(self):
        request = ChatRequest(
            prompt="Plan a migration.",
            mock_mode=True,
            real_mode=False,
        )
        state = self._state()
        state.progress_logger = MagicMock()
        result = _route_request(request, state)

        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert result.assigned_role == "thinker"
        assert call_kwargs["routing_meta"]["assigned_role"] == "thinker"

    def test_factual_risk_mode_persisted_in_progress_metadata(self):
        request = ChatRequest(
            prompt="Verify this deployment claim.",
            mock_mode=True,
            real_mode=False,
        )
        state = self._state()
        state.progress_logger = MagicMock()

        with patch("src.classifiers.factual_risk.get_mode", return_value="enforce"):
            result = _route_request(request, state)

        call_kwargs = state.progress_logger.log_task_started.call_args.kwargs
        assert result.factual_risk_mode == "enforce"
        assert call_kwargs["routing_meta"]["factual_risk_mode"] == "enforce"

    def test_factual_risk_mode_uses_task_id_as_canary_sample_key_without_request_id(self):
        request = ChatRequest(
            prompt="Verify this deployment claim.",
            mock_mode=True,
            real_mode=False,
        )
        state = self._state()
        state.progress_logger = MagicMock()

        with patch("src.classifiers.factual_risk.get_mode", return_value="shadow") as mock_get_mode:
            result = _route_request(request, state)

        assert result.factual_risk_mode == "shadow"
        call_kwargs = mock_get_mode.call_args.kwargs
        assert call_kwargs["sample_key"] == result.task_id
        assert call_kwargs["role"] == result.routing_decision[0]

    def test_factual_risk_mode_uses_request_id_as_canary_sample_key_when_available(self):
        request = ChatRequest(
            prompt="Verify this deployment claim.",
            mock_mode=True,
            real_mode=False,
            request_id="ri10-frontdoor-enforce-001",
        )
        state = self._state()
        state.progress_logger = MagicMock()

        with patch(
            "src.classifiers.factual_risk.get_mode", return_value="enforce"
        ) as mock_get_mode:
            result = _route_request(request, state)

        assert result.factual_risk_mode == "enforce"
        call_kwargs = mock_get_mode.call_args.kwargs
        assert call_kwargs["sample_key"] == "ri10-frontdoor-enforce-001"
        assert call_kwargs["role"] == result.routing_decision[0]


def test_routing_meta_persists_ure_uncertainty_when_shadow_enabled(monkeypatch):
    request = ChatRequest(prompt="Which backend should handle this?")
    state = SimpleNamespace(
        active_requests=0,
        llm_primitives=None,
        registry=None,
        hybrid_router=SimpleNamespace(
            last_decision_meta={
                "chosen_action": "frontdoor",
                "q_topk": [0.5, 0.49],
                "selection_score_topk": [0.5, 0.49],
                "q_robust_confidence": 0.5,
            }
        ),
    )
    monkeypatch.setattr(
        "src.features.features",
        lambda: SimpleNamespace(ure_uncertainty_shadow_log=True),
    )
    monkeypatch.setattr(
        "src.uncertainty_shadow.emit_uncertainty_shadow",
        lambda meta, **kwargs: True,
    )

    meta = routing_meta(
        request,
        state,
        routing_strategy="learned",
        heuristic_priors={},
        factual_risk_score=0.1,
        factual_risk_band="low",
        factual_risk_mode="shadow",
        difficulty_score=0.2,
        difficulty_band="easy",
        estimated_cost=0.001,
        assigned_role="worker",
    )

    assert meta["assigned_role"] == "worker"
    assert meta["factual_risk_mode"] == "shadow"
    assert 0.0 <= meta["uncertainty_score"] <= 1.0
    assert meta["uncertainty_components"]
    assert meta["uncertainty_n_alternatives"] == 2


def test_routing_meta_embeds_xmas_when_supplied(monkeypatch):
    request = ChatRequest(prompt="Refactor this function")
    state = SimpleNamespace(
        active_requests=0,
        llm_primitives=None,
        registry=None,
        hybrid_router=None,
    )
    monkeypatch.setattr(
        "src.features.features",
        lambda: SimpleNamespace(ure_uncertainty_shadow_log=False),
    )

    meta = routing_meta(
        request,
        state,
        routing_strategy="rules",
        heuristic_priors={},
        factual_risk_score=0.0,
        factual_risk_band="",
        factual_risk_mode="",
        difficulty_score=0.0,
        difficulty_band="",
        estimated_cost=0.0,
        assigned_role="worker",
        xmas_meta={"mode": "shadow", "cell": "code:refine", "applied": False},
    )

    assert meta["xmas"] == {
        "mode": "shadow",
        "cell": "code:refine",
        "applied": False,
    }


def _vision_meta(monkeypatch, request):
    """Build routing metadata for `request` with all shadow subsystems off."""
    state = SimpleNamespace(
        active_requests=0,
        llm_primitives=None,
        registry=None,
        hybrid_router=None,
    )
    monkeypatch.setattr(
        "src.features.features",
        lambda: SimpleNamespace(ure_uncertainty_shadow_log=False),
    )
    return routing_meta(
        request,
        state,
        routing_strategy="vision_input",
        heuristic_priors={},
        factual_risk_score=0.0,
        factual_risk_band="",
        factual_risk_mode="",
        difficulty_score=0.0,
        difficulty_band="",
        estimated_cost=0.0,
        assigned_role="worker",
    )


def test_routing_meta_captures_image_path(monkeypatch):
    """A vision request must leave a durable image reference in the progress log.

    Regression guard: before this, `image_path` was forwarded to the VL backend
    but persisted to NO progress event, so the dashboard and every offline
    consumer saw a vision task as an ordinary text task.
    """
    img = "/mnt/raid0/llm/epyc-orchestrator/benchmarks/images/vl/chartqa/chart_test_0452.png"
    meta = _vision_meta(monkeypatch, ChatRequest(prompt="Read the chart", image_path=img))

    assert meta["image_path"] == img
    assert meta["has_image"] is True
    assert meta["image_source"] == "path"


def test_routing_meta_never_persists_base64_payload(monkeypatch):
    """base64 images record a flag + source, never the (megabyte) payload."""
    payload = "A" * 4096
    meta = _vision_meta(monkeypatch, ChatRequest(prompt="Read it", image_base64=payload))

    assert meta["has_image"] is True
    assert meta["image_source"] == "base64"
    assert "image_path" not in meta
    assert payload not in json.dumps(meta)


def test_routing_meta_omits_image_keys_for_text_requests(monkeypatch):
    """Text traffic keeps its exact legacy payload shape — no new keys."""
    meta = _vision_meta(monkeypatch, ChatRequest(prompt="What is 2+2?"))

    assert "image_path" not in meta
    assert "has_image" not in meta
    assert "image_source" not in meta


def test_routing_meta_bounds_image_path_length(monkeypatch):
    """A pathological path is capped so it cannot balloon every log line."""
    from src.api.routes.chat_pipeline.routing_decision import MAX_IMAGE_PATH_LEN

    meta = _vision_meta(monkeypatch, ChatRequest(prompt="p", image_path="/mnt/raid0/" + "x" * 4096))
    assert len(meta["image_path"]) == MAX_IMAGE_PATH_LEN
