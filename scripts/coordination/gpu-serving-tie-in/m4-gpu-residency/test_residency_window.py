"""Source-level tests for the candidate, independent of the server runtime.

Set M4_GPU_SWEEP_SOURCE to the patched candidate, never the production tree.
These controls exercise the actual helper AST, not a second implementation.
"""
import ast
import os
from pathlib import Path

import pytest


@pytest.fixture
def inside():
    path = Path(os.environ["M4_GPU_SWEEP_SOURCE"])
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "residency_sample_inside_batch"]
    assert len(functions) == 1
    module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), functions[0]], type_ignores=[])
    namespace = {}
    exec(compile(ast.fix_missing_locations(module), str(path), "exec"), namespace)
    return namespace["residency_sample_inside_batch"]


def sample(start, end, pid=42):
    return {"pid": pid, "sample_start_monotonic_ns": start, "sample_end_monotonic_ns": end}


@pytest.mark.parametrize("samples,expected", [
    ([sample(120, 130)], True),
    ([sample(100, 200)], True),
    ([sample(80, 90)], False),
    ([sample(210, 220)], False),
    ([sample(90, 110)], False),
    ([sample(190, 210)], False),
    ([sample(130, 120)], False),
    ([sample(120, 130, 43)], False),
    ([{"pid": 42}], False),
    ([sample(True, 130)], False),
    ([sample(80, 90), sample(120, 130)], True),
])
def test_sample_is_wholly_inside_batch(inside, samples, expected):
    assert inside(samples, pid=42, batch_start_ns=100, batch_end_ns=200) is expected


def test_invalid_window_rejected(inside):
    assert not inside([sample(120, 130)], pid=42, batch_start_ns=200, batch_end_ns=100)
    assert not inside([sample(120, 130)], pid=0, batch_start_ns=100, batch_end_ns=200)
