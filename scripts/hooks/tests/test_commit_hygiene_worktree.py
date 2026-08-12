#!/usr/bin/env python3
"""Tests for check_commit_hygiene.py's worktree-aware is_shared() (P1/3b) and
the FETCH_HEAD resolution fix that followed it (P1/3 follow-up).

SHARED_REPOS used to be literal-path equality only, so its protections
silently lapsed for any worktree (a worktree's path is never literally one
of the five seed roots). is_shared() now ALSO qualifies a path via
`git -C <path> rev-parse --git-common-dir`: every worktree of a repo shares
ONE common-dir with it. Fixing that then exposed a second, latent bug: the
stale-fetch check's `Path(repo) / ".git" / "FETCH_HEAD"` is unresolvable for
a worktree (its `.git` is a FILE, not a directory) -- covered here too.

BOTH DIRECTIONS:
  - positive: a real worktree of THIS repo qualifies as shared, its
    common-dir matches its seed's, its FETCH_HEAD resolves to the one real
    shared file, and end-to-end hook behaviour (block wholesale add, allow
    explicit paths, gate on fetch freshness) applies inside it exactly as
    it already does for /workspace.
  - negative: a genuinely disconnected repo (its own `git init`, zero
    relationship to any seed) does NOT qualify, proving this is
    common-dir membership rather than "is this any git repo at all";
    nonexistent paths do not crash or false-positive either.

Usage: pytest scripts/hooks/tests/test_commit_hygiene_worktree.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "scripts" / "hooks" / "check_commit_hygiene.py"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "hooks"))
import check_commit_hygiene as hygiene  # noqa: E402

FRESH = {"EPYC_FETCH_MAX_AGE_S": "999999999"}  # any REAL mtime counts as fresh
STALE = {"EPYC_FETCH_MAX_AGE_S": "0"}


@pytest.fixture
def epyc_root_worktree(tmp_path: Path) -> Iterator[Path]:
    """A real, throwaway --detach worktree of THIS repo -- the same shape
    setup_main_worktrees.sh creates (minus the branch, irrelevant here),
    always removed after the test via `worktree remove` + `prune` (never a
    bare `rm -rf`, which is exactly the orphan-hygiene failure mode
    WORKTREE_MIGRATION.md documents)."""
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
    repo = tmp_path / "disconnected"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    return repo


def run_hook(cmd: str, env: dict | None = None) -> int:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
        capture_output=True, text=True,
        env={**os.environ, **(env or {})},
    ).returncode


# ------------------------------------------------------- in-process, both directions


def test_worktree_of_a_shared_repo_is_recognized_as_shared(epyc_root_worktree: Path) -> None:
    assert hygiene.is_shared(str(epyc_root_worktree)) is True


def test_worktree_common_dir_matches_its_seeds(epyc_root_worktree: Path) -> None:
    wt_common = hygiene._git_common_dir(str(epyc_root_worktree))
    seed_common = hygiene._git_common_dir(str(REPO_ROOT))
    assert wt_common is not None
    assert wt_common == seed_common


def test_disconnected_repo_is_not_shared(disconnected_repo: Path) -> None:
    """Negative direction: a real git repo with NO relationship to any of
    the five seeds must not qualify just because git-plumbing can answer a
    question about it -- proves this is common-dir MEMBERSHIP, not "is this
    any repo at all"."""
    assert hygiene.is_shared(str(disconnected_repo)) is False


def test_nonexistent_path_is_not_shared() -> None:
    assert hygiene.is_shared("/does/not/exist/at/all") is False


def test_seed_common_dirs_are_cached_across_calls(
        epyc_root_worktree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Performance guard: this hook fires on every Bash tool call, so the
    five-seed lookup must be computed once per process, not once per
    is_shared() call."""
    hygiene._seed_common_dirs_cache = None
    calls = {"n": 0}
    real = hygiene._git_common_dir

    def counting(path: str) -> str | None:
        calls["n"] += 1
        return real(path)

    monkeypatch.setattr(hygiene, "_git_common_dir", counting)
    hygiene.is_shared(str(epyc_root_worktree))
    first = calls["n"]
    hygiene.is_shared(str(epyc_root_worktree))
    second = calls["n"]
    assert second - first == 1, (
        "second is_shared() call re-derived more than just its own path's "
        "common-dir -- the seed set is not being cached"
    )
    hygiene._seed_common_dirs_cache = None


# ------------------------------------------------------------ FETCH_HEAD fix


def test_fetch_head_path_resolves_to_the_one_shared_file(epyc_root_worktree: Path) -> None:
    wt_fetch_head = hygiene.fetch_head_path(str(epyc_root_worktree))
    canon_fetch_head = hygiene.fetch_head_path(str(REPO_ROOT))
    assert wt_fetch_head is not None and canon_fetch_head is not None
    assert wt_fetch_head.resolve() == canon_fetch_head.resolve()


def test_fetch_head_path_is_not_the_broken_naive_join(epyc_root_worktree: Path) -> None:
    """Regression pin for the exact defect: `<worktree>/.git` is a FILE, so
    the naive Path(repo) / ".git" / "FETCH_HEAD" is unresolvable there --
    yet the real resolver must still produce a valid, EXISTING path."""
    naive = epyc_root_worktree / ".git" / "FETCH_HEAD"
    with pytest.raises(NotADirectoryError):
        naive.stat()

    real = hygiene.fetch_head_path(str(epyc_root_worktree))
    assert real is not None
    assert real.exists(), (
        "fetch_head_path() resolved to a path that doesn't exist -- if this "
        "repo has genuinely never been fetched, run `git fetch` once and "
        "re-run this test"
    )


# --------------------------------------------------------- end-to-end, subprocess


def test_wholesale_add_is_blocked_inside_a_worktree(epyc_root_worktree: Path) -> None:
    """Before item 3b, a worktree path never matched literal SHARED_REPOS,
    so this exact command was invisible to the guard -- silently allowed."""
    assert run_hook(f"git -C {epyc_root_worktree} add -A") == 2


def test_explicit_path_add_is_allowed_inside_a_worktree(epyc_root_worktree: Path) -> None:
    assert run_hook(f"git -C {epyc_root_worktree} add some/explicit/path.md") == 0


def test_commit_with_a_fresh_fetch_is_allowed_inside_a_worktree(epyc_root_worktree: Path) -> None:
    """End-to-end pin for the FETCH_HEAD fix: a commit inside the worktree
    must NOT be blocked as stale when the shared FETCH_HEAD is fresh."""
    assert hygiene.fetch_head_path(str(REPO_ROOT)).exists(), (
        "this repo has never been fetched in this environment -- run "
        "`git fetch` once, this test relies on FETCH_HEAD already existing"
    )
    assert run_hook(f'git -C {epyc_root_worktree} commit -m "x"', FRESH) == 0


def test_commit_with_a_stale_fetch_is_blocked_inside_a_worktree(epyc_root_worktree: Path) -> None:
    assert run_hook(f'git -C {epyc_root_worktree} commit -m "x"', STALE) == 2


def test_disconnected_repo_is_unaffected_by_the_shared_rules(disconnected_repo: Path) -> None:
    assert run_hook(f"git -C {disconnected_repo} add -A") == 0
