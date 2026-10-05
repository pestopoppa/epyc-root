"""SafetyGate speed-axis era provenance + absent-per-suite-data rendering (2026-08-03).

PART 1 — speed-instrument era fence. Before this the gate carried era provenance for the
eval QUALITY axis only (``eval_quality_era``). The THROUGHPUT floor compared
``result.speed < baseline.frontdoor_speed * 0.8`` with no era check at all, so a post-v8
trial could be charged against a floor derived from a pre-v8 baseline and nothing recorded
would reveal it. The fence mirrors the quality mechanism exactly (baseline field ->
load/save -> __init__ param -> rebaseline property), but DEMOTES rather than hard-fails:
charging a trial against an unattributable floor is the defect, so refusing the trial would
just relocate it.

PART 2 — ``analyze_failure``'s DEGRADED SUITES block rendered absent per-suite data as a
measured ``0.000``, and rendered n=1 quantization the same way it rendered a real collapse.

Every test here also pins the NEGATIVE case: with a same-era (or unfenced) baseline the
throughput floor must still bind normally. A guard that can be passed by deleting what it
inspects is not a guard.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import scripts.autopilot.host_health as hh  # noqa: E402
from safety_gate import (  # type: ignore[import-not-found]  # noqa: E402
    Baseline,
    EvalResult,
    SafetyGate,
    SafetyVerdict,
)

_SPEED_ERA = "E8-autopilot-speed"
_OLD_SPEED_ERA = "E7-autopilot-speed"


def _result(
    quality: float = 2.5,
    *,
    speed: float = 10.0,
    tier: int = 1,
    reliability: float = 0.99,
    **kw,
) -> EvalResult:
    return EvalResult(
        tier=tier,
        quality=quality,
        speed=speed,
        cost=0.1,
        reliability=reliability,
        per_suite_quality=kw.pop("per_suite_quality", {"coder": quality}),
        routing_distribution=kw.pop("routing_distribution", {"worker": 1.0}),
        **kw,
    )


def _gate(tmp_path, *, frontdoor_speed: float = 100.0, **kw) -> SafetyGate:
    """Gate whose throughput floor is 80 t/s, so a 10 t/s result is well under it."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", **kw)
    g.baseline.frontdoor_speed = frontdoor_speed
    g.baseline.baselines_by_tier = {}  # keep the quality legs out of the way
    return g


class _FakeHostState:
    def __init__(self, throttled: bool, triggers: list[str]):
        self._t = (throttled, triggers)

    def is_throttled(self):
        return self._t


def _no_throttle(monkeypatch) -> None:
    """Pin host-throttle detection OFF so the throughput branch is decided by era alone."""
    monkeypatch.setattr(
        hh.HostHealthState, "snapshot", staticmethod(lambda: _FakeHostState(False, []))
    )


# =========================================================================================
# PART 1a — the fence itself (provenance plumbing)
# =========================================================================================


def test_baseline_defaults_to_unstamped_speed_era() -> None:
    assert Baseline().autopilot_speed_era == ""


def test_speed_era_round_trips_through_state() -> None:
    b = Baseline()
    b.apply_state({"autopilot_speed_era": f"  {_SPEED_ERA}  "})
    assert b.autopilot_speed_era == _SPEED_ERA
    assert b.to_state_dict()["autopilot_speed_era"] == _SPEED_ERA


def test_unstamped_baseline_omits_speed_era_from_state_payload() -> None:
    # A legacy (unstamped) baseline's payload must stay byte-identical to the pre-fence
    # shape, so a missing key decodes back to the pre-boundary default.
    assert "autopilot_speed_era" not in Baseline().to_state_dict()


def test_no_active_speed_era_never_trips_hold(tmp_path) -> None:
    g = _gate(tmp_path)  # unfenced
    assert g.speed_rebaseline_required is False


def test_legacy_baseline_vs_active_speed_era_trips_hold(tmp_path) -> None:
    g = _gate(tmp_path, autopilot_speed_era=_SPEED_ERA)
    assert g.speed_rebaseline_required is True


def test_stale_era_baseline_vs_active_speed_era_trips_hold(tmp_path) -> None:
    g = _gate(
        tmp_path,
        autopilot_speed_era=_SPEED_ERA,
        baseline_state={"autopilot_speed_era": _OLD_SPEED_ERA},
    )
    assert g.speed_rebaseline_required is True


def test_same_era_baseline_does_not_trip_hold(tmp_path) -> None:
    g = _gate(
        tmp_path,
        autopilot_speed_era=_SPEED_ERA,
        baseline_state={"autopilot_speed_era": _SPEED_ERA},
    )
    assert g.speed_rebaseline_required is False


def test_speed_and_quality_fences_are_independent(tmp_path) -> None:
    """A same-era SPEED baseline must not be excused by a quality-era mismatch, or vice
    versa — the two axes carry different provenance and must not be conflated."""
    g = _gate(
        tmp_path,
        autopilot_speed_era=_SPEED_ERA,
        eval_quality_era="E8",
        baseline_state={"autopilot_speed_era": _SPEED_ERA},  # quality era absent
    )
    assert g.speed_rebaseline_required is False
    assert g.quality_rebaseline_required is True


# =========================================================================================
# PART 1b — check() behaviour: demote across eras, ENFORCE within one
# =========================================================================================


def test_cross_era_demotes_throughput_violation_to_warning(tmp_path, monkeypatch) -> None:
    _no_throttle(monkeypatch)
    g = _gate(tmp_path, autopilot_speed_era=_SPEED_ERA)
    verdict = g.check(_result(speed=10.0))  # floor is 80 t/s
    assert verdict.passed is True, "an unattributable floor must not force-revert a config"
    assert "throughput_rebaseline_required" in verdict.categories
    assert "throughput" not in verdict.categories
    assert not any("Throughput floor" in v for v in verdict.violations)
    assert any("speed_rebaseline_required" in w for w in verdict.warnings)
    # The demotion warning must still carry the numbers, so the operator can see WHAT was
    # withheld rather than just that something was.
    assert any("10.0 t/s" in w and "80.0 t/s" in w for w in verdict.warnings)


def test_same_era_baseline_still_enforces_throughput_floor(tmp_path, monkeypatch) -> None:
    """NEGATIVE CASE. The fence must only excuse a CROSS-era comparison. With the baseline
    stamped under the active era the floor binds exactly as before — otherwise the guard
    could be passed simply by declaring an era."""
    _no_throttle(monkeypatch)
    g = _gate(
        tmp_path,
        autopilot_speed_era=_SPEED_ERA,
        baseline_state={"autopilot_speed_era": _SPEED_ERA},
    )
    verdict = g.check(_result(speed=10.0))
    assert verdict.passed is False
    assert "throughput" in verdict.categories
    assert "throughput_rebaseline_required" not in verdict.categories
    assert any("Throughput floor" in v for v in verdict.violations)


def test_unfenced_gate_still_enforces_throughput_floor(tmp_path, monkeypatch) -> None:
    """NEGATIVE CASE. With no active speed era at all (single-era world / every
    pre-existing caller) the new branch is inert and behaviour is unchanged."""
    _no_throttle(monkeypatch)
    g = _gate(tmp_path)
    verdict = g.check(_result(speed=10.0))
    assert verdict.passed is False
    assert "throughput" in verdict.categories
    assert "throughput_rebaseline_required" not in verdict.categories


def test_cross_era_hold_does_not_excuse_a_healthy_speed(tmp_path, monkeypatch) -> None:
    """The hold must only fire when the floor was actually about to be charged; a result
    above the floor must not acquire a spurious rebaseline category."""
    _no_throttle(monkeypatch)
    g = _gate(tmp_path, autopilot_speed_era=_SPEED_ERA)
    verdict = g.check(_result(speed=95.0))  # comfortably above the 80 t/s floor
    assert "throughput_rebaseline_required" not in verdict.categories
    assert "throughput" not in verdict.categories


def test_cross_era_hold_logs_loudly_once(tmp_path, monkeypatch, caplog) -> None:
    _no_throttle(monkeypatch)
    g = _gate(tmp_path, autopilot_speed_era=_SPEED_ERA)
    with caplog.at_level(logging.ERROR, logger="autopilot.safety"):
        g.check(_result(speed=10.0))
        g.check(_result(speed=10.0))
    holds = [r for r in caplog.records if "SPEED-INSTRUMENT RE-BASELINE HOLD" in r.getMessage()]
    assert len(holds) == 1, "loud, but once per gate instance — not spam"
    assert _SPEED_ERA in holds[0].getMessage()


def test_era_hold_and_throttle_demotion_compose(tmp_path, monkeypatch) -> None:
    """SG-9's throttle demotion and the era hold mean different things downstream
    (exogenous_cache_flush excludes the trial from the planner's trust window; the era hold
    says the FLOOR is unattributable). When both apply, BOTH must be recorded — and the
    violation must still be demoted exactly once."""
    monkeypatch.setattr(
        hh.HostHealthState,
        "snapshot",
        staticmethod(lambda: _FakeHostState(True, ["cpu_freq_dip"])),
    )
    g = _gate(tmp_path, autopilot_speed_era=_SPEED_ERA)
    verdict = g.check(_result(speed=10.0))
    assert verdict.passed is True
    assert "throughput_rebaseline_required" in verdict.categories
    assert "throughput_throttle_demoted" in verdict.categories
    assert "exogenous_cache_flush" in verdict.categories
    assert "throughput" not in verdict.categories
    assert verdict.categories.count("throughput_rebaseline_required") == 1


def test_unmeasured_speed_branch_takes_precedence_over_era_hold(tmp_path) -> None:
    """A reliability-blocked 0.0 t/s sample is ABSENT, not slow; that branch is more
    specific than the era hold and must keep owning the trial."""
    g = _gate(tmp_path, autopilot_speed_era=_SPEED_ERA)
    verdict = g.check(_result(speed=0.0, reliability=0.1))
    assert "throughput_unmeasured" in verdict.categories
    assert "throughput_rebaseline_required" not in verdict.categories
    assert "throughput" not in verdict.categories


# =========================================================================================
# PART 1c — update_baseline stamps the era so a reseed closes the hold
# =========================================================================================


def test_update_baseline_stamps_active_speed_era(tmp_path, monkeypatch) -> None:
    g = _gate(
        tmp_path,
        autopilot_speed_era=_SPEED_ERA,
        baseline_state={"baselines_by_tier": {"1": 1.0}},
    )
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {}))
    monkeypatch.setattr(g, "_archive_best_quality", lambda tier: None)
    assert g.speed_rebaseline_required is True
    res = g.update_baseline(_result(2.9, tier=1, speed=42.0), source_trial_id=5)
    assert res.updated is True
    assert g.baseline.autopilot_speed_era == _SPEED_ERA
    # A promotion that actually re-measured frontdoor_speed closes the hold naturally.
    assert g.baseline.frontdoor_speed == 42.0
    assert g.speed_rebaseline_required is False


def test_update_baseline_does_not_stamp_speed_era_without_a_speed_sample(
    tmp_path, monkeypatch
) -> None:
    """update_tier only rewrites frontdoor_speed when speed > 0. Stamping the era onto a
    frontdoor_speed that was never re-measured would itself be the provenance lie this
    field exists to prevent."""
    g = _gate(
        tmp_path,
        autopilot_speed_era=_SPEED_ERA,
        baseline_state={"baselines_by_tier": {"1": 1.0}},
    )
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {}))
    monkeypatch.setattr(g, "_archive_best_quality", lambda tier: None)
    before = g.baseline.frontdoor_speed
    res = g.update_baseline(_result(2.9, tier=1, speed=0.0), source_trial_id=5)
    assert res.updated is True
    assert g.baseline.frontdoor_speed == before, "no speed sample => frontdoor_speed unchanged"
    assert g.baseline.autopilot_speed_era == ""
    assert g.speed_rebaseline_required is True, "the hold must survive a speed-less promotion"


def test_unfenced_update_baseline_never_invents_a_speed_era(tmp_path, monkeypatch) -> None:
    g = _gate(tmp_path, baseline_state={"baselines_by_tier": {"1": 1.0}})
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {}))
    monkeypatch.setattr(g, "_archive_best_quality", lambda tier: None)
    assert g.update_baseline(_result(2.9, tier=1, speed=42.0), source_trial_id=5).updated is True
    assert g.baseline.autopilot_speed_era == ""


# =========================================================================================
# PART 2 — absent per-suite data must never render as a measured 0.000
# =========================================================================================


_FAILED = SafetyVerdict(passed=False, violations=["Throughput floor: 7.4 t/s < 10.2 t/s"])


def _degraded_section(analysis: str) -> str:
    assert "DEGRADED SUITES:" in analysis
    return analysis.split("DEGRADED SUITES:")[1].split("\n\n")[0]


def test_none_per_suite_score_renders_as_absent_not_zero() -> None:
    """A None per-suite value is 'not measured'. It previously raised TypeError on
    `None < floor`, taking the whole failure narrative down with it."""
    result = _result(per_suite_quality={"coder": 2.0, "gpqa_diamond": None})
    analysis = SafetyGate.analyze_failure(result, _FAILED)
    assert "gpqa_diamond: not measured" in analysis
    assert "gpqa_diamond: 0.000" not in analysis


def test_nan_per_suite_score_renders_as_absent_not_silently_dropped() -> None:
    """`nan < floor` is False, so a NaN suite used to vanish with no trace at all."""
    result = _result(per_suite_quality={"coder": 2.0, "ruler": float("nan")})
    analysis = SafetyGate.analyze_failure(result, _FAILED)
    assert "ruler: not measured" in analysis
    assert "ruler: 0.000" not in analysis
    assert "nan" not in analysis.lower().replace("not measured", "")


def test_suite_with_no_scoreable_question_is_labelled_absent() -> None:
    """A suite that drew questions but had NONE of them scored never reaches
    per_suite_quality; it used to disappear entirely from the narrative."""
    result = _result(
        per_suite_quality={"coder": 2.0},
        per_suite_counts={"coder": 5},
        details={"per_suite_total_counts": {"coder": 5, "physics": 3}},
    )
    analysis = SafetyGate.analyze_failure(result, _FAILED)
    assert "physics: not measured (0 of 3 questions scored)" in analysis
    assert "physics: 0.000" not in analysis


def test_absent_suites_are_not_listed_as_degraded() -> None:
    result = _result(
        per_suite_quality={"coder": 2.0, "gpqa": None},
        details={"per_suite_total_counts": {"coder": 5, "gpqa": 1, "physics": 3}},
    )
    analysis = SafetyGate.analyze_failure(result, _FAILED)
    assert "DEGRADED SUITES:" not in analysis, "absence is not degradation"
    assert "SUITES WITHOUT A MEASURED SCORE" in analysis


def test_low_resolution_zero_is_labelled_as_resolution_not_regression() -> None:
    """The reported symptom: 13 lines of `<suite>: 0.000 (floor: 1.0)` from n=1 draws,
    which reads as 13 regressions. At n=1 the 0-3 score can only be 0.0 or 3.0."""
    result = _result(
        per_suite_quality={"aime": 0.0, "gpqa": 0.0, "ruler": 0.0},
        per_suite_counts={"aime": 1, "gpqa": 1, "ruler": 1},
    )
    section = _degraded_section(SafetyGate.analyze_failure(result, _FAILED))
    assert section.count("[low-resolution]") == 3
    assert "n=1" in section
    assert "NOT as measured regressions" in section


def test_well_supported_zero_is_not_labelled_low_resolution() -> None:
    """NEGATIVE CASE. A 0.000 measured over 50 questions IS a real collapse and must keep
    reading as one — the annotation must not launder every zero."""
    result = _result(per_suite_quality={"coder": 0.0}, per_suite_counts={"coder": 50})
    section = _degraded_section(SafetyGate.analyze_failure(result, _FAILED))
    assert "coder: 0.000 (floor: 1.0, n=50)" in section
    assert "low-resolution" not in section
    assert "NOTE:" not in section


def test_missing_count_is_labelled_unknown_not_assumed_adequate() -> None:
    """No per-suite count at all is itself absent provenance: it must not be silently
    treated as a well-supported sample."""
    result = _result(per_suite_quality={"coder": 0.0})  # per_suite_counts empty
    section = _degraded_section(SafetyGate.analyze_failure(result, _FAILED))
    assert "n=unknown" in section
    assert "[low-resolution]" in section


def test_suites_above_floor_are_still_excluded(tmp_path) -> None:
    """NEGATIVE CASE: the rewrite must not start listing healthy suites."""
    result = _result(
        per_suite_quality={"coder": 2.8, "math": 0.5},
        per_suite_counts={"coder": 50, "math": 50},
        details={"per_suite_total_counts": {"coder": 50, "math": 50}},
    )
    analysis = SafetyGate.analyze_failure(result, _FAILED)
    section = _degraded_section(analysis)
    assert "math" in section
    assert "coder" not in section
    assert "SUITES WITHOUT A MEASURED SCORE" not in analysis


def test_passing_verdict_still_returns_empty_narrative() -> None:
    result = _result(per_suite_quality={"coder": None})
    assert SafetyGate.analyze_failure(result, SafetyVerdict(passed=True, violations=[])) == ""
