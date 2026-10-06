"""Selected CJ fixture conformance only; inert package shells bypass eager imports.

Actual selected source/test modules remain unchanged. A noninstantiable sentinel
excludes the real LLMPrimitives class/getter branch, package initialization and
live backend schema compatibility from this fake-only validation.
"""
import os
import sys
import types
from pathlib import Path

root = Path.cwd()
for name, relative in (
    ("src", "src"),
    ("src.typed_decisions", "src/typed_decisions"),
    ("src.llm_primitives", "src/llm_primitives"),
):
    package = types.ModuleType(name)
    package.__path__ = [str(root / relative)]
    sys.modules[name] = package
    parent, _, child = name.rpartition(".")
    if parent:
        setattr(sys.modules[parent], child, package)

class _UnavailableRealPrimitives:
    def __new__(cls, *args, **kwargs):
        raise RuntimeError("real primitives unavailable in this fake-only runner")


sys.modules["src.llm_primitives"].LLMPrimitives = _UnavailableRealPrimitives

import pytest

raise SystemExit(pytest.main([
    "-o", "addopts=", "--noconftest", "-p", "no:cacheprovider", "-q",
    "tests/unit/test_typed_decisions_judge_redundancy.py",
    "--junitxml=" + os.environ["NI06_JUNIT_XML"],
]))
