#!/usr/bin/env python3
"""Regression pin for check_commit_hygiene.fetch_head_path() under LINKED WORKTREES.

WHAT BROKE (2026-08-16, commit 5235e335). The stale-fetch guard (rule B) asked
"when did this repo last fetch" by reading FETCH_HEAD out of the git COMMON dir
only, on the docstring's claim that FETCH_HEAD "lives once, in the common dir,
shared by every worktree". That claim is FALSE on this git: a `git fetch` run
from inside a linked worktree writes FETCH_HEAD into THAT WORKTREE's own
metadata dir (`<common>/worktrees/<name>/FETCH_HEAD`), leaving the common copy
untouched. So the guard read a file the worktree had never written, and
reported a stale fetch to precisely the trees that had just fetched — the first
pool worker was blocked twice with "stale fetch (50748s old)" seconds after a
successful fetch. The fix consults BOTH locations and takes the NEWEST.

WHY THIS TEST IS SHAPED THE WAY IT IS. The pre-existing coverage in
scripts/hooks/tests/test_commit_hygiene_worktree.py adds a throwaway worktree
of THIS repo and never fetches inside it, so the per-worktree FETCH_HEAD never
exists there and the two resolutions are indistinguishable — that suite passes
against the broken code. Catching this defect requires the two files to exist
SIMULTANEOUSLY with DIFFERENT mtimes, which is why everything here is built in
a disposable `git init` repo whose FETCH_HEAD mtimes we own outright.

MUTATION-CHECKED 2026-08-16: with fetch_head_path()'s body reverted to the
pre-fix `return Path(common) / "FETCH_HEAD"`, this file goes 3 failed / 5
passed — test_worktree_fetch_head_wins_when_fresher,
test_stale_fetch_symptom_does_not_recur and test_only_the_worktree_copy_exists
all FAIL. The other five pin behaviour the fix must NOT change and pass either
way, which is the point of having them.

BOTH DIRECTIONS:
  - positive: a fresh per-worktree FETCH_HEAD beside an old common one resolves
    to the per-worktree file, and the age the guard would compute is fresh.
  - negative: the rule is "newest wins", not "always prefer the worktree" — a
    fresh COMMON copy beside an old per-worktree one resolves back to the
    common file; the main checkout is unaffected; and a repo that has never
    fetched at all still yields the common path (so the guard's existing
    "no FETCH_HEAD" branch is untouched).

Usage: pytest scripts/coordination/tests/test_fetch_head_worktree_resolution.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterator, NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "hooks"))
import check_commit_hygiene as hygiene  # noqa: E402

# The guard's own default threshold. "Old" must be unambiguously past it and
# "fresh" unambiguously inside it, so a slow test host can never flip a verdict.
MAX_AGE_S = 600
OLD_AGE_S = 50_748          # the age the blocked pool worker was actually shown
FRESH_AGE_S = 5


class Fixture(NamedTuple):
    main: Path              # the original checkout
    worktree: Path          # a linked worktree of it
    common_fetch_head: Path # <main>/.git/FETCH_HEAD
    wt_fetch_head: Path     # <main>/.git/worktrees/<name>/FETCH_HEAD


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd) if cwd else None,
        check=True, capture_output=True, text=True,
    )


def _age(path: Path) -> float:
    return time.time() - path.stat().st_mtime


def _write_fetch_head(path: Path, age_s: float) -> None:
    """Create a FETCH_HEAD-shaped file whose mtime is `age_s` seconds old."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "0000000000000000000000000000000000000000\t\tbranch 'main' of origin\n"
    )
    when = time.time() - age_s
    os.utime(path, (when, when))


@pytest.fixture
def repo_with_worktree(tmp_path: Path) -> Iterator[Fixture]:
    """A disposable repo + one linked worktree, torn down with `worktree
    remove` + `prune` rather than a bare rmtree (orphaned worktree metadata is
    the hygiene failure WORKTREE_MIGRATION.md documents). Fully disconnected
    from the five shared seeds on purpose: fetch_head_path() answers "where
    does THIS tree keep FETCH_HEAD" and must not depend on sharedness.
    """
    main = tmp_path / "origin-checkout"
    main.mkdir()
    _git("init", "-q", "-b", "main", str(main))
    (main / "seed.txt").write_text("seed\n")
    _git("add", "seed.txt", cwd=main)
    _git("-c", "user.name=test", "-c", "user.email=test@example.invalid",
         "-c", "commit.gpgsign=false",
         "commit", "-q", "--no-verify", "-m", "seed", cwd=main)

    worktree = tmp_path / "linked-worktree"
    _git("worktree", "add", "-q", "--detach", str(worktree), cwd=main)

    # Resolve the per-worktree metadata dir from git itself rather than
    # hand-spelling `<common>/worktrees/<name>` — the point of the test is
    # where GIT puts the file, so git must be the one to say.
    gitdir = Path(_git("rev-parse", "--absolute-git-dir", cwd=worktree).stdout.strip())
    common = Path(_git("rev-parse", "--path-format=absolute", "--git-common-dir",
                       cwd=worktree).stdout.strip())
    assert gitdir != common, (
        "fixture is not exercising a linked worktree — its git-dir and "
        "git-common-dir are the same path"
    )

    try:
        yield Fixture(main=main, worktree=worktree,
                      common_fetch_head=common / "FETCH_HEAD",
                      wt_fetch_head=gitdir / "FETCH_HEAD")
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(worktree)],
                       cwd=str(main), capture_output=True, text=True)
        subprocess.run(["git", "worktree", "prune"],
                       cwd=str(main), capture_output=True, text=True)


# ------------------------------------------------------------------ the defect


def test_git_writes_fetch_head_into_the_worktree_metadata_dir(
        repo_with_worktree: Fixture) -> None:
    """Premise check before the behavioural ones: if THIS git ever starts
    keeping FETCH_HEAD only in the common dir, the tests below stop meaning
    what their names say, and this one says so first."""
    resolved = _git("rev-parse", "--path-format=absolute", "--git-path",
                    "FETCH_HEAD", cwd=repo_with_worktree.worktree).stdout.strip()
    assert Path(resolved) == repo_with_worktree.wt_fetch_head, (
        "git no longer resolves FETCH_HEAD to the per-worktree metadata dir; "
        "the premise of the 5235e335 fix has changed"
    )


def test_worktree_fetch_head_wins_when_fresher(repo_with_worktree: Fixture) -> None:
    """THE regression. Both files exist; the worktree just fetched, the common
    dir did not. Reading only the common dir picks the 50748s-old file and the
    guard blocks a tree that is in fact up to date."""
    _write_fetch_head(repo_with_worktree.common_fetch_head, OLD_AGE_S)
    _write_fetch_head(repo_with_worktree.wt_fetch_head, FRESH_AGE_S)

    resolved = hygiene.fetch_head_path(str(repo_with_worktree.worktree))

    assert resolved is not None
    assert resolved.exists()
    assert os.path.samefile(resolved, repo_with_worktree.wt_fetch_head), (
        f"fetch_head_path() returned {resolved}, expected the per-worktree "
        f"FETCH_HEAD at {repo_with_worktree.wt_fetch_head}"
    )
    assert not os.path.samefile(resolved, repo_with_worktree.common_fetch_head)


def test_stale_fetch_symptom_does_not_recur(repo_with_worktree: Fixture) -> None:
    """The symptom, in the guard's own terms: main() blocks when
    `time.time() - fetch_head.stat().st_mtime > EPYC_FETCH_MAX_AGE_S`. Pin the
    verdict, not just the path — a future resolver that returns some third
    fresh-looking path would satisfy the identity assertion above and still be
    wrong here."""
    _write_fetch_head(repo_with_worktree.common_fetch_head, OLD_AGE_S)
    _write_fetch_head(repo_with_worktree.wt_fetch_head, FRESH_AGE_S)

    resolved = hygiene.fetch_head_path(str(repo_with_worktree.worktree))

    assert resolved is not None
    age = _age(resolved)
    assert age <= MAX_AGE_S, (
        f"the guard would still block this worktree: computed age {int(age)}s "
        f"exceeds the {MAX_AGE_S}s threshold despite a {FRESH_AGE_S}s-old fetch"
    )


# ------------------------------------------------- negative: NEWEST, not WORKTREE


def test_newest_wins_in_both_directions(repo_with_worktree: Fixture) -> None:
    """The fix is "take the newest", not "always prefer the worktree". With the
    freshness reversed the common copy must win — otherwise a worktree that
    fetched last week would mask a common-dir fetch from a minute ago."""
    _write_fetch_head(repo_with_worktree.wt_fetch_head, OLD_AGE_S)
    _write_fetch_head(repo_with_worktree.common_fetch_head, FRESH_AGE_S)

    resolved = hygiene.fetch_head_path(str(repo_with_worktree.worktree))

    assert resolved is not None
    assert os.path.samefile(resolved, repo_with_worktree.common_fetch_head), (
        f"fetch_head_path() returned {resolved}, expected the common-dir "
        f"FETCH_HEAD at {repo_with_worktree.common_fetch_head}"
    )


def test_main_checkout_still_resolves_to_the_common_dir(
        repo_with_worktree: Fixture) -> None:
    """Unchanged behaviour for the original checkout, whose git-dir IS the
    common dir — the case that worked before the fix must keep working."""
    _write_fetch_head(repo_with_worktree.common_fetch_head, FRESH_AGE_S)
    _write_fetch_head(repo_with_worktree.wt_fetch_head, OLD_AGE_S)

    resolved = hygiene.fetch_head_path(str(repo_with_worktree.main))

    assert resolved is not None
    assert os.path.samefile(resolved, repo_with_worktree.common_fetch_head)


def test_only_the_worktree_copy_exists(repo_with_worktree: Fixture) -> None:
    """The real pool-worker shape: the common dir has NEVER been fetched into,
    so the old code found no file at all and fell through to the guard's
    `age = 10**9` "no FETCH_HEAD" branch — a hard block."""
    _write_fetch_head(repo_with_worktree.wt_fetch_head, FRESH_AGE_S)
    assert not repo_with_worktree.common_fetch_head.exists()

    resolved = hygiene.fetch_head_path(str(repo_with_worktree.worktree))

    assert resolved is not None
    assert resolved.exists()
    assert os.path.samefile(resolved, repo_with_worktree.wt_fetch_head)


def test_no_fetch_head_anywhere_still_returns_the_common_path(
        repo_with_worktree: Fixture) -> None:
    """Untouched fallback: with neither file present the resolver must still
    hand back a (nonexistent) path so main() takes its OSError branch and
    reports "no FETCH_HEAD" — returning None here would be read as
    "git-common-dir unresolvable", the same verdict by a different route, but
    a caller that ever distinguishes them would see the wrong reason."""
    assert not repo_with_worktree.common_fetch_head.exists()
    assert not repo_with_worktree.wt_fetch_head.exists()

    resolved = hygiene.fetch_head_path(str(repo_with_worktree.worktree))

    assert resolved is not None
    assert not resolved.exists()
    assert resolved.name == "FETCH_HEAD"


def test_non_repo_path_still_returns_none(tmp_path: Path) -> None:
    """A path that is not a git working tree at all has no answer, and the
    guard's fail-permissive posture depends on getting None rather than a
    fabricated path."""
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    assert hygiene.fetch_head_path(str(plain)) is None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
