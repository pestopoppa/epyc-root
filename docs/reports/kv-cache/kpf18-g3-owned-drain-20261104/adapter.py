#!/usr/bin/env python3
"""Fail-closed rowflow unit-entry gate for the unintegrated scratch adapter."""
import os
from pathlib import Path
import math
import sys
import time


def may_start_unit(stop_file: Path, deadline_epoch: float, *, now: float | None = None) -> bool:
    """A job may begin a new unit only before deadline and while STOP is absent."""
    current = time.time() if now is None else now
    return not stop_file.exists() and current < deadline_epoch


def rowflow_entry(env=None, *, now: float | None = None) -> tuple[bool, str]:
    """Apply filler_run15's exported job contract before starting one work unit.

    Missing or malformed grant fields fail closed. This is intended to be called
    at every unit boundary; it does not start work or manage child processes.
    """
    env = os.environ if env is None else env
    try:
        end = float(env["FILLER_END"])
        deadline = float(env["FILLER_DEADLINE"])
        stop = Path(env["FILLER_STOPFILE"])
    except (KeyError, TypeError, ValueError):
        return False, "missing-or-invalid-rowflow-contract"
    if not stop.is_absolute():
        return False, "invalid-stop-path"
    if not (math.isfinite(end) and math.isfinite(deadline) and deadline < end):
        return False, "invalid-rowflow-window"
    if stop.is_symlink():
        return False, "invalid-stop-path"
    if stop.exists():
        return False, "stop-file"
    current = time.time() if now is None else now
    if not math.isfinite(current) or current >= deadline:
        return False, "deadline"
    return True, "allowed"


if __name__ == "__main__":
    allowed, reason = rowflow_entry()
    print(reason, file=sys.stderr if not allowed else sys.stdout)
    raise SystemExit(0 if allowed else 78)
