"""Tests for AP-30 controller context-budget helpers."""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class FakeEntry:
    def __init__(self, description, insight, entry_type="raw", validity_score=0.5,
                 metadata=None):
        self.description = description
        self.insight = insight
        self.entry_type = entry_type
        self.validity_score = validity_score
        self.metadata = metadata or {}


class TestTruncateToBudget:
    def test_below_budget_passes_through(self):
        from scripts.autopilot.context_budget import truncate_to_budget

        out = truncate_to_budget("hello world", budget_tokens=100)
        assert out == "hello world"

    def test_above_budget_truncates_and_marks(self):
        from scripts.autopilot.context_budget import truncate_to_budget

        text = "\n".join([f"line {i}" for i in range(200)])
        out = truncate_to_budget(text, budget_tokens=20)
        assert "lines truncated" in out
        assert len(out) <= 20 * 4 + 80  # budget + marker tolerance

    def test_preserves_complete_lines(self):
        from scripts.autopilot.context_budget import truncate_to_budget

        text = "line one\nline two\nline three\nline four"
        out = truncate_to_budget(text, budget_tokens=5)
        # Every retained line should be intact
        retained = [line for line in out.split("\n") if not line.strip().startswith("…")]
        for line in retained:
            assert line in text


class TestApplySectionBudget:
    def test_registered_section_truncated(self):
        from scripts.autopilot.context_budget import apply_section_budget, SECTION_BUDGETS

        budget = SECTION_BUDGETS["plot_paths"]  # 100 tokens = 400 chars
        text = "x" * 5000
        out = apply_section_budget("plot_paths", text)
        assert len(out) <= budget * 4 + 80

    def test_unregistered_section_passes_through(self):
        from scripts.autopilot.context_budget import apply_section_budget

        text = "y" * 5000
        out = apply_section_budget("nonexistent_section", text)
        assert out == text


class TestFormatStrategiesTiered:
    def test_three_tier_formatting(self):
        from scripts.autopilot.context_budget import format_strategies_tiered

        entries = [
            FakeEntry("Convention A", "cross-species principle",
                      entry_type="convention", validity_score=0.9,
                      metadata={"total_source_trials": 30}),
            FakeEntry("Pattern B", "within-species pattern",
                      entry_type="pattern", validity_score=0.7,
                      metadata={"source_count": 4}),
            FakeEntry("Raw observation C", "single trial",
                      entry_type="raw", validity_score=0.5),
        ]
        out = format_strategies_tiered(entries)
        assert "Conventions" in out
        assert "Patterns" in out
        assert "Recent observations" in out
        assert "Convention A" in out
        # Convention shows insight; pattern doesn't
        assert "cross-species principle" in out
        assert "within-species pattern" not in out

    def test_caps_per_tier(self):
        from scripts.autopilot.context_budget import format_strategies_tiered

        entries = [
            FakeEntry(f"Raw {i}", "ins", entry_type="raw")
            for i in range(50)
        ]
        out = format_strategies_tiered(entries, max_raw=3)
        # Only the first 3 raw should appear
        assert out.count("- Raw") == 3

    def test_empty_input(self):
        from scripts.autopilot.context_budget import format_strategies_tiered

        out = format_strategies_tiered([])
        assert "no strategy" in out.lower()

    def test_uses_metadata_fallback_when_attribute_missing(self):
        from scripts.autopilot.context_budget import format_strategies_tiered

        class Bare:
            description = "metadata-only entry"
            insight = "insight"
            metadata = {"entry_type": "convention", "total_source_trials": 12}

        e = Bare()
        e.validity_score = 0.8
        out = format_strategies_tiered([e])
        assert "Conventions" in out
        assert "metadata-only entry" in out


class TestGateEvalOutput:
    def test_below_threshold_unchanged(self):
        from scripts.autopilot.context_budget import gate_eval_output

        text, gated = gate_eval_output("small text" * 10, threshold_bytes=10_000)
        assert gated is False
        assert "small text" in text

    def test_above_threshold_summarised(self):
        from scripts.autopilot.context_budget import gate_eval_output

        text = "X" * 20_000
        out, gated = gate_eval_output(text, threshold_bytes=5_000)
        assert gated is True
        assert "gated" in out
        assert len(out) < len(text)
        assert "HEAD" in out and "TAIL" in out

    def test_summary_hint_appears(self):
        from scripts.autopilot.context_budget import gate_eval_output

        text = "Z" * 20_000
        out, gated = gate_eval_output(text, threshold_bytes=5_000,
                                       summary_hint="seed_batch n=50 q=2.31")
        assert gated is True
        assert "seed_batch" in out


class TestBuildBudgetedSectionBlock:
    def test_sections_in_order(self):
        from scripts.autopilot.context_budget import build_budgeted_section_block

        sections = {
            "program": "PROG\n" * 10,
            "pareto_summary": "PARETO\n" * 10,
            "blacklist_text": "BLACKLIST\n" * 10,
        }
        titles = {"program": "Program", "pareto_summary": "Pareto"}
        block = build_budgeted_section_block(sections, section_titles=titles)
        assert block.index("Program") < block.index("Pareto")
        assert "PROG" in block
        assert "BLACKLIST" in block
