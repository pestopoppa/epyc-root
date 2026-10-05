"""Unit tests for `src.graph.helpers` inference-meta capture (TD-21.33 / TD-21.33a).

TD-21.33 migrated every same-context reader of `primitives._last_inference_meta` to the
per-call-safe `get_last_inference_meta()` getter, but left `_execute_turn`
(`src/graph/helpers.py`) with a documented residual: its LLM call runs via
`await asyncio.to_thread(llm_call_fn, ...)`, and `asyncio.to_thread` copies the CALLING
context (`contextvars.copy_context()`) into the worker thread -- a ContextVar `.set()` made
inside that thread is invisible to the PARENT once the `await` returns, so a parent-side
getter read would silently and always miss it in production and fall back to the plain,
cross-request-shared `_last_inference_meta` attribute (the TD-21.21 hazard).

TD-21.33a closes that gap for real: `_call_llm_capturing_meta` invokes the call AND reads
the meta INSIDE the same thread/context the call ran in, and hands the meta back to the
caller as part of the result instead of re-deriving it from ambient state afterward. Because
each `asyncio.to_thread` invocation runs against its own COPIED `contextvars.Context`, two
concurrent calls against the SAME `LLMPrimitives` instance can never observe each other's
`get_last_inference_meta()` value, even though they still share (and can still clobber) the
plain `_last_inference_meta` attribute -- which is exactly why the getter-based read must
happen inside the call's own thread, never after crossing back out of it.

These tests exercise a REAL `LLMPrimitives` instance's ContextVar/attribute machinery
(`_set_last_inference_meta`, `get_last_inference_meta`) so the propagation semantics under
test are the production ones, not a re-implementation of them. They deliberately do NOT go
through `LLMPrimitives.llm_call`/`_real_call`: that path also runs the cross-role contention
gate and a cross-process (`fcntl`) exclusive inference lock (`src/runtime/inference_lock.py`,
default 180s timeout) against REAL shared-host state -- unrelated to the ContextVar bug this
migration closes, and unsafe to engage from a unit test on a host other sessions' real
inference may be contending for (observed directly while writing this test: two concurrent
`_real_call`s intermittently blocked for 60s+ apiece). `llm_call_fn` below is a plain
synthetic stand-in, exactly like `_execute_turn`'s own `unittest.mock` detection branch treats
a mocked `llm_call`. No live requests; no backends, no locks.
"""
from __future__ import annotations

import asyncio
import threading

import pytest

from src.graph import helpers
from src.graph.helpers import _best_effort_last_inference_meta, _call_llm_capturing_meta
from src.llm_primitives import LLMPrimitives


@pytest.fixture
def force_thread_hop(monkeypatch):
    """`_use_inline_calls_in_tests()` reads `PYTEST_CURRENT_TEST`, which pytest always sets,
    so under a bare test run `_call_llm_capturing_meta` would always take the same-thread
    inline branch and never exercise the `asyncio.to_thread` hop this fix targets. Force the
    production (thread-hop) branch for tests that specifically need it.
    """
    monkeypatch.setattr(helpers, "_use_inline_calls_in_tests", lambda: False)


# ---------------------------------------------------------------------------
# `_best_effort_last_inference_meta` -- the low-level, context-agnostic primitive.
# ---------------------------------------------------------------------------


def test_same_context_call_uses_the_per_call_safe_getter():
    """When the call and the read share one context, the getter reports it directly."""
    prims = LLMPrimitives(mock_mode=True)
    prims._set_last_inference_meta({"completion_reason": "stop", "tokens": 5})

    meta = _best_effort_last_inference_meta(prims)

    assert meta["completion_reason"] == "stop"
    assert meta["tokens"] == 5


def test_getter_read_after_crossing_a_thread_hop_falls_back_to_the_plain_attribute():
    """Calling the raw getter-preferring helper from the PARENT side of a `to_thread` hop
    (i.e. NOT via `_call_llm_capturing_meta`) still falls back correctly when uncontended --
    this is the low-level primitive's own safety property, independent of how `_execute_turn`
    now uses it.
    """
    prims = LLMPrimitives(mock_mode=True)

    async def _run():
        await asyncio.to_thread(prims._set_last_inference_meta, {"completion_reason": "length", "tokens": 9})
        # Back in the PARENT context: the getter sees nothing from the child thread's copy.
        assert prims.get_last_inference_meta() is None
        return _best_effort_last_inference_meta(prims)

    meta = asyncio.run(_run())
    assert meta["completion_reason"] == "length"
    assert meta["tokens"] == 9


def test_parent_side_read_after_a_thread_hop_remains_vulnerable_to_a_concurrent_clobberer():
    """Documents WHY `_execute_turn` could not simply call `_best_effort_last_inference_meta`
    from the PARENT after `await asyncio.to_thread(...)` returns (the pre-TD-21.33a shape):
    another call against the SAME instance can land in the exposed gap between "the thread-hop
    call returns" and "the parent reads the meta", clobbering the plain shared attribute the
    getter falls back to (and always falls back to here, since the getter's ContextVar is
    scoped to the CHILD thread's copied context, invisible to the parent). This is exactly the
    hazard `_call_llm_capturing_meta` (tested below) closes by never exposing that gap at all --
    it reads the meta INSIDE the call's own thread, before the parent ever gets control back.
    """
    prims = LLMPrimitives(mock_mode=True)
    a_done = asyncio.Event()
    b_done = asyncio.Event()

    async def a_flow():
        await asyncio.to_thread(
            prims._set_last_inference_meta, {"completion_reason": "length", "tokens": 1}
        )
        a_done.set()
        await b_done.wait()  # exposed gap: B's clobber lands HERE, before A's read below.
        return _best_effort_last_inference_meta(prims)

    async def b_flow() -> None:
        await a_done.wait()
        await asyncio.to_thread(
            prims._set_last_inference_meta, {"completion_reason": "stop", "tokens": 2}
        )
        b_done.set()

    async def _run():
        return await asyncio.gather(a_flow(), b_flow())

    meta_a, _ = asyncio.run(_run())
    # A's own meta was "length" -- the pre-existing hazard means A instead observes B's.
    assert meta_a["completion_reason"] == "stop"


def test_falls_back_for_a_double_without_the_new_getter_at_all():
    class _Bare:
        def __init__(self) -> None:
            self._last_inference_meta = {"completion_reason": "eos"}

    assert _best_effort_last_inference_meta(_Bare()) == {"completion_reason": "eos"}


def test_missing_meta_returns_empty_dict():
    class _Bare:
        pass

    assert _best_effort_last_inference_meta(_Bare()) == {}


# ---------------------------------------------------------------------------
# `_call_llm_capturing_meta` -- the TD-21.33a fix: capture INSIDE the call's own thread.
# ---------------------------------------------------------------------------


def test_inline_path_returns_result_and_its_own_meta():
    """`_use_inline_calls_in_tests()` (default under pytest): call and capture run inline,
    same thread, same context -- both the result and the meta must be THIS call's own.
    """
    prims = LLMPrimitives(mock_mode=True)

    def llm_call_fn(prompt, **kwargs):
        prims._set_last_inference_meta({"completion_reason": "stop", "tokens": 7})
        return "output"

    async def _run():
        return await _call_llm_capturing_meta(llm_call_fn, prims, "prompt", role="role_a")

    code, meta = asyncio.run(_run())
    assert code == "output"
    assert meta["completion_reason"] == "stop"
    assert meta["tokens"] == 7


def test_mock_llm_call_fn_takes_the_inline_path_and_falls_back_cleanly():
    """`_execute_turn`'s own mock-detection: a `unittest.mock` double as `llm_call_fn`
    always takes the inline branch (even with `force_thread_hop`), and a bare `primitives`
    double without the getter falls back to its plain attribute -- identical to the
    pre-TD-21.33a shape for these tests.
    """
    from unittest.mock import Mock

    class _BarePrimitives:
        def __init__(self) -> None:
            self._last_inference_meta = {"completion_reason": "eos", "tokens": 3}

    llm_call_fn = Mock(return_value="mocked output")
    prims = _BarePrimitives()

    async def _run():
        return await _call_llm_capturing_meta(llm_call_fn, prims, "prompt", role="worker")

    code, meta = asyncio.run(_run())
    assert code == "mocked output"
    assert meta == {"completion_reason": "eos", "tokens": 3}


def test_thread_hop_each_concurrent_call_observes_its_own_meta_never_the_others(force_thread_hop):
    """The production shape, and the TD-21.33 residual this closes: two concurrent calls
    against the SAME `LLMPrimitives` instance, each crossing its own `asyncio.to_thread` hop.
    Worst-case interleaving is forced with a `threading.Event`: call A's `llm_call_fn` blocks
    until call B has FULLY completed and (as a side effect of `_set_last_inference_meta`)
    already clobbered the shared plain `_last_inference_meta` attribute with B's data --
    exactly the sequence that made the pre-TD-21.33a parent-side read observe the other
    call's data. Because `_call_llm_capturing_meta` reads the meta INSIDE the call's own
    thread/context via the getter (never falling through to the shared attribute unless the
    getter itself is unavailable), A must still report its OWN meta.
    """
    prims = LLMPrimitives(mock_mode=True)
    b_done = threading.Event()

    def llm_call_a(prompt, **kwargs):
        # Give B every opportunity to finish first and clobber the shared attribute.
        assert b_done.wait(timeout=10), "call B never completed -- test setup is broken"
        prims._set_last_inference_meta({"completion_reason": "length", "tokens": 1})
        return "output A"

    def llm_call_b(prompt, **kwargs):
        prims._set_last_inference_meta({"completion_reason": "stop", "tokens": 2})
        return "output B"

    async def a_flow():
        return await _call_llm_capturing_meta(llm_call_a, prims, "prompt A", role="role_a")

    async def b_flow():
        code, meta = await _call_llm_capturing_meta(llm_call_b, prims, "prompt B", role="role_b")
        b_done.set()
        return code, meta

    async def _run():
        return await asyncio.gather(a_flow(), b_flow())

    (code_a, meta_a), (code_b, meta_b) = asyncio.run(_run())

    # Sanity: the shared plain attribute is a last-writer-wins race by construction (B writes
    # "stop", THEN signals A, THEN A writes "length" last) -- exactly the TD-21.21 hazard.
    # If either call's OWN result below had come from that shared attribute instead of its
    # own getter-scoped meta, A's (the actual last writer) would leak into B's result too.
    assert prims._last_inference_meta.get("completion_reason") == "length"

    assert code_a == "output A"
    assert meta_a["completion_reason"] == "length"
    assert meta_a["tokens"] == 1
    assert code_b == "output B"
    assert meta_b["completion_reason"] == "stop"
    assert meta_b["tokens"] == 2
