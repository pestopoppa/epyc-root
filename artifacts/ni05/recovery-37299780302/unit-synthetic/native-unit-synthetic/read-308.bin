"""RTG-02 (2026-09-14): era-stamp REACHABILITY on both instrument axes.

Two defects, one shape: a baseline that can never acquire the era stamp it is required to
carry, so the instrument fences stay held open forever and quality promotion is dead.

(a) ``SafetyGate.update_baseline`` stamped ``baseline.autopilot_speed_era`` at the very END
    of the method, AFTER the eval-quality re-baseline hold returns early. The two fences are
    DIFFERENT INSTRUMENTS with DIFFERENT eras, but the speed stamp sat behind the quality
    refusal: while the quality hold is open no promotion completes, so the speed stamp never
    executes, so ``speed_rebaseline_required`` stays True forever — and the quality hold's
    own remediation is a reseeded, era-stamped baseline, which the loop cannot produce.
    The stamp waits on a rebaseline that waits on the stamp.

(b) ``autopilot._apply_calibrated_baseline_result`` wrote every baseline VALUE
    (baselines_by_tier / per_suite_*) and never wrote ``eval_quality_era``, so the one
    in-tree tool that produces a fresh baseline left the quality hold exactly where it was
    (documented verbatim in ``operator_seed_e8_operational_baseline.py``'s own header).
    The era it must stamp is the era of the INSTRUMENT THAT PRODUCED THE RESULT — carried on
    the result by ``eval_tower._stamp_eval_instrument`` — never the era current at write
    time, which differs from it across exactly the boundary the fence exists to detect.

Every test pins the NEGATIVE case too: the quality refusal stays fail-closed, and the speed
axis is NOT stamped where ``update_tier`` would not have re-measured ``frontdoor_speed``
(stamping an era onto a speed nobody re-measured is itself the provenance lie).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))
sys.path.insert(0, str(REPO_ROOT))

import autopilot  # type: ignore[import-not-found]  # noqa: E402
import eval_tower  # type: ignore[import-not-found]  # noqa: E402
from safety_gate import (  # type: ignore[import-not-found]  # noqa: E402
    Baseline,
    EvalResult,
    SafetyGate,
)
from src.autopilot_core.tier_specs import DEFAULT_FRONTIER_TIER  # noqa: E402

_QUALITY_ERA = "E16-eval-instrument"
_OLD_QUALITY_ERA = "E8-eval-instrument"
_SPEED_ERA = "E9-autopilot-speed"
_OLD_SPEED_ERA = "E8-autopilot-speed"


def _result(
    *,
    tier: int = DEFAULT_FRONTIER_TIER,
    quality: float = 2.5,
    speed: float = 42.0,
) -> EvalResult:
    return EvalResult(
        tier=tier,
        quality=quality,
        speed=speed,
        cost=0.1,
        reliability=0.99,
        per_suite_quality={"coder": quality},
        per_suite_counts={"coder": 10},
        n_questions=50,
        speed_metric_mode="aggregate_batch_tps",
    )


def _gate(tmp_path, monkeypatch, **kw) -> SafetyGate:
    """A gate whose eligibility + archive legs are out of the way, with both eras active."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", **kw)
    g.baseline.frontdoor_speed = 100.0
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {"x": 1}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: None))
    return g


def _held_gate(tmp_path, monkeypatch, **kw) -> SafetyGate:
    """Both fences OPEN: resident baseline stamped under the PREVIOUS era on both axes."""
    return _gate(
        tmp_path,
        monkeypatch,
        eval_quality_era=_QUALITY_ERA,
        autopilot_speed_era=_SPEED_ERA,
        baseline_state={
            "eval_quality_era": _OLD_QUALITY_ERA,
            "autopilot_speed_era": _OLD_SPEED_ERA,
        },
        **kw,
    )


# =========================================================================================
# (a) the deadlock
# =========================================================================================


def test_quality_hold_and_speed_hold_are_both_open_in_the_deadlock_state(tmp_path, monkeypatch):
    g = _held_gate(tmp_path, monkeypatch)
    assert g.quality_rebaseline_required is True
    assert g.speed_rebaseline_required is True


def test_speed_era_stamp_is_reachable_while_the_quality_hold_is_open(tmp_path, monkeypatch):
    """THE DEADLOCK. Pre-fix the quality-hold early return made the speed stamp unreachable."""
    g = _held_gate(tmp_path, monkeypatch)
    outcome = g.update_baseline(_result(), source_trial_id=1)

    assert outcome.updated is False, "quality promotion must stay REFUSED (fail-closed)"
    assert g.baseline.autopilot_speed_era == _SPEED_ERA, (
        "the SPEED era must be stamped independently of the quality hold — otherwise the "
        "throughput fence can never close"
    )
    assert g.speed_rebaseline_required is False, "speed hold must clear on its own axis"
    assert outcome.speed_reseeded is True


def test_speed_reseed_reanchors_frontdoor_speed_to_the_in_era_measurement(tmp_path, monkeypatch):
    g = _held_gate(tmp_path, monkeypatch)
    g.update_baseline(_result(speed=42.0), source_trial_id=1)
    assert g.baseline.frontdoor_speed == pytest.approx(42.0), (
        "the era stamp must name the speed it was measured with, not inherit the "
        "pre-boundary 100.0 floor"
    )


def test_quality_hold_refusal_stays_fail_closed_and_attributable(tmp_path, monkeypatch):
    g = _held_gate(tmp_path, monkeypatch)
    outcome = g.update_baseline(_result(), source_trial_id=1)
    assert outcome.ineligible_reason == "quality_rebaseline_required"
    assert "RE-BASELINE required" in outcome.reason
    assert g.baseline.eval_quality_era == _OLD_QUALITY_ERA, "quality era must NOT be advanced"
    assert g.baseline.quality_for_tier(DEFAULT_FRONTIER_TIER, strict=True) is None, (
        "no quality value may be written while the quality fence is held"
    )


def test_speed_reseed_refused_off_the_frontier_tier(tmp_path, monkeypatch):
    """frontdoor_speed is only re-measured at the frontier tier; anything else is a lie."""
    g = _held_gate(tmp_path, monkeypatch)
    outcome = g.update_baseline(_result(tier=2), source_trial_id=1)
    assert outcome.speed_reseeded is False
    assert g.baseline.autopilot_speed_era == _OLD_SPEED_ERA
    assert g.baseline.frontdoor_speed == pytest.approx(100.0)


def test_speed_reseed_refused_without_a_positive_speed_sample(tmp_path, monkeypatch):
    g = _held_gate(tmp_path, monkeypatch)
    outcome = g.update_baseline(_result(speed=0.0), source_trial_id=1)
    assert outcome.speed_reseeded is False
    assert g.baseline.autopilot_speed_era == _OLD_SPEED_ERA
    assert g.baseline.frontdoor_speed == pytest.approx(100.0)


def test_unfenced_speed_axis_is_never_stamped_under_a_quality_hold(tmp_path, monkeypatch):
    """No active speed era => the speed axis stays byte-identical to the pre-fence shape."""
    g = _gate(
        tmp_path,
        monkeypatch,
        eval_quality_era=_QUALITY_ERA,
        baseline_state={"eval_quality_era": _OLD_QUALITY_ERA},
    )
    outcome = g.update_baseline(_result(), source_trial_id=1)
    assert outcome.speed_reseeded is False
    assert g.baseline.autopilot_speed_era == ""
    assert g.baseline.frontdoor_speed == pytest.approx(100.0)


def test_already_in_era_speed_baseline_is_not_rewritten_under_a_quality_hold(tmp_path, monkeypatch):
    """The reseed fires only while the speed hold is OPEN — it is not a speed ratchet."""
    g = _gate(
        tmp_path,
        monkeypatch,
        eval_quality_era=_QUALITY_ERA,
        autopilot_speed_era=_SPEED_ERA,
        baseline_state={
            "eval_quality_era": _OLD_QUALITY_ERA,
            "autopilot_speed_era": _SPEED_ERA,
        },
    )
    outcome = g.update_baseline(_result(speed=42.0), source_trial_id=1)
    assert outcome.speed_reseeded is False
    assert g.baseline.frontdoor_speed == pytest.approx(100.0)


def test_ineligible_result_never_reseeds_the_speed_axis(tmp_path, monkeypatch):
    """Eligibility (speed semantics + certified-fresh contention matrix) still gates first."""
    g = SafetyGate(
        baseline_path=tmp_path / "absent.yaml",
        eval_quality_era=_QUALITY_ERA,
        autopilot_speed_era=_SPEED_ERA,
        baseline_state={
            "eval_quality_era": _OLD_QUALITY_ERA,
            "autopilot_speed_era": _OLD_SPEED_ERA,
        },
    )
    g.baseline.frontdoor_speed = 100.0
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (False, "stale-matrix", {}))
    outcome = g.update_baseline(_result(), source_trial_id=1)
    assert outcome.speed_reseeded is False
    assert g.baseline.autopilot_speed_era == _OLD_SPEED_ERA
    assert g.baseline.frontdoor_speed == pytest.approx(100.0)


def test_promotion_path_still_stamps_both_eras(tmp_path, monkeypatch):
    """Regression: with the quality fence SATISFIED the ordinary promotion still stamps both."""
    g = _gate(
        tmp_path,
        monkeypatch,
        eval_quality_era=_QUALITY_ERA,
        autopilot_speed_era=_SPEED_ERA,
        baseline_state={"eval_quality_era": _QUALITY_ERA},
    )
    outcome = g.update_baseline(_result(speed=42.0), source_trial_id=1)
    assert outcome.updated is True
    assert g.baseline.eval_quality_era == _QUALITY_ERA
    assert g.baseline.autopilot_speed_era == _SPEED_ERA
    assert outcome.speed_reseeded is False, "a completed promotion is not a held-axis reseed"


def test_speed_reseeded_defaults_false_on_the_result_contract() -> None:
    from safety_gate import BaselineUpdateResult  # noqa: PLC0415

    assert BaselineUpdateResult(True, "r", 1, None, 2.0).speed_reseeded is False


def test_speed_reseed_is_not_logged_as_a_skipped_no_op(caplog) -> None:
    """A refusal that re-anchored the speed axis WROTE state; it must not read as 'skipped'."""
    from safety_gate import BaselineUpdateResult  # noqa: PLC0415

    outcome = BaselineUpdateResult(
        False, "hold", DEFAULT_FRONTIER_TIER, None, 2.0, speed_reseeded=True
    )
    with caplog.at_level("INFO"):
        autopilot._log_baseline_update_result(7, outcome)
    assert "speed axis was re-anchored" in caplog.text
    assert "baseline update skipped" not in caplog.text


# =========================================================================================
# (b) the calibration era stamp
# =========================================================================================


def _stamped_result(era: str | None = _QUALITY_ERA, status: str = "active") -> EvalResult:
    result = _result()
    result.details["eval_quality_era_status"] = status
    if era is not None:
        result.details["eval_quality_era"] = era
    return result


def test_calibrated_baseline_stamps_the_producing_instruments_era(tmp_path) -> None:
    baseline = Baseline(source_path=tmp_path / "b.yaml")
    autopilot._apply_calibrated_baseline_result(baseline, _stamped_result())
    assert baseline.eval_quality_era == _QUALITY_ERA
    assert baseline.baselines_by_tier[DEFAULT_FRONTIER_TIER] == pytest.approx(2.5)


def test_calibrated_baseline_stamps_the_results_era_not_the_era_current_now(tmp_path) -> None:
    """A result produced before a boundary must be stamped with ITS era, not today's."""
    baseline = Baseline(source_path=tmp_path / "b.yaml")
    autopilot._apply_calibrated_baseline_result(baseline, _stamped_result(era=_OLD_QUALITY_ERA))
    assert baseline.eval_quality_era == _OLD_QUALITY_ERA


def test_calibrated_baseline_refuses_an_unstamped_result(tmp_path) -> None:
    baseline = Baseline(source_path=tmp_path / "b.yaml")
    result = _result()  # no era, no status — the pre-RTG-02 shape
    with pytest.raises(ValueError, match="eval_quality era"):
        autopilot._apply_calibrated_baseline_result(baseline, result)
    assert baseline.baselines_by_tier == {}, "refusal must write NOTHING (fail-closed)"
    assert baseline.eval_quality_era == ""


def test_calibrated_baseline_refuses_an_unresolved_era_registry(tmp_path) -> None:
    baseline = Baseline(source_path=tmp_path / "b.yaml")
    with pytest.raises(ValueError, match="eval_quality era"):
        autopilot._apply_calibrated_baseline_result(
            baseline, _stamped_result(era=None, status="unresolved")
        )
    assert baseline.baselines_by_tier == {}


def test_calibrated_baseline_accepts_an_unfenced_single_era_world(tmp_path) -> None:
    """Registry read fine, no eval_quality era open => nothing to stamp, hold is inert."""
    baseline = Baseline(source_path=tmp_path / "b.yaml")
    autopilot._apply_calibrated_baseline_result(
        baseline, _stamped_result(era=None, status="unfenced")
    )
    assert baseline.eval_quality_era == ""
    assert baseline.baselines_by_tier[DEFAULT_FRONTIER_TIER] == pytest.approx(2.5)


def test_calibrated_baseline_never_clears_an_existing_stamp_when_unfenced(tmp_path) -> None:
    baseline = Baseline(source_path=tmp_path / "b.yaml", eval_quality_era=_OLD_QUALITY_ERA)
    autopilot._apply_calibrated_baseline_result(
        baseline, _stamped_result(era=None, status="unfenced")
    )
    assert baseline.eval_quality_era == _OLD_QUALITY_ERA


def test_calibrated_baseline_closes_the_hold_end_to_end(tmp_path, monkeypatch) -> None:
    """The point of (b): after a calibration the gate's quality fence is CLOSED."""
    baseline = Baseline(source_path=tmp_path / "b.yaml", eval_quality_era=_OLD_QUALITY_ERA)
    autopilot._apply_calibrated_baseline_result(baseline, _stamped_result())
    g = SafetyGate(
        baseline_path=tmp_path / "absent.yaml",
        baseline_state=baseline.to_state_dict(),
        eval_quality_era=_QUALITY_ERA,
    )
    assert g.quality_rebaseline_required is False


# ── the era carrier: eval_tower stamps every tier result ────────────────────────────────


def test_eval_tower_stamps_the_active_era_on_every_result(monkeypatch) -> None:
    monkeypatch.setattr(
        eval_tower,
        "active_eval_quality_era",
        lambda: {"ok": True, "status": "active", "era_id": _QUALITY_ERA},
    )
    result = eval_tower._stamp_eval_instrument(
        _result(), questions=[], core_id="core-x", test_profile={}
    )
    assert result.details["eval_quality_era"] == _QUALITY_ERA
    assert result.details["eval_quality_era_status"] == "active"


def test_eval_tower_marks_an_unfenced_axis_explicitly(monkeypatch) -> None:
    monkeypatch.setattr(
        eval_tower,
        "active_eval_quality_era",
        lambda: {"ok": False, "status": "no_active_era"},
    )
    result = eval_tower._stamp_eval_instrument(
        _result(), questions=[], core_id="core-x", test_profile={}
    )
    assert result.details["eval_quality_era_status"] == "unfenced"
    assert "eval_quality_era" not in result.details


def test_eval_tower_invents_no_era_when_the_registry_is_unreadable(monkeypatch) -> None:
    monkeypatch.setattr(
        eval_tower,
        "active_eval_quality_era",
        lambda: {"ok": False, "status": "missing_registry", "reason": "boom"},
    )
    result = eval_tower._stamp_eval_instrument(
        _result(), questions=[], core_id="core-x", test_profile={}
    )
    assert result.details["eval_quality_era_status"] == "unresolved"
    assert "eval_quality_era" not in result.details


def test_eval_tower_treats_an_empty_era_id_as_unresolved(monkeypatch) -> None:
    monkeypatch.setattr(
        eval_tower,
        "active_eval_quality_era",
        lambda: {"ok": True, "status": "active", "era_id": "  "},
    )
    result = eval_tower._stamp_eval_instrument(
        _result(), questions=[], core_id="core-x", test_profile={}
    )
    assert result.details["eval_quality_era_status"] == "unresolved"
    assert "eval_quality_era" not in result.details
