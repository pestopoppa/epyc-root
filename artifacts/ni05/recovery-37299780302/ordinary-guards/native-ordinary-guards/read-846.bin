"""Tests for TD-21.20: proactive_stage plan-step decomposition repair.

Today (pre-fix): `_parse_plan_steps` fished the architect's JSON array with a
fence-strip + trailing-comma regex; on a miss it silently returned `[]` and
`_execute_proactive` fell through to the standard pipeline with NO counter
and NO telemetry -- the whole architect decomposition call was discarded
invisibly.

Covers: happy path is fished with zero repair calls (`_parse_plan_steps`
unchanged, byte-identical); a parse miss costs exactly one repair turn on
the SAME `architect_general` role and recovers a plan; an unrecognized
`actor` cannot come back "repaired" (schema enum, not silently substituted
or accepted); terminal repair failure is logged AND counted, not silent;
the (site, status) counters via `STRUCTURED_OUTPUT_REPAIR_COUNTS`.
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.models import ChatRequest
from src.api.routes.chat_pipeline.proactive_stage import (
    _PLAN_STEPS_REPAIR_SITE,
    _decompose_plan_steps,
    _execute_proactive,
)
from src.api.routes.chat_utils import RoutingResult
from src.structured_output.repair import STRUCTURED_OUTPUT_REPAIR_COUNTS, reset_counts_for_tests


@pytest.fixture(autouse=True)
def _clear_counts():
    reset_counts_for_tests()
    yield
    reset_counts_for_tests()


def _primitives(*llm_call_results):
    primitives = MagicMock()
    primitives.llm_call = MagicMock(side_effect=list(llm_call_results))
    return primitives


# --------------------------------------------------------------------------- _decompose_plan_steps (unit)


class TestDecomposePlanStepsHappyPath:
    @pytest.mark.asyncio
    async def test_clean_json_array_fished_with_zero_repair_calls(self):
        primitives = _primitives()  # llm_call must never be reached
        raw = json.dumps(
            [
                {"id": "s1", "action": "explore"},
                {"id": "s2", "action": "implement", "depends_on": ["s1"]},
            ]
        )

        steps = await _decompose_plan_steps(raw, primitives=primitives, task_id="t1")

        assert [s["id"] for s in steps] == ["s1", "s2"]
        assert steps[0]["actor"] == "worker"  # _parse_plan_steps's own default, unchanged
        primitives.llm_call.assert_not_called()
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS == {}


class TestDecomposePlanStepsRepair:
    @pytest.mark.asyncio
    async def test_unparseable_prose_costs_one_repair_call_and_recovers(self):
        repaired = json.dumps(
            [
                {"id": "S1", "action": "explore the codebase", "actor": "worker"},
                {"id": "S2", "action": "write the patch", "actor": "coder", "depends_on": ["S1"]},
            ]
        )
        primitives = _primitives(repaired)
        # TD-21.34 require_evidence: id/action/depends_on must be literally
        # present in the raw text (actor is exempt -- semantic mapping).
        raw = "S1: explore the codebase. S2: write the patch after that (depends on S1)."

        steps = await _decompose_plan_steps(raw, primitives=primitives, task_id="t2")

        assert len(steps) == 2
        assert steps[0] == {
            "id": "S1", "action": "explore the codebase", "actor": "worker",
            "depends_on": [], "outputs": [],
        }
        assert steps[1]["depends_on"] == ["S1"]
        assert primitives.llm_call.call_count == 1
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get((_PLAN_STEPS_REPAIR_SITE, "repaired")) == 1

    @pytest.mark.asyncio
    async def test_unrecognized_actor_is_not_silently_accepted(self):
        """A closed-set enum on `actor` makes an off-set value structurally
        impossible to receive as "repaired" -- unlike a Python clamp, which
        would silently substitute a default."""
        bad_repair = json.dumps(
            [
                {"id": "S1", "action": "review the design", "actor": "reviewer"},
                {"id": "S2", "action": "ship it", "actor": "worker"},
            ]
        )
        primitives = _primitives(bad_repair)
        raw = "First have someone review the design, then ship it."

        steps = await _decompose_plan_steps(raw, primitives=primitives, task_id="t3")

        assert steps == []
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get((_PLAN_STEPS_REPAIR_SITE, "failed")) == 1

    @pytest.mark.asyncio
    async def test_terminal_transport_failure_is_logged_and_counted(self, caplog):
        primitives = _primitives(RuntimeError("connection refused"))
        raw = "The architect's reply had no extractable plan at all."

        with caplog.at_level("WARNING"):
            steps = await _decompose_plan_steps(raw, primitives=primitives, task_id="t4")

        assert steps == []
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get((_PLAN_STEPS_REPAIR_SITE, "failed")) == 1
        assert any("plan-step repair failed" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_empty_array_repair_is_a_legitimate_zero_step_outcome(self):
        """The reply may genuinely contain no steps -- an empty array is a
        valid "repaired" outcome, not a failure; the caller's own >= 2
        threshold (unchanged) is what decides whether to fall through."""
        primitives = _primitives("[]")
        raw = "I don't think this task needs decomposition."

        steps = await _decompose_plan_steps(raw, primitives=primitives, task_id="t5")

        assert steps == []
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get((_PLAN_STEPS_REPAIR_SITE, "repaired")) == 1


# --------------------------------------------------------------------------- _execute_proactive (integration)


@pytest.fixture
def mock_state():
    state = MagicMock()
    state.registry = MagicMock()
    state.progress_logger = None
    state.hybrid_router = MagicMock()
    state.increment_request = MagicMock()
    return state


class TestExecuteProactiveRepairIntegration:
    @pytest.mark.asyncio
    async def test_malformed_plan_is_repaired_and_delegation_proceeds(self, mock_state):
        request = ChatRequest(prompt="Build a complex system", real_mode=True)
        routing = RoutingResult(
            task_id="proactive-repair-001",
            task_ir={"task_type": "code"},
            use_mock=False,
            routing_decision=["frontdoor"],
            routing_strategy="deterministic",
        )
        start_time = time.perf_counter()

        primitives = MagicMock()
        primitives._backends = True
        primitives.total_tokens_generated = 100
        primitives.total_prompt_eval_ms = 50
        primitives.total_generation_ms = 200
        primitives._last_predicted_tps = 25.0
        primitives.total_http_overhead_ms = 10
        primitives.get_cache_stats.return_value = {}
        repaired_plan = json.dumps(
            [
                {"id": "s1", "action": "first step", "actor": "worker"},
                {"id": "s2", "action": "second step", "actor": "coder", "depends_on": ["s1"]},
            ]
        )
        primitives.llm_call = MagicMock(
            side_effect=[
                # TD-21.34 require_evidence: id/action/depends_on must be
                # literally present for the repair turn to copy faithfully.
                "The architect rambled about s1 (first step) and s2 "
                "(second step, depends on s1) without emitting valid JSON.",
                repaired_plan,
            ]
        )

        mock_deleg_result = MagicMock()
        mock_deleg_result.aggregated_output = "Proactive result"
        mock_deleg_result.all_approved = True
        mock_deleg_result.subtask_results = [MagicMock(), MagicMock()]
        mock_deleg_result.roles_used = ["coder", "architect"]

        with patch("src.api.routes.chat_pipeline.proactive_stage.features") as mock_features:
            mock_features.return_value.parallel_execution = True
            with patch("src.proactive_delegation.classify_task_complexity") as mock_classify:
                from src.proactive_delegation import TaskComplexity

                mock_classify.return_value = (TaskComplexity.COMPLEX, {})
                with patch("src.proactive_delegation.ProactiveDelegator") as mock_pd:
                    mock_pd.return_value.delegate = AsyncMock(return_value=mock_deleg_result)
                    result = await _execute_proactive(request, routing, primitives, mock_state, start_time)

        assert result is not None
        assert result.answer == "Proactive result"
        assert primitives.llm_call.call_count == 2
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get((_PLAN_STEPS_REPAIR_SITE, "repaired")) == 1

    @pytest.mark.asyncio
    async def test_terminal_plan_repair_failure_falls_through_silently_to_caller(self, mock_state):
        """Falling through is still allowed (business rule unchanged) -- but
        it must be COUNTED, unlike the pre-TD-21.20 bare `[]`."""
        request = ChatRequest(prompt="Build a complex system", real_mode=True)
        routing = RoutingResult(
            task_id="proactive-repair-002",
            task_ir={"task_type": "code"},
            use_mock=False,
            routing_decision=["frontdoor"],
            routing_strategy="deterministic",
        )
        start_time = time.perf_counter()

        primitives = MagicMock()
        primitives.llm_call = MagicMock(
            side_effect=[
                "No plan here, just rambling.",
                RuntimeError("connection refused"),
            ]
        )

        with patch("src.api.routes.chat_pipeline.proactive_stage.features") as mock_features:
            mock_features.return_value.parallel_execution = True
            with patch("src.proactive_delegation.classify_task_complexity") as mock_classify:
                from src.proactive_delegation import TaskComplexity

                mock_classify.return_value = (TaskComplexity.COMPLEX, {})
                result = await _execute_proactive(request, routing, primitives, mock_state, start_time)

        assert result is None
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get((_PLAN_STEPS_REPAIR_SITE, "failed")) == 1
