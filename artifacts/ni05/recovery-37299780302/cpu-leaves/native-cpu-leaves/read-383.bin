"""GPQA rows with no gold answer must not MANUFACTURE one.

Before CJ-8, ``GPQAAdapter._row_to_prompt`` computed

    correct_idx = choices.index(correct_answer) if correct_answer in choices else 0

so a row whose ``Correct Answer`` field was empty silently produced
``expected="A"``. ``choices`` is built from ``correct_answer`` itself (filtered
for truthiness), so that ``else 0`` branch fires for exactly one reason: THERE IS
NO GOLD. Every model answering B/C/D on such a row was recorded wrong against an
invented oracle.

An invented reference is worse than a mislabelled verdict: a mislabelled verdict
can be re-read afterwards, an invented gold cannot be told apart from a real one.

These tests pin: gold present -> a real letter and NO coverage annotation; gold
absent -> no ``expected`` at all, an ``out-of-coverage``/``no_reference`` verdict
on the row, the row still PRESENT in the corpus (never silently dropped, which
would manufacture coverage), and the row refused by the scoring gate.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.benchmark.dataset_adapter_modules.general import GPQAAdapter  # noqa: E402

_GVV_PATH = REPO_ROOT / "scripts" / "benchmark" / "gate_verdict_vocab.py"
_SPEC = importlib.util.spec_from_file_location("gate_verdict_vocab", _GVV_PATH)
gvv = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gvv)


def _adapter(row: dict) -> GPQAAdapter:
    a = GPQAAdapter()
    a._dataset = [row]  # _get_tier_for_index reads the loaded dataset
    return a


def _row(correct: str) -> dict:
    return {
        "Question": "Which nuclide has the longer half-life?",
        "Correct Answer": correct,
        "Incorrect Answer 1": "wrong-one",
        "Incorrect Answer 2": "wrong-two",
        "Incorrect Answer 3": "wrong-three",
        "Subdomain": "Physics",
    }


# --------------------------------------------------------------------------- #
# Positive: a row WITH gold still scores exactly as before
# --------------------------------------------------------------------------- #
def test_row_with_gold_yields_the_letter_of_the_correct_choice() -> None:
    row = _row("the-right-answer")
    item = _adapter(row)._row_to_prompt(0, row)

    assert item["expected"] in ("A", "B", "C", "D")
    assert "gate_verdict" not in item, (
        "a DECIDED item must not carry a cause code — a cause on a decided row "
        "means the caller does not know which verdict it emitted"
    )
    # The letter must actually point at the gold text in the shuffled prompt,
    # not merely be a plausible letter.
    offered = {
        line.split(") ", 1)[0]: line.split(") ", 1)[1]
        for line in item["prompt"].splitlines()
        if len(line) > 2 and line[1:3] == ") "
    }
    assert offered[item["expected"]] == "the-right-answer"


# --------------------------------------------------------------------------- #
# The conversion: no gold -> out-of-coverage, NOT a fabricated "A"
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("missing", ["", None])
def test_row_without_gold_is_out_of_coverage_not_letter_a(missing) -> None:
    row = _row(missing)
    item = _adapter(row)._row_to_prompt(0, row)

    # The regression this test exists for: the old code emitted "A".
    assert item["expected"] != "A", (
        "a row with no gold must not be given a fabricated reference"
    )
    assert item["expected"] is None

    verdict = item["gate_verdict"]
    assert verdict["verdict"] == gvv.VERDICT_OUT_OF_COVERAGE
    assert verdict["cause"] == gvv.CAUSE_NO_REFERENCE
    assert verdict["verdict"] != gvv.VERDICT_FAIL, (
        "no-gold is an UNDECIDED item, never a decision against the model"
    )
    assert verdict["cause_means"], "an undecided count with no remedy is unusable"


def test_row_without_gold_is_still_emitted_never_dropped() -> None:
    """Dropping the row would shrink the denominator, which is how a suite
    manufactures coverage. It must survive as an undecided item."""
    item = _adapter(_row(""))._row_to_prompt(0, _row(""))
    assert item["id"] == "gpqa_Physics_0000"
    assert item["prompt"], "the item still exists on the asserted surface"


def test_out_of_coverage_row_is_refused_by_the_scoring_gate() -> None:
    """The row must be excised from scoring, not graded against nothing."""
    from scripts.autopilot.eval_tower import _is_scoreable_question

    with_gold = _adapter(_row("x"))._row_to_prompt(0, _row("the-right-answer"))
    without_gold = _adapter(_row(""))._row_to_prompt(0, _row(""))

    # Mutation guard: the predicate must SEPARATE the two. A predicate that
    # refused both (or accepted both) would make the assertion below vacuous.
    assert _is_scoreable_question(with_gold) is True
    assert _is_scoreable_question(without_gold) is False


def test_gold_absent_and_gold_present_do_not_collide() -> None:
    """Mutation test: remove the signal under test (the gold string) and the
    outcome must CHANGE. If both rows produced the same `expected`, the fix
    would be indistinguishable from the fabrication it replaced."""
    present = _adapter(_row("x"))._row_to_prompt(0, _row("the-right-answer"))
    absent = _adapter(_row(""))._row_to_prompt(0, _row(""))
    assert present["expected"] != absent["expected"]
    assert ("gate_verdict" in absent) and ("gate_verdict" not in present)
