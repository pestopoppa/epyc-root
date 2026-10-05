"""Resolution-aware per-suite regression gate + failed-verdict learning exclusion.

Root cause of the 2026-06-06 planner/critic deadlock (trial 707): the per-suite
regression gate compared per-suite scores quantized to {0.0, 1.5, 3.0} (≈2
questions/suite on a hybrid eval) against a fixed -0.1 floor. A single
correct→incorrect flip is a -1.5 swing — 15× the floor — so the gate fired on
essentially every seeder trial, every such trial was excluded via mad_noise, and
the planner looped until the critic guard halted it.

Two coupled fixes:
  1. safety_gate.per_suite_regression_threshold() widens the floor to the coarser
     of the result/baseline single-flip quantum (3/n) when counts are known.
     Low-support threshold crossings are advisory unless the drop is catastrophic.
  2. classify_learning_exclusion() treats mad_noise as benign ONLY when the
     verdict otherwise passed, so a failed verdict can't be laundered into a
     trusted Pareto representative.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from safety_gate import (  # type: ignore[import-not-found]
    EvalResult,
    SafetyGate,
    PER_SUITE_REGRESSION,
    per_suite_regression_threshold,
)
from autopilot import classify_learning_exclusion  # type: ignore[import-not-found]


# ── per_suite_regression_threshold ────────────────────────────────────────────

def test_threshold_falls_back_to_fixed_floor_without_counts():
    """No counts (legacy baseline) ⇒ unchanged -0.1 floor."""
    assert per_suite_regression_threshold(None, None) == PER_SUITE_REGRESSION
    assert per_suite_regression_threshold(0, 0) == PER_SUITE_REGRESSION


def test_threshold_widens_to_single_flip_quantum_at_low_n():
    """At 2 questions/suite a single flip is 1.5 → threshold must be -1.5 so the
    flip is NOT counted as a regression."""
    assert per_suite_regression_threshold(2, 2) == -1.5
    # A one-flip drop (3.0 -> 1.5) is exactly -1.5, which is NOT < -1.5 → no fire.
    assert not ((1.5 - 3.0) < per_suite_regression_threshold(2, 2))
    # A two-flip collapse (3.0 -> 0.0) IS < -1.5 → genuine regression still fires.
    assert (0.0 - 3.0) < per_suite_regression_threshold(2, 2)


def test_threshold_uses_coarser_of_the_two_samples():
    """Mismatched n ⇒ the coarser (smaller-n) quantum governs."""
    # result n=2 (quantum 1.5) vs baseline n=10 (quantum 0.3) → 1.5 wins.
    assert per_suite_regression_threshold(2, 10) == -1.5
    assert per_suite_regression_threshold(10, 2) == -1.5


def test_threshold_never_tighter_than_fixed_floor():
    """At large n the quantum is tiny; the fixed -0.1 floor still applies."""
    assert per_suite_regression_threshold(100, 100) == PER_SUITE_REGRESSION


# ── gate.check integration ────────────────────────────────────────────────────

def _gate(tmp_path):
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    g.baseline.frontdoor_speed = 1.0
    return g


def _trial(per_suite, counts, tier=1, quality=1.7):
    return EvalResult(
        tier=tier,
        quality=quality,
        speed=99.0,
        cost=0.1,
        reliability=0.99,
        per_suite_quality=per_suite,
        per_suite_counts=counts,
        routing_distribution={"worker": 1.0},
    )


def test_single_question_flip_at_n2_is_not_a_regression(tmp_path):
    """The trial-707 case: baseline 3.0, result 1.5, n=2 each → noise, not gate."""
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {1: {"hotpotqa": 3.0}}
    g.baseline.per_suite_counts_by_tier = {1: {"hotpotqa": 2}}
    verdict = g.check(_trial({"hotpotqa": 1.5}, {"hotpotqa": 2}))
    assert "per_suite_regression" not in verdict.categories


def test_sparse_baseline_moderate_drop_is_advisory_not_terminal(tmp_path):
    """W8 case: a two-question baseline should not make moderate drops terminal."""
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {1: {"general": 3.0}}
    g.baseline.per_suite_counts_by_tier = {1: {"general": 2}}
    verdict = g.check(_trial({"general": 1.2}, {"general": 5}))
    assert verdict.passed
    assert "per_suite_regression" not in verdict.categories
    assert "per_suite_regression_advisory" in verdict.categories
    # The n=2 baseline now takes the small-sample-baseline annotation path
    # (2026-07-16 thrash guard) rather than the generic low-support wording.
    assert any("small-sample baseline" in warning for warning in verdict.warnings)


def test_total_collapse_at_tiny_baseline_n_is_advisory_not_hard(tmp_path):
    """2026-07-16 rollback thrash (trials 1404-1433, resume-precondition in
    autopilot-continuous-optimization.md): a debugbench baseline measured on
    only n=2 scored 3.0, so a 0.0 trial looked like a -3.0 catastrophic
    collapse and hard-failed via the low-support catastrophic escape, feeding
    consecutive_failures into ~10 straight rollbacks. A baseline sampled below
    PER_SUITE_BASELINE_HARD_MIN_N can no longer certify a HARD rollback — the
    drop stays visible as an annotated advisory warning."""
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {1: {"debugbench": 3.0}}
    g.baseline.per_suite_counts_by_tier = {1: {"debugbench": 2}}
    verdict = g.check(_trial({"debugbench": 0.0}, {"debugbench": 2}))
    assert verdict.passed
    assert "per_suite_regression" not in verdict.categories
    assert "per_suite_regression_advisory" in verdict.categories
    assert any("small-sample baseline" in warning for warning in verdict.warnings)


def test_same_collapse_with_adequate_baseline_n_still_hard_fails(tmp_path):
    """The same -3.0 collapse against a baseline with n >= the minimum keeps
    its teeth: hard violation, not advisory."""
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {1: {"debugbench": 3.0}}
    g.baseline.per_suite_counts_by_tier = {1: {"debugbench": 5}}
    verdict = g.check(_trial({"debugbench": 0.0}, {"debugbench": 5}))
    assert not verdict.passed
    assert "per_suite_regression" in verdict.categories


def test_small_baseline_guard_min_n_is_env_configurable(tmp_path, monkeypatch):
    """AUTOPILOT_PER_SUITE_BASELINE_MIN_N=2 re-arms the catastrophic escape at
    n_baseline=2 (operator opt-in), while a malformed override is ignored."""
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {1: {"debugbench": 3.0}}
    g.baseline.per_suite_counts_by_tier = {1: {"debugbench": 2}}
    monkeypatch.setenv("AUTOPILOT_PER_SUITE_BASELINE_MIN_N", "2")
    verdict = g.check(_trial({"debugbench": 0.0}, {"debugbench": 2}))
    assert "per_suite_regression" in verdict.categories

    from safety_gate import _per_suite_regression_binding, PER_SUITE_BASELINE_HARD_MIN_N
    monkeypatch.setenv("AUTOPILOT_PER_SUITE_BASELINE_MIN_N", "banana")
    assert PER_SUITE_BASELINE_HARD_MIN_N == 5
    assert _per_suite_regression_binding(-3.0, 5, 2) is False  # falls back to 5
    monkeypatch.setenv("AUTOPILOT_PER_SUITE_BASELINE_MIN_N", "-3")
    assert _per_suite_regression_binding(-3.0, 5, 2) is False  # falls back to 5


def test_small_drop_at_high_n_still_regresses(tmp_path):
    """At adequate n the gate keeps its teeth: a 0.3 drop trips the -0.1 floor."""
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {1: {"coder": 2.4}}
    g.baseline.per_suite_counts_by_tier = {1: {"coder": 50}}
    verdict = g.check(_trial({"coder": 2.1}, {"coder": 50}))
    assert "per_suite_regression" in verdict.categories


def test_gate_check_is_idempotent_for_same_eval_result(tmp_path):
    """Action handlers and the main loop may both ask for a verdict; state mutates once."""
    g = _gate(tmp_path)
    result = _trial({"coder": 0.0}, {"coder": 50}, quality=0.0)
    first = g.check(result)
    second = g.check(result)
    assert second is first
    assert g.consecutive_failures == 1
    assert g.quality_history_for_tier(result.tier) == []


def test_counts_roundtrip_through_baseline_persistence(tmp_path):
    """per_suite_counts_by_tier must survive save()/load() so a refreshed baseline
    keeps its resolution after restart."""
    from safety_gate import Baseline
    path = tmp_path / "baseline.yaml"
    b = Baseline(source_path=path)
    b.per_suite_counts_by_tier = {1: {"hotpotqa": 2, "coder": 50}}
    b.per_suite_quality_by_tier = {1: {"hotpotqa": 3.0, "coder": 2.4}}
    b.save()
    restored = Baseline.load(path)
    assert restored.per_suite_counts_for_tier(1) == {"hotpotqa": 2, "coder": 50}


# ── classify_learning_exclusion: mad_noise must not mask a failed verdict ──────

@dataclass
class _FakeVerdict:
    categories: list[str] = field(default_factory=list)
    passed: bool = True


@dataclass
class _FakeEvalResult:
    n_exogenous_unrecovered: int = 0
    exogenous_question_ids: list[str] = field(default_factory=list)
    n_questions: int = 0


def test_mad_noise_benign_only_when_verdict_passed():
    v = _FakeVerdict(categories=["mad_noise"], passed=True)
    by, _, _ = classify_learning_exclusion(v, _FakeEvalResult())
    assert by == "mad_noise"


def test_mad_noise_with_failed_verdict_is_not_benign():
    """A failed verdict (e.g. genuine per-suite regression) co-tagged mad_noise must
    NOT be classified benign — else it is admitted as a trusted Pareto rep."""
    v = _FakeVerdict(categories=["per_suite_regression", "mad_noise"], passed=False)
    by, reason, def_cat = classify_learning_exclusion(v, _FakeEvalResult())
    assert by == "", "failed verdict must not be laundered as within-noise"
    assert reason == "" and def_cat == ""


def test_reproduction_confirmed_with_failed_verdict_is_not_benign():
    v = _FakeVerdict(
        categories=["per_suite_regression", "mad_noise", "reproduction_confirmed"],
        passed=False,
    )
    by, _, _ = classify_learning_exclusion(v, _FakeEvalResult())
    assert by == ""


# ── calibration path must propagate + persist per-suite counts ─────────────────

def test_calibration_applies_per_suite_counts():
    """_apply_calibrated_baseline_result must store counts, not just quality —
    else a live baseline refresh leaves the baseline-side 3/n term inactive."""
    from autopilot import _apply_calibrated_baseline_result  # type: ignore[import-not-found]
    from safety_gate import Baseline
    b = Baseline()
    r = EvalResult(
        tier=1, quality=1.7, speed=50.0, cost=0.5, reliability=0.98, n_questions=43,
        per_suite_quality={"hotpotqa": 1.5, "coder": 3.0},
        per_suite_counts={"hotpotqa": 2, "coder": 2},
        # RTG-02 (2026-09-14): every real EvalTower result now carries its eval-quality
        # instrument era (eval_tower._stamp_eval_instrument) and the calibration REFUSES an
        # unstamped result. Declare the unfenced single-era world so this test keeps
        # exercising the per-suite-count path it was written for, not the era refusal —
        # the refusal has its own coverage in test_era_stamp_reachability.py.
        details={"eval_quality_era_status": "unfenced"},
    )
    _apply_calibrated_baseline_result(b, r)
    assert b.per_suite_counts_for_tier(1) == {"hotpotqa": 2, "coder": 2}


def test_write_baseline_yaml_tiers_roundtrips_counts(tmp_path):
    """Fresh-file and existing-file (drop+reappend) write paths both persist counts,
    and a second write replaces the block rather than duplicating it."""
    from autopilot import _write_baseline_yaml_tiers  # type: ignore[import-not-found]
    from safety_gate import Baseline
    path = tmp_path / "autopilot_baseline.yaml"

    b = Baseline(source_path=path)
    b.baselines_by_tier = {1: 1.7}
    b.per_suite_quality_by_tier = {1: {"hotpotqa": 3.0}}
    b.per_suite_counts_by_tier = {1: {"hotpotqa": 2}}
    _write_baseline_yaml_tiers(path, b)  # fresh-file branch
    assert Baseline.load(path).per_suite_counts_for_tier(1) == {"hotpotqa": 2}

    b.per_suite_counts_by_tier = {1: {"hotpotqa": 50}}  # re-measured at higher n
    _write_baseline_yaml_tiers(path, b)  # existing-file drop+reappend branch
    assert Baseline.load(path).per_suite_counts_for_tier(1) == {"hotpotqa": 50}
    assert path.read_text().count("per_suite_counts_by_tier:") == 1, "no stale duplicate block"


# ── tool_use advisory regression gate ─────────────────────────────────────────


def test_tool_use_single_flip_is_at_resolution_noise(tmp_path):
    """B2 / SG-1: a -0.6 drop on tool_use is EXACTLY one flip of 5 questions (3/5=0.6),
    i.e. the single-flip quantum and the per-suite threshold itself. It is at-resolution
    noise, not even advisory — the PER_SUITE_EPS boundary guard keeps float rounding from
    crossing the bare `<`. (Before the fix, `2.4-3.0 = -0.6000000000000001` slipped just
    past `threshold = -0.6`, spuriously tagging this single flip as an advisory regression —
    one of the 185 (n,k) float-boundary artifacts.)"""
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {1: {"tool_use": 3.0}}
    g.baseline.per_suite_counts_by_tier = {1: {"tool_use": 5}}
    # 4/5 correct → 2.4, delta = -0.6 == one flip → below the crossing threshold.
    verdict = g.check(_trial({"tool_use": 2.4}, {"tool_use": 5}))
    assert verdict.passed
    assert "per_suite_regression" not in verdict.categories
    assert "tool_use_regression_advisory" not in verdict.categories


def test_tool_use_catastrophic_regression_still_blocks(tmp_path):
    """A -3.0 drop on tool_use (all 5 questions wrong) IS a hard violation."""
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {1: {"tool_use": 3.0}}
    g.baseline.per_suite_counts_by_tier = {1: {"tool_use": 5}}
    # 0/5 correct → 0.0, delta = -3.0
    verdict = g.check(_trial({"tool_use": 0.0}, {"tool_use": 5}))
    assert not verdict.passed
    assert "per_suite_regression" in verdict.categories
    assert "tool_use_regression_advisory" not in verdict.categories


def test_tool_use_severely_bad_regression_blocks(tmp_path):
    """A -2.4 drop on tool_use (only 1 of 5 correct) is NOT catastrophic, so advisory."""
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {1: {"tool_use": 3.0}}
    g.baseline.per_suite_counts_by_tier = {1: {"tool_use": 5}}
    # 1/5 correct → 0.6, delta = -2.4 (> -3.0, so still advisory)
    verdict = g.check(_trial({"tool_use": 0.6}, {"tool_use": 5}))
    assert verdict.passed
    assert "per_suite_regression" not in verdict.categories
    assert "tool_use_regression_advisory" in verdict.categories


def test_non_tool_use_suites_unaffected_by_tool_use_gate(tmp_path):
    """Non-tool_use suites still follow the standard binding rules."""
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {1: {"coder": 2.4}}
    g.baseline.per_suite_counts_by_tier = {1: {"coder": 50}}
    # Small drop at high n → hard violation (standard behavior preserved)
    verdict = g.check(_trial({"coder": 2.1}, {"coder": 50}))
    assert "per_suite_regression" in verdict.categories
    assert "tool_use_regression_advisory" not in verdict.categories


def test_tool_use_and_other_suite_regression_combined(tmp_path):
    """tool_use advisory + other-suite violation → verdict still fails (other suite)."""
    g = _gate(tmp_path)
    g.baseline.per_suite_quality_by_tier = {1: {"tool_use": 3.0, "coder": 2.4}}
    g.baseline.per_suite_counts_by_tier = {1: {"tool_use": 5, "coder": 50}}
    # tool_use 3.0 -> 1.8 is a TWO-flip drop (delta -1.2, past the -0.6 single-flip
    # threshold) so it still crosses and is treated as advisory (non-catastrophic). A
    # single flip would now be at-resolution noise post-B2 (see the single-flip test).
    verdict = g.check(
        _trial({"tool_use": 1.8, "coder": 2.0}, {"tool_use": 5, "coder": 50})
    )
    assert not verdict.passed  # coder regression is a hard violation
    assert "per_suite_regression" in verdict.categories  # from coder
    assert "tool_use_regression_advisory" in verdict.categories  # tool_use is advisory
