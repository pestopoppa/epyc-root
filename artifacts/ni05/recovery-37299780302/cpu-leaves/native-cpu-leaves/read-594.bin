"""WP-2 tests: evaluate_placement filters candidates by topology overlap.

Pure-function tests against the placement-policy module. Dispatcher
integration is exercised separately via test_concurrency_aware_*.
"""

from __future__ import annotations


from src.scheduling.placement import (
    Place,
    QueueReason,
    evaluate_placement,
)


# Synthetic frontdoor topology (matches stack_numa.py shape):
#   instance 0 = full (NUMA_NODE0)   → {q0, q1}
#   instance 1 = q0_inst             → {q0}
#   instance 2 = q1_inst             → {q1}
#   instance 3 = q2_inst             → {q2}
#   instance 4 = q3_inst             → {q3}
FRONTDOOR_TOPOLOGY = {
    ("frontdoor", 0): frozenset({"q0", "q1"}),
    ("frontdoor", 1): frozenset({"q0"}),
    ("frontdoor", 2): frozenset({"q1"}),
    ("frontdoor", 3): frozenset({"q2"}),
    ("frontdoor", 4): frozenset({"q3"}),
}

# Dispatcher priority order (matches _dispatch candidate construction):
#   (-1, 0) full, then quarters in NUMA-disjoint preference order:
#   q_idx 2 (topo 3 → q2), q_idx 3 (topo 4 → q3), q_idx 0 (topo 1 → q0), q_idx 1 (topo 2 → q1)
# For these tests we use the simplest order: full, q3, q2, q1, q0 — matches
# the actual preference for frontdoor's NUMA_NODE0 full.
FRONTDOOR_CANDIDATES = [
    (-1, 0),  # full
    (3, 4),   # q3 (NUMA-disjoint)
    (2, 3),   # q2 (NUMA-disjoint)
    (1, 2),   # q1 (overlaps full)
    (0, 1),   # q0 (overlaps full)
]


# ── No holders → full is the first safe candidate ──────────────────────


def test_no_holders_full_first() -> None:
    r = evaluate_placement("frontdoor", FRONTDOOR_CANDIDATES, [], FRONTDOOR_TOPOLOGY)
    assert not r.is_queue
    assert r.places[0] == Place(internal_idx=-1, topology_idx=0)
    # All 5 candidates are safe when no holders exist.
    assert len(r.places) == 5


# ── Full held → q3 + q2 safe; q1 + q0 overlap → filtered ───────────────


def test_full_held_filters_overlapping_quarters() -> None:
    r = evaluate_placement("frontdoor", FRONTDOOR_CANDIDATES, [0], FRONTDOOR_TOPOLOGY)
    assert not r.is_queue
    # full(0) overlaps with itself → filtered. q3(4) and q2(3) disjoint → kept.
    # q1(2) and q0(1) overlap full's {q0,q1} → filtered.
    assert r.places == (Place(3, 4), Place(2, 3))


def test_full_plus_q3_held_only_q2_safe() -> None:
    r = evaluate_placement("frontdoor", FRONTDOOR_CANDIDATES, [0, 4], FRONTDOOR_TOPOLOGY)
    assert not r.is_queue
    assert r.places == (Place(2, 3),)  # only q2 left


def test_full_plus_q3_plus_q2_held_no_safe_candidate() -> None:
    r = evaluate_placement("frontdoor", FRONTDOOR_CANDIDATES, [0, 3, 4], FRONTDOOR_TOPOLOGY)
    assert r.is_queue
    assert r.queue.reason is QueueReason.TOPOLOGY_OVERLAP
    # Holders union covers all 4 regions → every candidate overlaps.
    assert set(r.queue.blocking_instance_idxs) == {0, 1, 2, 3, 4}
    assert "holders=[0, 3, 4]" in r.queue.detail


def test_all_four_quarters_held_no_safe() -> None:
    """Sanity: 4 quarters in use → full blocked (overlap) → queue."""
    r = evaluate_placement("frontdoor", FRONTDOOR_CANDIDATES, [1, 2, 3, 4], FRONTDOOR_TOPOLOGY)
    assert r.is_queue
    assert r.queue.reason is QueueReason.TOPOLOGY_OVERLAP


# ── Cross-role isolation: holders on a different role don't affect this role ─


def test_holders_on_different_role_ignored() -> None:
    # Even though "worker_general" instance 0 covers everything, it shouldn't
    # affect frontdoor placement — same_role-only filter.
    topology = {**FRONTDOOR_TOPOLOGY, ("worker_general", 0): frozenset({"q0", "q1", "q2", "q3"})}
    r = evaluate_placement(
        "frontdoor",
        FRONTDOOR_CANDIDATES,
        [],  # no frontdoor holders
        topology,
    )
    assert not r.is_queue
    assert len(r.places) == 5


# ── Part A: cross-role disjoint placement ──────────────────────────────
# When `cross_role_holders` is supplied (the full {role: [idxs]} map from
# active_region_holders()), evaluate_placement unions occupied regions across
# ALL roles, not just the dispatching role. This is what lets a light role
# backfill the free quarters while a heavy role's node-half is in flight.
# Overlap is computed from canonical region sets — never from a shape label
# like "full" (frontdoor/ingest "full" = node0-half {q0,q1}; worker_general
# "full" = all four). The legacy single-role path (cross_role_holders=None)
# is unchanged; test_holders_on_different_role_ignored documents it.

# Two node0-half roles + frontdoor quarters.
CROSS_ROLE_TOPOLOGY = {
    **FRONTDOOR_TOPOLOGY,
    ("ingest_long_context", 0): frozenset({"q0", "q1"}),  # node0-half primary
}


def test_cross_role_holder_filters_overlapping_quarters() -> None:
    """ingest_long_context.half0 holds {q0,q1}; frontdoor may still land on
    the free node1 quarters q2/q3, but full/q0/q1 candidates are filtered."""
    r = evaluate_placement(
        "frontdoor",
        FRONTDOOR_CANDIDATES,
        [],  # no same-role frontdoor holders
        CROSS_ROLE_TOPOLOGY,
        cross_role_holders={"ingest_long_context": [0]},
    )
    assert not r.is_queue
    # full(0)={q0,q1} overlaps; q3(4)/q2(3) disjoint → safe; q1(2)/q0(1) overlap.
    assert r.places == (Place(3, 4), Place(2, 3))


def test_cross_role_union_combines_with_same_role_holders() -> None:
    """Same-role holder (frontdoor q3) AND a cross-role holder (ingest half0)
    both constrain: only q2 survives."""
    r = evaluate_placement(
        "frontdoor",
        FRONTDOOR_CANDIDATES,
        [4],  # frontdoor q3 held
        CROSS_ROLE_TOPOLOGY,
        cross_role_holders={"ingest_long_context": [0]},
    )
    assert not r.is_queue
    assert r.places == (Place(2, 3),)  # only q2 disjoint from {q0,q1}∪{q3}


def test_cross_role_full_machine_holder_blocks_all() -> None:
    """A whole-machine holder (worker_general full = {q0,q1,q2,q3}) leaves no
    disjoint quarter → queue."""
    topo = {
        **FRONTDOOR_TOPOLOGY,
        ("worker_general", 0): frozenset({"q0", "q1", "q2", "q3"}),
    }
    r = evaluate_placement(
        "frontdoor",
        FRONTDOOR_CANDIDATES,
        [],
        topo,
        cross_role_holders={"worker_general": [0]},
    )
    assert r.is_queue
    assert r.queue.reason is QueueReason.TOPOLOGY_OVERLAP


def test_cross_role_holders_self_role_only_preserves_legacy_order() -> None:
    """Audit P1: the size-ordering reorder must trigger on *other-role* occupied
    regions, NOT merely on a holder map being passed. If cross_role_holders
    contains ONLY the dispatching role (no other role holds anything), there is
    no cross-role pressure → ordering must stay byte-identical to legacy
    (dispatcher priority: full first), not size-sorted (quarters first)."""
    r = evaluate_placement(
        "frontdoor",
        FRONTDOOR_CANDIDATES,
        [],  # no same-role holders via holder_idxs
        FRONTDOOR_TOPOLOGY,
        cross_role_holders={"frontdoor": [1]},  # self-role only → union empty
    )
    assert not r.is_queue
    # Legacy dispatcher order preserved: full (topo 0) FIRST, not a size-1 quarter.
    assert r.places[0] == Place(-1, 0)
    assert len(r.places) == 5


def test_cross_role_none_preserves_legacy_isolation() -> None:
    """Backward-compat: cross_role_holders=None → cross-role holders ignored,
    exactly as test_holders_on_different_role_ignored asserts."""
    r = evaluate_placement(
        "frontdoor",
        FRONTDOOR_CANDIDATES,
        [],
        CROSS_ROLE_TOPOLOGY,
        cross_role_holders=None,
    )
    assert not r.is_queue
    assert len(r.places) == 5  # ingest holder invisible without the map


def test_cross_role_disjoint_holder_prefers_smallest_then_full() -> None:
    """A cross-role holder on node1 (vision half1 = {q2,q3}) does NOT block
    frontdoor's node0 candidates, but the locked invariant requires the
    SMALLEST disjoint candidate first: quarters q0/q1 (size 1) precede full
    (size 2). q2/q3 overlap the holder → filtered."""
    topo = {
        **FRONTDOOR_TOPOLOGY,
        ("vision_escalation", 0): frozenset({"q2", "q3"}),  # node1-half
    }
    r = evaluate_placement(
        "frontdoor",
        FRONTDOOR_CANDIDATES,
        [],
        topo,
        cross_role_holders={"vision_escalation": [0]},
    )
    assert not r.is_queue
    # q2/q3 filtered (overlap {q2,q3}); survivors are q0, q1, full.
    assert set(r.places) == {Place(0, 1), Place(1, 2), Place(-1, 0)}
    # Invariant: smallest disjoint first — full (size 2) must come LAST.
    assert r.places[-1] == Place(-1, 0)
    # The two size-1 quarters precede it (dispatcher priority preserved among ties).
    assert r.places[0] in (Place(0, 1), Place(1, 2))


# ── Sticky-quarter scenario: q3 listed first via sticky session ────────


def test_sticky_quarter_promoted_to_head() -> None:
    sticky_candidates = [
        (3, 4),     # sticky q3 first
        (-1, 0),    # full
        (2, 3),     # q2
        (1, 2),     # q1
        (0, 1),     # q0
    ]
    r = evaluate_placement("frontdoor", sticky_candidates, [], FRONTDOOR_TOPOLOGY)
    assert r.places[0] == Place(3, 4)


# ── Candidate without region info (e.g. embedder on HT-only) → safe fallthrough ─


def test_unknown_region_candidate_is_considered_safe() -> None:
    """If a candidate's (role, idx) has no region entry, treat as overlap-free
    and pass through. The lock layer is the final arbiter."""
    candidates = [(-1, 0), (99, 99)]  # second candidate has no topology entry
    topology = {("frontdoor", 0): frozenset({"q0", "q1"})}
    r = evaluate_placement("frontdoor", candidates, [0], topology)
    # full is filtered (overlaps itself), unknown candidate is kept.
    assert r.places == (Place(99, 99),)


# ── Empty candidate list returns queue ─────────────────────────────────


def test_empty_candidates_returns_queue() -> None:
    r = evaluate_placement("frontdoor", [], [], FRONTDOOR_TOPOLOGY)
    assert r.is_queue
    assert r.queue.reason is QueueReason.TOPOLOGY_OVERLAP


# ── Worker-general shape: full=0-95 → every quarter overlaps ────────────


WORKER_GENERAL_TOPOLOGY = {
    ("worker_general", 0): frozenset({"q0", "q1", "q2", "q3"}),  # full = 0-95
    ("worker_general", 1): frozenset({"q0"}),
    ("worker_general", 2): frozenset({"q1"}),
    ("worker_general", 3): frozenset({"q2"}),
    ("worker_general", 4): frozenset({"q3"}),
}
WORKER_GENERAL_CANDIDATES = [
    (-1, 0),
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
]


def test_worker_general_full_held_no_safe_quarter() -> None:
    r = evaluate_placement(
        "worker_general",
        WORKER_GENERAL_CANDIDATES,
        [0],
        WORKER_GENERAL_TOPOLOGY,
    )
    assert r.is_queue
    assert r.queue.reason is QueueReason.TOPOLOGY_OVERLAP
    # All 5 candidates overlap full's {q0,q1,q2,q3} or self.
    assert set(r.queue.blocking_instance_idxs) == {0, 1, 2, 3, 4}


def test_worker_general_quarter_held_full_blocked() -> None:
    """One quarter in use → full overlaps → queue (no other safe candidate)."""
    r = evaluate_placement(
        "worker_general",
        WORKER_GENERAL_CANDIDATES,
        [1],  # q0 in use
        WORKER_GENERAL_TOPOLOGY,
    )
    # full overlaps q0 (its {q0,q1,q2,q3} ⊃ {q0}); q0 overlaps itself; q2/q3 disjoint.
    assert not r.is_queue
    assert r.places == (Place(1, 2), Place(2, 3), Place(3, 4))
