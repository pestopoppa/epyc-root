"""Tests for SafetyGate.analyze_failure() — structured failure narratives."""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.autopilot.safety_gate import (
    EvalResult,
    SafetyGate,
    SafetyVerdict,
)


def _make_result(**overrides) -> EvalResult:
    defaults = dict(
        tier=0,
        quality=2.5,
        speed=15.0,
        cost=0.3,
        reliability=0.95,
        per_suite_quality={},
        routing_distribution={},
        n_questions=100,
    )
    defaults.update(overrides)
    return EvalResult(**defaults)


class TestAnalyzeFailure:

    def test_passed_verdict_returns_empty(self):
        result = _make_result()
        verdict = SafetyVerdict(passed=True, violations=[], warnings=[])
        assert SafetyGate.analyze_failure(result, verdict) == ""

    def test_quality_floor_violation(self):
        result = _make_result(quality=1.5)
        verdict = SafetyVerdict(
            passed=False,
            violations=["Quality floor violation: 1.500 < 2.0"],
        )
        analysis = SafetyGate.analyze_failure(result, verdict)
        assert "VIOLATIONS:" in analysis
        assert "Quality floor" in analysis

    def test_per_suite_degradation(self):
        result = _make_result(
            per_suite_quality={"math": 1.2, "coding": 2.8}
        )
        verdict = SafetyVerdict(
            passed=False,
            violations=["Quality floor violation"],
        )
        analysis = SafetyGate.analyze_failure(result, verdict)
        assert "DEGRADED SUITES:" in analysis
        assert "math" in analysis
        # coding is above floor, should not appear in degraded
        assert "coding" not in analysis.split("DEGRADED SUITES:")[1].split("\n\n")[0]

    def test_routing_imbalance(self):
        result = _make_result(
            routing_distribution={"architect": 0.75, "worker": 0.25}
        )
        verdict = SafetyVerdict(
            passed=False,
            violations=["Routing diversity violation"],
        )
        analysis = SafetyGate.analyze_failure(result, verdict)
        assert "ROUTING IMBALANCE:" in analysis
        assert "architect" in analysis

    def test_warnings_included(self):
        result = _make_result()
        verdict = SafetyVerdict(
            passed=False,
            violations=["Some violation"],
            warnings=["Speed marginal: 9.0 t/s"],
        )
        analysis = SafetyGate.analyze_failure(result, verdict)
        assert "WARNINGS:" in analysis
        assert "Speed marginal" in analysis

    def test_multiple_violations_compound(self):
        result = _make_result(
            quality=1.0,
            per_suite_quality={"math": 0.5, "reasoning": 1.0},
            routing_distribution={"architect": 0.8},
        )
        verdict = SafetyVerdict(
            passed=False,
            violations=[
                "Quality floor violation: 1.000 < 2.0",
                "Routing diversity violation: 80% architect-tier",
            ],
            warnings=["Slight quality drop"],
        )
        analysis = SafetyGate.analyze_failure(result, verdict)
        assert "VIOLATIONS:" in analysis
        assert "DEGRADED SUITES:" in analysis
        assert "ROUTING IMBALANCE:" in analysis
        assert "WARNINGS:" in analysis
