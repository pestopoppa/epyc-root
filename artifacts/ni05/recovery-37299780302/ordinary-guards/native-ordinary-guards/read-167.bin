"""Unit tests for NextPLAID code_search / doc_search REPL tools.

Phase 4: Tests cover dual-client routing (code→:8088, docs→:8089),
fallback behavior (docs container down → code container), and
both-down graceful degradation.
"""

from __future__ import annotations

import json
import subprocess
import sys
import types
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Inject fake next_plaid_client modules so that
#   `from next_plaid_client.models import SearchParams`
# succeeds without the real package installed.
# ---------------------------------------------------------------------------

@dataclass
class _FakeSearchParams:
    """Stand-in for next_plaid_client.models.SearchParams."""
    top_k: int = 5

_fake_npc = types.ModuleType("next_plaid_client")
_fake_npc_models = types.ModuleType("next_plaid_client.models")
_fake_npc_models.SearchParams = _FakeSearchParams  # type: ignore[attr-defined]
_fake_npc.models = _fake_npc_models  # type: ignore[attr-defined]

# Register in sys.modules so `from next_plaid_client.models import SearchParams` works
sys.modules.setdefault("next_plaid_client", _fake_npc)
sys.modules.setdefault("next_plaid_client.models", _fake_npc_models)


# ---------------------------------------------------------------------------
# Minimal fakes for the NextPLAID client models
# ---------------------------------------------------------------------------

@dataclass
class FakeQueryResult:
    query_id: int
    document_ids: list[int]
    scores: list[float]
    metadata: list[dict[str, Any]]


@dataclass
class FakeSearchResult:
    results: list[FakeQueryResult]
    num_queries: int


@dataclass
class FakeHealthResponse:
    status: str = "healthy"
    version: str = "1.0.4"
    loaded_indices: int = 2
    index_dir: str = "/data/indices"
    memory_usage_bytes: int = 100_000_000
    indices: list[str] | None = None


class FakeNextPlaidClient:
    """Mock NextPLAID client returning deterministic results."""

    def __init__(self, url: str):
        self.url = url
        self._health_calls = 0
        self._search_calls: list[tuple[str, list[str]]] = []

    def health(self) -> FakeHealthResponse:
        self._health_calls += 1
        return FakeHealthResponse()

    def search_with_encoding(self, index, queries, params=None):
        self._search_calls.append((index, queries))
        return FakeSearchResult(
            results=[
                FakeQueryResult(
                    query_id=0,
                    document_ids=[42, 7],
                    scores=[8.5, 5.2],
                    metadata=[
                        {
                            "file": "src/escalation.py",
                            "start_line": "10",
                            "end_line": "25",
                            "unit_type": "class",
                            "unit_name": "EscalationPolicy",
                            "signature": "class EscalationPolicy:",
                            "has_docstring": "True",
                        },
                        {
                            "file": "tests/test_escalation.py",
                            "start_line": "1",
                            "end_line": "15",
                            "unit_type": "function",
                            "unit_name": "test_escalation_basic",
                            "signature": "def test_escalation_basic():",
                            "has_docstring": "False",
                        },
                    ],
                )
            ],
            num_queries=1,
        )


class FakeUnhealthyClient:
    """Mock NextPLAID client that reports unhealthy."""

    def __init__(self, url: str):
        self.url = url

    def health(self) -> FakeHealthResponse:
        return FakeHealthResponse(status="unhealthy")


class FakeConnectionErrorClient:
    """Mock NextPLAID client that raises on health check."""

    def __init__(self, url: str):
        self.url = url

    def health(self):
        raise ConnectionError(f"Cannot reach {self.url}")


# ---------------------------------------------------------------------------
# Fixture: build a minimal REPLEnvironment with code_search wired up
# ---------------------------------------------------------------------------

@pytest.fixture
def repl(monkeypatch):
    """Create a REPLEnvironment with mocked NextPLAID client.

    Default-disables colgrep (REPL_COLGREP=0) so legacy tests get NextPLAID-shape
    behavior. ColGREP-specific tests override per-test via monkeypatch.setenv.
    """
    from src.repl_environment.environment import REPLEnvironment

    monkeypatch.setenv("REPL_COLGREP", "0")
    env = REPLEnvironment(context="test context", role="frontdoor")
    # Reset any cached clients from previous tests
    env._code_client = None
    env._docs_client = None
    return env


# ---------------------------------------------------------------------------
# Tests: Basic Functionality
# ---------------------------------------------------------------------------

class TestCodeSearchMixin:
    """Tests for _CodeSearchMixin integrated via REPLEnvironment."""

    def test_code_search_registered_in_globals(self, repl):
        """code_search and doc_search are available as sandbox globals."""
        assert "code_search" in repl._globals
        assert "doc_search" in repl._globals

    @patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client")
    def test_code_search_happy_path(self, mock_get_client, repl):
        """code_search returns structured results from NextPLAID."""
        fake_client = FakeNextPlaidClient("http://localhost:8088")
        mock_get_client.return_value = fake_client

        raw = repl._code_search("escalation policy")
        # Strip tool output wrapper if present
        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)

        assert result["index"] == "code"
        assert result["query"] == "escalation policy"
        assert len(result["results"]) == 2
        assert result["results"][0]["file"] == "src/escalation.py"
        assert result["results"][0]["lines"] == "10-25"
        assert result["results"][0]["score"] == 8.5

    @patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client")
    def test_doc_search_uses_docs_index(self, mock_get_client, repl):
        """doc_search routes to the 'docs' index."""
        fake_client = FakeNextPlaidClient("http://localhost:8089")
        mock_get_client.return_value = fake_client

        repl._doc_search("benchmark results")

        assert len(fake_client._search_calls) == 1
        assert fake_client._search_calls[0][0] == "docs"

    @patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client")
    def test_code_search_respects_limit(self, mock_get_client, repl):
        """Limit parameter caps number of results."""
        fake_client = FakeNextPlaidClient("http://localhost:8088")
        mock_get_client.return_value = fake_client

        raw = repl._code_search("test", limit=1)
        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)

        assert len(result["results"]) == 1

    def test_code_search_unavailable_graceful(self, repl):
        """When NextPLAID is down, returns empty results without error."""
        repl._code_client = None
        repl._docs_client = None

        with patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client", return_value=None):
            raw = repl._code_search("anything")
            output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
            result = json.loads(output)

            assert result["results"] == []
            assert "error" in result

    @patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client")
    def test_code_search_invalid_index(self, mock_get_client, repl):
        """Invalid index name returns error."""
        raw = repl._nextplaid_search("test", index="invalid", limit=5)
        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)

        assert result["results"] == []
        assert "Invalid index" in result["error"]

    @patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client")
    def test_code_search_increments_exploration_calls(self, mock_get_client, repl):
        """Each search increments the exploration counter."""
        fake_client = FakeNextPlaidClient("http://localhost:8088")
        mock_get_client.return_value = fake_client

        before = repl._exploration_calls
        repl._code_search("test query")
        assert repl._exploration_calls == before + 1

    @patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client")
    def test_code_search_tracks_tool_output(self, mock_get_client, repl):
        """Results are appended to artifacts._tool_outputs."""
        fake_client = FakeNextPlaidClient("http://localhost:8088")
        mock_get_client.return_value = fake_client

        repl._code_search("test")
        outputs = repl.artifacts.get("_tool_outputs", [])
        assert len(outputs) >= 1

    @patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client")
    def test_code_search_tracks_research_context(self, mock_get_client, repl):
        """Search results create research context nodes."""
        fake_client = FakeNextPlaidClient("http://localhost:8088")
        mock_get_client.return_value = fake_client

        repl._code_search("escalation logic")
        assert repl._last_research_node is not None
        assert repl._last_research_node.startswith("CS")

    @patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client")
    def test_doc_search_tracks_research_context_ds_prefix(self, mock_get_client, repl):
        """doc_search nodes use DS prefix in research context."""
        fake_client = FakeNextPlaidClient("http://localhost:8089")
        mock_get_client.return_value = fake_client

        repl._doc_search("model quirks")
        assert repl._last_research_node is not None
        assert repl._last_research_node.startswith("DS")

    @patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client")
    def test_search_exception_returns_error(self, mock_get_client, repl):
        """If search raises, error is captured gracefully."""
        mock_client = MagicMock()
        mock_client.search_with_encoding.side_effect = RuntimeError("connection reset")
        mock_get_client.return_value = mock_client

        raw = repl._code_search("crash test")
        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)

        assert result["results"] == []
        assert "connection reset" in result["error"]


# ---------------------------------------------------------------------------
# Tests: AST Metadata in Results (Phase 5)
# ---------------------------------------------------------------------------

class TestASTMetadata:
    """Tests for Phase 5 AST-chunked metadata in search results."""

    @patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client")
    def test_results_include_unit_field(self, mock_get_client, repl):
        """Results include unit field when AST metadata is present."""
        fake_client = FakeNextPlaidClient("http://localhost:8088")
        mock_get_client.return_value = fake_client

        raw = repl._code_search("escalation policy")
        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)

        assert len(result["results"]) == 2
        assert result["results"][0]["unit"] == "class:EscalationPolicy"
        assert result["results"][0]["signature"] == "class EscalationPolicy:"
        assert result["results"][1]["unit"] == "function:test_escalation_basic"

    @patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client")
    def test_results_omit_unit_when_no_metadata(self, mock_get_client, repl):
        """Results omit unit field when AST metadata is absent."""
        mock_client = MagicMock()
        mock_client.search_with_encoding.return_value = FakeSearchResult(
            results=[
                FakeQueryResult(
                    query_id=0,
                    document_ids=[1],
                    scores=[5.0],
                    metadata=[{"file": "README.md", "start_line": "1", "end_line": "10"}],
                )
            ],
            num_queries=1,
        )
        mock_get_client.return_value = mock_client

        raw = repl._code_search("readme")
        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)

        assert len(result["results"]) == 1
        assert "unit" not in result["results"][0]
        assert "signature" not in result["results"][0]


# ---------------------------------------------------------------------------
# Tests: Dual-Client Routing (Phase 4)
# ---------------------------------------------------------------------------

class TestDualClientRouting:
    """Tests for Phase 4 dual-container routing logic."""

    @patch("src.repl_environment.code_search._CodeSearchMixin._init_nextplaid_client")
    def test_code_search_uses_code_client(self, mock_init, repl):
        """code_search() routes to :8088 code client."""
        code_client = FakeNextPlaidClient("http://localhost:8088")
        mock_init.return_value = code_client

        repl._code_search("def retrieve")

        # _init_nextplaid_client called with code URL
        mock_init.assert_called_with("http://localhost:8088")
        assert len(code_client._search_calls) == 1
        assert code_client._search_calls[0][0] == "code"

    @patch("src.repl_environment.code_search._CodeSearchMixin._init_nextplaid_client")
    def test_doc_search_uses_docs_client(self, mock_init, repl):
        """doc_search() routes to :8089 docs client."""
        docs_client = FakeNextPlaidClient("http://localhost:8089")
        mock_init.return_value = docs_client

        repl._doc_search("escalation policy")

        # _init_nextplaid_client called with docs URL
        mock_init.assert_called_with("http://localhost:8089")
        assert len(docs_client._search_calls) == 1
        assert docs_client._search_calls[0][0] == "docs"

    @patch("src.repl_environment.code_search._CodeSearchMixin._init_nextplaid_client")
    def test_docs_fallback_to_code_client(self, mock_init, repl):
        """When docs container (:8089) is down, doc_search falls back to code container (:8088)."""
        code_client = FakeNextPlaidClient("http://localhost:8088")

        def init_side_effect(url):
            if url == "http://localhost:8089":
                return None  # Docs container down
            return code_client

        mock_init.side_effect = init_side_effect

        raw = repl._doc_search("escalation policy")
        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)

        # Should still return results (from code client fallback)
        assert len(result["results"]) == 2
        assert result["index"] == "docs"
        # Code client was used as fallback
        assert len(code_client._search_calls) == 1

    @patch("src.repl_environment.code_search._CodeSearchMixin._init_nextplaid_client")
    def test_both_containers_down_graceful(self, mock_init, repl):
        """When both containers are down, returns graceful error."""
        mock_init.return_value = None  # Both unavailable

        raw = repl._doc_search("anything")
        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)

        assert result["results"] == []
        assert "error" in result
        assert "not available" in result["error"]

    @patch("src.repl_environment.code_search._CodeSearchMixin._init_nextplaid_client")
    def test_both_containers_down_code_search(self, mock_init, repl):
        """code_search with code container down returns graceful error."""
        mock_init.return_value = None

        raw = repl._code_search("anything")
        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)

        assert result["results"] == []
        assert "not available" in result["error"]

    @patch("src.repl_environment.code_search._CodeSearchMixin._init_nextplaid_client")
    def test_clients_are_cached(self, mock_init, repl):
        """Clients are lazy-loaded and cached — _init only called once per URL."""
        code_client = FakeNextPlaidClient("http://localhost:8088")
        docs_client = FakeNextPlaidClient("http://localhost:8089")

        def init_side_effect(url):
            if url == "http://localhost:8088":
                return code_client
            return docs_client

        mock_init.side_effect = init_side_effect

        # Two code searches → only one init call
        repl._code_search("query1")
        repl._code_search("query2")

        # Two doc searches → only one init call
        repl._doc_search("query3")
        repl._doc_search("query4")

        # _init called twice total: once for code URL, once for docs URL
        assert mock_init.call_count == 2


# ---------------------------------------------------------------------------
# Tests: REPL Sandbox Integration
# ---------------------------------------------------------------------------

class TestCodeSearchRepl:
    """Integration-style: execute code_search via REPL sandbox exec."""

    @patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client")
    def test_exec_code_search(self, mock_get_client, repl):
        """code_search() is callable from within exec'd sandbox code."""
        fake_client = FakeNextPlaidClient("http://localhost:8088")
        mock_get_client.return_value = fake_client

        result = repl.execute('result = code_search("FAISS index")')
        assert result.error is None, f"REPL exec failed: {result.error}"


# ---------------------------------------------------------------------------
# Tests: ColGREP CLI integration (REPL_COLGREP feature flag)
# ---------------------------------------------------------------------------

class TestColgrepIntegration:
    """code_search() routes to ColGREP CLI when REPL_COLGREP=1."""

    _SAMPLE_COLGREP_JSON = json.dumps([
        {
            "unit": {
                "name": "frecency_score",
                "qualified_name": "file_recency.py::frecency_score",
                "file": "/proj/src/repl_environment/file_recency.py",
                "line": 42,
                "end_line": 58,
                "language": "python",
                "unit_type": "function",
                "signature": "def frecency_score(access_count, last_access):",
            },
            "score": 0.873,
        },
        {
            "unit": {
                "name": "raw_code_1",
                "file": "/proj/src/repl_environment/__init__.py",
                "line": 1, "end_line": 12,
                "unit_type": "rawcode",
                "signature": "\"\"\"Sandboxed Python REPL.",
            },
            "score": 0.214,
        },
    ])

    def test_default_colgrep_binary_path_is_version_pinned(self):
        """Default ColGREP path points at a versioned binary, not the mutable alias."""
        from src.repl_environment.code_search import (
            COLGREP_BIN,
            COLGREP_EXPECTED_SHA256,
            COLGREP_VERSION,
        )

        assert COLGREP_VERSION == "1.2.0"
        assert COLGREP_BIN.endswith(f"/colgrep-{COLGREP_VERSION}")
        assert len(COLGREP_EXPECTED_SHA256) == 64

    def _fake_proc(self, stdout: str = "", returncode: int = 0, stderr: str = ""):
        proc = MagicMock()
        proc.stdout = stdout
        proc.stderr = stderr
        proc.returncode = returncode
        return proc

    def test_flag_unset_uses_colgrep_by_default(self, repl, monkeypatch, tmp_path):
        """REPL_COLGREP unset → colgrep path (default ON as of 2026-04-29)."""
        monkeypatch.delenv("REPL_COLGREP", raising=False)
        fake_bin = tmp_path / "colgrep"
        fake_bin.write_text("#!/bin/sh\necho '[]'\n")
        fake_bin.chmod(0o755)
        monkeypatch.setenv("REPL_COLGREP_BIN", str(fake_bin))
        with patch("src.repl_environment.code_search.subprocess.run") as mock_run:
            mock_run.return_value = self._fake_proc(stdout="[]")
            repl._code_search("anything")
            mock_run.assert_called_once()

    def test_explicit_off_uses_nextplaid(self, repl, monkeypatch):
        """REPL_COLGREP=0 → NextPLAID path (explicit opt-out)."""
        monkeypatch.setenv("REPL_COLGREP", "0")
        with patch("src.repl_environment.code_search.subprocess.run") as mock_run, \
             patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client") as mock_get:
            mock_get.return_value = FakeNextPlaidClient("http://localhost:8088")
            repl._code_search("anything")
            mock_run.assert_not_called()

    def test_explicit_false_uses_nextplaid(self, repl, monkeypatch):
        """REPL_COLGREP=false → NextPLAID path."""
        monkeypatch.setenv("REPL_COLGREP", "false")
        with patch("src.repl_environment.code_search.subprocess.run") as mock_run, \
             patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client") as mock_get:
            mock_get.return_value = FakeNextPlaidClient("http://localhost:8088")
            repl._code_search("anything")
            mock_run.assert_not_called()

    def test_flag_on_uses_colgrep(self, repl, monkeypatch, tmp_path):
        """REPL_COLGREP=1 routes through subprocess.run with the colgrep binary."""
        monkeypatch.setenv("REPL_COLGREP", "1")
        # Create a fake binary path that os.path.isfile() will accept.
        fake_bin = tmp_path / "colgrep"
        fake_bin.write_text("#!/bin/sh\necho '[]'\n")
        fake_bin.chmod(0o755)
        monkeypatch.setenv("REPL_COLGREP_BIN", str(fake_bin))
        monkeypatch.setenv("REPL_COLGREP_PATH", "/proj/src")

        with patch("src.repl_environment.code_search.subprocess.run") as mock_run:
            mock_run.return_value = self._fake_proc(stdout=self._SAMPLE_COLGREP_JSON)
            raw = repl._code_search("frecency", limit=5)

            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == str(fake_bin)
            assert cmd[1] == "search"
            assert cmd[2] == "frecency"
            assert "--json" in cmd
            # alpha=0.95 default biases hybrid toward semantic to avoid
            # FTS5 over-ranking __init__.py re-exports.
            assert "--alpha" in cmd and cmd[cmd.index("--alpha") + 1] == "0.95"
            assert mock_run.call_args.kwargs["env"]["NEXT_PLAID_FORCE_CPU"] == "1"

        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)
        assert result["index"] == "code"
        assert result["engine"] == "colgrep"
        assert result["query"] == "frecency"
        assert "latency_ms" in result
        assert len(result["results"]) == 2
        # File path is relativized against REPL_COLGREP_PATH
        assert result["results"][0]["file"] == "repl_environment/file_recency.py"
        assert result["results"][0]["lines"] == "42-58"
        assert result["results"][0]["score"] == 0.873
        assert result["results"][0]["unit"] == "function:frecency_score"
        # rawcode unit_type → no "unit" field (matches NextPLAID rawcode behavior)
        assert "unit" not in result["results"][1]
        telemetry = repl.artifacts["_code_search_telemetry"][-1]
        assert telemetry["engine"] == "colgrep"
        assert telemetry["fallback"] is False
        assert telemetry["result_count"] == 2
        assert isinstance(telemetry["latency_ms"], int)
        assert repl._exploration_log.events[-1].args["engine"] == "colgrep"
        assert repl._exploration_log.events[-1].args["fallback"] is False

    def test_colgrep_missing_binary_falls_back(self, repl, monkeypatch):
        """Missing colgrep binary → falls back to NextPLAID, no exception."""
        monkeypatch.setenv("REPL_COLGREP", "1")
        monkeypatch.setenv("REPL_COLGREP_BIN", "/nonexistent/colgrep")

        with patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client") as mock_get:
            mock_get.return_value = FakeNextPlaidClient("http://localhost:8088")
            raw = repl._code_search("frecency")

        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)
        # NextPLAID engine path → no "engine" key (only colgrep sets it)
        assert "engine" not in result
        assert result["index"] == "code"
        telemetry = repl.artifacts["_code_search_telemetry"][-1]
        assert telemetry["fallback"] is True
        assert telemetry["fallback_reason"] == "missing_binary"
        assert isinstance(telemetry["latency_ms"], int)

    def test_colgrep_timeout_falls_back(self, repl, monkeypatch, tmp_path):
        """Subprocess timeout → falls back to NextPLAID."""
        monkeypatch.setenv("REPL_COLGREP", "1")
        fake_bin = tmp_path / "colgrep"
        fake_bin.write_text("#!/bin/sh\nsleep 60\n")
        fake_bin.chmod(0o755)
        monkeypatch.setenv("REPL_COLGREP_BIN", str(fake_bin))

        with patch("src.repl_environment.code_search.subprocess.run") as mock_run, \
             patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client") as mock_get:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="colgrep", timeout=10)
            mock_get.return_value = FakeNextPlaidClient("http://localhost:8088")
            raw = repl._code_search("anything")

        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)
        assert "engine" not in result  # fell back to NextPLAID
        telemetry = repl.artifacts["_code_search_telemetry"][-1]
        assert telemetry["fallback"] is True
        assert telemetry["fallback_reason"] == "timeout"

    def test_colgrep_nonzero_exit_falls_back(self, repl, monkeypatch, tmp_path):
        """Non-zero colgrep exit → falls back to NextPLAID."""
        monkeypatch.setenv("REPL_COLGREP", "1")
        fake_bin = tmp_path / "colgrep"
        fake_bin.write_text("#!/bin/sh\nexit 2\n")
        fake_bin.chmod(0o755)
        monkeypatch.setenv("REPL_COLGREP_BIN", str(fake_bin))

        with patch("src.repl_environment.code_search.subprocess.run") as mock_run, \
             patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client") as mock_get:
            mock_run.return_value = self._fake_proc(stdout="", returncode=2, stderr="boom")
            mock_get.return_value = FakeNextPlaidClient("http://localhost:8088")
            raw = repl._code_search("anything")

        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)
        assert "engine" not in result
        telemetry = repl.artifacts["_code_search_telemetry"][-1]
        assert telemetry["fallback"] is True
        assert telemetry["fallback_reason"] == "nonzero_exit"
        assert telemetry["returncode"] == 2

    def test_colgrep_bad_json_falls_back(self, repl, monkeypatch, tmp_path):
        """Malformed colgrep stdout → falls back to NextPLAID."""
        monkeypatch.setenv("REPL_COLGREP", "1")
        fake_bin = tmp_path / "colgrep"
        fake_bin.write_text("#!/bin/sh\necho not-json\n")
        fake_bin.chmod(0o755)
        monkeypatch.setenv("REPL_COLGREP_BIN", str(fake_bin))

        with patch("src.repl_environment.code_search.subprocess.run") as mock_run, \
             patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client") as mock_get:
            mock_run.return_value = self._fake_proc(stdout="not-json", returncode=0)
            mock_get.return_value = FakeNextPlaidClient("http://localhost:8088")
            raw = repl._code_search("anything")

        output = raw.replace("<<<TOOL_OUTPUT>>>", "").replace("<<<END_TOOL_OUTPUT>>>", "").strip()
        result = json.loads(output)
        assert "engine" not in result
        telemetry = repl.artifacts["_code_search_telemetry"][-1]
        assert telemetry["fallback"] is True
        assert telemetry["fallback_reason"] == "bad_json"

    def test_colgrep_doc_search_unaffected(self, repl, monkeypatch):
        """REPL_COLGREP=1 does NOT route doc_search through colgrep (code-only)."""
        monkeypatch.setenv("REPL_COLGREP", "1")
        with patch("src.repl_environment.code_search.subprocess.run") as mock_run, \
             patch("src.repl_environment.code_search._CodeSearchMixin._get_nextplaid_client") as mock_get:
            mock_get.return_value = FakeNextPlaidClient("http://localhost:8089")
            repl._doc_search("anything")
            mock_run.assert_not_called()
