"""Tests for REPL contextual suggestions (S3a)."""

from unittest.mock import MagicMock


from src.repl_environment.suggestions import (
    _SuggestionsMixin,
    generate_suggestions,
)


class TestFeatureGating:
    """Verify suggestions are disabled by default."""

    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("REPL_SUGGESTIONS", raising=False)
        assert generate_suggestions("web_search") == ""

    def test_disabled_when_off(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "0")
        assert generate_suggestions("web_search") == ""

    def test_enabled_when_1(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "1")
        result = generate_suggestions("web_search")
        assert "[Suggested next]" in result

    def test_enabled_when_true(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "true")
        result = generate_suggestions("web_search")
        assert "[Suggested next]" in result

    def test_enabled_when_on(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "on")
        result = generate_suggestions("web_search")
        assert "[Suggested next]" in result


class TestCooccurrenceSuggestions:
    """Verify correct suggestions for known tool types."""

    def test_web_search_suggests_web_search_and_wikipedia(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "1")
        result = generate_suggestions("web_search")
        assert "web_search" in result
        assert "search_wikipedia" in result

    def test_peek_suggests_grep(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "1")
        result = generate_suggestions("peek")
        assert "grep" in result

    def test_grep_suggests_peek(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "1")
        result = generate_suggestions("grep")
        assert "peek" in result

    def test_list_dir_suggests_peek(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "1")
        result = generate_suggestions("list_dir")
        assert "peek" in result

    def test_unknown_tool_returns_empty(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "1")
        result = generate_suggestions("nonexistent_tool")
        assert result == ""


class TestMaxSuggestions:
    """Verify max_suggestions cap is respected."""

    def test_max_suggestions_default(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "1")
        result = generate_suggestions("peek")
        # peek has 3 co-occurrences, max default is 3
        # Count suggestion lines (indented with 2 spaces in the raw output)
        lines = [line for line in result.split("\n") if line.startswith("  ")]
        assert len(lines) <= 3

    def test_max_suggestions_1(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "1")
        result = generate_suggestions("peek", max_suggestions=1)
        lines = [line for line in result.split("\n") if line.startswith("  ")]
        assert len(lines) == 1


class TestFrecencyIntegration:
    """Verify frecency store integration."""

    def test_frecency_files_appear(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "1")
        store = MagicMock()
        store.top_k.return_value = ["/path/to/foo.py", "/path/to/bar.py"]
        result = generate_suggestions("peek", frecency_store=store)
        assert "foo.py" in result
        assert "bar.py" in result

    def test_frecency_error_graceful(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "1")
        store = MagicMock()
        store.top_k.side_effect = RuntimeError("db locked")
        # Should not raise, just skip frecency suggestions
        result = generate_suggestions("peek", frecency_store=store)
        assert "[Suggested next]" in result  # Co-occurrence still works

    def test_frecency_not_used_for_web_search(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "1")
        store = MagicMock()
        store.top_k.return_value = ["/path/to/foo.py"]
        _result = generate_suggestions("web_search", frecency_store=store)
        # web_search is not a file-oriented tool
        store.top_k.assert_not_called()


class TestMixin:
    """Verify the _SuggestionsMixin integration."""

    def test_mixin_appends_when_enabled(self, monkeypatch):
        monkeypatch.setenv("REPL_SUGGESTIONS", "1")

        class Env(_SuggestionsMixin):
            pass

        env = Env()
        result = env._maybe_append_suggestions("web_search", "Observation: test output")
        assert result.startswith("Observation: test output")
        assert "[Suggested next]" in result

    def test_mixin_noop_when_disabled(self, monkeypatch):
        monkeypatch.delenv("REPL_SUGGESTIONS", raising=False)

        class Env(_SuggestionsMixin):
            pass

        env = Env()
        result = env._maybe_append_suggestions("web_search", "Observation: test output")
        assert result == "Observation: test output"
