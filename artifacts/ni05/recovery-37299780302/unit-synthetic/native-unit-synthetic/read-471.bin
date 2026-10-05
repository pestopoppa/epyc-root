"""Tests for LangGraph migration Phase 1.

Tests cover:
1. State conversion round-trip (TaskState <-> OrchestratorState)
2. Edge validation (valid/invalid transitions match pydantic_graph topology)
3. Bridge feature flag dispatching
4. Node function routing (next_node field)
5. Custom reducers (artifacts, workspace_state, think_harder_roi)
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from src.graph.state import TaskDeps, TaskResult, TaskState
from src.roles import Role

_RETIRED_ARCHITECT_ROLE = "architect_" "coding"


# ---------------------------------------------------------------------------
# 1. State conversion round-trip
# ---------------------------------------------------------------------------


class TestStateConversion:
    """Test TaskState <-> OrchestratorState conversion."""

    def test_task_state_to_lg_basic_fields(self):
        from src.graph.langgraph.state import task_state_to_lg

        state = TaskState(
            task_id="test-123",
            prompt="What is 2+2?",
            current_role=Role.FRONTDOOR,
            turns=3,
            max_turns=15,
        )
        lg = task_state_to_lg(state)

        assert lg["task_id"] == "test-123"
        assert lg["prompt"] == "What is 2+2?"
        assert lg["current_role"] == "frontdoor"
        assert lg["turns"] == 3
        assert lg["max_turns"] == 15

    def test_task_state_to_lg_skips_non_serializable(self):
        from src.graph.langgraph.state import task_state_to_lg, _SKIP_TO_LG, _CONFIG_FIELDS

        state = TaskState()
        lg = task_state_to_lg(state)

        for field in _SKIP_TO_LG:
            assert field not in lg
        for field in _CONFIG_FIELDS:
            assert field not in lg

    def test_task_state_to_lg_role_enum_serialized(self):
        from src.graph.langgraph.state import task_state_to_lg

        state = TaskState(current_role=Role.ARCHITECT_CODING)
        lg = task_state_to_lg(state)

        assert lg["current_role"] == str(Role.ARCHITECT_CODING)
        assert isinstance(lg["current_role"], str)

    def test_round_trip_preserves_fields(self):
        from src.graph.langgraph.state import task_state_to_lg, lg_to_task_state

        original = TaskState(
            task_id="rt-1",
            prompt="test prompt",
            context="test context",
            current_role=Role.CODER_ESCALATION,
            consecutive_failures=2,
            escalation_count=1,
            role_history=["frontdoor", "coder_escalation"],
            turns=5,
            last_error="some error",
            last_output="some output",
            artifacts={"key": "value"},
            workspace_state={"version": 3, "broadcast_version": 1,
                             "selection_policy": "priority_then_recency",
                             "objective": "test", "constraints": [],
                             "invariants": [], "proposals": [],
                             "commitments": [], "open_questions": [],
                             "resolved_questions": [], "decisions": [],
                             "broadcast_log": [], "updated_at": ""},
        )

        lg = task_state_to_lg(original)
        restored = TaskState()
        lg_to_task_state(lg, restored)

        assert restored.task_id == original.task_id
        assert restored.prompt == original.prompt
        assert restored.consecutive_failures == original.consecutive_failures
        assert restored.escalation_count == original.escalation_count
        assert restored.role_history == original.role_history
        assert restored.turns == original.turns
        assert restored.last_error == original.last_error
        assert restored.artifacts == original.artifacts

    def test_lg_to_task_state_skips_next_node(self):
        from src.graph.langgraph.state import lg_to_task_state

        state = TaskState()
        lg = {"next_node": "frontdoor", "task_id": "x"}
        lg_to_task_state(lg, state)

        assert state.task_id == "x"
        assert not hasattr(state, "next_node") or "next_node" not in {
            f.name for f in __import__("dataclasses").fields(state)
        }


# ---------------------------------------------------------------------------
# 2. Edge validation
# ---------------------------------------------------------------------------


class TestEdgeValidation:
    """Verify LangGraph graph has the correct edge topology."""

    def test_valid_transitions_defined(self):
        from src.graph.langgraph.graph import VALID_TRANSITIONS

        # All 6 active nodes present
        assert set(VALID_TRANSITIONS.keys()) == {
            "frontdoor", "worker", "coder", "coder_escalation",
            "ingest", "architect",
        }

    def test_valid_transitions_match_pydantic_graph(self):
        from src.graph.langgraph.graph import VALID_TRANSITIONS, END

        # Frontdoor -> {self, coder_escalation, worker, END}
        assert VALID_TRANSITIONS["frontdoor"] == {"frontdoor", "coder_escalation", "worker", END}

        # Worker -> {self, coder_escalation, END}
        assert VALID_TRANSITIONS["worker"] == {"worker", "coder_escalation", END}

        # Coder -> {self, architect, END}
        assert VALID_TRANSITIONS["coder"] == {"coder", "architect", END}

        # CoderEscalation -> {self, architect, END}
        assert VALID_TRANSITIONS["coder_escalation"] == {"coder_escalation", "architect", END}

        # Ingest -> {self, architect, END}
        assert VALID_TRANSITIONS["ingest"] == {"ingest", "architect", END}

        # Architect -> {self, END} (terminal)
        assert VALID_TRANSITIONS["architect"] == {"architect", END}

    def test_invalid_transitions_disjoint(self):
        from src.graph.langgraph.graph import VALID_TRANSITIONS, INVALID_TRANSITIONS

        for node, valid in VALID_TRANSITIONS.items():
            invalid = INVALID_TRANSITIONS.get(node, set())
            assert valid.isdisjoint(invalid), f"Node {node} has overlap: {valid & invalid}"

    def test_all_nodes_covered(self):
        from src.graph.langgraph.graph import VALID_TRANSITIONS, INVALID_TRANSITIONS, END

        all_nodes = set(VALID_TRANSITIONS.keys()) | {END}
        for node in VALID_TRANSITIONS:
            valid = VALID_TRANSITIONS[node]
            invalid = INVALID_TRANSITIONS.get(node, set())
            # Every other node should be in either valid or invalid
            other_nodes = all_nodes - {node}
            for target in other_nodes:
                assert target in valid or target in invalid, \
                    f"Node {node} -> {target} not classified as valid or invalid"


# ---------------------------------------------------------------------------
# 3. Bridge feature flag
# ---------------------------------------------------------------------------


class TestBridge:
    """Test that bridge dispatches based on feature flag."""

    @pytest.mark.asyncio
    async def test_bridge_uses_pydantic_graph_when_flag_off(self):
        from src.features import Features, set_features, reset_features

        try:
            set_features(Features(langgraph_bridge=False))

            with patch("src.graph.graph.run_task", new_callable=AsyncMock) as mock_pg:
                mock_pg.return_value = TaskResult(answer="pg", success=True)

                from src.graph.langgraph.bridge import run_task_auto
                result = await run_task_auto(TaskState(), TaskDeps())

                mock_pg.assert_called_once()
                assert result.answer == "pg"
        finally:
            reset_features()

    @pytest.mark.asyncio
    async def test_bridge_uses_langgraph_when_flag_on(self):
        from src.features import Features, set_features, reset_features

        try:
            set_features(Features(langgraph_bridge=True))

            with patch("src.graph.langgraph.graph.run_task_lg", new_callable=AsyncMock) as mock_lg:
                mock_lg.return_value = TaskResult(answer="lg", success=True)

                from src.graph.langgraph.bridge import run_task_auto
                result = await run_task_auto(TaskState(), TaskDeps())

                mock_lg.assert_called_once()
                assert result.answer == "lg"
        finally:
            reset_features()


# ---------------------------------------------------------------------------
# 4. Node function routing
# ---------------------------------------------------------------------------


class TestNodeRouting:
    """Test that node functions set next_node correctly."""

    def test_role_to_lg_node_mapping(self):
        from src.graph.langgraph.graph import build_orchestration_graph
        from src.graph.langgraph.nodes import ROLE_TO_LG_NODE, select_start_lg_node
        from src.registry.stack_priors import live_stack_role_records

        assert ROLE_TO_LG_NODE["frontdoor"] == "frontdoor"
        assert ROLE_TO_LG_NODE["worker_general"] == "worker"
        assert ROLE_TO_LG_NODE["worker_math"] == "worker"
        assert ROLE_TO_LG_NODE["coder_escalation"] == "coder_escalation"
        assert ROLE_TO_LG_NODE["ingest_long_context"] == "ingest"
        assert ROLE_TO_LG_NODE["architect_general"] == "architect"
        assert ROLE_TO_LG_NODE[str(Role.ARCHITECT_CODING)] == "architect"

        # Every mapped node must be a node the graph actually registers, or the
        # start node is unreachable.
        registered = set(build_orchestration_graph().nodes)
        assert registered
        for role, node in ROLE_TO_LG_NODE.items():
            assert node in registered, f"{role} maps to unregistered node {node!r}"

        # COMPLETENESS, derived from the live stack priors rather than a pasted
        # row list: every live routable role must have an entry. Unmapped live
        # roles silently start at the frontdoor node — the defect that left
        # architect_critic (the terminal 122B rung) and vision_escalation
        # misrouted after the 2026-08-01 W1 cutover.
        #
        # Stack priors also publish legacy server_mode ROW names that are not
        # Roles: since the 2026-09-22 cutover (orchestrator 860b0b2d) the
        # ``worker`` row is an ``alias_of: frontdoor`` row listed in
        # frontdoor.shared_with, so it appears as a live record. Production
        # canonicalizes such row names through one table
        # (src.config.models._CANONICAL_SERVER_URL_ALIASES, worker ->
        # worker_general); apply that same table here instead of restating it,
        # and still require every canonicalized name to be a real Role.
        from src.config.models import _CANONICAL_SERVER_URL_ALIASES

        live_roles = set(live_stack_role_records())
        assert live_roles, "live stack priors produced no roles"
        for raw_role in sorted(live_roles):
            canonical = _CANONICAL_SERVER_URL_ALIASES.get(raw_role, raw_role)
            resolved = Role.from_string(canonical)
            assert resolved is not None, (
                f"live role {raw_role!r} (canonical {canonical!r}) is not a Role"
            )
            assert str(resolved) in ROLE_TO_LG_NODE, (
                f"live role {raw_role!r} has no ROLE_TO_LG_NODE entry — it would "
                f"silently start at the frontdoor node"
            )

        # RETIRED roles are deliberately absent (weights deleted 2026-03-06) and
        # degrade to the frontdoor node rather than dispatching into a live backend.
        retired = "thinking_" "reasoning"
        assert retired not in ROLE_TO_LG_NODE
        assert retired not in live_roles
        assert select_start_lg_node(retired) == "frontdoor"

    def test_select_start_lg_node_default(self):
        from src.graph.langgraph.nodes import select_start_lg_node

        assert select_start_lg_node("unknown_role") == "frontdoor"
        assert select_start_lg_node("frontdoor") == "frontdoor"
        assert select_start_lg_node(str(Role.ARCHITECT_CODING)) == "architect"
        assert select_start_lg_node(_RETIRED_ARCHITECT_ROLE) == "architect"


# ---------------------------------------------------------------------------
# 5. Custom reducers
# ---------------------------------------------------------------------------


class TestReducers:
    """Test custom reducer functions for complex dict fields."""

    def test_merge_artifacts_latest_wins(self):
        from src.graph.langgraph.state import _merge_artifacts

        left = {"a": 1, "b": 2}
        right = {"b": 3, "c": 4}
        result = _merge_artifacts(left, right)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_think_harder_roi(self):
        from src.graph.langgraph.state import _merge_think_harder_roi

        left = {"frontdoor": {"ema": 0.5, "samples": 3}}
        right = {"frontdoor": {"ema": 0.7}, "coder": {"ema": 0.3}}
        result = _merge_think_harder_roi(left, right)
        assert result["frontdoor"] == {"ema": 0.7, "samples": 3}
        assert result["coder"] == {"ema": 0.3}

    def test_merge_workspace_version_wins(self):
        from src.graph.langgraph.state import _merge_workspace_state

        left = {"version": 5, "objective": "old", "broadcast_log": [], "proposals": []}
        right = {"version": 3, "objective": "new"}
        result = _merge_workspace_state(left, right)
        # Lower version => left wins
        assert result["objective"] == "old"

    def test_merge_workspace_broadcast_appends(self):
        from src.graph.langgraph.state import _merge_workspace_state

        left = {"version": 1, "broadcast_log": [{"id": "a"}], "proposals": []}
        right = {"version": 2, "broadcast_log": [{"id": "b"}], "proposals": []}
        result = _merge_workspace_state(left, right)
        assert len(result["broadcast_log"]) == 2

    def test_merge_workspace_proposals_dedup(self):
        from src.graph.langgraph.state import _merge_workspace_state

        p1 = {"id": "p1", "text": "proposal 1"}
        p2 = {"id": "p2", "text": "proposal 2"}
        left = {"version": 1, "broadcast_log": [], "proposals": [p1]}
        right = {"version": 2, "broadcast_log": [], "proposals": [p1, p2]}
        result = _merge_workspace_state(left, right)
        assert len(result["proposals"]) == 2  # p1 deduped


# ---------------------------------------------------------------------------
# 6. Graph construction
# ---------------------------------------------------------------------------


class TestGraphConstruction:
    """Test that the LangGraph StateGraph builds and compiles."""

    def test_build_orchestration_graph(self):
        from src.graph.langgraph.graph import build_orchestration_graph

        graph = build_orchestration_graph()
        assert graph is not None

    def test_compile_graph(self):
        from src.graph.langgraph.graph import build_orchestration_graph

        graph = build_orchestration_graph()
        compiled = graph.compile()
        assert compiled is not None

    def test_get_compiled_graph_singleton(self):
        from src.graph.langgraph.graph import get_compiled_graph

        g1 = get_compiled_graph()
        g2 = get_compiled_graph()
        assert g1 is g2


# ---------------------------------------------------------------------------
# 7. Feature flag field exists
# ---------------------------------------------------------------------------


class TestFeatureFlag:
    """Test that langgraph_bridge feature flag works correctly."""

    def test_feature_flag_default_false(self):
        from src.features import Features

        f = Features()
        assert f.langgraph_bridge is False

    def test_feature_flag_in_summary(self):
        from src.features import Features

        f = Features(langgraph_bridge=True)
        assert "langgraph_bridge" in f.summary()
        assert f.summary()["langgraph_bridge"] is True

    def test_feature_flag_env_var(self):
        import os
        from src.features import get_features

        os.environ["ORCHESTRATOR_LANGGRAPH_BRIDGE"] = "1"
        try:
            f = get_features()
            assert f.langgraph_bridge is True
        finally:
            del os.environ["ORCHESTRATOR_LANGGRAPH_BRIDGE"]
