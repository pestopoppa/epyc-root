from __future__ import annotations

from pathlib import Path

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
