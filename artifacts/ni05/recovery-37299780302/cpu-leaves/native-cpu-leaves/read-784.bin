"""summarize_session_with_worker must use a LIVE stack role, never worker_fast.

Regression for the dead-8102 landmine (model-stack-update-pipeline audit class,
sibling fixes 5b4f6838/cc401c08/f41f9564): session_log.py raw-keyed
``role="worker_fast"``, which is deliberately exempt from server-URL alias
normalization and resolves to the retired port 8102 — the call fails with a
connection error and the ``[ERROR: ...]`` string could be embedded as the
"AI Summary".
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from src.graph.session_log import (
    TurnRecord,
    _session_summary_worker_role,
    summarize_session_with_worker,
)


def _records() -> list[TurnRecord]:
    return [TurnRecord(turn=1, role="worker", output_preview="did a thing", outcome="ok")]


def test_role_selection_prefers_worker_summarize_when_live():
    with patch(
        "src.registry.stack_priors.live_stack_role_records",
        return_value={"worker_summarize": {}, "worker_general": {}},
    ):
        assert _session_summary_worker_role() == "worker_summarize"


def test_role_selection_falls_through_preference_order():
    with patch(
        "src.registry.stack_priors.live_stack_role_records",
        return_value={"worker_general": {}, "toolrunner": {}},
    ):
        assert _session_summary_worker_role() == "worker_general"


def test_role_selection_degrades_when_priors_unreadable():
    with patch(
        "src.registry.stack_priors.live_stack_role_records",
        side_effect=OSError("no priors"),
    ):
        assert _session_summary_worker_role() == "worker_summarize"


def test_summarize_never_calls_worker_fast():
    primitives = MagicMock()
    primitives.llm_call.return_value = "a fine summary"
    with patch(
        "src.graph.session_log._session_summary_worker_role",
        return_value="worker_summarize",
    ):
        result = asyncio.run(
            summarize_session_with_worker(primitives, _records(), inline=True)
        )
    role_used = primitives.llm_call.call_args.kwargs["role"]
    assert role_used == "worker_summarize"
    assert role_used != "worker_fast"
    assert "a fine summary" in result


def test_error_string_response_falls_back_to_deterministic():
    primitives = MagicMock()
    primitives.llm_call.return_value = "[ERROR: connection refused port 8102]"
    with patch(
        "src.graph.session_log._session_summary_worker_role",
        return_value="worker_summarize",
    ):
        result = asyncio.run(
            summarize_session_with_worker(primitives, _records(), inline=True)
        )
    assert "[ERROR" not in result
    assert "AI Summary" not in result  # deterministic fallback, not the LLM path
