"""Golden-corpus drift test for the vendored canonical answer_scoring library.

handoffs/active/scoring-infra-standardization.md, 1c-fix (a): the orchestrator
carries a byte-for-byte VENDORED copy of epyc-inference-research's
`scripts/benchmark/answer_scoring.py` at
`scripts/benchmark/answer_scoring_vendored.py` (data-only coupling -- no
runtime cross-repo import). This test is the sync enforcement for that copy:

  1. A sha256 pin on the vendored file itself, so any hand-edit (accidental or
     not) fails loudly instead of silently drifting from what was vendored.
  2. A replay of `tests/fixtures/answer_scoring_golden_corpus.json` (built from
     the canonical library's own regression suite, research's
     `test_answer_scoring.py`) through the vendored copy's `score_response` /
     `score_ordered_subsequence`, asserting every recorded verdict.

If (1) fails: you edited the vendored file. Either revert the edit, or you are
deliberately re-vendoring -- follow the procedure in the header comment of
answer_scoring_vendored.py, then update EXPECTED_VENDORED_SHA256 below to match.

If (2) fails after a legitimate re-vendor: a corpus row's verdict changed
under the new upstream version. That is a SCORING CHANGE to disclose (a
handoff row, operator-visible), not a fixture to quietly update to match.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VENDORED_PATH = REPO_ROOT / "scripts" / "benchmark" / "answer_scoring_vendored.py"
CORPUS_PATH = REPO_ROOT / "tests" / "fixtures" / "answer_scoring_golden_corpus.json"

sys.path.insert(0, str(VENDORED_PATH.parent))

import answer_scoring_vendored as vendored  # noqa: E402

# Recorded at vendor time (2026-08-12) from
# `python3 -c "import hashlib;print(hashlib.sha256(open('scripts/benchmark/answer_scoring_vendored.py','rb').read()).hexdigest())"`.
# Update procedure on a legitimate re-vendor: see the header comment in
# answer_scoring_vendored.py.
# Re-pinned 2026-09-07 (CJ-11): the upstream library gained
# `score_response_or_error`, a three-valued SIBLING of `score_response`. The
# upstream diff is 158 insertions and 0 DELETIONS -- `score_response` is
# byte-identical -- so every golden-corpus verdict below is expected to be
# unchanged, and the replay below is what proves it rather than asserts it.
EXPECTED_VENDORED_SHA256 = (
    "3b59d04efd12755c015b2dd483edaf58617639926c74071f2f4d7fdee032e5e2"
)


def _load_corpus() -> list[dict]:
    data = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    rows = data["rows"]
    assert rows, "golden corpus must not be empty -- an empty corpus vacuously passes"
    return rows


def test_vendored_file_sha256_matches_recorded_hash() -> None:
    """Tripwire: any edit to the vendored file (re-vendor or accidental) must
    be a deliberate, procedure-following change, not a silent drift."""
    actual = hashlib.sha256(VENDORED_PATH.read_bytes()).hexdigest()
    assert actual == EXPECTED_VENDORED_SHA256, (
        f"scripts/benchmark/answer_scoring_vendored.py sha256 changed "
        f"(expected {EXPECTED_VENDORED_SHA256}, got {actual}). "
        "If this is a deliberate re-vendor from epyc-inference-research's "
        "scripts/benchmark/answer_scoring.py, follow the update procedure in "
        "the header comment of answer_scoring_vendored.py: diff the upstream "
        "change, replace the body verbatim, recompute this hash, update "
        "EXPECTED_VENDORED_SHA256 here and the `@<commit>` + source-file-sha256 "
        "in the header, then re-run this test -- if any corpus row's verdict "
        "changed, that is a SCORING CHANGE to disclose, not a fixture to "
        "silently update. If this is an accidental hand-edit, revert it: the "
        "vendored file must stay byte-for-byte identical to its upstream source."
    )


def test_golden_corpus_has_all_three_regression_categories() -> None:
    """The corpus must actually cover what it claims to (bare-letter,
    truncated-boxed, ordered-subsequence) -- a corpus that silently lost a
    category would still "pass" while testing less than it claims."""
    rows = _load_corpus()
    methods = {row["scoring_method"] for row in rows}
    assert "multiple_choice" in methods
    assert "math_numeric" in methods
    assert "ordered_subsequence" in methods
    ids = {row["id"] for row in rows}
    assert "letter_verbose_bare_final_line_reasoning_then_option_word" in ids, (
        "the A4 gpqa bare-letter regression row must be present"
    )
    assert "boxed_takes_last_complete_truncated_trailing" in ids, (
        "the truncated-boxed regression row must be present"
    )


@pytest.mark.parametrize("row", _load_corpus(), ids=lambda row: row["id"])
def test_vendored_copy_matches_golden_corpus_verdict(row: dict) -> None:
    response = row["response"]
    expected = row["expected"]
    scoring_method = row["scoring_method"]
    scoring_config = row.get("scoring_config", {})
    q = {"scoring_method": scoring_method, "scoring_config": scoring_config}

    if "expect_error" in row:
        import builtins

        error_type = getattr(builtins, row["expect_error"])
        with pytest.raises(error_type):
            vendored.score_response(response, expected, q)
        return

    got = vendored.score_response(response, expected, q)
    assert got == row["verdict"], (
        f"corpus row {row['id']!r} (source_test={row.get('source_test')!r}): "
        f"vendored score_response returned {got}, corpus expects {row['verdict']}"
    )


def test_corpus_rows_have_required_fields() -> None:
    """Mutation-guard: a row missing scoring_method or verdict must not
    silently no-op past the parametrized test above."""
    rows = _load_corpus()
    for row in rows:
        assert "id" in row and row["id"]
        assert "response" in row
        assert "expected" in row
        assert "scoring_method" in row
        assert "verdict" in row or "expect_error" in row
