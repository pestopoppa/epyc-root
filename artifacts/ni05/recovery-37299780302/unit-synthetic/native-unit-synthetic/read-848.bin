"""Tests for TD-21.26: env_synth TaskSynthesizer / ETDAgent repair.

Before: `TaskSynthesizer._parse` used a bare `json.loads`, no fence
tolerance; a fenced or trailing-prose reply failed the WHOLE attempt and the
caller regenerated FROM ZERO (`max_retries+1` full model calls) instead of
recovering the one reply it already had. `ETDAgent.discover` did the same,
returning `[]` with no counter and no recovery attempt.

After: both fish first via the shared `src.structured_output.repair`
(fence-aware, string-aware balanced-bracket fallback) and, on a miss, spend
ONE repair turn against the SAME injected `llm` callable before falling back
to (task_synthesizer) a from-zero regeneration or (etd_agent) a typed `[]`.

Covers: happy path costs zero repair calls; a fenced/prefixed reply is fished
without any repair call; an unparseable reply is repaired via one extra
`llm` call; a still-unparseable reply is a typed miss (verified via the
shared `STRUCTURED_OUTPUT_REPAIR_COUNTS`), never a fabricated task/candidate.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.autopilot.species.env_synth import (  # noqa: E402
    DifficultyBand,
    ETDAgent,
    MCPToolEntry,
    MCPToolRegistry,
    TaskSynthesizer,
)
from src.structured_output.repair import (  # noqa: E402
    STRUCTURED_OUTPUT_REPAIR_COUNTS,
    reset_counts_for_tests,
)

_TASK_SITE = "env_synth.task_synthesizer"
_ETD_SITE = "env_synth.etd_agent.discover"


def _mk_tool(tool_id: str) -> MCPToolEntry:
    return MCPToolEntry(
        tool_id=tool_id,
        name=f"tool {tool_id}",
        description="test tool",
        endpoint=f"http://example.com/{tool_id}/mcp",
        discovered_via="etd_web",
        environment_id="env_x",
    )


_VALID_TASK_JSON = json.dumps(
    {
        "prompt": "Using the tools, compute the answer.",
        "verifier": {"type": "exact_match", "reference": "42"},
        "ground_truth_hint": "42",
        "metadata": {"topic": "arithmetic"},
    }
)


class TestTaskSynthesizerHappyPathUnchanged:
    def setup_method(self):
        reset_counts_for_tests()

    def test_clean_json_costs_zero_llm_calls_beyond_generation(self):
        calls = {"n": 0}

        async def llm(system, user):
            calls["n"] += 1
            return _VALID_TASK_JSON

        synth = TaskSynthesizer(llm=llm)
        task = asyncio.run(synth.synthesize("env_x", [_mk_tool("t0")], DifficultyBand.EASY))
        assert task is not None
        assert task.prompt.startswith("Using the tools")
        assert calls["n"] == 1  # only the one generation call, no repair turn
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get((_TASK_SITE, "repaired"), 0) == 0

    def test_fenced_reply_is_fished_without_a_repair_call(self):
        calls = {"n": 0}

        async def llm(system, user):
            calls["n"] += 1
            return f"Here is the task:\n```json\n{_VALID_TASK_JSON}\n```\nHope that helps!"

        synth = TaskSynthesizer(llm=llm)
        task = asyncio.run(synth.synthesize("env_x", [_mk_tool("t0")], DifficultyBand.EASY))
        assert task is not None
        assert calls["n"] == 1  # fish recovered it -- no repair turn needed
        # The pure-fish path (`_parse` inside `_parse_with_repair`) short-
        # circuits before `parse_with_repair_async` is ever called, so it
        # costs zero telemetry too -- not just zero LLM calls.
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get((_TASK_SITE, "parsed"), 0) == 0
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get((_TASK_SITE, "repaired"), 0) == 0


class TestTaskSynthesizerRepairRecoversWithoutFromZeroRegeneration:
    def setup_method(self):
        reset_counts_for_tests()

    def test_unparseable_reply_is_repaired_in_place(self):
        calls: list[str] = []

        async def llm(system, user):
            calls.append(user)
            if len(calls) == 1:
                # First (generation) call: unusable prose, no JSON at all --
                # but it already states everything the repair turn must copy
                # (TD-21.34 require_evidence: prompt/reference/hint/topic
                # must come from THIS reply; only verifier.type is exempt).
                return (
                    "I think a good task would be to have the model use the "
                    "tools: 'Using the tools, compute the answer.' The "
                    "correct answer is 42, and this is an arithmetic "
                    "exercise, but I can't format this as JSON right now."
                )
            # Second (repair) call: the injected LLM is asked to re-express
            # its own reply into the schema.
            return _VALID_TASK_JSON

        synth = TaskSynthesizer(llm=llm, max_retries=2)
        task = asyncio.run(synth.synthesize("env_x", [_mk_tool("t0")], DifficultyBand.EASY))
        assert task is not None
        assert task.ground_truth_hint == "42"
        # Recovered on attempt 1 via repair -- no from-zero regeneration
        # (a 3rd call would mean the outer retry loop regenerated instead).
        assert len(calls) == 2
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[(_TASK_SITE, "repaired")] == 1

    def test_repair_failure_falls_back_to_retry_not_a_fabricated_task(self):
        async def always_bad(system, user):
            return "definitely not JSON, ever"

        synth = TaskSynthesizer(llm=always_bad, max_retries=1)
        task = asyncio.run(synth.synthesize("env_x", [_mk_tool("t0")], DifficultyBand.EASY))
        # Still None -- never a fabricated SynthesizedTask.
        assert task is None
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[(_TASK_SITE, "failed")] >= 1


class TestEtdAgentHappyPathAndRepair:
    def setup_method(self):
        reset_counts_for_tests()

    def _agent(self, llm, tmp_path):
        reg = MCPToolRegistry(tmp_path / "reg.jsonl")

        async def web_search(query, n):
            return []

        async def fetch_url(url):
            return ""

        async def tool_enum(endpoint):
            return []

        return ETDAgent(
            llm=llm, web_search=web_search, fetch_url=fetch_url,
            tool_enum=tool_enum, registry=reg,
        )

    def test_clean_json_list_zero_repair_calls(self, tmp_path):
        async def llm(system, user):
            return json.dumps([{"name": "MathEnv", "description": "math", "search_queries": ["m"]}])

        agent = self._agent(llm, tmp_path)
        discoveries = asyncio.run(agent.discover("math"))
        assert len(discoveries) == 1
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get((_ETD_SITE, "repaired"), 0) == 0

    def test_unparseable_reply_is_repaired_via_the_same_llm(self, tmp_path):
        calls = {"n": 0}

        async def llm(system, user):
            calls["n"] += 1
            if calls["n"] == 1:
                # TD-21.34 require_evidence: name/description must come from
                # THIS reply for the repair turn to copy faithfully.
                return (
                    "Sure, I found an environment called MathEnv that's "
                    "great for math problems, but I can't format this as "
                    "JSON right now."
                )
            return json.dumps([{"name": "MathEnv", "description": "math", "search_queries": ["m"]}])

        agent = self._agent(llm, tmp_path)
        discoveries = asyncio.run(agent.discover("math"))
        assert len(discoveries) == 1
        assert discoveries[0].theme == "math"
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[(_ETD_SITE, "repaired")] == 1

    def test_unrecoverable_reply_is_typed_failure_not_silent_success(self, tmp_path):
        async def always_bad(system, user):
            return "no list here at all"

        agent = self._agent(always_bad, tmp_path)
        discoveries = asyncio.run(agent.discover("math"))
        assert discoveries == []
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS[(_ETD_SITE, "failed")] == 1
