"""Audit P1: exact-region snapshot helper `held_regions_by_role`.

`active_region_holders` is an ATTRIBUTION view: it marks an instance "active" if
ANY of its regions is held (matching how an instance acquires the union of its
region locks). That OVER-REPORTS for shape-aware decisions — a held quarter q0
makes the role's `full` instance (which contains q0) also report active, even
though only q0's physical region is actually locked.

`held_regions_by_role` is the EXACT view: {role: frozenset(regions that have a
held lock)}. These tests prove the exact view AND that the legacy attribution
function's semantics are unchanged (no regression to active_region_holders).

Real OS flock via tmp_path so the /proc/locks scan is genuine, not mocked.
"""

from __future__ import annotations

import fcntl
from pathlib import Path

from src.runtime.cpu_region_lock import (
    active_region_holder_instances,
    active_region_holders,
    held_regions_by_role,
    region_lock_path,
)


# frontdoor: full(0)={q0,q1}; q0 inst(1)={q0}; q1 inst(2)={q1}; q2(3)={q2}; q3(4)={q3}
_FRONTDOOR_REGIONS = {
    ("frontdoor", 0): frozenset({"q0", "q1"}),
    ("frontdoor", 1): frozenset({"q0"}),
    ("frontdoor", 2): frozenset({"q1"}),
    ("frontdoor", 3): frozenset({"q2"}),
    ("frontdoor", 4): frozenset({"q3"}),
}


def _hold(tmp_path: Path, role: str, region: str):
    """Acquire a real flock on the (role, region) lock file; return the open fh
    (caller keeps it open to hold the lock, closes to release)."""
    p = region_lock_path(role, region)
    p.parent.mkdir(parents=True, exist_ok=True)
    fh = open(p, "a+b")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
    return fh


def test_held_regions_exact_no_holders(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
    assert held_regions_by_role(instance_regions=_FRONTDOOR_REGIONS) == {}


def test_held_regions_reports_only_the_locked_region(tmp_path, monkeypatch) -> None:
    """Hold ONLY q0. Exact view = {frontdoor: {q0}} — NOT q1/full's other
    regions. This is the over-reporting `active_region_holders` cannot avoid."""
    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
    fh = _hold(tmp_path, "frontdoor", "q0")
    try:
        exact = held_regions_by_role(instance_regions=_FRONTDOOR_REGIONS)
        assert exact == {"frontdoor": frozenset({"q0"})}
    finally:
        fh.close()


def test_active_region_holders_overreports_same_scenario(tmp_path, monkeypatch) -> None:
    """Contrast: with ONLY q0 held, the legacy attribution view reports BOTH
    the q0 instance (idx 1) AND the full instance (idx 0, since it contains q0).
    This documents WHY the exact view is needed — and pins legacy semantics so
    the new helper is proven not to have changed them."""
    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
    fh = _hold(tmp_path, "frontdoor", "q0")
    try:
        attribution = active_region_holders(instance_regions=_FRONTDOOR_REGIONS)
        # full (0) and q0 (1) both contain q0 → both reported active.
        assert attribution == {"frontdoor": [0, 1]}
    finally:
        fh.close()


def test_active_holder_instances_reports_exact_single_quarter(tmp_path, monkeypatch) -> None:
    """Exact holder-instance view resolves the owning PID's shape, not every
    overlapping configured shape."""
    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
    fh = _hold(tmp_path, "frontdoor", "q0")
    try:
        assert active_region_holder_instances(instance_regions=_FRONTDOOR_REGIONS) == {"frontdoor": [1]}
    finally:
        fh.close()


def test_active_holder_instances_collapses_full_shape_mtp_holder(tmp_path, monkeypatch) -> None:
    """A single full-shape worker holding all four regions is one active
    holder instance. The legacy attribution view still reports all overlapping
    shapes, which is exactly what dashboard metrics must avoid."""
    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
    regions = {
        ("worker_general", 0): frozenset({"q0", "q1", "q2", "q3"}),
        ("worker_general", 1): frozenset({"q0"}),
        ("worker_general", 2): frozenset({"q1"}),
        ("worker_general", 3): frozenset({"q2"}),
        ("worker_general", 4): frozenset({"q3"}),
    }
    fhs = [_hold(tmp_path, "worker_general", region) for region in ("q0", "q1", "q2", "q3")]
    try:
        assert active_region_holders(instance_regions=regions) == {"worker_general": [0, 1, 2, 3, 4]}
        assert active_region_holder_instances(instance_regions=regions) == {"worker_general": [0]}
    finally:
        for fh in fhs:
            fh.close()


def test_exact_vs_attribution_diverge(tmp_path, monkeypatch) -> None:
    """Side-by-side on the same lock state: exact = {q0}; attribution = idxs
    [0,1]. Same physical truth, different (correct-for-purpose) projections."""
    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
    fh = _hold(tmp_path, "frontdoor", "q0")
    try:
        exact = held_regions_by_role(instance_regions=_FRONTDOOR_REGIONS)
        attribution = active_region_holders(instance_regions=_FRONTDOOR_REGIONS)
        assert exact == {"frontdoor": frozenset({"q0"})}
        assert attribution == {"frontdoor": [0, 1]}
    finally:
        fh.close()


def test_held_regions_multiple_regions_one_role(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
    fh0 = _hold(tmp_path, "frontdoor", "q0")
    fh3 = _hold(tmp_path, "frontdoor", "q3")
    try:
        exact = held_regions_by_role(instance_regions=_FRONTDOOR_REGIONS)
        assert exact == {"frontdoor": frozenset({"q0", "q3"})}
    finally:
        fh0.close()
        fh3.close()


def test_held_regions_cross_role(tmp_path, monkeypatch) -> None:
    """Two roles holding different regions → exact per-role region sets."""
    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
    regions = {
        **_FRONTDOOR_REGIONS,
        ("ingest_long_context", 0): frozenset({"q0", "q1"}),
        ("ingest_long_context", 3): frozenset({"q2"}),
    }
    fh_fd = _hold(tmp_path, "frontdoor", "q0")
    fh_ing = _hold(tmp_path, "ingest_long_context", "q2")
    try:
        exact = held_regions_by_role(instance_regions=regions)
        assert exact == {
            "frontdoor": frozenset({"q0"}),
            "ingest_long_context": frozenset({"q2"}),
        }
    finally:
        fh_fd.close()
        fh_ing.close()


def test_held_regions_empty_instance_regions(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
    assert held_regions_by_role(instance_regions={}) == {}
