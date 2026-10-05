"""B3: SafetyGate baseline-integrity fixes.

SG-3 (B3a): the regression gate in check() and the monotonic gate in update_baseline use
  the STRICT same-tier baseline (quality_for_tier(tier, strict=True)) — no cross-tier
  legacy fallback. When there is no same-tier baseline the regression gate is skipped and
  update_baseline SEEDS the tier baseline.
SG-5 (B3b): a non-finite result.quality fails closed ("quality is not finite — degenerate
  eval") BEFORE any comparison-based leg, independent of the reliability suppression.
SG-4 (B3c): apply_state() applies load()'s above-archive-max guard to state-sourced tier
  baselines (dropping over-max tiers), so a corrupt state dict cannot gate-lock the loop.
MISC-1: update_tier only overwrites the top-level speed/cost/reliability scalars at
  DEFAULT_FRONTIER_TIER (mirroring the existing quality/frontdoor_speed gating).

Tests the AUTOPILOT's safety_gate (scripts/autopilot/safety_gate.py).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import pytest
import safety_gate as sg  # type: ignore[import-not-found]
from safety_gate import (  # type: ignore[import-not-found]
    Baseline,
    DEFAULT_FRONTIER_TIER,
    EvalResult,
    SafetyGate,
)


def _gate(tmp_path) -> SafetyGate:
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    g.baseline.frontdoor_speed = 1.0
    return g


def _result(quality: float, tier: int = 2, reliability: float = 0.99) -> EvalResult:
    return EvalResult(
        tier=tier,
        quality=quality,
        speed=99.0,
        cost=0.1,
        reliability=reliability,
        speed_metric_mode="aggregate_batch_tps",
        n_questions=50,
        routing_distribution={"worker": 1.0},
    )


# ── SG-3: strict same-tier regression gate + seeding ──────────────────────────

def test_regression_skipped_without_strict_same_tier_baseline(tmp_path):
    """A T2 result BELOW the top-level legacy quality (1.16) must NOT regress when there is
    no strict T2 baseline — the old lenient cross-tier fallback is gone."""
    g = _gate(tmp_path)
    assert g.baseline.quality_for_tier(2, strict=True) is None
    verdict = g.check(_result(1.05, tier=2))  # above tier floor 1.0, below legacy 1.16
    assert "regression" not in verdict.categories
    assert verdict.passed


def test_update_baseline_seeds_tier_even_below_legacy_quality(tmp_path, monkeypatch):
    """update_baseline seeds a fresh tier baseline (strict None → no monotonic block) even
    when the result is below the top-level legacy quality — no cross-tier fallback."""
    g = _gate(tmp_path)
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: None))
    res = g.update_baseline(_result(0.9, tier=2))  # 0.9 < legacy 1.16
    assert res.updated
    assert g.baseline.quality_for_tier(2, strict=True) == pytest.approx(0.9)


# ── SG-5: non-finite quality fails closed ─────────────────────────────────────

def test_nan_quality_fails_closed(tmp_path):
    g = _gate(tmp_path)
    verdict = g.check(_result(math.nan, tier=1))
    assert not verdict.passed
    assert "quality_not_finite" in verdict.categories


def test_inf_quality_fails_closed(tmp_path):
    g = _gate(tmp_path)
    verdict = g.check(_result(math.inf, tier=1))
    assert not verdict.passed
    assert "quality_not_finite" in verdict.categories


def test_nan_quality_fails_even_when_reliability_blocked(tmp_path):
    """SG-5 is independent of the REL-1 reliability suppression: a degenerate (NaN) quality
    must still fail closed even when reliability is below the floor."""
    g = _gate(tmp_path)
    verdict = g.check(_result(math.nan, tier=1, reliability=0.5))
    assert not verdict.passed
    assert "quality_not_finite" in verdict.categories
    assert "reliability_floor" in verdict.categories
    assert verdict.reliability_blocked is True


# ── SG-4: apply_state drops over-archive-max tier baselines ───────────────────

def test_apply_state_drops_over_archive_max_tier(tmp_path, monkeypatch):
    """A corrupt state dict carrying an above-frontier tier baseline is dropped on apply,
    exactly as the load() path drops it — a 2.9 T2 value over a 2.4 frontier max would
    otherwise force-revert every honest trial (2026-05-31 gate-lock)."""
    monkeypatch.setattr(sg, "_pareto_frontier_best_quality", lambda tier=None: 2.4)
    b = Baseline(source_path=tmp_path / "absent.yaml")
    b.apply_state({"baselines_by_tier": {"2": 2.9, "1": 1.5}})
    assert b.quality_for_tier(2, strict=True) is None, "over-max T2 baseline must be dropped"
    assert b.quality_for_tier(1, strict=True) == pytest.approx(1.5), "within-max survives"


def test_apply_state_keeps_tiers_when_archive_unreadable(tmp_path, monkeypatch):
    """Fresh bootstrap (archive empty/unreadable → None): the guard is skipped so a
    legitimate first state write is never blocked."""
    monkeypatch.setattr(sg, "_pareto_frontier_best_quality", lambda tier=None: None)
    b = Baseline(source_path=tmp_path / "absent.yaml")
    b.apply_state({"baselines_by_tier": {"2": 2.9}})
    assert b.quality_for_tier(2, strict=True) == pytest.approx(2.9)


# ── MISC-1: update_tier top-level scalars are frontier-gated ───────────────────

def test_update_tier_offfrontier_does_not_clobber_toplevel_scalars(tmp_path):
    """A non-frontier (T2) promotion must not overwrite the top-level speed/cost/reliability
    that describe the DEFAULT_FRONTIER_TIER production point (they feed the throughput floor)."""
    off_tier = DEFAULT_FRONTIER_TIER + 1
    b = Baseline(speed=10.0, cost=0.5, reliability=0.9, source_path=tmp_path / "absent.yaml")
    r = EvalResult(tier=off_tier, quality=2.0, speed=99.0, cost=0.1, reliability=0.99)
    b.update_tier(r)
    assert b.speed == pytest.approx(10.0), "top-level speed must be untouched by off-frontier tier"
    assert b.cost == pytest.approx(0.5)
    assert b.reliability == pytest.approx(0.9)
    assert b.baselines_by_tier[off_tier] == pytest.approx(2.0), "the tier baseline still updates"


def test_update_tier_frontier_updates_toplevel_scalars(tmp_path):
    b = Baseline(speed=10.0, cost=0.5, reliability=0.9, source_path=tmp_path / "absent.yaml")
    r = EvalResult(tier=DEFAULT_FRONTIER_TIER, quality=2.0, speed=88.0, cost=0.2, reliability=0.95)
    b.update_tier(r)
    assert b.speed == pytest.approx(88.0)
    assert b.cost == pytest.approx(0.2)
    assert b.reliability == pytest.approx(0.95)
    assert b.frontdoor_speed == pytest.approx(88.0)
    assert b.quality == pytest.approx(2.0)
