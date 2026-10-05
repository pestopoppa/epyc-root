"""An `infra_failed` row must not enter a paired test as a WRONG ANSWER.

`eval_tower._compact_question_result` has stamped `disposition` onto every
journal row since the 2026-08-03 incident, and `test_infra_failed_disposition.py`
proves the stamp survives into the row. But FOUR downstream coercers read only
`correct` and dropped the stamp on the floor:

  * `sequential_verdict._coerce_question_results` -> a fabricated `x = 0.0`
    observation in an anytime-valid e-process,
  * `autopilot._question_outcome_map`             -> poisons the baseline profile
    every later observation is centred against,
  * `autopilot._question_outcome_vector`          -> feeds `mcnemar_from_vectors`
    directly; THE live McNemar leak,
  * `eval_tower._arm_outcome_vector`              -> `QuestionOutcome` has no
    disposition field, so this is where the stamp died.

Excluded rows shrink the denominator; they are never clamped to a value, and
never converted into a correct answer.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for extra in (REPO_ROOT, REPO_ROOT / "scripts" / "autopilot", REPO_ROOT / "scripts" / "benchmark"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from src.autopilot_core.measurement_guards import (  # noqa: E402
    DISPOSITION_INFRA_FAILED,
    DISPOSITION_SCORED,
    DISPOSITION_SCORING_FAILED,
    DISPOSITION_TASK_FAILED,
    is_quality_admissible,
)
from src.autopilot_core.sequential_verdict import (  # noqa: E402
    _coerce_question_results,
    excluded_question_results,
    quality_trial_statistic,
)


def _row(qid, correct, disposition=None):
    row = {"qid": qid, "correct": correct}
    if disposition is not None:
        row["disposition"] = disposition
    return row


# --------------------------------------------------------------------------- #
# The one shared predicate
# --------------------------------------------------------------------------- #
def test_only_the_two_non_quality_dispositions_are_excluded():
    assert is_quality_admissible(DISPOSITION_SCORED) is True
    # A genuine task failure IS quality evidence: learning that a role gets
    # things wrong is the signal this subsystem exists to collect.
    assert is_quality_admissible(DISPOSITION_TASK_FAILED) is True
    assert is_quality_admissible(DISPOSITION_INFRA_FAILED) is False
    assert is_quality_admissible(DISPOSITION_SCORING_FAILED) is False


def test_absent_disposition_is_admissible():
    """Rows written before the taxonomy existed are `scored` by default;
    flipping that would silently empty every historical denominator."""
    assert is_quality_admissible(None) is True
    assert is_quality_admissible("") is True


# --------------------------------------------------------------------------- #
# The e-process
# --------------------------------------------------------------------------- #
def test_infra_row_does_not_become_a_negative_e_process_observation():
    rows = [
        _row("q1", True, DISPOSITION_SCORED),
        _row("q2", False, DISPOSITION_INFRA_FAILED),
    ]
    profile = {"q1": 0.5, "q2": 0.5}

    stat = quality_trial_statistic(rows, profile)
    assert stat.qids == ("q1",), "the infra row must not enter the statistic"
    assert stat.r_eff == 1

    # Mutation guard: remove the signal under test — the disposition — and the
    # SAME rows produce the old, contaminated statistic. Without this the
    # assertion above could hold for a coercer that dropped q2 for any reason.
    unstamped = [dict(r, disposition=DISPOSITION_SCORED) for r in rows]
    contaminated = quality_trial_statistic(unstamped, profile)
    assert contaminated.r_eff == 2
    assert contaminated.s < stat.s, (
        "the infra row used to drag the statistic down; that is the defect"
    )


def test_exclusions_are_counted_not_silently_absorbed():
    rows = [
        _row("q1", True, DISPOSITION_SCORED),
        _row("q2", False, DISPOSITION_INFRA_FAILED),
        _row("q3", False, DISPOSITION_SCORING_FAILED),
        _row("q4", False, DISPOSITION_TASK_FAILED),
    ]
    assert set(_coerce_question_results(rows)) == {"q1", "q4"}
    assert excluded_question_results(rows) == {
        DISPOSITION_INFRA_FAILED: 1,
        DISPOSITION_SCORING_FAILED: 1,
    }


# --------------------------------------------------------------------------- #
# The McNemar leak
# --------------------------------------------------------------------------- #
def test_infra_rows_leave_the_mcnemar_universe():
    from autopilot import _question_outcome_map, _question_outcome_vector

    rows = [
        _row("q1", True, DISPOSITION_SCORED),
        _row("q2", False, DISPOSITION_INFRA_FAILED),
    ]
    assert set(_question_outcome_map(rows)) == {"q1"}

    vector = _question_outcome_vector(rows, trial_id=3)
    assert set(vector) == {"q1"}
    assert vector["q1"].correct is True

    # Mutation guard: a scored-but-wrong row still enters as a wrong answer.
    wrong = [_row("q1", False, DISPOSITION_SCORED)]
    assert _question_outcome_vector(wrong, trial_id=3)["q1"].correct is False


def test_eval_tower_arm_vector_excludes_infra_rows():
    from eval_tower import _arm_outcome_vector

    vector = _arm_outcome_vector({
        "q1": {"correct": True, "suite": "s", "disposition": DISPOSITION_SCORED},
        "q2": {"correct": False, "suite": "s", "disposition": DISPOSITION_INFRA_FAILED},
        "q3": {"correct": False, "suite": "s"},
        "q4": True,
    })
    assert set(vector) == {"q1", "q3", "q4"}, (
        "only the non-quality disposition is excluded; a bare bool and an "
        "unstamped row carry no disposition and stay in"
    )
    assert vector["q3"].correct is False


def test_arm_vector_pair_loses_the_infra_qid_rather_than_scoring_it_wrong():
    from eval_tower import _arm_outcome_vector
    from paired_stats import mcnemar_from_vectors

    baseline = _arm_outcome_vector({
        "q1": {"correct": True, "disposition": DISPOSITION_SCORED},
        "q2": {"correct": True, "disposition": DISPOSITION_SCORED},
    })
    candidate_clean = _arm_outcome_vector({
        "q1": {"correct": True, "disposition": DISPOSITION_SCORED},
        "q2": {"correct": False, "disposition": DISPOSITION_INFRA_FAILED},
    })
    candidate_contaminated = _arm_outcome_vector({
        "q1": {"correct": True, "disposition": DISPOSITION_SCORED},
        "q2": {"correct": False, "disposition": DISPOSITION_SCORED},
    })

    clean = mcnemar_from_vectors(baseline, candidate_clean, label_a="a", label_b="b")
    dirty = mcnemar_from_vectors(baseline, candidate_contaminated, label_a="a", label_b="b")

    assert clean.shared_qids == 1
    assert clean.a_correct_b_wrong == 0, (
        "a backend blip must not occupy a discordant cell"
    )
    # Mutation guard: with the disposition removed the SAME numbers produce the
    # old contaminated table, so the assertion above is about the stamp.
    assert dirty.shared_qids == 2
    assert dirty.a_correct_b_wrong == 1


def test_paired_screen_reports_the_exclusion_it_made():
    """CJ-9: the excluded rows are COUNTED, not silently absorbed. `n` is the
    decided count and `asserted_n` is the surface it is a fraction of."""
    from eval_tower import screen_paired_arms

    profile = {"dataset_sha256": "sha", "test_profile": "prof"}
    out = screen_paired_arms([
        {
            "label": "a",
            "profile": profile,
            "outcomes": {
                "q1": {"correct": True, "disposition": DISPOSITION_SCORED},
                "q2": {"correct": False, "disposition": DISPOSITION_INFRA_FAILED},
            },
        },
        {
            "label": "b",
            "profile": profile,
            "outcomes": {
                "q1": {"correct": False, "disposition": DISPOSITION_SCORED},
                "q2": {"correct": False, "disposition": DISPOSITION_SCORED},
            },
        },
    ])
    assert out["arms"]["a"]["n"] == 1
    assert out["arms"]["a"]["asserted_n"] == 2
    assert out["arms"]["a"]["excluded_non_quality"] == {DISPOSITION_INFRA_FAILED: 1}
    # Mutation guard: the clean arm reports no exclusion, so the numbers above
    # are not simply what this function always emits.
    assert out["arms"]["b"]["excluded_non_quality"] == {}
    assert out["arms"]["b"]["n"] == out["arms"]["b"]["asserted_n"] == 2
