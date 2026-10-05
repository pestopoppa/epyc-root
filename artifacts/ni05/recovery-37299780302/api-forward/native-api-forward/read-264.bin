"""WP-2 integration: ConcurrencyAwareBackend._dispatch + placement state machine.

Validates that when `ORCHESTRATOR_PLACEMENT_STATE_MACHINE=1`:
  * Topology-safe candidates pass through and acquire region locks.
  * When every candidate overlaps in-flight holders, the dispatcher
    polls + re-evaluates instead of falling back to blocking-on-full.
  * On poll timeout, `ContentionDenied` is raised (not `CpuRegionLockTimeout`).

We mock `cpu_region_lock_for_instance` and `active_region_holders` to control
the placement scenario without launching real llama-servers.
"""

from __future__ import annotations

import contextlib
import importlib
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "server"))

ca_mod = importlib.import_module("src.backends.concurrency_aware")


class _StubBackend:
    def __init__(self, url: str = "http://localhost:0"):
        self.config = type("C", (), {"base_url": url})()
        self.url = url


class _FakeLockCtx:
    """Mimics cpu_region_lock_for_instance's context-manager return."""

    def __init__(self, role: str, topo_idx: int, succeed: bool = True):
        self.role = role
        self.topo_idx = topo_idx
        self.succeed = succeed
        self.entered = False

    def __enter__(self):
        if not self.succeed:
            from src.runtime.cpu_region_lock import CpuRegionLockTimeout
            raise CpuRegionLockTimeout(f"mock timeout role={self.role} idx={self.topo_idx}")
        self.entered = True
        return [f"/tmp/cpu_region.{self.role}.mock-{self.topo_idx}.lock"]

    def __exit__(self, *exc):
        self.entered = False
        return False


def _make_backend(monkeypatch: pytest.MonkeyPatch, role: str = "frontdoor"):
    """Build a ConcurrencyAwareBackend with 4 quarters wired to stubs."""
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.setenv("ORCHESTRATOR_PLACEMENT_STATE_MACHINE", "1")
    full = _StubBackend("http://localhost:8070")
    quarters = [_StubBackend(f"http://localhost:80{80 + i * 100}") for i in range(4)]
    return ca_mod.ConcurrencyAwareBackend(
        full_backend=full,
        quarter_backends=quarters,
        role=role,
        full_port=8070,
    )


# Synthetic frontdoor topology — matches the production NUMA_NODE0 shape.
_FRONTDOOR_REGIONS = {
    ("frontdoor", 0): frozenset({"q0", "q1"}),
    ("frontdoor", 1): frozenset({"q0"}),
    ("frontdoor", 2): frozenset({"q1"}),
    ("frontdoor", 3): frozenset({"q2"}),
    ("frontdoor", 4): frozenset({"q3"}),
}


def test_eval_batch_uses_certified_shared_full_lease(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.setenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "1")
    full = _StubBackend("http://localhost:8070")
    backend = ca_mod.ConcurrencyAwareBackend(
        full_backend=full,
        quarter_backends=[_StubBackend("http://localhost:8080")],
        role="frontdoor",
        full_port=8070,
        native_batch_width=4,
    )
    calls: list[dict] = []

    @contextlib.contextmanager
    def fake_region_lock(role, instance_idx, **kwargs):
        calls.append({"role": role, "instance_idx": instance_idx, **kwargs})
        yield {"q0": Path("/tmp/q0")}

    from src.runtime import cpu_region_lock

    monkeypatch.setattr(cpu_region_lock, "cpu_region_lock_for_instance", fake_region_lock)
    request = SimpleNamespace(
        workload_class="eval_batch", batch_id="t1-batch", timeout=1200
    )

    with backend._dispatch(request=request) as (selected, idx, is_full):
        assert selected is full
        assert idx == -1
        assert is_full is True

    assert calls == [
        {
            "role": "frontdoor",
            "instance_idx": 0,
            "timeout_s": 1200.0,
            "request_tag": "t1-batch",
            "shared": True,
            "capacity": 4,
        }
    ]


def test_mixed_role_eval_bypasses_native_full_and_starts_split(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.setenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "1")
    full = _StubBackend("http://localhost:8070")
    split = _StubBackend("http://localhost:8080")
    backend = ca_mod.ConcurrencyAwareBackend(
        full_backend=full,
        quarter_backends=[split],
        role="frontdoor",
        full_port=8070,
        native_batch_width=4,
    )
    calls: list[dict] = []

    @contextlib.contextmanager
    def fake_region_lock(role, instance_idx, **kwargs):
        calls.append({"role": role, "instance_idx": instance_idx, **kwargs})
        yield {"q0": Path("/tmp/q0")}

    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.cpu_region_lock_for_instance", fake_region_lock
    )
    request = SimpleNamespace(
        workload_class="eval_batch",
        batch_id="t1-mixed",
        batch_placement_mode="mixed_role_split",
        timeout=1200,
    )

    with backend._dispatch(request=request) as (selected, idx, is_full):
        assert selected is split
        assert idx == 0
        assert is_full is False

    assert calls[0]["instance_idx"] == 1
    assert calls[0].get("shared") is not True


def test_dispatcher_uses_topology_safe_candidate_when_full_held(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Full is in-flight (holder=[0]); dispatcher should skip q0/q1 (overlap)
    and acquire one of q2/q3 (disjoint)."""
    backend = _make_backend(monkeypatch)
    acquired_idxs: list[int] = []

    def _mock_lock(role, instance_idx, timeout_s=None, deadline_s=None):
        # full(0) is "held" — its lock attempt times out. Quarters succeed.
        succeed = (instance_idx != 0)
        if succeed:
            acquired_idxs.append(instance_idx)
        return _FakeLockCtx(role, instance_idx, succeed=succeed)

    monkeypatch.setattr("src.runtime.cpu_region_lock.cpu_region_lock_for_instance", _mock_lock)
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.active_region_holders",
        lambda: {"frontdoor": [0]},
    )
    # The dispatcher's placement filter reads the EXACT held-region set. Full
    # (idx 0) genuinely decoding == its regions {q0, q1} held.
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.held_regions_by_role",
        lambda *a, **k: {"frontdoor": frozenset({"q0", "q1"})},
    )
    monkeypatch.setattr(
        "src.runtime.instance_topology.get_instance_regions",
        lambda: _FRONTDOOR_REGIONS,
    )

    with backend._dispatch(session_id="s1") as (chosen_backend, idx, is_full):
        assert is_full is False
        # The chosen quarter should be from the disjoint set (topo 3 or 4 — q2/q3).
        assert acquired_idxs[-1] in (3, 4)
        assert idx in (2, 3)  # internal idx for q2/q3


def test_dispatcher_queues_when_all_candidates_overlap_then_succeeds_after_release(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All regions in use → first eval queues → re-poll after holders shrink → succeeds."""
    backend = _make_backend(monkeypatch)

    # First call: all 4 atomic regions covered by holders ⇒ every candidate overlaps.
    # After 1 poll: holders drop (q3 released) so q3 becomes safe.
    holder_state = {"calls": 0, "current": {"frontdoor": [0, 3, 4]}}

    def _holders():
        holder_state["calls"] += 1
        if holder_state["calls"] >= 2:
            holder_state["current"] = {"frontdoor": [0, 3]}  # q2 released → q3 still has q2 free? no: drop q3 idx
            holder_state["current"] = {"frontdoor": [0, 3]}  # q2's topo idx is 3; q3's topo idx is 4 — release q3 → topo 4 gone
            return {"frontdoor": [0, 3]}  # q3 (topo 4) released → safe
        return holder_state["current"]

    def _mock_lock(role, instance_idx, timeout_s=None, deadline_s=None):
        # full(0) and q0(1),q1(2) always overlap holders; q2(3) overlaps holder q2 (topo 3);
        # q3(4) becomes acquirable on second eval.
        return _FakeLockCtx(role, instance_idx, succeed=(instance_idx == 4))

    def _held():
        # EXACT held-region view derived from the same holder-idx state the
        # dispatcher's placement filter now consumes.
        idxs = holder_state["current"].get("frontdoor", [])
        acc: set[str] = set()
        for i in idxs:
            acc |= _FRONTDOOR_REGIONS.get(("frontdoor", i), frozenset())
        return {"frontdoor": frozenset(acc)} if acc else {}

    monkeypatch.setattr("src.runtime.cpu_region_lock.cpu_region_lock_for_instance", _mock_lock)
    monkeypatch.setattr("src.runtime.cpu_region_lock.active_region_holders", _holders)
    monkeypatch.setattr("src.runtime.cpu_region_lock.held_regions_by_role", lambda *a, **k: _held())
    monkeypatch.setattr(
        "src.runtime.instance_topology.get_instance_regions",
        lambda: _FRONTDOOR_REGIONS,
    )

    start = time.perf_counter()
    with backend._dispatch(session_id="s2") as (chosen_backend, idx, is_full):
        elapsed = time.perf_counter() - start
        assert is_full is False
        assert idx == 3  # q3 internal idx
        # Must have polled at least once (each poll = 150ms; we expect 1-2 polls).
        assert elapsed >= 0.150
        assert holder_state["calls"] >= 2


def test_dispatcher_raises_contention_denied_on_poll_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When no safe candidate ever appears, the poll loop times out at 60s.
    To keep the test fast, we patch the deadline to elapse immediately."""
    backend = _make_backend(monkeypatch)

    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.active_region_holders",
        lambda: {"frontdoor": [0, 1, 2, 3, 4]},  # all instances "held"
    )
    # EXACT held-region view: every atomic region is occupied → no safe candidate.
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.held_regions_by_role",
        lambda *a, **k: {"frontdoor": frozenset({"q0", "q1", "q2", "q3"})},
    )
    monkeypatch.setattr(
        "src.runtime.instance_topology.get_instance_regions",
        lambda: _FRONTDOOR_REGIONS,
    )

    # Make the poll deadline elapse immediately by patching time.perf_counter.
    times = iter([0.0, 0.0, 100.0])  # first two calls return 0, third returns 100s
    monkeypatch.setattr("src.backends.concurrency_aware.time.perf_counter", lambda: next(times))
    monkeypatch.setattr("src.backends.concurrency_aware.time.sleep", lambda _x: None)

    from src.scheduling.contention_gate import ContentionDenied
    with pytest.raises(ContentionDenied) as exc_info:
        with backend._dispatch(session_id="s3"):
            pass
    assert "placement timeout" in str(exc_info.value)
    assert "frontdoor" in str(exc_info.value)
    assert exc_info.value.provenance()["class"] == "admission_denied"
    assert exc_info.value.provenance()["code"] == "placement_topology_overlap_timeout"


def test_dispatcher_marks_only_lock_snapshot_races_as_race_lost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed non-blocking acquire after a safe placement is a real race.

    This is deliberately distinct from a topology queue timeout: only this
    situation carries the E8-eligible ``admission_timeout/race_lost`` pair.
    """
    backend = _make_backend(monkeypatch)
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.active_region_holders", lambda: {}
    )
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.held_regions_by_role", lambda *a, **k: {}
    )
    monkeypatch.setattr(
        "src.runtime.instance_topology.get_instance_regions",
        lambda: _FRONTDOOR_REGIONS,
    )
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.cpu_region_lock_for_instance",
        lambda role, idx, **kwargs: _FakeLockCtx(role, idx, succeed=False),
    )
    times = iter([0.0, 100.0])
    monkeypatch.setattr(
        "src.backends.concurrency_aware.time.perf_counter", lambda: next(times)
    )
    monkeypatch.setattr("src.backends.concurrency_aware.time.sleep", lambda _x: None)

    request = type(
        "Request", (), {"workload_class": "quality_baseline", "max_queue_wait_ms": 250}
    )()
    from src.scheduling.contention_gate import ContentionDenied

    with pytest.raises(ContentionDenied) as exc_info:
        with backend._dispatch(session_id="race", request=request):
            pass

    provenance = exc_info.value.provenance()
    assert provenance["class"] == "admission_timeout"
    assert provenance["code"] == "race_lost"
    assert provenance["role"] == "frontdoor"
    assert provenance["workload_class"] == "quality_baseline"
    assert provenance["max_queue_wait_ms"] == 250


def test_dispatcher_legacy_path_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ORCHESTRATOR_PLACEMENT_STATE_MACHINE is not set, the legacy
    greedy try-loop + blocking-on-full fallback runs unchanged."""
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.delenv("ORCHESTRATOR_PLACEMENT_STATE_MACHINE", raising=False)

    full = _StubBackend("http://localhost:8070")
    quarters = [_StubBackend(f"http://localhost:80{80 + i * 100}") for i in range(4)]
    backend = ca_mod.ConcurrencyAwareBackend(
        full_backend=full, quarter_backends=quarters, role="frontdoor", full_port=8070,
    )

    # In legacy path, full's try-acquire succeeds → no quarter attempt needed.
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.cpu_region_lock_for_instance",
        lambda role, idx, **kw: _FakeLockCtx(role, idx, succeed=(idx == 0)),
    )

    with backend._dispatch(session_id="s_legacy") as (chosen_backend, idx, is_full):
        assert is_full is True
        assert idx == -1


# ── DISPATCH-A: placement_policy governs the full (all-region) candidate ──────

# Lineup-independence (2026-09-26). The DISPATCH-A cases below used to pin
# worker_general as its own fleet (NUMA_CONFIG["worker_general"], full :8072,
# quarters :8082..:8382). The operator-signed 2026-09-22 lineup cutover
# (orchestrator 860b0b2d) made worker_general an ALIAS of frontdoor's :8070
# fleet and deleted its NUMA_CONFIG entry (KeyError). The fleet is now DERIVED:
# worker_general's host from orchestration/model_registry.yaml server_mode, its
# aligned idx-0 full port from NUMA_CONFIG. The dispatch identity (role /
# topology_role) is that host, exactly as the fleet layer builds it.


def _registry_server_mode() -> dict:
    import yaml

    return yaml.safe_load(
        (ROOT / "orchestration" / "model_registry.yaml").read_text(encoding="utf-8")
    )["server_mode"]


def _host_fleet_of(role: str) -> str:
    """The server_mode row that physically hosts ``role`` (shared_with/alias_of)."""
    for host, row in _registry_server_mode().items():
        if row.get("alias_of"):
            continue
        if host == role or role in (row.get("shared_with") or []):
            return host
    raise AssertionError(f"registry declares no host fleet for {role!r}")


def _full_port(role: str) -> int:
    import scripts.server.stack_numa as _stack_numa

    return int(_stack_numa.NUMA_CONFIG[role]["instances"][0][1])


WG_HOST = _host_fleet_of("worker_general")
WG_HOST_FULL = _full_port(WG_HOST)
# SYNTHETIC quarter endpoints: no live fleet carries four quarters since the
# 2026-07-30 retirement. They dispatch at positional topology idxs 1..4, which
# _WORKER_GENERAL_REGIONS below maps to one region each.
_SYNTH_QUARTER_PORTS = [WG_HOST_FULL + 11000 + i for i in range(4)]

# The host fleet's topology, SYNTHETIC 1 full + 4 quarters shape: full (idx 0)
# = "0-95" = ALL regions; the four quarters each occupy exactly one region. A
# request routed to idx 0 acquires every region lock (+ every global cross-role
# mutex) — the DISPATCH-A amplifier. Installed via get_instance_regions mocks.
_WORKER_GENERAL_REGIONS = {
    (WG_HOST, 0): frozenset({"q0", "q1", "q2", "q3"}),  # full = 0-95
    (WG_HOST, 1): frozenset({"q0"}),
    (WG_HOST, 2): frozenset({"q1"}),
    (WG_HOST, 3): frozenset({"q2"}),
    (WG_HOST, 4): frozenset({"q3"}),
}


class _HeldLockCtx:
    """Lock ctx that records the topology idx as held for the lifetime of the
    dispatch context (added on __enter__, removed on __exit__) so nested
    concurrent dispatches see each other's occupancy."""

    def __init__(self, held: set[int], topo_idx: int):
        self._held = held
        self.topo_idx = topo_idx

    def __enter__(self):
        self._held.add(self.topo_idx)
        return [f"/tmp/cpu_region.mock-{self.topo_idx}.lock"]

    def __exit__(self, *exc):
        self._held.discard(self.topo_idx)
        return False


def test_full_disabled_places_four_concurrent_on_four_quarters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DISPATCH-A (a): a FULL_DISABLED fleet (its full is not in the serving
    stack). Four concurrent same-role requests must occupy four DISTINCT
    quarters; the all-region idx-0 lock is NEVER attempted (big instance stays
    idle) — the design-contract acceptance.

    SYNTHETIC policy + shape on the LIVE host of worker_general (WG_HOST): no
    live fleet is full_disabled or carries four quarters, so both are injected
    (policy via NUMA_CONFIG[WG_HOST], regions via get_instance_regions)."""
    from src.scheduling.placement_policy import (
        RolePlacementPolicy,
        get_placement_policy,
    )

    # The live host policy is burst_prefer_split (see
    # test_worker_general_live_policy_is_burst_prefer_split). This test keeps
    # pinning the DISPATCH-A fix for the FULL_DISABLED policy itself, so the
    # policy is monkeypatched onto the host rather than read from live config.
    import scripts.server.stack_numa as _stack_numa

    monkeypatch.setitem(
        _stack_numa.NUMA_CONFIG[WG_HOST], "placement_policy", "full_disabled"
    )
    assert get_placement_policy(WG_HOST) is RolePlacementPolicy.FULL_DISABLED

    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.setenv("ORCHESTRATOR_PLACEMENT_STATE_MACHINE", "1")
    full = _StubBackend(f"http://localhost:{WG_HOST_FULL}")
    quarters = [_StubBackend(f"http://localhost:{p}") for p in _SYNTH_QUARTER_PORTS]
    backend = ca_mod.ConcurrencyAwareBackend(
        full_backend=full, quarter_backends=quarters,
        role=WG_HOST, full_port=WG_HOST_FULL,  # aligned idx-0 port
    )
    assert backend._full_slot_aligned is True  # full is a real candidate the policy must drop

    held: set[int] = set()
    attempted: list[int] = []

    def _mock_lock(role, instance_idx, timeout_s=None, deadline_s=None):
        attempted.append(instance_idx)
        if instance_idx in held:
            return _FakeLockCtx(role, instance_idx, succeed=False)  # non-blocking miss
        return _HeldLockCtx(held, instance_idx)

    monkeypatch.setattr("src.runtime.cpu_region_lock.cpu_region_lock_for_instance", _mock_lock)
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.active_region_holders",
        lambda: {WG_HOST: sorted(held)},
    )
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.held_regions_by_role",
        lambda *args, **kwargs: {
            WG_HOST: frozenset().union(
                *(_WORKER_GENERAL_REGIONS[(WG_HOST, idx)] for idx in held)
            )
            if held
            else frozenset(),
        },
    )
    monkeypatch.setattr(
        "src.runtime.instance_topology.get_instance_regions",
        lambda: dict(_WORKER_GENERAL_REGIONS),
    )

    chosen_topos: list[int] = []
    with contextlib.ExitStack() as stack:
        for i in range(4):
            _b, idx, is_full = stack.enter_context(backend._dispatch(session_id=f"wg{i}"))
            assert is_full is False
            chosen_topos.append(0 if idx == -1 else idx + 1)

    assert sorted(chosen_topos) == [1, 2, 3, 4]  # four distinct quarters
    assert 0 not in attempted  # all-region idx-0 lock never acquired


def test_worker_general_live_policy_is_burst_prefer_split() -> None:
    """Live-policy pin: worker_general dispatches on its registry host fleet
    (frontdoor's since the 2026-09-22 cutover), and the dispatcher resolves the
    policy by that TOPOLOGY role, so the host's live policy is what worker_general
    gets: BURST_PREFER_SPLIT — solo gets the full for peak throughput, bursts
    spread on split instances. A revert to full_disabled must be a deliberate
    config change, not drift."""
    from src.scheduling.placement_policy import (
        RolePlacementPolicy,
        get_placement_policy,
    )

    assert "worker_general" in (_registry_server_mode()[WG_HOST].get("shared_with") or [])
    assert get_placement_policy(WG_HOST) is RolePlacementPolicy.BURST_PREFER_SPLIT


def test_burst_prefer_split_solo_request_goes_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DISPATCH-A (b1): BURST_PREFER_SPLIT with ZERO same-role holders →
    single-request mode routes to the full instance for peak latency."""
    backend = _make_backend(monkeypatch, role="frontdoor")  # full_port 8070 (aligned)
    acquired: list[int] = []

    def _mock_lock(role, instance_idx, timeout_s=None, deadline_s=None):
        acquired.append(instance_idx)
        return _FakeLockCtx(role, instance_idx, succeed=True)

    monkeypatch.setattr("src.runtime.cpu_region_lock.cpu_region_lock_for_instance", _mock_lock)
    monkeypatch.setattr("src.runtime.cpu_region_lock.active_region_holders", lambda: {})
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.held_regions_by_role", lambda *args, **kwargs: {}
    )
    # Third seam (570200ff): without this patch the test reads LIVE host lock
    # state — a real frontdoor decode holding q0 flips is_full to False
    # (deterministically reproduced by the WP-12 session, 2026-07-23). Siblings
    # patch all three seams; this one must too.
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.held_regions_by_role", lambda *a, **k: {}
    )
    monkeypatch.setattr(
        "src.runtime.instance_topology.get_instance_regions",
        lambda: dict(_FRONTDOOR_REGIONS),
    )

    with backend._dispatch(session_id="solo") as (_b, idx, is_full):
        assert is_full is True
        assert idx == -1
        assert acquired[-1] == 0  # full (topology idx 0)


def test_burst_prefer_split_under_load_prefers_split_over_free_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DISPATCH-A (b2): BURST_PREFER_SPLIT with a same-role holder present →
    the router prefers a split instance EVEN THOUGH the full is free and disjoint
    from the held split instance. A full-first policy would grab the free full; this
    proves mode abandonment under concurrent load."""
    backend = _make_backend(monkeypatch, role="frontdoor")
    acquired: list[int] = []

    def _mock_lock(role, instance_idx, timeout_s=None, deadline_s=None):
        acquired.append(instance_idx)
        return _FakeLockCtx(role, instance_idx, succeed=True)

    monkeypatch.setattr("src.runtime.cpu_region_lock.cpu_region_lock_for_instance", _mock_lock)
    # q2 (topo idx 3, region {q2}) is in flight. frontdoor full (topo 0 = {q0,q1})
    # is DISJOINT from {q2} and free → a full-first policy would take it.
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.active_region_holders",
        lambda: {"frontdoor": [3]},
    )
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.held_regions_by_role",
        lambda *a, **k: {"frontdoor": frozenset({"q2"})},
    )
    monkeypatch.setattr(
        "src.runtime.instance_topology.get_instance_regions",
        lambda: dict(_FRONTDOOR_REGIONS),
    )

    with backend._dispatch(session_id="s_load") as (_b, idx, is_full):
        assert is_full is False  # NOT the full, despite it being free+disjoint
        assert idx != -1
        assert acquired[-1] != 0  # full (topo 0) never acquired


def test_full_slot_port_mismatch_skips_full_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DISPATCH-A (c): an endpoint wired as `full:` whose port is NOT the role's
    NUMA_CONFIG idx-0 port is a quarter impersonating the full. The alignment
    guard disables the full candidate so the all-region idx-0 lock is never
    grabbed — even in single-request (solo) mode where full would be preferred."""
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.setenv("ORCHESTRATOR_PLACEMENT_STATE_MACHINE", "1")
    full = _StubBackend("http://localhost:9999")
    quarters = [_StubBackend(f"http://localhost:80{80 + i * 100}") for i in range(4)]
    backend = ca_mod.ConcurrencyAwareBackend(
        full_backend=full, quarter_backends=quarters,
        role="frontdoor", full_port=9999,  # NOT frontdoor idx-0 (8070)
    )
    assert backend._full_slot_aligned is False

    acquired: list[int] = []

    def _mock_lock(role, instance_idx, timeout_s=None, deadline_s=None):
        acquired.append(instance_idx)
        return _FakeLockCtx(role, instance_idx, succeed=True)

    monkeypatch.setattr("src.runtime.cpu_region_lock.cpu_region_lock_for_instance", _mock_lock)
    monkeypatch.setattr("src.runtime.cpu_region_lock.active_region_holders", lambda: {})
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.held_regions_by_role",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(
        "src.runtime.instance_topology.get_instance_regions",
        lambda: dict(_FRONTDOOR_REGIONS),
    )

    with backend._dispatch(session_id="s_mismatch") as (_b, idx, is_full):
        assert is_full is False  # never the mislabeled full
        assert idx != -1
        assert 0 not in acquired  # all-region idx-0 lock never attempted


# ── DISPATCH-A residual serializer regression (attribution over-report) ───────
#
# The DISPATCH-A tests above mock `active_region_holders` with CLEAN idx lists
# and therefore never reproduce the production ATTRIBUTION view: when only
# physical region q0 is held, `active_region_holders` reports EVERY instance
# whose region-set contains q0 — including the all-region `full` (idx 0). The
# placement filter used to expand those idxs to a region union, which a single
# held quarter inflated to the WHOLE machine, so every disjoint quarter was
# QUEUED and concurrent same-role traffic serialized onto ONE quarter. The fix
# feeds the filter the EXACT held-region set (`held_regions_by_role`). This test
# uses a FAITHFUL attribution model so it fails on the pre-fix code and pins the
# spread.


class _AttributionLockModel:
    """Faithful host-fleet (WG_HOST) lock layer: tracks held physical regions and
    reproduces BOTH the attribution over-report (active_region_holders) and the
    exact region view (held_regions_by_role)."""

    def __init__(self, regions_map: dict):
        self.regions_map = regions_map          # (role, topo_idx) -> frozenset(regions)
        self.owner: dict[str, int] = {}          # region -> owning topo_idx

    def active_region_holders(self, *a, **k) -> dict[str, list[int]]:
        # ATTRIBUTION: an instance is "active" if ANY of its regions is held —
        # so a single held q0 flags the all-region full (idx 0) too.
        idxs = sorted(
            idx
            for (role, idx), regions in self.regions_map.items()
            if role == WG_HOST and any(r in self.owner for r in regions)
        )
        return {WG_HOST: idxs} if idxs else {}

    def held_regions_by_role(self, *a, **k) -> dict[str, frozenset[str]]:
        return {WG_HOST: frozenset(self.owner)} if self.owner else {}

    def lock(self, role, instance_idx, timeout_s=None, deadline_s=None):
        regions = self.regions_map.get((role, instance_idx), frozenset())
        model = self

        class _Ctx:
            def __enter__(self_ctx):
                for rg in regions:
                    if model.owner.get(rg, instance_idx) != instance_idx:
                        from src.runtime.cpu_region_lock import CpuRegionLockTimeout

                        raise CpuRegionLockTimeout(f"region {rg} held")
                for rg in regions:
                    model.owner[rg] = instance_idx
                return [f"/tmp/cpu_region.mock.{role}.{instance_idx}.lock"]

            def __exit__(self_ctx, *exc):
                for rg in regions:
                    if model.owner.get(rg) == instance_idx:
                        del model.owner[rg]
                return False

        return _Ctx()


def test_full_disabled_four_concurrent_spread_despite_attribution_over_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DISPATCH-A residual pin: 4 concurrent same-fleet (FULL_DISABLED)
    dispatches must occupy 4 DISTINCT quarters even though the attribution view
    reports the phantom full (idx 0) as a holder the moment one quarter is held.
    Pre-fix, the placement filter expanded [0, ...] to the whole-machine union
    and QUEUED every disjoint quarter → serialization onto one quarter.

    Runs on worker_general's LIVE host fleet with a SYNTHETIC full_disabled
    policy and 1 full + 4 quarters shape (see the note in
    test_full_disabled_places_four_concurrent_on_four_quarters)."""
    from types import SimpleNamespace

    import scripts.server.stack_numa as _stack_numa

    monkeypatch.setitem(
        _stack_numa.NUMA_CONFIG[WG_HOST], "placement_policy", "full_disabled"
    )

    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.setenv("ORCHESTRATOR_PLACEMENT_STATE_MACHINE", "1")
    # Isolate the placement filter: cross-role + shape-aware seam OFF.
    monkeypatch.delenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_SHAPE_AWARE_CONTENTION", raising=False)

    full = _StubBackend(f"http://localhost:{WG_HOST_FULL}")
    quarters = [_StubBackend(f"http://localhost:{p}") for p in _SYNTH_QUARTER_PORTS]
    backend = ca_mod.ConcurrencyAwareBackend(
        full_backend=full, quarter_backends=quarters,
        role=WG_HOST, full_port=WG_HOST_FULL,  # aligned; FULL_DISABLED drops full anyway
    )

    model = _AttributionLockModel(dict(_WORKER_GENERAL_REGIONS))
    monkeypatch.setattr(
        "src.runtime.instance_topology.get_instance_regions",
        lambda: dict(_WORKER_GENERAL_REGIONS),
    )
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.active_region_holders", model.active_region_holders
    )
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.held_regions_by_role", model.held_regions_by_role
    )
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.cpu_region_lock_for_instance", model.lock
    )

    # Bounded queue budget: a regression (attribution-driven QUEUE) times out
    # fast into ContentionDenied instead of hanging the suite for 60s.
    req = SimpleNamespace(request_priority="background", max_queue_wait_ms=600)

    chosen_topos: list[int] = []
    with contextlib.ExitStack() as stack:
        for i in range(4):
            _b, idx, is_full = stack.enter_context(
                backend._dispatch(session_id=f"wg{i}", request=req)
            )
            assert is_full is False
            chosen_topos.append(0 if idx == -1 else idx + 1)
        # Assert WHILE all four contexts are still held (locks release on exit).
        assert sorted(chosen_topos) == [1, 2, 3, 4]  # four DISTINCT quarters, not serialized
        assert 0 not in model.owner.values()          # all-region full never acquired
        assert len(model.owner) == 4                   # exactly the four disjoint regions held
