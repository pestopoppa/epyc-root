"""Direct tests for graph observability helper edge cases."""

from __future__ import annotations

from types import SimpleNamespace

from src.escalation import ErrorCategory
from src.graph.observability import _log_escalation, _record_failure


def test_record_failure_sets_last_failure_id_and_caps_severity():
    captured = {}

    class _FailureGraph:
        def record_failure(self, **kwargs):
            captured.update(kwargs)
            return "failure-123"

    ctx = SimpleNamespace(
        state=SimpleNamespace(
            task_id="task-1",
            current_role="worker",
            consecutive_failures=99,
            last_failure_id=None,
        ),
        deps=SimpleNamespace(failure_graph=_FailureGraph()),
    )

    result = _record_failure(ctx, ErrorCategory.TIMEOUT, "x" * 250)

    assert result == "failure-123"
    assert ctx.state.last_failure_id == "failure-123"
    assert captured["memory_id"] == "task-1"
    assert captured["severity"] == 5
    assert captured["symptoms"][0] == "timeout"
    assert len(captured["symptoms"][1]) == 100
    assert len(captured["description"]) <= len("worker failed: ") + 200


def test_log_escalation_still_updates_app_state_when_progress_logger_fails():
    events = []

    class _ProgressLogger:
        def log_escalation(self, **kwargs):
            raise RuntimeError("logger down")

    class _AppState:
        def record_escalation(self, from_role, to_role):
            events.append((from_role, to_role))

    ctx = SimpleNamespace(
        state=SimpleNamespace(task_id="task-1"),
        deps=SimpleNamespace(progress_logger=_ProgressLogger(), app_state=_AppState()),
    )

    _log_escalation(ctx, "frontdoor", "coder", "needs code")

    assert events == [("frontdoor", "coder")]
