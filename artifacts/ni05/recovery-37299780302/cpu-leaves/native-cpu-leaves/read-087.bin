"""Tests for ParetoArchive.parent_utility_ranking / parent_utility_text (AP-ME-2).

AP-ME-2 adds a computed, ALWAYS-ON parent utility (port of aira-evo
`compute_parent_utilities`, intake-1024 / parent paper intake-940) over
normalized score, positive-only gain over the strongest parent, and
method-family novelty 1/sqrt(1+N_f). Uses the SHIPPED weights
score 1.0 / delta 0.4 / novelty 0.25 — NOT the paper's prose 1.0/0.6/0.3.
Islands are inactive in every shipped profile, so no island machinery is ported.
"""

from __future__ import annotations

import importlib
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUTOPILOT_DIR))

pareto_archive = importlib.import_module("pareto_archive")
ParetoArchive = pareto_archive.ParetoArchive
ParetoEntry = pareto_archive.ParetoEntry


def _make_entry(
    trial_id: int,
    q: float,
    sp: float,
    neg_cost: float,
    rel: float,
    *,
    parent_trial: int | None = None,
    action: str = "code_mutation",
) -> ParetoEntry:
    return ParetoEntry(
        trial_id=trial_id,
        objectives=(q, sp, neg_cost, rel),
        eval_tier=1,
        parent_trial=parent_trial,
        reasoning=f'{{"type": "{action}"}}',
    )


def _archive_with(entries: list[ParetoEntry]) -> ParetoArchive:
    a = ParetoArchive(state_path=Path("/tmp/_test_parent_utility_does_not_exist.json"))
    a._frontiers = {1: list(entries)}
    a._all_entries = list(entries)
    return a


def test_empty_frontier_returns_empty():
    a = ParetoArchive(state_path=Path("/tmp/_test_parent_utility_empty.json"))
    assert a.parent_utility_ranking() == []
    assert "no candidate parents" in a.parent_utility_text()


def test_shipped_weights_are_used_not_paper_prose():
    # The task pins the SHIPPED weights; the paper's 1.0/0.6/0.3 must not leak in.
    assert ParetoArchive.PARENT_UTILITY_WEIGHTS == {
        "score": 1.0,
        "delta": 0.4,
        "novelty": 0.25,
    }


def test_single_candidate_has_unit_components():
    a = _archive_with([_make_entry(1, 2.0, 50.0, -0.1, 0.9)])
    out = a.parent_utility_ranking()
    assert len(out) == 1
    r = out[0]
    assert r["trial_id"] == 1
    # Degenerate single-value minmax maps to 0.5 (aira-evo `_normalize_minmax_values`),
    # so a lone candidate is never zeroed out.
    assert r["score_component"] == 0.5
    assert r["delta_component"] == 0.0  # no positive delta -> 0
    assert r["novelty_component"] == 1.0
    # utility = 1.0*0.5 + 0.4*0.0 + 0.25*1.0 = 0.75
    assert abs(r["utility"] - 0.75) < 1e-9
    assert abs(r["probability"] - 1.0) < 1e-9


def test_delta_is_positive_only_gain_over_strongest_parent():
    # child quality 3.0 vs parent quality 2.0 -> delta 1.0 (positive).
    # A sibling whose parent is STRONGER (2.5) gets a smaller delta.
    a = _archive_with([
        _make_entry(1, 2.0, 50.0, -0.1, 0.9, action="code_mutation"),
        _make_entry(2, 3.0, 30.0, -0.2, 0.7, parent_trial=1, action="prompt_mutation"),
        _make_entry(3, 2.2, 40.0, -0.15, 0.8, parent_trial=1, action="structural_experiment"),
    ])
    out = {r["trial_id"]: r for r in a.parent_utility_ranking()}
    assert abs(out[2]["delta"] - 1.0) < 1e-9  # 3.0 - 2.0, positive
    assert abs(out[3]["delta"] - 0.2) < 1e-9  # 2.2 - 2.0, positive
    assert out[1]["delta"] == 0.0  # no parent -> 0, never negative
    # delta component minmax over POSITIVE deltas: max=1.0 -> 1.0/0.2/0.0
    assert abs(out[1]["delta_component"] - 0.0) < 1e-9
    assert abs(out[2]["delta_component"] - 1.0) < 1e-9
    assert abs(out[3]["delta_component"] - 0.2) < 1e-9


def test_novelty_penalizes_same_family_concentration():
    # Two candidates in the same method family: the second gets 1/sqrt(2).
    a = _archive_with([
        _make_entry(1, 2.0, 50.0, -0.1, 0.9, action="code_mutation"),
        _make_entry(2, 2.1, 49.0, -0.11, 0.9, action="code_mutation"),
        _make_entry(3, 2.05, 48.0, -0.12, 0.9, action="prompt_mutation"),
    ])
    out = {r["trial_id"]: r for r in a.parent_utility_ranking()}
    assert abs(out[1]["novelty_component"] - 1.0) < 1e-9
    assert abs(out[2]["novelty_component"] - 1.0 / math.sqrt(2.0)) < 1e-9
    assert abs(out[3]["novelty_component"] - 1.0) < 1e-9


def test_probabilities_sum_to_one():
    a = _archive_with([
        _make_entry(1, 2.0, 50.0, -0.1, 0.9),
        _make_entry(2, 3.0, 30.0, -0.2, 0.7, parent_trial=1, action="prompt_mutation"),
        _make_entry(3, 2.2, 40.0, -0.15, 0.8, parent_trial=1, action="structural_experiment"),
    ])
    out = a.parent_utility_ranking()
    total = sum(r["probability"] for r in out)
    assert abs(total - 1.0) < 1e-9


def test_ranking_sorted_by_utility_descending():
    a = _archive_with([
        _make_entry(1, 2.0, 50.0, -0.1, 0.9),
        _make_entry(2, 3.0, 30.0, -0.2, 0.7, parent_trial=1, action="prompt_mutation"),
        _make_entry(3, 2.2, 40.0, -0.15, 0.8, parent_trial=1, action="structural_experiment"),
    ])
    out = a.parent_utility_ranking()
    utilities = [r["utility"] for r in out]
    assert utilities == sorted(utilities, reverse=True)


def test_text_renders_weights_and_rows():
    a = _archive_with([
        _make_entry(1, 2.0, 50.0, -0.1, 0.9),
        _make_entry(2, 3.0, 30.0, -0.2, 0.7, parent_trial=1, action="prompt_mutation"),
    ])
    text = a.parent_utility_text()
    assert "1.0 / delta 0.4 / novelty 0.25" in text
    assert "#1" in text and "#2" in text
    assert "util=" in text and "p=" in text
