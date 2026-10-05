"""Regression coverage for multiple-choice textual labels."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))

import pytest  # noqa: E402

from debug_scorer import ScoringUnavailableError, score_answer  # noqa: E402


def test_multiple_choice_accepts_configured_textual_label() -> None:
    assert score_answer(
        answer="**incorrect**",
        expected="incorrect",
        scoring_method="multiple_choice",
        scoring_config={"choices": ["correct", "incorrect"]},
    )


def test_multiple_choice_maps_letter_to_configured_textual_expected() -> None:
    assert score_answer(
        answer="Answer: B",
        expected="incorrect",
        scoring_method="multiple_choice",
        scoring_config={"choices": ["correct", "incorrect"]},
    )
    assert not score_answer(
        answer="Answer: A",
        expected="incorrect",
        scoring_method="multiple_choice",
        scoring_config={"choices": ["correct", "incorrect"]},
    )


def test_multiple_choice_accepts_parenthesized_expected_letter() -> None:
    assert score_answer(
        answer="Answer: B",
        expected="(B)",
        scoring_method="multiple_choice",
        scoring_config={},
    )


def test_multiple_choice_prefers_longer_overlapping_text_choice() -> None:
    choices = ["cat", "black cat"]

    assert score_answer(
        answer="black cat",
        expected="black cat",
        scoring_method="multiple_choice",
        scoring_config={"choices": choices},
    )
    assert not score_answer(
        answer="black cat",
        expected="cat",
        scoring_method="multiple_choice",
        scoring_config={"choices": choices},
    )


def test_multiple_choice_prefers_containing_choice_with_same_end() -> None:
    choices = ["None", "None of the above"]

    assert score_answer(
        answer="None of the above",
        expected="None of the above",
        scoring_method="multiple_choice",
        scoring_config={"choices": choices},
    )
    assert not score_answer(
        answer="None of the above",
        expected="None",
        scoring_method="multiple_choice",
        scoring_config={"choices": choices},
    )


def test_multiple_choice_requires_choices_for_textual_expected() -> None:
    """CJ-8 (2026-09-07) RENEGOTIATED: this used to assert `False`.

    A textual gold with no `choices` is a GOLD defect — there is nothing to
    decide against — and returning False recorded it as the MODEL being wrong,
    a systematic 0 across every row of a malformed slice. It now raises
    `ScoringUnavailableError`, the same refusal this module already makes for an
    unparseable `math_verify` gold and a non-list `f1_list` gold.

    It is still BLOCKING: `score_answer_or_error` turns the raise into
    `(None, reason)` and `eval_tower` EXCLUDES the row from the quality
    denominator. It is never converted into a pass.
    """
    with pytest.raises(ScoringUnavailableError):
        score_answer(
            answer="**incorrect**",
            expected="incorrect",
            scoring_method="multiple_choice",
            scoring_config={},
        )


def test_unusable_gold_is_excluded_not_scored_wrong() -> None:
    """The row leaves the denominator; it does NOT become a correct answer."""
    from seeding_scoring import score_answer_or_error

    verdict, reason = score_answer_or_error(
        answer="**incorrect**",
        expected="incorrect",
        scoring_method="multiple_choice",
        scoring_config={},
    )
    assert verdict is None, "an unscoreable row has no verdict — not True, not False"
    assert reason

    # Mutation guard: supply the missing signal (the choices list) and the SAME
    # inputs score normally again, so the refusal above is about the unusable
    # gold and not about this scorer having stopped working.
    verdict, reason = score_answer_or_error(
        answer="**incorrect**",
        expected="incorrect",
        scoring_method="multiple_choice",
        scoring_config={"choices": ["correct", "incorrect"]},
    )
    assert verdict is True
    assert reason is None
