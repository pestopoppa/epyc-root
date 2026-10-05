"""The rebuilt debugbench oracle: score the CHANGE, not the reproduction.

Origin: epyc-root `artifacts/audit/debugbench-oracle-vacuity-20260812.md`. The suite
shipped two oracles and both were useless in opposite directions. For cpp/java,
`expected` was a 100-character PREFIX of the reference solution scored `substring` —
boilerplate already present in the buggy code, so echoing the input PASSED (measured
through the real scorer over the upstream corpus: 57.0% of cpp, 49.0% of java rows).
For python, `code_execution` with no `test_code` and no `entry_point`, a configuration
`_score_code_execution` answers with an unconditional False — the reference solution
itself FAILED on 100% of python rows.

Widening the prefix is not a fix and is not tested here: the defect is containment in
the input, not length (`test_core_pool_vacuous_oracle.py` pins that separately).

Every test below asserts one of the two directions that matter:
  * an answer that changes NOTHING must not pass, and
  * the known-correct reference solution must pass.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "dbo_under_test", REPO / "scripts" / "benchmark" / "debugbench_oracle.py")
dbo = importlib.util.module_from_spec(_spec)
sys.modules["dbo_under_test"] = dbo
_spec.loader.exec_module(dbo)

_scorer_spec = importlib.util.spec_from_file_location(
    "dbg_scorer_under_test", REPO / "scripts" / "benchmark" / "debug_scorer.py")
scorer = importlib.util.module_from_spec(_scorer_spec)
sys.modules["dbg_scorer_under_test"] = scorer
_scorer_spec.loader.exec_module(scorer)

_cvs_spec = importlib.util.spec_from_file_location(
    "cvs_for_oracle", REPO / "scripts" / "autopilot" / "core_v2_select.py")
cvs = importlib.util.module_from_spec(_cvs_spec)
sys.modules["cvs_for_oracle"] = cvs
_cvs_spec.loader.exec_module(cvs)

_coding_spec = importlib.util.spec_from_file_location(
    "coding_adapters_under_test",
    REPO / "scripts" / "benchmark" / "dataset_adapter_modules" / "coding.py",
    submodule_search_locations=[
        str(REPO / "scripts" / "benchmark" / "dataset_adapter_modules")],
)
sys.path[:0] = [str(REPO / "scripts" / "benchmark")]
coding = importlib.util.module_from_spec(_coding_spec)
sys.modules["coding_adapters_under_test"] = coding
_coding_spec.loader.exec_module(coding)


# A LeetCode-shaped pair: one off-by-one in a loop bound, one wrong return.
BUGGY = """\
class Solution {
    public int longestCycle(int[] edges) {
        int ans = -1;
        for (int i = 0; i <= edges.length; i++) {
            ans = Math.max(ans, walk(edges, i));
        }
        return ans;
    }
}"""

SOLUTION = """\
class Solution {
    public int longestCycle(int[] edges) {
        int ans = -1;
        for (int i = 0; i < edges.length; i++) {
            ans = Math.max(ans, walk(edges, i));
        }
        return ans;
    }
}"""

PROMPT = f"## Buggy Code\n```java\n{BUGGY}\n```\nFix the bug."


def _oracle(buggy: str = BUGGY, solution: str = SOLUTION):
    built = dbo.build_oracle(buggy, solution)
    assert built is not None, "fixture must be buildable or the test proves nothing"
    return built


def _score(answer: str, oracle) -> bool:
    return scorer.score_answer(answer, "", "programmatic", oracle)


# ── the two directions ───────────────────────────────────────────────────


def test_echoing_the_buggy_code_fails() -> None:
    """THE decisive test. Under the old oracle this exact answer scored a PASS."""
    assert _score(BUGGY, _oracle()) is False


def test_echoing_the_whole_prompt_fails() -> None:
    """A model that parrots its input, fenced block and all, still changed nothing."""
    assert _score(PROMPT, _oracle()) is False


def test_the_reference_solution_passes() -> None:
    """The other direction: an oracle the known-correct answer fails is equally useless."""
    assert _score(SOLUTION, _oracle()) is True


def test_the_reference_solution_passes_inside_a_fenced_block() -> None:
    assert _score(f"Here you go:\n```java\n{SOLUTION}\n```", _oracle()) is True


def test_reformatting_the_correct_answer_still_passes() -> None:
    """Whitespace is not the thing under test; a differently-formatted fix is a fix."""
    reformatted = SOLUTION.replace("i < edges.length", "i<edges.length").replace(
        "    ", "        ")
    assert _score(reformatted, _oracle()) is True


def test_a_fix_that_extends_a_forbidden_line_passes() -> None:
    """Why `forbidden` is matched per-LINE and never as a substring.

    Buggy `return idx;` is a substring of corrected `return idx + 1;`. Substring
    matching on the forbidden side would fail every correct answer on rows of this
    shape — the over-strict failure mode, as useless as the vacuous one.
    """
    buggy = "int f() {\n    int idx = compute();\n    return idx;\n}"
    solution = "int f() {\n    int idx = compute();\n    return idx + 1;\n}"
    oracle = _oracle(buggy, solution)
    assert "return idx;" in oracle["forbidden_lines"]
    assert _score(solution, oracle) is True
    assert _score(buggy, oracle) is False


def test_a_half_fix_that_leaves_a_broken_line_in_place_fails() -> None:
    """Multi-bug rows: fixing one of two is not fixing the bug."""
    buggy = "int f(int n) {\n    int a = n + 1;\n    int b = n - 2;\n    return a * b;\n}"
    solution = "int f(int n) {\n    int a = n + 2;\n    int b = n - 3;\n    return a * b;\n}"
    oracle = _oracle(buggy, solution)
    half = "int f(int n) {\n    int a = n + 2;\n    int b = n - 2;\n    return a * b;\n}"
    assert _score(solution, oracle) is True
    assert _score(half, oracle) is False


def test_an_answer_that_merely_deletes_the_broken_line_fails() -> None:
    """The only test where the REQUIRED side is load-bearing.

    Mutation-tested alongside its twin below: with `required_lines` ignored, every
    other test still passed, because the echo answers all carry a forbidden line.
    Deleting the offending statement removes the forbidden line without repairing
    anything — a degenerate answer that a forbidden-only oracle would reward.
    """
    answer = "\n".join(
        line for line in SOLUTION.splitlines() if "for (int i" not in line)
    oracle = _oracle()
    assert not any(bad.strip() in answer for bad in oracle["forbidden_lines"])
    assert _score(answer, oracle) is False


def test_an_answer_that_keeps_the_broken_line_alongside_the_fix_fails() -> None:
    """The only test where the FORBIDDEN side is load-bearing — and it must exist.

    Mutation-tested: with `forbidden_lines` ignored by the scorer, every other test
    in this file still passed, because the required side alone already rejects a
    verbatim echo. That made the forbidden side unpinned, which is how a check
    survives being deleted. This answer contains every required line, so only the
    forbidden side can see that the broken statement is still in the program.
    """
    answer = SOLUTION.replace(
        "        for (int i = 0; i < edges.length; i++) {",
        "        for (int i = 0; i <= edges.length; i++) {\n"
        "        for (int i = 0; i < edges.length; i++) {",
    )
    oracle = _oracle()
    assert all(line.strip() in answer for line in oracle["required_lines"])
    assert _score(answer, oracle) is False


def test_an_answer_that_quotes_the_bug_in_one_block_and_fixes_it_in_another_passes() -> None:
    """Blocks are scored independently, so showing the before/after is not punished."""
    answer = f"Before:\n```java\n{BUGGY}\n```\nAfter:\n```java\n{SOLUTION}\n```"
    assert _score(answer, _oracle()) is True


# ── construction of the oracle ───────────────────────────────────────────


def test_required_lines_come_from_the_solution_and_forbidden_from_the_buggy_code() -> None:
    required, forbidden = dbo.patch_sides(BUGGY, SOLUTION)
    assert required == ["for (int i = 0; i < edges.length; i++) {"]
    assert forbidden == ["for (int i = 0; i <= edges.length; i++) {"]


def test_comments_are_not_part_of_the_oracle() -> None:
    """Requiring a model to reproduce the reference's prose measures prose."""
    buggy = "int f() {\n    // helper\n    return 1;\n}"
    solution = "int f() {\n    // recompute the helper carefully\n    return 2;\n}"
    required, forbidden = dbo.patch_sides(buggy, solution)
    assert required == ["return 2;"]
    assert forbidden == ["return 1;"]


def test_brace_only_lines_are_not_part_of_the_oracle() -> None:
    """Pinning a bare `}` would make the oracle a brace counter."""
    buggy = "int f() {\n    return 1;\n  }\n}"
    solution = "int f() {\n    return 2;\n}\n"
    required, forbidden = dbo.patch_sides(buggy, solution)
    assert required == ["return 2;"]
    assert forbidden == ["return 1;"]


def test_a_patch_that_rewrites_too_much_is_not_scored() -> None:
    """Above the cap the oracle asks 'did you write THIS implementation' — drop it."""
    buggy = "int f() {\n    undefinedHelper();\n}"
    solution = "int f() {\n" + "".join(
        f"    int v{i} = compute({i});\n" for i in range(10)) + "    return v0;\n}"
    assert dbo.build_oracle(buggy, solution, max_required=4) is None
    assert dbo.build_oracle(buggy, solution, max_required=20) is not None


def test_an_empty_oracle_fails_closed() -> None:
    """No oracle is not a free pass — same rule `_score_substring` applies to an empty needle."""
    empty = {"verifier": "code_patch", "required_lines": [], "forbidden_lines": []}
    assert _score(SOLUTION, empty) is False


# ── the build gate, which is the actual remediation ──────────────────────


def test_build_validated_oracle_emits_a_row_that_discriminates() -> None:
    oracle, diag = dbo.build_validated_oracle(
        prompt=PROMPT, buggy_code=BUGGY, solution=SOLUTION, language="java")
    assert oracle is not None
    assert diag["reason"] == "ok"
    assert diag["any_echo_passes"] is False
    assert diag["all_correct_pass"] is True


def test_build_validated_oracle_refuses_a_row_the_input_already_satisfies() -> None:
    """The gate is not decorative: it rejects 20 real upstream rows of this shape.

    Upstream's `illegal comment` subtype injects the bug by COMMENTING OUT a correct
    line. Comments are excluded from both sides of the patch (they are prose), so
    nothing lands in `forbidden_lines`, and the required line's text is still there
    in the buggy code inside the comment — echo would pass. Whitespace-free
    containment cannot see the difference, so the row is dropped rather than shipped.
    """
    buggy = "class S {\n    /*int v = compute(a);*/\n    int r = v + 1;\n}"
    solution = "class S {\n    int v = compute(a);\n    int r = v + 1;\n}"
    candidate = dbo.build_oracle(buggy, solution)
    assert candidate["forbidden_lines"] == []
    oracle, diag = dbo.build_validated_oracle(
        prompt=f"```\n{buggy}\n```", buggy_code=buggy, solution=solution, language="cpp")
    assert oracle is None
    assert diag["reason"] == "failed_validation"
    assert diag["any_echo_passes"] is True


def test_build_validated_oracle_refuses_a_row_with_no_patch_at_all() -> None:
    oracle, diag = dbo.build_validated_oracle(
        prompt="x", buggy_code=SOLUTION, solution=SOLUTION, language="java")
    assert oracle is None
    assert diag["reason"] == "no_buildable_patch"


# ── integration with the shipped pool guards ─────────────────────────────


def test_the_old_prefix_shape_is_flagged_by_the_pool_vacuity_guard() -> None:
    """Control. Without this the next test could pass by examining nothing."""
    old_row = {
        "id": "debugbench_x_java", "suite": "debugbench", "scoring_method": "substring",
        "expected": SOLUTION[:100], "prompt": PROMPT, "buggy_code": BUGGY,
    }
    hits = cvs.vacuous_rows([old_row])
    assert [h["severity"] for h in hits] == ["structural"]


def test_the_rebuilt_expected_is_not_input_contained_even_under_substring_scoring() -> None:
    """`expected` is now a SOLUTION line absent from the buggy code.

    Asserted with `scoring_method` forced to substring on purpose: the real row is
    `programmatic`, which `vacuous_rows` skips by design, and a guard that skips a
    row proves nothing about it.
    """
    row = coding.DebugBenchAdapter()._row_to_prompt(0, _upstream_row())
    forced = dict(row, scoring_method="substring")
    assert cvs.vacuous_rows([forced]) == []


# ── the adapter that produced the defect ─────────────────────────────────


def _upstream_row(language: str = "java") -> dict:
    return {
        "question": "Return the length of the longest cycle.",
        "buggy_code": BUGGY,
        "solution": SOLUTION,
        "bug_explanation": "loop bound is off by one",
        "examples": [],
        "constraints": "",
        "language": language,
        "level": "medium",
        "slug": "longest-cycle-in-a-graph",
        "category": "logic error",
    }


def test_the_adapter_emits_the_diff_oracle_not_a_solution_prefix() -> None:
    row = coding.DebugBenchAdapter()._row_to_prompt(0, _upstream_row())
    assert row["scoring_method"] == "programmatic"
    assert row["scoring_config"]["verifier"] == "code_patch"
    assert row["expected"] != SOLUTION[:100]
    assert row["metadata"]["oracle"] == "code_patch_diff_v1"


def test_an_adapter_row_is_scored_correctly_end_to_end() -> None:
    """The row as the pool would carry it, through `score_answer` as the tower calls it."""
    row = coding.DebugBenchAdapter()._row_to_prompt(0, _upstream_row())
    verdict = scorer.score_answer
    assert verdict(BUGGY, row["expected"], row["scoring_method"], row["scoring_config"]) is False
    assert verdict(SOLUTION, row["expected"], row["scoring_method"], row["scoring_config"]) is True


def test_python_rows_get_a_real_oracle_instead_of_an_always_false_one() -> None:
    """Pins the second defect: `code_execution` with no test_code can never pass.

    1,414 upstream python rows shipped that way, so the whole python third of the
    suite scored 0 regardless of the answer.
    """
    old_config = {"language": "python", "timeout": 30}
    assert scorer.score_answer(SOLUTION, SOLUTION[:100], "code_execution", old_config) is False

    row = coding.DebugBenchAdapter()._row_to_prompt(0, _upstream_row("python3"))
    assert row["scoring_method"] == "programmatic"
    assert scorer.score_answer(
        SOLUTION, row["expected"], row["scoring_method"], row["scoring_config"]) is True


def test_the_adapter_no_longer_truncates_the_buggy_code() -> None:
    """90 upstream rows had NO broken line inside the old 1000-character cut."""
    long_buggy = BUGGY.replace(
        "int ans = -1;", "int ans = -1;\n" + "        int pad = 0;\n" * 90)
    upstream = dict(_upstream_row(), buggy_code=long_buggy)
    row = coding.DebugBenchAdapter()._row_to_prompt(0, upstream)
    assert len(long_buggy) > 1000
    assert long_buggy in row["prompt"]


def test_the_adapter_drops_a_row_whose_oracle_cannot_be_validated() -> None:
    upstream = dict(_upstream_row(), solution=BUGGY)
    assert coding.DebugBenchAdapter()._row_to_prompt(0, upstream) == {}


def test_live_pool_report_measures_the_oracle_the_pool_actually_carries(tmp_path) -> None:
    """The shipped rows are their own instrument and must be measured as shipped.

    The pool's python rows were retargeted `code_execution` -> `substring` inside the
    pool file on 2026-08-04, so the adapter code is not evidence about what has been
    scored since. This row is the real shape: `expected` is a 100-character prefix of
    the solution, and the prompt contains it.
    """
    upstream = [_upstream_row()]
    upstream[0]["language"] = "java"
    shipped = {
        "id": "debugbench_longest-cycle-in-a-graph_java",
        "suite": "debugbench",
        "prompt": PROMPT,
        "expected": SOLUTION[:100],
        "scoring_method": "substring",
        "scoring_config": {"case_sensitive": True},
        "metadata": {"language": "java"},
    }
    pool = tmp_path / "pool.jsonl"
    pool.write_text(json.dumps(shipped) + "\n")

    measured = dbo.live_pool_report(pool, upstream)
    assert measured["rows"] == 1
    assert measured["echo_the_prompt_pass_rate_pct"] == 100.0
    assert measured["reference_solution_matched"] == 1


def test_a_prose_answer_naming_the_corrected_line_passes_documented_limitation() -> None:
    """Honest pin of a known weakness, not an endorsement.

    With no fenced block the whole answer is the candidate, so an answer that states
    the corrected statement in prose satisfies the oracle without emitting a program.
    It is a real answer to a real question, and no line-level oracle over this dataset
    can distinguish it — upstream ships no tests to execute. Recorded so a future
    reader sees it was measured rather than missed.
    """
    answer = "Change the loop bound to `for (int i = 0; i < edges.length; i++) {`."
    assert _score(answer, _oracle()) is True
