"""Pin the B7 ratified scorer semantics against the golden delta corpus.

The B7 golden-delta report
(``orchestration/reports/b7_scorer_golden_delta_20260721/``) recorded, for
every corpus case, the outcome the POST-package scorer produced (the ``new``
column of ``results.jsonl``). That column is the *ratified* semantics of the
07a20a7c + 8f24679a scorer package.

This test re-runs the CURRENT ``scripts/benchmark/debug_scorer.py`` over the
same corpus and asserts it still produces exactly those recorded outcomes. If a
future scorer edit changes any outcome, this test fails — forcing whoever makes
the change to regenerate and re-review the golden file *deliberately* (via
``run_delta.py``), rather than silently drifting the eval instrument.

The fast subset (``pin_fast`` — pure in-process scoring, no subprocess/network)
is the hard, always-run pin. A second test covers the subprocess/network rows
(code_execution, llm_judge) and is skipped where their host infra is absent.

B7b addendum (SCORE-07/08/09/12, ratified 2026-07-21): rows carrying a
``scorer`` discriminator (``rubric_parse`` / ``rubric_aggregate`` /
``code_exec_confidence``) live in ``scripts/autopilot/eval_tower.py`` +
``rubric_scoring.py``, NOT in ``debug_scorer.py``. They are pinned against those
surfaces by ``_b7b_outcome`` and are segregated from the debug_scorer rows so
neither pin scores the other's cases.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO_ROOT / "orchestration" / "reports" / "b7_scorer_golden_delta_20260721"
CORPUS_PATH = REPORT_DIR / "golden_corpus.jsonl"
RESULTS_PATH = REPORT_DIR / "results.jsonl"
CODE_EXEC_TMP = Path("/mnt/raid0/llm/tmp")

sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import debug_scorer  # noqa: E402
from debug_scorer import score_answer  # noqa: E402
import eval_tower  # noqa: E402
from rubric_scoring import aggregate_rubric_score  # noqa: E402

DEBUG_SCORER_SRC = REPO_ROOT / "scripts" / "benchmark" / "debug_scorer.py"


def _shipped_exclude_unparseable_default() -> bool:
    """Re-derive the SHIPPED ``EXCLUDE_UNPARSEABLE_ANSWERS`` default straight
    from source, independent of whatever this pytest process's shared
    ``debug_scorer`` module instance currently holds.

    2026-09-24 post-mortem: this file does a plain ``import debug_scorer``,
    the same ``sys.modules`` entry every other test file in the process
    shares. A test elsewhere that flips
    ``debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS`` and fails to restore it in
    ``finally`` (``test_debug_scorer_score25_26.py::
    test_structural_edge_no_solution_marker_is_false`` did exactly this)
    silently changes what THIS pin scores against — the golden corpus then
    passes against the wrong semantics instead of failing loudly. Reading
    the assignment straight out of the source file makes that leak
    impossible to hide: whatever the module attribute says at test time is
    checked against the byte the file actually ships.
    """
    match = re.search(
        r"^EXCLUDE_UNPARSEABLE_ANSWERS\s*=\s*(True|False)\s*$",
        DEBUG_SCORER_SRC.read_text(),
        re.MULTILINE,
    )
    assert match, "could not find EXCLUDE_UNPARSEABLE_ANSWERS default in debug_scorer.py"
    return match.group(1) == "True"


def test_golden_pin_sees_the_modules_real_exclude_unparseable_flag() -> None:
    """Guard against the exact leak this comment/test pair was added for
    (see ``_shipped_exclude_unparseable_default``): if any other test file
    in this process left ``debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS`` at a
    value other than the shipped default, the golden-corpus pin below would
    silently score against the WRONG semantics instead of failing. Assert
    the live value matches source before any golden-corpus row is scored.
    """
    assert debug_scorer.EXCLUDE_UNPARSEABLE_ANSWERS == _shipped_exclude_unparseable_default()


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _outcome(row: dict) -> Any:
    """Mirror run_delta.py: bool outcome, or 'ERROR:<ExcType>'."""
    try:
        return bool(
            score_answer(
                answer=row["answer"],
                expected=row["expected"],
                scoring_method=row["scoring_method"],
                scoring_config=row.get("scoring_config"),
            )
        )
    except Exception as exc:  # noqa: BLE001 — classify by exception type name
        return f"ERROR:{type(exc).__name__}"


def _recorded_new(value: Any) -> Any:
    # results.jsonl stores booleans as JSON true/false and errors as strings.
    return value


def _b7b_outcome(row: dict) -> Any:
    """Re-derive a B7b row's ratified outcome from the eval_tower/rubric surfaces."""
    scorer = row["scorer"]
    if scorer == "rubric_parse":  # SCORE-07
        return eval_tower._parse_rubric_judge_scores(row["answer"])
    if scorer == "rubric_aggregate":  # SCORE-09
        return round(aggregate_rubric_score(json.loads(row["answer"])).score, 6)
    if scorer == "code_exec_confidence":  # SCORE-12
        conf, source = eval_tower._derive_question_confidence(
            scoring_method=row["scoring_method"],
            correct=row["correct"],
            probability_confidence=None,
            rubric_scores={},
        )
        return [conf, source]
    raise AssertionError(f"unknown b7b scorer: {scorer}")


CORPUS = {r["case_id"]: r for r in _load_jsonl(CORPUS_PATH)}
RESULTS = _load_jsonl(RESULTS_PATH)


def _scorer_of(case_id: str) -> str:
    return CORPUS[case_id].get("scorer", "debug_scorer")


# Segregate the debug_scorer package (B7) rows from the eval_tower B7b rows so
# neither pin ever scores the other's cases.
DEBUG_RESULTS = [r for r in RESULTS if _scorer_of(r["case_id"]) == "debug_scorer"]
B7B_RESULTS = [r for r in RESULTS if _scorer_of(r["case_id"]) != "debug_scorer"]
FAST_RESULTS = [r for r in DEBUG_RESULTS if r["pin_fast"]]
SLOW_RESULTS = [r for r in DEBUG_RESULTS if not r["pin_fast"]]


def test_corpus_and_results_are_aligned() -> None:
    corpus_ids = set(CORPUS)
    result_ids = {r["case_id"] for r in RESULTS}
    assert corpus_ids == result_ids
    assert len(RESULTS) == len(CORPUS)
    # internal consistency: recorded `changed` == (old != new)
    for r in RESULTS:
        assert r["changed"] == (r["old"] != r["new"]), r["case_id"]


def test_headline_delta_counts_are_pinned() -> None:
    # Pins the operator-facing numbers so an accidental corpus/scorer drift is
    # caught even before per-row diffing.
    assert len(RESULTS) == 159
    assert sum(1 for r in RESULTS if r["changed"]) == 58
    # B7 debug_scorer package sub-counts (07a20a7c + 8f24679a) — unchanged.
    assert len(DEBUG_RESULTS) == 146
    assert sum(1 for r in DEBUG_RESULTS if r["changed"]) == 50
    sentinel_changed = {
        r["provenance"].split(":", 1)[1].split("/", 1)[0]
        for r in RESULTS
        if r["changed"] and r["provenance"].startswith("sentinel:")
    }
    assert len(sentinel_changed) == 21
    # B7b remainder (SCORE-07/08/09/12) — 13 rows, 8 behavior changes.
    assert len(B7B_RESULTS) == 13
    assert sum(1 for r in B7B_RESULTS if r["changed"]) == 8


@pytest.mark.parametrize("res", FAST_RESULTS, ids=[r["case_id"] for r in FAST_RESULTS])
def test_fast_subset_reproduces_ratified_new(res: dict) -> None:
    """Hard pin: current scorer must reproduce every ratified POST outcome
    (pure in-process scoring only — runs in well under 5s)."""
    row = CORPUS[res["case_id"]]
    assert _outcome(row) == _recorded_new(res["new"])


@pytest.mark.skipif(
    not CODE_EXEC_TMP.is_dir(),
    reason="code_execution rows require the host sandbox dir /mnt/raid0/llm/tmp",
)
@pytest.mark.parametrize("res", SLOW_RESULTS, ids=[r["case_id"] for r in SLOW_RESULTS])
def test_subprocess_and_network_rows_reproduce_ratified_new(res: dict) -> None:
    """code_execution (subprocess) + llm_judge (unreachable-judge) rows. Still
    fast here (~a few subprocess spawns / refused TCP connects), but gated on
    host infra and split out from the always-run fast pin."""
    row = CORPUS[res["case_id"]]
    assert _outcome(row) == _recorded_new(res["new"])


@pytest.mark.parametrize("res", B7B_RESULTS, ids=[r["case_id"] for r in B7B_RESULTS])
def test_b7b_rows_reproduce_ratified_new(res: dict) -> None:
    """Hard pin for the B7b remainder (SCORE-07/08/09/12): the eval_tower rubric
    range-validation, empty-rubric, and code_execution-confidence surfaces must
    still reproduce every ratified POST outcome. Pure in-process — always run."""
    row = CORPUS[res["case_id"]]
    assert _b7b_outcome(row) == _recorded_new(res["new"])
