"""Tests for the shared Bradley-Terry pairwise-ranking module.

Covers the cross-handoff invariant noted in:
  - handoffs/active/autopilot-continuous-optimization.md § P17 (AP-37)
  - handoffs/active/decision-aware-routing.md § DAR-6.4
  - handoffs/active/swarm-dataset-distillation.md § Phase 3

This is the one BT implementation; do not duplicate it in any of the three
consumer call sites.
"""

from __future__ import annotations

import importlib
import sys
from math import isclose
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# bradley_terry lives in src/ (moved 2026-05-27 as part of DAR-6 scaffolding).
bt = importlib.import_module("src.bradley_terry")


# ── basic ranking ───────────────────────────────────────────────


def test_trivial_inputs():
    """Empty and singleton inputs must not raise and must converge instantly."""
    r = bt.bradley_terry_rank([], {})
    assert r.ranking == []
    assert r.converged
    assert r.iterations == 0

    r = bt.bradley_terry_rank(["only"], {})
    assert r.ranking == ["only"]
    assert r.converged


def test_linear_order_two_items():
    """A always beats B → ranking [A, B], A's log-skill > B's."""
    r = bt.bradley_terry_rank(["A", "B"], {("A", "B"): 10.0})
    assert r.ranking == ["A", "B"]
    assert r.log_skills["A"] > r.log_skills["B"]
    assert r.converged
    assert r.comparison_graph_connected


def test_linear_order_four_items_transitive():
    """A>B>C>D with strict pairwise wins — BT must recover the linear order."""
    pairs = []
    # Each higher item beats each lower item once.
    items = ["A", "B", "C", "D"]
    for i, hi in enumerate(items):
        for lo in items[i + 1:]:
            pairs.append((hi, lo))
    r = bt.bradley_terry_from_pairs(items, pairs)
    assert r.ranking == ["A", "B", "C", "D"]
    # Strict monotone decrease in log-skill.
    for hi, lo in zip(r.ranking, r.ranking[1:]):
        assert r.log_skills[hi] > r.log_skills[lo]
    assert r.converged


def test_anchor_is_zero_for_lowest():
    """The anchor convention is min(log_skills) == 0."""
    pairs = [("A", "B"), ("A", "B"), ("A", "B")]
    r = bt.bradley_terry_from_pairs(["A", "B"], pairs)
    assert isclose(min(r.log_skills.values()), 0.0, abs_tol=1e-9)


# ── from-scores wrapper ────────────────────────────────────────


def test_from_scores_symmetric_inference():
    """Giving only (A,B):0.8 should imply (B,A):0.2 — A still ranks first."""
    r = bt.bradley_terry_from_scores(["A", "B"], {("A", "B"): 0.8})
    assert r.ranking == ["A", "B"]


def test_from_scores_clips_invalid():
    """Scores outside [0,1] are clipped; NaN/inf are dropped silently."""
    r = bt.bradley_terry_from_scores(["A", "B"], {("A", "B"): 1.5, ("B", "A"): 0.0})
    assert r.ranking[0] == "A"
    # Should not have raised, should have converged.
    assert r.converged


def test_from_scores_both_directions_count_independently():
    """When both directions are given they each contribute (judge ran twice)."""
    r = bt.bradley_terry_from_scores(
        ["A", "B"],
        {("A", "B"): 0.9, ("B", "A"): 0.9},  # contradictory judgments
    )
    # Should converge; A vs B are roughly tied since both judgments are equally strong.
    assert r.converged
    gap = abs(r.log_skills["A"] - r.log_skills["B"])
    assert gap < 0.5  # roughly tied (would be 0 with perfectly symmetric data)


# ── diagnostics ────────────────────────────────────────────────


def test_disconnected_graph_flagged():
    """Two disjoint pairs → graph disconnected → flag set, no exception."""
    pairs = [("A", "B"), ("C", "D")]
    r = bt.bradley_terry_from_pairs(["A", "B", "C", "D"], pairs)
    assert not r.comparison_graph_connected
    assert any("disconnected" in w for w in r.warnings)


def test_condorcet_cycle_flagged():
    """Rock-paper-scissors style: A>B, B>C, C>A — cycle must be detected."""
    pairs = [
        ("A", "B"), ("A", "B"), ("A", "B"),
        ("B", "C"), ("B", "C"), ("B", "C"),
        ("C", "A"), ("C", "A"), ("C", "A"),
    ]
    r = bt.bradley_terry_from_pairs(["A", "B", "C"], pairs)
    assert r.condorcet_cycles, "expected at least one Condorcet cycle"
    assert any("Condorcet" in w for w in r.warnings)


def test_dominance_skew_flagged():
    """One item sweeps the field → dominance_skew > 3 → capability-skew warning."""
    # A beats B, C, D each 50 times. B, C, D never play each other.
    pairs = []
    for opp in ["B", "C", "D"]:
        pairs.extend([("A", opp)] * 50)
    r = bt.bradley_terry_from_pairs(["A", "B", "C", "D"], pairs)
    assert r.ranking[0] == "A"
    assert r.dominance_skew > 3.0
    assert any("dominance skew" in w for w in r.warnings)


def test_transitive_data_has_no_cycles():
    """A clean linear order should never report a Condorcet cycle."""
    pairs = [
        ("A", "B"), ("B", "C"), ("C", "D"),
        ("A", "C"), ("A", "D"), ("B", "D"),
    ]
    r = bt.bradley_terry_from_pairs(["A", "B", "C", "D"], pairs)
    assert r.condorcet_cycles == []


# ── numerical robustness ───────────────────────────────────────


def test_regularization_handles_zero_wins():
    """An item with zero wins should still receive a finite low score."""
    r = bt.bradley_terry_from_pairs(["A", "B"], [("A", "B")] * 100)
    # B has zero wins but the regularization prior keeps its log-skill finite.
    assert r.log_skills["B"] >= 0.0  # >= floor (anchor) by construction
    assert r.log_skills["A"] > r.log_skills["B"]
    for v in r.log_skills.values():
        assert v == v  # not NaN
        assert v < float("inf")


def test_continuous_weights_not_just_integer_counts():
    """Fractional weights (e.g., from continuous judge scores) work the same."""
    r = bt.bradley_terry_rank(
        ["A", "B", "C"],
        {("A", "B"): 0.7, ("B", "A"): 0.3, ("A", "C"): 0.9, ("C", "A"): 0.1, ("B", "C"): 0.6, ("C", "B"): 0.4},
    )
    assert r.ranking == ["A", "B", "C"]
    assert r.converged


def test_convergence_in_reasonable_iterations():
    """With well-conditioned data Zermelo converges quickly (<200 iters)."""
    pairs = []
    items = list(range(8))
    # Each higher index beats each lower index 5 times.
    for hi in items:
        for lo in items:
            if hi > lo:
                pairs.extend([(hi, lo)] * 5)
    r = bt.bradley_terry_from_pairs(items, pairs)
    assert r.converged
    assert r.iterations < 200
    assert r.ranking == sorted(items, reverse=True)


# ── invariance ────────────────────────────────────────────────


def test_ranking_invariant_to_item_input_order():
    """Permuting the items list does not change the relative ranking."""
    pairs = [("A", "B"), ("A", "B"), ("B", "C"), ("A", "C")]
    r1 = bt.bradley_terry_from_pairs(["A", "B", "C"], pairs)
    r2 = bt.bradley_terry_from_pairs(["C", "B", "A"], pairs)
    r3 = bt.bradley_terry_from_pairs(["B", "A", "C"], pairs)
    assert r1.ranking == r2.ranking == r3.ranking


def test_ranking_scale_invariant():
    """Scaling all win counts by a constant does not change the ranking."""
    base = {("A", "B"): 3.0, ("A", "C"): 2.0, ("B", "C"): 1.5}
    r1 = bt.bradley_terry_rank(["A", "B", "C"], base)
    scaled = {k: v * 100 for k, v in base.items()}
    r2 = bt.bradley_terry_rank(["A", "B", "C"], scaled)
    assert r1.ranking == r2.ranking
