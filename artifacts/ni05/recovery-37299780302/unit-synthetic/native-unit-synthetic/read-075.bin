"""Tests for the ParetoArchive.bt_tiebreak_topk method (AP-38).

AP-38 added a zero-inference Bradley-Terry diagnostic that aggregates top-K
Pareto frontier entries via axis-wise pairwise comparison. J13 later removed
the cosmetic live-planner prompt hint, so these tests cover the offline
aggregation helper itself rather than prompt integration.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUTOPILOT_DIR))

pareto_archive = importlib.import_module("pareto_archive")
ParetoArchive = pareto_archive.ParetoArchive
ParetoEntry = pareto_archive.ParetoEntry


def _make_entry(trial_id: int, q: float, sp: float, neg_cost: float, rel: float) -> ParetoEntry:
    return ParetoEntry(
        trial_id=trial_id,
        objectives=(q, sp, neg_cost, rel),
        eval_tier=1,
    )


def _archive_with(entries: list[ParetoEntry]) -> ParetoArchive:
    a = ParetoArchive(state_path=Path("/tmp/_test_archive_does_not_exist.json"))
    # Bypass file IO; inject directly into the canonical-tier (T1) frontier (per-tier schema).
    a._frontiers = {1: list(entries)}
    a._all_entries = list(entries)
    return a


def test_empty_frontier_returns_safe_default():
    a = ParetoArchive(state_path=Path("/tmp/_test_archive_empty.json"))
    out = a.bt_tiebreak_topk(k=5)
    assert out["ranking"] == []
    assert "skipped" in out["note"]


def test_singleton_frontier_returns_safe_default():
    a = _archive_with([_make_entry(1, 2.0, 50.0, -0.1, 0.9)])
    out = a.bt_tiebreak_topk(k=5)
    assert out["ranking"] == [1]
    assert "skipped" in out["note"]


def test_two_entry_frontier_runs_and_returns_ranking():
    a = _archive_with([
        _make_entry(1, 3.0, 50.0, -0.1, 0.9),
        _make_entry(2, 2.0, 30.0, -0.2, 0.7),
    ])
    out = a.bt_tiebreak_topk(k=5)
    assert set(out["ranking"]) == {1, 2}
    # #1 dominates on all axes, so BT must rank it first.
    assert out["ranking"][0] == 1
    assert out["converged"]


def test_axis_wise_disagreement_surfaced():
    """A candidate that beats peers on more axes pairwise should be
    picked by BT even when the *range-normalized* naive sum picks
    differently. That disagreement is the value of this method.

    Setup (post scale-bias fix 2026-05-27): each candidate specializes
    in a different axis or pair, so no single one dominates the
    range-normalized sum. BT must surface the candidate that wins the
    most pairwise comparisons.

      Trial 100: q-specialist          (q=4 top)
      Trial 101: sp-specialist         (sp=80 top)
      Trial 102: cost+rel-specialist   (cost=-0.1 top, rel=0.9 top)

    Range-normalized sum: 102 > 101 > 100 → naive-top = 102.
    Axis-wise pairwise wins: 100 (q wins broadly) > 102 > 101 → BT-top = 100.
    """
    a = _archive_with([
        _make_entry(100, 4.0, 40.0, -0.3, 0.5),  # q-specialist
        _make_entry(101, 3.0, 80.0, -0.4, 0.4),  # sp-specialist
        _make_entry(102, 3.0, 30.0, -0.1, 0.9),  # cost+rel-specialist
    ])
    out = a.bt_tiebreak_topk(k=3)
    assert out["top_k_trial_ids"][0] == 102, "test setup invariant: range-normalized naive-top is trial 102"
    assert out["ranking"][0] == 100, "BT must pick trial 100 (q-specialist wins the most axis-pair comparisons)"
    assert "disagrees" in out["note"] or "BT picks" in out["note"]


def test_topk_selection_is_range_normalized_not_scale_biased():
    """Regression for the 2026-05-27 scale-bias fix.

    Before the fix, top-K candidate selection used raw sum-of-(obj − ref)
    which let high-magnitude axes (e.g., speed in t/s, range 0-100+)
    dominate vs low-magnitude axes (e.g., reliability in [0,1]).

    Setup:
      Trial 200: ONLY wins on speed (sp=100, very high magnitude).
                 OLD raw-sum would pick this as naive-top.
      Trial 201: balanced winner — wins on q, cost, rel (3 of 4 axes).
                 NEW range-normalized sum picks this correctly.

    Post-fix: naive-top must be 201 (the balanced winner), and BT
    must agree with it because 201 wins 3 of 4 axes pairwise.
    """
    a = _archive_with([
        _make_entry(200, 1.0, 100.0, -0.9, 0.1),  # speed-only
        _make_entry(201, 4.0, 30.0, -0.1, 0.9),   # balanced 3-of-4 winner
    ])
    out = a.bt_tiebreak_topk(k=2)
    assert out["top_k_trial_ids"][0] == 201, (
        "post-fix: range-normalized top-K must put trial 201 first "
        "(it wins 3 of 4 axes; trial 200's very-high speed must not swamp the sum)"
    )
    assert out["ranking"][0] == 201


def test_k_caps_at_frontier_size():
    """Asking for k > frontier_size should not raise; uses all available."""
    a = _archive_with([
        _make_entry(1, 3.0, 50.0, -0.1, 0.9),
        _make_entry(2, 2.0, 60.0, -0.2, 0.8),
    ])
    out = a.bt_tiebreak_topk(k=10)
    assert len(out["ranking"]) == 2


def test_uniform_axes_all_ties():
    """Pathological case: all entries equal on every axis → BT must not crash;
    ranking is arbitrary but every log_skill is ~0 and convergence holds."""
    a = _archive_with([
        _make_entry(1, 2.0, 50.0, -0.1, 0.8),
        _make_entry(2, 2.0, 50.0, -0.1, 0.8),
        _make_entry(3, 2.0, 50.0, -0.1, 0.8),
    ])
    out = a.bt_tiebreak_topk(k=3)
    assert out["converged"]
    for ls in out["log_skills"].values():
        assert abs(ls) < 1e-6


def test_log_skill_anchor_is_zero():
    a = _archive_with([
        _make_entry(1, 4.0, 60.0, -0.1, 0.9),
        _make_entry(2, 3.0, 50.0, -0.2, 0.8),
        _make_entry(3, 2.0, 40.0, -0.3, 0.7),
    ])
    out = a.bt_tiebreak_topk(k=3)
    assert min(out["log_skills"].values()) == 0.0


def test_dominance_skew_warning_propagates_through_archive_method():
    """If one frontier entry sweeps the field, the warning must surface."""
    a = _archive_with([
        _make_entry(1, 10.0, 100.0, 0.0, 1.0),  # dominates on every axis
        _make_entry(2, 1.0, 10.0, -0.5, 0.1),
        _make_entry(3, 1.0, 10.0, -0.5, 0.1),
        _make_entry(4, 1.0, 10.0, -0.5, 0.1),
    ])
    out = a.bt_tiebreak_topk(k=4)
    assert out["ranking"][0] == 1
    assert any("dominance skew" in w for w in out["warnings"])
