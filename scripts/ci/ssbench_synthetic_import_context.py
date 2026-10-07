"""Hosted synthetic import context using the unchanged existing APP fixture.

No physical capacity, kernel store, deployment or live topology warrant.
"""
from __future__ import annotations
import importlib
import os
from pathlib import Path
import tempfile
import pytest

_fixture = None
_patch = None
_temporary = None

def pytest_configure(config):
    global _fixture, _patch, _temporary
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("SSBENCH_SYNTHETIC_IMPORT_CONTEXT") != "existing_fixture_1tib_import_only":
        raise RuntimeError("synthetic import context is restricted to the bound hosted capture")
    source = Path(os.environ["SSBENCH_APP_SOURCE"]).resolve()
    module = importlib.import_module("tests.unit.test_stack_change_guard")
    expected = source / "tests/unit/test_stack_change_guard.py"
    if Path(module.__file__).resolve() != expected:
        raise RuntimeError("existing synthetic fixture module identity differs")
    function = module._synthetic_stack_manifest_inputs._get_wrapped_function()
    if Path(function.__code__.co_filename).resolve() != expected:
        raise RuntimeError("existing fixture callable identity differs")
    _patch = pytest.MonkeyPatch()
    _temporary = tempfile.TemporaryDirectory(prefix="ssbench-synthetic-import-", dir=os.environ["RUNNER_TEMP"])
    _fixture = function(monkeypatch=_patch, tmp_path=Path(_temporary.name))
    try:
        next(_fixture)
    except BaseException:
        pytest_unconfigure(config)
        raise

def pytest_unconfigure(config):
    global _fixture, _patch, _temporary
    try:
        if _fixture is not None:
            _fixture.close()
    finally:
        if _patch is not None:
            _patch.undo()
        if _temporary is not None:
            _temporary.cleanup()
        _fixture = _patch = _temporary = None
