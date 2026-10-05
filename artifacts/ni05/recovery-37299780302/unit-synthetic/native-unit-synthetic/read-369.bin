"""Tests for frecency wiring in _list_dir() and _nextplaid_search().

P6 S1b-c: verifies feature-flag gating, score boosting, and graceful degradation.
"""

from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock, patch



# ---------------------------------------------------------------------------
# Minimal stub that satisfies the mixin contracts
# ---------------------------------------------------------------------------

def _make_env(monkeypatch, frecency_env: str | None = None):
    """Build a lightweight object that inherits both mixins."""
    from src.repl_environment.file_exploration import _FileExplorationMixin
    from src.repl_environment.code_search import _CodeSearchMixin

    class _Stub(_FileExplorationMixin, _CodeSearchMixin):
        pass

    obj = _Stub()

    # Required attributes expected by the mixins
    obj.config = types.SimpleNamespace(
        max_grep_results=100,
        use_toon_encoding=False,
    )
    obj.context = ""
    obj.artifacts = {}
    obj._exploration_calls = 0
    obj._exploration_log = MagicMock()
    obj._grep_hits_buffer = []
    obj._validate_file_path = MagicMock(return_value=(True, None))
    obj._research_context = MagicMock()
    obj._research_context.add = MagicMock(return_value="node-1")
    obj._last_research_node = None
    obj._state_lock = None
    obj._maybe_wrap_tool_output = lambda self_or_val, val=None: val if val is not None else self_or_val

    if frecency_env is not None:
        monkeypatch.setenv("REPL_FRECENCY", frecency_env)
    else:
        monkeypatch.delenv("REPL_FRECENCY", raising=False)

    return obj


# ===========================================================================
# _list_dir tests
# ===========================================================================

def _fake_scandir(entries):
    """Return a list of mock DirEntry objects for os.scandir."""
    mocks = []
    for name, is_dir, size in entries:
        m = MagicMock()
        m.name = name
        m.is_dir = MagicMock(return_value=is_dir)
        m.is_file = MagicMock(return_value=not is_dir)
        if not is_dir:
            stat = MagicMock()
            stat.st_size = size
            m.stat = MagicMock(return_value=stat)
        mocks.append(m)
    return mocks


class TestListDirFrecency:
    """Tests for frecency wiring in _list_dir."""

    def test_list_dir_flag_off(self, monkeypatch):
        """With REPL_FRECENCY unset, entries sorted normally (dirs first, alpha)."""
        env = _make_env(monkeypatch, frecency_env=None)

        entries = [
            ("zebra.py", False, 100),
            ("alpha", True, 0),
            ("beta.py", False, 200),
            ("delta", True, 0),
        ]
        with patch("os.scandir", return_value=_fake_scandir(entries)):
            raw = env._list_dir("/fake/path")

        result = json.loads(raw)
        names = [e["name"] for e in result["files"]]
        # dirs first alphabetically, then files alphabetically
        assert names == ["alpha", "delta", "beta.py", "zebra.py"]

    def test_list_dir_flag_on(self, monkeypatch):
        """With REPL_FRECENCY=1, entries re-sorted by frecency within type groups."""
        env = _make_env(monkeypatch, frecency_env="1")

        entries = [
            ("alpha.py", False, 10),
            ("beta.py", False, 20),
            ("gamma.py", False, 30),
        ]

        # Mock FrecencyStore so beta.py has the highest score
        mock_store = MagicMock()
        mock_store.get_scores.return_value = {
            "/fake/path/alpha.py": 0.0,
            "/fake/path/beta.py": 5.0,
            "/fake/path/gamma.py": 1.0,
        }
        mock_store.record_access = MagicMock()

        # Create a mock module for the lazy import
        mock_recency_mod = types.ModuleType("src.repl_environment.file_recency")
        mock_recency_mod.FrecencyStore = MagicMock(return_value=mock_store)

        with patch("os.scandir", return_value=_fake_scandir(entries)), \
             patch.dict(sys.modules, {"src.repl_environment.file_recency": mock_recency_mod}):
            raw = env._list_dir("/fake/path")

        result = json.loads(raw)
        names = [e["name"] for e in result["files"]]
        # beta.py (5.0) > gamma.py (1.0) > alpha.py (0.0)
        assert names == ["beta.py", "gamma.py", "alpha.py"]
        mock_store.record_access.assert_called_once_with("/fake/path")

    def test_list_dir_flag_on_dirs_and_files(self, monkeypatch):
        """Dirs stay before files; frecency only reorders within each group."""
        env = _make_env(monkeypatch, frecency_env="true")

        entries = [
            ("z_dir", True, 0),
            ("a_dir", True, 0),
            ("z_file.py", False, 10),
            ("a_file.py", False, 20),
        ]

        mock_store = MagicMock()
        mock_store.get_scores.return_value = {
            "/fake/path/z_dir": 3.0,
            "/fake/path/a_dir": 0.0,
            "/fake/path/z_file.py": 5.0,
            "/fake/path/a_file.py": 0.0,
        }
        mock_store.record_access = MagicMock()

        mock_recency_mod = types.ModuleType("src.repl_environment.file_recency")
        mock_recency_mod.FrecencyStore = MagicMock(return_value=mock_store)

        with patch("os.scandir", return_value=_fake_scandir(entries)), \
             patch.dict(sys.modules, {"src.repl_environment.file_recency": mock_recency_mod}):
            raw = env._list_dir("/fake/path")

        result = json.loads(raw)
        names = [e["name"] for e in result["files"]]
        types_list = [e["type"] for e in result["files"]]
        # Dirs first (z_dir boosted above a_dir), then files (z_file boosted above a_file)
        assert types_list == ["dir", "dir", "file", "file"]
        assert names == ["z_dir", "a_dir", "z_file.py", "a_file.py"]

    def test_list_dir_graceful_degradation(self, monkeypatch):
        """With flag on but FrecencyStore import fails, no crash -- falls back to normal sort."""
        env = _make_env(monkeypatch, frecency_env="1")

        entries = [
            ("beta.py", False, 20),
            ("alpha.py", False, 10),
        ]

        # Make the import raise
        mock_recency_mod = types.ModuleType("src.repl_environment.file_recency")
        mock_recency_mod.FrecencyStore = MagicMock(side_effect=Exception("boom"))

        with patch("os.scandir", return_value=_fake_scandir(entries)), \
             patch.dict(sys.modules, {"src.repl_environment.file_recency": mock_recency_mod}):
            # Should not raise
            raw = env._list_dir("/fake/path")

        result = json.loads(raw)
        names = [e["name"] for e in result["files"]]
        # Falls back to alpha sort (from the first sort)
        assert names == ["alpha.py", "beta.py"]


# ===========================================================================
# code_search / _nextplaid_search tests
# ===========================================================================

def _make_search_result(items):
    """Build a mock NextPLAID search result."""
    qr = MagicMock()
    qr.document_ids = [it[0] for it in items]
    qr.scores = [it[1] for it in items]
    qr.metadata = [it[2] for it in items]

    result = MagicMock()
    result.results = [qr]
    return result


# Build a mock next_plaid_client package for sys.modules patching
def _mock_nextplaid_modules():
    """Return dict of mock modules for next_plaid_client."""
    mock_models = types.ModuleType("next_plaid_client.models")
    mock_models.SearchParams = MagicMock()

    mock_pkg = types.ModuleType("next_plaid_client")
    mock_pkg.models = mock_models
    mock_pkg.NextPlaidClient = MagicMock()

    return {
        "next_plaid_client": mock_pkg,
        "next_plaid_client.models": mock_models,
    }


class TestCodeSearchFrecency:
    """Tests for frecency wiring in _nextplaid_search."""

    def _make_search_env(self, monkeypatch, frecency_env: str | None = None):
        """Build env with a mocked NextPLAID client."""
        env = _make_env(monkeypatch, frecency_env=frecency_env)

        items = [
            ("doc1", 0.9, {"file": "/src/a.py", "start_line": "1", "end_line": "10"}),
            ("doc2", 0.8, {"file": "/src/b.py", "start_line": "5", "end_line": "15"}),
            ("doc3", 0.7, {"file": "/src/c.py", "start_line": "20", "end_line": "30"}),
        ]
        mock_client = MagicMock()
        mock_client.search_with_encoding.return_value = _make_search_result(items)

        # Inject the client directly
        env._code_client = mock_client

        return env

    def test_code_search_flag_off(self, monkeypatch):
        """With REPL_FRECENCY unset, scores are unchanged."""
        env = self._make_search_env(monkeypatch, frecency_env=None)

        with patch.dict(sys.modules, _mock_nextplaid_modules()):
            raw = env._code_search("test query", limit=5)

        result = json.loads(raw)
        scores = [r["score"] for r in result["results"]]
        assert scores == [0.9, 0.8, 0.7]

    def test_code_search_flag_on(self, monkeypatch):
        """With REPL_FRECENCY=1, scores are boosted and results re-sorted."""
        env = self._make_search_env(monkeypatch, frecency_env="1")

        # Mock FrecencyStore: c.py has high frecency, a.py has none
        mock_store = MagicMock()
        mock_store.get_score.side_effect = lambda path: {
            "/src/a.py": 0.0,
            "/src/b.py": 0.0,
            "/src/c.py": 3.0,
        }.get(path, 0.0)

        mock_recency_mod = types.ModuleType("src.repl_environment.file_recency")
        mock_recency_mod.FrecencyStore = MagicMock(return_value=mock_store)

        modules = _mock_nextplaid_modules()
        modules["src.repl_environment.file_recency"] = mock_recency_mod

        with patch.dict(sys.modules, modules):
            raw = env._code_search("test query", limit=5)

        result = json.loads(raw)
        files = [r["file"] for r in result["results"]]
        # c.py should be boosted: 0.7 * (1 + 0.3 * 3.0) = 0.7 * 1.9 = 1.33
        # a.py stays at 0.9, b.py stays at 0.8
        assert files[0] == "/src/c.py", f"Expected c.py first, got {files}"
        assert result["results"][0]["score"] > 0.9

    def test_code_search_frecency_degradation(self, monkeypatch):
        """With flag on but FrecencyStore fails, scores unchanged."""
        env = self._make_search_env(monkeypatch, frecency_env="1")

        mock_recency_mod = types.ModuleType("src.repl_environment.file_recency")
        mock_recency_mod.FrecencyStore = MagicMock(side_effect=Exception("db locked"))

        modules = _mock_nextplaid_modules()
        modules["src.repl_environment.file_recency"] = mock_recency_mod

        with patch.dict(sys.modules, modules):
            raw = env._code_search("test query", limit=5)

        result = json.loads(raw)
        scores = [r["score"] for r in result["results"]]
        # Should fall back to original scores
        assert scores == [0.9, 0.8, 0.7]
