#!/usr/bin/env python3
"""Fail-closed rowflow unit-entry gate for the unintegrated scratch adapter."""
import os
from pathlib import Path
import math
import sys
import time


def _stop_path_state(stop: Path) -> str:
    """Return an explicit fail-closed state for the STOP path and its parents."""
    if not stop.is_absolute() or stop == stop.parent:
        return "invalid-stop-path"
    # Inspect every component without following symlinks. A missing STOP leaf is
    # allowed, but every directory leading to it must exist and be usable.
    current = Path(stop.anchor)
    try:
        for component in stop.parent.parts[1:]:
            current = current / component
            st = current.lstat()
            if current.is_symlink() or not current.is_dir():
                return "invalid-stop-path"
            if not os.access(current, os.X_OK | os.R_OK):
                return "invalid-stop-path"
        if stop.is_symlink():
            return "invalid-stop-path"
        try:
            stop.lstat()
        except FileNotFoundError:
            return "missing"
        return "stop-file"
    except OSError:
        return "invalid-stop-path"


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
    stop_state = _stop_path_state(stop)
    if stop_state == "invalid-stop-path":
        return False, "invalid-stop-path"
    if stop_state == "stop-file":
        return False, "stop-file"
    current = time.time() if now is None else now
    if not math.isfinite(current) or current >= deadline:
        return False, "deadline"
    return True, "allowed"


if __name__ == "__main__":
    allowed, reason = rowflow_entry()
    print(reason, file=sys.stderr if not allowed else sys.stdout)
    raise SystemExit(0 if allowed else 78)
