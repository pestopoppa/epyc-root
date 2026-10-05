#!/usr/bin/env python3
"""SEQ-B2 — the refutation counterfactual must be captured AT STOP TIME.

A sequential candidate stamped ``state="refuted"`` STOPS accumulating trials. A
future objective can rescore every trial that exists; it cannot recover trials
never run. So the two facts a re-run decision needs — WHICH axis refuted, and the
surviving margin on the OTHER axis at the moment of the stop — have to be written
by the gate at stop time or they do not exist. Before SEQ-B2 the journal carried
only the JOINT ``state``; the attribution lived exclusively post hoc in
``scripts/analysis/readjudicate_sequential_candidates.py``.

These tests pin:
  * the canonical per-axis predicate + margin (one definition, two consumers)
  * the deterministic both-axes attribution (quality first, both flagged)
  * the live gate write on each of the speed(rate)- and quality-refuted paths
  * backward compatibility: a legacy row with no ``refutation`` field still
    attributes, via reconstruction, and says so
  * live-vs-reconstructed AGREEMENT on a synthetic candidate — the property that
    makes the fallback trustworthy and would break first if the two definitions
    ever drifted apart
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import pytest
from safety_gate import EvalResult, SafetyGate  # type: ignore[import-not-found]

from src.autopilot_core.sequential_verdict import (
    DEFAULT_POLICY,
    SEQ_REFUTATION_SCHEMA,
    axis_refutation,
    refutation_record,
)

_SCRIPT = (
    REPO_ROOT / "scripts" / "analysis" / "readjudicate_sequential_candidates.py"
)


@pytest.fixture(scope="module")
def readjudicate():
    spec = importlib.util.spec_from_file_location("_readjudicate_seqb2", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _result() -> EvalResult:
    return EvalResult(
        tier=2,
        quality=2.5,
        speed=12.7,
        cost=0.1,
        reliability=0.99,
        per_suite_quality={"coder": 2.5},
        n_questions=2,
        question_results={"q1": True, "q2": True},
    )


def _gate(tmp_path) -> SafetyGate:
    return SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)


# ---------------------------------------------------------------------------
# canonical per-axis definition: predicate, threshold selection, margin sign
# ---------------------------------------------------------------------------
def test_axis_margin_is_negative_exactly_when_below_the_bar():
    pol = DEFAULT_POLICY
    # before the budget horizon the binding bar is futility_e
    early = axis_refutation("quality", 1.0, pol.budget - 1, pol)
    assert early.rule == "futility_e"
    assert early.threshold == pytest.approx(pol.futility_e)
    assert early.refuted is False
    assert early.margin == pytest.approx(1.0 - pol.futility_e)

    # at/past the horizon the budget clause is the binding bar
    late = axis_refutation("quality", 1.0, pol.budget, pol)
    assert late.rule == "budget_min_e"
    assert late.threshold == pytest.approx(pol.budget_min_e)
    assert late.refuted is True
    assert late.margin == pytest.approx(1.0 - pol.budget_min_e)
    assert late.margin < 0.0

    healthy = axis_refutation("rate", 11.55, 40, pol)
    assert healthy.refuted is False
    assert healthy.margin > 0.0


def test_axis_futility_is_inclusive_and_budget_is_strict():
    """The one boundary asymmetry, inherited from the policy, not invented."""
    pol = DEFAULT_POLICY
    at_futility = axis_refutation("quality", pol.futility_e, 1, pol)
    assert at_futility.refuted is True
    assert at_futility.margin == pytest.approx(0.0)

    at_budget = axis_refutation("quality", pol.budget_min_e, pol.budget, pol)
    assert at_budget.refuted is False
    assert at_budget.margin == pytest.approx(0.0)


def test_unmeasured_axis_never_refutes_and_has_no_margin():
    a = axis_refutation("rate", None, 40, DEFAULT_POLICY)
    assert a.refuted is False
    assert a.margin is None
    assert a.as_journal_dict()["wealth"] is None


# ---------------------------------------------------------------------------
# record shape + deterministic attribution
# ---------------------------------------------------------------------------
def test_record_attributes_quality_and_reports_the_other_axis_margin():
    rec = refutation_record(e_quality=1.0, e_rate=11.55, k=40)
    assert rec["schema"] == SEQ_REFUTATION_SCHEMA
    assert rec["refuting_axis"] == "quality"
    assert rec["refuting_margin"] == pytest.approx(1.0 - DEFAULT_POLICY.budget_min_e)
    assert rec["other_axis"] == "rate"
    assert rec["other_axis_margin"] == pytest.approx(11.55 - DEFAULT_POLICY.budget_min_e)
    assert rec["both_axes_refuted"] is False
    assert rec["n_trials_at_stop"] == 40
    assert rec["thresholds"]["budget_min_e"] == DEFAULT_POLICY.budget_min_e
    assert rec["captured_at"]


def test_record_attribution_is_symmetric_for_a_rate_stop():
    rec = refutation_record(e_quality=11.55, e_rate=1.11, k=40)
    assert rec["refuting_axis"] == "rate"
    assert rec["refuting_margin"] == pytest.approx(1.11 - DEFAULT_POLICY.budget_min_e)
    assert rec["other_axis"] == "quality"
    assert rec["other_axis_margin"] == pytest.approx(11.55 - DEFAULT_POLICY.budget_min_e)
    assert rec["both_axes_refuted"] is False


def test_both_axes_refuted_is_deterministic_quality_first_and_flagged():
    rec = refutation_record(e_quality=0.5, e_rate=0.9, k=40)
    assert rec["refuting_axis"] == "quality"
    assert rec["both_axes_refuted"] is True
    # neither axis's own verdict is lost to the precedence choice
    assert rec["axes"]["quality"]["refuted"] is True
    assert rec["axes"]["rate"]["refuted"] is True


def test_no_axis_refutes_yields_a_null_attribution():
    """The residual bucket the re-adjudicator reports as UNEXPLAINED."""
    rec = refutation_record(e_quality=11.55, e_rate=9.9, k=40)
    assert rec["refuting_axis"] is None
    assert rec["refuting_margin"] is None
    assert rec["other_axis"] is None
    assert rec["both_axes_refuted"] is False


# ---------------------------------------------------------------------------
# LIVE capture in the gate
# ---------------------------------------------------------------------------
def test_gate_records_quality_as_the_refuting_axis_with_the_rate_margin(tmp_path):
    """Quality wealth stuck below the budget bar while the RATE axis is healthy."""
    verdict = _gate(tmp_path).check(
        _result(),
        question_results={"q1": False},  # z=0 => quality wealth frozen at ~1.0
        baseline_profile={"q1": 0.0},
        task_rate=1.0,
        baseline_task_rate=0.5,
        prior_quality_obs=[(i, 0.0) for i in range(8)],
        prior_rate_obs=[(i, 1.2) for i in range(10)],
    )
    seq = verdict.seq
    assert seq["state"] == "refuted"
    rec = seq["refutation"]
    assert rec["source"] == "live"
    assert rec["refuting_axis"] == "quality"
    assert rec["refuting_margin"] < 0.0
    assert rec["other_axis"] == "rate"
    # the surviving margin on the OTHER axis — the number that only exists now
    assert rec["other_axis_margin"] > 0.0
    assert rec["other_axis_margin"] == pytest.approx(
        seq["E_rate_noninf"] - DEFAULT_POLICY.budget_min_e, abs=1e-5
    )
    assert rec["both_axes_refuted"] is False
    assert rec["n_trials_at_stop"] == seq["k"]


def test_gate_records_rate_as_the_refuting_axis_with_the_quality_margin(tmp_path):
    """Symmetric case: quality is strong, the SPEED (rate) axis is what stopped it."""
    verdict = _gate(tmp_path).check(
        _result(),
        question_results={"q1": True},
        baseline_profile={"q1": 0.0},
        task_rate=1.0,
        baseline_task_rate=0.5,
        prior_quality_obs=[(i, 1.2) for i in range(10)],
        prior_rate_obs=[(i, 0.0) for i in range(8)],
    )
    seq = verdict.seq
    assert seq["state"] == "refuted"
    rec = seq["refutation"]
    assert rec["source"] == "live"
    assert rec["refuting_axis"] == "rate"
    assert rec["refuting_margin"] < 0.0
    assert rec["other_axis"] == "quality"
    assert rec["other_axis_margin"] > 0.0
    assert rec["other_axis_margin"] == pytest.approx(
        seq["E_quality"] - DEFAULT_POLICY.budget_min_e, abs=1e-5
    )
    assert rec["both_axes_refuted"] is False


def test_gate_records_both_axes_when_both_refute(tmp_path):
    verdict = _gate(tmp_path).check(
        _result(),
        question_results={"q1": False},
        baseline_profile={"q1": 0.0},
        task_rate=1.0,
        baseline_task_rate=0.5,
        prior_quality_obs=[(i, 0.0) for i in range(8)],
        prior_rate_obs=[(i, 0.0) for i in range(8)],
    )
    rec = verdict.seq["refutation"]
    assert rec["both_axes_refuted"] is True
    assert rec["refuting_axis"] == "quality"


def test_gate_records_an_unmeasured_rate_axis_as_absent_not_refuted(tmp_path):
    """A skipped rate axis must not be attributed a refutation it never earned."""
    verdict = _gate(tmp_path).check(
        _result(),
        question_results={"q1": False},
        baseline_profile={"q1": 0.0},
        prior_quality_obs=[(i, 0.0) for i in range(8)],
    )
    rec = verdict.seq["refutation"]
    assert rec["refuting_axis"] == "quality"
    assert rec["other_axis"] == "rate"
    assert rec["other_axis_margin"] is None
    assert rec["axes"]["rate"]["refuted"] is False
    assert rec["axes"]["rate"]["wealth"] is None


def test_non_refuted_trials_carry_no_refutation_record(tmp_path):
    """Additive: the field appears only on the stop, so every other row is unchanged."""
    verdict = _gate(tmp_path).check(
        _result(),
        question_results={"q1": True},
        baseline_profile={"q1": 0.0},
        prior_quality_obs=[(i, 0.5) for i in range(3)],
    )
    assert verdict.seq["state"] == "accumulating"
    assert "refutation" not in verdict.seq


# ---------------------------------------------------------------------------
# readjudication: prefer live, fall back to reconstruction, say which
# ---------------------------------------------------------------------------
def test_readjudicator_prefers_the_live_record(readjudicate):
    live = refutation_record(e_quality=1.0, e_rate=11.55, k=40, source="live")
    row = {"E_quality": 1.0, "E_rate_noninf": 11.55, "k": 40, "refutation": live}
    rec, provenance = readjudicate.refutation_of(row, DEFAULT_POLICY)
    assert provenance == "live"
    assert rec is live


def test_legacy_row_without_the_field_still_readjudicates(readjudicate):
    """Every journal row written before SEQ-B2 must load and attribute unchanged."""
    row = {"E_quality": 11.55, "E_rate_noninf": 1.11, "k": 40}
    rec, provenance = readjudicate.refutation_of(row, DEFAULT_POLICY)
    assert provenance == "reconstructed"
    assert rec["source"] == "reconstructed"
    assert rec["refuting_axis"] == "rate"
    assert rec["other_axis_margin"] == pytest.approx(
        11.55 - DEFAULT_POLICY.budget_min_e
    )


def test_legacy_row_with_no_rate_axis_reconstructs_without_fabricating_one(
    readjudicate,
):
    row = {"E_quality": 1.0, "k": 40}
    rec, provenance = readjudicate.refutation_of(row, DEFAULT_POLICY)
    assert provenance == "reconstructed"
    assert rec["refuting_axis"] == "quality"
    assert rec["other_axis_margin"] is None


def test_readjudicator_axis_refuted_delegates_to_the_canonical_rule(readjudicate):
    """The script's predicate is now the same code the live writer uses."""
    for wealth, k in ((1.0, 40), (11.55, 40), (0.01, 1), (1.5, 3), (None, 40)):
        assert readjudicate.axis_refuted(wealth, k, DEFAULT_POLICY) is (
            axis_refutation("quality", wealth, k, DEFAULT_POLICY).refuted
        )


def test_live_and_reconstructed_agree_on_a_synthetic_candidate(tmp_path, readjudicate):
    """The agreement property that makes the fallback trustworthy.

    Run a synthetic candidate through the real gate to a rate-axis stop, then
    reconstruct the attribution from the SAME journal row with the live field
    stripped — the way every pre-SEQ-B2 row is read. Everything except the
    provenance/timestamp must match.
    """
    verdict = _gate(tmp_path).check(
        _result(),
        question_results={"q1": True},
        baseline_profile={"q1": 0.0},
        task_rate=1.0,
        baseline_task_rate=0.5,
        prior_quality_obs=[(i, 1.2) for i in range(10)],
        prior_rate_obs=[(i, 0.0) for i in range(8)],
    )
    seq = dict(verdict.seq)
    live = seq.pop("refutation")
    assert live["source"] == "live"

    rebuilt, provenance = readjudicate.refutation_of(seq, DEFAULT_POLICY)
    assert provenance == "reconstructed"

    volatile = {"source", "captured_at"}
    assert {k: v for k, v in live.items() if k not in volatile} == {
        k: v for k, v in rebuilt.items() if k not in volatile
    }
