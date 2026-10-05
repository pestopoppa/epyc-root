"""P2a/P2b: B wiring seam (`seam_admit`) — same-role preservation + default-off.

The seam is the adapter the gate/seeder will eventually call. It is NOT yet
wired into runtime. Properties under test:

  - DEFAULT-OFF (P2b): `seam_admit` returns None unless shape-aware contention
    is enabled, so callers keep their legacy pair_policy/nway_policy path — no
    live behavior change.
  - DUAL-FLAG (audit #1): enabling requires BOTH env flags; there is no
    `enabled` override parameter, so a runtime caller cannot bypass the gate.
    Tests enable the seam ONLY by setting both env flags (the `shape_aware_on`
    fixture), exercising the exact runtime path.
  - SAME-ROLE PRESERVATION (P2a): same-role contention is routed through
    pair_policy(role, role) so the `same_role` matrix verdict is honored.
    `admit_set` alone delegates the disjoint case to nway_policy, which dedupes
    roles and would collapse a same-role pair to ALLOW.
  - SNAPSHOT FAILURE (audit #2): unknown occupancy never silently ALLOWs.
"""

from __future__ import annotations

import pytest

from src.scheduling.contention import (
    ContentionMatrix,
    Nway,
    Pair,
    PairDecision,
    Placement,
    SameRole,
    TrafficClass,
    admit_set,
    seam_admit,
    shape_aware_contention_enabled,
)



def _live_cpu_cross_role() -> str:
    """A live CPU fleet that is NOT bound onto frontdoor's process.

    Lineup-independence (2026-09-26): the cross-role cases below used
    ingest_long_context as "the heavy CPU role beside frontdoor". The
    operator-signed 2026-09-22 cutover (orchestrator 860b0b2d) made it an alias
    of the GPU architect_general, so seam_admit's device axis now (correctly)
    resolves it to GPU — a GPU placement claims no CPU region, so the overlap
    case read ALLOW. The role is derived instead: the first NUMA_CONFIG fleet
    outside frontdoor's registry binding whose device resolves to CPU. Its
    region sets below stay SYNTHETIC; only its identity (and CPU device) is live.
    """
    from pathlib import Path

    import yaml
    from scripts.server.stack_numa import NUMA_CONFIG
    from src.scheduling.device_model import DeviceClass, resolve_role_device

    root = Path(__file__).resolve().parents[2]
    mode = yaml.safe_load(
        (root / "orchestration" / "model_registry.yaml").read_text(encoding="utf-8")
    )["server_mode"]
    fd_fleet = {"frontdoor", *(mode["frontdoor"].get("shared_with") or [])}
    fd_fleet |= {k for k, v in mode.items() if v.get("alias_of") == "frontdoor"}
    for role in sorted(NUMA_CONFIG):
        if role in fd_fleet or role == "eval_batch_frontdoor":
            continue
        if resolve_role_device(role).device_class is DeviceClass.CPU:
            return role
    raise AssertionError("no live CPU fleet outside frontdoor's — cross-role cases are vacuous")


# Heavy cross-role CPU partner (was ingest_long_context).
XR = _live_cpu_cross_role()

# frontdoor: full(0)={q0,q1}; q0(1)={q0}; q1(2)={q1}; q2(3)={q2}; q3(4)={q3}
_FD_REGIONS = {
    ("frontdoor", 0): frozenset({"q0", "q1"}),
    ("frontdoor", 1): frozenset({"q0"}),
    ("frontdoor", 2): frozenset({"q1"}),
    ("frontdoor", 3): frozenset({"q2"}),
    ("frontdoor", 4): frozenset({"q3"}),
    (XR, 0): frozenset({"q0", "q1"}),
    (XR, 3): frozenset({"q2"}),
    ("eval_batch_frontdoor", 0): frozenset({"q0", "q1"}),
    ("worker_general", 2): frozenset({"q2", "q3"}),
}


@pytest.fixture
def shape_aware_on(monkeypatch):
    """Enable the seam the ONLY supported way: set BOTH dual-flag env vars.
    There is no `enabled=` override on seam_admit (audit), so this fixture
    exercises the exact runtime gate a wired call site would hit."""
    monkeypatch.setenv("ORCHESTRATOR_SHAPE_AWARE_CONTENTION", "1")
    monkeypatch.setenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "1")


def _matrix(*, n_way=None, pairs=None, same_role=None, light=(), heavy=()):
    nway = {}
    for roles, ratio, verdict in n_way or []:
        key = tuple(sorted(roles))
        nway[key] = Nway(
            roles=key, ratio=ratio, verdict=verdict, contains_heavy=any(r in heavy for r in key)
        )
    pair_map = {}
    for roles, ratio, verdict in pairs or []:
        key = tuple(sorted(roles))
        pair_map[key] = Pair(roles=key, ratio=ratio, verdict=verdict)
    sr = {}
    for role, verdict in same_role or []:
        sr[role] = SameRole(role=role, verdict=verdict)
    return ContentionMatrix(
        version=1,
        measured_at="",
        host="",
        topology_hash="synthetic",
        default_floor=0.85,
        pairs=pair_map,
        same_role=sr,
        unknown_pairs=[],
        n_way=nway,
        light_roles=frozenset(light),
        heavy_roles=frozenset(heavy),
    )


# ── P2b: default-off / dual-flag gate ─────────────────────────────────


def test_seam_default_off_returns_none(monkeypatch) -> None:
    monkeypatch.delenv("ORCHESTRATOR_SHAPE_AWARE_CONTENTION", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", raising=False)
    assert shape_aware_contention_enabled() is False
    out = seam_admit(
        "frontdoor",
        3,
        {"frontdoor": frozenset({"q0"})},
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=_matrix(same_role=[("frontdoor", "block")]),
    )
    assert out is None


def test_seam_requires_BOTH_flags(monkeypatch) -> None:
    """Dual-flag safety contract (audit #1): shape-aware admission requires BOTH
    ORCHESTRATOR_SHAPE_AWARE_CONTENTION=1 AND
    ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1. Either alone -> disabled."""
    # only SHAPE_AWARE -> still disabled
    monkeypatch.setenv("ORCHESTRATOR_SHAPE_AWARE_CONTENTION", "1")
    monkeypatch.delenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", raising=False)
    assert shape_aware_contention_enabled() is False
    # only PLACEMENT -> still disabled
    monkeypatch.delenv("ORCHESTRATOR_SHAPE_AWARE_CONTENTION", raising=False)
    monkeypatch.setenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "1")
    assert shape_aware_contention_enabled() is False
    # BOTH -> enabled
    monkeypatch.setenv("ORCHESTRATOR_SHAPE_AWARE_CONTENTION", "1")
    monkeypatch.setenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "1")
    assert shape_aware_contention_enabled() is True


def test_seam_only_shape_flag_makes_seam_return_none(monkeypatch) -> None:
    """With only SHAPE_AWARE set (placement flag off), seam_admit must stay
    inert (None) — no shape-aware verdict leaks without the placement layer."""
    monkeypatch.setenv("ORCHESTRATOR_SHAPE_AWARE_CONTENTION", "1")
    monkeypatch.delenv("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", raising=False)
    out = seam_admit(
        "frontdoor",
        3,
        {"frontdoor": frozenset({"q0"})},
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=_matrix(same_role=[("frontdoor", "block")]),
    )
    assert out is None


def test_seam_flag_on_enables(shape_aware_on) -> None:
    assert shape_aware_contention_enabled() is True
    out = seam_admit(
        "frontdoor",
        3,
        {},  # no holders
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=_matrix(),
    )
    assert out == PairDecision.ALLOW


# ── P2a: same-role preservation ───────────────────────────────────────


def test_seam_same_role_block_queues_where_admit_set_allows(shape_aware_on) -> None:
    """The crux. frontdoor holds q0; candidate frontdoor.q2 (disjoint). With a
    same_role 'block' verdict, the seam must QUEUE (bg) via pair_policy(role,
    role) — whereas plain admit_set returns ALLOW because nway_policy dedupes
    frontdoor+frontdoor to one role."""
    m = _matrix(same_role=[("frontdoor", "block")])
    active = {"frontdoor": frozenset({"q0"})}

    seam = seam_admit(
        "frontdoor",
        3,
        active,
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=m,
    )
    assert seam == PairDecision.QUEUE

    # Plain admit_set on the same scenario collapses to ALLOW — the bug the
    # seam exists to prevent.
    naive = admit_set(
        (Placement("frontdoor", frozenset({"q0"})),),
        Placement("frontdoor", frozenset({"q2"})),
        TrafficClass.BACKGROUND,
        matrix=m,
    )
    assert naive == PairDecision.ALLOW


def test_seam_same_role_allow_passes(shape_aware_on) -> None:
    m = _matrix(same_role=[("frontdoor", "allow")])
    out = seam_admit(
        "frontdoor",
        3,
        {"frontdoor": frozenset({"q0"})},
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=m,
    )
    assert out == PairDecision.ALLOW


def test_seam_same_role_overlap_queues(shape_aware_on) -> None:
    """Candidate frontdoor.q0 against held frontdoor q0 → physical overlap → QUEUE."""
    m = _matrix(same_role=[("frontdoor", "allow")])
    out = seam_admit(
        "frontdoor",
        1,
        {"frontdoor": frozenset({"q0"})},
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=m,
    )
    assert out == PairDecision.QUEUE


def test_seam_same_role_block_foreground_degraded_allow(shape_aware_on) -> None:
    """Foreground same_role block → DEGRADED_ALLOW (pair_policy), not QUEUE."""
    m = _matrix(same_role=[("frontdoor", "block")])
    out = seam_admit(
        "frontdoor",
        3,
        {"frontdoor": frozenset({"q0"})},
        traffic_class=TrafficClass.FOREGROUND_INTERACTIVE,
        instance_regions=_FD_REGIONS,
        matrix=m,
    )
    assert out == PairDecision.DEGRADED_ALLOW


# ── cross-role delegation ─────────────────────────────────────────────


def test_seam_cross_role_disjoint_allows(shape_aware_on) -> None:
    m = _matrix(n_way=[(("frontdoor", XR), 1.7, "allow")], heavy=(XR,))
    out = seam_admit(
        XR,
        3,  # partner q2
        {"frontdoor": frozenset({"q0"})},
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=m,
    )
    assert out == PairDecision.ALLOW


def test_seam_aux_frontdoor_allows_disjoint_worker_half(shape_aware_on) -> None:
    m = _matrix(
        n_way=[(("frontdoor", "worker_general"), 1.2, "allow")],
        heavy=("worker_general",),
    )

    out = seam_admit(
        "worker_general",
        2,
        {"eval_batch_frontdoor": frozenset({"q0", "q1"})},
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=m,
    )

    assert out == PairDecision.ALLOW


def test_seam_cross_role_overlap_queues(shape_aware_on) -> None:
    from src.scheduling.device_model import DeviceClass, resolve_role_device

    # Non-vacuity: both sides must be CPU placements, or a GPU side would claim
    # no region and the "overlap" would be physically empty.
    assert resolve_role_device(XR).device_class is DeviceClass.CPU
    assert resolve_role_device("frontdoor").device_class is DeviceClass.CPU
    m = _matrix(n_way=[(("frontdoor", XR), 9.9, "allow")], heavy=(XR,))
    out = seam_admit(
        XR,
        0,  # partner {q0,q1} overlaps frontdoor q0
        {"frontdoor": frozenset({"q0"})},
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=m,
    )
    assert out == PairDecision.QUEUE


def test_seam_combines_same_and_cross_worst(shape_aware_on) -> None:
    """Same-role allow + cross-role measured block → worst = QUEUE."""
    m = _matrix(
        same_role=[("frontdoor", "allow")],
        n_way=[(("frontdoor", XR), 0.5, "block")],
        heavy=(XR,),
    )
    # active: frontdoor q0 (same-role) + partner q1 (cross-role). candidate frontdoor q2.
    active = {"frontdoor": frozenset({"q0"}), XR: frozenset({"q1"})}
    out = seam_admit(
        "frontdoor",
        3,
        active,
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=m,
    )
    assert out == PairDecision.QUEUE


# ── unknown candidate placement ───────────────────────────────────────


def test_seam_unknown_candidate_bg_fails_closed(shape_aware_on) -> None:
    m = _matrix(same_role=[("frontdoor", "allow")])
    out = seam_admit(
        "frontdoor",
        99,  # unknown idx → empty regions
        {"frontdoor": frozenset({"q0"})},
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=m,
    )
    assert out == PairDecision.QUEUE


# ── live-read path (active_holders=None) ──────────────────────────────


def test_seam_reads_held_regions_when_active_holders_none(shape_aware_on, monkeypatch) -> None:
    import src.runtime.cpu_region_lock as crl

    monkeypatch.setattr(
        crl,
        "held_regions_by_role",
        lambda instance_regions=None: {"frontdoor": frozenset({"q0"})},
    )
    m = _matrix(same_role=[("frontdoor", "block")])
    out = seam_admit(
        "frontdoor",
        3,
        None,
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=m,
    )
    assert out == PairDecision.QUEUE


# ── snapshot failure (audit #2): unknown occupancy must not silently ALLOW ──


def test_seam_snapshot_failure_background_fails_closed(shape_aware_on, monkeypatch) -> None:
    """If held_regions_by_role raises, occupancy is unknown. Background must
    FAIL CLOSED (QUEUE) — never silently ALLOW under unknown occupancy."""
    import src.runtime.cpu_region_lock as crl

    def _boom(instance_regions=None):
        raise RuntimeError("proc-lock scan failed")

    monkeypatch.setattr(crl, "held_regions_by_role", _boom)
    out = seam_admit(
        "frontdoor",
        3,
        None,
        traffic_class=TrafficClass.BACKGROUND,
        instance_regions=_FD_REGIONS,
        matrix=_matrix(),
    )
    assert out == PairDecision.QUEUE


def test_seam_snapshot_failure_foreground_falls_back_to_legacy(shape_aware_on, monkeypatch) -> None:
    """On snapshot failure, foreground returns None so the caller uses its
    legacy pair_policy/nway_policy path rather than a fabricated verdict."""
    import src.runtime.cpu_region_lock as crl

    def _boom(instance_regions=None):
        raise RuntimeError("proc-lock scan failed")

    monkeypatch.setattr(crl, "held_regions_by_role", _boom)
    out = seam_admit(
        "frontdoor",
        3,
        None,
        traffic_class=TrafficClass.FOREGROUND_INTERACTIVE,
        instance_regions=_FD_REGIONS,
        matrix=_matrix(),
    )
    assert out is None
