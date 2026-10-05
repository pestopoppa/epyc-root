"""WP-12 fleet layer — one breaker fact per (fleet, endpoint).

Acceptance plan coverage (wp12-fleet-layer-design.md §6):
  * case 4 — failures observed via one role's dispatch open THE fleet circuit
    for that endpoint; every bound role observes the same fact; exactly one
    half-open transition per cooldown across all bound roles
  * case 5 (fail-fast half) — with the whole fleet circuit open, dispatch
    fails fast with a circuit-open error instead of burning the poll budget

All offline: stub child backends, mocked lock seam, no sockets.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from src.api.health_tracker import BackendHealthTracker
from src.backends.concurrency_aware import ConcurrencyAwareBackend

WG = "worker_general"
FULL_URL = "http://localhost:8072"
Q0_URL = "http://localhost:8082"
Q1_URL = "http://localhost:8182"


class _StubChild:
    """Offline CachingBackend stand-in: fixed result, never touches sockets."""

    def __init__(self, url: str, result=None):
        self.config = SimpleNamespace(base_url=url)
        self._result = result if result is not None else SimpleNamespace(
            success=True, partial=False
        )

    def infer(self, role_config, request):
        return self._result

    def infer_stream_text(self, role_config, request, on_chunk=None):
        return self._result


_FAILING = SimpleNamespace(success=False, partial=False)
_PARTIAL = SimpleNamespace(success=False, partial=True)


def _legacy_dispatch_env(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "0")
    monkeypatch.delenv("ORCHESTRATOR_PLACEMENT_STATE_MACHINE", raising=False)


# ── Case 4 — one circuit per fleet endpoint, shared by every bound role ─────


def test_case4_failures_via_one_role_open_the_fleet_circuit(monkeypatch):
    """Failures injected through worker_math's dispatch open the circuit for
    the DISPATCHED endpoint; worker_general/toolrunner observe availability
    through the identical tracker fact (no per-role health opinions)."""
    _legacy_dispatch_env(monkeypatch)
    tracker = BackendHealthTracker(failure_threshold=2, cooldown_s=60.0)
    cab = ConcurrencyAwareBackend(
        _StubChild(FULL_URL, result=_FAILING),
        [_StubChild(Q0_URL)],
        role=WG,
        full_port=8072,
        topology_role=WG,
        health_tracker=tracker,
    )
    assert cab.fleet_health_managed

    # worker_math's calls (logical role threaded per-call via request.role).
    req = SimpleNamespace(role="worker_math", session_id="wm-1")
    cab.infer(None, req)
    assert tracker.is_available(FULL_URL)  # 1 failure < threshold
    cab.infer(None, req)

    status = tracker.get_status()
    assert status[FULL_URL]["state"] == "open"
    # ONE fact: any bound role asking about this endpoint sees it down.
    assert tracker.is_available(FULL_URL) is False
    # The fleet is not down — the quarter endpoint is untouched.
    assert Q0_URL not in status or status[Q0_URL]["state"] == "closed"
    assert cab.any_endpoint_available() is True


def test_case4_success_and_partial_policies_mirror_primitives_layer(monkeypatch):
    _legacy_dispatch_env(monkeypatch)
    tracker = BackendHealthTracker(failure_threshold=2, cooldown_s=60.0)
    cab = ConcurrencyAwareBackend(
        _StubChild(FULL_URL, result=_PARTIAL),
        [_StubChild(Q0_URL)],
        role=WG,
        full_port=8072,
        topology_role=WG,
        health_tracker=tracker,
    )
    req = SimpleNamespace(role=WG, session_id="s1")
    # Partial results are neither success nor failure — no circuit movement.
    cab.infer(None, req)
    cab.infer(None, req)
    assert FULL_URL not in tracker.get_status()

    tracker.record_failure(FULL_URL)
    cab._record_endpoint_result(-1, SimpleNamespace(success=True, partial=False))
    assert tracker.get_status()[FULL_URL]["failure_count"] == 0  # success resets


def test_case4_exactly_one_half_open_transition_per_cooldown():
    """After cooldown, the first availability probe (whichever bound role
    makes it) flips open→half-open ONCE; other roles' checks observe the same
    half-open circuit rather than re-transitioning; one success closes it for
    every role."""
    tracker = BackendHealthTracker(failure_threshold=2, cooldown_s=0.05)
    tracker.record_failure(Q0_URL)
    tracker.record_failure(Q0_URL)
    assert tracker.get_status()[Q0_URL]["state"] == "open"
    assert tracker.is_available(Q0_URL) is False

    time.sleep(0.06)
    # "worker_math's" check performs the single open→half-open transition...
    assert tracker.is_available(Q0_URL) is True
    assert tracker.get_status()[Q0_URL]["state"] == "half-open"
    # ..."worker_general"/"toolrunner" checks see the SAME half-open circuit
    # (no second transition, no per-role probe amplification).
    assert tracker.is_available(Q0_URL) is True
    assert tracker.get_status()[Q0_URL]["state"] == "half-open"

    tracker.record_success(Q0_URL)
    assert tracker.get_status()[Q0_URL]["state"] == "closed"
    assert tracker.is_available(Q0_URL) is True


# ── Dispatch-level circuit awareness (SM path) ──────────────────────────────


class _GrantAllLockCtx:
    @contextmanager
    def lock(self, role, idx, **_kw):
        yield [f"/tmp/mock.{role}.{idx}.lock"]


def _wire_sm(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.setenv("ORCHESTRATOR_PLACEMENT_STATE_MACHINE", "1")
    monkeypatch.delenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_SHAPE_AWARE_CONTENTION", raising=False)
    locks = _GrantAllLockCtx()
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.cpu_region_lock_for_instance",
        lambda role, idx, **kw: locks.lock(role, idx),
    )
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.active_region_holders", lambda: {}
    )
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.held_regions_by_role", lambda *_a, **_k: {}
    )


def _quarters_cab(tracker) -> ConcurrencyAwareBackend:
    return ConcurrencyAwareBackend(
        None,
        [_StubChild(Q0_URL), _StubChild(Q1_URL)],
        role=WG,
        full_port=0,
        topology_role=WG,
        quarter_topology_idxs=[1, 2],
        health_tracker=tracker,
    )


def test_case4_dispatch_skips_open_endpoint(monkeypatch):
    """An endpoint whose fleet circuit is open is skipped by placement for
    EVERY bound role — dispatch lands on the healthy sibling."""
    _wire_sm(monkeypatch)
    tracker = BackendHealthTracker(failure_threshold=2, cooldown_s=60.0)
    cab = _quarters_cab(tracker)

    tracker.record_failure(Q0_URL)
    tracker.record_failure(Q0_URL)

    with cab._dispatch(session_id="s1") as (_backend, idx, is_full):
        assert not is_full
        assert idx == 1  # healthy 8182, not the circuit-open 8082


def test_case5_fail_fast_when_whole_fleet_circuit_open(monkeypatch):
    """All endpoints open → the request fails FAST with a circuit-open error
    (classified circuit_open upstream) instead of polling the placement loop;
    the role layer can then consult cross-fleet fallback only."""
    _wire_sm(monkeypatch)
    tracker = BackendHealthTracker(failure_threshold=2, cooldown_s=60.0)
    cab = _quarters_cab(tracker)

    for url in (Q0_URL, Q1_URL):
        tracker.record_failure(url)
        tracker.record_failure(url)
    assert cab.any_endpoint_available() is False

    start = time.perf_counter()
    with pytest.raises(RuntimeError, match="circuit open"):
        with cab._dispatch(session_id="s1"):
            pass
    assert time.perf_counter() - start < 1.0  # fail fast, no poll budget burn

    # classify_failure maps the message to the circuit_open failover reason.
    assert tracker.classify_failure(
        RuntimeError(f"Backend unavailable (circuit open): all endpoints for fleet {WG}")
    ) == "circuit_open"


def test_legacy_construction_has_no_fleet_health(monkeypatch):
    """Byte-identity guard: a CAB constructed the legacy way (no tracker)
    never records endpoint health and never filters candidates."""
    _wire_sm(monkeypatch)
    cab = ConcurrencyAwareBackend(
        None,
        [_StubChild(Q0_URL), _StubChild(Q1_URL)],
        role=WG,
        full_port=0,
        topology_role=WG,
        quarter_topology_idxs=[1, 2],
    )
    assert cab.fleet_health_managed is False
    assert cab.any_endpoint_available() is True
    with cab._dispatch(session_id="s1") as (_backend, idx, _is_full):
        assert idx == 0  # first preference, no availability filtering
