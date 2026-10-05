#!/usr/bin/env python3
"""Unit tests for REPL combined operations (_CombinedOpsMixin)."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.repl_environment import REPLEnvironment

AP26_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "ap26"
    / "metadata_first_workspace_trace.json"
)


@pytest.fixture(autouse=True)
def _clear_feature_flag():
    """Ensure REPL_COMBINED_OPS is unset before/after each test."""
    old = os.environ.pop("REPL_COMBINED_OPS", None)
    yield
    if old is not None:
        os.environ["REPL_COMBINED_OPS"] = old
    else:
        os.environ.pop("REPL_COMBINED_OPS", None)


def _make_repl_with_registry(use_toon=False):
    """Create a REPLEnvironment with a mocked tool_registry."""
    from src.repl_environment.types import REPLConfig

    config = REPLConfig(use_toon_encoding=use_toon)
    registry = MagicMock()
    repl = REPLEnvironment(
        context="test", tool_registry=registry, role="worker_general", config=config,
    )
    return repl, registry


def _make_repl_with_llm(use_toon=False):
    """Create a REPLEnvironment with mocked llm_primitives."""
    from src.repl_environment.types import REPLConfig

    config = REPLConfig(use_toon_encoding=use_toon)
    llm = MagicMock()
    repl = REPLEnvironment(
        context="test", llm_primitives=llm, role="worker_general", config=config,
    )
    return repl, llm


def _make_repl(use_toon=False):
    """Create a plain REPLEnvironment with TOON disabled for JSON tests."""
    from src.repl_environment.types import REPLConfig

    config = REPLConfig(use_toon_encoding=use_toon)
    return REPLEnvironment(context="test", config=config)


class TestBatchWebSearchDisabled:
    """Tests for batch_web_search when feature flag is off."""

    def test_batch_web_search_disabled(self):
        """Flag off returns feature disabled message."""
        repl = REPLEnvironment(context="test")
        result = repl.execute('artifacts["r"] = batch_web_search(["q1", "q2"])')
        assert result.error is None
        assert "Combined ops disabled" in repl.artifacts["r"]

    def test_batch_web_search_disabled_explicit_off(self):
        """Explicit '0' value keeps feature disabled."""
        os.environ["REPL_COMBINED_OPS"] = "0"
        repl = REPLEnvironment(context="test")
        result = repl.execute('artifacts["r"] = batch_web_search(["q1"])')
        assert result.error is None
        assert "Combined ops disabled" in repl.artifacts["r"]


class TestBatchWebSearchEnabled:
    """Tests for batch_web_search when feature flag is on."""

    def test_batch_web_search_enabled(self):
        """Flag on, mock tool registry, returns consolidated results."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, registry = _make_repl_with_registry(use_toon=False)

        registry.invoke.return_value = [{"title": "Result", "url": "https://example.com"}]

        result = repl._batch_web_search(["python asyncio", "rust tokio"], max_results=2)
        parsed = json.loads(result)

        assert parsed["operation"] == "batch_web_search"
        assert parsed["query_count"] == 2
        assert "python asyncio" in parsed["results"]
        assert "rust tokio" in parsed["results"]
        assert registry.invoke.call_count == 2

    def test_batch_web_search_caps_at_5(self):
        """More than 5 queries gets capped to 5."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, registry = _make_repl_with_registry(use_toon=False)

        registry.invoke.return_value = []
        queries = [f"query_{i}" for i in range(8)]

        result = repl._batch_web_search(queries)
        parsed = json.loads(result)

        assert parsed["query_count"] == 5
        assert parsed["capped"] is True
        assert registry.invoke.call_count == 5

    def test_batch_web_search_empty_queries(self):
        """Empty query list returns error."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl()
        result = repl._batch_web_search([])
        assert "[ERROR: No queries provided]" in result

    def test_batch_web_search_no_registry(self):
        """No tool registry returns error."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl()
        result = repl._batch_web_search(["query"])
        assert "No tool registry" in result

    def test_batch_web_search_handles_tool_error(self):
        """Individual tool errors are captured per-query."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, registry = _make_repl_with_registry(use_toon=False)

        registry.invoke.side_effect = [
            [{"title": "OK"}],
            RuntimeError("search failed"),
        ]

        result = repl._batch_web_search(["good_query", "bad_query"])
        parsed = json.loads(result)

        assert "good_query" in parsed["results"]
        assert "ERROR" in parsed["results"]["bad_query"]

    def test_batch_web_search_toon_encoding(self):
        """TOON encoding produces text format."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, registry = _make_repl_with_registry(use_toon=True)

        registry.invoke.return_value = [{"title": "Result"}]

        result = repl._batch_web_search(["test query"])
        assert "=== batch_web_search" in result
        assert '--- "test query" ---' in result


class TestSearchAndVerify:
    """Tests for search_and_verify."""

    def test_search_and_verify_disabled(self):
        """Flag off returns feature disabled message."""
        repl = _make_repl()
        result = repl._search_and_verify("test query")
        assert "Combined ops disabled" in result

    def test_search_and_verify_enabled(self):
        """Returns both web and wikipedia results."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, registry = _make_repl_with_registry(use_toon=False)

        def invoke_side_effect(tool_name, role, **kwargs):
            if tool_name == "web_search":
                return [{"title": "Web Result", "url": "https://example.com"}]
            elif tool_name == "search_wikipedia":
                return {"summary": "Wikipedia summary text"}
            return None

        registry.invoke.side_effect = invoke_side_effect

        result = repl._search_and_verify("quantum computing", max_results=2)
        parsed = json.loads(result)

        assert parsed["operation"] == "search_and_verify"
        assert parsed["query"] == "quantum computing"
        assert parsed["web_results"] is not None
        assert parsed["wikipedia"] is not None
        assert registry.invoke.call_count == 2

    def test_search_and_verify_no_registry(self):
        """No tool registry returns error."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl()
        result = repl._search_and_verify("test")
        assert "No tool registry" in result

    def test_search_and_verify_toon_encoding(self):
        """TOON encoding produces labeled sections."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, registry = _make_repl_with_registry(use_toon=True)

        registry.invoke.return_value = "some result"

        result = repl._search_and_verify("test")
        assert "## Web Results" in result
        assert "## Wikipedia" in result


class TestPeekGrep:
    """Tests for peek_grep."""

    def test_peek_grep_disabled(self):
        """Flag off returns feature disabled message."""
        repl = _make_repl()
        result = repl._peek_grep("/tmp/test.txt", "pattern")
        assert "Combined ops disabled" in result

    def test_peek_grep_enabled(self):
        """Reads file, applies pattern, returns matches with context."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl(use_toon=False)

        content = "line 1\nline 2\nfoo target bar\nline 4\nline 5\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", dir="/tmp", delete=False
        ) as f:
            f.write(content)
            tmp_path = f.name

        try:
            result = repl._peek_grep(tmp_path, "target", context_lines=1)
            parsed = json.loads(result)

            assert parsed["operation"] == "peek_grep"
            assert parsed["match_count"] == 1
            assert len(parsed["matches"]) == 1
            # The match block should contain the target line and context
            assert "target" in parsed["matches"][0]
            assert ">>>" in parsed["matches"][0]
        finally:
            os.unlink(tmp_path)

    def test_peek_grep_no_matches(self):
        """Pattern not found returns empty matches message."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", dir="/tmp", delete=False
        ) as f:
            f.write("nothing interesting here\n")
            tmp_path = f.name

        try:
            result = repl._peek_grep(tmp_path, "nonexistent_pattern")
            assert "No matches" in result
        finally:
            os.unlink(tmp_path)

    def test_peek_grep_file_not_found(self):
        """Missing file returns error."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl()
        result = repl._peek_grep("/tmp/does_not_exist_xyz.txt", "pattern")
        assert "File not found" in result

    def test_peek_grep_invalid_regex(self):
        """Invalid regex returns error."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", dir="/tmp", delete=False
        ) as f:
            f.write("content\n")
            tmp_path = f.name

        try:
            result = repl._peek_grep(tmp_path, "[invalid")
            assert "Invalid regex" in result
        finally:
            os.unlink(tmp_path)

    def test_peek_grep_toon_encoding(self):
        """TOON encoding produces text format."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl(use_toon=True)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", dir="/tmp", delete=False
        ) as f:
            f.write("hello world\n")
            tmp_path = f.name

        try:
            result = repl._peek_grep(tmp_path, "hello")
            assert "=== peek_grep:" in result
            assert "1 matches" in result
        finally:
            os.unlink(tmp_path)


class TestBatchLlmQueryDisabled:
    """Tests for batch_llm_query when feature flag is off."""

    def test_batch_llm_query_disabled(self):
        """Flag off returns feature disabled message."""
        repl = _make_repl()
        result = repl._batch_llm_query(["summarize this", "translate that"])
        assert "Combined ops disabled" in result

    def test_batch_llm_query_disabled_explicit_off(self):
        """Explicit '0' value keeps feature disabled."""
        os.environ["REPL_COMBINED_OPS"] = "0"
        repl = _make_repl()
        result = repl._batch_llm_query(["prompt"])
        assert "Combined ops disabled" in result


class TestBatchLlmQueryEnabled:
    """Tests for batch_llm_query when feature flag is on."""

    def test_batch_llm_query_enabled(self):
        """Flag on, mock LLM, returns structured results."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, llm = _make_repl_with_llm(use_toon=False)

        llm.llm_batch.return_value = ["Summary of doc A", "Translation of doc B"]

        result = repl._batch_llm_query(["summarize doc A", "translate doc B"], role="worker")
        parsed = json.loads(result)

        assert parsed["operation"] == "batch_llm_query"
        assert parsed["prompt_count"] == 2
        assert parsed["role"] == "worker"
        assert len(parsed["results"]) == 2
        assert parsed["results"][0]["response"] == "Summary of doc A"
        assert parsed["results"][1]["response"] == "Translation of doc B"
        llm.llm_batch.assert_called_once_with(
            ["summarize doc A", "translate doc B"], role="worker", persona=None,
            json_schema=None,
        )

    def test_batch_llm_query_caps_at_5(self):
        """More than 5 prompts gets capped to 5."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, llm = _make_repl_with_llm(use_toon=False)

        llm.llm_batch.return_value = [f"response_{i}" for i in range(5)]
        prompts = [f"prompt_{i}" for i in range(8)]

        result = repl._batch_llm_query(prompts)
        parsed = json.loads(result)

        assert parsed["prompt_count"] == 5
        assert parsed["capped"] is True
        # Verify only 5 prompts were passed to the backend
        call_args = llm.llm_batch.call_args
        assert len(call_args[0][0]) == 5

    def test_batch_llm_query_empty_prompts(self):
        """Empty prompt list returns error."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, _ = _make_repl_with_llm()
        result = repl._batch_llm_query([])
        assert "[ERROR: No prompts provided]" in result

    def test_batch_llm_query_no_llm_primitives(self):
        """No LLM primitives returns error."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl()
        result = repl._batch_llm_query(["prompt"])
        assert "No LLM primitives" in result

    def test_batch_llm_query_with_persona(self):
        """Persona is passed through to llm_batch."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, llm = _make_repl_with_llm(use_toon=False)

        llm.llm_batch.return_value = ["response"]

        result = repl._batch_llm_query(["prompt"], role="coder", persona="analyst")
        parsed = json.loads(result)

        assert parsed["persona"] == "analyst"
        assert parsed["role"] == "coder"
        llm.llm_batch.assert_called_once_with(
            ["prompt"], role="coder", persona="analyst", json_schema=None,
        )

    def test_batch_llm_query_schema_validates_response(self):
        """Schema mode parses valid child JSON into structured response."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, llm = _make_repl_with_llm(use_toon=False)
        schema = {
            "type": "object",
            "properties": {"answer": {"type": "integer"}},
            "required": ["answer"],
        }

        llm.llm_batch.return_value = ['{"answer": 42}']

        result = repl._batch_llm_query(["return the answer"], schema=schema)
        parsed = json.loads(result)

        assert parsed["schema_validation"] is True
        assert parsed["results"][0]["valid"] is True
        assert parsed["results"][0]["response"] == {"answer": 42}
        assert parsed["results"][0]["raw_response"] == '{"answer": 42}'
        assert parsed["results"][0]["attempts"] == 1
        call_prompts = llm.llm_batch.call_args.args[0]
        assert "Return only a JSON value" in call_prompts[0]
        assert "return the answer" in call_prompts[0]
        # TD-21.22a: the schema now ALSO reaches the wire via json_schema=,
        # not just the prose preamble asserted above.
        assert llm.llm_batch.call_args.kwargs["json_schema"] == schema

    def test_batch_llm_query_repair_completer_forwards_json_schema(self):
        """TD-21.22a: the repair/extraction turn's own llm_batch call also
        carries json_schema=, not just the retained prose preamble."""
        from src.structured_output.repair import reset_counts_for_tests

        reset_counts_for_tests()
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, llm = _make_repl_with_llm(use_toon=False)
        schema = {
            "type": "object",
            "properties": {"answer": {"type": "integer"}},
            "required": ["answer"],
        }
        llm.llm_batch.side_effect = [
            ["not json, but the answer is 7"],
            ['{"answer": 7}'],
        ]

        result = repl._batch_llm_query(["return the answer"], schema=schema)
        parsed = json.loads(result)

        assert parsed["results"][0]["valid"] is True
        assert llm.llm_batch.call_count == 2
        # Call 0: the initial batch carries the schema verbatim.
        assert llm.llm_batch.call_args_list[0].kwargs["json_schema"] == schema
        # Call 1: the repair completer's own llm_batch call also carries a
        # wire schema (parse_with_repair closes it with
        # additionalProperties=False before the extraction turn, so it is
        # the same shape, not byte-identical to the original).
        repair_schema = llm.llm_batch.call_args_list[1].kwargs["json_schema"]
        assert repair_schema is not None
        assert repair_schema["type"] == "object"
        assert repair_schema["properties"] == schema["properties"]

    def test_batch_llm_query_schema_repairs_invalid_response_without_full_recall(self):
        """TD-21.22: an invalid-but-recoverable child reply is fixed by ONE
        repair turn (fish, then one constrained extraction call back to the
        role via ``llm_batch``) rather than the old full re-call retry loop.
        ``attempts`` stays at 1 because the full-recall loop never runs."""
        from src.structured_output.repair import (
            STRUCTURED_OUTPUT_REPAIR_COUNTS,
            reset_counts_for_tests,
        )

        reset_counts_for_tests()
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, llm = _make_repl_with_llm(use_toon=False)
        schema = {
            "type": "object",
            "properties": {"answer": {"type": "integer"}},
            "required": ["answer"],
        }
        llm.llm_batch.side_effect = [
            ["not json, but the answer is 7"],
            ['{"answer": 7}'],
        ]

        result = repl._batch_llm_query(["return the answer"], schema=schema)
        parsed = json.loads(result)

        assert parsed["results"][0]["valid"] is True
        assert parsed["results"][0]["response"] == {"answer": 7}
        # The full re-call retry loop never ran -- repair recovered it first.
        assert parsed["results"][0]["attempts"] == 1
        assert llm.llm_batch.call_count == 2
        extraction_prompt = llm.llm_batch.call_args_list[1].args[0][0]
        assert "not json" in extraction_prompt
        assert STRUCTURED_OUTPUT_REPAIR_COUNTS.get(("repl_combined_ops", "repaired")) == 1

    def test_batch_llm_query_schema_reports_exhausted_retry(self):
        """Schema mode reports invalid entries instead of silently returning
        junk, after BOTH the repair turn and the full re-call retry loop miss."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, llm = _make_repl_with_llm(use_toon=False)
        schema = {
            "type": "object",
            "properties": {"answer": {"type": "integer"}},
            "required": ["answer"],
        }
        llm.llm_batch.side_effect = [
            ["not json"],
            ["still not json"],
            ['{"answer": "wrong"}'],
        ]

        result = repl._batch_llm_query(["return the answer"], schema=schema)
        parsed = json.loads(result)

        assert parsed["results"][0]["valid"] is False
        assert parsed["results"][0]["response"] == '{"answer": "wrong"}'
        assert parsed["results"][0]["raw_response"] == '{"answer": "wrong"}'
        assert "not of type" in parsed["results"][0]["error"]
        assert parsed["results"][0]["attempts"] == 2
        assert llm.llm_batch.call_count == 3

    def test_batch_llm_query_schema_rejects_non_dict_schema(self):
        """Schema argument must be a JSON Schema dict."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, _ = _make_repl_with_llm(use_toon=False)

        result = repl._batch_llm_query(["prompt"], schema="not a dict")

        assert "schema must be a JSON Schema dict" in result

    def test_batch_llm_query_toon_encoding(self):
        """TOON encoding produces text format with headers."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, llm = _make_repl_with_llm(use_toon=True)

        llm.llm_batch.return_value = ["The answer is 42"]

        result = repl._batch_llm_query(["what is the meaning?"], role="worker")
        assert "=== batch_llm_query" in result
        assert "role=worker" in result
        assert "The answer is 42" in result
        assert '--- prompt 1:' in result

    def test_batch_llm_query_increments_exploration(self):
        """Exploration counter is incremented."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl, llm = _make_repl_with_llm()

        llm.llm_batch.return_value = ["response"]
        initial = repl._exploration_calls

        repl._batch_llm_query(["prompt"])

        assert repl._exploration_calls == initial + 1


class TestWorkspaceScanDisabled:
    """Tests for workspace_scan when feature flag is off."""

    def test_workspace_scan_disabled(self):
        """Flag off returns feature disabled message."""
        repl = _make_repl()
        result = repl._workspace_scan()
        assert "Combined ops disabled" in result


class TestWorkspaceScanEnabled:
    """Tests for workspace_scan when feature flag is on."""

    def test_workspace_scan_no_history(self):
        """Empty frecency store returns informative message."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl(use_toon=False)

        # Use in-memory DB so it's empty
        from src.repl_environment.file_recency import FrecencyStore
        repl._frecency_store = FrecencyStore(db_path=":memory:")

        result = repl._workspace_scan()
        assert "No file access history" in result

    def test_workspace_scan_returns_ranked_files(self):
        """Returns frecency-ranked file list."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl(use_toon=False)

        from src.repl_environment.file_recency import FrecencyStore
        store = FrecencyStore(db_path=":memory:")
        # Record accesses to build history
        store.record_access("/src/main.py")
        store.record_access("/src/main.py")  # accessed twice → higher score
        store.record_access("/src/utils.py")
        repl._frecency_store = store

        result = repl._workspace_scan(limit=10)
        parsed = json.loads(result)

        assert parsed["operation"] == "workspace_scan"
        assert parsed["file_count"] == 2
        # main.py accessed twice, should rank first
        assert parsed["files"][0]["path"] == "/src/main.py"
        assert parsed["files"][0]["frecency_score"] > parsed["files"][1]["frecency_score"]

    def test_workspace_scan_query_reranks(self):
        """Query re-ranks results by filename relevance."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl(use_toon=False)

        from src.repl_environment.file_recency import FrecencyStore
        store = FrecencyStore(db_path=":memory:")
        # utils.py has more accesses but query matches router.py
        for _ in range(5):
            store.record_access("/src/utils.py")
        store.record_access("/src/router.py")
        repl._frecency_store = store

        result = repl._workspace_scan(query="router", limit=10)
        parsed = json.loads(result)

        # router.py should rank first due to query relevance despite fewer accesses
        assert parsed["files"][0]["path"] == "/src/router.py"

    def test_workspace_scan_ap26_fixture_metadata_first_win_condition(self):
        """AP-26 staging fixture: query scan beats high-frecency distractors."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl(use_toon=False)

        from src.repl_environment.file_recency import FrecencyStore

        fixture = json.loads(AP26_FIXTURE.read_text(encoding="utf-8"))
        store = FrecencyStore(db_path=":memory:")
        for item in fixture["access_history"]:
            for _ in range(item["access_count"]):
                store.record_access(item["path"])
        repl._frecency_store = store

        result = repl._workspace_scan(
            query=fixture["query"],
            limit=fixture["win_condition"]["max_scan_files"],
        )
        parsed = json.loads(result)
        paths = [entry["path"] for entry in parsed["files"]]

        assert parsed["query"] == fixture["query"]
        assert parsed["file_count"] == fixture["win_condition"]["max_scan_files"]
        assert paths[0] == fixture["expected_first_path"]
        assert all(path in paths for path in fixture["expected_required_paths"])
        assert not any(path in paths for path in fixture["distractor_paths"])

    def test_workspace_scan_toon_encoding(self):
        """TOON encoding produces text format with scores."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl(use_toon=True)

        from src.repl_environment.file_recency import FrecencyStore
        store = FrecencyStore(db_path=":memory:")
        store.record_access("/src/main.py")
        repl._frecency_store = store

        result = repl._workspace_scan()
        assert "=== workspace_scan" in result
        assert "/src/main.py" in result

    def test_workspace_scan_increments_exploration(self):
        """Exploration counter is incremented."""
        os.environ["REPL_COMBINED_OPS"] = "1"
        repl = _make_repl()

        from src.repl_environment.file_recency import FrecencyStore
        repl._frecency_store = FrecencyStore(db_path=":memory:")
        initial = repl._exploration_calls

        repl._workspace_scan()

        assert repl._exploration_calls == initial + 1
