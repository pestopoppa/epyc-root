"""Tests for REPL STUCK("reason") signal (NIB2-24)."""

from unittest.mock import MagicMock


from src.repl_environment import REPLEnvironment


def _make_repl():
    """Create a plain REPLEnvironment for testing."""
    from src.repl_environment.types import REPLConfig
    config = REPLConfig()
    return REPLEnvironment(context="test", config=config)


class TestStuckSignalBasic:
    """Test basic STUCK signal behavior."""

    def test_stuck_returns_string(self):
        """STUCK returns recovery guidance as a string."""
        repl = _make_repl()
        result = repl._stuck("Cannot find the target function")
        assert isinstance(result, str)
        assert "Stuck" in result

    def test_stuck_includes_reason(self):
        """Guidance includes the stuck reason."""
        repl = _make_repl()
        result = repl._stuck("All search queries return empty results")
        assert "All search queries return empty results" in result

    def test_stuck_includes_recovery_options(self):
        """Guidance includes recovery options."""
        repl = _make_repl()
        result = repl._stuck("dead end")
        assert "Recovery options" in result
        assert "escalate" in result
        assert "FINAL" in result

    def test_stuck_increments_exploration(self):
        """Exploration counter is incremented."""
        repl = _make_repl()
        initial = repl._exploration_calls
        repl._stuck("reason")
        assert repl._exploration_calls > initial

    def test_stuck_logs_to_exploration_log(self):
        """Stuck event is recorded in exploration log."""
        repl = _make_repl()
        repl._stuck("test reason")
        events = repl._exploration_log.events
        stuck_events = [e for e in events if e.function == "stuck"]
        assert len(stuck_events) == 1
        assert stuck_events[0].args["reason"] == "test reason"

    def test_stuck_is_non_terminating(self):
        """STUCK does not raise an exception (unlike FINAL)."""
        repl = _make_repl()
        # This should not raise
        result = repl._stuck("test")
        assert result is not None

    def test_stuck_available_in_repl_globals(self):
        """STUCK is registered in REPL globals."""
        repl = _make_repl()
        globals_dict = repl._build_globals()
        assert "STUCK" in globals_dict
        assert callable(globals_dict["STUCK"])

    def test_stuck_via_execute(self):
        """STUCK can be called via execute()."""
        repl = _make_repl()
        result = repl.execute('artifacts["guidance"] = STUCK("cannot find file")')
        assert result.error is None
        assert "Stuck" in repl.artifacts["guidance"]


class TestStuckWithExplorationHistory:
    """Test STUCK with prior exploration context."""

    def test_includes_recent_tools(self):
        """When exploration history exists, recent tools are shown."""
        repl = _make_repl()
        # Add some exploration events
        repl._exploration_log.add_event("peek", {"path": "/tmp/test"}, "content")
        repl._exploration_log.add_event("grep", {"pattern": "foo"}, "no matches")

        result = repl._stuck("grep found nothing")
        assert "peek" in result or "grep" in result

    def test_includes_strategy_summary(self):
        """Exploration summary is included in guidance."""
        repl = _make_repl()
        # Build some exploration history
        for i in range(3):
            repl._exploration_log.add_event("web_search", {"query": f"q{i}"}, "results")

        result = repl._stuck("web search not helpful")
        assert "Exploration so far" in result


class TestStuckMemoryIntegration:
    """Test STUCK with episodic memory recall."""

    def test_includes_memory_guidance_when_available(self):
        """Memory recall results included when retriever available."""
        repl = _make_repl()

        # Mock _recall to return useful memory
        repl._recall = MagicMock(return_value='{"results": [{"action": "escalate", "q_value": 0.8}]}')

        result = repl._stuck("model keeps repeating itself")
        assert "Similar past situations" in result

    def test_graceful_with_no_memories(self):
        """Works fine when recall returns no memories."""
        repl = _make_repl()
        # Healthy recall with zero hits must not add a memory section.
        repl._recall = MagicMock(
            return_value='{\n  "status": "ok",\n  "results": [],\n  "best_action": null\n}'
        )
        result = repl._stuck("stuck without memory")
        assert "Stuck" in result
        assert "Similar past situations" not in result

    def test_unavailable_recall_is_not_guidance(self):
        """A broken-recall payload is not injected as 'similar past situations'."""
        repl = _make_repl()
        repl._recall = MagicMock(
            return_value='{"status": "unavailable", "results": [], "error": "AttributeError: x"}'
        )
        result = repl._stuck("test")
        assert "Stuck" in result
        assert "Similar past situations" not in result
        assert "AttributeError" not in result

    def test_recall_failure_graceful(self):
        """Recall exceptions are caught gracefully."""
        repl = _make_repl()
        repl._recall = MagicMock(side_effect=RuntimeError("store unavailable"))
        result = repl._stuck("test")
        # Should not raise, just skip memory section
        assert "Stuck" in result
