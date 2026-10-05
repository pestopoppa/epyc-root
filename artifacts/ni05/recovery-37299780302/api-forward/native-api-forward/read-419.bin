"""INF-78 scoped exception (operator 2026-09-25): architect REPL only for task-scoped requests."""
from src.roles import Role, architect_repl_allowed
from scripts.benchmark.seeding_types import ARCHITECT_MODES, architect_modes


def test_architect_repl_needs_task_root():
    assert architect_repl_allowed(Role.ARCHITECT_GENERAL, task_root="/mnt/raid0/llm/tmp/lane")
    assert not architect_repl_allowed(Role.ARCHITECT_GENERAL, task_root=None)
    assert not architect_repl_allowed("architect_general")
    assert not architect_repl_allowed(Role.ARCHITECT_CRITIC)


def test_non_architect_roles_unaffected():
    assert architect_repl_allowed(Role.FRONTDOOR)
    assert architect_repl_allowed("frontdoor", task_root=None)
    assert architect_repl_allowed(None)


def test_seeding_modes():
    assert "repl" not in ARCHITECT_MODES
    assert architect_modes() == {"direct", "delegated"}
    assert architect_modes(task_scoped=True) == {"direct", "delegated", "repl"}
