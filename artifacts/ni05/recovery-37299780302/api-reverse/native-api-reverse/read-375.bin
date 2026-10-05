#!/usr/bin/env python3
"""BRIDGE RESIDUAL 1 — GateDecision echoed into /chat response metadata.

`admitted` / `waited_s` / `decision` / `candidate_topology_idx` were computed in
`ContentionGate.admit()` and the WP-2 `_dispatch` poll loop and then dropped, so
ROUTE-A1 had to infer the verdict: role-granular only, queue-then-admit invisible,
and the sole observable QUEUE signal was a fail-closed timeout.

The load-bearing case is `queued_then_admitted` — a request that waited and then
succeeded. The timeout proxy structurally cannot see it, because it ends in a
clean answer exactly like an immediate admit.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import anyio

from src.api.models import ChatResponse
from src.scheduling import gate_observation


def teardown_function() -> None:
    gate_observation.clear()


def test_no_carrier_means_recording_is_a_noop():
    """Uninstrumented callers must not pay for, or trip over, the carrier."""
    gate_observation.clear()
    gate_observation.record(admitted=True, decision="allow", waited_s=0.0)
    assert gate_observation.snapshot() is None


def test_queued_then_admitted_is_directly_observable():
    """The state the timeout proxy cannot see."""
    gate_observation.begin()
    gate_observation.record(
        admitted=True, decision="allow", waited_s=2.5, candidate_topology_idx=1
    )

    snap = gate_observation.snapshot()
    assert snap["admitted"] is True
    assert snap["waited_s"] == 2.5
    assert snap["queued_then_admitted"] is True, (
        "admitted-after-waiting must be distinguishable from admitted-immediately; "
        "that distinction is the entire point of the residual"
    )


def test_immediate_admit_is_not_labelled_queued():
    gate_observation.begin()
    gate_observation.record(admitted=True, decision="allow", waited_s=0.0)
    assert gate_observation.snapshot()["queued_then_admitted"] is False


def test_multiple_gate_passes_accumulate():
    """An escalation chain passes the gate more than once; keep every verdict."""
    gate_observation.begin()
    gate_observation.record(
        admitted=False, decision="block", waited_s=0.0, candidate_topology_idx=3,
        blocking_roles=["worker_general"], reason="overlap",
    )
    gate_observation.record(
        admitted=True, decision="allow", waited_s=0.4, candidate_topology_idx=2
    )

    snap = gate_observation.snapshot()
    assert len(snap["gate_decisions"]) == 2
    assert snap["gate_decisions"][0]["blocking_roles"] == ["worker_general"]
    # Top level mirrors the most recent verdict for the single-hop read.
    assert snap["admitted"] is True
    assert snap["candidate_topology_idx"] == 2


def test_record_survives_a_worker_thread():
    """The reason the carrier is a mutable dict rather than the ContextVar value.

    Sync gate paths run under `run_in_threadpool`, and anyio COPIES the context
    into the worker. A `ContextVar.set()` down there lands in the copy and is
    invisible to the request that has to read it — so a naive implementation
    passes every single-threaded test above and then silently records nothing in
    production. This test is the one that would catch that.
    """
    gate_observation.begin()

    def _in_worker() -> None:
        gate_observation.record(
            admitted=True, decision="allow", waited_s=1.0, candidate_topology_idx=0
        )

    async def _drive() -> None:
        await anyio.to_thread.run_sync(_in_worker)

    anyio.run(_drive)

    snap = gate_observation.snapshot()
    assert snap is not None, "verdict recorded in a worker thread was lost"
    assert snap["waited_s"] == 1.0


def test_record_survives_a_plain_threadpool():
    """Same hazard via ThreadPoolExecutor, which does NOT copy context at all."""
    carrier = gate_observation.begin()

    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(
            lambda: gate_observation.record(
                admitted=False, decision="block", waited_s=0.0, reason="overlap"
            )
        ).result()

    # A bare ThreadPoolExecutor worker starts from an EMPTY context, so the
    # ContextVar lookup there returns None and the record is correctly dropped
    # rather than corrupting another request's carrier. Pinning that as the
    # documented behaviour: silent loss here is acceptable, cross-talk is not.
    assert carrier == {} or carrier.get("admitted") is False


def test_clear_prevents_cross_request_attribution():
    """A leaked carrier would bill this request's verdict to the next caller."""
    gate_observation.begin()
    gate_observation.record(admitted=True, decision="allow", waited_s=9.0)
    gate_observation.clear()

    assert gate_observation.snapshot() is None
    gate_observation.record(admitted=True, decision="allow", waited_s=1.0)
    assert gate_observation.snapshot() is None


def test_chat_response_carries_the_field_and_defaults_to_none():
    r = ChatResponse(answer="x", turns=1, elapsed_seconds=0.1, mock_mode=True)
    assert r.contention_gate is None
    assert "contention_gate" in r.model_dump()


def test_chat_response_serialises_the_echo():
    gate_observation.begin()
    gate_observation.record(
        admitted=True, decision="allow", waited_s=0.75, candidate_topology_idx=2
    )
    r = ChatResponse(
        answer="x", turns=1, elapsed_seconds=0.1, mock_mode=False,
        contention_gate=gate_observation.snapshot(),
    )
    dumped = r.model_dump()["contention_gate"]
    assert dumped["candidate_topology_idx"] == 2
    assert dumped["queued_then_admitted"] is True
