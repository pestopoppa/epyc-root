from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "validate"
    / "check_stack_fact_migration_discipline.py"
)
_SPEC = importlib.util.spec_from_file_location(
    "check_stack_fact_migration_discipline",
    _SCRIPT,
)
assert _SPEC and _SPEC.loader
check_stack_fact_migration_discipline = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = check_stack_fact_migration_discipline
_SPEC.loader.exec_module(check_stack_fact_migration_discipline)


def _check(paths: list[str]) -> list[str]:
    return check_stack_fact_migration_discipline.check_stack_fact_migration_discipline(
        paths
    )


def test_non_stack_fact_change_passes() -> None:
    assert _check(["handoffs/active/orchestration-robustness-audit-2026-07-11.md"]) == []


def test_stack_fact_change_without_contract_fails() -> None:
    errors = _check(["scripts/server/stack_manifest.py"])

    assert len(errors) == 1
    assert "scripts/server/stack_manifest.py" in errors[0]
    assert "tests/unit/test_stack_numa_reader_agreement.py" in errors[0]


def test_stack_fact_change_with_reader_agreement_passes() -> None:
    assert _check(
        [
            "scripts/server/stack_manifest.py",
            "tests/unit/test_stack_numa_reader_agreement.py",
        ]
    ) == []


def test_orchestrator_prefixed_paths_normalize() -> None:
    errors = _check(["epyc-orchestrator/src/config/stack_templates.py"])

    assert len(errors) == 1
    assert "src/config/stack_templates.py" in errors[0]


def test_absolute_paths_under_repo_root_normalize(tmp_path: Path) -> None:
    source = tmp_path / "scripts" / "server" / "orchestrator_stack.py"
    companion = tmp_path / "tests" / "unit" / "test_stack_manifest_imports.py"

    errors = check_stack_fact_migration_discipline.check_stack_fact_migration_discipline(
        [str(source), str(companion)],
        repo_root=tmp_path,
    )

    assert errors == []
