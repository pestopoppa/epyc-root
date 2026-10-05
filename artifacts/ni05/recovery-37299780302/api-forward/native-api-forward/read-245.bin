"""Golden fixtures for the additive f1_list / structural_exact_match scorers.

Audit SCORE-25 (``f1_list``, tulving_episodic — 456 rows) and SCORE-26
(``structural_exact_match``, longcot_mini — 402 rows). Before these landed both
methods raised "Unknown scoring method" and every row of those suites was
honestly EXCLUDED (REL-1) from the quality denominator. The scorers are
ADDITIVE: they touch ONLY those two previously-erroring methods; no other
scorer's verdict changes (the B7 golden-corpus pin, which has no f1_list /
structural_exact_match rows, still passes byte-for-byte).

All gold values below are copied verbatim from real pool rows
(``epyc-inference-research/benchmarks/prompts/question_pool.jsonl``):
  - f1_list golds are JSON lists of answer items (locations, names, dates).
  - structural_exact_match golds are canonical JSON scalars / arrays / objects
    (math answer lists, chess FEN strings, chemistry SMILES, CS int/dict).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))

import debug_scorer  # noqa: E402
from debug_scorer import (  # noqa: E402
    ScoringUnavailableError,
    score_answer,
)


# ── Dispatch: the two methods are now recognised (no ValueError) ──────────


@pytest.mark.parametrize("method", ["f1_list", "structural_exact_match"])
def test_method_is_dispatched_not_unknown(method: str) -> None:
    # A recognised method returns a bool; an unrecognised one would raise
    # ValueError("Unknown scoring method: ...") — the pre-fix behaviour.
    expected = '["x"]' if method == "f1_list" else '"x"'
    out = score_answer("- x" if method == "f1_list" else "solution = x", expected, method, {})
    assert isinstance(out, bool)


# ── SCORE-25: f1_list (tulving_episodic) ─────────────────────────────────

# Real single-item gold (retrieval_type=Spaces).
GOLD_SINGLE = '["High Line"]'
# Real single-item gold (retrieval_type=Entities).
GOLD_ENTITY = '["Levi Rodriguez"]'
# Real multi-item gold (Entities).
GOLD_MULTI = '["Benjamin Green", "Henry Reed"]'
# Real multi-item date gold (Times).
GOLD_DATES = '["May 11, 2026", "February 27, 2026"]'
# Real empty gold — the group-0 hallucination check (nb_gt == 0).
GOLD_EMPTY = "[]"

F1_CFG = {"normalize": True, "threshold": 0.5}


def _f1(answer: str, expected: str) -> bool:
    return score_answer(answer, expected, "f1_list", F1_CFG)


def test_f1_list_correct_bullet_exact() -> None:
    assert _f1("- High Line", GOLD_SINGLE) is True


def test_f1_list_correct_numbered_list() -> None:
    assert _f1("1. Benjamin Green\n2. Henry Reed", GOLD_MULTI) is True


def test_f1_list_correct_comma_separated() -> None:
    assert _f1("May 11, 2026, February 27, 2026", GOLD_DATES) is True


def test_f1_list_incorrect_unrelated() -> None:
    assert _f1("- totally unrelated nonsense", GOLD_SINGLE) is False


def test_f1_list_incorrect_partial_below_threshold() -> None:
    # Only 1 of 2 gold items recovered → recall 0.5, precision 1.0 on the
    # lenient denominator → F1 below the 0.5 cutoff is NOT guaranteed; but a
    # single wrong item against a 2-item gold is well below threshold.
    assert _f1("- wrong entity name", GOLD_MULTI) is False


def test_f1_list_edge_empty_gold_abstention_is_correct() -> None:
    # Empty gold + explicit abstention ("None") ⇒ correctly avoided hallucination.
    assert _f1("None", GOLD_EMPTY) is True


def test_f1_list_edge_empty_gold_hallucination_is_wrong() -> None:
    # Empty gold + a listed item ⇒ hallucination ⇒ False.
    assert _f1("- Some Place", GOLD_EMPTY) is False


def test_f1_list_edge_b7_article_leniency() -> None:
    # B7 _normalize_text strips articles: "The High Line" still matches "High Line".
    assert _f1("- The High Line", GOLD_SINGLE) is True


def test_f1_list_edge_b7_diacritic_fold() -> None:
    # B7 _normalize_text folds diacritics (NFKD + combining strip).
    assert _f1("- Levi Rodríguez", GOLD_ENTITY) is True


def test_f1_list_edge_case_insensitive() -> None:
    assert _f1("- high line", GOLD_SINGLE) is True


def test_f1_list_gold_defect_non_list_raises() -> None:
    # A non-list gold is a dataset/gold defect ⇒ ScoringUnavailableError, so the
    # caller records an EXCLUDED row rather than scoring a wrong answer.
    with pytest.raises(ScoringUnavailableError):
        score_answer("- x", '"not a list"', "f1_list", F1_CFG)


def test_f1_list_gold_defect_unparseable_raises() -> None:
    with pytest.raises(ScoringUnavailableError):
        score_answer("- x", "High Line", "f1_list", F1_CFG)


# ── SCORE-26: structural_exact_match (longcot_mini) ──────────────────────

# Real golds (verbatim from the pool).
GOLD_MATH_LIST = '["2013^{4025}", 2692, 26]'          # math, mixed str+int list
GOLD_FEN = '"8/r7/kn3p2/1pr1pPpp/NP2PbPP/5K2/3B4/1bR1bB2 w - - 122 349"'  # chess
GOLD_SMILES = '"C1(CCCC1)NC1=CC=CC=2N1N=C(C2C2=CC(=NC=C2)F)C2=CC=C(C=C2)F"'  # chemistry
GOLD_INT = "391365"                                    # cs / chess int scalar
GOLD_DICT = '{"Q1": "(M_1*(M_2*(M_3*M_4)))", "Q2": 3159991384, "Q3": 3, "Q4": 3, "Q5": 0}'

ST_CFG = {"is_scorable": True, "extract_pattern": r"solution\s*=\s*(.+)"}


def _st(answer: str, expected: str) -> bool:
    return score_answer(answer, expected, "structural_exact_match", ST_CFG)


def test_structural_correct_exact_list() -> None:
    assert _st("reasoning...\nsolution = " + GOLD_MATH_LIST, GOLD_MATH_LIST) is True


def test_structural_correct_multiline_container_with_trailing_junk() -> None:
    # Balanced-bracket scan stops at the matching ']'; trailing text is ignored.
    ans = "work\nsolution = [\n  \"2013^{4025}\",\n  2692,\n  26\n]\nDone."
    assert _st(ans, GOLD_MATH_LIST) is True


def test_structural_correct_fen_string() -> None:
    assert _st("solution = " + GOLD_FEN, GOLD_FEN) is True


def test_structural_correct_smiles_case_preserved() -> None:
    assert _st("solution = " + GOLD_SMILES, GOLD_SMILES) is True


def test_structural_correct_int_scalar() -> None:
    assert _st("solution = 391365", GOLD_INT) is True


def test_structural_correct_numeric_string_equals_int() -> None:
    # "391365" (numeric string) canonicalizes to the same int as gold 391365.
    assert _st('solution = "391365"', GOLD_INT) is True


def test_structural_correct_float_form_of_int() -> None:
    assert _st("solution = 391365.0", GOLD_INT) is True


def test_structural_correct_dict_key_order_independent() -> None:
    reordered = '{"Q5": 0, "Q4": 3, "Q3": 3, "Q2": 3159991384, "Q1": "(M_1*(M_2*(M_3*M_4)))"}'
    assert _st("solution = " + reordered, GOLD_DICT) is True


def test_structural_incorrect_wrong_scalar() -> None:
    assert _st("solution = 999999", GOLD_INT) is False


def test_structural_incorrect_fen_case_sensitive() -> None:
    # FEN is case-sensitive (piece colour); lowercasing must NOT match.
    assert _st("solution = " + GOLD_FEN.lower(), GOLD_FEN) is False


def test_structural_edge_no_solution_marker_is_false() -> None:
    # Model ignored the required "solution =" format ⇒ task failure ⇒ False
    # (NOT a scorer-unavailability error) AT THE PRE-EQ-1/E19 default
    # (debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS=False). Forced explicitly so
    # this golden fixture stays byte-for-byte regardless of the module's
    # shipped default once EQ-1/E19 (TD-21.11..21.14,
    # scripts/operator/ratify_eq1_answer_parse_exclusion_20260924.sh, epyc-
    # root repo) is ratified — at that point the SAME input instead raises
    # AnswerParseError (see test_debug_scorer_td21_parse_exclusion.py for the
    # flag-aware behavior at both settings).
    #
    # Restore the PRIOR value (not a hardcoded False) in `finally`: this
    # module does a plain `import debug_scorer`, the same `sys.modules`
    # entry every other test file in this process sees (including the B7
    # golden-corpus pin) — leaving the flag forced to False here leaked into
    # and silently masked a real classification defect in
    # `test_b7_golden_corpus_pin.py` when both files ran in the same pytest
    # invocation (2026-09-24, TD-21.14 EQ-1/E19 post-ratification review).
    _prior_flag = debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS
    debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = False
    try:
        assert _st("the answer is " + GOLD_MATH_LIST, GOLD_MATH_LIST) is False
    finally:
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = _prior_flag
        debug_scorer.reset_parse_failure_stats()


def test_structural_edge_last_marker_wins() -> None:
    # Models echo the format instruction earlier; the real answer is the LAST
    # "solution =" occurrence.
    ans = "solution = WRONG_EARLY\n...more work...\nsolution = " + GOLD_INT
    assert _st(ans, GOLD_INT) is True


def test_structural_edge_trailing_period_on_scalar() -> None:
    assert _st("solution = 391365.", GOLD_INT) is True
