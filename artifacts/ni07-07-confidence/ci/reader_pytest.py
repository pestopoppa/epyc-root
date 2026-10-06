#!/usr/bin/env python3
"""Run only the pinned fake-fixture tests with inert parent package shells."""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

app = Path(os.environ["NI07_RC10_APP_ROOT"]).resolve()
for name, relative in (("src", "src"), ("src.typed_decisions", "src/typed_decisions")):
    package = types.ModuleType(name)
    package.__path__ = [str(app / relative)]
    sys.modules[name] = package
    parent, _, child = name.rpartition(".")
    if parent:
        setattr(sys.modules[parent], child, package)

import pytest

raise SystemExit(
    pytest.main(
        [
            "-o",
            "addopts=",
            "--noconftest",
            "-p",
            "no:cacheprovider",
            "-q",
            "tests/unit/test_confidence_expectation.py",
            "--junitxml=" + os.environ["NI07_RC10_JUNIT_XML"],
        ]
    )
)
