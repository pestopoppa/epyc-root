"""Unit tests for autopilot.classify_learning_exclusion (intake-421 + Phase 5).

The helper consolidates the "should this trial be excluded from archive +
AP-22 memory?" decision so the run_loop wiring is testable without driving
the whole loop. Exogenous reloads and abandoned eval requests are measurement
corruption paths; mad_noise and related within-noise signals are benign
learning exclusions. Exogenous takes priority on the rare both-set path.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from autopilot import (  # type: ignore[import-not-found]
    BENIGN_LEARNING_EXCLUSIONS,
    classify_learning_exclusion,
    learning_exclusion_criticism,
)


def test_mad_noise_is_benign_so_not_journaled_as_bug_corrupted():
    """2026-06-04 policy correction: a trusted within-noise measurement is now
    Pareto-admissible (robust-median representative), so it must NOT be journaled as
    `bug_corrupted_by` — `mad_noise` joins BENIGN_LEARNING_EXCLUSIONS alongside
    `reproduction_confirmed`. classify still returns `mad_noise` to suppress AP-22
    learning (that gate keys on `learning_excluded_by`, not `bug_corrupted_by`).
    Genuine corruption (kills/reloads) stays NON-benign and keeps tagging."""
    assert "mad_noise" in BENIGN_LEARNING_EXCLUSIONS
    assert "reproduction_confirmed" in BENIGN_LEARNING_EXCLUSIONS
    assert "exogenous_operator_reload" not in BENIGN_LEARNING_EXCLUSIONS
    by, _, _ = classify_learning_exclusion(
        _FakeVerdict(categories=["mad_noise"]), _FakeEvalResult()
    )
    assert by == "mad_noise", "still flagged for AP-22 suppression"


@dataclass
class _FakeVerdict:
    """Minimal SafetyVerdict stand-in — only `.categories` is read."""

    categories: list[str] = field(default_factory=list)
    passed: bool = True


@dataclass
class _FakeEvalResult:
    """Minimal EvalResult stand-in for the fields classify_learning_exclusion reads."""

    n_exogenous_unrecovered: int = 0
    exogenous_question_ids: list[str] = field(default_factory=list)
    n_questions: int = 0
    oracle_adequacy: dict = field(default_factory=dict)
    bug_corrupted_by: str = ""
    bug_corrupted_reason: str = ""
    details: dict = field(default_factory=dict)


def test_no_signals_returns_empty():
    by, reason, def_cat = classify_learning_exclusion(_FakeVerdict(), _FakeEvalResult())
    assert by == ""
    assert reason == ""
    assert def_cat == ""


def test_eval_result_bug_corruption_takes_priority():
    result = _FakeEvalResult(
        bug_corrupted_by="structural_flag_revert_failure",
        bug_corrupted_reason="connection refused while restoring plan_review=false",
        n_exogenous_unrecovered=2,
        n_questions=10,
    )

    by, reason, def_cat = classify_learning_exclusion(
        _FakeVerdict(categories=["mad_noise"]),
        result,
    )

    assert by == "structural_flag_revert_failure"
    assert "connection refused" in reason
    assert def_cat == "structural_flag_revert_failure"


def test_report_only_control_attestation_does_not_exclude_learning():
    result = _FakeEvalResult(
        oracle_adequacy={
            "control_attestation": {
                "status": "failed",
                "observe_only": True,
            }
        }
    )

    by, reason, def_cat = classify_learning_exclusion(_FakeVerdict(), result)

    assert by == ""
    assert reason == ""
    assert def_cat == ""


def test_mad_noise_only_marks_mad():
    v = _FakeVerdict(categories=["mad_noise"])
    by, reason, def_cat = classify_learning_exclusion(v, _FakeEvalResult())
    assert by == "mad_noise"
    assert "MAD noise band" in reason
    assert def_cat == "mad_noise"


def test_learning_exclusion_criticism_blocks_keep_signal():
    criticism = learning_exclusion_criticism(
        "mad_noise",
        "quality improvement was within MAD noise band",
    )

    text = criticism.as_text()
    assert criticism.keep_or_revert == "excluded"
    assert "Decision: excluded" in text
    assert "Do not treat this outcome as a keep" in text
    assert "continue exploring this surface" not in text


def test_reproduction_confirmed_is_distinct_benign_exclusion():
    """mad_noise + reproduction_confirmed → benign convergence reason, NOT mad_noise."""
    v = _FakeVerdict(categories=["mad_noise", "reproduction_confirmed"])
    by, reason, def_cat = classify_learning_exclusion(v, _FakeEvalResult())
    assert by == "reproduction_confirmed"
    assert def_cat == "reproduction_confirmed"
    assert "convergence" in reason.lower()
    assert "not corrupted" in reason.lower()


def test_reproduction_confirmed_criticism_signals_convergence_not_failure():
    """Criticism for a reproduction must NOT demand another trial or imply noise."""
    criticism = learning_exclusion_criticism(
        "reproduction_confirmed",
        "within-noise reproduction of an already-established above-baseline config",
    )
    text = criticism.as_text().lower()
    assert criticism.what_went_wrong == "", "a confirmation is not a failure"
    assert "confirmed" in text or "converged" in text
    assert "explore a different surface or idle" in text
    # Must not tell the planner to re-run / treat as noisy.
    assert "require a clean, non-excluded metric trial" not in text


def test_exogenous_unrecovered_marks_exo():
    r = _FakeEvalResult(
        n_exogenous_unrecovered=2,
        exogenous_question_ids=["q1", "q2"],
        n_questions=10,
    )
    by, reason, def_cat = classify_learning_exclusion(_FakeVerdict(), r)
    assert by == "exogenous_operator_reload"
    assert "2/10 questions" in reason
    assert "q1" in reason  # sample ids present
    assert def_cat == "exogenous_reload"


def test_exo_priority_over_mad_when_both_somehow_fire():
    """Defensive: in production exo bypasses gate.check so categories is empty,
    but the helper must still encode the priority order if both are set."""
    v = _FakeVerdict(categories=["mad_noise"])
    r = _FakeEvalResult(n_exogenous_unrecovered=1, n_questions=5)
    by, _, def_cat = classify_learning_exclusion(v, r)
    assert by == "exogenous_operator_reload"
    assert def_cat == "exogenous_reload"


def test_exo_priority_over_abandoned_eval_requests_when_both_somehow_fire():
    r = _FakeEvalResult(
        n_exogenous_unrecovered=1,
        n_questions=5,
        details={
            "eval_contaminated_by_abandoned_requests": True,
            "eval_orphan_contamination_count": 2,
        },
    )

    by, reason, def_cat = classify_learning_exclusion(_FakeVerdict(), r)

    assert by == "exogenous_operator_reload"
    assert "remained unrecovered" in reason
    assert def_cat == "exogenous_reload"


def test_abandoned_eval_requests_mark_corrupted_learning_exclusion():
    r = _FakeEvalResult(
        n_questions=3,
        details={
            "eval_contaminated_by_abandoned_requests": True,
            "eval_orphan_contamination_count": 1,
        },
    )

    by, reason, def_cat = classify_learning_exclusion(_FakeVerdict(), r)

    assert by == "eval_abandoned_requests"
    assert "1/3 eval request(s)" in reason
    assert "server-side" in reason
    assert def_cat == "eval_abandoned_requests"
    assert "eval_abandoned_requests" not in BENIGN_LEARNING_EXCLUSIONS


def test_exo_n_questions_fallback_to_question_ids_len():
    """When n_questions=0 but exogenous_question_ids has entries, the reason
    string should still produce a sensible denominator."""
    r = _FakeEvalResult(
        n_exogenous_unrecovered=1,
        exogenous_question_ids=["q1", "q2", "q3"],
        n_questions=0,
    )
    _, reason, _ = classify_learning_exclusion(_FakeVerdict(), r)
    assert "1/3 questions" in reason


def test_recovered_only_exo_is_not_excluded():
    """Trials that hit a reload but recovered via retry are sound — they
    carry audit metadata in eval_details but must NOT be excluded."""
    r = _FakeEvalResult(
        n_exogenous_unrecovered=0,  # nothing unrecovered
        exogenous_question_ids=["q1"],  # had retries
        n_questions=10,
    )
    by, _, _ = classify_learning_exclusion(_FakeVerdict(), r)
    assert by == ""


def test_missing_attributes_safe():
    """Helper must not crash if the verdict / eval_result are missing fields
    (e.g. lightweight mocks in other tests). Treat as no exclusion."""

    class _Empty: ...

    by, reason, def_cat = classify_learning_exclusion(_Empty(), _Empty())
    assert by == "" and reason == "" and def_cat == ""
