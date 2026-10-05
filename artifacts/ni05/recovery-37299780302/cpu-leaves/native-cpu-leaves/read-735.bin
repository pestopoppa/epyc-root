"""ETR-2 (eval-tower loop robustness audit, 2026-07-20): the gate READS quality_measured.

`EvalResult.quality` is a plain float on the Pareto/SafetyGate contract, so a trial where
NOTHING was scored (pool never loaded, every row infra-failed, partition filter emptied the
decision subset) arrives carrying 0.0 as a PLACEHOLDER. Before this change the flag was
computed, documented and never consulted: neither `check()` nor `update_baseline()` read it,
so the placeholder entered the gate as a literal 0.0 candidate score and only the
INDEPENDENT REL-1 reliability floor happened to stop it.

The contract pinned here:
  - `check()` fails CLOSED on an unmeasured quality with the distinguishable
    `quality_not_measured` category, and suppresses the quality-floor / regression /
    per-suite legs (charging a non-measurement as a quality regression writes a fabricated
    regression into planner-visible failure_analysis).
  - a MEASURED 0.0 is still a measurement and is gated as one.
  - `update_baseline()` refuses to write a baseline from an unmeasured quality.
  - the producers set the flag truthfully.

Tests the AUTOPILOT's safety_gate (scripts/autopilot/safety_gate.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import pytest
from safety_gate import EvalResult, SafetyGate  # type: ignore[import-not-found]


def _gate(tmp_path) -> SafetyGate:
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    g.baseline.frontdoor_speed = 1.0  # keep the throughput floor out of the way
    return g


def _result(
    *,
    quality: float,
    quality_measured: bool,
    reason: str = "",
    reliability: float = 0.99,
    tier: int = 1,
) -> EvalResult:
    return EvalResult(
        tier=tier,
        quality=quality,
        speed=99.0,
        cost=0.1,
        reliability=reliability,
        per_suite_quality={"coder": quality},
        per_suite_counts={"coder": 50},
        routing_distribution={"worker": 1.0},
        n_questions=50,
        quality_measured=quality_measured,
        quality_unmeasured_reason=reason,
        speed_metric_mode="aggregate_batch_tps",
    )


# ── check() ───────────────────────────────────────────────────────────────────


def test_unmeasured_quality_is_not_promotable(tmp_path):
    """The whole defect: reliability is fine, so REL-1 cannot save us — the flag must."""
    g = _gate(tmp_path)
    verdict = g.check(
        _result(
            quality=0.0,
            quality_measured=False,
            reason="all_rows_infra_failed",
            reliability=0.99,
        )
    )
    assert not verdict.passed
    assert "quality_not_measured" in verdict.categories
    assert verdict.reliability_blocked is False, "this is NOT the REL-1 path"
    # ETR-5: the state is a first-class verdict field, not only a category string.
    assert verdict.quality_unmeasured is True
    assert verdict.retry_not_revert is True
    assert any("NOT MEASURED" in v and "all_rows_infra_failed" in v for v in verdict.violations)
    # Not conflated with a measured collapse: the quality legs are suppressed, not charged.
    assert "quality_floor" not in verdict.categories
    assert "regression" not in verdict.categories
    assert "per_suite_regression" not in verdict.categories


def test_unmeasured_quality_does_not_arm_auto_rollback(tmp_path):
    """The absence of a measurement is not evidence of a regression: RETRY, not revert."""
    g = _gate(tmp_path)
    g.baseline.baselines_by_tier = {1: 2.4}
    for _ in range(4):
        g.check(_result(quality=0.0, quality_measured=False, reason="no_question_results"))
    assert g.consecutive_failures == 0
    assert g.should_rollback() is False


def test_unmeasured_reason_is_surfaced_even_when_blank(tmp_path):
    g = _gate(tmp_path)
    verdict = g.check(_result(quality=0.0, quality_measured=False, reason=""))
    assert "quality_not_measured" in verdict.categories
    assert any("unspecified" in v for v in verdict.violations)


def test_measured_quality_still_passes(tmp_path):
    g = _gate(tmp_path)
    g.baseline.baselines_by_tier = {1: 2.0}
    g.baseline.per_suite_quality_by_tier = {1: {"coder": 2.0}}
    g.baseline.per_suite_counts_by_tier = {1: {"coder": 50}}
    verdict = g.check(_result(quality=2.5, quality_measured=True))
    assert verdict.passed, verdict.violations
    assert "quality_not_measured" not in verdict.categories
    assert verdict.quality_unmeasured is False


def test_measured_zero_is_a_measurement_not_a_placeholder(tmp_path):
    """A real 0.0 (the model answered everything wrong) must still be gated as a score."""
    g = _gate(tmp_path)
    g.baseline.baselines_by_tier = {1: 2.4}
    verdict = g.check(_result(quality=0.0, quality_measured=True, reliability=0.99))
    assert not verdict.passed
    assert "quality_not_measured" not in verdict.categories
    assert verdict.quality_unmeasured is False
    assert verdict.retry_not_revert is False  # a measured collapse IS revert evidence
    # Charged on the quality axis, which is the correct attribution for a measurement.
    assert "quality_floor" in verdict.categories
    assert "regression" in verdict.categories
    # And a measured failure DOES advance the rollback counter.
    assert g.consecutive_failures == 1


def test_unmeasured_quality_never_enters_the_mad_history(tmp_path):
    g = _gate(tmp_path)
    g.check(_result(quality=0.0, quality_measured=False, reason="no_scoreable_rows"))
    assert g.quality_history_for_tier(1) == []


# ── update_baseline() ─────────────────────────────────────────────────────────


def _eligible_gate(tmp_path, monkeypatch) -> SafetyGate:
    g = _gate(tmp_path)
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {"x": 1}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: None))
    return g


def test_update_baseline_refuses_unmeasured_quality(tmp_path, monkeypatch):
    g = _eligible_gate(tmp_path, monkeypatch)
    before = g.baseline.quality_for_tier(2, strict=True)
    outcome = g.update_baseline(
        _result(quality=2.9, quality_measured=False, reason="loader_error:question_pool", tier=2)
    )
    assert not outcome.updated
    assert outcome.ineligible_reason == "quality_not_measured"
    assert "NOT MEASURED" in outcome.reason and "loader_error:question_pool" in outcome.reason
    assert g.baseline.quality_for_tier(2, strict=True) == before, "baseline must not move"


def test_update_baseline_accepts_measured_quality(tmp_path, monkeypatch):
    g = _eligible_gate(tmp_path, monkeypatch)
    outcome = g.update_baseline(_result(quality=2.9, quality_measured=True, tier=2))
    assert outcome.updated, outcome.reason
    assert g.baseline.quality_for_tier(2, strict=True) == pytest.approx(2.9)


def test_update_baseline_measured_zero_is_gated_as_a_measurement(tmp_path, monkeypatch):
    """A measured 0.0 is refused by the MONOTONIC leg, not by the ETR-2 leg."""
    g = _eligible_gate(tmp_path, monkeypatch)
    g.baseline.baselines_by_tier = {2: 2.0}
    outcome = g.update_baseline(_result(quality=0.0, quality_measured=True, tier=2))
    assert not outcome.updated
    assert outcome.ineligible_reason != "quality_not_measured"
    assert "monotonic" in outcome.reason
