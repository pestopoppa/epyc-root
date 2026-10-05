"""TD-21.11..21.14: model-side parse failures vs. parsed-and-wrong.

Proves, for each converted site (multiple_choice, f1_list,
structural_exact_match, exact_match):

  1. An unparseable model answer is DETECTED (counted via
     ``parse_failure_stats()``) regardless of the exclusion flag.
  2. With ``EXCLUDE_UNPARSEABLE_ANSWERS`` False (the shipped default), the
     row scores exactly as before: ``False``, no exception — live scores are
     byte-identical to pre-TD-21.11..21.14 (see also the SCORE-25/26 golden
     fixtures in ``test_debug_scorer_score25_26.py`` and the B7 golden-corpus
     pin, both still green).
  3. With the flag True, the SAME unparseable input raises
     ``AnswerParseError`` (a ``ScoringUnavailableError`` subclass), routing
     through ``seeding_scoring.score_answer_or_error``'s existing
     EXCLUDED/``scoring_failed`` path.
  4. A cleanly PARSED-AND-WRONG answer (a real letter/list/marker/tag that
     just doesn't match gold) stays a plain wrong answer under BOTH flag
     settings — the flag only ever changes the unparseable case.
  5. The happy path (correct answer) is unaffected by the flag either way.

``handoffs/active/typed-decision-plane.md`` TD-21.11..21.14;
``artifacts/audits/td-json-consumer-audit-20260924.md`` J-03/J-05/J-06/J-07.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))

import debug_scorer  # noqa: E402
from debug_scorer import (  # noqa: E402
    AnswerParseError,
    ScoringUnavailableError,
    score_answer,
)

# Captured at IMPORT time, before any fixture below (or any other test file
# sharing this process) can mutate the module attribute. The autouse fixture
# forces `EXCLUDE_UNPARSEABLE_ANSWERS = False` before every test in this file
# runs, INCLUDING the shipped-default check below — reading
# `debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS` from inside a test body would be
# vacuous (it would only ever see what the fixture just set, never the
# module's real top-level default). This constant is the one place that
# actually observes the shipped value.
_SHIPPED_DEFAULT_ON_IMPORT = debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS

# ── seeding_scoring, loaded the way test_seeding_scoring.py loads it: a
# private module identity so its own ScoringUnavailableError/AnswerParseError
# classes are self-consistent with the debug_scorer copy IT dynamically
# loads (mirrors seeding_scoring._load_orchestrator_debug_scorer). ──────────
_SS_ROOT = REPO_ROOT / "scripts" / "benchmark"
_SS_SPEC = importlib.util.spec_from_file_location(
    "seeding_scoring_td21_test", _SS_ROOT / "seeding_scoring.py"
)
_SS: ModuleType = importlib.util.module_from_spec(_SS_SPEC)
sys.modules["seeding_scoring_td21_test"] = _SS
_SS_SPEC.loader.exec_module(_SS)


@pytest.fixture(autouse=True)
def _reset_flag_and_stats():
    """Every test starts from a controlled flag=False baseline, counters zero.

    Setup deliberately forces False (not the shipped default) so every test
    in this file gets a deterministic starting point to flip from — most
    tests exercise both flag states explicitly within their own body.

    Teardown restores `_SHIPPED_DEFAULT_ON_IMPORT` (the module's REAL
    top-level default, captured once at this file's import time) rather
    than hardcoding False: this module does a plain `import debug_scorer`,
    the same `sys.modules` entry every other test file in the process
    shares, and hardcoding False here leaked a stale value forward into
    later files (including the B7 golden-corpus pin, which then silently
    scored against the wrong semantics instead of failing loudly — 2026-09-24
    TD-21.14 EQ-1/E19 post-ratification review, the same class of leak
    `test_debug_scorer_score25_26.py::
    test_structural_edge_no_solution_marker_is_false` had).
    """
    debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = False
    debug_scorer.reset_parse_failure_stats()
    yield
    debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = _SHIPPED_DEFAULT_ON_IMPORT
    debug_scorer.reset_parse_failure_stats()


def test_shipped_default_matches_ratification_state():
    """Pins the flag's SHIPPED value to whatever the EQ-1/E19 ratification
    state actually is.

    Ratified (2026-09-24): `EXCLUDE_UNPARSEABLE_ANSWERS` ships True — a
    genuinely empty/unparseable model answer is EXCLUDED (scoring_failed),
    never scored wrong. This is the "default-off contract" test the operator
    flagged in review: it WILL need updating the moment the flag's shipped
    value next changes, exactly like RTG-09's
    `test_default_config_reward_is_byte_identical_with_and_without_duration`
    needed renaming/updating into `test_pre_e18_config_reward_is_byte_
    identical_with_and_without_duration` (pinning the PRE-boundary values
    explicitly) plus a new `test_scoring_config_defaults_are_ratified` once
    E18 landed.
    #EQ1_RATIFICATION_TEST_SENTINEL: EXCLUDE_UNPARSEABLE_ANSWERS ships True (ratified — see instrument_eras.yaml E19)

    2026-09-24 history: briefly SUSPENDED to False (commit fcbb705f) because
    the TD-21.12/21.14 classification excluded WRONG answers (no structured
    marker, but a real candidate via the raw-last-line/line-split fallback)
    instead of scoring them wrong. RE-ENABLED on fix/e19-wrong-not-unparseable
    once `_score_exact_match`/`_score_f1_list` were corrected so a candidate
    extracted by ANY means — including the fallback — that disagrees with
    gold is always WRONG, never excluded; only a genuinely empty extraction
    still raises `AnswerParseError`. See `test_b7_golden_corpus_pin.py`
    (the 5 *_cot_wrongfinal / cotwrong cases) for the regression proof.
    """
    assert _SHIPPED_DEFAULT_ON_IMPORT is True


# ── multiple_choice (TD-21.11) ─────────────────────────────────────────────


def test_multiple_choice_unparseable_counts_and_scores_false_by_default():
    result = score_answer(
        answer="I refuse to pick a letter, this question is ambiguous.",
        expected="B",
        scoring_method="multiple_choice",
        scoring_config={},
    )
    assert result is False
    assert debug_scorer.parse_failure_stats().get("multiple_choice") == 1


def test_multiple_choice_unparseable_raises_when_flag_on():
    debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = True
    with pytest.raises(AnswerParseError):
        score_answer(
            answer="I refuse to pick a letter, this question is ambiguous.",
            expected="B",
            scoring_method="multiple_choice",
            scoring_config={},
        )
    assert debug_scorer.parse_failure_stats().get("multiple_choice") == 1


def test_multiple_choice_parsed_and_wrong_stays_wrong_under_both_flags():
    for flag in (False, True):
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = flag
        assert (
            score_answer("Answer: A", "B", "multiple_choice", {}) is False
        ), f"flag={flag}"
    assert "multiple_choice" not in debug_scorer.parse_failure_stats()


def test_multiple_choice_happy_path_unaffected_by_flag():
    for flag in (False, True):
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = flag
        assert score_answer("Answer: B", "B", "multiple_choice", {}) is True, f"flag={flag}"


# ── f1_list (TD-21.12) ──────────────────────────────────────────────────────

_F1_CFG = {"normalize": True, "threshold": 0.5}


def test_f1_list_unparseable_counts_and_scores_false_by_default():
    # A genuinely empty answer: no bullet/numbered/comma structure, and the
    # raw line-split fallback finds nothing at all (not even junk) to
    # compare against gold. TD-21.12 (corrected 2026-09-24): only THIS —
    # zero candidate items — is a model-side parse failure. A non-empty
    # fallback extraction that simply misses threshold is a wrong answer
    # (see test_f1_list_fallback_with_content_stays_wrong_under_both_flags).
    #
    # Calls the site scorer DIRECTLY, not the public `score_answer()`:
    # `score_answer()` has its OWN, older, unconditional guard
    # (`if not answer or not answer.strip(): return False`) that already
    # scores any whitespace-only answer False before dispatching to ANY
    # per-method scorer at all — regardless of this flag, and unaffected by
    # this fix. That pre-existing guard means the true "nothing extracted"
    # branch inside `_score_f1_list` itself is what TD-21.12 classifies;
    # exercise it directly the way `score_answer` would dispatch to it.
    result = debug_scorer._score_f1_list(
        "   ", '["High Line", "Central Park"]', _F1_CFG
    )
    assert result is False
    assert debug_scorer.parse_failure_stats().get("f1_list") == 1


def test_f1_list_unparseable_raises_when_flag_on():
    debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = True
    with pytest.raises(AnswerParseError):
        debug_scorer._score_f1_list("   ", '["High Line", "Central Park"]', _F1_CFG)


def test_f1_list_parsed_and_wrong_stays_wrong_under_both_flags():
    for flag in (False, True):
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = flag
        assert (
            score_answer("- totally unrelated nonsense", '["High Line"]', "f1_list", _F1_CFG)
            is False
        ), f"flag={flag}"
    assert "f1_list" not in debug_scorer.parse_failure_stats()


def test_f1_list_fallback_with_content_stays_wrong_under_both_flags():
    # TD-21.12 (corrected 2026-09-24): a prose paragraph with no
    # bullet/numbered/comma structure — the raw line-split fallback still
    # produces a non-empty candidate ("I am not sure which locations were
    # mentioned in this story." as one item) that simply misses threshold.
    # That is a genuine WRONG answer, never excluded and never counted as a
    # parse failure: the model DID produce something comparable, it was
    # just wrong. Before this fix, this exact input was misclassified as
    # unparseable (see the b7 golden-corpus pin regression this fixes).
    for flag in (False, True):
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = flag
        assert (
            score_answer(
                "I am not sure which locations were mentioned in this story.",
                '["High Line", "Central Park"]',
                "f1_list",
                _F1_CFG,
            )
            is False
        ), f"flag={flag}"
    assert "f1_list" not in debug_scorer.parse_failure_stats()


def test_f1_list_happy_path_unaffected_by_flag():
    for flag in (False, True):
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = flag
        assert (
            score_answer("- High Line", '["High Line"]', "f1_list", _F1_CFG) is True
        ), f"flag={flag}"


# ── structural_exact_match (TD-21.13) ───────────────────────────────────────

_ST_CFG = {"is_scorable": True, "extract_pattern": r"solution\s*=\s*(.+)"}


def test_structural_unparseable_counts_and_scores_false_by_default():
    result = score_answer(
        answer="the answer is 391365",  # no 'solution = ' marker at all
        expected="391365",
        scoring_method="structural_exact_match",
        scoring_config=_ST_CFG,
    )
    assert result is False
    assert debug_scorer.parse_failure_stats().get("structural_exact_match") == 1


def test_structural_unparseable_raises_when_flag_on():
    debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = True
    with pytest.raises(AnswerParseError):
        score_answer(
            answer="the answer is 391365",
            expected="391365",
            scoring_method="structural_exact_match",
            scoring_config=_ST_CFG,
        )


def test_structural_parsed_and_wrong_stays_wrong_under_both_flags():
    for flag in (False, True):
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = flag
        assert (
            score_answer("solution = 999999", "391365", "structural_exact_match", _ST_CFG)
            is False
        ), f"flag={flag}"
    assert "structural_exact_match" not in debug_scorer.parse_failure_stats()


def test_structural_happy_path_unaffected_by_flag():
    for flag in (False, True):
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = flag
        assert (
            score_answer("solution = 391365", "391365", "structural_exact_match", _ST_CFG)
            is True
        ), f"flag={flag}"


# ── exact_match's last-resort fallback (TD-21.14) ───────────────────────────


def test_exact_match_unparseable_counts_and_scores_false_by_default():
    # A genuinely empty/whitespace-only answer: no <answer>/####/\boxed{}
    # marker, and even the blind last-line fallback finds nothing at all
    # (not even a non-matching sentence) to compare against gold. TD-21.14
    # (corrected 2026-09-24): only THIS — no candidate extracted at all — is
    # a model-side parse failure. A prose sentence, or any other non-empty
    # last-line fallback that simply doesn't match, is a wrong answer (see
    # test_exact_match_fallback_mismatch_stays_wrong_under_both_flags).
    #
    # Calls the site scorer DIRECTLY, not the public `score_answer()`:
    # `score_answer()` has its OWN, older, unconditional guard
    # (`if not answer or not answer.strip(): return False`) that already
    # scores any whitespace-only answer False before dispatching to ANY
    # per-method scorer at all — regardless of this flag, and unaffected by
    # this fix. (One practical consequence of this fix: because that outer
    # guard already absorbs every truly-empty answer, and the raw-last-line
    # fallback here always finds SOMETHING in any non-empty answer, this
    # exact_match AnswerParseError branch is effectively unreachable via the
    # public `score_answer()` API — it only fires when a caller invokes the
    # site scorer directly. That is a correct, intended consequence of "a
    # candidate extracted by any means, including the raw fallback, is
    # never excluded": exercise it directly the way `score_answer` would
    # dispatch to it.)
    result = debug_scorer._score_exact_match("   \n  \n", "42", {})
    assert result is False
    assert debug_scorer.parse_failure_stats().get("exact_match") == 1


def test_exact_match_unparseable_raises_when_flag_on():
    debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = True
    with pytest.raises(AnswerParseError):
        debug_scorer._score_exact_match("   \n  \n", "42", {})


def test_exact_match_structured_mismatch_stays_wrong_under_both_flags():
    # A real <answer> tag that simply disagrees with gold: never a parse
    # failure, regardless of the flag.
    for flag in (False, True):
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = flag
        assert (
            score_answer("<answer>7</answer>", "42", "exact_match", {}) is False
        ), f"flag={flag}"
    assert "exact_match" not in debug_scorer.parse_failure_stats()


def test_exact_match_fallback_mismatch_stays_wrong_under_both_flags():
    # TD-21.14 (corrected 2026-09-24): no <answer>/####/\boxed{} marker, but
    # the raw last-line fallback DOES extract a non-empty candidate ("Final
    # answer: 999") that simply disagrees with gold. That is a genuine WRONG
    # answer, never excluded and never counted as a parse failure — the
    # model gamed the required-marker format by burying a competing
    # candidate answer in prose, and the B7 golden-corpus pin (sentinel
    # cot_wrongfinal cases, orchestration/reports/
    # b7_scorer_golden_delta_20260721/golden_corpus.jsonl) has always scored
    # this False. Before this fix it was misclassified as unparseable
    # (silently EXCLUDED once EXCLUDE_UNPARSEABLE_ANSWERS shipped True) —
    # exactly the quality-denominator gaming E17 exists to prevent.
    for flag in (False, True):
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = flag
        assert (
            score_answer(
                "Candidate: 25\nFinal answer: 999", "25", "exact_match", {}
            )
            is False
        ), f"flag={flag}"
    assert "exact_match" not in debug_scorer.parse_failure_stats()


def test_exact_match_happy_path_unaffected_by_flag():
    for flag in (False, True):
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = flag
        assert score_answer("<answer>42</answer>", "42", "exact_match", {}) is True, f"flag={flag}"


def test_exact_match_fallback_that_happens_to_match_is_not_a_parse_failure():
    # Existing golden behavior (test_debug_scorer_semantics.py): the raw
    # last-line fallback CAN legitimately match gold (e.g. via the quoted-
    # text OCR fallback). That must stay a clean True, not a parse failure,
    # under either flag setting.
    answer = 'Earlier evidence mentions "Paris".\nFinal answer: "London"'
    for flag in (False, True):
        debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS = flag
        assert score_answer(answer, "London", "exact_match", {}) is True, f"flag={flag}"
    assert "exact_match" not in debug_scorer.parse_failure_stats()


# ── AnswerParseError subclasses ScoringUnavailableError ────────────────────


def test_answer_parse_error_is_a_scoring_unavailable_error():
    assert issubclass(AnswerParseError, ScoringUnavailableError)


# ── end-to-end: seeding_scoring.score_answer_or_error already excludes it ──


def test_score_answer_or_error_excludes_parse_failure_when_flag_on():
    """The literal "route through the existing exclusion path" claim.

    With the flag on, seeding_scoring.score_answer_or_error (the exclusion
    path named in TD-21.11..21.14, seeding_scoring.py:83-113) needs NO code
    change of its own: it already catches ScoringUnavailableError generically,
    and AnswerParseError is one.

    The flag lives on the debug_scorer module INSTANCE that
    ``seeding_scoring._load_orchestrator_debug_scorer`` dynamically loads
    under its own private ``sys.modules`` key — a separate object from this
    test file's plain ``import debug_scorer`` above — so it must be set
    there, not on ``_SS`` (seeding_scoring itself has no such attribute).
    """
    scorer_mod = _SS._load_orchestrator_debug_scorer()
    scorer_mod.EXCLUDE_UNPARSEABLE_ANSWERS = True
    try:
        verdict, reason = _SS.score_answer_or_error(
            answer="I refuse to pick a letter.",
            expected="B",
            scoring_method="multiple_choice",
            scoring_config={},
        )
    finally:
        scorer_mod.EXCLUDE_UNPARSEABLE_ANSWERS = False
        scorer_mod.reset_parse_failure_stats()
    assert verdict is None
    assert reason is not None
    assert "scoring_unavailable" in reason
    assert "answer_parse_failed[multiple_choice]" in reason


# ── _is_valid_json: NOT converted, and NOT switched to fish_json ───────────
#
# 2026-09-24 main-session review: an earlier draft of this commit swapped
# _is_valid_json's extraction over to the shared `fish_json` helper
# (src/structured_output/repair.py). fish_json REPAIRS trailing commas and
# stray closers and tolerates a fenced block, which would make this IFEval
# `json_valid` oracle accept text that is not actually valid JSON — an
# ungated live-score change to a real correctness check, with no era
# boundary covering it. Reverted before landing; this section now pins the
# oracle's byte-identical, pre-TD-21 behavior instead.


def test_is_valid_json_still_accepts_a_single_clean_object():
    assert debug_scorer._is_valid_json('{"a": 1}') is True


def test_is_valid_json_rejects_pure_prose():
    assert debug_scorer._is_valid_json("there is no json here at all") is False


def test_is_valid_json_rejects_trailing_comma_object():
    # fish_json would REPAIR this and return a parsed value (accepting it as
    # "valid JSON"). The oracle must not: a trailing comma is not valid JSON,
    # and json_valid's callers rely on that being a hard fail.
    assert debug_scorer._is_valid_json('{"a": 1,}') is False


def test_is_valid_json_rejects_multiple_blobs_legacy_slice_still_fails():
    # Documents the pre-existing (unchanged) false negative: the naive
    # find("{")/rfind("}") slice spans from the FIRST "{" to the LAST "}",
    # producing invalid JSON here. This stays False — no fish_json swap.
    assert debug_scorer._is_valid_json('{"a": 1} some text {"b": 2}') is False


def test_json_valid_verifier_end_to_end_via_score_answer_still_naive():
    result = score_answer(
        answer='noisy prefix {"a": 1,} trailing',
        expected="",
        scoring_method="programmatic",
        scoring_config={"verifier": "json_valid"},
    )
    assert result is False


# ── arm-keyed parse-failure counting: concurrent arms don't mix counts ─────


def test_parse_failure_stats_bucketed_by_arm_key_does_not_mix():
    debug_scorer.reset_parse_failure_stats(arm_key="arm-a")
    debug_scorer.reset_parse_failure_stats(arm_key="arm-b")
    try:
        score_answer(
            "no letter here", "B", "multiple_choice", {"_eval_batch_id": "arm-a"}
        )
        score_answer(
            "no letter here", "B", "multiple_choice", {"_eval_batch_id": "arm-a"}
        )
        score_answer(
            "no letter here", "B", "multiple_choice", {"_eval_batch_id": "arm-b"}
        )
        assert debug_scorer.parse_failure_stats(arm_key="arm-a") == {"multiple_choice": 2}
        assert debug_scorer.parse_failure_stats(arm_key="arm-b") == {"multiple_choice": 1}
        # The unscoped (arm_key=None) bucket — used by callers that never set
        # _eval_batch_id, e.g. the seeding harness — is untouched by either.
        assert "multiple_choice" not in debug_scorer.parse_failure_stats(arm_key=None) or (
            debug_scorer.parse_failure_stats(arm_key=None).get("multiple_choice", 0) == 0
        )
    finally:
        debug_scorer.reset_parse_failure_stats(arm_key="arm-a")
        debug_scorer.reset_parse_failure_stats(arm_key="arm-b")


def test_reset_parse_failure_stats_only_clears_its_own_arm_key():
    debug_scorer.reset_parse_failure_stats(arm_key="arm-c")
    debug_scorer.reset_parse_failure_stats(arm_key="arm-d")
    score_answer("no letter here", "B", "multiple_choice", {"_eval_batch_id": "arm-c"})
    score_answer("no letter here", "B", "multiple_choice", {"_eval_batch_id": "arm-d"})
    debug_scorer.reset_parse_failure_stats(arm_key="arm-c")
    assert debug_scorer.parse_failure_stats(arm_key="arm-c") == {}
    assert debug_scorer.parse_failure_stats(arm_key="arm-d") == {"multiple_choice": 1}
    debug_scorer.reset_parse_failure_stats(arm_key="arm-d")


def test_score_answer_or_error_unaffected_when_flag_off():
    """Default OFF: the seeding exclusion path is not exercised by a parse
    failure at all — the row keeps scoring `False`, exactly as before."""
    scorer_mod = _SS._load_orchestrator_debug_scorer()
    try:
        verdict, reason = _SS.score_answer_or_error(
            answer="I refuse to pick a letter.",
            expected="B",
            scoring_method="multiple_choice",
            scoring_config={},
        )
    finally:
        # This still counts (unconditionally) via `_record_parse_failure` in
        # the module-global `arm_key=None` bucket — clear it so it cannot
        # leak into another test file that reads that same shared
        # dynamically-loaded debug_scorer instance (`_load_orchestrator_
        # debug_scorer` caches by a fixed sys.modules key, shared across
        # every seeding_scoring instance and eval_tower.py in this process).
        scorer_mod.reset_parse_failure_stats()
    assert verdict is False
    assert reason is None
