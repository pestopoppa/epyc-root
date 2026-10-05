"""Part B scaffolding tests: shape-keyed `admit_set` (cross-role placement-aware
admission). admit_set is NOT yet wired into the gate/seeder — these prove the
pure decision logic against synthetic matrices + one real-matrix regression.

Decision summary (see src/scheduling/contention.py::admit_set):
  - physical region overlap  → QUEUE (serialize; cannot co-run on same cores)
  - disjoint                 → role-set nway_policy verdict for certified placement
  - unknown placement        → bg QUEUE; fg legacy role-keyed pair_policy
"""

from __future__ import annotations

from src.scheduling.contention import (
    ContentionMatrix,
    Nway,
    Pair,
    Placement,
    PairDecision,
    TrafficClass,
    admit_set,
    placement_for_instance,
    placements_overlap,
)


def _matrix(*, n_way=None, pairs=None, light=(), heavy=(), unknown=()):
    """Build a synthetic ContentionMatrix for truth-table tests."""
    nway = {}
    for roles, ratio, verdict in (n_way or []):
        key = tuple(sorted(roles))
        nway[key] = Nway(roles=key, ratio=ratio, verdict=verdict,
                         contains_heavy=any(r in heavy for r in key))
    pair_map = {}
    for roles, ratio, verdict in (pairs or []):
        key = tuple(sorted(roles))
        pair_map[key] = Pair(roles=key, ratio=ratio, verdict=verdict)
    return ContentionMatrix(
        version=1, measured_at="", host="", topology_hash="synthetic",
        default_floor=0.85, pairs=pair_map, same_role={},
        unknown_pairs=[tuple(sorted(u)) for u in unknown], n_way=nway,
        light_roles=frozenset(light), heavy_roles=frozenset(heavy),
    )


# ── value-type helpers ────────────────────────────────────────────────

def test_placements_overlap_is_region_set_intersection_not_label() -> None:
    # frontdoor "full" = node0-half {q0,q1}; vision "full" = node1-half {q2,q3}.
    # Same LABEL ("full") but DISJOINT — overlap must be False.
    fd_full = Placement("frontdoor", frozenset({"q0", "q1"}))
    vis_full = Placement("vision_escalation", frozenset({"q2", "q3"}))
    assert placements_overlap(fd_full, vis_full) is False
    # worker_general "full" = all four → overlaps everything.
    wg_full = Placement("worker_general", frozenset({"q0", "q1", "q2", "q3"}))
    assert placements_overlap(wg_full, fd_full) is True


def test_placement_for_instance_resolves_from_map() -> None:
    regions = {("frontdoor", 1): frozenset({"q0"})}
    p = placement_for_instance("frontdoor", 1, instance_regions=regions)
    assert p == Placement("frontdoor", frozenset({"q0"}))
    # Unknown (role, idx) → empty regions (admit_set treats as unknown).
    assert placement_for_instance("frontdoor", 9, instance_regions=regions).regions == frozenset()


# ── empty active set ──────────────────────────────────────────────────

def test_empty_active_set_allows() -> None:
    m = _matrix()
    cand = Placement("frontdoor", frozenset({"q0"}))
    assert admit_set((), cand, TrafficClass.BACKGROUND, matrix=m) == PairDecision.ALLOW


# ── (1) physical overlap → QUEUE, even if a generous n_way exists ──────

def test_overlap_queues_regardless_of_matrix() -> None:
    # A wildly generous n_way for the role pair must NOT rescue an overlapping
    # placement — overlap is a hard physical conflict on shared cores.
    m = _matrix(n_way=[(("frontdoor", "ingest_long_context"), 9.9, "allow")],
                heavy=("ingest_long_context",))
    active = (Placement("frontdoor", frozenset({"q0", "q1"})),)
    cand = Placement("ingest_long_context", frozenset({"q0", "q1"}))  # same node0-half
    assert admit_set(active, cand, TrafficClass.FOREGROUND_INTERACTIVE, matrix=m) == PairDecision.QUEUE
    assert admit_set(active, cand, TrafficClass.BACKGROUND, matrix=m) == PairDecision.QUEUE


# ── (2) certified disjoint placement → role-set n_way verdict ─────────

def test_disjoint_measured_allow() -> None:
    m = _matrix(n_way=[(("frontdoor", "ingest_long_context"), 1.7, "allow")],
                heavy=("ingest_long_context",))
    active = (Placement("frontdoor", frozenset({"q0"})),)
    cand = Placement("ingest_long_context", frozenset({"q2", "q3"}))  # disjoint half
    assert admit_set(active, cand, TrafficClass.BACKGROUND, matrix=m) == PairDecision.ALLOW


def test_disjoint_measured_block_queues() -> None:
    m = _matrix(n_way=[(("frontdoor", "ingest_long_context"), 0.5, "block")],
                heavy=("ingest_long_context",))
    active = (Placement("frontdoor", frozenset({"q0"})),)
    cand = Placement("ingest_long_context", frozenset({"q2"}))
    assert admit_set(active, cand, TrafficClass.BACKGROUND, matrix=m) == PairDecision.QUEUE
    # foreground may serialize too (nway_policy returns QUEUE for measured block)
    assert admit_set(active, cand, TrafficClass.FOREGROUND_INTERACTIVE, matrix=m) == PairDecision.QUEUE


def test_disjoint_measured_borderline_traffic_split() -> None:
    m = _matrix(n_way=[(("frontdoor", "worker_general"), 0.9, "borderline")])
    active = (Placement("frontdoor", frozenset({"q0"})),)
    cand = Placement("worker_general", frozenset({"q2"}))
    assert admit_set(active, cand, TrafficClass.FOREGROUND_INTERACTIVE, matrix=m) == PairDecision.ALLOW
    assert admit_set(active, cand, TrafficClass.BACKGROUND, matrix=m) == PairDecision.QUEUE


def test_disjoint_verdict_is_nway_for_role_set_precondition_quarter_placement() -> None:
    # The matrix's n_way layer is role-set keyed; admit_set relies on callers
    # passing A's certified smallest-disjoint placements before this branch.
    # For that contract, role-keyed pair QUEUE must not poison the n_way ALLOW.
    m = _matrix(
        pairs=[(("frontdoor", "vision_escalation"), 0.84, "borderline")],
        n_way=[(("frontdoor", "vision_escalation"), 1.434, "allow")],
        heavy=("vision_escalation",),
    )
    active = (Placement("frontdoor", frozenset({"q0"})),)
    cand = Placement("vision_escalation", frozenset({"q2"}))
    assert admit_set(active, cand, TrafficClass.BACKGROUND, matrix=m) == PairDecision.ALLOW


def test_disjoint_unmeasured_all_light_allows() -> None:
    # No n_way entry; all roles light + quartered → allow-by-policy.
    m = _matrix(light=("frontdoor", "worker_general"))
    active = (Placement("frontdoor", frozenset({"q0"})),)
    cand = Placement("worker_general", frozenset({"q2"}))
    assert admit_set(active, cand, TrafficClass.BACKGROUND, matrix=m) == PairDecision.ALLOW


def test_disjoint_unmeasured_with_heavy_fails_closed_for_background() -> None:
    # Unmeasured set containing a heavy role → fail closed (bg QUEUE / fg open).
    m = _matrix(light=("frontdoor",), heavy=("ingest_long_context",))
    active = (Placement("frontdoor", frozenset({"q0"})),)
    cand = Placement("ingest_long_context", frozenset({"q2", "q3"}))
    assert admit_set(active, cand, TrafficClass.BACKGROUND, matrix=m) == PairDecision.QUEUE
    assert admit_set(active, cand, TrafficClass.FOREGROUND_INTERACTIVE, matrix=m) == PairDecision.ALLOW


# ── (3) unknown placement → bg fail-closed; fg pair_policy fallback ───

def test_unknown_candidate_placement_falls_back_to_pair_policy() -> None:
    # Candidate has no region info (empty) → background fails closed, foreground
    # uses the legacy pair_policy fallback.
    m = _matrix(unknown=[("frontdoor", "ingest_long_context")],
                heavy=("ingest_long_context",))
    active = (Placement("frontdoor", frozenset({"q0"})),)
    cand = Placement("ingest_long_context", frozenset())  # unknown shape
    assert admit_set(active, cand, TrafficClass.BACKGROUND, matrix=m) == PairDecision.QUEUE
    assert admit_set(active, cand, TrafficClass.FOREGROUND_INTERACTIVE, matrix=m) == PairDecision.ALLOW


def test_unknown_placement_background_fails_closed_even_for_known_allow_pair() -> None:
    # Unknown placement means overlap is undecidable. Background must fail
    # closed before consulting legacy pair_policy, even for a measured-good pair.
    m = _matrix(pairs=[(("frontdoor", "worker_general"), 1.11, "allow")])
    active = (Placement("frontdoor", frozenset({"q0"})),)
    cand = Placement("worker_general", frozenset())
    assert admit_set(active, cand, TrafficClass.BACKGROUND, matrix=m) == PairDecision.QUEUE
    assert admit_set(active, cand, TrafficClass.FOREGROUND_INTERACTIVE, matrix=m) == PairDecision.ALLOW


def test_unknown_active_placement_also_forces_fallback() -> None:
    # If an ACTIVE placement is unknown, overlap is undecidable → background
    # fails closed.
    m = _matrix(pairs=[(("frontdoor", "ingest_long_context"), 0.37, "block")],
                heavy=("ingest_long_context",))
    active = (Placement("frontdoor", frozenset()),)  # unknown active shape
    cand = Placement("ingest_long_context", frozenset({"q2"}))
    assert admit_set(active, cand, TrafficClass.BACKGROUND, matrix=m) == PairDecision.QUEUE


# ── (3-bis) the core disambiguation, synthetic ────────────────────────

def test_same_pair_opposite_verdicts_by_placement() -> None:
    """The crux: ONE role pair, TWO placements, OPPOSITE verdicts — which a
    role-keyed lookup cannot produce. Overlapping → QUEUE; disjoint → ALLOW."""
    m = _matrix(
        pairs=[(("frontdoor", "ingest_long_context"), 0.37, "block")],   # overlapping primary
        n_way=[(("frontdoor", "ingest_long_context"), 1.716, "allow")],  # disjoint quarters
        heavy=("ingest_long_context",),
    )
    fd = Placement("frontdoor", frozenset({"q0", "q1"}))
    overlapping = Placement("ingest_long_context", frozenset({"q0", "q1"}))
    disjoint = Placement("ingest_long_context", frozenset({"q2", "q3"}))
    assert admit_set((fd,), overlapping, TrafficClass.BACKGROUND, matrix=m) == PairDecision.QUEUE
    assert admit_set((fd,), disjoint, TrafficClass.BACKGROUND, matrix=m) == PairDecision.ALLOW


# ── step 3: regression against the REAL contention matrix ─────────────

def test_real_matrix_disjoint_triple_allows_overlap_queues() -> None:
    """Proof B resolves what A could not, using the shipped matrix:
    disjoint {frontdoor, ingest_long_context, worker_general} → ALLOW (the
    measured 1.535 n_way), while overlapping-primary frontdoor+ingest → QUEUE."""
    from src.scheduling.contention import load_contention_matrix

    m = load_contention_matrix()  # real orchestration/contention_matrix.yaml

    # Disjoint triple on distinct quarters → measured n_way allow.
    active = (
        Placement("frontdoor", frozenset({"q0"})),
        Placement("ingest_long_context", frozenset({"q1"})),
    )
    cand_ok = Placement("worker_general", frozenset({"q2"}))
    assert admit_set(active, cand_ok, TrafficClass.BACKGROUND, matrix=m) == PairDecision.ALLOW

    # Overlapping-primary frontdoor + ingest (both node0-half) → QUEUE.
    fd_half = Placement("frontdoor", frozenset({"q0", "q1"}))
    ingest_half = Placement("ingest_long_context", frozenset({"q0", "q1"}))
    assert admit_set((fd_half,), ingest_half, TrafficClass.BACKGROUND, matrix=m) == PairDecision.QUEUE
