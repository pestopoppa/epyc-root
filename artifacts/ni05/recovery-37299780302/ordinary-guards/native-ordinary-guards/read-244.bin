"""PRB-T4 (2026-09-17) guards: MMLU-Pro I/J gold and the vacuous code-substring oracle.

Two defects surfaced by the PRB-T4 TALE run (epyc-inference-research ``b4d38ebc``):

* ``mmlu_pro`` died at question 1 with ``ScoringUnavailableError``: the adapter
  emitted the upstream gold letter with ``scoring_config={}``, and this scorer's
  letter range was hard-wired to A-H. 2,053 of 12,032 rows have gold I or J and
  could never be scored (before CJ-8 they were silently scored False).
* ``livecodebench`` "passed" on ``substring 'def '``: 2,349 pool rows built before
  the 2026-08-12 oracle rebuild still carry it, and any Python answer contains it.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))

import pytest  # noqa: E402

import debug_scorer  # noqa: E402
from debug_scorer import AnswerParseError, ScoringUnavailableError, score_answer  # noqa: E402

TEN = [f"option {i}" for i in range(10)]
MMLU_PRO_CFG = {"choices": TEN, "choice_labels": "ABCDEFGHIJ"}


def _mc(answer: str, expected: str, config: dict | None = None) -> bool:
    return score_answer(answer, expected, "multiple_choice", config)


# ── MMLU-Pro label range ────────────────────────────────────────────────────


@pytest.mark.parametrize("gold", list("ABCDEFGHIJ"))
def test_every_mmlu_pro_gold_letter_scores_right_and_a_wrong_letter_fails(gold: str) -> None:
    wrong = "A" if gold != "A" else "J"
    assert _mc(gold, gold, MMLU_PRO_CFG) is True
    assert _mc(f"Answer: {gold}", gold, MMLU_PRO_CFG) is True
    assert _mc(f"**{gold}**", gold, MMLU_PRO_CFG) is True
    assert _mc(wrong, gold, MMLU_PRO_CFG) is False
    assert _mc(f"The answer is {wrong}.", gold, MMLU_PRO_CFG) is False


def test_the_prbt4_row_shape_still_refuses_rather_than_scoring_wrong() -> None:
    """Undeclared rows keep the historical A-H range: I/J gold is a join defect."""
    with pytest.raises(ScoringUnavailableError, match="A-H"):
        _mc("I", "I", {})


def test_undeclared_rows_keep_the_historical_a_to_h_parse() -> None:
    """Sealed captures scored before the fix must re-score identically."""
    assert _mc("Answer: B", "B", {}) is True
    # "J" is outside A-H, so the parse falls through to the last standalone A-H.
    assert _mc("Not A. Answer: J", "A", {}) is True


def test_the_pronoun_i_is_not_a_vote_for_option_i() -> None:
    # "I don't know" carries no option letter at all under any extraction
    # strategy (the pronoun-guard excludes bare "I" from the loose
    # standalone-letter match) — genuinely no candidate, not a comparable
    # wrong letter. TD-21.11/EQ-1: with EXCLUDE_UNPARSEABLE_ANSWERS off it
    # scores False (pre-EQ-1 behavior, byte-identical); with the shipped
    # default (True) it is a real model-side parse failure and raises
    # AnswerParseError, exactly like every other "nothing extracted" case
    # in tests/unit/test_debug_scorer_td21_parse_exclusion.py. Pin both
    # explicitly rather than relying on whatever another test file in this
    # process happened to leave the flag at.
    _prior_flag = debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS
    try:
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = False
        assert _mc("I don't know", "I", MMLU_PRO_CFG) is False
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = True
        with pytest.raises(AnswerParseError):
            _mc("I don't know", "I", MMLU_PRO_CFG)
    finally:
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = _prior_flag
        debug_scorer.reset_parse_failure_stats()
    assert _mc("I think it is B", "B", MMLU_PRO_CFG) is True
    assert _mc("I believe\nI", "I", MMLU_PRO_CFG) is True


def test_gold_letter_past_the_configured_options_is_a_corpus_defect() -> None:
    with pytest.raises(ScoringUnavailableError, match="points past"):
        _mc("J", "J", {"choices": TEN[:4], "choice_labels": "ABCDEFGHIJ"})
    with pytest.raises(ScoringUnavailableError):
        _mc("J", "J", {"choices": TEN[:4], "choice_labels": "ABCD"})


@pytest.mark.parametrize("labels", ["ABD", "BCD", "", ["A", "C"]])
def test_malformed_choice_labels_refuse(labels) -> None:
    with pytest.raises(ScoringUnavailableError, match="contiguous"):
        _mc("A", "A", {"choice_labels": labels})


def test_list_form_labels_are_accepted() -> None:
    assert _mc("I", "I", {"choice_labels": list("ABCDEFGHIJ")}) is True


# ── MMLU-Pro adapter (orchestrator twin of the research builder) ────────────


def _adapter_row(**overrides) -> dict:
    row = {
        "question": "Q?",
        "options": list(TEN),
        "answer": "I",
        "answer_index": 8,
        "category": "law",
    }
    row.update(overrides)
    return row


def _adapter():
    from dataset_adapter_modules.general import MMLUProAdapter

    adapter = MMLUProAdapter()
    adapter._dataset = [_adapter_row()]
    return adapter


def test_adapter_emits_a_scoreable_i_row_and_known_wrong_fails() -> None:
    q = _adapter()._row_to_prompt(0, _adapter_row())
    assert q["expected"] == "I"
    assert q["scoring_config"] == {"choices": TEN, "choice_labels": "ABCDEFGHIJ"}
    args = (q["expected"], q["scoring_method"], q["scoring_config"])
    assert score_answer("I", *args) is True
    assert score_answer("H", *args) is False


def test_adapter_label_range_follows_the_option_count() -> None:
    row = _adapter_row(options=TEN[:4], answer="C", answer_index=2)
    q = _adapter()._row_to_prompt(0, row)
    assert q["scoring_config"]["choice_labels"] == "ABCD"


@pytest.mark.parametrize(
    "overrides",
    [
        {"answer": "H"},  # letter disagrees with index
        {"answer_index": 10},  # past the options
        {"answer_index": None},
        {"answer_index": True},
        {"options": []},
    ],
)
def test_adapter_refuses_inconsistent_gold(overrides: dict) -> None:
    from dataset_adapter_modules.general import MMLUProAdapter

    with pytest.raises(ValueError):
        MMLUProAdapter.gold_letter(_adapter_row(**overrides))


# ── vacuous code-substring oracle ───────────────────────────────────────────

STALE_LCB_CFG = {"language": "python", "timeout": 30, "case_sensitive": True, "substring": "def "}


@pytest.mark.parametrize(
    "answer",
    [
        "def solve():\n    pass",  # known-wrong: used to PASS
        "def twoSum(nums, target):\n    return [0, 1]",
        "no code at all",
    ],
)
def test_substring_on_a_code_row_refuses_instead_of_passing(answer: str) -> None:
    with pytest.raises(ScoringUnavailableError, match="code row"):
        score_answer(answer, "def ", "substring", STALE_LCB_CFG)


def test_plain_substring_rows_are_unchanged() -> None:
    assert score_answer("the P.S. line", "P.S.", "substring", {"case_sensitive": True}) is True
    assert score_answer("nothing", "P.S.", "substring", {}) is False
