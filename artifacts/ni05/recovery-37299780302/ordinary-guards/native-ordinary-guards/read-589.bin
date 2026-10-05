"""B2 / SG-1: per-suite regression float-boundary fix.

per_suite_regression_threshold() returns the single-flip quantum (3/n) as the boundary,
and its docstring says a delta must be "MORE negative" than the threshold to count as a
violation. But `fraction_correct*3` and `-max(..., 3/n)` are computed separately, so a
delta that is exactly one flip lands ~1e-16 to one side of the threshold at random — 185
(n, k) pairs cross the bare `<` purely from float rounding. Comparing against
`threshold - PER_SUITE_EPS` restores the documented intent: exactly one flip is
at-resolution noise, not a violation; two or more flips still fire.

Tests the AUTOPILOT's safety_gate (scripts/autopilot/safety_gate.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from safety_gate import (  # type: ignore[import-not-found]
    EvalResult,
    PER_SUITE_EPS,
    SafetyGate,
    per_suite_regression_threshold,
)


def _gate(tmp_path) -> SafetyGate:
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    g.baseline.frontdoor_speed = 1.0
    return g


def _trial(suite_score: float, n: int) -> EvalResult:
    # quality high (clears the tier-1 floor); the per-suite score is what's under test.
    return EvalResult(
        tier=1,
        quality=2.5,
        speed=99.0,
        cost=0.1,
        reliability=0.99,
        per_suite_quality={"s": suite_score},
        per_suite_counts={"s": n},
        routing_distribution={"worker": 1.0},
    )


def test_eps_is_tiny_positive():
    assert 0.0 < PER_SUITE_EPS <= 1e-6


def test_single_flip_never_violates_across_n(tmp_path):
    """PROPERTY: for n in 2..60 and every k, dropping one correct answer (baseline 3k/n,
    result 3(k-1)/n) is exactly one flip and must NOT be a per-suite regression. This is the
    exact family of 185 float-boundary artifacts the eps guard kills."""
    for n in range(2, 61):
        for k in range(1, n + 1):
            baseline = 3.0 * k / n
            result = 3.0 * (k - 1) / n
            g = _gate(tmp_path)
            g.baseline.per_suite_quality_by_tier = {1: {"s": baseline}}
            g.baseline.per_suite_counts_by_tier = {1: {"s": n}}
            verdict = g.check(_trial(result, n))
            assert "per_suite_regression" not in verdict.categories, (
                f"single flip at n={n}, k={k} must not be a hard regression"
            )
            # A single flip is at-resolution: it must not even cross into advisory.
            assert "per_suite_regression_advisory" not in verdict.categories, (
                f"single flip at n={n}, k={k} must be silent (at-resolution noise)"
            )


def test_two_flip_drop_at_n5_still_violates(tmp_path):
    """A genuine two-flip collapse (3.0 -> 1.8 at n=5, delta -1.2 past the -0.6 threshold)
    at adequate support IS a hard per-suite regression."""
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {1: {"s": 3.0}}
    g.baseline.per_suite_counts_by_tier = {1: {"s": 5}}
    verdict = g.check(_trial(1.8, 5))  # 3/5 correct
    assert "per_suite_regression" in verdict.categories


def test_boundary_is_the_single_flip_quantum(tmp_path):
    """The n=5 tool-of-the-fix worked example: delta == threshold (one flip) is below the
    eps-guarded crossing, a slightly-more-negative delta is above it."""
    threshold = per_suite_regression_threshold(5, 5)
    assert threshold == -max(0.1, 3.0 / 5)
    one_flip = 2.4 - 3.0  # -0.6000000000000001 in float
    assert not (one_flip < threshold - PER_SUITE_EPS)  # noise
    two_flips = 1.8 - 3.0  # -1.2
    assert two_flips < threshold - PER_SUITE_EPS  # violation
