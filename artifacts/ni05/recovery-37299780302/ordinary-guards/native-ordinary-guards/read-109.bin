"""C PREP (tests/helpers only — NO removal of veto/idle-barrier/pressure-skip):
pure `select_backfill_candidate` — given free regions + candidate (role, idx)
options + active holders, pick the highest-priority candidate that BOTH
physically fits the free regions AND is admitted (ALLOW) by the shape-aware
policy. This is the work-conserving selection C will eventually call to fill
idle quarters beside a heavy node-half holder. It is pure + unused by runtime.
"""

from __future__ import annotations

from src.scheduling.contention import (
    ContentionMatrix,
    Nway,
    Pair,
    SameRole,
    TrafficClass,
    select_backfill_candidate,
)

_REGIONS = {
    ("frontdoor", 1): frozenset({"q0"}),
    ("frontdoor", 2): frozenset({"q1"}),
    ("frontdoor", 3): frozenset({"q2"}),
    ("frontdoor", 4): frozenset({"q3"}),
    ("worker_general", 1): frozenset({"q0"}),
    ("worker_general", 3): frozenset({"q2"}),
    ("ingest_long_context", 0): frozenset({"q0", "q1"}),
    ("vision_escalation", 3): frozenset({"q2"}),
    ("vision_escalation", 4): frozenset({"q3"}),
}


def _matrix(*, n_way=None, pairs=None, same_role=None, light=(), heavy=()):
    nway = {}
    for roles, ratio, verdict in (n_way or []):
        key = tuple(sorted(roles))
        nway[key] = Nway(roles=key, ratio=ratio, verdict=verdict,
                         contains_heavy=any(r in heavy for r in key))
    pair_map = {}
    for roles, ratio, verdict in (pairs or []):
        key = tuple(sorted(roles))
        pair_map[key] = Pair(roles=key, ratio=ratio, verdict=verdict)
    sr = {role: SameRole(role=role, verdict=v) for role, v in (same_role or [])}
    return ContentionMatrix(
        version=1, measured_at="", host="", topology_hash="synthetic",
        default_floor=0.85, pairs=pair_map, same_role=sr, unknown_pairs=[],
        n_way=nway, light_roles=frozenset(light), heavy_roles=frozenset(heavy),
    )


def test_picks_disjoint_admissible_candidate() -> None:
    """ingest holds {q0,q1} (node0-half). Candidate worker_general.q2 is disjoint
    AND measured-allow → selected."""
    m = _matrix(n_way=[(("ingest_long_context", "worker_general"), 1.1, "allow")],
                heavy=("ingest_long_context",))
    active = {"ingest_long_context": frozenset({"q0", "q1"})}
    candidates = [("worker_general", 3)]  # q2
    pick = select_backfill_candidate(
        candidates, active, TrafficClass.BACKGROUND,
        instance_regions=_REGIONS, matrix=m,
    )
    assert pick == ("worker_general", 3)


def test_skips_overlapping_candidate() -> None:
    """A candidate that overlaps the held region is never selected even if its
    role pair is allow."""
    m = _matrix(n_way=[(("ingest_long_context", "worker_general"), 1.1, "allow")],
                heavy=("ingest_long_context",))
    active = {"ingest_long_context": frozenset({"q0", "q1"})}
    candidates = [("worker_general", 1)]  # q0 — overlaps held q0
    pick = select_backfill_candidate(
        candidates, active, TrafficClass.BACKGROUND,
        instance_regions=_REGIONS, matrix=m,
    )
    assert pick is None


def test_priority_order_first_fit() -> None:
    """Candidates are tried in order; first disjoint+admissible wins. q0 (overlap)
    is skipped, q2 (disjoint, allow) is chosen."""
    m = _matrix(n_way=[(("ingest_long_context", "worker_general"), 1.1, "allow")],
                heavy=("ingest_long_context",))
    active = {"ingest_long_context": frozenset({"q0", "q1"})}
    candidates = [("worker_general", 1), ("worker_general", 3)]  # q0 then q2
    pick = select_backfill_candidate(
        candidates, active, TrafficClass.BACKGROUND,
        instance_regions=_REGIONS, matrix=m,
    )
    assert pick == ("worker_general", 3)


def test_skips_same_role_occupied_candidate_then_picks_later_admissible() -> None:
    """Same-role policy cannot override physical occupancy of an active quarter."""
    m = _matrix(
        n_way=[(("frontdoor", "worker_general"), 1.1, "allow")],
        same_role=[("frontdoor", "allow")],
    )
    active = {"frontdoor": frozenset({"q0"})}
    candidates = [("frontdoor", 1), ("worker_general", 3)]  # occupied q0, then disjoint q2

    pick = select_backfill_candidate(
        candidates, active, TrafficClass.BACKGROUND,
        instance_regions=_REGIONS, matrix=m,
    )

    assert pick == ("worker_general", 3)


def test_skips_disjoint_but_blocked_candidate() -> None:
    """Disjoint but measured-block n_way → not admissible → skipped."""
    m = _matrix(n_way=[(("ingest_long_context", "worker_general"), 0.5, "block")],
                heavy=("ingest_long_context",))
    active = {"ingest_long_context": frozenset({"q0", "q1"})}
    candidates = [("worker_general", 3)]  # q2 disjoint but blocked
    pick = select_backfill_candidate(
        candidates, active, TrafficClass.BACKGROUND,
        instance_regions=_REGIONS, matrix=m,
    )
    assert pick is None


def test_no_active_holders_picks_first() -> None:
    """Empty active set → admit_set ALLOWs → first candidate selected."""
    m = _matrix()
    pick = select_backfill_candidate(
        [("worker_general", 3)], {}, TrafficClass.BACKGROUND,
        instance_regions=_REGIONS, matrix=m,
    )
    assert pick == ("worker_general", 3)


def test_empty_candidates_returns_none() -> None:
    m = _matrix()
    assert select_backfill_candidate([], {"ingest_long_context": frozenset({"q0"})},
                                     TrafficClass.BACKGROUND,
                                     instance_regions=_REGIONS, matrix=m) is None


def test_unknown_candidate_placement_skipped_for_background() -> None:
    """A candidate whose (role, idx) has no region info → unknown placement →
    admit_set bg fails closed (QUEUE) → not selected."""
    m = _matrix()
    candidates = [("worker_general", 99)]  # unknown idx
    pick = select_backfill_candidate(
        candidates, {"ingest_long_context": frozenset({"q0"})},
        TrafficClass.BACKGROUND, instance_regions=_REGIONS, matrix=m,
    )
    assert pick is None


def test_multi_candidate_picks_first_admissible() -> None:
    """Two disjoint candidates, first is blocked, second allowed → picks second."""
    m = _matrix(
        n_way=[
            (("ingest_long_context", "vision_escalation"), 0.5, "block"),
            (("ingest_long_context", "worker_general"), 1.2, "allow"),
        ],
        heavy=("ingest_long_context",),
    )
    active = {"ingest_long_context": frozenset({"q0", "q1"})}
    # vision q2 (blocked) then worker_general q2 (allow)
    candidates = [("vision_escalation", 3), ("worker_general", 3)]
    pick = select_backfill_candidate(
        candidates, active, TrafficClass.BACKGROUND,
        instance_regions=_REGIONS, matrix=m,
    )
    assert pick == ("worker_general", 3)
