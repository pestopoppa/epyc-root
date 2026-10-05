"""Tests for pipeline_monitor diagnostic record builder and JSONL writer."""

from __future__ import annotations

import json
from pathlib import Path

from src.pipeline_monitor.diagnostic import build_diagnostic, append_diagnostic

_RETIRED_ARCHITECT_ROLE = "architect_" "coding"


class TestBuildDiagnostic:
    def test_basic_structure(self):
        diag = build_diagnostic(
            question_id="thinking/t1_q1",
            suite="thinking",
            config="SELF:direct",
            role="frontdoor",
            mode="direct",
            passed=True,
            answer="C",
            expected="C",
            scoring_method="multiple_choice",
            error=None,
            error_type="none",
            tokens_generated=50,
            elapsed_s=3.5,
            role_history=["frontdoor"],
            delegation_events=[],
            tools_used=0,
            tools_called=[],
            tool_chains=[],
        )
        assert diag["question_id"] == "thinking/t1_q1"
        assert diag["suite"] == "thinking"
        assert diag["passed"] is True
        assert diag["anomaly_signals"] is not None
        assert isinstance(diag["anomaly_score"], float)
        assert "ts" in diag
        assert diag["delegation_diagnostics"] == {}
        # NIB2-35: shadow routing telemetry defaults
        assert diag["difficulty_score"] == 0.0
        assert diag["difficulty_band"] == ""
        assert diag["factual_risk_score"] == 0.0
        assert diag["factual_risk_band"] == ""

    def test_shadow_routing_telemetry_populated(self):
        """NIB2-35: shadow routing fields flow from build_diagnostic to output."""
        diag = build_diagnostic(
            question_id="simpleqa/q42",
            suite="simpleqa",
            config="SELF:direct",
            role="frontdoor",
            mode="direct",
            passed=False,
            answer="Napoleon",
            expected="Wellington",
            scoring_method="f1",
            error=None,
            error_type="none",
            tokens_generated=10,
            elapsed_s=2.0,
            role_history=["frontdoor"],
            delegation_events=[],
            tools_used=0,
            tools_called=[],
            tool_chains=[],
            difficulty_score=0.27,
            difficulty_band="medium",
            factual_risk_score=0.82,
            factual_risk_band="high",
        )
        assert diag["difficulty_score"] == 0.27
        assert diag["difficulty_band"] == "medium"
        assert diag["factual_risk_score"] == 0.82
        assert diag["factual_risk_band"] == "high"

    def test_delegation_diagnostics_included(self):
        diag = build_diagnostic(
            question_id="test",
            suite="coding",
            config="ARCHITECT:delegated",
            role=_RETIRED_ARCHITECT_ROLE,
            mode="delegated",
            passed=False,
            answer="",
            expected="",
            scoring_method="code_execution",
            error="timeout",
            error_type="timeout",
            tokens_generated=999,
            elapsed_s=90.0,
            role_history=[_RETIRED_ARCHITECT_ROLE, "coder_escalation"],
            delegation_events=[{"to_role": "coder_escalation"}],
            delegation_diagnostics={"break_reason": "role_repetition", "effective_max_loops": 2},
            tools_used=1,
            tools_called=["delegate"],
            tool_chains=[{"chain_id": "c1", "steps": ["delegate", "final"]}],
        )
        assert diag["delegation_diagnostics"]["break_reason"] == "role_repetition"
        assert diag["tool_chains"][0]["chain_id"] == "c1"

    def test_anomaly_signals_populated(self):
        diag = build_diagnostic(
            question_id="test",
            suite="thinking",
            config="ARCHITECT",
            role="architect_general",
            mode="delegated",
            passed=False,
            answer="After careful analysis of the quantum mechanics problem I believe the correct answer is B based on first principles",
            expected="C",
            scoring_method="exact_match",
            error=None,
            error_type="none",
            tokens_generated=100,
            elapsed_s=5.0,
            role_history=["architect_general"],
            delegation_events=[],
            tools_used=0,
            tools_called=[],
            tool_chains=[],
        )
        assert diag["anomaly_signals"]["format_violation"] is True
        assert diag["anomaly_score"] >= 1.0

    def test_tap_offset_included(self):
        diag = build_diagnostic(
            question_id="test",
            suite="thinking",
            config="SELF:direct",
            role="frontdoor",
            mode="direct",
            passed=True,
            answer="C",
            expected="C",
            scoring_method="multiple_choice",
            error=None,
            error_type="none",
            tokens_generated=10,
            elapsed_s=1.0,
            role_history=["frontdoor"],
            delegation_events=[],
            tools_used=0,
            tools_called=[],
            tool_chains=[],
            tap_offset_bytes=1024,
            tap_length_bytes=4096,
        )
        assert diag["tap_offset_bytes"] == 1024
        assert diag["tap_length_bytes"] == 4096


class TestAppendDiagnostic:
    def test_writes_valid_jsonl(self, tmp_path: Path):
        path = tmp_path / "test_diag.jsonl"
        diag = build_diagnostic(
            question_id="thinking/t1_q1",
            suite="thinking",
            config="SELF:direct",
            role="frontdoor",
            mode="direct",
            passed=True,
            answer="C",
            expected="C",
            scoring_method="multiple_choice",
            error=None,
            error_type="none",
            tokens_generated=10,
            elapsed_s=1.0,
            role_history=["frontdoor"],
            delegation_events=[],
            tools_used=0,
            tools_called=[],
            tool_chains=[],
        )
        append_diagnostic(diag, path=path)

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 1
        loaded = json.loads(lines[0])
        assert loaded["question_id"] == "thinking/t1_q1"

    def test_appends_multiple(self, tmp_path: Path):
        path = tmp_path / "test_diag.jsonl"
        for i in range(3):
            diag = build_diagnostic(
                question_id=f"q{i}",
                suite="thinking",
                config="SELF:direct",
                role="frontdoor",
                mode="direct",
                passed=True,
                answer="C",
                expected="C",
                scoring_method="multiple_choice",
                error=None,
                error_type="none",
                tokens_generated=10,
                elapsed_s=1.0,
            role_history=["frontdoor"],
            delegation_events=[],
            tools_used=0,
            tools_called=[],
            tool_chains=[],
        )
            append_diagnostic(diag, path=path)

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 3
        for i, line in enumerate(lines):
            loaded = json.loads(line)
            assert loaded["question_id"] == f"q{i}"
