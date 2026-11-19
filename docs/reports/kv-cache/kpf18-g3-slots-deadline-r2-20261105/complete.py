#!/usr/bin/env python3
"""Fail closed unless the declared synthetic qualification result is complete."""
import json
import os
from pathlib import Path
import sys
try:
    result = json.loads(Path(os.environ["SLOTS_RESULT"]).read_text())
    assert result["schema"] == "kpf18.slots-transport-qualification.v1"
    assert result["status"] == "PASS"
    assert result["tests"] == 11 and result["failures"] == 0 and result["errors"] == 0
    assert len(result["observations"]) == 6
    assert all(len(value) == 64 for value in result["inputs"].values())
except (OSError, ValueError, KeyError, TypeError, AssertionError):
    sys.exit(1)
