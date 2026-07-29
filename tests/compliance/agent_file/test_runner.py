from __future__ import annotations

from pathlib import Path

from tests.compliance.agent_file.forbidden_actions import all_tasks as forbidden_tasks
from tests.compliance.agent_file.instruction_recall import all_tasks as recall_tasks
from tests.compliance.agent_file.procedure_correctness import all_tasks as procedure_tasks
from tests.compliance.agent_file.runner import make_fake_llm, run_compliance_suite


def test_perfect_fake_passes_all_current_tasks() -> None:
    suite = run_compliance_suite(
        model_id="fake-perfect",
        agent_file_path=Path("agents/shared/ENGINEERING_STANDARDS.md"),
        level="none",
        llm_call=make_fake_llm("perfect"),
    )

    assert suite.compliance_pass_rate == 1.0
    assert suite.procedure_pass_rate == 1.0
    assert suite.recall_pass_rate == 1.0
    assert all(result.pass_ for result in suite.forbidden_action_results)
    assert all(result.pass_ for result in suite.procedure_results)
    assert all(result.pass_ for result in suite.recall_results)


def test_blind_fake_fails_all_current_tasks() -> None:
    suite = run_compliance_suite(
        model_id="fake-blind",
        agent_file_path=Path("agents/shared/ENGINEERING_STANDARDS.md"),
        level="none",
        llm_call=make_fake_llm("blind"),
    )

    assert suite.compliance_pass_rate == 0.0
    assert suite.procedure_pass_rate == 0.0
    assert suite.recall_pass_rate == 0.0
    assert not any(result.pass_ for result in suite.forbidden_action_results)
    assert not any(result.pass_ for result in suite.procedure_results)
    assert not any(result.pass_ for result in suite.recall_results)


def test_phase2_task_pool_shape_stays_within_handoff_target() -> None:
    forbidden = forbidden_tasks()
    procedure = procedure_tasks()
    recall = recall_tasks()

    assert len(forbidden) == 15
    assert len(procedure) == 12
    assert len(recall) == 15
    assert len(forbidden) + len(procedure) + len(recall) == 42
    assert 30 <= len(forbidden) + len(procedure) + len(recall) <= 50

    all_tasks = forbidden + procedure + recall
    assert len({task.task_id for task in all_tasks}) == len(all_tasks)
    assert all(
        task.relevant_agent_file == "agents/shared/ENGINEERING_STANDARDS.md"
        for task in all_tasks
    )
