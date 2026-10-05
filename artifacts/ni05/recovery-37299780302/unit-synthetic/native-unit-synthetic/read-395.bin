"""Tests for graph helper modules extracted from helpers.py.

Covers task_ir_helpers, decision_gates, and compaction — the three
extracted modules with the lowest test coverage.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from src.escalation import ErrorCategory


# ── task_ir_helpers ──────────────────────────────────────────────────────


class TestExtractCandidateFiles:
    """Tests for _extract_candidate_files_from_task_ir."""

    def test_empty_task_ir(self):
        from src.graph.task_ir_helpers import _extract_candidate_files_from_task_ir

        state = MagicMock()
        state.task_ir = {}
        assert _extract_candidate_files_from_task_ir(state) == []

    def test_none_task_ir(self):
        from src.graph.task_ir_helpers import _extract_candidate_files_from_task_ir

        state = MagicMock()
        state.task_ir = None
        assert _extract_candidate_files_from_task_ir(state) == []

    def test_extracts_files_from_steps(self):
        from src.graph.task_ir_helpers import _extract_candidate_files_from_task_ir

        state = MagicMock()
        state.task_ir = {
            "plan": {
                "steps": [
                    {"action": "edit", "files": ["src/foo.py", "src/bar.py"]},
                    {"action": "test", "files": ["tests/test_foo.py"]},
                ]
            }
        }
        result = _extract_candidate_files_from_task_ir(state)
        assert result == ["src/foo.py", "src/bar.py", "tests/test_foo.py"]

    def test_deduplicates(self):
        from src.graph.task_ir_helpers import _extract_candidate_files_from_task_ir

        state = MagicMock()
        state.task_ir = {
            "plan": {
                "steps": [
                    {"action": "a", "files": ["src/foo.py"]},
                    {"action": "b", "files": ["src/foo.py"]},
                ]
            }
        }
        assert _extract_candidate_files_from_task_ir(state) == ["src/foo.py"]

    def test_caps_at_10(self):
        from src.graph.task_ir_helpers import _extract_candidate_files_from_task_ir

        state = MagicMock()
        state.task_ir = {
            "plan": {"steps": [{"action": "a", "files": [f"f{i}.py" for i in range(20)]}]}
        }
        assert len(_extract_candidate_files_from_task_ir(state)) == 10

    def test_skips_non_dict_steps(self):
        from src.graph.task_ir_helpers import _extract_candidate_files_from_task_ir

        state = MagicMock()
        state.task_ir = {"plan": {"steps": ["not a dict", {"action": "a", "files": ["ok.py"]}]}}
        assert _extract_candidate_files_from_task_ir(state) == ["ok.py"]


class TestAutoSeedTasks:
    """Tests for _auto_seed_tasks_from_task_ir."""

    def test_seeds_from_plan(self):
        from src.graph.task_ir_helpers import _auto_seed_tasks_from_task_ir

        manager = MagicMock()
        manager.has_tasks.return_value = False

        state = MagicMock()
        state.task_ir = {
            "plan": {"steps": [{"action": "Write foo", "id": "s1"}, {"action": "Test foo", "id": "s2"}]}
        }
        state.task_manager = manager
        state.task_type = "coding"

        _auto_seed_tasks_from_task_ir(state)
        assert manager.create.call_count == 2

    def test_skips_when_tasks_exist(self):
        from src.graph.task_ir_helpers import _auto_seed_tasks_from_task_ir

        manager = MagicMock()
        manager.has_tasks.return_value = True

        state = MagicMock()
        state.task_ir = {"plan": {"steps": [{"action": "Write foo"}]}}
        state.task_manager = manager

        _auto_seed_tasks_from_task_ir(state)
        manager.create.assert_not_called()

    def test_skips_empty_actions(self):
        from src.graph.task_ir_helpers import _auto_seed_tasks_from_task_ir

        manager = MagicMock()
        manager.has_tasks.return_value = False

        state = MagicMock()
        state.task_ir = {"plan": {"steps": [{"action": ""}, {"action": "Real task"}]}}
        state.task_manager = manager
        state.task_type = "coding"

        _auto_seed_tasks_from_task_ir(state)
        assert manager.create.call_count == 1


class TestAutoGatherContext:
    """Tests for _auto_gather_context."""

    def test_returns_empty_without_repl(self):
        from src.graph.task_ir_helpers import _auto_gather_context

        ctx = MagicMock()
        ctx.deps.repl = None
        assert _auto_gather_context(ctx, ["foo.py"]) == ""

    def test_returns_empty_without_files(self):
        from src.graph.task_ir_helpers import _auto_gather_context

        ctx = MagicMock()
        ctx.deps.repl = MagicMock()
        assert _auto_gather_context(ctx, []) == ""

    def test_gathers_file_content(self):
        from src.graph.task_ir_helpers import _auto_gather_context

        ctx = MagicMock()
        ctx.deps.repl._peek.return_value = "def hello(): pass"
        ctx.state.gathered_files = []

        result = _auto_gather_context(ctx, ["src/hello.py"])
        assert "src/hello.py" in result
        assert "def hello(): pass" in result

    def test_handles_peek_failure(self):
        from src.graph.task_ir_helpers import _auto_gather_context

        ctx = MagicMock()
        ctx.deps.repl._peek.side_effect = RuntimeError("file not found")
        ctx.state.gathered_files = []

        result = _auto_gather_context(ctx, ["missing.py"])
        assert "[Could not read]" in result

    def test_skips_already_gathered(self):
        from src.graph.task_ir_helpers import _auto_gather_context

        ctx = MagicMock()
        ctx.deps.repl._peek.return_value = "content"
        ctx.state.gathered_files = ["already.py"]

        result = _auto_gather_context(ctx, ["already.py"])
        assert result == ""
        ctx.deps.repl._peek.assert_not_called()


class TestCheckAntiPattern:
    """Tests for _check_anti_pattern."""

    def test_returns_none_without_failure_graph(self):
        from src.graph.task_ir_helpers import _check_anti_pattern

        ctx = MagicMock()
        ctx.deps.failure_graph = None
        assert _check_anti_pattern(ctx) is None

    def test_returns_none_without_errors(self):
        from src.graph.task_ir_helpers import _check_anti_pattern

        ctx = MagicMock()
        ctx.deps.failure_graph = MagicMock()
        ctx.state.consecutive_failures = 0
        ctx.state.last_error = ""
        assert _check_anti_pattern(ctx) is None

    def test_returns_mitigation_for_recurring_pattern(self):
        from src.graph.task_ir_helpers import _check_anti_pattern

        fg = MagicMock()
        match = MagicMock()
        match.severity = 5
        match.description = "Timeout on coder_escalation"
        fg.find_matching_failures.return_value = [match]
        fg.get_effective_mitigations.return_value = [
            {"action": "switch_to_architect", "success_rate": 0.75}
        ]

        ctx = MagicMock()
        ctx.deps.failure_graph = fg
        ctx.state.consecutive_failures = 3
        ctx.state.last_error = "Timeout"
        ctx.state.current_role = "coder"

        result = _check_anti_pattern(ctx)
        assert "switch_to_architect" in result
        assert "75%" in result

    def test_returns_description_without_mitigations(self):
        from src.graph.task_ir_helpers import _check_anti_pattern

        fg = MagicMock()
        match = MagicMock()
        match.severity = 5
        match.description = "Repeated schema failure"
        fg.find_matching_failures.return_value = [match]
        fg.get_effective_mitigations.return_value = []

        ctx = MagicMock()
        ctx.deps.failure_graph = fg
        ctx.state.consecutive_failures = 2
        ctx.state.last_error = ""
        ctx.state.current_role = "worker"

        result = _check_anti_pattern(ctx)
        assert "Recurring pattern" in result

    def test_returns_none_for_low_severity(self):
        from src.graph.task_ir_helpers import _check_anti_pattern

        fg = MagicMock()
        match = MagicMock()
        match.severity = 1
        fg.find_matching_failures.return_value = [match]

        ctx = MagicMock()
        ctx.deps.failure_graph = fg
        ctx.state.consecutive_failures = 2
        ctx.state.last_error = "minor"
        ctx.state.current_role = "worker"

        assert _check_anti_pattern(ctx) is None

    def test_handles_exception_gracefully(self):
        from src.graph.task_ir_helpers import _check_anti_pattern

        fg = MagicMock()
        fg.find_matching_failures.side_effect = RuntimeError("graph error")

        ctx = MagicMock()
        ctx.deps.failure_graph = fg
        ctx.state.consecutive_failures = 3
        ctx.state.last_error = "error"
        ctx.state.current_role = "worker"

        assert _check_anti_pattern(ctx) is None


# ── decision_gates ──────────────────────────────────────────────────────


class TestShouldEscalate:
    """Tests for _should_escalate."""

    def _make_ctx(self, **overrides):
        ctx = MagicMock()
        ctx.deps.config.no_escalate_categories = {ErrorCategory.FORMAT}
        ctx.deps.config.max_escalations = 3
        ctx.deps.config.max_retries = 2
        ctx.state.escalation_count = 0
        ctx.state.consecutive_failures = 3
        ctx.state.last_error = ""
        ctx.state.role_history = ["worker"]
        for k, v in overrides.items():
            setattr(ctx.state, k, v)
        return ctx

    def test_no_escalate_for_format_errors(self):
        from src.graph.decision_gates import _should_escalate
        from src.roles import Role

        ctx = self._make_ctx()
        assert _should_escalate(ctx, ErrorCategory.FORMAT, Role.CODER_ESCALATION) is False

    def test_no_escalate_without_next_tier(self):
        from src.graph.decision_gates import _should_escalate

        ctx = self._make_ctx()
        assert _should_escalate(ctx, ErrorCategory.CODE, None) is False

    def test_no_escalate_at_max_escalations(self):
        from src.graph.decision_gates import _should_escalate
        from src.roles import Role

        ctx = self._make_ctx(escalation_count=3)
        assert _should_escalate(ctx, ErrorCategory.CODE, Role.CODER_ESCALATION) is False

    def test_escalates_after_max_retries(self):
        from src.graph.decision_gates import _should_escalate
        from src.roles import Role

        ctx = self._make_ctx(consecutive_failures=3)
        with patch("src.graph.decision_gates._detect_role_cycle_impl", return_value=False):
            assert _should_escalate(ctx, ErrorCategory.CODE, Role.CODER_ESCALATION) is True

    def test_no_escalate_before_max_retries(self):
        from src.graph.decision_gates import _should_escalate
        from src.roles import Role

        ctx = self._make_ctx(consecutive_failures=1)
        with patch("src.graph.decision_gates._detect_role_cycle_impl", return_value=False):
            assert _should_escalate(ctx, ErrorCategory.CODE, Role.CODER_ESCALATION) is False

    def test_no_escalate_on_role_cycle(self):
        from src.graph.decision_gates import _should_escalate
        from src.roles import Role

        ctx = self._make_ctx(consecutive_failures=3)
        with patch("src.graph.decision_gates._detect_role_cycle_impl", return_value=True):
            assert _should_escalate(ctx, ErrorCategory.CODE, Role.CODER_ESCALATION) is False

    def test_schema_escalate_on_capability_gap(self):
        from src.graph.decision_gates import _should_escalate
        from src.roles import Role

        ctx = self._make_ctx(consecutive_failures=3, last_error="validation failed: required property missing")
        assert _should_escalate(ctx, ErrorCategory.SCHEMA, Role.CODER_ESCALATION) is True

    def test_schema_no_escalate_on_parser_error(self):
        from src.graph.decision_gates import _should_escalate
        from src.roles import Role

        ctx = self._make_ctx(consecutive_failures=3, last_error="json decode error at line 5")
        assert _should_escalate(ctx, ErrorCategory.SCHEMA, Role.CODER_ESCALATION) is False

    def test_schema_no_escalate_without_next_tier(self):
        from src.graph.decision_gates import _should_escalate

        ctx = self._make_ctx(consecutive_failures=3, last_error="validation failed")
        assert _should_escalate(ctx, ErrorCategory.SCHEMA, None) is False


class TestShouldRetry:
    """Tests for _should_retry."""

    def test_no_retry_on_timeout(self):
        from src.graph.decision_gates import _should_retry
        from src.escalation import ErrorCategory

        ctx = MagicMock()
        assert _should_retry(ctx, ErrorCategory.TIMEOUT) is False

    def test_retry_when_under_max(self):
        from src.graph.decision_gates import _should_retry
        from src.escalation import ErrorCategory

        ctx = MagicMock()
        ctx.state.consecutive_failures = 1
        ctx.deps.config.max_retries = 3
        assert _should_retry(ctx, ErrorCategory.CODE) is True

    def test_no_retry_at_max(self):
        from src.graph.decision_gates import _should_retry
        from src.escalation import ErrorCategory

        ctx = MagicMock()
        ctx.state.consecutive_failures = 3
        ctx.deps.config.max_retries = 3
        assert _should_retry(ctx, ErrorCategory.CODE) is False


class TestTimeoutSkip:
    """Tests for _timeout_skip."""

    def test_skips_optional_gate(self):
        from src.graph.decision_gates import _timeout_skip

        ctx = MagicMock()
        ctx.deps.config.optional_gates = ["vision", "pdf"]
        assert _timeout_skip(ctx, "vision processing timed out") is True

    def test_no_skip_for_required(self):
        from src.graph.decision_gates import _timeout_skip

        ctx = MagicMock()
        ctx.deps.config.optional_gates = ["vision"]
        assert _timeout_skip(ctx, "inference timed out") is False


class TestCheckApprovalGate:
    """Tests for _check_approval_gate."""

    def test_approved_when_gates_disabled(self):
        from src.graph.decision_gates import _check_approval_gate

        ctx = MagicMock()
        with patch("src.features.features") as mock_feat:
            mock_feat.return_value.approval_gates = False
            assert _check_approval_gate(ctx, "worker", "architect", "test") is True
