"""LEDGER-W4: anytime-valid sequential e-process verdict wiring in the AUTOPILOT
safety_gate (scripts/autopilot/safety_gate.py — the module the autopilot imports,
NOT src/safety_gate.py).

The wiring is DEFAULT-OFF: with the AUTOPILOT_SEQ_VERDICT flag unset (or with the
per-question inputs absent) check()/update_baseline behave byte-identically to the
pre-W4 MAD-only gate. These tests pin both the default-off invariance and the
behaviour of the seq path when the operator deliberately enables it. Deploy remains
evidence-gated (flip-rate >= 30% over ~120 trusted vectors) — this only lands the
mechanism, tested.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import pytest
from safety_gate import EvalResult, SafetyGate  # type: ignore[import-not-found]

from src.autopilot_core.learning_exclusions import (
    BENIGN_LEARNING_EXCLUSIONS,
    NON_CORRUPT_LEARNING_EXCLUSIONS,
    classify_learning_exclusion,
)
from src.autopilot_core.authority_consent import (
    SEQ_P0_2_BRIDGE_CONSENT,
    SEQ_P0_2_BRIDGE_ENV,
    SEQ_P0_2_BRIDGE_MODE,
)


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------
def _improvement_result(quality: float = 2.5, speed: float = 12.7) -> EvalResult:
    """An EvalResult that lands in check()'s improvement branch (q >> baseline 1.16)
    and clears the quality floor + throughput floor (default frontdoor_speed 12.7)."""
    return EvalResult(
        tier=2,
        quality=quality,
        speed=speed,
        cost=0.1,
        reliability=0.99,
        per_suite_quality={"coder": quality},
        n_questions=2,
        question_results={"q1": True, "q2": True},
    )


def _promotion_result(speed_metric_mode: str = "aggregate_batch_tps") -> EvalResult:
    return EvalResult(
        tier=2,
        quality=2.9,
        speed=99.0,
        cost=0.1,
        reliability=0.99,
        per_suite_quality={"coder": 2.9},
        n_questions=50,
        speed_metric_mode=speed_metric_mode,
    )


class _Verdict:
    def __init__(self, categories, passed=True):
        self.categories = categories
        self.passed = passed


class _Eval:
    n_exogenous_unrecovered = 0


# ---------------------------------------------------------------------------
# default-off invariance — the load-bearing safety property
# ---------------------------------------------------------------------------
def test_flag_off_by_default(tmp_path):
    assert SafetyGate(baseline_path=tmp_path / "absent.yaml").use_sequential is False


def test_flag_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_SEQ_VERDICT", "1")
    assert SafetyGate(baseline_path=tmp_path / "absent.yaml").use_sequential is True
    monkeypatch.setenv("AUTOPILOT_SEQ_VERDICT", "off")
    assert SafetyGate(baseline_path=tmp_path / "absent.yaml").use_sequential is False


def test_explicit_arg_overrides_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_SEQ_VERDICT", "1")
    assert SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=False).use_sequential is False


def test_check_default_off_is_inert(tmp_path):
    """Flag off: even when seq inputs are supplied, the seq path never runs — no
    seq_* category, verdict.seq stays None, legacy MAD path is in force."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")  # flag off
    verdict = g.check(
        _improvement_result(),
        question_results={"q1": True},
        baseline_profile={"q1": 0.0},
        prior_quality_obs=[(i, 1.2) for i in range(10)],
    )
    assert verdict.seq is None
    assert not any(c.startswith("seq_") for c in verdict.categories)


def test_check_flag_on_but_no_inputs_is_inert(tmp_path):
    """Flag on but the caller passes no per-question inputs (today's autopilot call
    site): the seq path is skipped and the MAD filter runs as before."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    verdict = g.check(_improvement_result())
    assert verdict.seq is None
    assert not any(c.startswith("seq_") for c in verdict.categories)


def test_seq_aware_call_can_upgrade_cached_legacy_pass_without_side_effects(tmp_path):
    """Action handlers run an early legacy gate check before the central loop threads
    W4 per-question evidence. The central call must be able to replace that cached
    pass with a seq-aware verdict without appending to the MAD history twice."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    result = _improvement_result()

    legacy = g.check(result)
    assert legacy.seq is None
    assert result.gate_verdict is legacy
    assert g.quality_history_for_tier(2) == [pytest.approx(result.quality)]

    upgraded = g.check(
        result,
        question_results={"q1": True},
        baseline_profile={"q1": 0.0},
        task_rate=1.0,
        baseline_task_rate=0.5,
        prior_quality_obs=[(i, 1.2) for i in range(10)],
        prior_rate_obs=[(i, 1.2) for i in range(10)],
    )

    assert upgraded is result.gate_verdict
    assert upgraded is not legacy
    assert upgraded.seq is not None
    assert upgraded.seq["state"] == "confirmed"
    assert "seq_confirmed" in upgraded.categories
    assert g.quality_history_for_tier(2) == [pytest.approx(result.quality)]


# ---------------------------------------------------------------------------
# seq path through check() — the three joint states
# ---------------------------------------------------------------------------
def test_check_seq_accumulating(tmp_path):
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    verdict = g.check(
        _improvement_result(),
        question_results={"q1": True},
        baseline_profile={"q1": 0.0},
        prior_quality_obs=[(i, 0.5) for i in range(3)],
    )
    assert verdict.seq is not None
    assert verdict.seq["state"] == "accumulating"
    assert verdict.seq["confirmed"] is False
    assert "seq_accumulating" in verdict.categories
    # no rate evidence => cannot confirm on quality alone
    assert verdict.seq.get("E_rate_noninf") is None


def test_check_seq_confirmed_requires_both_axes(tmp_path):
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    verdict = g.check(
        _improvement_result(),
        question_results={"q1": True},
        baseline_profile={"q1": 0.0},
        task_rate=1.0,
        baseline_task_rate=0.5,
        prior_quality_obs=[(i, 1.2) for i in range(10)],
        prior_rate_obs=[(i, 1.2) for i in range(10)],
    )
    assert verdict.seq["state"] == "confirmed"
    assert verdict.seq["confirmed"] is True
    assert verdict.seq["E_quality"] >= 20.0
    assert verdict.seq["E_rate_noninf"] >= 20.0
    assert verdict.seq["r_eff"] == 1
    assert "seq_confirmed" in verdict.categories


def test_check_seq_confirmed_blocked_without_rate(tmp_path):
    """Strong quality evidence but NO rate axis must stay accumulating — quality alone
    can never ratchet the baseline (01c §3 joint rule)."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    verdict = g.check(
        _improvement_result(),
        question_results={"q1": True},
        baseline_profile={"q1": 0.0},
        prior_quality_obs=[(i, 1.2) for i in range(10)],
    )
    assert verdict.seq["E_quality"] >= 20.0
    assert verdict.seq["confirmed"] is False
    assert verdict.seq["state"] == "accumulating"


def test_check_seq_p0_2_bridge_confirms_quality_with_rate_advisory(
    tmp_path,
    monkeypatch,
):
    grant = tmp_path / "consent.json"
    grant.write_text(json.dumps({SEQ_P0_2_BRIDGE_CONSENT: "allow"}), encoding="utf-8")
    monkeypatch.setenv("AUTOPILOT_AUTHORITY_CONSENT_PATH", str(grant))
    monkeypatch.setenv(SEQ_P0_2_BRIDGE_ENV, "1")
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)

    verdict = g.check(
        _improvement_result(),
        question_results={"q1": True},
        baseline_profile={"q1": 0.0},
        prior_quality_obs=[(i, 1.2) for i in range(10)],
    )

    assert verdict.seq["E_quality"] >= 20.0
    assert verdict.seq.get("E_rate_noninf") is None
    assert verdict.seq["confirmed"] is True
    assert verdict.seq["state"] == "confirmed"
    assert verdict.seq["rate_axis_mode"] == SEQ_P0_2_BRIDGE_MODE
    assert verdict.seq["rate_axis_binding"] is False
    assert verdict.seq["p0_2_bridge"]["enabled"] is True
    assert "seq_confirmed" in verdict.categories


def test_check_seq_refuted_via_budget(tmp_path):
    """Wealth stuck below budget_min_e after the budget horizon => refuted."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    verdict = g.check(
        _improvement_result(),
        question_results={"q1": False},  # z=0 (no qid qualifies vs p_base=0)
        baseline_profile={"q1": 0.0},
        prior_quality_obs=[(i, 0.0) for i in range(8)],
    )
    assert verdict.seq["state"] == "refuted"
    assert verdict.seq["confirmed"] is False
    assert "seq_refuted" in verdict.categories


def test_seq_path_never_adds_a_violation(tmp_path):
    """The seq verdict is advisory at the gate; promotion is gated downstream in
    update_baseline. A refuted seq verdict must NOT by itself fail the gate."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    verdict = g.check(
        _improvement_result(),
        question_results={"q1": False},
        baseline_profile={"q1": 0.0},
        prior_quality_obs=[(i, 0.0) for i in range(8)],
    )
    assert verdict.passed is True


def test_seq_shadow_journaled_for_failed_regression(tmp_path):
    """Failed trials still need seq shadow rows for W4 readiness denominators.
    The seq tag must remain advisory and must not launder the failed verdict."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    # SG-3 (audit B3a): the regression gate now uses the STRICT same-tier baseline; seed a
    # T2 baseline so the crater (q=0.2 vs 1.16) still trips the regression leg (the old
    # lenient fallback to the top-level legacy quality is gone).
    g.baseline.baselines_by_tier[2] = 1.16
    verdict = g.check(
        _improvement_result(quality=0.2),
        question_results={"q1": False},
        baseline_profile={"q1": 0.0},
        prior_quality_obs=[(i, 0.0) for i in range(8)],
    )

    assert verdict.seq is not None
    assert verdict.seq["state"] == "refuted"
    assert "seq_refuted" in verdict.categories
    assert "quality_floor" in verdict.categories
    assert "regression" in verdict.categories
    assert verdict.categories[0] == "quality_floor"
    assert verdict.passed is False
    by, _, _ = classify_learning_exclusion(verdict, _Eval())
    assert by != "seq_refuted"


# ---------------------------------------------------------------------------
# update_baseline confirmed-gate (anti-ratchet)
# ---------------------------------------------------------------------------
def _eligible_bootstrap(g, monkeypatch):
    monkeypatch.setattr(g, "_baseline_eligible", lambda result: (True, "test-eligible", {"x": 1}))
    monkeypatch.setattr(SafetyGate, "_archive_best_quality", staticmethod(lambda tier=None: None))


def test_update_baseline_blocked_when_seq_not_confirmed(tmp_path, monkeypatch):
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    _eligible_bootstrap(g, monkeypatch)
    before = g.baseline.quality_for_tier(2)
    res = g.update_baseline(_promotion_result(), seq_confirmed=False)
    assert res.updated is False
    assert "not confirmed" in res.reason
    assert g.baseline.quality_for_tier(2) == before, "non-confirmed candidate must not ratchet baseline"


def test_update_baseline_allowed_when_seq_confirmed(tmp_path, monkeypatch):
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    _eligible_bootstrap(g, monkeypatch)
    res = g.update_baseline(_promotion_result(), seq_confirmed=True)
    assert res.updated is True
    assert g.baseline.quality_for_tier(2, strict=True) == pytest.approx(2.9)


def test_update_baseline_gate_inert_when_flag_off(tmp_path, monkeypatch):
    """Flag off: seq_confirmed is ignored, legacy promotion path is unchanged."""
    g = SafetyGate(baseline_path=tmp_path / "absent.yaml")  # flag off
    _eligible_bootstrap(g, monkeypatch)
    res = g.update_baseline(_promotion_result(), seq_confirmed=False)
    assert res.updated is True, "with the flag off, seq_confirmed=False must NOT block promotion"


# ---------------------------------------------------------------------------
# learning_exclusions seq mapping (01c §3 part 3)
# ---------------------------------------------------------------------------
def test_learning_exclusion_seq_accumulating_is_benign():
    assert "seq_accumulating" in BENIGN_LEARNING_EXCLUSIONS
    by, reason, override = classify_learning_exclusion(_Verdict(["seq_accumulating"]), _Eval())
    assert by == "seq_accumulating"
    assert override == "seq_accumulating"
    assert "accumulating" in reason


def test_learning_exclusion_seq_accumulating_not_laundered_on_fail():
    """A within-noise seq reading must NOT launder a FAILED verdict — falls through
    to the normal failed-trial path (mirrors the mad_noise guard)."""
    by, _, _ = classify_learning_exclusion(_Verdict(["seq_accumulating"], passed=False), _Eval())
    assert by == ""


def test_learning_exclusion_seq_confirmed_includes_normally():
    by, _, _ = classify_learning_exclusion(_Verdict(["seq_confirmed"]), _Eval())
    assert by == "", "a confirmed improvement is learned from, not excluded"


def test_learning_exclusion_seq_refuted_is_non_corrupt_negative_evidence():
    assert "seq_refuted" not in BENIGN_LEARNING_EXCLUSIONS
    assert "seq_refuted" in NON_CORRUPT_LEARNING_EXCLUSIONS
    by, reason, override = classify_learning_exclusion(_Verdict(["seq_refuted"]), _Eval())
    assert by == "seq_refuted"
    assert override == "seq_refuted"
    assert "refuted" in reason
    assert "strategy distillation" in reason


def test_learning_exclusion_seq_refuted_preserves_primary_failed_verdict():
    by, _, _ = classify_learning_exclusion(_Verdict(["quality_floor", "seq_refuted"], passed=False), _Eval())
    assert by == ""


def test_learning_exclusion_seq_stale_reference_is_benign():
    assert "seq_stale_reference" in BENIGN_LEARNING_EXCLUSIONS
    by, reason, override = classify_learning_exclusion(_Verdict(["seq_stale_reference"]), _Eval())
    assert by == "seq_stale_reference"
    assert override == "seq_stale_reference"
    assert "reference profile is stale" in reason


def test_learning_exclusion_seq_stale_reference_takes_precedence():
    by, reason, override = classify_learning_exclusion(
        _Verdict(["seq_accumulating", "seq_stale_reference"]),
        _Eval(),
    )
    assert by == "seq_stale_reference"
    assert override == "seq_stale_reference"
    assert "reference profile is stale" in reason


def test_learning_exclusion_seq_stale_reference_not_laundered_on_fail():
    by, _, _ = classify_learning_exclusion(_Verdict(["seq_stale_reference"], passed=False), _Eval())
    assert by == ""
