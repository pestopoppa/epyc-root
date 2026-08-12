#!/usr/bin/env python3
"""Tests for install_git_hooks.sh's worktree-correct HOOK_SRC_DIR resolution
(guard-universe-and-worktree-isolation P1/3a).

The OLD emitted pre-commit wrapper baked HOOK_SRC_DIR="/workspace/scripts/
hooks" in at GENERATION time (heredoc variable interpolation), unconditionally,
for every repo and every worktree -- but .git/hooks/ is shared across every
worktree of a repo (one file, many worktrees), so it has to resolve at
RUNTIME which worktree is actually committing. The fix is a priority cascade:
  1. EPYC_HOOK_SRC_DIR (test-only override)
  2. the committing worktree's own scripts/hooks, if it has pii_precommit.sh
  3. the git-common-dir's primary tree (sparse-worktree fallback)
  4. literal /workspace/scripts/hooks, last resort only -- needed because the
     sibling repos (epyc-orchestrator, epyc-inference-research) have never
     carried their own copy of these two shared governance hooks and have no
     git relationship to epyc-root through which to discover its location.

Each tier gets its own test, both directions where meaningful (the tier
fires AND does not leak into a sibling context it shouldn't affect).

Usage: pytest scripts/hooks/tests/test_hook_worktree_resolution.py
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALLER = REPO_ROOT / "scripts" / "hooks" / "install_git_hooks.sh"
INSTALLED_HOOK = REPO_ROOT / ".git" / "hooks" / "pre-commit"

# Assembled from two literals, not written whole: a single literal would
# itself match pii_precommit.sh's AKIA[0-9A-Z]{16} pattern and block every
# commit of THIS FILE. Same trick as test_precommit_wrapper.sh's BAD_BLOB
# and setup_main_worktrees.sh's bad_blob. Not a real credential.
BAD_BLOB = "AKIA" "1234567890ABCDEF"


@pytest.fixture(scope="module", autouse=True)
def _fresh_install() -> Iterator[None]:
    """Guarantee the installed hook reflects the CURRENT source before any
    test in this module runs — install_git_hooks.sh is idempotent and
    already proven safe to re-run (item 3a's own commit)."""
    subprocess.run(["bash", str(INSTALLER)], cwd=str(REPO_ROOT),
                    check=True, capture_output=True, text=True)
    yield


def _stage_and_run(repo: Path, content: str, env: dict | None = None) -> int:
    """Stage a scratch file with `content`, run the INSTALLED hook against
    it with cwd=repo, then unstage and remove the scratch file -- never
    commits, so the repo's real history is untouched regardless of outcome."""
    scratch = repo / ".hook-resolution-scratch"
    scratch.write_text(content + "\n")
    subprocess.run(["git", "-C", str(repo), "add", ".hook-resolution-scratch"],
                    check=True, capture_output=True, text=True)
    try:
        proc = subprocess.run(
            ["bash", str(INSTALLED_HOOK)], cwd=str(repo),
            capture_output=True, text=True,
            env={**os.environ, **(env or {})},
        )
        return proc.returncode
    finally:
        subprocess.run(["git", "-C", str(repo), "reset", "-q", "HEAD", "--",
                         ".hook-resolution-scratch"], capture_output=True)
        scratch.unlink(missing_ok=True)


@pytest.fixture
def worktree(tmp_path: Path) -> Iterator[Path]:
    """A real, throwaway --detach worktree of THIS repo, always removed via
    `worktree remove` + `prune` (never a bare `rm -rf` — the orphan-hygiene
    failure mode WORKTREE_MIGRATION.md documents)."""
    wt = tmp_path / "wt"
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "worktree", "add", "--detach", str(wt)],
        check=True, capture_output=True, text=True,
    )
    try:
        yield wt
    finally:
        subprocess.run(
            ["git", "-C", str(REPO_ROOT), "worktree", "remove", "--force", str(wt)],
            capture_output=True, text=True,
        )
        subprocess.run(["git", "-C", str(REPO_ROOT), "worktree", "prune"],
                        capture_output=True, text=True)


@pytest.fixture
def disconnected_repo(tmp_path: Path) -> Path:
    """A repo with ZERO git relationship to epyc-root — its own `git init`,
    standing in for the sibling repos' actual situation (no worktree/common-
    dir link to epyc-root, no local copy of the shared hook scripts)."""
    repo = tmp_path / "disconnected"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    return repo


# --------------------------------------------------------------- tier 1: override


def test_env_override_wins_over_everything(tmp_path: Path) -> None:
    """positive: pointing EPYC_HOOK_SRC_DIR at always-allow stubs proves the
    override is consulted before any git-plumbing resolution runs at all,
    even from a repo with no other relationship to epyc-root."""
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    for name in ("pii_precommit.sh", "hermes_drift_precommit.sh"):
        script = stub_dir / name
        script.write_text("#!/bin/bash\nexit 0\n")
        script.chmod(0o755)

    repo = tmp_path / "unrelated"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)

    rc = _stage_and_run(repo, BAD_BLOB, env={"EPYC_HOOK_SRC_DIR": str(stub_dir)})
    assert rc == 0, "override should have redirected scanning to the always-allow stubs"


# ------------------------------------------------------- tier 2: worktree-local


def test_worktree_with_its_own_checkout_uses_its_own_copy(worktree: Path) -> None:
    """positive, the core fix: patch the WORKTREE's own pii_precommit.sh to
    always allow, leaving canonical /workspace's real copy untouched. If
    tier 2 (worktree-local) really wins, the secret-shaped blob is ALLOWED
    here -- proof this worktree's own on-disk copy answered, since
    canonical's real copy would still block it."""
    local_pii = worktree / "scripts" / "hooks" / "pii_precommit.sh"
    assert local_pii.exists(), "worktree checkout is missing its own pii_precommit.sh"
    local_pii.write_text("#!/bin/bash\nexit 0\n")
    local_pii.chmod(0o755)

    rc = _stage_and_run(worktree, BAD_BLOB)
    assert rc == 0, (
        "worktree did not use its OWN patched pii_precommit.sh -- "
        "tier 2 (worktree-local resolution) is not winning"
    )


def test_canonical_is_unaffected_by_the_worktree_local_patch(worktree: Path) -> None:
    """negative / isolation check: patching the worktree's own copy must
    not somehow also affect canonical /workspace's real pii_precommit.sh --
    exercise canonical's real scanning immediately after the patch."""
    local_pii = worktree / "scripts" / "hooks" / "pii_precommit.sh"
    local_pii.write_text("#!/bin/bash\nexit 0\n")
    local_pii.chmod(0o755)

    rc = _stage_and_run(REPO_ROOT, BAD_BLOB)
    assert rc != 0, "canonical /workspace's real secret scan should still fire, unaffected"


# ------------------------------------------------ tier 3: common-dir primary tree


def test_sparse_worktree_falls_back_to_the_common_dir_primary_tree(worktree: Path) -> None:
    """A worktree missing its own scripts/hooks entirely (sparse checkout)
    must still correctly scan -- via the git-common-dir fallback to
    canonical -- not silently no-op because a script path was missing."""
    shutil.rmtree(worktree / "scripts" / "hooks")
    rc = _stage_and_run(worktree, BAD_BLOB)
    assert rc != 0, "sparse worktree should have fallen back to canonical and blocked"


def test_sparse_worktree_fallback_allows_a_clean_commit_too(worktree: Path) -> None:
    shutil.rmtree(worktree / "scripts" / "hooks")
    rc = _stage_and_run(worktree, "ordinary content")
    assert rc == 0


# --------------------------------------------------- tier 4: disconnected literal


def test_disconnected_repo_falls_back_to_the_canonical_literal(disconnected_repo: Path) -> None:
    """A repo with no git relationship to epyc-root (standing in for the
    real sibling repos, which have never carried their own copy of these
    two scripts -- verified empirically, see install_git_hooks.sh's header)
    must still reach real scanning via the tier-4 literal fallback."""
    rc = _stage_and_run(disconnected_repo, BAD_BLOB)
    assert rc != 0, "disconnected repo should have fallen back to canonical literal and blocked"


def test_disconnected_repo_allows_a_clean_commit_too(disconnected_repo: Path) -> None:
    """both directions: the fallback must distinguish clean from bad, not
    just fail-closed on everything."""
    rc = _stage_and_run(disconnected_repo, "ordinary content")
    assert rc == 0


# ------------------------------------------------------------ no baked literal


def test_resolution_is_conditional_not_an_unconditional_top_level_assignment() -> None:
    """Regression pin for the exact shape of the original bug: the first
    executable line of the emitted hook must be the override check, not a
    bare `HOOK_SRC_DIR="/workspace/scripts/hooks"` assignment reached
    unconditionally regardless of who is committing."""
    body = INSTALLED_HOOK.read_text()
    exec_lines = [ln for ln in body.splitlines()[1:]  # [0] is the shebang
                   if ln.strip() and not ln.strip().startswith("#")]
    assert exec_lines, "emitted hook has no executable content"
    assert "EPYC_HOOK_SRC_DIR" in exec_lines[0], (
        f"first executable line was {exec_lines[0]!r}, expected the override check first"
    )
    assert "git rev-parse --show-toplevel" in body
    # Tier 4's literal is allowed to exist -- exactly once, as a documented
    # last resort -- but never as the ONLY resolution strategy.
    literal_assignments = re.findall(r'HOOK_SRC_DIR="/workspace/scripts/hooks"', body)
    assert len(literal_assignments) == 1, (
        f"expected exactly one literal fallback assignment, found {len(literal_assignments)}"
    )
