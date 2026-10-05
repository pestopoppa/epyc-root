"""SafetyGate MAD-based noise filter (intake-421 pi-autoresearch).

Median Absolute Deviation as a robust significance test on improvement-direction
quality deltas. Purely additive — emits warnings ("mad_noise" category) when an
"improvement" is within the noise band of recent history. Never blocks.

Tests the AUTOPILOT's safety_gate (scripts/autopilot/safety_gate.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import pytest
from safety_gate import (  # type: ignore[import-not-found]
    EvalResult,
    SafetyGate,
    MAD_MIN_SAMPLES,
    MAD_Z_THRESHOLD,
)


def _result(quality: float, speed: float = 99.0, tier: int = 2) -> EvalResult:
    """Build an otherwise-clean trial result at a given quality."""
    return EvalResult(
        tier=tier,
        quality=quality,
        speed=speed,
        cost=0.1,
        reliability=0.99,
        per_suite_quality={"coder": quality},
        routing_distribution={"worker": 1.0},
    )


def _gate(tmp_path, history: list[float] | None = None) -> SafetyGate:
    """Build a gate with a high frontdoor_speed baseline so the throughput
    floor doesn't trip during MAD tests (those run far below the floor)."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", quality_history=history)
    g.baseline.frontdoor_speed = 1.0  # any positive value low enough to ignore
    return g


def test_mad_skipped_when_history_below_min(tmp_path):
    """With fewer than MAD_MIN_SAMPLES, the filter must NOT fire."""
    g = _gate(tmp_path, history=[2.0] * (MAD_MIN_SAMPLES - 1))
    # SG-3 (audit B3a): the regression/MAD path now requires a STRICT same-tier baseline
    # (quality_for_tier(tier, strict=True)) — the old lenient fallback to the top-level
    # legacy quality is gone. Seed a same-tier baseline so the improvement branch runs.
    g.baseline.baselines_by_tier = {2: 1.16}
    verdict = g.check(_result(2.01))
    assert "mad_noise" not in verdict.categories


def test_mad_fires_on_noise_level_improvement(tmp_path):
    """Improvement within ~1 MAD of history median → warning, no violation."""
    history = [2.00, 2.02, 1.98, 2.01, 1.99]
    g = _gate(tmp_path, history=history)
    g.baseline.baselines_by_tier = {2: 1.16}  # SG-3 (B3a): strict same-tier baseline needed
    verdict = g.check(_result(2.01))  # well inside the noise band
    assert verdict.passed, "MAD filter must never block; it only warns"
    assert "mad_noise" in verdict.categories
    assert any("within noise" in w.lower() for w in verdict.warnings)
    # Warning text must reflect autopilot-side semantics: trial is still
    # journaled, but archive.update + AP-22 memory are skipped by the
    # classify_learning_exclusion() helper. Must NOT say "do not learn"
    # (over-claim) or "still recorded and learned from" (stale wording from
    # the diagnostic-only era).
    assert not any("do not learn" in w.lower() for w in verdict.warnings), \
        "warning text must reflect new exclusion semantics, not the old over-claim"
    assert not any("still recorded and learned from" in w.lower() for w in verdict.warnings), \
        "stale diagnostic-only wording; should say 'excluded from archive/learning'"
    assert any("excluded from archive/learning" in w.lower() for w in verdict.warnings)


def test_mad_passes_significant_improvement(tmp_path):
    """A real improvement (> Z_THRESHOLD MADs from median) must NOT warn."""
    history = [2.00, 2.02, 1.98, 2.01, 1.99]
    g = _gate(tmp_path, history=history)
    g.baseline.baselines_by_tier = {2: 1.16}  # SG-3 (B3a): strict same-tier baseline needed
    verdict = g.check(_result(2.50))
    assert verdict.passed
    assert "mad_noise" not in verdict.categories


def test_mad_history_is_per_tier(tmp_path):
    """A noisy T1 plateau must not suppress a T2 measurement."""
    g = SafetyGate(
        baseline_path=tmp_path / "absent.yaml",
        quality_history_by_tier={"1": [2.00, 2.02, 1.98, 2.01, 1.99]},
    )
    g.baseline.frontdoor_speed = 1.0
    g.baseline.baselines_by_tier = {1: 1.16, 2: 1.16}
    verdict = g.check(_result(2.01, tier=2))
    assert verdict.passed
    assert "mad_noise" not in verdict.categories
    assert g.quality_history_for_tier(1) == [2.00, 2.02, 1.98, 2.01, 1.99]
    assert g.quality_history_for_tier(2) == [2.01]


def test_mad_only_fires_on_improvement_branch(tmp_path):
    """A measurement below baseline takes the regression/warning branch,
    not the MAD branch."""
    history = [2.00, 2.02, 1.98, 2.01, 1.99]
    g = _gate(tmp_path, history=history)
    # SG-3 (B3a): set the STRICT same-tier baseline above the result so it takes the
    # regression/slight-drop branch, not the MAD branch. (Was g.baseline.quality=3.0, which
    # the strict regression gate no longer consults for a T2 result.)
    g.baseline.baselines_by_tier = {2: 3.0}
    verdict = g.check(_result(2.01))
    assert "mad_noise" not in verdict.categories


def test_regression_gate_uses_same_tier_baseline(tmp_path):
    g = _gate(tmp_path)
    g.baseline.baselines_by_tier = {1: 2.4, 2: 1.16}
    t2_verdict = g.check(_result(1.20, tier=2))
    assert t2_verdict.passed
    assert "regression" not in t2_verdict.categories

    t1_verdict = g.check(_result(1.20, tier=1))
    assert not t1_verdict.passed
    assert "regression" in t1_verdict.categories


def test_per_suite_regression_uses_same_tier_baseline(tmp_path):
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {
        1: {"coder": 2.4},
        2: {"coder": 1.16},
    }
    t2_verdict = g.check(_result(1.20, tier=2))
    assert t2_verdict.passed
    assert "per_suite_regression" not in t2_verdict.categories

    t1_verdict = g.check(_result(1.20, tier=1))
    assert not t1_verdict.passed
    assert "per_suite_regression" in t1_verdict.categories


def test_mad_zero_window_small_change_is_noise_not_significant(tmp_path):
    """SG-7 (audit B9): on a degenerate zero-MAD window (constant history) a change WITHIN
    two single-flip quanta (< MAD_ZERO_MIN_DELTA ≈ 0.2) is NOISE, not a fresh gain.

    Old semantics flagged ANY nonzero delta as significant (a NaN z then dodged the
    mad_noise tag entirely). New semantics: the within-band change is tagged mad_noise
    PLUS the distinct mad_zero_window so a saturated window can no longer launder a
    within-tolerance change as a real improvement."""
    g = _gate(tmp_path, history=[2.0, 2.0, 2.0])
    g.baseline.baselines_by_tier = {2: 1.16}  # SG-3 (B3a): strict same-tier baseline needed
    verdict = g.check(_result(2.0001))  # delta 0.0001 << 0.2
    assert verdict.passed
    assert "mad_noise" in verdict.categories
    assert "mad_zero_window" in verdict.categories


def test_mad_zero_window_large_change_is_significant(tmp_path):
    """SG-7 (audit B9): a change CLEARING two single-flip quanta (> MAD_ZERO_MIN_DELTA) on
    a zero-MAD window is a real change → no noise tag."""
    g = _gate(tmp_path, history=[2.0, 2.0, 2.0])
    g.baseline.baselines_by_tier = {2: 1.16}
    verdict = g.check(_result(2.5))  # delta 0.5 > 0.2
    assert "mad_noise" not in verdict.categories
    assert "mad_zero_window" not in verdict.categories


def test_quality_history_persists_across_check_calls(tmp_path):
    """Each completed trial extends the rolling window, bounded by maxlen."""
    g = _gate(tmp_path)
    for q in [1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6]:
        g.check(_result(q))
    history = g.quality_history
    assert len(history) == 10, "rolling window must respect MAD_HISTORY_DEPTH"
    assert history[-1] == pytest.approx(2.6)
    assert history[0] == pytest.approx(1.7), "oldest entries evicted FIFO"


def test_negative_quality_not_recorded(tmp_path):
    """Junk trials (negative quality) shouldn't poison the noise estimate."""
    g = _gate(tmp_path, history=[2.0, 2.0, 2.0])
    g.check(_result(-1.0))
    assert g.quality_history == [2.0, 2.0, 2.0]


def test_reproduction_confirmed_on_above_baseline_level(tmp_path):
    """A within-noise reproduction of an established ABOVE-baseline level must
    tag `reproduction_confirmed` (convergence) ALONGSIDE `mad_noise`. The invariant
    tested here is the GATE classification only (still mad_noise). NOTE (2026-06-04
    policy correction): the tag no longer implies "no Pareto point" — multi-objective
    archive admission is decoupled from this quality-only test (see
    ParetoArchive.upsert_representative); only AP-22/strategy learning stays excluded."""
    # History clustered ~1.8, baseline 1.16 (default) → established gain.
    history = [1.74, 1.58, 1.66, 1.82, 1.80]
    g = _gate(tmp_path, history=history)
    g.baseline.baselines_by_tier = {2: 1.16}  # SG-3 (B3a): strict same-tier baseline needed
    verdict = g.check(_result(1.816))  # reproduces the established level
    assert verdict.passed
    assert "mad_noise" in verdict.categories, "MAD invariant must be preserved"
    assert "reproduction_confirmed" in verdict.categories
    assert any("convergence" in w.lower() for w in verdict.warnings)


def test_reproduction_not_confirmed_near_baseline(tmp_path):
    """A within-noise tiny gain over a level that sits AT baseline is NOT a
    reproduction-confirmation — just mad_noise (genuinely inconclusive)."""
    # Non-zero spread centered on baseline (avoid the zero-MAD edge case).
    g = _gate(tmp_path, history=[1.16, 1.20, 1.12, 1.18, 1.14])
    g.baseline.quality = 1.16
    g.baseline.baselines_by_tier = {2: 1.16}  # SG-3 (B3a): strict same-tier baseline needed
    verdict = g.check(_result(1.17))  # within noise, but median ≈ baseline
    assert "mad_noise" in verdict.categories
    assert "reproduction_confirmed" not in verdict.categories


def test_reverted_trial_excluded_from_noise_window(tmp_path):
    """A gate-FAILING (reverted) trial must not shape the MAD noise band."""
    g = _gate(tmp_path, history=[1.8, 1.8, 1.8])
    g.baseline.quality = 1.16
    g.baseline.baselines_by_tier = {2: 1.16}  # SG-3 (B3a): strict same-tier baseline needed
    verdict = g.check(_result(0.40))  # −66% vs baseline → regression violation
    assert not verdict.passed
    assert g.quality_history == [1.8, 1.8, 1.8], "reverted trial must not enter window"


def test_mad_constants_sane():
    """Guard against silent threshold changes."""
    assert MAD_MIN_SAMPLES >= 3, "below 3 samples the median is meaningless"
    assert MAD_Z_THRESHOLD >= 1.5, "looser than ~1.5σ would let real noise through"
