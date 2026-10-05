"""Tests for session analytics and token budgeting (B5)."""

from dataclasses import dataclass, field

from src.session_analytics import (
    SessionTokenBudget,
    compute_analytics,
    format_analytics,
)


# Mock TurnRecord for testing (avoids importing session_log)
@dataclass
class MockTurnRecord:
    turn: int = 0
    role: str = "frontdoor"
    outcome: str = "ok"
    tool_calls: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# SessionTokenBudget
# ---------------------------------------------------------------------------


class TestSessionTokenBudget:
    def test_unlimited_budget(self):
        budget = SessionTokenBudget(max_tokens=0)
        budget.record_tokens(1000, 500)
        status = budget.check()
        assert not status.should_compact
        assert not status.should_stop
        assert status.budget == 0
        assert status.used == 1500

    def test_below_threshold(self):
        budget = SessionTokenBudget(max_tokens=10000)
        budget.record_tokens(2000, 1000)
        status = budget.check()
        assert not status.should_compact
        assert not status.should_stop
        assert status.utilization < 0.7

    def test_compaction_trigger(self):
        budget = SessionTokenBudget(max_tokens=10000)
        budget.record_tokens(5000, 2500)  # 75%
        status = budget.check()
        assert status.should_compact
        assert not status.should_stop

    def test_hard_stop(self):
        budget = SessionTokenBudget(max_tokens=10000)
        budget.record_tokens(6000, 4500)  # 105%
        status = budget.check()
        assert status.should_compact
        assert status.should_stop
        assert "exhausted" in status.message

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_MAX_SESSION_TOKENS", "50000")
        budget = SessionTokenBudget.from_env()
        assert budget.max_tokens == 50000

    def test_from_env_default(self, monkeypatch):
        monkeypatch.delenv("ORCHESTRATOR_MAX_SESSION_TOKENS", raising=False)
        budget = SessionTokenBudget.from_env()
        assert budget.max_tokens == 0

    def test_cumulative_recording(self):
        budget = SessionTokenBudget(max_tokens=10000)
        budget.record_tokens(1000, 500)
        budget.record_tokens(2000, 700)
        assert budget.input_tokens == 3000
        assert budget.output_tokens == 1200
        assert budget.total_tokens == 4200

    def test_compaction_flag_set_once(self):
        budget = SessionTokenBudget(max_tokens=10000)
        budget.record_tokens(4000, 3500)  # 75%
        status1 = budget.check()
        assert status1.should_compact
        assert budget.compaction_triggered
        # Second check still shows should_compact but flag already set
        status2 = budget.check()
        assert status2.should_compact

    def test_remaining_calculation(self):
        budget = SessionTokenBudget(max_tokens=10000)
        budget.record_tokens(3000, 1000)
        status = budget.check()
        assert status.remaining == 6000


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class TestAnalytics:
    def test_compute_empty(self):
        result = compute_analytics([])
        assert result.total_turns == 0
        assert result.total_tool_calls == 0

    def test_compute_basic(self):
        records = [
            MockTurnRecord(turn=1, role="frontdoor", outcome="ok", tool_calls=["grep", "read"]),
            MockTurnRecord(turn=2, role="coder", outcome="ok", tool_calls=["execute"]),
            MockTurnRecord(turn=3, role="frontdoor", outcome="error"),
            MockTurnRecord(turn=4, role="architect", outcome="escalation"),
        ]
        result = compute_analytics(records)
        assert result.total_turns == 4
        assert result.total_tool_calls == 3
        assert result.tool_usage["grep"] == 1
        assert result.tool_usage["execute"] == 1
        assert result.error_count == 1
        assert result.escalation_count == 1
        assert result.role_distribution["frontdoor"] == 2

    def test_format_analytics(self):
        records = [
            MockTurnRecord(turn=1, role="frontdoor", outcome="ok", tool_calls=["grep"]),
            MockTurnRecord(turn=2, role="coder", outcome="ok", tool_calls=["execute"]),
        ]
        analytics = compute_analytics(records)
        report = format_analytics(analytics)
        assert "2 turns" in report
        assert "grep" in report
        assert "execute" in report
