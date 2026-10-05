"""Regression tests for token-accounting integrity (2026-06-01 audit).

The Pareto/HV speed objective is derived from `primitives.total_tokens_generated`
(repl_executor reports it as the response `tokens_generated`, EvalTower turns it
into t/s). So model-decode tokens must be counted EXACTLY once, and tool output
must NEVER inflate it. These tests lock in the three audit invariants:

  1. The backend's exact completion count is not double-counted by the
     primitives-layer char-estimate (the bug that ~2x-inflated the speed objective).
  2. The char-estimate is still used when the backend did NOT count (mock / cache
     hit) — the guard suppresses the *double* add, not all accounting.
  3. EvalTower/Pareto speed depends only on model `tokens_generated`, never on
     tool-call counts / tool output.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "autopilot"))

from src.llm_primitives.primitives import LLMPrimitives  # noqa: E402
from eval_tower import EvalTower, QuestionResult  # noqa: E402


def _real_primitives() -> LLMPrimitives:
    p = LLMPrimitives(mock_mode=True)
    p.mock_mode = False  # force the real (_real_call) branch in _llm_call_impl
    return p


def test_backend_tokens_not_double_counted():
    """Real path: the backend's exact count is recorded ONCE; the char-estimate
    is not re-added on top (the 2026-06-01 double-count bug)."""
    p = _real_primitives()
    BACKEND_N = 37
    long_text = "word " * 500  # would estimate to hundreds of tokens if re-added

    def fake_real_call(prompt, role, *a, **k):
        # Mimic inference.py:772 — backend adds its exact completion count.
        p.total_tokens_generated += BACKEND_N
        return long_text

    p._real_call = fake_real_call
    before = p.total_tokens_generated
    p._llm_call_impl("solve x", role="frontdoor")
    added = p.total_tokens_generated - before
    assert added == BACKEND_N, f"expected exactly {BACKEND_N} (backend, once), got {added}"


def test_estimate_used_when_backend_absent():
    """Cache-hit / mock path (backend does not count): the char-estimate IS used,
    so tokens are not silently dropped — the guard only suppresses the DOUBLE add."""
    p = _real_primitives()

    def fake_real_call_no_count(prompt, role, *a, **k):
        return "a plausible model answer with several words"

    p._real_call = fake_real_call_no_count
    before = p.total_tokens_generated
    p._llm_call_impl("q", role="frontdoor")
    assert p.total_tokens_generated > before, "estimate must be used when backend didn't count"


def test_eval_speed_ignores_tool_output():
    """EvalTower/Pareto speed depends only on model tokens_generated; tool-call
    counts (a proxy for tool output) never change speed or the tokens figure."""
    t = EvalTower()

    def q(tools: int) -> QuestionResult:
        return QuestionResult(
            question_id="x", suite="general", prompt="p", expected="e",
            answer="a", correct=True, tokens_generated=100, elapsed_s=2.0,
            tools_used=tools, tools_called=["Bash"] * tools,
        )

    no_tools = [q(0), q(0), q(0)]
    many_tools = [q(9), q(9), q(9)]
    er_a = t._aggregate(no_tools, tier=1)
    er_b = t._aggregate(many_tools, tier=1)
    assert er_a.speed == er_b.speed, "speed must not depend on tool count"
    assert er_a.details["tokens_generated"] == er_b.details["tokens_generated"]
    # And the speed numerator is genuinely model tokens, not tool-inflated.
    assert er_b.details["tokens_generated"] == 300


def test_tool_helpfulness_is_marginal_not_raw_rate():
    """tool_helpfulness = P(correct|tools) - P(correct|no tools); NaN on thin data."""
    t = EvalTower()

    def q(tools: int, correct: bool) -> QuestionResult:
        return QuestionResult(
            question_id="x", suite="general", prompt="p", expected="e",
            answer="a", correct=correct, tokens_generated=100, elapsed_s=2.0,
            tools_used=tools, tools_called=["Bash"] * tools,
        )

    # tools help: 3/3 correct with tools, 0/3 with no tools -> helpfulness = 1.0
    helps = [q(2, True), q(2, True), q(2, True), q(0, False), q(0, False), q(0, False)]
    assert t._aggregate(helps, tier=1).tool_helpfulness == 1.0
    # thin data (only 1 tool arm) -> NaN, cannot be chased
    thin = [q(2, True), q(0, False), q(0, True)]
    assert math.isnan(t._aggregate(thin, tier=1).tool_helpfulness)


def test_tool_helpfulness_is_per_suite_not_cross_suite_contaminated():
    """Cross-suite composition (trivial no-tool base suite + an all-tool suite)
    must yield NaN, not a misleading negative. The 2026-06-04 cutover saw −0.4
    because easy base suites (all correct, no tools) anchored the without-tools
    arm against the harder tool suite. Helpfulness is now computed within-suite."""
    t = EvalTower()

    def q(suite: str, tools: int, correct: bool) -> QuestionResult:
        return QuestionResult(
            question_id="x", suite=suite, prompt="p", expected="e",
            answer="a", correct=correct, tokens_generated=100, elapsed_s=2.0,
            tools_used=tools, tools_called=["get_eval_secret"] * tools,
        )

    # base: all no-tool + all correct (trivial). tool_use: all-tool, mixed.
    # NEITHER suite has both arms -> NaN (NOT a negative cross-suite delta).
    contaminated = (
        [q("base", 0, True) for _ in range(4)]
        + [q("tool_use", 1, True), q("tool_use", 1, True), q("tool_use", 1, False)]
    )
    er = t._aggregate(contaminated, tier=1)
    assert math.isnan(er.tool_helpfulness), er.tool_helpfulness
    assert er.per_suite_tool_helpfulness == {}

    # Within one suite with both arms (>= _MIN_ARM each): delta IS computed and
    # surfaced per-suite.
    within = [
        q("tool_use", 1, True), q("tool_use", 1, True), q("tool_use", 1, True),
        q("tool_use", 0, False), q("tool_use", 0, False), q("tool_use", 0, False),
    ]
    er2 = t._aggregate(within, tier=1)
    assert er2.per_suite_tool_helpfulness.get("tool_use") == 1.0
    assert er2.tool_helpfulness == 1.0
