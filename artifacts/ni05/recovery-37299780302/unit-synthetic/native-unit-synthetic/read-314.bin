"""EV-14d: a short draw is recorded as short, and no consumer scores it as complete.

`EvalTower._eval_batch` returns `[r for r in results if r is not None]`, so a batch
can legitimately come back SHORT (an abandoned lane, a cancelled future, the serial
wall-budget break). Defining `n_questions = len(results)` renamed that shortfall as
the denominator: 40 of 50 scored was indistinguishable from a complete draw of 40.
These tests pin the requested/completed split, the fail-closed completeness
predicate, the per-role → top-level fold, and the window-runner gate that now
refuses an arm whose recorded counts disagree.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "autopilot"))
sys.path.insert(0, str(ROOT / "scripts" / "benchmark"))

from eval_tower import (  # noqa: E402
    QUESTION_COUNT_FIELDS,
    draw_is_complete,
    draw_shortfall,
    fold_role_completeness,
    question_count_fields,
)


# --- counts -------------------------------------------------------------------


def test_a_complete_draw_records_requested_equals_completed():
    fields = question_count_fields(50, 50)
    assert fields["n_questions"] == 50
    assert fields["n_questions_requested"] == 50
    assert fields["n_questions_completed"] == 50
    assert fields["n_questions_missing"] == 0
    assert fields["completeness_ratio"] == 1.0
    assert fields["draw_complete"] is True
    assert set(fields) == set(QUESTION_COUNT_FIELDS)


def test_a_short_draw_keeps_the_requested_count_as_the_denominator():
    fields = question_count_fields(50, 40)
    # The pre-fix defect: n_questions was 40, so the shortfall vanished.
    assert fields["n_questions"] == 50
    assert fields["n_questions_completed"] == 40
    assert fields["n_questions_missing"] == 10
    assert fields["completeness_ratio"] == 0.8
    assert fields["draw_complete"] is False


def test_a_zero_request_is_never_complete():
    assert question_count_fields(0, 0)["draw_complete"] is False


# --- predicates ---------------------------------------------------------------


def test_draw_is_complete_is_fail_closed_on_a_payload_with_no_counts():
    # Absence of the fields is not evidence of completeness.
    assert draw_is_complete({}) is False
    assert draw_is_complete({"n_questions": 50}) is False
    assert draw_is_complete(None) is False


def test_draw_is_complete_only_on_a_recorded_met_request():
    assert draw_is_complete(question_count_fields(50, 50)) is True
    assert draw_is_complete(question_count_fields(50, 49)) is False


def test_draw_shortfall_stays_silent_on_legacy_and_complete_payloads():
    assert draw_shortfall({}) is None
    assert draw_shortfall({"n_questions": 40}) is None
    assert draw_shortfall(question_count_fields(50, 50)) is None
    assert draw_shortfall(question_count_fields(50, 40)) == (50, 40)


def test_fold_names_the_incomplete_roles():
    per_role = {
        "worker_math": question_count_fields(50, 50),
        "verifier": question_count_fields(50, 41),
    }
    fold = fold_role_completeness(per_role)
    assert fold["draw_complete"] is False
    assert fold["incomplete_roles"] == ["verifier"]

    ok = fold_role_completeness({"worker_math": question_count_fields(50, 50)})
    assert ok == {"draw_complete": True, "incomplete_roles": []}


# --- the gate/fold consumer ---------------------------------------------------


def _window_runner():
    import eval_batch_serving_evaltower_window as mod

    return mod


def test_window_runner_blocks_a_verifier_mode_report_whose_role_drew_short():
    mod = _window_runner()
    result = {
        "mode": "math_rebaseline",
        "per_role": {
            "worker_math": {
                **question_count_fields(1819, 1400),
                "n_scored": 1400,
            }
        },
        **fold_role_completeness(
            {"worker_math": question_count_fields(1819, 1400)}
        ),
    }
    blocker = mod._verifier_result_blocker(result, expected_n=1819)
    assert blocker is not None
    assert "draw incomplete" in blocker
    assert "1400/1819" in blocker


def test_window_runner_admits_a_complete_verifier_mode_report():
    mod = _window_runner()
    counts = question_count_fields(1819, 1819)
    result = {
        "mode": "math_rebaseline",
        "per_role": {"worker_math": {**counts, "n_scored": 1819}},
        **fold_role_completeness({"worker_math": counts}),
    }
    assert mod._verifier_result_blocker(result, expected_n=1819) is None


def test_window_runner_still_admits_a_pre_ev14d_payload():
    """Backward compatibility: old artifacts carry no counts and must not be failed here."""
    mod = _window_runner()
    result = {"n_questions": 1819, "n_scored": 1819}
    assert mod._verifier_result_blocker(result, expected_n=1819) is None


def test_window_runner_blocks_an_arm_whose_metrics_record_a_shortfall():
    mod = _window_runner()
    arm = {
        "ok": True,
        "metrics": {
            **question_count_fields(50, 40),
            "n_scored": 40,
            "reliability": 1.0,
        },
    }
    blocker = mod._arm_decision_blocker("cand", arm, expected_n=50)
    assert blocker is not None
    assert "draw incomplete" in blocker


def test_window_runner_admits_an_arm_whose_draw_is_complete():
    mod = _window_runner()
    arm = {
        "ok": True,
        "metrics": {
            **question_count_fields(50, 50),
            "n_scored": 50,
            "reliability": 1.0,
        },
    }
    assert mod._arm_decision_blocker("cand", arm, expected_n=50) is None


# --- the real call site -------------------------------------------------------


def _subset_report(monkeypatch, *, requested: int, returned: int) -> dict:
    """Drive the real `eval_question_subset` writer with a stubbed batch.

    Nothing here dispatches: `_eval_batch` is replaced with a function that
    returns FEWER results than it was handed, which is exactly the hole
    `[r for r in results if r is not None]` can leave.
    """
    import eval_tower as et

    questions = [
        {"id": f"q{i}", "prompt": "p", "expected": "e", "suite": "math"}
        for i in range(requested)
    ]

    class _Adapter:
        def extract_all(self):
            return [dict(q) for q in questions]

    tower = et.EvalTower.__new__(et.EvalTower)
    tower.timeout = 1
    monkeypatch.setattr(et.EvalTower, "_normalize_roles", lambda self, roles: ["worker_math"])
    monkeypatch.setattr(et.EvalTower, "_load_dataset_adapter", lambda self, suite: _Adapter())
    monkeypatch.setattr(et.EvalTower, "_with_forced_role", lambda self, q, role: dict(q))

    def _short_batch(self, role_qs, client, log_every=None, label=""):
        return [
            et.QuestionResult(
                question_id=q["id"],
                suite="math",
                prompt="p",
                expected="e",
                answer="e",
                correct=True,
            )
            for q in role_qs[:returned]
        ]

    monkeypatch.setattr(et.EvalTower, "_eval_batch", _short_batch)

    class _Agg:
        quality = 1.0
        reliability = 1.0
        ece = None
        auroc = None
        details = {"confidence_is_real": False, "confidence_source_counts": {}}

    monkeypatch.setattr(et.EvalTower, "_aggregate", lambda self, results, tier=2: _Agg())

    return tower.eval_question_subset(
        suite="math",
        question_ids=[q["id"] for q in questions],
        roles="worker_math",
    )


def test_real_call_site_marks_a_short_draw_incomplete(monkeypatch):
    report = _subset_report(monkeypatch, requested=10, returned=7)
    role = report["per_role"]["worker_math"]
    assert role["n_questions"] == 10  # requested, not the 7 that came back
    assert role["n_questions_requested"] == 10
    assert role["n_questions_completed"] == 7
    assert role["n_questions_missing"] == 3
    assert role["draw_complete"] is False
    assert draw_is_complete(role) is False
    assert report["draw_complete"] is False
    assert report["incomplete_roles"] == ["worker_math"]
    # ...and the gate consumer refuses it.
    assert _window_runner()._verifier_result_blocker(report, expected_n=10) is not None


def test_real_call_site_marks_a_full_draw_complete(monkeypatch):
    report = _subset_report(monkeypatch, requested=10, returned=10)
    role = report["per_role"]["worker_math"]
    assert (role["n_questions_requested"], role["n_questions_completed"]) == (10, 10)
    assert role["draw_complete"] is True
    assert report["draw_complete"] is True
    assert report["incomplete_roles"] == []
    assert _window_runner()._verifier_result_blocker(report, expected_n=10) is None
