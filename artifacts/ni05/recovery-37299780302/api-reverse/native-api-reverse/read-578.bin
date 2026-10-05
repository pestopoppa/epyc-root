"""Objective-dimensionality guard for the Pareto archive + its `pareto_math` primitives.

`dominates()` (src/autopilot_core/pareto_math.py) already raises on a dimensionality
mismatch — its docstring explains that `zip` truncates to the shorter sequence, so
comparing objective tuples built under DIFFERENT objective policies (e.g. a 3D
"task_rate_3d_v1" shadow vector against the live 4D vector) used to return a confident,
meaningless answer instead of refusing to compare.

`hypervolume()` had the identical hazard, unguarded: its own `zip(point, ref_tuple)`
filter truncates the same way. Worse, the guard `dominates()` added is not even ALWAYS
reached: `ParetoArchive._rebuild_frontier` / `.update()` call `dominates()` only inside
`any(... for existing in <tier's current frontier>)` comprehensions. For the FIRST entry
admitted to a tier, that frontier is `[]`, so `any(...)` short-circuits to False and
`dominates()` is never invoked — an unchecked entry is appended straight onto the
frontier and flows into `hypervolume()`.

These tests cover both the low-level primitives directly AND the real path: a
dimensionally-wrong FIRST entry of a tier, admitted through `ParetoArchive` exactly as
production code would (state-file load / `.update()`), never a bare call to
`hypervolume()` in isolation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from src.autopilot_core.pareto_math import (
    hypervolume,
    hypervolume_monte_carlo,
    median_objectives,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from pareto_archive import ParetoArchive, ParetoEntry  # noqa: E402


# ── pareto_math.py primitives, direct calls ──────────────────────────────────


def test_hypervolume_raises_on_point_shorter_than_reference():
    """A 3D point ('task_rate_3d_v1' shadow shape) against the live 4D reference point.

    Before the fix, the exact inclusion-exclusion branch's `point[dim]` indexing (dim
    ranging over the REFERENCE point's length) raised an opaque, contextless
    `IndexError` for this direction of mismatch — a crash, not a clean diagnostic.
    """
    with pytest.raises(ValueError, match="dimensionality mismatch"):
        hypervolume([(1.5, 40.0, -0.4)], ref=(0.0, 0.0, -1.0, 0.0))


def test_hypervolume_raises_on_point_longer_than_reference():
    """A point with an extra axis against a shorter reference point.

    Before the fix, this direction of mismatch did NOT crash — `zip` truncated the
    filter to the reference point's length and `point[dim]` never ran out of bounds
    (the reference point is the shorter one), so `hypervolume()` returned a confident,
    silently-wrong number (32.4 for this exact input) instead of raising.
    """
    with pytest.raises(ValueError, match="dimensionality mismatch"):
        hypervolume([(1.5, 40.0, -0.4, 0.9, 999.0)], ref=(0.0, 0.0, -1.0, 0.0))


def test_hypervolume_monte_carlo_raises_on_dimensionality_mismatch():
    """Same guard on the large-frontier Monte Carlo branch (its own `point[dim]`
    indexing has the identical shorter/longer hazard as the exact branch)."""
    with pytest.raises(ValueError, match="dimensionality mismatch"):
        hypervolume_monte_carlo(
            [(1.5, 40.0, -0.4, 0.9, 999.0)], ref=(0.0, 0.0, -1.0, 0.0), samples=10
        )


def test_median_objectives_raises_on_ragged_cluster():
    """`zip(*rows)` truncates to the shortest row — a sibling of the same defect class
    in the same module, on the reproduction-cluster median path."""
    with pytest.raises(ValueError, match="dimensionality mismatch"):
        median_objectives([(1.5, 40.0, -0.4, 0.9), (1.6, 41.0, -0.4)])


def test_hypervolume_still_works_for_consistent_dimensionality():
    """The guard must not break the ordinary, well-formed case."""
    hv = hypervolume([(1.5, 40.0, -0.4, 0.9)], ref=(0.0, 0.0, -1.0, 0.0))
    assert hv == pytest.approx(1.5 * 40.0 * 0.6 * 0.9)


# ── Real path: a dimensionally-wrong FIRST entry of a tier, via ParetoArchive ──


def _entry(trial_id: int, *, tier: int, objectives: tuple[float, ...]) -> ParetoEntry:
    return ParetoEntry(trial_id=trial_id, objectives=objectives, eval_tier=tier)


def test_first_entry_of_tier_wrong_dimensionality_excluded_on_state_load(tmp_path: Path):
    """The bulk/reload path (`ParetoArchive(state_path=...)` -> `_load()` ->
    `_rebuild_frontier()`), exactly as production hits on process start.

    A malformed 3D entry is the ONLY entry for T1, so `_rebuild_frontier`'s
    `rebuilt = by_tier.setdefault(1, [])` starts empty and
    `any(existing.dominates(entry) for existing in rebuilt)` short-circuits to False —
    `dominates()` is never called, reproducing the empty-list bypass. Before the fix,
    this entry landed on the frontier and `archive.hypervolume(tier=1)` would silently
    truncate/crash. After the fix, it must be excluded from the frontier and the tier's
    hypervolume must be the clean empty-frontier 0.0, with no exception raised (bulk
    reconstruction must not abort archive load over one bad historical record).
    """
    state_path = tmp_path / "state.json"
    bad = _entry(1, tier=1, objectives=(1.5, 40.0, -0.4)).to_dict()  # 3D, T1 expects 4D
    state_path.write_text(json.dumps({
        "trial_counter": 1,
        "pareto_archive": {"all_entries": [bad]},
    }))

    archive = ParetoArchive(state_path=state_path)

    assert archive.frontier(tier=1) == []
    assert archive.hypervolume(tier=1) == 0.0
    # Audit trail is preserved even though the entry never reaches any frontier.
    assert [e.trial_id for e in archive._all_entries] == [1]


def test_update_raises_on_first_entry_dimensionality_mismatch(tmp_path: Path):
    """The live single-trial path (`ParetoArchive.update()`), first entry of a fresh
    tier. `is_pareto_candidate` walks `self._front(tier)`, which is `[]` for a brand
    new tier, so `dominates()` is never invoked here either — same bypass, different
    entry point. `update()` must raise (unlike the bulk loader) so a caller does not
    silently admit a corrupt entry onto a live frontier.
    """
    archive = ParetoArchive(state_path=tmp_path / "state.json")
    bad = _entry(1, tier=1, objectives=(1.5, 40.0, -0.4))  # 3D, T1 expects 4D

    with pytest.raises(ValueError, match="dimensionality mismatch"):
        archive.update(bad)

    # The raise happens BEFORE any frontier mutation, so a caller catching this broadly
    # (as the exogenous-restart Pareto re-import in autopilot.py does) is left with a
    # clean, untouched frontier rather than one partially updated then abandoned.
    assert archive.frontier(tier=1) == []
    assert archive.hypervolume_trend(tier=1) == []
    # The audit trail (`_all_entries`) still records the attempt.
    assert [e.trial_id for e in archive._all_entries] == [1]


def test_update_still_admits_well_formed_first_entry_of_a_tier(tmp_path: Path):
    """The guard must not break the ordinary, well-formed first-entry-of-a-tier case
    that `any(... for existing in [])` -> False -> append was always meant to allow."""
    archive = ParetoArchive(state_path=tmp_path / "state.json")
    good = _entry(1, tier=1, objectives=(1.5, 40.0, -0.4, 0.9))  # 4D, matches T1

    status = archive.update(good)

    assert status == "frontier"
    assert [e.trial_id for e in archive.frontier(tier=1)] == [1]
    assert archive.hypervolume(tier=1) > 0.0
