"""Tests for MutationGraph — PromptForge mutation-knowledge graph (AP-31)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.autopilot.species.mutation_graph import (
    MutationGraph,
    MutationOutcome,
    OUTCOME_ACCEPTED,
    OUTCOME_PARETO,
    OUTCOME_REJECTED,
    OUTCOME_SAFETY_FAIL,
)


@pytest.fixture
def graph(tmp_path):
    g = MutationGraph(db_path=tmp_path / "mut.db")
    yield g
    g.close()


def _record(graph, **kwargs):
    defaults = dict(
        trial_id=0,
        mutation_type="targeted_fix",
        failure_pattern="tool_compliance_low",
        target_file="frontdoor.md",
        outcome=OUTCOME_ACCEPTED,
        delta_quality=0.05,
        delta_speed=0.0,
        section_ids=[],
    )
    defaults.update(kwargs)
    return graph.record(MutationOutcome(**defaults))


class TestMutationGraph:
    def test_record_and_count(self, graph):
        rid = _record(graph, trial_id=1)
        assert rid > 0
        rows = graph._conn.execute(
            "SELECT COUNT(*) as c FROM mutation_outcomes"
        ).fetchone()
        assert rows["c"] == 1

    def test_stats_aggregation(self, graph):
        # 3 of (compress, missing_eval) — 2 pareto, 1 reject
        for i in range(2):
            _record(graph, mutation_type="compress",
                    failure_pattern="missing_eval",
                    outcome=OUTCOME_PARETO, delta_quality=0.10, trial_id=i)
        _record(graph, mutation_type="compress",
                failure_pattern="missing_eval",
                outcome=OUTCOME_REJECTED, delta_quality=-0.02, trial_id=2)

        stats = graph.stats(mutation_type="compress",
                            failure_pattern="missing_eval")
        assert len(stats) == 1
        s = stats[0]
        assert s.total == 3
        assert s.pareto == 2
        assert s.rejected == 1
        assert s.success_rate == pytest.approx(2 / 3, abs=1e-6)
        assert s.mean_delta_quality == pytest.approx((0.10 + 0.10 - 0.02) / 3,
                                                      abs=1e-6)

    def test_best_mutation_for_respects_min_trials(self, graph):
        # Two mutations; one has 1 great trial, one has 5 mediocre trials.
        _record(graph, mutation_type="few_shot_evolution",
                failure_pattern="off_topic",
                outcome=OUTCOME_PARETO, trial_id=1)
        for i in range(5):
            _record(graph, mutation_type="targeted_fix",
                    failure_pattern="off_topic",
                    outcome=OUTCOME_ACCEPTED, trial_id=10 + i)

        # min_trials=3 disqualifies few_shot_evolution
        winner = graph.best_mutation_for("off_topic", min_trials=3)
        assert winner == "targeted_fix"

        # min_trials=1 lets the higher-success-rate one through
        winner = graph.best_mutation_for("off_topic", min_trials=1)
        assert winner == "few_shot_evolution"

    def test_best_mutation_returns_none_when_empty(self, graph):
        assert graph.best_mutation_for("never_seen") is None

    def test_avoid_for(self, graph):
        # 6 rejections of crossover for tool_compliance_low → AVOID.
        for i in range(6):
            _record(graph, mutation_type="crossover",
                    failure_pattern="tool_compliance_low",
                    outcome=OUTCOME_SAFETY_FAIL, trial_id=i)
        # 1 mediocre attempt — below min_trials, should not appear.
        _record(graph, mutation_type="compress",
                failure_pattern="tool_compliance_low",
                outcome=OUTCOME_REJECTED, trial_id=99)
        avoid = graph.avoid_for("tool_compliance_low",
                                max_success_rate=0.1, min_trials=5)
        assert "crossover" in avoid
        assert "compress" not in avoid

    def test_pareto_best_sections(self, graph):
        # Section ids accumulate Pareto hits.
        _record(graph, outcome=OUTCOME_PARETO,
                section_ids=["preamble", "tools", "format"], trial_id=1)
        _record(graph, outcome=OUTCOME_PARETO,
                section_ids=["preamble", "format"], trial_id=2)
        _record(graph, outcome=OUTCOME_REJECTED,
                section_ids=["preamble", "rejected_section"], trial_id=3)

        ranked = graph.pareto_best_sections()
        ids = [sid for sid, _ in ranked]
        assert ids[0] == "preamble"  # 2 pareto hits
        # rejected-only section must NOT appear
        assert "rejected_section" not in ids

    def test_pareto_best_sections_filters_target_file(self, graph):
        _record(graph, outcome=OUTCOME_PARETO,
                target_file="frontdoor.md", section_ids=["a", "b"], trial_id=1)
        _record(graph, outcome=OUTCOME_PARETO,
                target_file="worker_explore.md", section_ids=["x"], trial_id=2)

        ranked_fd = graph.pareto_best_sections(target_file="frontdoor.md")
        ids = [sid for sid, _ in ranked_fd]
        assert ids == ["a", "b"] or ids == ["b", "a"]
        assert "x" not in ids

    def test_informed_crossover_candidates(self, graph):
        for _ in range(3):
            _record(graph, outcome=OUTCOME_PARETO,
                    target_file="frontdoor.md",
                    section_ids=["winner_section"], trial_id=1)
        _record(graph, outcome=OUTCOME_PARETO,
                target_file="frontdoor.md",
                section_ids=["one_off"], trial_id=2)

        cands = graph.informed_crossover_candidates(
            target_file="frontdoor.md", min_pareto_count=2
        )
        assert "winner_section" in cands
        assert "one_off" not in cands

    def test_context_manager_closes_db(self, tmp_path):
        path = tmp_path / "mut.db"
        with MutationGraph(db_path=path) as g:
            g.record(MutationOutcome(
                trial_id=1, mutation_type="t", failure_pattern="p",
                target_file="f.md", outcome=OUTCOME_ACCEPTED,
            ))
        # Re-open should work cleanly
        g2 = MutationGraph(db_path=path)
        try:
            row = g2._conn.execute(
                "SELECT COUNT(*) as c FROM mutation_outcomes"
            ).fetchone()
            assert row["c"] == 1
        finally:
            g2.close()
