"""Extended tests for REPL state management.

Tests coverage for src/repl_environment/state.py (58% coverage).
Focus on uncovered checkpoint/restore logic and edge cases.
"""

import time
from unittest.mock import Mock

import pytest

from src.repl_environment.state import _StateMixin, _is_json_serializable
from src.repl_environment.types import ExplorationEvent, ExplorationLog


class MockREPLEnvironment(_StateMixin):
    """Mock REPL environment for testing state mixin."""

    def __init__(self):
        self.config = Mock()
        self.context = "Test context with some data"
        self.artifacts = {}
        self._exploration_calls = 0
        self._exploration_log = ExplorationLog()
        self._execution_count = 0
        self._final_answer = None
        self._grep_hits_buffer = []
        self._findings_buffer = []
        self._globals = {}
        self._builtin_global_keys = frozenset({"artifacts"})
        self.progress_logger = None
        self.task_id = "test_task_123"
        self.role = "worker_general"

    def _build_globals(self):
        """Build globals dict."""
        return {"artifacts": self.artifacts}


class TestGetState:
    """Test get_state() method."""

    def test_get_state_empty_artifacts(self):
        """Test state summary with no artifacts."""
        env = MockREPLEnvironment()
        state = env.get_state()

        assert "context: str" in state
        assert "artifacts: {}" in state

    def test_get_state_with_artifacts(self):
        """Test state summary with artifacts."""
        env = MockREPLEnvironment()
        env.artifacts["result"] = "Test result value"
        env.artifacts["count"] = 42

        state = env.get_state()

        assert "artifacts: ['result', 'count']" in state
        assert "Test result value" in state


class TestExplorationLog:
    """Test exploration logging methods."""

    def test_get_exploration_log(self):
        """Test retrieving exploration log."""
        env = MockREPLEnvironment()
        log = env.get_exploration_log()

        assert isinstance(log, ExplorationLog)
        assert log.events == []

    def test_get_grep_history(self):
        """Test retrieving grep history."""
        env = MockREPLEnvironment()
        env._grep_hits_buffer = [{"match": "test1"}, {"match": "test2"}]

        history = env.get_grep_history()

        assert len(history) == 2
        assert history[0]["match"] == "test1"

    def test_clear_grep_history(self):
        """Test clearing grep history."""
        env = MockREPLEnvironment()
        env._grep_hits_buffer = [{"match": "test"}]

        env.clear_grep_history()

        assert env._grep_hits_buffer == []

    def test_get_exploration_strategy(self):
        """Test getting exploration strategy summary."""
        env = MockREPLEnvironment()
        env._exploration_log.events.append(
            ExplorationEvent(
                function="grep",
                args={"pattern": "test"},
                result_size=100,
                timestamp=time.time(),
                token_estimate=25,
            )
        )

        strategy = env.get_exploration_strategy()

        assert isinstance(strategy, dict)
        assert "function_counts" in strategy or "total_tokens" in strategy


class TestLogExplorationCompleted:
    """Test log_exploration_completed() method."""

    def test_log_exploration_completed_without_logger(self):
        """Test completion logging without progress logger."""
        env = MockREPLEnvironment()
        env.progress_logger = None

        data = env.log_exploration_completed(success=True, result="Test result")

        assert data["success"] is True
        assert "strategy" in data
        assert "efficiency" in data

    def test_log_exploration_completed_with_logger(self):
        """Test completion logging with progress logger."""
        env = MockREPLEnvironment()
        env.progress_logger = Mock()

        data = env.log_exploration_completed(success=True, result="Test result")

        env.progress_logger.log_exploration.assert_called_once()
        assert data["success"] is True


class TestSuggestExploration:
    """Test suggest_exploration() method."""

    def test_suggest_exploration_without_retriever(self):
        """Test suggestions without retriever."""
        env = MockREPLEnvironment()
        env.context = "Short context"

        suggestions = env.suggest_exploration("Find data", retriever=None)

        assert len(suggestions) > 0
        assert any("peek" in s for s in suggestions)

    def test_suggest_exploration_long_context(self):
        """Test suggestions for long context."""
        env = MockREPLEnvironment()
        env.context = "x" * 5000  # Long context

        suggestions = env.suggest_exploration("Task", retriever=None)

        # Should suggest grep for long contexts
        assert any("grep" in s for s in suggestions)

    def test_suggest_exploration_with_retriever(self):
        """Test suggestions with retriever providing episodic memories."""
        env = MockREPLEnvironment()
        retriever = Mock()

        # Mock retrieval result
        mock_memory = Mock()
        mock_memory.outcome = "success"
        mock_memory.context = {
            "exploration_strategy": {
                "strategy_type": "scan",
                "function_counts": {"peek": 3, "grep": 2},
            }
        }

        mock_result = Mock()
        mock_result.q_value = 0.8
        mock_result.memory = mock_memory

        retriever.retrieve_for_exploration.return_value = [mock_result]

        suggestions = env.suggest_exploration("Task description", retriever=retriever)

        # Should include episodic suggestions from similar tasks
        assert len(suggestions) > 0


class TestCheckpoint:
    """Test checkpoint() method."""

    def test_checkpoint_basic(self):
        """Test basic checkpoint creation."""
        env = MockREPLEnvironment()
        env.artifacts["key"] = "value"
        env._execution_count = 5

        checkpoint = env.checkpoint()

        assert checkpoint["version"] == 1
        assert checkpoint["artifacts"]["key"] == "value"
        assert checkpoint["execution_count"] == 5
        assert checkpoint["task_id"] == "test_task_123"

    def test_checkpoint_with_exploration_events(self):
        """Test checkpoint includes exploration events."""
        env = MockREPLEnvironment()
        env._exploration_log.events.append(
            ExplorationEvent(
                function="grep",
                args={"pattern": "test"},
                result_size=100,
                timestamp=time.time(),
                token_estimate=25,
            )
        )

        checkpoint = env.checkpoint()

        assert len(checkpoint["exploration_events"]) == 1
        assert checkpoint["exploration_events"][0]["function"] == "grep"

    def test_checkpoint_sanitizes_unserializable(self):
        """Test checkpoint sanitizes non-JSON-serializable values."""
        env = MockREPLEnvironment()

        # Add non-serializable object
        class CustomObject:
            pass

        env.artifacts["obj"] = CustomObject()
        env.artifacts["good_val"] = "serializable"

        checkpoint = env.checkpoint()

        # Good value should be preserved
        assert checkpoint["artifacts"]["good_val"] == "serializable"

        # Bad value should be marked
        assert checkpoint["artifacts"]["obj"]["__unserializable__"] is True
        assert "CustomObject" in checkpoint["artifacts"]["obj"]["type"]

    def test_checkpoint_with_nested_artifacts(self):
        """Test checkpoint handles nested artifact structures."""
        env = MockREPLEnvironment()
        env.artifacts["nested"] = {"level1": {"level2": "value", "list": [1, 2, 3]}}

        checkpoint = env.checkpoint()

        # Should preserve nested structure
        assert checkpoint["artifacts"]["nested"]["level1"]["level2"] == "value"
        assert checkpoint["artifacts"]["nested"]["level1"]["list"] == [1, 2, 3]

    def test_checkpoint_serializes_user_globals(self):
        env = MockREPLEnvironment()
        env._globals = {"artifacts": env.artifacts, "x": 7, "name": "alice"}

        checkpoint = env.checkpoint()

        assert checkpoint["user_globals"]["x"] == 7
        assert checkpoint["user_globals"]["name"] == "alice"
        assert checkpoint["variable_lineage"]["x"]["role"] == "worker_general"

    def test_checkpoint_skips_non_serializable_user_globals(self):
        env = MockREPLEnvironment()
        env._globals = {"artifacts": env.artifacts, "ok": {"a": 1}, "bad": lambda x: x}

        checkpoint = env.checkpoint()

        assert checkpoint["user_globals"]["ok"] == {"a": 1}
        assert "bad" not in checkpoint["user_globals"]
        assert "bad" in checkpoint["skipped_user_globals"]


class TestRestore:
    """Test restore() method."""

    def test_restore_basic(self):
        """Test basic restore from checkpoint."""
        env = MockREPLEnvironment()

        checkpoint = {
            "version": 1,
            "artifacts": {"key": "value"},
            "execution_count": 5,
            "exploration_calls": 3,
            "exploration_tokens": 100,
            "exploration_events": [],
            "grep_hits_buffer": [],
            "findings_buffer": [],
            "context_length": 100,
            "task_id": "restored_task",
        }

        env.restore(checkpoint)

        assert env.artifacts["key"] == "value"
        assert env._execution_count == 5
        assert env._exploration_calls == 3

    def test_restore_invalid_version(self):
        """Test restore with unsupported version."""
        env = MockREPLEnvironment()

        checkpoint = {
            "version": 99,  # Unsupported version
        }

        with pytest.raises(ValueError, match="Unsupported checkpoint version"):
            env.restore(checkpoint)

    def test_restore_missing_version_defaults_to_v1(self):
        env = MockREPLEnvironment()
        checkpoint = {
            "artifacts": {"key": "value"},
            "execution_count": 1,
            "exploration_calls": 0,
            "exploration_tokens": 0,
            "exploration_events": [],
            "grep_hits_buffer": [],
            "findings_buffer": [],
        }
        env.restore(checkpoint)
        assert env.artifacts["key"] == "value"

    def test_restore_with_exploration_events(self):
        """Test restore rebuilds exploration log."""
        env = MockREPLEnvironment()

        checkpoint = {
            "version": 1,
            "artifacts": {},
            "execution_count": 0,
            "exploration_calls": 0,
            "exploration_tokens": 50,
            "exploration_events": [
                {
                    "function": "grep",
                    "args": {"pattern": "test"},
                    "result_size": 100,
                    "timestamp": time.time(),
                    "token_estimate": 25,
                }
            ],
            "grep_hits_buffer": [],
            "findings_buffer": [],
        }

        env.restore(checkpoint)

        assert len(env._exploration_log.events) == 1
        assert env._exploration_log.events[0].function == "grep"
        assert env._exploration_log.total_exploration_tokens == 50

    def test_restore_rebuilds_globals(self):
        """Test restore rebuilds globals dict."""
        env = MockREPLEnvironment()

        checkpoint = {
            "version": 1,
            "artifacts": {"data": "test_data"},
            "execution_count": 0,
            "exploration_calls": 0,
            "exploration_tokens": 0,
            "exploration_events": [],
            "grep_hits_buffer": [],
            "findings_buffer": [],
        }

        env.restore(checkpoint)

        # Globals should be rebuilt with restored artifacts
        assert env._globals["artifacts"]["data"] == "test_data"

    def test_restore_merges_user_globals(self):
        env = MockREPLEnvironment()
        checkpoint = {
            "version": 1,
            "artifacts": {},
            "execution_count": 0,
            "exploration_calls": 0,
            "exploration_tokens": 0,
            "exploration_events": [],
            "grep_hits_buffer": [],
            "findings_buffer": [],
            "user_globals": {"memo": [1, 2, 3]},
        }

        env.restore(checkpoint)
        assert env._globals["memo"] == [1, 2, 3]


class TestRestoreReconciliation:
    """restore() must report what ACTUALLY landed, not what the payload claimed."""

    def _checkpoint(self, **overrides):
        base = {
            "version": 1,
            "artifacts": {},
            "execution_count": 0,
            "exploration_calls": 0,
            "exploration_tokens": 0,
            "exploration_events": [],
            "grep_hits_buffer": [],
            "findings_buffer": [],
            "user_globals": {},
        }
        base.update(overrides)
        return base

    def test_reconciliation_reports_restored_names(self):
        env = MockREPLEnvironment()
        result = env.restore(self._checkpoint(user_globals={"memo": [1, 2], "n": 3}))

        assert sorted(result["restored"]) == ["memo", "n"]
        assert result["claimed"] == 2
        assert result["unavailable"] == {}
        assert env._restore_reconciliation == result

    def test_builtin_collision_is_reported_not_silently_dropped(self):
        """A name colliding with an engine builtin never lands — say so."""
        env = MockREPLEnvironment()
        result = env.restore(self._checkpoint(user_globals={"artifacts": {"x": 1}, "ok": 5}))

        assert result["restored"] == ["ok"]
        assert result["claimed"] == 2
        assert "artifacts" in result["unavailable"]
        assert "builtin" in result["unavailable"]["artifacts"]

    def test_save_time_drops_are_carried_into_reconciliation(self):
        env = MockREPLEnvironment()
        result = env.restore(
            self._checkpoint(user_globals={"ok": 1}, skipped_user_globals=["helper_fn"])
        )

        assert result["restored"] == ["ok"]
        assert result["dropped_at_save"] == ["helper_fn"]
        assert "never checkpointed" in result["unavailable"]["helper_fn"]

    def test_get_state_surfaces_unavailable_names_to_the_model(self):
        env = MockREPLEnvironment()
        env.restore(
            self._checkpoint(user_globals={"kept": 1}, skipped_user_globals=["lost_fn"])
        )

        state = env.get_state()
        assert "Not Restored" in state
        assert "lost_fn" in state

    def test_get_state_omits_section_when_nothing_missing(self):
        env = MockREPLEnvironment()
        env.restore(self._checkpoint(user_globals={"kept": 1}))

        assert "Not Restored" not in env.get_state()


class TestSerializationHelper:
    def test_is_json_serializable_callable_false(self):
        assert _is_json_serializable(lambda x: x) is False

    def test_is_json_serializable_plain_types_true(self):
        assert _is_json_serializable({"x": [1, 2, 3]}) is True


class TestCheckpointMetadata:
    """Test get_checkpoint_metadata() method."""

    def test_get_checkpoint_metadata(self):
        """Test retrieving checkpoint metadata."""
        env = MockREPLEnvironment()
        env._execution_count = 10
        env._exploration_calls = 5
        env.artifacts = {"a": 1, "b": 2}
        env._grep_hits_buffer = [{"match": "x"}]
        env._findings_buffer = [{"finding": "y"}]

        metadata = env.get_checkpoint_metadata()

        assert metadata["execution_count"] == 10
        assert metadata["exploration_calls"] == 5
        assert metadata["artifact_count"] == 2
        assert metadata["context_length"] == len(env.context)
        assert metadata["grep_hits_count"] == 1
        assert metadata["findings_count"] == 1


class TestReset:
    """Test reset() method."""

    def test_reset_clears_state(self):
        """Test reset clears all state except context."""
        env = MockREPLEnvironment()
        env.artifacts = {"key": "value"}
        env._final_answer = "Some answer"
        env._execution_count = 10
        env._exploration_calls = 5
        env._grep_hits_buffer = [{"match": "x"}]
        env._findings_buffer = [{"finding": "y"}]

        original_context = env.context

        env.reset()

        assert env.artifacts == {}
        assert env._final_answer is None
        assert env._execution_count == 0
        assert env._exploration_calls == 0
        assert env._grep_hits_buffer == []
        assert env._findings_buffer == []
        # Context should be preserved
        assert env.context == original_context

    def test_reset_creates_new_exploration_log(self):
        """Test reset creates fresh exploration log."""
        env = MockREPLEnvironment()
        env._exploration_log.events.append(ExplorationEvent("test", {}, 0, time.time(), 0))

        env.reset()

        assert len(env._exploration_log.events) == 0
        assert env._exploration_log.total_exploration_tokens == 0


class TestCurationLayer:
    """D-d — remember() is curation layered over auto-save."""

    def _env(self):
        env = MockREPLEnvironment()
        env._globals = {"artifacts": env.artifacts}
        return env

    def test_remember_records_a_note(self):
        env = self._env()
        env._globals["idx"] = {"a": 1}
        msg = env.remember("idx", note="inverted index over the corpus")
        assert "idx" in msg
        assert env.get_curated() == {"idx": "inverted index over the corpus"}

    def test_remember_without_a_note_still_marks(self):
        env = self._env()
        env._globals["counts"] = [1, 2]
        env.remember("counts")
        assert env.get_curated() == {"counts": ""}

    def test_remember_unknown_name_errors_and_lists_options(self):
        env = self._env()
        env._globals["present"] = 1
        msg = env.remember("absent")
        assert msg.startswith("[ERROR")
        assert "present" in msg
        assert env.get_curated() == {}

    def test_remember_rejects_non_string_arguments(self):
        env = self._env()
        env._globals["x"] = 1
        assert env.remember(None).startswith("[ERROR")
        assert env.remember("x", note=123).startswith("[ERROR")

    def test_curation_flows_into_lineage_and_survives_a_round_trip(self):
        env = self._env()
        env._globals["idx"] = {"a": 1}
        env.remember("idx", note="the index")

        cp = env.checkpoint()
        assert cp["curated"] == {"idx": "the index"}
        assert cp["variable_lineage"]["idx"]["curated"] is True
        assert cp["variable_lineage"]["idx"]["note"] == "the index"

        fresh = self._env()
        fresh.restore(cp)
        assert fresh.get_curated() == {"idx": "the index"}

    def test_uncurated_variables_carry_no_curation_keys(self):
        env = self._env()
        env._globals["plain"] = 5
        lineage = env.checkpoint()["variable_lineage"]["plain"]
        assert "curated" not in lineage and "note" not in lineage


class TestCodeLog:
    """D-c1 — record executed steps and size the counterfactual preamble."""

    def _env(self):
        env = MockREPLEnvironment()
        env._globals = {"artifacts": env.artifacts}
        return env

    def test_records_ok_and_failed_steps(self):
        env = self._env()
        env._record_code_log("x = 1", ok=True)
        env._record_code_log("import os\nos.system('x')", ok=False)

        log = env.get_code_log()
        assert len(log) == 2
        assert log[0]["ok"] is True and log[0]["code"] == "x = 1"
        # A failed step keeps only its first line.
        assert log[1]["ok"] is False and log[1]["code"] == "import os"

    def test_metrics_size_the_counterfactual_without_touching_prompts(self):
        env = self._env()
        env._record_code_log("a = 1", ok=True)
        env._record_code_log("b = 2", ok=True)
        m = env.code_log_metrics()
        assert m["steps"] == 2 and m["steps_ok"] == 2 and m["steps_failed"] == 0
        assert m["rendered_chars"] == len("a = 1") + len("b = 2")
        assert m["rendered_tokens_est"] == m["rendered_chars"] // 4

    def test_log_is_bounded_and_reports_what_it_elided(self):
        env = self._env()
        for i in range(env.CODE_LOG_MAX_STEPS + 15):
            env._record_code_log(f"v{i} = {i}", ok=True)
        assert len(env.get_code_log()) == env.CODE_LOG_MAX_STEPS
        assert env.code_log_metrics()["steps_elided"] == 15

    def test_long_step_is_truncated_but_raw_size_is_retained(self):
        env = self._env()
        big = "x = '" + "a" * (env.CODE_LOG_MAX_CHARS + 500) + "'"
        env._record_code_log(big, ok=True)
        entry = env.get_code_log()[0]
        assert len(entry["code"]) < len(big)
        assert entry["chars"] == len(big)

    def test_code_log_survives_a_checkpoint_round_trip(self):
        env = self._env()
        env._record_code_log("keep = 1", ok=True)
        cp = env.checkpoint()
        assert cp["code_log"][0]["code"] == "keep = 1"
        assert cp["code_log_metrics"]["steps"] == 1

        fresh = self._env()
        fresh.restore(cp)
        assert fresh.get_code_log()[0]["code"] == "keep = 1"

    def test_code_log_is_not_injected_into_get_state(self):
        """The whole point of D-c1 is measurement WITHOUT a prompt change."""
        env = self._env()
        env._record_code_log("secret_marker_xyz = 1", ok=True)
        assert "secret_marker_xyz" not in env.get_state()
