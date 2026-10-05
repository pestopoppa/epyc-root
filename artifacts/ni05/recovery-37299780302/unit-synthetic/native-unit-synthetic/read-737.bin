"""B1 / REL-1: reliability conditioning of the SafetyGate quality legs.

When an eval's non-error fraction (reliability) is below RELIABILITY_FLOOR the
per-question outcomes are untrustworthy (infra errors). Running the quality-floor /
regression / per-suite legs over that garbage would convert an infrastructure failure
into a spurious quality-regression REVERT. The gate instead:
  - records a `reliability_floor` violation and marks the verdict reliability_blocked,
  - SKIPS the quality-floor / regression / per-suite legs,
  - and does NOT advance the consecutive-failure rollback counter (RETRY, not revert).

Tests the AUTOPILOT's safety_gate (scripts/autopilot/safety_gate.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from safety_gate import (  # type: ignore[import-not-found]
    EvalResult,
    RELIABILITY_FLOOR,
    SafetyGate,
)


def _gate(tmp_path) -> SafetyGate:
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    g.baseline.frontdoor_speed = 1.0  # keep the throughput floor out of the way
    return g


def _crater(reliability: float, tier: int = 1) -> EvalResult:
    """A cratered trial that WOULD trip quality-floor + regression + per-suite if run."""
    return EvalResult(
        tier=tier,
        quality=0.2,
        speed=99.0,
        cost=0.1,
        reliability=reliability,
        per_suite_quality={"coder": 0.0},
        per_suite_counts={"coder": 50},
        routing_distribution={"worker": 1.0},
    )


def test_reliability_floor_default_is_point_eight():
    assert RELIABILITY_FLOOR == 0.8


def test_low_reliability_suppresses_quality_checks_and_signals_retry(tmp_path):
    g = _gate(tmp_path)
    # A genuine same-tier baseline so, absent suppression, the crater WOULD regress.
    g.baseline.baselines_by_tier = {1: 2.4}
    g.baseline.per_suite_quality_by_tier = {1: {"coder": 3.0}}
    g.baseline.per_suite_counts_by_tier = {1: {"coder": 50}}

    verdict = g.check(_crater(reliability=0.7))  # 30% infra-error trial

    assert not verdict.passed
    assert verdict.reliability_blocked is True
    assert "reliability_floor" in verdict.categories
    assert any("Reliability" in v and "below floor" in v for v in verdict.violations)
    # The garbage-evidence legs must be suppressed — NOT converted into a revert signal.
    assert "regression" not in verdict.categories
    assert "quality_floor" not in verdict.categories
    assert "per_suite_regression" not in verdict.categories
    # RETRY, not revert: the rollback counter must not advance.
    assert g.consecutive_failures == 0


def test_repeated_low_reliability_never_triggers_rollback(tmp_path):
    g = _gate(tmp_path)
    g.baseline.baselines_by_tier = {1: 2.4}
    for _ in range(3):
        g.check(_crater(reliability=0.7))
    assert g.consecutive_failures == 0
    assert g.should_rollback() is False


def test_good_reliability_genuine_drop_still_regresses(tmp_path):
    g = _gate(tmp_path)
    g.baseline.baselines_by_tier = {1: 2.4}
    result = EvalResult(
        tier=1,
        quality=1.0,  # real drop vs 2.4 baseline (−58%)
        speed=99.0,
        cost=0.1,
        reliability=0.95,  # trustworthy evidence
        routing_distribution={"worker": 1.0},
    )
    verdict = g.check(result)
    assert verdict.reliability_blocked is False
    assert not verdict.passed
    assert "regression" in verdict.categories


def test_reliability_exactly_at_floor_is_not_blocked(tmp_path):
    """Strictly-below semantics: reliability == floor is trustworthy enough."""
    g = _gate(tmp_path)
    g.baseline.baselines_by_tier = {1: 1.16}
    result = EvalResult(
        tier=1, quality=1.5, speed=99.0, cost=0.1, reliability=RELIABILITY_FLOOR,
        routing_distribution={"worker": 1.0},
    )
    verdict = g.check(result)
    assert verdict.reliability_blocked is False
    assert "reliability_floor" not in verdict.categories


def test_env_override_raises_floor(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_RELIABILITY_FLOOR", "0.9")
    g = _gate(tmp_path)
    result = EvalResult(
        tier=1, quality=2.0, speed=99.0, cost=0.1, reliability=0.85,
        routing_distribution={"worker": 1.0},
    )
    verdict = g.check(result)
    assert verdict.reliability_blocked is True  # 0.85 < overridden floor 0.9


def test_env_override_ignored_below_default(tmp_path, monkeypatch):
    """Without the override, reliability 0.85 (>= default 0.8) is fine."""
    monkeypatch.delenv("AUTOPILOT_RELIABILITY_FLOOR", raising=False)
    g = _gate(tmp_path)
    g.baseline.baselines_by_tier = {1: 1.16}
    result = EvalResult(
        tier=1, quality=2.0, speed=99.0, cost=0.1, reliability=0.85,
        routing_distribution={"worker": 1.0},
    )
    verdict = g.check(result)
    assert verdict.reliability_blocked is False


def test_malformed_env_override_falls_back_to_default(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_RELIABILITY_FLOOR", "not-a-number")
    g = _gate(tmp_path)
    # 0.85 >= default 0.8, so a fat-fingered override must NOT silently disarm the guard
    # by parsing to something odd — it falls back to 0.8, leaving 0.85 unblocked.
    result = EvalResult(
        tier=1, quality=2.0, speed=99.0, cost=0.1, reliability=0.85,
        per_suite_quality={}, routing_distribution={"worker": 1.0},
    )
    g.baseline.baselines_by_tier = {1: 1.16}
    verdict = g.check(result)
    assert verdict.reliability_blocked is False
    # And a truly low reliability is still blocked under the fallback floor.
    assert g.check(_crater(reliability=0.5)).reliability_blocked is True


# ---------------------------------------------------------------------------
# REL-1 extension: on a reliability-blocked trial a 0.0 t/s sample is ABSENT,
# not slow.
#
# REL-1 deliberately exempts the throughput leg ("does not depend on
# per-question correctness"), which is right while the eval GENERATED tokens and
# merely scored them badly. At speed == 0 nothing was generated, so the same
# infra failure produced both numbers — and the gate was charging one of them.
# Trial 1459 (2026-08-03) carried a fabricated "Throughput floor: 0.0 t/s <
# 10.2 t/s (80% of baseline 12.7)" into failure_analysis, which is
# planner-visible evidence.
# ---------------------------------------------------------------------------


def _unmeasured(reliability: float) -> EvalResult:
    """An infra-failed trial: nothing generated, so speed is absent, not low."""
    return EvalResult(
        tier=1,
        quality=0.0,
        speed=0.0,
        cost=0.0,
        reliability=reliability,
        per_suite_quality={},
        routing_distribution={"frontdoor": 1.0},
    )


def test_zero_speed_on_reliability_blocked_trial_is_not_a_throughput_violation(tmp_path):
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    g.baseline.frontdoor_speed = 12.7  # floor = 10.16 t/s, so 0.0 would trip it

    verdict = g.check(_unmeasured(reliability=0.0))

    assert verdict.reliability_blocked is True
    assert "throughput_unmeasured" in verdict.categories
    assert "throughput" not in verdict.categories
    assert not any("Throughput floor" in v for v in verdict.violations), (
        "an infra failure that generated no tokens must not be reported as a "
        "throughput regression — failure_analysis is planner-visible evidence"
    )
    assert any("not measured" in w for w in verdict.warnings)


def test_zero_speed_with_intact_reliability_still_violates(tmp_path, monkeypatch):
    """Narrow scope: a genuine hang IS attributable to the config under test."""
    import scripts.autopilot.host_health as hh  # noqa: PLC0415

    class _NotThrottled:
        @staticmethod
        def is_throttled():
            return False, []

    # Neutralise the SG-9 throttle demotion so this asserts the throughput leg,
    # not the host's mood.
    monkeypatch.setattr(hh.HostHealthState, "snapshot", staticmethod(_NotThrottled))

    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    g.baseline.frontdoor_speed = 12.7

    verdict = g.check(_unmeasured(reliability=0.99))

    assert verdict.reliability_blocked is False
    assert "throughput" in verdict.categories
    assert "throughput_unmeasured" not in verdict.categories
    assert any("Throughput floor" in v for v in verdict.violations)
