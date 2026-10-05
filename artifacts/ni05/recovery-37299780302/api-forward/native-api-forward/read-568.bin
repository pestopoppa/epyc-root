"""Tests for the legacy orchestration tool registry adapter."""

from __future__ import annotations

from orchestration.tools.executor import ToolRegistry

LEGACY_ARCHITECT_ROLE = "architect" "_coding"


class _FakeExecutor:
    def __init__(self) -> None:
        self._tools = {
            "read_notes": {"name": "read_notes", "category": "data"},
            "run_tests": {"name": "run_tests", "category": "code"},
        }

    def get_tool_spec(self, tool_name: str) -> dict | None:
        return self._tools.get(tool_name)

    def list_tools(self) -> list[dict]:
        return list(self._tools.values())

    def execute(self, tool_name: str, **kwargs):
        return {"tool": tool_name, "kwargs": kwargs}


def test_legacy_architect_role_uses_live_architect_permissions() -> None:
    registry = ToolRegistry(_FakeExecutor())

    assert LEGACY_ARCHITECT_ROLE not in registry.ROLE_PERMISSIONS
    assert registry._check_permission("read_notes", LEGACY_ARCHITECT_ROLE) is True
    assert registry._check_permission("run_tests", LEGACY_ARCHITECT_ROLE) is False
    assert registry.list_tools(LEGACY_ARCHITECT_ROLE) == [
        {"name": "read_notes", "category": "data"}
    ]


def test_unknown_role_does_not_gain_permissions() -> None:
    registry = ToolRegistry(_FakeExecutor())

    assert registry._check_permission("read_notes", "unknown_role") is False
    assert registry.list_tools("unknown_role") == []
