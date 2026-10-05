"""Tests for NIB2-45 Week 2: MindDR pydantic_graph subgraph.

Covers:
  - Planning output parser: happy path, tag filtering, index dedup, clamp.
  - Sub-report parser: fields extracted; evidence lines lifted.
  - Sub-reports → synthesis format renderer.
  - End-to-end graph run with mock LLMs — full success path.
  - Planning failure → End(error) with no DeepSearch invoked.
  - Fan-out parallelism: 5 sub-questions run within a narrow wall time
    when each LLM takes 100ms and max_parallel=5.
  - DeepSearch per-question failure degrades gracefully.
  - Report LLM failure produces an End with success=False.
  - load_minddr_prompts reads the three prompt files from disk.
  - minddr_graph mermaid generation (sanity check on node registration).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.graph.minddr import (
    EVIDENCE_TAGS,
    EvidenceTag,
    MindDRDeps,
    MindDRResult,
    SubQuestion,
    SubReport,
    load_minddr_prompts,
    minddr_graph,
    parse_planning_output,
    parse_sub_report,
    run_minddr,
)
from src.graph.minddr.parsing import format_sub_reports_for_synthesis


# ── parser tests ────────────────────────────────────────────────────

def test_parse_planning_output_happy_path():
    raw = """
1. [WEB] What architectures exist?
2. [BENCHMARK] What are published metrics?
3. [COMPARISON] How do they compare on latency vs quality?
""".strip()
    items = parse_planning_output(raw)
    assert len(items) == 3
    assert items[0].evidence_tag == EvidenceTag.WEB
    assert items[1].evidence_tag == EvidenceTag.BENCHMARK
    assert items[2].evidence_tag == EvidenceTag.COMPARISON


def test_parse_planning_rejects_unknown_tags_and_duplicates():
    raw = """
1. [WEB] Question one.
1. [WEB] Duplicate index should drop.
2. [QUANTUM] Unknown tag should drop.
3. [CITATION] Question three.
4. [DOCS] Question four.
""".strip()
    items = parse_planning_output(raw, min_items=3, max_items=7)
    assert [i.index for i in items] == [1, 3, 4]
    assert all(i.evidence_tag.value in EVIDENCE_TAGS for i in items)


def test_parse_planning_clamps_to_max():
    raw = "\n".join(f"{i}. [WEB] Question {i}." for i in range(1, 11))
    items = parse_planning_output(raw, max_items=5)
    assert len(items) == 5


def test_parse_planning_raises_when_too_few():
    with pytest.raises(ValueError):
        parse_planning_output("1. [WEB] Only one.", min_items=3)


def test_parse_sub_report_extracts_fields_and_evidence():
    sq = SubQuestion(index=1, text="What is X?", evidence_tag=EvidenceTag.WEB)
    raw = """
Thought: time to answer.
## Sub-Report for Q1
- **Sub-question**: What is X?
- **Finding**: X is a technique for Y.
- **Evidence**:
  - [src:https://arxiv.org/abs/1234] X was introduced in 2023
  - [src:doc-42] X outperforms Y by 5%
- **Confidence**: high
- **Gaps**: No benchmark on MoE architectures.
""".strip()
    sr = parse_sub_report(raw, sq)
    assert sr.finding.startswith("X is a technique")
    assert len(sr.evidence) == 2
    assert sr.confidence == "high"
    assert "MoE" in sr.gaps


def test_format_sub_reports_for_synthesis_renders_all():
    reports = [
        SubReport(
            sub_question=SubQuestion(1, "Q1?", EvidenceTag.WEB),
            finding="Finding 1.",
            evidence=["[src:a] claim a"],
            confidence="high",
        ),
        SubReport(
            sub_question=SubQuestion(2, "Q2?", EvidenceTag.BENCHMARK),
            finding="Finding 2.",
            evidence=[],
            confidence="low",
            gaps="unclear",
        ),
    ]
    rendered = format_sub_reports_for_synthesis(reports)
    assert "Sub-Report for Q1" in rendered
    assert "Sub-Report for Q2" in rendered
    assert "Finding 1." in rendered
    assert "no evidence captured" in rendered


# ── end-to-end graph tests ──────────────────────────────────────────

_PLANNING_OUTPUT = """
1. [WEB] What is X?
2. [BENCHMARK] What metrics on X?
3. [COMPARISON] X vs Y tradeoffs?
""".strip()


def _sub_report_for(n: int) -> str:
    return f"""
## Sub-Report for Q{n}
- **Sub-question**: Mock sub-question {n}
- **Finding**: Mock finding for Q{n}.
- **Evidence**:
  - [src:mock-{n}-a] point a
  - [src:mock-{n}-b] point b
- **Confidence**: medium
- **Gaps**:
""".strip()


def _mock_deps(
    planning_return: str = _PLANNING_OUTPUT,
    deep_search_latency: float = 0.0,
    deep_search_fail_on: set[int] | None = None,
    report_raises: bool = False,
    max_parallel: int = 4,
) -> MindDRDeps:
    fail_on = deep_search_fail_on or set()

    async def planning_llm(role: str, content: str) -> str:
        return planning_return

    async def deep_search_llm(role: str, content: str) -> str:
        if deep_search_latency > 0:
            await asyncio.sleep(deep_search_latency)
        # Extract sub_question index from content; very loose because test-only.
        for n in (1, 2, 3, 4, 5, 6, 7):
            if f"Mock sub-question {n}" in content or f"Q{n}" in content:
                if n in fail_on:
                    raise RuntimeError(f"forced failure on Q{n}")
                return _sub_report_for(n)
        # Fallback: build from the injected sub_question text.
        return "## Sub-Report for Q?\n- **Finding**: mock finding"

    async def report_llm(role: str, content: str) -> str:
        if report_raises:
            raise RuntimeError("forced report failure")
        return "# Outline\n- s1\n\n# s1\nMock synthesized report."

    return MindDRDeps(
        planning_prompt="PLAN:\n{prompt}",
        deep_search_prompt="DS:\n{sub_question}\n{evidence_tag}\n{planning_context}",
        report_prompt="REP:\n{prompt}\n{sub_reports}",
        planning_llm=planning_llm,
        deep_search_llm=deep_search_llm,
        report_llm=report_llm,
        max_parallel=max_parallel,
    )


def test_end_to_end_success_path():
    deps = _mock_deps()

    # Patch the deep_search prompt so the mock can match each sub-question.
    async def deep_search_llm(role: str, content: str) -> str:
        # We get the content with {sub_question} already substituted — pull the
        # index from the planning output (Q1/Q2/Q3 sub_reports are indexed by
        # the sub-question's own number).
        for n in (1, 2, 3, 4, 5):
            marker = f"sub-question {n}"  # not actually in content — we use index match below
            if marker in content:
                return _sub_report_for(n)
        # Fall back: the content contains the sub-question text; use a simple
        # ordinal counter stored on the function.
        deep_search_llm.counter += 1  # type: ignore
        return _sub_report_for(deep_search_llm.counter)  # type: ignore

    deep_search_llm.counter = 0  # type: ignore
    deps.deep_search_llm = deep_search_llm  # type: ignore

    result: MindDRResult = asyncio.run(run_minddr("what is X?", deps))
    assert result.success is True
    assert "Mock synthesized report" in result.report
    assert len(result.sub_reports) == 3
    assert len(result.sub_questions) == 3


def test_planning_failure_terminates_before_fan_out():
    async def bad_planning(role, content):
        return "no valid lines here"

    deps = _mock_deps()
    deps.planning_llm = bad_planning  # type: ignore

    result = asyncio.run(run_minddr("bad prompt", deps))
    assert result.success is False
    assert "planning_parse_error" in (result.error or "")
    assert result.sub_reports == []


def test_planning_llm_exception_captured():
    async def boom(role, content):
        raise RuntimeError("boom")

    deps = _mock_deps()
    deps.planning_llm = boom  # type: ignore

    result = asyncio.run(run_minddr("prompt", deps))
    assert result.success is False
    assert "planning_llm_error" in (result.error or "")


def test_fan_out_runs_in_parallel():
    """5 sub-questions × 100ms each = ~500ms serial, ~100ms parallel."""
    planning_5 = "\n".join(f"{i}. [WEB] Q{i}?" for i in range(1, 6))

    async def planning_llm(role, content):
        return planning_5

    call_log: list[float] = []

    async def deep_search_llm(role, content):
        call_log.append(time.time())
        await asyncio.sleep(0.1)
        # Counter-based sub-report id.
        deep_search_llm.n += 1  # type: ignore
        return _sub_report_for(deep_search_llm.n)  # type: ignore

    deep_search_llm.n = 0  # type: ignore

    async def report_llm(role, content):
        return "final"

    deps = MindDRDeps(
        planning_prompt="{prompt}",
        deep_search_prompt="{sub_question}{evidence_tag}{planning_context}",
        report_prompt="{prompt}{sub_reports}",
        planning_llm=planning_llm,
        deep_search_llm=deep_search_llm,
        report_llm=report_llm,
        max_parallel=5,
    )

    t0 = time.time()
    result = asyncio.run(run_minddr("p", deps))
    elapsed = time.time() - t0

    assert result.success is True
    assert len(result.sub_reports) == 5
    # Should finish in well under 500ms (serial bound) — 300ms is generous.
    assert elapsed < 0.3, f"Fan-out not parallel enough: {elapsed:.3f}s"


def test_deep_search_per_question_failure_degrades_gracefully():
    deps = _mock_deps(deep_search_fail_on={2})

    async def deep_search_llm(role, content):
        # Identify sub-question by a marker we embed in the content via the
        # mock prompt template ("DS:\n{sub_question}\n..."). The prompt text
        # contains the original sub-question string which we can fuzzy-match.
        deep_search_llm.n += 1  # type: ignore
        if deep_search_llm.n == 2:  # type: ignore
            raise RuntimeError("forced failure on Q2")
        return _sub_report_for(deep_search_llm.n)  # type: ignore

    deep_search_llm.n = 0  # type: ignore
    deps.deep_search_llm = deep_search_llm  # type: ignore

    result = asyncio.run(run_minddr("p", deps))
    assert result.success is True  # report still runs
    # One sub-report has empty finding + deep_search_error gap.
    failures = [sr for sr in result.sub_reports if "deep_search_error" in sr.gaps]
    assert len(failures) == 1


def test_report_llm_failure_produces_unsuccessful_result():
    deps = _mock_deps(report_raises=True)

    async def deep_search_llm(role, content):
        deep_search_llm.n += 1  # type: ignore
        return _sub_report_for(deep_search_llm.n)  # type: ignore

    deep_search_llm.n = 0  # type: ignore
    deps.deep_search_llm = deep_search_llm  # type: ignore

    result = asyncio.run(run_minddr("p", deps))
    assert result.success is False
    assert "report_llm_error" in (result.error or "")
    assert len(result.sub_reports) == 3  # sub-reports still captured


# ── integration helpers ─────────────────────────────────────────────

def test_load_minddr_prompts_reads_from_disk():
    planning, deep_search, report = load_minddr_prompts()
    assert "MindDR" in planning
    assert "NIB2-45" in deep_search
    assert "MindDR" in report
    assert "{prompt}" in planning
    assert "{sub_question}" in deep_search
    assert "{sub_reports}" in report


def test_minddr_graph_mermaid_generates():
    mermaid = minddr_graph.mermaid_code(start_node="PlanningNode")
    assert "PlanningNode" in mermaid
    assert "DeepSearchFanOutNode" in mermaid
    assert "ReportSynthesisNode" in mermaid
