"""Unit tests for src/api/routes/chat_pipeline/telemetry.py (TD-21.33).

``llm_completion_probabilities`` is the one function in this module that reads
``_last_inference_meta`` (``llm_completion_meta`` reads unrelated CUMULATIVE
counters and never touches it). Its only call site, ``_execute_direct``
(``direct_stage.py``), is invoked as a WHOLE unit via ``asyncio.to_thread`` from
``chat.py`` against ``state._real_primitives`` -- the SAME shared-instance shape
that produced the TD-21.21 edit-transaction bug. No live requests; fake
backends only.
"""
from __future__ import annotations

import asyncio
import threading
from unittest.mock import Mock

from src.api.routes.chat_pipeline.telemetry import llm_completion_probabilities
from src.llm_primitives import LLMPrimitives
from src.model_server import InferenceResult


def _result(role: str, completion_reason: str, rows: list[dict]) -> InferenceResult:
    return InferenceResult(
        role=role, output="ignored", tokens_generated=1, generation_speed=1.0,
        elapsed_time=0.001, success=True, prompt_eval_ms=0.1, generation_ms=0.1,
        http_overhead_ms=0.0, completion_reason=completion_reason,
        completion_probabilities=rows,
    )


def test_llm_completion_probabilities_reads_own_call_not_a_concurrent_ones():
    """Two REAL `_real_call` invocations on ONE shared `LLMPrimitives` instance,
    ordered with threading.Event so the OTHER concurrent call's write provably
    lands on the shared plain `_last_inference_meta` attribute AFTER this call's
    own backend response and BEFORE this call reads its probability rows back
    (the exact TD-21.21 race window). `llm_completion_probabilities` must still
    return THIS call's own rows, never the concurrent call's.
    """
    prims = LLMPrimitives(
        mock_mode=False,
        server_urls={"role_a": "http://localhost:9101", "role_b": "http://localhost:9102"},
    )
    backend_a, backend_b = Mock(spec=[]), Mock(spec=[])
    backend_a.infer = Mock(return_value=_result("role_a", "stop", [{"id": 1, "logprob": -0.1}]))
    backend_b.infer = Mock(return_value=_result("role_b", "stop", [{"id": 2, "logprob": -0.9}]))
    prims._backends["role_a"] = backend_a
    prims._backends["role_b"] = backend_b

    a_done = threading.Event()
    b_done = threading.Event()

    def call_a() -> list[dict]:
        prims._real_call("prompt A", "role_a", n_tokens=8)
        a_done.set()
        assert b_done.wait(timeout=5), "concurrent call B never completed"
        return llm_completion_probabilities(prims)

    def call_b() -> None:
        assert a_done.wait(timeout=5), "call A's backend response never landed"
        prims._real_call("prompt B", "role_b", n_tokens=8)
        b_done.set()

    async def _run():
        return await asyncio.gather(
            asyncio.to_thread(call_a),
            asyncio.to_thread(call_b),
        )

    rows_a, _ = asyncio.run(_run())

    # Sanity: the race actually happened -- the shared plain attribute WAS clobbered by B.
    assert prims._last_inference_meta["completion_probabilities"] == [{"id": 2, "logprob": -0.9}]
    # But the per-call-safe read still reports A's OWN rows.
    assert rows_a == [{"id": 1, "logprob": -0.1}]


def test_llm_completion_probabilities_falls_back_for_non_llmprimitives_double():
    """A test double that predates `get_last_inference_meta` (plain attribute
    only) keeps its pre-existing exact behavior -- the isinstance guard must
    not require every caller's fake to grow the new method."""

    class _Fake:
        def __init__(self) -> None:
            self._last_inference_meta = {"completion_probabilities": [{"id": 9}]}

    assert llm_completion_probabilities(_Fake()) == [{"id": 9}]


def test_llm_completion_probabilities_handles_missing_meta():
    class _Fake:
        pass

    assert llm_completion_probabilities(_Fake()) == []
