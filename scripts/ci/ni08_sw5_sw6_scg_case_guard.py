"""Require the four complete reviewed modules and exact AST-derived JUnit names."""
from __future__ import annotations

import json
import os
from pathlib import Path
import pytest

SELECTED_FILES = {
    "tests/unit/test_registry_compiler.py",
    "tests/unit/test_env_attestation.py",
    "tests/unit/test_diag_env_override.py",
    "tests/unit/test_ufh12_arms.py",
}


def pytest_collection_finish(session):
    manifest_path = Path(os.environ["NI08_SW_SCG_EXPECTED_CASES"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {(row["classname"], row["name"]) for row in manifest["expected_cases"]}
    actual = []
    selected = set()
    for item in session.items:
        path = Path(str(item.path)).as_posix()
        selected_file = next((candidate for candidate in SELECTED_FILES
                              if path.endswith("/" + candidate)), None)
        if selected_file is None:
            continue
        selected.add(selected_file)
        classname = Path(selected_file).with_suffix("").as_posix().replace("/", ".")
        actual.append((classname, item.name))
    problems = []
    if selected != SELECTED_FILES:
        problems.append(f"selected module set differs: expected={sorted(SELECTED_FILES)} actual={sorted(selected)}")
    if len(actual) != len(expected) or len(set(actual)) != len(actual) or set(actual) != expected:
        problems.append(f"exact selected case identities differ: expected={len(expected)} actual={len(actual)}")
    if problems:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter is not None:
            for problem in problems:
                reporter.write_line("NI08 SW5/SW6/SCG COLLECTION GUARD: " + problem, red=True)
        raise pytest.UsageError("; ".join(problems))
