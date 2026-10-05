"""Part A dispatch-level integration: ConcurrencyAwareBackend._dispatch with
ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT.

The pure `evaluate_placement` cross-role tests live in test_placement.py. This
file proves the behavior the FLAG actually ships: that `_dispatch` passes the
FULL active_region_holders() map (not just self-role) into evaluate_placement
when the flag is on, so a role lands on a quarter disjoint from ANOTHER role's
in-flight node-half — and that with the flag off, the cross-role holder is
invisible (legacy behaviour: full chosen first).

Mock seams mirror test_dispatch_placement_state_machine.py: _dispatch imports
active_region_holders / get_instance_regions / cpu_region_lock_for_instance
function-locally from their SOURCE modules, so patch them there.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "server"))

ca_mod = importlib.import_module("src.backends.concurrency_aware")
contention = importlib.import_module("src.scheduling.contention")


# Lineup-independence (2026-09-26). This file used to name two cross-role
# partners that no longer exist as CPU fleets: ingest_long_context (a node0-half
# holder) and worker_general (an all-region "0-95" full + 4 quarters). The
# operator-signed 2026-09-22 lineup cutover (orchestrator 860b0b2d) made
# worker_general an ALIAS of frontdoor's fleet — i.e. not a cross-role partner
# of frontdoor at all — and ingest_long_context an alias of the GPU
# architect_general, deleting both NUMA_CONFIG entries (KeyError). The partners
# are now DERIVED from the live NUMA_CONFIG topology, by the SHAPE each case
# needs, among CPU fleets that are not frontdoor's own:
#   * _HALF_HOLDER — a fleet whose idx-0 instance is exactly a node0 half;
#   * _XR          — a fleet whose idx-0 full spans ALL regions (the amplifier).
# Only their idx-0 shape is live; the extra quarters the cases dispatch on are
# SYNTHETIC (no live fleet carries quarters since the 2026-07-30 retirement).

_ALL_REGIONS = frozenset({"q0", "q1", "q2", "q3"})
_NODE0_HALF = frozenset({"q0", "q1"})


def _registry_server_mode() -> dict:
    import yaml

    return yaml.safe_load(
        (ROOT / "orchestration" / "model_registry.yaml").read_text(encoding="utf-8")
    )["server_mode"]


def _frontdoor_fleet() -> set[str]:
    """frontdoor plus every role the registry binds onto its process."""
    mode = _registry_server_mode()
    bound = {"frontdoor", *(mode["frontdoor"].get("shared_with") or [])}
    bound |= {k for k, v in mode.items() if v.get("alias_of") == "frontdoor"}
    return bound


def _cpu_partner_with_full_shape(shape: frozenset) -> str:
    """First (sorted) live CPU fleet, not frontdoor's, whose idx-0 regions == shape."""
    from scripts.server.stack_numa import NUMA_CONFIG
    from src.runtime.instance_topology import build_instance_regions
    from src.scheduling.device_model import DeviceClass, resolve_role_device

    live = build_instance_regions(NUMA_CONFIG)
    fd_fleet = _frontdoor_fleet()
    for role in sorted(NUMA_CONFIG):
        if role in fd_fleet or live.get((role, 0)) != shape:
            continue
        if resolve_role_device(role).device_class is DeviceClass.CPU:
            return role
    raise AssertionError(f"no live CPU cross-role fleet with idx-0 shape {sorted(shape)}")


def _full_port(role: str) -> int:
    from scripts.server.stack_numa import NUMA_CONFIG

    return int(NUMA_CONFIG[role]["instances"][0][1])


_HALF_HOLDER = _cpu_partner_with_full_shape(_NODE0_HALF)
_XR = _cpu_partner_with_full_shape(_ALL_REGIONS)


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

    def __enter__(self):
        if not self.succeed:
            from src.runtime.cpu_region_lock import CpuRegionLockTimeout

            raise CpuRegionLockTimeout(f"mock timeout role={self.role} idx={self.topo_idx}")
        return [f"/tmp/cpu_region.{self.role}.mock-{self.topo_idx}.lock"]

    def __exit__(self, *exc):
        return False


# frontdoor (SYNTHETIC shape): full(0)={q0,q1} (node0-half), quarters topo
# 1..4 = q0..q3. _HALF_HOLDER full(0) = its LIVE node0 half — the cross-role
# holder to avoid.
_REGIONS = {
    ("frontdoor", 0): frozenset({"q0", "q1"}),
    ("frontdoor", 1): frozenset({"q0"}),
    ("frontdoor", 2): frozenset({"q1"}),
    ("frontdoor", 3): frozenset({"q2"}),
    ("frontdoor", 4): frozenset({"q3"}),
    (_HALF_HOLDER, 0): _NODE0_HALF,
}
# frontdoor topo idxs disjoint from the holder's half (q2/q3 → topo 3/4).
_DISJOINT_FROM_HOLDER = sorted(
    idx for (role, idx), rg in _REGIONS.items() if role == "frontdoor" and rg.isdisjoint(_NODE0_HALF)
)


def _make_frontdoor_backend(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.setenv("ORCHESTRATOR_PLACEMENT_STATE_MACHINE", "1")
    full = _StubBackend("http://localhost:8070")
    quarters = [_StubBackend(f"http://localhost:80{80 + i * 100}") for i in range(4)]
    return ca_mod.ConcurrencyAwareBackend(
        full_backend=full,
        quarter_backends=quarters,
        role="frontdoor",
        full_port=8070,
    )


def _wire(monkeypatch: pytest.MonkeyPatch, holders: dict, acquired: list[int]) -> None:
    monkeypatch.setattr(
        "src.runtime.instance_topology.get_instance_regions",
        lambda: dict(_REGIONS),
    )
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.active_region_holders",
        lambda *a, **k: dict(holders),
    )

    def _held(*a, **k) -> dict[str, frozenset[str]]:
        # EXACT held-region view derived from the same holder-idx map. The
        # dispatcher's placement filter consumes this (not the attribution view).
        out: dict[str, frozenset[str]] = {}
        for role, idxs in holders.items():
            acc: set[str] = set()
            for i in idxs:
                acc |= _REGIONS.get((role, i), frozenset())
            if acc:
                out[role] = frozenset(acc)
        return out

    monkeypatch.setattr("src.runtime.cpu_region_lock.held_regions_by_role", _held)

    def _mock_lock(role, instance_idx, timeout_s=None, deadline_s=None):
        # All disjoint candidates acquire cleanly; we record which topo_idx the
        # dispatcher actually attempted/acquired.
        acquired.append(instance_idx)
        return _FakeLockCtx(role, instance_idx, succeed=True)

    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.cpu_region_lock_for_instance", _mock_lock
    )


def test_cross_role_flag_on_avoids_other_role_held_node_half(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cross-role CPU fleet (_HALF_HOLDER) holds {q0,q1}; with the flag ON, frontdoor must land
    on a node1 quarter (q2/q3 → topo 3/4), proving _dispatch passed the full
    holder map and honored the cross-role union (and the smallest-disjoint
    ordering selects a quarter, not full)."""
    monkeypatch.setenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "1")
    acquired: list[int] = []
    backend = _make_frontdoor_backend(monkeypatch)
    _wire(monkeypatch, {_HALF_HOLDER: [0]}, acquired)
    with backend._dispatch(session_id="s1") as (chosen_backend, idx, is_full):
        assert is_full is False
        assert _DISJOINT_FROM_HOLDER == [3, 4]  # non-vacuity: the synthetic shape
        assert acquired[-1] in _DISJOINT_FROM_HOLDER  # q2 or q3 — never q0/q1/full(0)


def test_cross_role_flag_off_ignores_other_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same holders, flag OFF → cross-role holder invisible; frontdoor takes
    full (topo 0) as the first candidate. Proves the flag gates the behavior
    and the default path is unchanged."""
    monkeypatch.delenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", raising=False)
    acquired: list[int] = []
    backend = _make_frontdoor_backend(monkeypatch)
    _wire(monkeypatch, {_HALF_HOLDER: [0]}, acquired)
    with backend._dispatch(session_id="s1") as (chosen_backend, idx, is_full):
        assert is_full is True
        assert acquired[-1] == 0  # full — cross-role holder ignored


def test_shape_aware_gate_runs_per_real_candidate_and_skips_denied_idx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B-live wiring: dispatch evaluates the gate with each real topology_idx.

    Here placement finds q2/q3 safe beside _HALF_HOLDER's held node0 half. The fake
    seam queues q2 and allows q3; dispatch must skip q2 and acquire q3, proving
    the candidate_topology_idx comes from the actual candidate loop.
    """
    monkeypatch.setenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "1")
    monkeypatch.setenv("ORCHESTRATOR_SHAPE_AWARE_CONTENTION", "1")
    acquired: list[int] = []
    evaluated: list[int | None] = []
    backend = _make_frontdoor_backend(monkeypatch)
    _wire(monkeypatch, {_HALF_HOLDER: [0]}, acquired)

    class FakeGate:
        def evaluate(self, role, traffic_class, candidate_topology_idx=None):
            evaluated.append(candidate_topology_idx)
            admitted = candidate_topology_idx == 4
            return SimpleNamespace(
                admitted=admitted,
                decision=(
                    contention.PairDecision.ALLOW
                    if admitted
                    else contention.PairDecision.QUEUE
                ),
                waited_s=0.0,
                blocking_roles=[],
                reason="fake candidate verdict",
            )

    monkeypatch.setattr("src.scheduling.contention_gate.get_gate", lambda: FakeGate())

    with backend._dispatch(session_id="s1") as (_chosen_backend, idx, is_full):
        assert is_full is False
        assert idx == 3  # internal idx for topology q3
        assert acquired[-1] == 4
        assert evaluated[:2] == [3, 4]


# ── DISPATCH-A cross-role co-placement acceptance (operator 2026-07-21) ───────
#
# Unblocking quarters explicitly includes CROSS-ROLE mixing: different roles'
# quarter instances co-place on DISJOINT regions, coordinated by the GLOBAL
# per-region mutex (one holder per physical region, across roles) + cross-role
# pair verdicts. Same-region cross-role stacking must still serialize.

# Cross-role topology: frontdoor (node0-half full + 4 quarters) alongside _XR
# (its LIVE all-region full + 4 SYNTHETIC quarters). Quarter topo idx 1..4 =
# q0..q3. (Was worker_general's shape before the 2026-09-22 cutover.)
_XROLE_REGIONS = {
    **_REGIONS,
    (_XR, 0): _ALL_REGIONS,  # "0-95" full — the amplifier shape
    (_XR, 1): frozenset({"q0"}),
    (_XR, 2): frozenset({"q1"}),
    (_XR, 3): frozenset({"q2"}),
    (_XR, 4): frozenset({"q3"}),
}


class _RegionMutexModel:
    """Faithful mock of the lock layer's exclusion: the GLOBAL per-region mutex
    plus the per-role region lock together mean each physical region has at most
    ONE holder (role, topo_idx) at a time — across roles. A non-blocking acquire
    whose region set overlaps another holder raises CpuRegionLockTimeout."""

    def __init__(self, regions_map: dict):
        self.regions_map = regions_map
        self.owner: dict[str, tuple[str, int]] = {}  # region -> (role, topo)

    def holders(self, *a, **k) -> dict[str, list[int]]:
        out: dict[str, set[int]] = {}
        for (role, topo) in self.owner.values():
            out.setdefault(role, set()).add(topo)
        return {role: sorted(topos) for role, topos in out.items()}

    def held_regions(self, *a, **k) -> dict[str, frozenset[str]]:
        """EXACT held-region view (the `held_regions_by_role` counterpart): the
        physical regions actually owned, grouped by role — never the phantom
        full over-report."""
        out: dict[str, set[str]] = {}
        for rg, (role, _topo) in self.owner.items():
            out.setdefault(role, set()).add(rg)
        return {role: frozenset(rs) for role, rs in out.items()}

    def lock(self, role, instance_idx, timeout_s=None, deadline_s=None):
        regions = self.regions_map.get((role, instance_idx), frozenset())
        model = self

        class _Ctx:
            def __enter__(self_ctx):
                for rg in regions:
                    held_by = model.owner.get(rg)
                    if held_by is not None and held_by != (role, instance_idx):
                        from src.runtime.cpu_region_lock import CpuRegionLockTimeout

                        raise CpuRegionLockTimeout(f"region {rg} held by {held_by}")
                for rg in regions:
                    model.owner[rg] = (role, instance_idx)
                return [f"/tmp/cpu_region.mock.{role}.{instance_idx}.lock"]

            def __exit__(self_ctx, *exc):
                for rg in regions:
                    if model.owner.get(rg) == (role, instance_idx):
                        del model.owner[rg]
                return False

        return _Ctx()


def _wire_model(monkeypatch: pytest.MonkeyPatch, model: _RegionMutexModel) -> None:
    monkeypatch.setattr(
        "src.runtime.instance_topology.get_instance_regions", lambda: dict(model.regions_map)
    )
    monkeypatch.setattr("src.runtime.cpu_region_lock.active_region_holders", model.holders)
    monkeypatch.setattr("src.runtime.cpu_region_lock.held_regions_by_role", model.held_regions)
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.cpu_region_lock_for_instance", model.lock
    )


def _pin_full_disabled(monkeypatch: pytest.MonkeyPatch, role: str) -> None:
    """Pin `role` to FULL_DISABLED as a SYNTHETIC policy, not a live read.

    No live fleet is full_disabled (the partner these cases use, _XR, runs its
    live default policy) — under a full-first policy a solo dispatch
    legitimately takes the full candidate first.
    That commit moved the DISPATCH-A full_disabled pins in
    test_dispatch_placement_state_machine.py onto a synthetic policy for exactly
    this reason but never reached this file. The regression the pins guard (a
    FULL_DISABLED role must never acquire the all-region set) is a property of
    the POLICY, not of whichever role happens to carry it this week, so inject
    the policy rather than relaxing the assertions.
    """
    from src.scheduling.placement_policy import RolePlacementPolicy, get_placement_policy

    import scripts.server.stack_numa as _stack_numa

    monkeypatch.setitem(
        _stack_numa.NUMA_CONFIG[role], "placement_policy", "full_disabled"
    )
    assert get_placement_policy(role) is RolePlacementPolicy.FULL_DISABLED


def _make_role_backend(monkeypatch: pytest.MonkeyPatch, role: str, full_port: int):
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.setenv("ORCHESTRATOR_PLACEMENT_STATE_MACHINE", "1")
    full = _StubBackend(f"http://localhost:{full_port}")
    quarters = [_StubBackend(f"http://localhost:{full_port + 10 + i}") for i in range(4)]
    return ca_mod.ConcurrencyAwareBackend(
        full_backend=full, quarter_backends=quarters, role=role, full_port=full_port,
    )


def test_cross_role_disjoint_quarters_coplace_no_machine_wide_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DISPATCH-A (a): a cross-role (_XR) quarter decode on q0 (holding ONLY its
    per-role q0 + GLOBAL q0) co-places CONCURRENTLY with a frontdoor quarter on a
    disjoint region — no machine-wide blocking. Neither role touches the
    all-region set."""
    monkeypatch.setenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "1")
    model = _RegionMutexModel(_XROLE_REGIONS)
    _wire_model(monkeypatch, model)

    _pin_full_disabled(monkeypatch, _XR)  # synthetic, see helper
    wg = _make_role_backend(monkeypatch, _XR, _full_port(_XR))  # FULL_DISABLED
    fd = _make_role_backend(monkeypatch, "frontdoor", _full_port("frontdoor"))  # live policy

    with wg._dispatch(session_id="wg") as (_b1, idx1, is_full1):
        assert is_full1 is False
        topo1 = 0 if idx1 == -1 else idx1 + 1
        r1 = _XROLE_REGIONS[(_XR, topo1)]
        assert r1 == frozenset({"q0"})  # partner's first quarter is q0

        # Second role dispatches WHILE worker holds q0 — must succeed on a
        # disjoint region, not queue and not grab the all-region full.
        with fd._dispatch(session_id="fd") as (_b2, idx2, is_full2):
            assert is_full2 is False
            topo2 = 0 if idx2 == -1 else idx2 + 1
            r2 = _XROLE_REGIONS[("frontdoor", topo2)]
            assert r1.isdisjoint(r2)          # co-placed on disjoint regions
            assert r2 != _ALL_REGIONS          # frontdoor did not grab all-region
            live = model.holders()
            assert topo1 in live[_XR]  # both concurrently held
            assert topo2 in live["frontdoor"]
            # No region is double-booked across the two roles.
            assert len(model.owner) == len(r1) + len(r2)


def test_cross_role_same_region_stacking_queues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DISPATCH-A (b): same-region cross-role stacking (_XR q0 + frontdoor q0)
    must NOT co-place — the GLOBAL q0 mutex serializes it. With _XR's other
    quarters occupied and frontdoor already holding q0, an _XR dispatch whose
    only remaining region is q0 queues (ContentionDenied), never double-booking
    q0."""
    monkeypatch.setenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "1")
    model = _RegionMutexModel(_XROLE_REGIONS)
    # frontdoor holds q0 (its q0 quarter); _XR holds q1/q2/q3.
    model.owner["q0"] = ("frontdoor", 1)
    model.owner["q1"] = (_XR, 2)
    model.owner["q2"] = (_XR, 3)
    model.owner["q3"] = (_XR, 4)
    _wire_model(monkeypatch, model)

    wg = _make_role_backend(monkeypatch, _XR, _full_port(_XR))

    # Bound the poll loop so the queue resolves to ContentionDenied fast.
    times = iter([0.0, 0.0, 100.0])
    monkeypatch.setattr("src.backends.concurrency_aware.time.perf_counter", lambda: next(times))
    monkeypatch.setattr("src.backends.concurrency_aware.time.sleep", lambda _x: None)

    from src.scheduling.contention_gate import ContentionDenied

    with pytest.raises(ContentionDenied) as exc:
        with wg._dispatch(session_id="wg-q0"):
            pass
    assert _XR in str(exc.value)
    # q0 was never double-booked — still owned by frontdoor.
    assert model.owner["q0"] == ("frontdoor", 1)


def test_all_region_full_partner_never_acquires_more_than_candidate_region_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DISPATCH-A (c) regression pin: a dispatch on the all-region-full partner
    (_XR; was worker_general) acquires ONLY its chosen quarter's region set —
    NEVER the all-region idx-0 set (the amplifier bug this fix kills).
    FULL_DISABLED makes the whole-machine grab structurally impossible. The
    policy is injected synthetically (see `_pin_full_disabled`) because no live
    fleet carries it."""
    model = _RegionMutexModel(_XROLE_REGIONS)
    _wire_model(monkeypatch, model)
    _pin_full_disabled(monkeypatch, _XR)
    wg = _make_role_backend(monkeypatch, _XR, _full_port(_XR))
    assert wg._full_slot_aligned is True  # the all-region full IS a real candidate

    with wg._dispatch(session_id="wg-solo") as (_b, idx, is_full):
        assert is_full is False
        topo = 0 if idx == -1 else idx + 1
        assert topo != 0  # never the all-region full instance
        held_regions = set(model.owner)          # regions this dispatch holds
        assert held_regions == set(_XROLE_REGIONS[(_XR, topo)])
        assert held_regions != set(_ALL_REGIONS)  # NOT the whole machine
        assert len(held_regions) == 1             # exactly its own quarter
