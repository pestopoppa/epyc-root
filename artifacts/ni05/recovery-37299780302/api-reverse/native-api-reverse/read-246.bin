"""Regression coverage for B7 deterministic scorer semantics."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))

from debug_scorer import score_answer  # noqa: E402


def test_exact_match_quote_fallback_only_uses_final_region() -> None:
    answer = 'Earlier evidence mentions "Paris".\nFinal answer: "London"'

    assert score_answer(answer, "London", "exact_match")
    assert not score_answer(answer, "Paris", "exact_match")


def test_exact_match_extracts_nested_boxed_answer() -> None:
    assert score_answer(
        answer=r"Work omitted. Therefore \boxed{\frac{1}{2}}.",
        expected=r"\frac{1}{2}",
        scoring_method="exact_match",
    )


def test_exact_match_rejects_multi_group_extract_pattern() -> None:
    with pytest.raises(ValueError):
        score_answer(
            answer="xy",
            expected="x",
            scoring_method="exact_match",
            scoring_config={"extract_pattern": r"(x)(y)"},
        )


def test_exact_match_stringifies_non_string_expected() -> None:
    assert score_answer("1,234", 1234, "exact_match")


def test_substring_uses_text_boundaries() -> None:
    assert score_answer("the black cat slept", "cat", "substring")
    assert not score_answer("concatenate these strings", "cat", "substring")


def test_f1_uses_multiset_token_overlap() -> None:
    assert score_answer(
        answer="<answer>red red blue</answer>",
        expected="red red green",
        scoring_method="f1",
        scoring_config={"threshold": 0.6},
    )


def test_f1_rejects_multi_group_extract_pattern() -> None:
    with pytest.raises(ValueError):
        score_answer(
            answer="xy",
            expected="x",
            scoring_method="f1",
            scoring_config={"extract_pattern": r"(x)(y)"},
        )
