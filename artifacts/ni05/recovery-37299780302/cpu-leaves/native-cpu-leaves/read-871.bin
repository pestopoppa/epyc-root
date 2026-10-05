"""WP-1 tests: topology-derived safe-N for autopilot fan-out.

`compute_max_safe_concurrency(numa_config, role)` is the pure function under
test; `max_safe_concurrency(role)` is the live wrapper (covered indirectly
via the production NUMA_CONFIG smoke).
"""

from __future__ import annotations

import pytest

from src.runtime.instance_topology import (
    compute_max_disjoint_live_concurrency,
    compute_max_safe_concurrency,
    max_safe_concurrency,
)


# ── Property: safe-N is always ≥1 ──────────────────────────────────────


@pytest.mark.parametrize(
    "cfg",
    [
        {},
        {"role_x": {}},
        {"role_x": {"instances": []}},
        {"role_x": {"instances": [("0-23", 8080, 24)]}},
        {"role_x": {"instances": [("garbage-cpu-list", 8080, 24)]}},
        {"role_x": {"instances": [(None, 8080, 24)]}},  # malformed
    ],
)
def test_safe_n_always_at_least_one(cfg: dict) -> None:
    assert compute_max_safe_concurrency(cfg, "role_x") >= 1
    assert compute_max_safe_concurrency(cfg, "missing_role") == 1
    assert compute_max_safe_concurrency(None, "anything") == 1  # type: ignore[arg-type]


# ── Frontdoor shape: full=NUMA_NODE0, q2/q3 disjoint, q0/q1 overlap ────


def test_frontdoor_shape_safe_n_is_3() -> None:
    """Frontdoor's full=NUMA_NODE0 covers q0+q1; quarters q2/q3 disjoint."""
    cfg = {
        "frontdoor": {
            "instances": [
                ("0-47,96-143", 8070, 96),   # full (NUMA_NODE0 → q0+q1)
                ("0-23,96-119", 8080, 48),   # q0_inst → q0 (overlap)
                ("24-47,120-143", 8180, 48),  # q1_inst → q1 (overlap)
                ("48-71,144-167", 8280, 48),  # q2_inst → q2 (disjoint)
                ("72-95,168-191", 8380, 48),  # q3_inst → q3 (disjoint)
            ],
        },
    }
    assert compute_max_safe_concurrency(cfg, "frontdoor") == 3


def test_full_machine_role_safe_n_is_1() -> None:
    """Roles whose full covers 0-95 have no disjoint quarter; safe-N = 1."""
    cfg = {
        "worker_general": {
            "instances": [
                ("0-95", 8072, 96),         # full (q0+q1+q2+q3 — covers all)
                ("0-23,96-119", 8082, 48),
                ("24-47,120-143", 8182, 48),
                ("48-71,144-167", 8282, 48),
                ("72-95,168-191", 8382, 48),
            ],
        },
    }
    assert compute_max_safe_concurrency(cfg, "worker_general") == 1


def test_full_machine_role_live_quarter_fleet_safe_n_is_4() -> None:
    """A quarter-only v7 fleet is not bounded by the legacy full-first cap."""
    cfg = {
        "worker_general": {
            "instances": [
                ("0-95", 8072, 96),          # full, not live in quarter mode
                ("0-23,96-119", 8082, 48),   # q0
                ("24-47,120-143", 8182, 48),  # q1
                ("48-71,144-167", 8282, 48),  # q2
                ("72-95,168-191", 8382, 48),  # q3
            ],
        },
    }
    assert compute_max_safe_concurrency(cfg, "worker_general") == 1
    assert (
        compute_max_disjoint_live_concurrency(
            cfg,
            "worker_general",
            live_ports={8082, 8182, 8282, 8382},
        )
        == 4
    )


def test_frontdoor_live_quarter_fleet_safe_n_is_4() -> None:
    """Frontdoor full-first safe-N is 3, quarter-only live fleet is 4."""
    cfg = {
        "frontdoor": {
            "instances": [
                ("0-47,96-143", 8070, 96),
                ("0-23,96-119", 8080, 48),
                ("24-47,120-143", 8180, 48),
                ("48-71,144-167", 8280, 48),
                ("72-95,168-191", 8380, 48),
            ],
        },
    }
    assert compute_max_safe_concurrency(cfg, "frontdoor") == 3
    assert (
        compute_max_disjoint_live_concurrency(
            cfg,
            "frontdoor",
            live_ports={8080, 8180, 8280, 8380},
        )
        == 4
    )


def test_single_instance_role_safe_n_is_1() -> None:
    """Single-instance roles (architect_general, worker_vision) → 1."""
    for cpu_list in ("0-95", "24-47,120-143", "48-71"):
        cfg = {"role_x": {"instances": [(cpu_list, 9999, 48)]}}
        assert compute_max_safe_concurrency(cfg, "role_x") == 1


def test_quarters_only_role_uses_largest_disjoint_set() -> None:
    """Role with no full instance but 4 disjoint quarters: greedy picks all 4.

    Note: NUMA_CONFIG convention is "instance 0 = full"; this test verifies
    the function degrades sensibly when 'instance 0' is actually a quarter.
    """
    cfg = {
        "quartered_role": {
            "instances": [
                ("0-23,96-119", 8080, 48),   # "instance 0" (treated as full)
                ("24-47,120-143", 8081, 48),  # disjoint from instance 0
                ("48-71,144-167", 8082, 48),  # disjoint from 0+1
                ("72-95,168-191", 8083, 48),  # disjoint from 0+1+2
            ],
        },
    }
    # Greedy: instance 0 (q0) + 1 (q1) + 2 (q2) + 3 (q3) = 4
    assert compute_max_safe_concurrency(cfg, "quartered_role") == 4


def test_partial_overlap_skips_overlapping_quarters() -> None:
    """Full = NUMA_NODE0 (q0+q1); q1-only quarter overlaps full and is skipped;
    q2-only and q3-only quarters are accepted."""
    cfg = {
        "partial": {
            "instances": [
                ("0-47", 8000, 48),     # full → q0+q1
                ("24-47", 8001, 24),    # overlaps full (q1)
                ("48-71", 8002, 24),    # disjoint (q2)
                ("72-95", 8003, 24),    # disjoint (q3)
            ],
        },
    }
    assert compute_max_safe_concurrency(cfg, "partial") == 3  # full + q2 + q3


def test_preference_order_visits_disjoint_first() -> None:
    """When quarters are reordered with overlapping ones first, the greedy
    still picks all disjoint quarters thanks to NUMA-disjoint sorting."""
    cfg = {
        "reordered": {
            "instances": [
                ("0-47", 8000, 48),     # full
                ("48-71", 8001, 24),    # disjoint (listed first)
                ("24-47", 8002, 24),    # overlaps full (listed second)
                ("0-23", 8003, 24),     # overlaps full
                ("72-95", 8004, 24),    # disjoint
            ],
        },
    }
    assert compute_max_safe_concurrency(cfg, "reordered") == 3  # full + q2 + q3


def test_empty_full_cpulist_falls_back_to_1() -> None:
    """If 'full' instance has an unparseable cpu_list, return 1 conservatively."""
    cfg = {
        "broken": {
            "instances": [
                ("", 8000, 48),
                ("48-71", 8001, 24),
            ],
        },
    }
    assert compute_max_safe_concurrency(cfg, "broken") == 1


# ── Live wrapper smoke ─────────────────────────────────────────────────


def test_live_wrapper_returns_at_least_1_for_unknown_role() -> None:
    # max_safe_concurrency may import production NUMA_CONFIG; unknown role
    # path always returns 1.
    assert max_safe_concurrency("definitely_not_a_real_role_xyz") >= 1


def test_live_wrapper_caches_results() -> None:
    """Repeated calls for the same role hit the per-process cache."""
    a = max_safe_concurrency("frontdoor")
    b = max_safe_concurrency("frontdoor")
    assert a == b
    assert a >= 1
