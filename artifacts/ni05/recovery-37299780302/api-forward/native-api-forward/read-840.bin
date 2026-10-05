"""Focused unit tests for graph task-IR helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock


class TestExtractCandidateFilesFromTaskIr:
    def test_trims_deduplicates_and_stringifies_file_entries(self):
        from src.graph.task_ir_helpers import _extract_candidate_files_from_task_ir

        state = SimpleNamespace(
            task_ir={
                "plan": {
                    "steps": [
                        {"files": [" src/a.py ", "src/b.py", None, 123, "src/a.py"]},
                        {"files": ["src/c.py", ""]},
                    ]
                }
            }
        )

        assert _extract_candidate_files_from_task_ir(state) == [
            "src/a.py",
            "src/b.py",
            "None",
            "123",
            "src/c.py",
        ]

    def test_caps_output_at_ten_files(self):
        from src.graph.task_ir_helpers import _extract_candidate_files_from_task_ir

        state = SimpleNamespace(
            task_ir={
                "plan": {
                    "steps": [
                        {
                            "files": [f"src/file_{i}.py" for i in range(12)],
                        }
                    ]
                }
            }
        )

        result = _extract_candidate_files_from_task_ir(state)

        assert len(result) == 10
        assert result == [f"src/file_{i}.py" for i in range(10)]


class TestAutoSeedTasksFromTaskIr:
    def test_skips_non_list_steps(self):
        from src.graph.task_ir_helpers import _auto_seed_tasks_from_task_ir

        manager = MagicMock()
        manager.has_tasks.return_value = False
        state = SimpleNamespace(
            task_ir={"plan": {"steps": {"action": "Should not happen"}}},
            task_manager=manager,
            task_type="coding",
        )

        _auto_seed_tasks_from_task_ir(state)

        manager.create.assert_not_called()

    def test_skips_non_dict_steps(self):
        from src.graph.task_ir_helpers import _auto_seed_tasks_from_task_ir

        manager = MagicMock()
        manager.has_tasks.return_value = False
        state = SimpleNamespace(
            task_ir={
                "plan": {
                    "steps": [
                        {"id": "step-1", "action": "Investigate"},
                        "not-a-dict",
                    ]
                }
            },
            task_manager=manager,
            task_type="coding",
        )

        _auto_seed_tasks_from_task_ir(state)

        manager.create.assert_called_once_with(
            subject="Investigate",
            description="Investigate",
            active_form="Working on step 1",
            metadata={"source": "task_ir", "step_id": "step-1"},
            task_type="coding",
        )

    def test_seeds_only_non_empty_actions_and_preserves_step_id(self):
        from src.graph.task_ir_helpers import _auto_seed_tasks_from_task_ir

        manager = MagicMock()
        manager.has_tasks.return_value = False
        state = SimpleNamespace(
            task_ir={
                "plan": {
                    "steps": [
                        {"id": "step-1", "action": "  "},
                        {"id": "step-2", "action": "Investigate"},
                    ]
                }
            },
            task_manager=manager,
            task_type="coding",
        )

        _auto_seed_tasks_from_task_ir(state)

        manager.create.assert_called_once_with(
            subject="Investigate",
            description="Investigate",
            active_form="Working on step 2",
            metadata={"source": "task_ir", "step_id": "step-2"},
            task_type="coding",
        )

    def test_noops_when_task_manager_missing_or_tasks_exist(self):
        from src.graph.task_ir_helpers import _auto_seed_tasks_from_task_ir

        missing_manager = SimpleNamespace(task_ir={"plan": {"steps": [{"action": "Investigate"}]}})
        _auto_seed_tasks_from_task_ir(missing_manager)

        existing_manager = MagicMock()
        existing_manager.has_tasks.return_value = True
        state = SimpleNamespace(
            task_ir={"plan": {"steps": [{"action": "Investigate"}]}},
            task_manager=existing_manager,
        )

        _auto_seed_tasks_from_task_ir(state)
        existing_manager.create.assert_not_called()


class TestAutoGatherContext:
    def test_limits_to_ten_files_and_tracks_seen_files(self):
        from src.graph.task_ir_helpers import _auto_gather_context

        repl = MagicMock()
        repl._peek.side_effect = lambda _limit, file_path: f"content:{file_path}"
        ctx = SimpleNamespace(
            deps=SimpleNamespace(repl=repl),
            state=SimpleNamespace(gathered_files=["src/seen.py"]),
        )

        result = _auto_gather_context(
            ctx,
            [
                "src/seen.py",
                *[f"src/file_{i}.py" for i in range(12)],
            ],
        )

        assert "src/seen.py" not in result
        assert "src/file_0.py" in result
        assert "src/file_8.py" in result
        assert "src/file_9.py" not in result
        assert set(ctx.state.gathered_files) == {
            "src/seen.py",
            *[f"src/file_{i}.py" for i in range(9)],
        }
        assert len(ctx.state.gathered_files) == 10


class TestCheckAntiPattern:
    def test_uses_effective_mitigation_when_present(self):
        from src.graph.task_ir_helpers import _check_anti_pattern

        fg = MagicMock()
        match = SimpleNamespace(severity=5, description="Repeated timeout on coder")
        fg.find_matching_failures.return_value = [match]
        fg.get_effective_mitigations.return_value = [
            {"action": "switch_roles", "success_rate": 0.8}
        ]
        ctx = SimpleNamespace(
            deps=SimpleNamespace(failure_graph=fg),
            state=SimpleNamespace(
                consecutive_failures=3,
                last_error="timeout",
                current_role="coder",
            ),
        )

        result = _check_anti_pattern(ctx)

        assert result == "Recurring pattern seen before. Prior mitigation: switch_roles (success=80%)."

    def test_returns_none_when_failure_graph_reports_low_severity(self):
        from src.graph.task_ir_helpers import _check_anti_pattern

        fg = MagicMock()
        fg.find_matching_failures.return_value = [SimpleNamespace(severity=2, description="minor")]
        ctx = SimpleNamespace(
            deps=SimpleNamespace(failure_graph=fg),
            state=SimpleNamespace(
                consecutive_failures=2,
                last_error="timeout",
                current_role="worker",
            ),
        )

        assert _check_anti_pattern(ctx) is None

    def test_returns_none_when_no_matching_patterns(self):
        from src.graph.task_ir_helpers import _check_anti_pattern

        fg = MagicMock()
        fg.find_matching_failures.return_value = []
        ctx = SimpleNamespace(
            deps=SimpleNamespace(failure_graph=fg),
            state=SimpleNamespace(
                consecutive_failures=2,
                last_error="timeout",
                current_role="worker",
            ),
        )

        assert _check_anti_pattern(ctx) is None

    def test_returns_none_when_symptoms_are_empty(self):
        from src.graph.task_ir_helpers import _check_anti_pattern

        fg = MagicMock()
        fg.find_matching_failures.return_value = []
        ctx = SimpleNamespace(
            deps=SimpleNamespace(failure_graph=fg),
            state=SimpleNamespace(
                consecutive_failures=float("nan"),
                last_error="",
                current_role="worker",
            ),
        )

        assert _check_anti_pattern(ctx) is None
