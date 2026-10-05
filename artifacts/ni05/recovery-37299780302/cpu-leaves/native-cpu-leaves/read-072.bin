"""Regression tests for the autopilot dirty-tree fence (actions.py).

A file-mutating controller action must never commit — or write on top of —
pre-existing uncommitted changes in its commit target. The forge stages
per-file for ``code_mutation`` and ``structural_prune`` but stages the WHOLE
prompts dir for ``prompt_mutation`` / ``gepa_optimize``, so the guard scope
differs accordingly. The guard fires regardless of auto_commit and fails closed
on any git error.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUTOPILOT_DIR))

actions = importlib.import_module("actions")


# ── helper: _mutation_dirty_target_reason scoping ────────────────────────────


def _patch_pathspec(monkeypatch: pytest.MonkeyPatch, dirty: bool):
    """Make _pathspec_pending_change_report return `dirty` and record the
    pathspec it was asked about."""
    seen: list[Path] = []

    def fake(pathspec: Path) -> tuple[bool, str]:
        seen.append(pathspec)
        return dirty, f"pathspec={pathspec}; fake evidence"

    monkeypatch.setattr(actions, "_pathspec_pending_change_report", fake)
    return seen


def test_code_mutation_dirty_target_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _patch_pathspec(monkeypatch, dirty=True)
    reason = actions._mutation_dirty_target_reason(
        {"type": "code_mutation", "file": "src/api/routes/chat.py"}
    )
    assert reason is not None
    assert "chat.py" in reason
    # code_mutation checks the single resolved target file, not the prompts dir.
    assert len(seen) == 1
    assert seen[0] == (actions._REPO_ROOT / "src/api/routes/chat.py").resolve()


def test_code_mutation_clean_target_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_pathspec(monkeypatch, dirty=False)
    reason = actions._mutation_dirty_target_reason(
        {"type": "code_mutation", "file": "src/api/routes/chat.py"}
    )
    assert reason is None


def test_new_file_code_mutation_checks_parent_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _patch_pathspec(monkeypatch, dirty=False)
    reason = actions._mutation_dirty_target_reason(
        {
            "type": "code_mutation",
            "file": "src/generated/new_module.py",
            "mutation": "new_file",
        }
    )
    assert reason is None
    assert len(seen) == 1
    assert seen[0] == (actions._REPO_ROOT / "src/generated").resolve()


def test_new_file_code_mutation_dirty_parent_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _patch_pathspec(monkeypatch, dirty=True)
    reason = actions._mutation_dirty_target_reason(
        {
            "type": "code_mutation",
            "file": "src/generated/new_module.py",
            "mutation": "new_file",
        }
    )
    assert reason is not None
    assert "new_module.py" in reason
    assert len(seen) == 1
    assert seen[0] == (actions._REPO_ROOT / "src/generated").resolve()


def test_code_mutation_missing_file_defers_to_scope_validator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _patch_pathspec(monkeypatch, dirty=True)
    reason = actions._mutation_dirty_target_reason({"type": "code_mutation"})
    assert reason is None  # missing file -> scope validator's job, not the fence
    assert seen == []  # never queried git for an empty target


@pytest.mark.parametrize("action_type", ["prompt_mutation", "gepa_optimize"])
def test_prompt_dir_mutators_check_whole_prompts_dir(
    monkeypatch: pytest.MonkeyPatch, action_type: str
) -> None:
    # Even with a clean-looking individual file, a dirty SIBLING prompt must
    # block these, because the commit stages the whole prompts dir.
    seen = _patch_pathspec(monkeypatch, dirty=True)
    reason = actions._mutation_dirty_target_reason(
        {"type": action_type, "file": "frontdoor.md", "block": "## X"}
    )
    assert reason is not None
    assert "prompts dir" in reason
    assert "fake evidence" in reason
    assert len(seen) == 1
    assert seen[0] == actions._PROMPTS_DIR


@pytest.mark.parametrize("action_type", ["prompt_mutation", "gepa_optimize"])
def test_prompt_dir_mutators_clean_dir_passes(
    monkeypatch: pytest.MonkeyPatch, action_type: str
) -> None:
    _patch_pathspec(monkeypatch, dirty=False)
    reason = actions._mutation_dirty_target_reason(
        {"type": action_type, "file": "frontdoor.md", "block": "## X"}
    )
    assert reason is None


def test_structural_prune_checks_single_prompt_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = _patch_pathspec(monkeypatch, dirty=True)
    reason = actions._mutation_dirty_target_reason(
        {"type": "structural_prune", "file": "frontdoor.md", "block": "## X"}
    )
    assert reason is not None
    assert "frontdoor.md" in reason
    assert "fake evidence" in reason
    assert len(seen) == 1
    assert seen[0] == (actions._PROMPTS_DIR / "frontdoor.md").resolve()


def test_structural_prune_clean_target_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_pathspec(monkeypatch, dirty=False)
    reason = actions._mutation_dirty_target_reason(
        {"type": "structural_prune", "file": "frontdoor.md", "block": "## X"}
    )
    assert reason is None


@pytest.mark.parametrize("action_type", ["seed_batch", "deep_eval", "numeric_trial", "rollback"])
def test_non_mutating_actions_never_blocked(
    monkeypatch: pytest.MonkeyPatch, action_type: str
) -> None:
    # The fence must not even consult git for non-file-mutating actions.
    def boom(_pathspec):  # pragma: no cover - must not be called
        raise AssertionError("git checked for a non-mutating action")

    monkeypatch.setattr(actions, "_pathspec_has_pending_changes", boom)
    assert actions._mutation_dirty_target_reason({"type": action_type}) is None


def test_pathspec_helper_fails_closed_on_git_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raising_run(*_a, **_k):
        raise OSError("git not available")

    monkeypatch.setattr(actions.subprocess, "run", raising_run)
    # Fail closed: an error must read as "dirty" so the mutation is skipped.
    assert actions._pathspec_has_pending_changes(Path("/whatever")) is True
    dirty, evidence = actions._pathspec_pending_change_report(Path("/whatever"))
    assert dirty is True
    assert "git status raised OSError" in evidence


def test_pathspec_helper_nonzero_returncode_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _R:
        returncode = 128
        stdout = ""
        stderr = "fatal: bad pathspec"

    monkeypatch.setattr(actions.subprocess, "run", lambda *a, **k: _R())
    assert actions._pathspec_has_pending_changes(Path("/whatever")) is True
    dirty, evidence = actions._pathspec_pending_change_report(Path("/whatever"))
    assert dirty is True
    assert "rc=128" in evidence
    assert "fatal: bad pathspec" in evidence


def test_pathspec_helper_clean_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    class _R:
        returncode = 0
        stdout = "   \n"  # whitespace only == clean
        stderr = ""

    monkeypatch.setattr(actions.subprocess, "run", lambda *a, **k: _R())
    assert actions._pathspec_has_pending_changes(Path("/whatever")) is False
    dirty, evidence = actions._pathspec_pending_change_report(Path("/whatever"))
    assert dirty is False
    assert "git status clean" in evidence


def test_pathspec_report_includes_status_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _R:
        returncode = 0
        stdout = " M orchestration/prompts/frontdoor.md\n?? orchestration/prompts/tmp.md\n"
        stderr = ""

    monkeypatch.setattr(actions.subprocess, "run", lambda *a, **k: _R())
    dirty, evidence = actions._pathspec_pending_change_report(Path("orchestration/prompts"))
    assert dirty is True
    assert "M orchestration/prompts/frontdoor.md" in evidence
    assert "?? orchestration/prompts/tmp.md" in evidence


# ── dispatch_action routing: fence -> skipped trial, handler not reached ──────


def test_dispatch_action_routes_dirty_mutation_to_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Fence reports dirty; the handler must never run and dispatch returns the
    # skipped-trial shape (SkipOutcome, action_type) so the main loop journals
    # the fence reason instead of silently dropping it.
    called = {"handler": False}

    def fake_handler(_action, _ctx):  # pragma: no cover - must not be called
        called["handler"] = True
        return ("RESULT", "prompt_forge")

    monkeypatch.setitem(actions._ACTION_HANDLERS, "code_mutation", fake_handler)
    monkeypatch.setattr(actions, "_mutation_dirty_target_reason", lambda _a: "dirty target")

    result, species = actions.dispatch_action(
        {"type": "code_mutation", "file": "src/api/routes/chat.py"},
        seeder=None,
        swarm=None,
        forge=None,
        lab=None,
        tower=None,
        gate=None,
        archive=None,
        journal=None,
        state={},
    )
    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert "Dirty-tree fence" in result.reason
    assert species == "code_mutation"
    assert called["handler"] is False


def test_dispatch_action_allows_clean_mutation_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # When the fence is clean, dispatch proceeds to the handler.
    called = {"handler": False}

    def fake_handler(_action, _ctx):
        called["handler"] = True
        return ("RESULT", "prompt_forge")

    monkeypatch.setitem(actions._ACTION_HANDLERS, "code_mutation", fake_handler)
    monkeypatch.setattr(actions, "_mutation_dirty_target_reason", lambda _a: None)

    result, species = actions.dispatch_action(
        {"type": "code_mutation", "file": "src/api/routes/chat.py"},
        seeder=None,
        swarm=None,
        forge=None,
        lab=None,
        tower=None,
        gate=None,
        archive=None,
        journal=None,
        state={},
    )
    assert called["handler"] is True
    assert result == "RESULT"
