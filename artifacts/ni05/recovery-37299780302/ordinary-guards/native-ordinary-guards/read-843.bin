"""Phase 1 (BEP harness): task-root override — default-off parity + active redirect.

Critical invariant: with ORCHESTRATOR_EDIT_ROOT unset, every accessor behaves exactly as
before (production unchanged). When set to an existing dir, model-facing relative paths
resolve under the task-root.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from src.repl_environment import task_root as TR


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv(TR.ENV_VAR, raising=False)


# ─── default-off parity (env unset) ──────────────────────────────────────────────

def test_inactive_when_unset():
    assert TR.task_root_active() is False


def test_get_task_root_unset_is_project_root():
    # falls back to project root (or cwd if config unavailable) — same as today
    root = TR.get_task_root()
    assert isinstance(root, Path)
    # not the empty/garbage value; it's an existing dir
    assert root.exists()


def test_resolve_task_path_unset_matches_realpath():
    # parity: identical to os.path.realpath for both relative + absolute
    assert TR.resolve_task_path("cart.py") == os.path.realpath("cart.py")
    assert TR.resolve_task_path("/etc/hostname") == os.path.realpath("/etc/hostname")


# ─── active (env set to an existing dir) ──────────────────────────────────────────

def test_active_when_set_to_existing_dir(monkeypatch, tmp_path):
    monkeypatch.setenv(TR.ENV_VAR, str(tmp_path))
    assert TR.task_root_active() is True
    assert TR.get_task_root() == tmp_path


def test_relative_path_resolves_under_task_root(monkeypatch, tmp_path):
    monkeypatch.setenv(TR.ENV_VAR, str(tmp_path))
    # relative task path → under scratch, NOT under cwd
    assert TR.resolve_task_path("cart.py") == os.path.realpath(str(tmp_path / "cart.py"))
    assert TR.resolve_task_path("pkg/mod.py") == os.path.realpath(str(tmp_path / "pkg/mod.py"))


def test_absolute_path_passes_through_when_active(monkeypatch, tmp_path):
    monkeypatch.setenv(TR.ENV_VAR, str(tmp_path))
    # absolute paths are NOT rebased onto task-root
    assert TR.resolve_task_path("/etc/hostname") == os.path.realpath("/etc/hostname")


# ─── safety: garbage / nonexistent override falls back (never silently mis-roots) ──

def test_nonexistent_dir_falls_back_to_project_root(monkeypatch, tmp_path):
    monkeypatch.setenv(TR.ENV_VAR, str(tmp_path / "does_not_exist"))
    assert TR.task_root_active() is False
    assert TR.get_task_root() == TR._project_root()
    # and relative resolution reverts to cwd parity
    assert TR.resolve_task_path("cart.py") == os.path.realpath("cart.py")


def test_empty_env_is_inactive(monkeypatch):
    monkeypatch.setenv(TR.ENV_VAR, "   ")
    assert TR.task_root_active() is False
