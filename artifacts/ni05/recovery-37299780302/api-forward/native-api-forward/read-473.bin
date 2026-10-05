"""Tests for LangGraph migration Phase 3 — per-node dispatch.

Tests cover:
1. Feature flag dispatch: flag off = pydantic_graph, flag on = LangGraph
2. Per-node dual-run parity: both backends produce identical results
3. Cross-backend escalation: state round-trips cleanly between backends
4. _run_via_langgraph helper: correct conversion and mapping
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.state import TaskDeps, TaskState
from src.roles import Role


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_deps() -> TaskDeps:
    """Create minimal TaskDeps for testing."""
    deps = TaskDeps()
    deps.primitives = MagicMock()
    deps.repl = MagicMock()
    deps.failure_graph = MagicMock()
    deps.failure_graph.check_veto.return_value = (False, "", 0.0)
    return deps


def _make_state(**kwargs) -> TaskState:
    """Create TaskState with test defaults."""
    defaults = dict(
        task_id="phase3-test",
        prompt="test prompt",
        max_turns=15,
    )
    defaults.update(kwargs)
    return TaskState(**defaults)


def _make_ctx(**kwargs) -> SimpleNamespace:
    """Create a pydantic_graph-compatible ctx."""
    state = _make_state(**kwargs)
    deps = _make_deps()
    return SimpleNamespace(state=state, deps=deps)


# Node params: (node_name, pg_class_name, role, lg_flag_name, escalation_target)
NODE_PARAMS = [
    ("ingest", "IngestNode", Role.INGEST_LONG_CONTEXT, "langgraph_ingest", "architect"),
    ("architect", "ArchitectNode", Role.ARCHITECT_GENERAL, "langgraph_architect", None),
    ("worker", "WorkerNode", Role.WORKER_GENERAL, "langgraph_worker", "coder_escalation"),
    ("frontdoor", "FrontdoorNode", Role.FRONTDOOR, "langgraph_frontdoor", "coder_escalation"),
    ("coder", "CoderNode", Role.THINKING_REASONING, "langgraph_coder", "architect"),
    ("coder_escalation", "CoderEscalationNode", Role.CODER_ESCALATION, "langgraph_coder_escalation", "architect"),
]


NODE_IDS = [p[0] for p in NODE_PARAMS]


# ---------------------------------------------------------------------------
# 1. Feature flag dispatch tests
# ---------------------------------------------------------------------------


class TestFeatureFlagDispatch:
    """Verify per-node flags route to the correct backend."""

    @pytest.mark.parametrize("node_name,pg_class,role,flag_name,_esc_target", NODE_PARAMS, ids=NODE_IDS)
    @pytest.mark.asyncio
    async def test_flag_off_uses_pydantic_graph(self, node_name, pg_class, role, flag_name, _esc_target):
        """With flag off, node should NOT call _run_via_langgraph."""
        from src.graph import nodes as nodes_mod

        node_cls = getattr(nodes_mod, pg_class)
        node = node_cls()
        ctx = _make_ctx(current_role=role)

        # Mock _execute_turn to return immediate success
        mock_turn = AsyncMock(return_value=("Answer", None, True, {"_tool_outputs": []}))

        # Ensure flag is off
        mock_features = MagicMock()
        setattr(mock_features, flag_name, False)

        with patch("src.graph.nodes._get_features", return_value=mock_features), \
             patch("src.graph.nodes._execute_turn", mock_turn), \
             patch("src.graph.nodes._make_end_result") as mock_end, \
             patch("src.graph.nodes._run_via_langgraph") as mock_lg:
            mock_end.return_value = MagicMock()  # End[TaskResult]
            await node.run(ctx)

        mock_lg.assert_not_called()

    @pytest.mark.parametrize("node_name,pg_class,role,flag_name,_esc_target", NODE_PARAMS, ids=NODE_IDS)
    @pytest.mark.asyncio
    async def test_flag_on_uses_langgraph(self, node_name, pg_class, role, flag_name, _esc_target):
        """With flag on, node should delegate to _run_via_langgraph."""
        from src.graph import nodes as nodes_mod

        node_cls = getattr(nodes_mod, pg_class)
        node = node_cls()
        ctx = _make_ctx(current_role=role)

        mock_features = MagicMock()
        setattr(mock_features, flag_name, True)

        mock_lg_result = MagicMock()

        with patch("src.graph.nodes._get_features", return_value=mock_features), \
             patch("src.graph.nodes._run_via_langgraph", new_callable=AsyncMock, return_value=mock_lg_result) as mock_lg:
            result = await node.run(ctx)

        mock_lg.assert_called_once_with(ctx, node_name)
        assert result is mock_lg_result


# ---------------------------------------------------------------------------
# 2. Per-node dual-run parity tests
# ---------------------------------------------------------------------------


class TestDualRunParity:
    """Run same scenario through both backends, compare results."""

    @pytest.mark.parametrize("node_name,pg_class,role,flag_name,_esc_target", NODE_PARAMS, ids=NODE_IDS)
    @pytest.mark.asyncio
    async def test_success_parity(self, node_name, pg_class, role, flag_name, _esc_target):
        """Both backends should return __end__ on immediate success."""
        from src.graph.langgraph.nodes import (
            frontdoor_node, worker_node, coder_node,
            coder_escalation_node, ingest_node, architect_node,
        )
        from src.graph.langgraph.state import task_state_to_lg

        lg_funcs = {
            "frontdoor": frontdoor_node, "worker": worker_node,
            "coder": coder_node, "coder_escalation": coder_escalation_node,
            "ingest": ingest_node, "architect": architect_node,
        }
        lg_func = lg_funcs[node_name]

        mock_turn = AsyncMock(return_value=("Success answer", None, True, {"_tool_outputs": []}))

        # Run LangGraph backend
        state = _make_state(current_role=role)
        state_dict = task_state_to_lg(state)
        config = {"configurable": {"deps": _make_deps()}}

        with patch("src.graph.langgraph.nodes._execute_turn", mock_turn), \
             patch("src.graph.langgraph.nodes._make_end_result"):
            lg_result = await lg_func(state_dict, config)

        assert lg_result["next_node"] == "__end__"
        assert lg_result["_result"]["success"] is True

    @pytest.mark.parametrize("node_name,pg_class,role,flag_name,_esc_target", NODE_PARAMS, ids=NODE_IDS)
    @pytest.mark.asyncio
    async def test_self_loop_parity(self, node_name, pg_class, role, flag_name, _esc_target):
        """Both backends should return self-loop on retryable error."""
        from src.graph.langgraph.nodes import (
            frontdoor_node, worker_node, coder_node,
            coder_escalation_node, ingest_node, architect_node,
        )
        from src.graph.langgraph.state import task_state_to_lg

        lg_funcs = {
            "frontdoor": frontdoor_node, "worker": worker_node,
            "coder": coder_node, "coder_escalation": coder_escalation_node,
            "ingest": ingest_node, "architect": architect_node,
        }
        lg_func = lg_funcs[node_name]

        mock_turn = AsyncMock(return_value=("", "Transient error", False, {}))

        state = _make_state(current_role=role)
        state_dict = task_state_to_lg(state)
        config = {"configurable": {"deps": _make_deps()}}

        with patch("src.graph.langgraph.nodes._execute_turn", mock_turn), \
             patch("src.graph.langgraph.nodes._should_escalate", return_value=False), \
             patch("src.graph.langgraph.nodes._should_think_harder", return_value=False), \
             patch("src.graph.langgraph.nodes._should_retry", return_value=True), \
             patch("src.graph.langgraph.nodes._record_failure"):
            lg_result = await lg_func(state_dict, config)

        assert lg_result["next_node"] == node_name
        assert lg_result["consecutive_failures"] == 1

    @pytest.mark.parametrize(
        "node_name,pg_class,role,flag_name,esc_target",
        [p for p in NODE_PARAMS if p[4] is not None],
        ids=[p[0] for p in NODE_PARAMS if p[4] is not None],
    )
    @pytest.mark.asyncio
    async def test_escalation_parity(self, node_name, pg_class, role, flag_name, esc_target):
        """Non-terminal nodes should escalate to the correct target."""
        from src.graph.langgraph.nodes import (
            frontdoor_node, worker_node, coder_node,
            coder_escalation_node, ingest_node,
        )
        from src.graph.langgraph.state import task_state_to_lg

        lg_funcs = {
            "frontdoor": frontdoor_node, "worker": worker_node,
            "coder": coder_node, "coder_escalation": coder_escalation_node,
            "ingest": ingest_node,
        }
        lg_func = lg_funcs[node_name]

        mock_turn = AsyncMock(return_value=("", "Critical error", False, {}))

        state = _make_state(current_role=role, role_history=[node_name])
        state_dict = task_state_to_lg(state)
        config = {"configurable": {"deps": _make_deps()}}

        with patch("src.graph.langgraph.nodes._execute_turn", mock_turn), \
             patch("src.graph.langgraph.nodes._should_think_harder", return_value=False), \
             patch("src.graph.langgraph.nodes._should_escalate", return_value=True), \
             patch("src.graph.langgraph.nodes._should_retry", return_value=False), \
             patch("src.graph.langgraph.nodes._record_failure"), \
             patch("src.graph.langgraph.nodes._log_escalation"):
            lg_result = await lg_func(state_dict, config)

        assert lg_result["next_node"] == esc_target
        assert lg_result["escalation_count"] == 1

    @pytest.mark.parametrize("node_name,pg_class,role,flag_name,_esc_target", NODE_PARAMS, ids=NODE_IDS)
    @pytest.mark.asyncio
    async def test_max_turns_parity(self, node_name, pg_class, role, flag_name, _esc_target):
        """Both backends should terminate when max_turns reached."""
        from src.graph.langgraph.nodes import (
            frontdoor_node, worker_node, coder_node,
            coder_escalation_node, ingest_node, architect_node,
        )
        from src.graph.langgraph.state import task_state_to_lg

        lg_funcs = {
            "frontdoor": frontdoor_node, "worker": worker_node,
            "coder": coder_node, "coder_escalation": coder_escalation_node,
            "ingest": ingest_node, "architect": architect_node,
        }
        lg_func = lg_funcs[node_name]

        # State at max turns
        state = _make_state(current_role=role, turns=15, max_turns=15)
        state_dict = task_state_to_lg(state)
        config = {"configurable": {"deps": _make_deps()}}

        with patch("src.graph.langgraph.nodes._make_end_result"):
            lg_result = await lg_func(state_dict, config)

        assert lg_result["next_node"] == "__end__"
        assert "Max turns" in lg_result.get("_result", {}).get("answer", "")


class TestInfraFailureShortCircuit:
    """`_execute_turn` tags `artifacts["_infra_failure"]` when the raw LLM
    call returned the orchestrator's own in-band `[ERROR: ...]` backend
    sentinel (a placement/admission timeout, circuit-open, dead connection,
    ...) instead of genuine model output -- see
    `src/graph/helpers.py::_backend_infra_sentinel`. EVERY node, in BOTH
    backends, must end the turn immediately on that signal: no retry, no
    escalation, and the sentinel text preserved verbatim (never rewrapped as
    `[FAILED: ...]`) so `_annotate_error` can classify the correct HTTP
    status. This is checked BEFORE `_should_escalate`/`_should_retry` are
    even consulted -- asserted here by never having patched them (a
    regression that fell through to the ordinary error path would raise
    `AttributeError`/`TypeError` calling the real, un-mocked decision
    functions against a `MagicMock` error-category)."""

    _SENTINEL = "[ERROR: placement timeout role=frontdoor reason=race_lost holders=[] after 60.0s]"

    @pytest.mark.parametrize("node_name,pg_class,role,flag_name,_esc_target", NODE_PARAMS, ids=NODE_IDS)
    @pytest.mark.asyncio
    async def test_langgraph_backend_ends_verbatim_no_escalation(
        self, node_name, pg_class, role, flag_name, _esc_target
    ):
        from src.graph.langgraph.nodes import (
            frontdoor_node, worker_node, coder_node,
            coder_escalation_node, ingest_node, architect_node,
        )
        from src.graph.langgraph.state import task_state_to_lg

        lg_funcs = {
            "frontdoor": frontdoor_node, "worker": worker_node,
            "coder": coder_node, "coder_escalation": coder_escalation_node,
            "ingest": ingest_node, "architect": architect_node,
        }
        lg_func = lg_funcs[node_name]

        mock_turn = AsyncMock(
            return_value=("", self._SENTINEL, False, {"_infra_failure": True})
        )

        state = _make_state(current_role=role, role_history=[node_name])
        state_dict = task_state_to_lg(state)
        deps = _make_deps()
        deps.repl.artifacts = {}
        config = {"configurable": {"deps": deps}}

        with patch("src.graph.langgraph.nodes._execute_turn", mock_turn):
            lg_result = await lg_func(state_dict, config)

        assert lg_result["next_node"] == "__end__"
        assert lg_result["_result"]["success"] is False
        assert lg_result["_result"]["answer"] == self._SENTINEL
        assert lg_result["escalation_count"] == 0
        assert lg_result["consecutive_failures"] == 0

    @pytest.mark.parametrize("node_name,pg_class,role,flag_name,_esc_target", NODE_PARAMS, ids=NODE_IDS)
    @pytest.mark.asyncio
    async def test_pydantic_graph_backend_ends_verbatim_no_escalation(
        self, node_name, pg_class, role, flag_name, _esc_target
    ):
        from src.graph import nodes as nodes_mod

        node_cls = getattr(nodes_mod, pg_class)
        node = node_cls()
        ctx = _make_ctx(current_role=role, role_history=[node_name])
        ctx.deps.repl.artifacts = {}

        mock_turn = AsyncMock(
            return_value=("", self._SENTINEL, False, {"_infra_failure": True})
        )
        mock_features = MagicMock()
        setattr(mock_features, flag_name, False)

        with patch("src.graph.nodes._get_features", return_value=mock_features), \
             patch("src.graph.nodes._execute_turn", mock_turn):
            result = await node.run(ctx)

        assert result.data.success is False
        assert result.data.answer == self._SENTINEL
        assert ctx.state.escalation_count == 0
        assert ctx.state.consecutive_failures == 0


# ---------------------------------------------------------------------------
# 3. _run_via_langgraph helper tests
# ---------------------------------------------------------------------------


class TestRunViaLanggraph:
    """Test the _run_via_langgraph dispatch helper in nodes.py."""

    @pytest.mark.asyncio
    async def test_success_returns_end(self):
        """On __end__, helper should return End[TaskResult]."""
        from pydantic_graph import End
        from src.graph.nodes import _run_via_langgraph

        ctx = _make_ctx(current_role=Role.FRONTDOOR)

        lg_result = {
            "next_node": "__end__",
            "_result": {
                "answer": "Test answer",
                "success": True,
                "role_history": ["frontdoor"],
                "turns": 1,
                "delegation_events": [],
            },
            "turns": 1,
            "consecutive_failures": 0,
        }

        mock_lg_func = AsyncMock(return_value=lg_result)

        with patch("src.graph.nodes._get_lg_node_map", return_value={"frontdoor": mock_lg_func}), \
             patch("src.graph.nodes.lg_to_task_state"):
            result = await _run_via_langgraph(ctx, "frontdoor")

        assert isinstance(result, End)
        assert result.data.success is True
        assert result.data.answer == "Test answer"

    @pytest.mark.asyncio
    async def test_self_loop_returns_node_instance(self):
        """On self-loop, helper should return the correct node class instance."""
        from src.graph.nodes import FrontdoorNode, _run_via_langgraph

        ctx = _make_ctx(current_role=Role.FRONTDOOR)

        lg_result = {
            "next_node": "frontdoor",
            "consecutive_failures": 1,
        }

        mock_lg_func = AsyncMock(return_value=lg_result)

        with patch("src.graph.nodes._get_lg_node_map", return_value={"frontdoor": mock_lg_func}), \
             patch("src.graph.nodes.lg_to_task_state"):
            result = await _run_via_langgraph(ctx, "frontdoor")

        assert isinstance(result, FrontdoorNode)

    @pytest.mark.asyncio
    async def test_escalation_returns_target_node(self):
        """On escalation, helper should return the escalation target node."""
        from src.graph.nodes import CoderEscalationNode, _run_via_langgraph

        ctx = _make_ctx(current_role=Role.FRONTDOOR)

        lg_result = {
            "next_node": "coder_escalation",
            "escalation_count": 1,
        }

        mock_lg_func = AsyncMock(return_value=lg_result)

        with patch("src.graph.nodes._get_lg_node_map", return_value={"frontdoor": mock_lg_func}), \
             patch("src.graph.nodes.lg_to_task_state"):
            result = await _run_via_langgraph(ctx, "frontdoor")

        assert isinstance(result, CoderEscalationNode)

    @pytest.mark.asyncio
    async def test_unknown_next_node_raises(self):
        """Unknown next_node should raise ValueError."""
        from src.graph.nodes import _run_via_langgraph

        ctx = _make_ctx(current_role=Role.FRONTDOOR)

        lg_result = {"next_node": "nonexistent_node"}
        mock_lg_func = AsyncMock(return_value=lg_result)

        with patch("src.graph.nodes._get_lg_node_map", return_value={"frontdoor": mock_lg_func}), \
             patch("src.graph.nodes.lg_to_task_state"), \
             pytest.raises(ValueError, match="Unknown next_node"):
            await _run_via_langgraph(ctx, "frontdoor")

    @pytest.mark.asyncio
    async def test_state_conversion_roundtrip(self):
        """State should survive the TaskState → LG → TaskState round-trip."""
        from src.graph.nodes import _run_via_langgraph

        ctx = _make_ctx(
            current_role=Role.FRONTDOOR,
            role_history=["frontdoor"],
            turns=3,
            consecutive_failures=1,
            escalation_count=0,
        )

        # Capture the state dict passed to the LG function
        captured_state = {}

        async def capture_lg_func(state_dict, config):
            captured_state.update(state_dict)
            return {
                "next_node": "frontdoor",
                "consecutive_failures": 2,
            }

        with patch("src.graph.nodes._get_lg_node_map", return_value={"frontdoor": capture_lg_func}), \
             patch("src.graph.nodes.lg_to_task_state"):
            await _run_via_langgraph(ctx, "frontdoor")

        # Verify key fields were converted
        assert captured_state["turns"] == 3
        assert captured_state["current_role"] == str(Role.FRONTDOOR)
        assert captured_state["role_history"] == ["frontdoor"]


# ---------------------------------------------------------------------------
# 4. Cross-backend escalation test
# ---------------------------------------------------------------------------


class TestCrossBackendEscalation:
    """Test escalation across backends (LG node → PG node via state transfer)."""

    @pytest.mark.asyncio
    async def test_worker_lg_to_coder_escalation_pg(self):
        """WorkerNode on LangGraph escalates to CoderEscalationNode on pydantic_graph.

        Verifies state survives the cross-backend boundary.
        """
        from src.graph.langgraph.nodes import worker_node
        from src.graph.langgraph.state import task_state_to_lg, lg_to_task_state

        mock_turn = AsyncMock(return_value=("", "Critical failure", False, {}))

        # Initial state
        state = _make_state(
            current_role=Role.WORKER_GENERAL,
            role_history=["worker"],
            turns=2,
        )
        state_dict = task_state_to_lg(state)
        config = {"configurable": {"deps": _make_deps()}}

        # Run worker via LangGraph — should escalate
        with patch("src.graph.langgraph.nodes._execute_turn", mock_turn), \
             patch("src.graph.langgraph.nodes._should_think_harder", return_value=False), \
             patch("src.graph.langgraph.nodes._should_escalate", return_value=True), \
             patch("src.graph.langgraph.nodes._should_retry", return_value=False), \
             patch("src.graph.langgraph.nodes._record_failure"), \
             patch("src.graph.langgraph.nodes._log_escalation"):
            lg_result = await worker_node(state_dict, config)

        assert lg_result["next_node"] == "coder_escalation"

        # Now convert LG result back to TaskState (simulating cross-backend handoff)
        handoff_state = _make_state(
            current_role=Role.WORKER_GENERAL,
            role_history=["worker"],
            turns=2,
        )
        lg_to_task_state(lg_result, handoff_state)

        # Verify critical fields survived
        assert handoff_state.escalation_count == 1
        assert handoff_state.consecutive_failures == 0
        # Role history should include the new role from escalation
        assert "coder_escalation" in [str(r) for r in handoff_state.role_history]


# ---------------------------------------------------------------------------
# 5. _NEXT_NODE_TO_PG mapping completeness
# ---------------------------------------------------------------------------


class TestNodeMapping:
    """Verify the next_node → PG class mapping is complete."""

    def test_all_node_names_mapped(self):
        """Every LangGraph node name should have a PG class mapping."""
        from src.graph.nodes import _NEXT_NODE_TO_PG

        expected = {
            "frontdoor", "worker", "coder", "coder_escalation",
            "ingest", "architect",
        }
        assert set(_NEXT_NODE_TO_PG.keys()) == expected

    def test_mapping_classes_are_correct(self):
        """PG class mapping should match the node class names."""
        from src.graph.nodes import (
            _NEXT_NODE_TO_PG,
            FrontdoorNode, WorkerNode, CoderNode, CoderEscalationNode,
            IngestNode, ArchitectNode,
        )

        assert _NEXT_NODE_TO_PG["frontdoor"] is FrontdoorNode
        assert _NEXT_NODE_TO_PG["worker"] is WorkerNode
        assert _NEXT_NODE_TO_PG["coder"] is CoderNode
        assert _NEXT_NODE_TO_PG["coder_escalation"] is CoderEscalationNode
        assert _NEXT_NODE_TO_PG["ingest"] is IngestNode
        assert _NEXT_NODE_TO_PG["architect"] is ArchitectNode
