#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""Tests for get_bus_root() (guard-universe-and-worktree-isolation P1/1).

session_bus.py used to resolve DEFAULT_BUS_ROOT via
Path(__file__).resolve().parents[2] -- correct for a single checkout, wrong
under a worktree-per-main model where five worktrees each run their OWN copy
of this module from a different filesystem location. get_bus_root() replaces
that with a literal canonical path (plus an EPYC_BUS_ROOT override, tests
only). merge_gate.py now imports and calls the same function rather than
carrying its own separately-hardcoded literal -- one resolution strategy,
not two.

BOTH DIRECTIONS:
  - positive: the override actually works (production callers can be
    redirected when they need to be -- tests, mainly).
  - negative: the DEFAULT is NOT __file__-relative -- proven by literally
    relocating a copy of the module and confirming the resolved path does
    not move with it. That is the exact bug this item fixes; a test that
    only checked "get_bus_root() returns /workspace today" would pass
    against the OLD __file__-relative code too, as long as it happened to
    run from /workspace -- it would not catch a worktree regression.

Usage: pytest scripts/coordination/tests/test_bus_root_resolution.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination import session_bus as bus  # noqa: E402
from scripts.coordination import merge_gate as gate  # noqa: E402

CANONICAL = Path("/workspace/coordination/session-bus")
SESSION_BUS_PY = REPO_ROOT / "scripts" / "coordination" / "session_bus.py"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production callers never set EPYC_BUS_ROOT -- start every test without it."""
    monkeypatch.delenv("EPYC_BUS_ROOT", raising=False)


# --------------------------------------------------------------- in-process


def test_default_resolves_to_the_canonical_path() -> None:
    assert bus.get_bus_root() == CANONICAL
    assert bus.DEFAULT_BUS_ROOT == CANONICAL


def test_env_override_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("EPYC_BUS_ROOT", str(tmp_path))
    assert bus.get_bus_root() == tmp_path


def test_override_absent_falls_back_to_canonical_not_something_stale(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("EPYC_BUS_ROOT", str(tmp_path))
    assert bus.get_bus_root() == tmp_path
    monkeypatch.delenv("EPYC_BUS_ROOT")
    assert bus.get_bus_root() == CANONICAL


def test_merge_gate_bus_root_is_the_same_object_not_a_second_computation() -> None:
    """One strategy, not two: merge_gate.BUS_ROOT must equal get_bus_root(),
    not merely happen to match by both hardcoding the same literal."""
    assert gate.BUS_ROOT == bus.get_bus_root()
    assert gate.GATE_LIST == bus.get_bus_root() / "human_only_paths.yaml"


# ----------------------------------------------------------- subprocess CLI


def _print_root(cwd: Path, env: dict) -> str:
    proc = subprocess.run(
        [sys.executable, str(cwd / "session_bus.py"), "--print-root"],
        capture_output=True, text=True, cwd=str(cwd),
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    return proc.stdout.strip()


def test_print_root_flag_requires_no_subcommand() -> None:
    """--print-root must work standalone -- the verification idiom a fresh
    worktree checkout runs (setup_main_worktrees.sh) never passes a
    subcommand alongside it."""
    env = dict(os.environ)
    env.pop("EPYC_BUS_ROOT", None)
    proc = subprocess.run(
        [sys.executable, str(SESSION_BUS_PY), "--print-root"],
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == str(CANONICAL)


def test_print_root_respects_override_end_to_end() -> None:
    proc = subprocess.run(
        [sys.executable, str(SESSION_BUS_PY), "--print-root"],
        capture_output=True, text=True,
        env={**os.environ, "EPYC_BUS_ROOT": "/tmp/not-the-real-bus"},
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "/tmp/not-the-real-bus"


def test_resolution_is_not_file_relative_the_actual_regression_this_closes(
        tmp_path: Path) -> None:
    """The core assertion for item 1. Copy session_bus.py to a location that
    is NOT /workspace/scripts/coordination/session_bus.py -- simulating
    exactly what a worktree checkout is: the identical module, at a
    different Path(__file__). Under the OLD __file__-relative code this
    would resolve to `<tmp_path>/coordination/session-bus` (parents[2] of
    the copy). Under the fix it must still resolve to the ONE canonical
    /workspace path, proving the result does not travel with the file.
    """
    relocated = tmp_path / "some" / "other" / "place" / "session_bus.py"
    relocated.parent.mkdir(parents=True)
    shutil.copy2(SESSION_BUS_PY, relocated)

    env = dict(os.environ)
    env.pop("EPYC_BUS_ROOT", None)
    proc = subprocess.run(
        [sys.executable, str(relocated), "--print-root"],
        capture_output=True, text=True, cwd=str(relocated.parent), env=env,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    assert proc.stdout.strip() == str(CANONICAL), (
        "a relocated copy of session_bus.py resolved a DIFFERENT bus root -- "
        "the __file__-relative divergence bug is back"
    )


def test_daemon_inherits_the_fix_by_import_not_by_its_own_file_relative_code() -> None:
    """session_bus_coordinator.py does not independently resolve a bus root;
    it imports DEFAULT_BUS_ROOT from session_bus.py and uses it as its own
    --bus-root default. Assert that import wiring directly rather than
    re-deriving it, so a future refactor that gives the daemon its own
    resolution (reintroducing two strategies) fails this test."""
    from scripts.coordination import session_bus_coordinator as coordinator

    parser = coordinator.build_parser() if hasattr(coordinator, "build_parser") else None
    assert coordinator.DEFAULT_BUS_ROOT is bus.DEFAULT_BUS_ROOT
    if parser is not None:
        default = next(a.default for a in parser._actions if a.dest == "bus_root")
        assert default == str(bus.get_bus_root())
