"""Tests for the graph SQLiteStatePersistence adapter."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from pydantic_graph import End

from src.features import Features, set_features, reset_features
from src.graph.persistence import (
    SQLiteStatePersistence,
    _state_to_dict,
    _state_to_dict_full,
)
from src.graph.nodes import FrontdoorNode, CoderNode
from src.graph.state import TaskState, TaskResult
from src.roles import Role


class TestStateToDict:
    """Test TaskState serialization."""

    def test_basic_serialization(self):
        state = TaskState(
            task_id="test-001",
            prompt="hello world",
            current_role=Role.CODER_ESCALATION,
            consecutive_failures=1,
            escalation_count=2,
            role_history=["frontdoor", "coder_escalation"],
            turns=3,
            last_error="some error",
        )
        d = _state_to_dict(state)
        assert d["task_id"] == "test-001"
        assert d["current_role"] == "coder_escalation"
        assert d["consecutive_failures"] == 1
        assert d["escalation_count"] == 2
        assert d["role_history"] == ["frontdoor", "coder_escalation"]
        assert d["turns"] == 3
        assert d["last_error"] == "some error"

    def test_prompt_truncation(self):
        state = TaskState(prompt="x" * 1000)
        d = _state_to_dict(state)
        assert len(d["prompt"]) == 500

    def test_error_truncation(self):
        state = TaskState(last_error="e" * 500)
        d = _state_to_dict(state)
        assert len(d["last_error"]) == 200


class TestSQLiteStatePersistence:
    """Test persistence adapter with mock session store."""

    def test_init(self):
        store = MagicMock()
        persistence = SQLiteStatePersistence(store, "session-001")
        assert persistence._session_id == "session-001"

    @pytest.mark.asyncio
    async def test_snapshot_node(self):
        store = MagicMock()
        persistence = SQLiteStatePersistence(store, "session-001")

        state = TaskState(task_id="test", current_role=Role.FRONTDOOR)
        node = FrontdoorNode()

        await persistence.snapshot_node(state, node)
        store.save_graph_snapshot.assert_called_once()
        store.save_checkpoint.assert_not_called()

    @pytest.mark.asyncio
    async def test_snapshot_end(self):
        store = MagicMock()
        persistence = SQLiteStatePersistence(store, "session-001")

        state = TaskState(task_id="test")
        end = End(TaskResult(answer="done", success=True))

        await persistence.snapshot_end(state, end)
        store.save_graph_snapshot.assert_called_once()
        store.save_checkpoint.assert_not_called()

    @pytest.mark.asyncio
    async def test_load_next_returns_none(self):
        """load_next returns None (resume not yet implemented)."""
        store = MagicMock()
        persistence = SQLiteStatePersistence(store, "session-001")
        result = await persistence.load_next()
        assert result is None

    @pytest.mark.asyncio
    async def test_load_all_returns_snapshots(self):
        store = MagicMock()
        persistence = SQLiteStatePersistence(store, "session-001")

        state = TaskState(task_id="test")
        node = CoderNode()

        await persistence.snapshot_node(state, node)
        all_snaps = await persistence.load_all()
        assert len(all_snaps) == 1
        assert all_snaps[0]["type"] == "node"
        assert all_snaps[0]["node_class"] == "CoderNode"

    def test_write_with_no_store(self):
        """_write does nothing when store is None."""
        persistence = SQLiteStatePersistence(None, "session-001")
        persistence._write({"test": True})  # Should not raise

    @pytest.mark.asyncio
    async def test_record_run_context_manager(self):
        """record_run should work as an async context manager."""
        store = MagicMock()
        persistence = SQLiteStatePersistence(store, "session-001")
        async with persistence.record_run("run-001"):
            pass  # Should not raise


@pytest.fixture(autouse=True)
def _reset_features_after():
    """Reset features after each test in this module."""
    yield
    reset_features()


class TestFullStateSerialization:
    """Tests for _state_to_dict_full() (LangGraph pre-migration)."""

    def test_full_state_serialization(self):
        """Full serializer captures all dataclass fields minus skip set."""
        state = TaskState(
            task_id="t-full",
            prompt="long prompt",
            current_role=Role.CODER_ESCALATION,
            consecutive_failures=2,
            escalation_count=1,
            role_history=["frontdoor", "coder_escalation"],
            turns=5,
            last_error="err",
            last_output="out",
            last_code="print(1)",
            artifacts={"key": "val"},
        )
        d = _state_to_dict_full(state)

        # Must include core fields
        assert d["task_id"] == "t-full"
        assert d["prompt"] == "long prompt"  # no truncation
        assert d["turns"] == 5
        assert d["last_error"] == "err"  # no truncation
        assert d["artifacts"] == {"key": "val"}

        # Must have many more fields than the minimal 8
        assert len(d) > 20

    def test_full_state_handles_role_enum(self):
        state = TaskState(current_role=Role.CODER_ESCALATION)
        d = _state_to_dict_full(state)
        assert d["current_role"] == "coder_escalation"

    def test_full_state_skips_task_manager(self):
        state = TaskState()
        d = _state_to_dict_full(state)
        assert "task_manager" not in d
        assert "pending_approval" not in d

    def test_feature_flag_controls_detail(self):
        state = TaskState(task_id="t-flag", prompt="x" * 1000, last_error="e" * 500)

        # Flag off → minimal (8 keys)
        set_features(Features(state_history_snapshots=False))
        d_min = _state_to_dict(state)
        assert len(d_min) == 8
        assert len(d_min["prompt"]) == 500  # truncated

        # Flag on → full (many keys)
        set_features(Features(state_history_snapshots=True))
        d_full = _state_to_dict(state)
        assert len(d_full) > 20
        assert len(d_full["prompt"]) == 1000  # not truncated
