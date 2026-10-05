"""SafetyGate eval-instrument era fence (defect #3/#4).

Covers the fail-closed re-baseline hold (a post-E7 result must NOT gate promote/revert
against a pre-E7 baseline/per-suite/MAD window), quality-history provenance round-trip,
and era-filtered MAD windows. All pre-fence behavior is preserved when no active era is
set — that contract lives in the existing test_safety_gate_* suites and stays green.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from safety_gate import (  # type: ignore[import-not-found]  # noqa: E402
    EvalResult,
    SafetyGate,
    _coerce_quality_obs,
)

_ERA = "E7-eval-instrument"


def _result(quality: float, *, tier: int = 1, per_suite: dict | None = None) -> EvalResult:
    return EvalResult(
        tier=tier,
        quality=quality,
        speed=99.0,
        cost=0.1,
        reliability=0.99,
        per_suite_quality=per_suite if per_suite is not None else {"coder": quality},
        routing_distribution={"worker": 1.0},
        n_questions=50,
        speed_metric_mode="aggregate_batch_tps",
    )


def _gate(tmp_path, **kwargs) -> SafetyGate:
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", **kwargs)
    g.baseline.frontdoor_speed = 1.0
    return g


# ---- re-baseline hold: detection ------------------------------------------------------


def test_legacy_baseline_vs_active_era_trips_hold(tmp_path) -> None:
    g = _gate(tmp_path, eval_quality_era=_ERA)
    # No eval_quality_era on the baseline state => pre-boundary legacy baseline.
    assert g.quality_rebaseline_required is True


def test_same_era_baseline_does_not_trip_hold(tmp_path) -> None:
    g = _gate(tmp_path, eval_quality_era=_ERA, baseline_state={"eval_quality_era": _ERA})
    assert g.quality_rebaseline_required is False


def test_no_active_era_never_trips_hold(tmp_path) -> None:
    g = _gate(tmp_path)  # unfenced
    assert g.quality_rebaseline_required is False


# ---- re-baseline hold: check() suppresses cross-era gating -----------------------------


def test_hold_suppresses_cross_era_regression_revert(tmp_path) -> None:
    """A post-E7 result far below a pre-E7 baseline must NOT be reverted while the hold
    is active — that revert would charge a scorer/pool change to the model."""
    g = _gate(tmp_path, eval_quality_era=_ERA)
    g.baseline.baselines_by_tier = {1: 2.4}  # pre-E7 baseline (unstamped)
    verdict = g.check(_result(1.2, tier=1))  # -50% vs the stale baseline
    assert verdict.passed, "cross-era regression must be suppressed, not force a revert"
    assert "regression" not in verdict.categories
    assert "quality_rebaseline_required" in verdict.categories


def test_hold_suppresses_cross_era_per_suite_regression(tmp_path) -> None:
    g = _gate(tmp_path, eval_quality_era=_ERA)
    g.baseline.per_suite_quality_by_tier = {1: {"coder": 3.0}}
    verdict = g.check(_result(1.2, tier=1, per_suite={"coder": 0.0}))
    assert verdict.passed
    assert "per_suite_regression" not in verdict.categories


def test_hold_keeps_absolute_quality_floor(tmp_path) -> None:
    """The floor is era-neutral (absolute safety), so it still fires under the hold."""
    g = _gate(tmp_path, eval_quality_era=_ERA)
    g.baseline.baselines_by_tier = {1: 2.4}
    verdict = g.check(_result(0.2, tier=1))  # below QUALITY_FLOOR_T1
    assert not verdict.passed
    assert "quality_floor" in verdict.categories


def test_same_era_baseline_still_gates_regression(tmp_path) -> None:
    """Once a same-era baseline exists the hold clears and normal gating resumes."""
    g = _gate(tmp_path, eval_quality_era=_ERA, baseline_state={"eval_quality_era": _ERA})
    g.baseline.baselines_by_tier = {1: 2.4}
    verdict = g.check(_result(1.2, tier=1))
    assert not verdict.passed
    assert "regression" in verdict.categories


# ---- re-baseline hold: update_baseline refuses cross-era promotion ---------------------


def test_update_baseline_refuses_under_hold(tmp_path, monkeypatch) -> None:
    g = _gate(tmp_path, eval_quality_era=_ERA)
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {}))
    res = g.update_baseline(_result(2.9, tier=2))
    assert res.updated is False
    assert res.ineligible_reason == "quality_rebaseline_required"


def test_update_baseline_promotes_and_stamps_era_when_not_held(tmp_path, monkeypatch) -> None:
    # Same-era baseline => no hold; a monotonic promotion stamps the active era so the
    # cross-era condition can be detected at the NEXT boundary.
    g = _gate(
        tmp_path,
        eval_quality_era=_ERA,
        baseline_state={"eval_quality_era": _ERA, "baselines_by_tier": {"2": 1.0}},
    )
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {}))
    monkeypatch.setattr(g, "_archive_best_quality", lambda tier: None)
    res = g.update_baseline(_result(2.9, tier=2), source_trial_id=5)
    assert res.updated is True
    assert g.baseline.eval_quality_era == _ERA


# ---- quality-history provenance -------------------------------------------------------


def test_coerce_quality_obs_decodes_legacy_float_as_pre_boundary() -> None:
    obs = _coerce_quality_obs(1.85)
    assert obs is not None
    assert obs.q == 1.85
    assert obs.era == ""  # legacy bare float => pre-boundary prior
    obs2 = _coerce_quality_obs({"q": 2.0, "ts": "2026-07-22T00:00:00Z", "era": _ERA, "core_id": "c"})
    assert obs2.era == _ERA and obs2.core_id == "c"
    assert _coerce_quality_obs(float("nan")) is None
    assert _coerce_quality_obs("junk") is None


def test_provenance_round_trips_through_state(tmp_path) -> None:
    prov = {"1": [{"q": 1.9, "ts": "2026-07-22T00:00:00Z", "era": _ERA, "core_id": "c1"}]}
    g = _gate(tmp_path, eval_quality_era=_ERA, quality_history_provenance_by_tier=prov)
    out = g.quality_history_provenance_by_tier
    assert out["1"][0]["q"] == 1.9
    assert out["1"][0]["era"] == _ERA
    assert out["1"][0]["core_id"] == "c1"
    # The legacy float mirror is still exposed for external readers.
    assert g.quality_history_by_tier["1"] == [1.9]


def test_append_carries_active_era_provenance(tmp_path) -> None:
    g = _gate(tmp_path, eval_quality_era=_ERA, baseline_state={"eval_quality_era": _ERA})
    g.baseline.baselines_by_tier = {1: 1.16}
    g.check(_result(1.8, tier=1))
    prov = g.quality_history_provenance_by_tier["1"]
    assert len(prov) == 1
    assert prov[0]["era"] == _ERA
    assert prov[0]["ts"]  # a timestamp was stamped


def test_mad_window_excludes_other_era_samples(tmp_path) -> None:
    """A post-E7 MAD median must be computed over E7 samples only — pre-E7 bare floats are
    priors and must not drag the median."""
    # Pre-E7 window sits at ~0.5; a lone post-E7 sample at 1.8. With the era filter the
    # post-E7 window has <MAD_MIN_SAMPLES E7 samples => MAD skipped (accept at face value),
    # so a 1.85 improvement is NOT tagged mad_noise against the stale 0.5 band.
    prov = {
        "1": [
            {"q": 0.5, "ts": "2026-07-01T00:00:00Z", "era": ""},
            {"q": 0.5, "ts": "2026-07-01T00:00:00Z", "era": ""},
            {"q": 0.5, "ts": "2026-07-01T00:00:00Z", "era": ""},
            {"q": 1.8, "ts": "2026-07-22T00:00:00Z", "era": _ERA},
        ]
    }
    g = _gate(
        tmp_path,
        eval_quality_era=_ERA,
        baseline_state={"eval_quality_era": _ERA},
        quality_history_provenance_by_tier=prov,
    )
    g.baseline.baselines_by_tier = {1: 1.16}
    verdict = g.check(_result(1.85, tier=1))
    assert verdict.passed
    assert "mad_noise" not in verdict.categories


def test_unfenced_mad_uses_full_window(tmp_path) -> None:
    # Regression guard: with no active era the era filter is inert and the full window is used
    # exactly like the pre-fence gate (mirrors test_safety_gate_mad behavior).
    g = _gate(tmp_path, quality_history=[2.00, 2.02, 1.98, 2.01, 1.99])
    g.baseline.baselines_by_tier = {2: 1.16}
    verdict = g.check(_result(2.01, tier=2))
    assert verdict.passed
    assert "mad_noise" in verdict.categories
