"""Phase-2 verification: per-main git worktree isolation is STRUCTURAL.

Companion to `scripts/coordination/WORKTREE_MIGRATION.md` and
`scripts/coordination/setup_main_worktrees.sh`. Phase 1 built the machinery
against a single throwaway lane; phase 2 is the five real lanes
(`mainA mainB mainC mainD auditor`) being live. This file is the evidence
that the isolation claim is a property of git's data model, not a habit
agents are asked to keep.

WHAT IS BEING CLAIMED, AND WHY IT NEEDS A TEST
----------------------------------------------
Three failures cost real work in a single shared `/workspace` clone:

  (a) a pathspec-limited commit swept ANOTHER session's uncommitted hunks
      out of the same file, because both sessions were editing one file in
      one working tree;
  (b) one agent's staged files rode into a different agent's commit,
      because five agents shared one index;
  (c) `git clean -ffdx` in the shared clone removed nested worktrees and
      untracked files belonging to other sessions.

Under the two-plane model each main works in its own worktree at
`/mnt/raid0/llm/worktrees/mains/<agent>` on `lane/<agent>`, while the
coordination RUNTIME plane (`/workspace/coordination/session-bus`) stays
single and unforked. (a) and (b) then stop being "please be careful": a
worktree has its own index and its own untracked-file plane, so there is no
mechanism by which a commit in one can reach into another.

(c) is only PARTLY closed, and this file says so out loud. The lane working
trees are not inside the shared clone, so a recursive delete there cannot
reach the work. But each lane's `.git` is a pointer file into
`<shared clone>/.git/worktrees/<agent>` -- which IS inside the shared clone.
Destroying that directory leaves every lane's files perfectly intact and
every lane's git completely dead. That is not hypothetical: it happened to
all five lanes at once on 2026-08-12 while this harness was being written,
which is why `test_each_lane_worktree_is_a_functioning_git_checkout` exists
and why the coupling is pinned by
`test_lane_git_metadata_still_lives_inside_the_shared_clone_residual_coupling`
rather than papered over.

The mechanism behind that event has its own test,
`test_worktree_registrations_are_identical_from_every_path_to_the_repo`: this
repo is reachable as `/workspace` (depth 1) AND `/mnt/raid0/llm/epyc-root`
(depth 4) -- one directory, shared inode -- while git registers worktrees
with RELATIVE gitdir pointers that only resolve at the depth they were
written for. From the deeper path every worktree looks `prunable`, so a
`git worktree prune` or `git gc` there deletes live worktrees' admin data.
pytest.ini instructs agents to use the deeper path, so this recurs.

EVERY TEST HERE RUNS IN BOTH DIRECTIONS
---------------------------------------
A guard that also blocks the correct usage is a defect, not a stricter
guard. So for each hazard this file asserts the hazard is impossible AND
that the ordinary compliant operation still works:

  * isolation holds   AND  a normal pathspec commit inside one worktree
                           still succeeds and still captures that
                           worktree's own change;
  * the bus root is canonical  AND  the `EPYC_BUS_ROOT` override is still
                           honoured -- without that negative control the
                           test cannot tell "canonical" from "hardcoded and
                           ignoring its inputs".

There is also a HAZARD CONTROL (`test_shared_tree_pathspec_commit_*`) which
reproduces failure (a) inside a single working tree and asserts the sweep
DOES happen there. Its job is anti-vacuity: it proves this file's assertion
machinery is capable of SEEING a sweep, so the isolation tests passing means
"no sweep occurred", not "the check cannot detect one".

SAFETY
------
Every git write in this file happens inside a throwaway repository created
under pytest's `tmp_path`, checked by `_assert_sandboxed()` before the
command runs. The real repositories are only ever read (`git worktree
list`, `git rev-parse`). Nothing here creates, deletes or prunes a worktree
outside `tmp_path`, and nothing here runs `git clean` anywhere -- hazard (c)
is asserted by path containment instead, which is the actual property
(a clean in the shared clone cannot reach a path outside the shared clone).

Usage: pytest tests/coordination/test_worktree_isolation_phase2.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pytest

# --------------------------------------------------------------------------
# Constants describing the deployed two-plane layout.
# --------------------------------------------------------------------------

#: The one canonical runtime plane. Literal on purpose: the whole point of
#: get_bus_root() is that this string does NOT vary with the caller's checkout.
CANONICAL_BUS_ROOT = "/workspace/coordination/session-bus"

#: The shared clone that hosts the canonical runtime plane.
CANONICAL_CLONE = Path("/workspace")

#: The SAME repository, reached by its other name. `/workspace/.git` and
#: `/mnt/raid0/llm/epyc-root/.git` are one directory (pytest.ini documents the
#: shared inode, and pytest.ini tells agents to work from the second one).
#: The two paths are at different depths, which is why
#: test_worktree_registrations_are_identical_from_every_path_to_the_repo
#: exists.
ALT_CLONE = Path("/mnt/raid0/llm/epyc-root")

#: Where the versioned work plane lives -- deliberately NOT under the shared
#: clone, which is what puts it out of reach of hazard (c).
LANE_WORKTREE_ROOT = Path("/mnt/raid0/llm/worktrees/mains")

LANE_AGENTS = ("mainA", "mainB", "mainC", "mainD", "auditor")

REPO_ROOT = Path(__file__).resolve().parents[2]
SESSION_BUS_PY = REPO_ROOT / "scripts" / "coordination" / "session_bus.py"

#: A session_bus.py smaller than this is not the real module (truncated
#: checkout, LFS pointer, empty file). Comparing against a stub would pass
#: for the wrong reason, so size is asserted before the module is used.
MIN_SESSION_BUS_BYTES = 5_000


# --------------------------------------------------------------------------
# Subprocess plumbing. No output is ever discarded: a swallowed stderr turns
# "the command failed" into "the property held", which is the failure mode
# this file exists to avoid.
# --------------------------------------------------------------------------


def _hermetic_git_env() -> Dict[str, str]:
    """Environment for git calls against the throwaway repo.

    The shared clone sets `core.hooksPath=/workspace/.git/hooks` and this
    host has no global `user.email`, so an inherited environment would make
    throwaway commits either run foreign hooks or fail outright. Both would
    be a test failure with nothing to do with isolation. Inherited
    GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE are dropped for the same reason --
    they would silently retarget a `-C`-scoped command.
    """
    env = dict(os.environ)
    for leaked in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
                   "GIT_OBJECT_DIRECTORY", "GIT_COMMON_DIR"):
        env.pop(leaked, None)
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_AUTHOR_NAME="wtiso",
        GIT_AUTHOR_EMAIL="wtiso@invalid",
        GIT_COMMITTER_NAME="wtiso",
        GIT_COMMITTER_EMAIL="wtiso@invalid",
        GIT_TERMINAL_PROMPT="0",
    )
    return env


#: Real trees that a git WRITE from this file must never be able to reach.
PROTECTED_TREES = (CANONICAL_CLONE, LANE_WORKTREE_ROOT, REPO_ROOT)


def _assert_sandboxed(path: Path, sandbox_root: Path) -> Path:
    """Refuse to issue a git WRITE outside the throwaway tree.

    `sandbox_root` is pytest's `tmp_path` (normally under /tmp), which pytest
    owns and reaps. The check is on containment rather than on a hardcoded
    /tmp prefix so that a runner with a relocated TMPDIR is still protected
    rather than merely rejected -- and it additionally refuses outright if the
    temp dir somehow lands inside a real tree.
    """
    resolved = Path(path).resolve()
    root = Path(sandbox_root).resolve()
    assert root.is_absolute() and root.is_dir(), f"bad sandbox root {root}"
    for protected in PROTECTED_TREES:
        p = protected.resolve()
        assert p != root and p not in root.parents and root not in p.parents, (
            f"sandbox root {root} overlaps the real tree {p}; refusing to run git writes"
        )
    assert resolved == root or root in resolved.parents, (
        f"refusing to run a git write against {resolved}: outside sandbox {root}"
    )
    return resolved


def _git(args: List[str], cwd: Path, *, expect_ok: bool = True,
         env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True, text=True, env=env if env is not None else _hermetic_git_env(),
    )
    if expect_ok:
        assert proc.returncode == 0, (
            f"git {' '.join(args)} (in {cwd}) exited {proc.returncode}\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    return proc


def _lines(text: str) -> List[str]:
    return [ln for ln in text.splitlines() if ln.strip()]


# --------------------------------------------------------------------------
# Throwaway multi-worktree repository.
# --------------------------------------------------------------------------

SHARED_FILE = "shared.txt"
SIDE_FILE = "side.txt"
BASE_CONTENT = "line-one\nline-two\nline-three\n"
A_EDIT = "EDIT-FROM-WORKTREE-A"
B_EDIT = "EDIT-FROM-WORKTREE-B"


@dataclass(frozen=True)
class Sandbox:
    root: Path
    base: Path      # the "shared clone" analogue: repo with a working tree
    wt_a: Path      # lane worktree A
    wt_b: Path      # lane worktree B


@pytest.fixture()
def sandbox(tmp_path: Path) -> Sandbox:
    """A repo with a base working tree plus two sibling worktrees.

    This is a faithful miniature of the deployed layout: one object store,
    three working trees, three indexes, three branches.
    """
    root = _assert_sandboxed(tmp_path, tmp_path)
    base = root / "base"
    base.mkdir()

    env = _hermetic_git_env()
    proc = subprocess.run(
        ["git", "-c", "init.defaultBranch=main", "init", "--quiet", str(base)],
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 0, f"git init failed: {proc.stderr}"

    (base / SHARED_FILE).write_text(BASE_CONTENT)
    (base / SIDE_FILE).write_text("side-original\n")
    _git(["add", SHARED_FILE, SIDE_FILE], base)
    _git(["commit", "--quiet", "-m", "seed"], base)

    wt_a = _assert_sandboxed(root / "wtA", root)
    wt_b = _assert_sandboxed(root / "wtB", root)
    _git(["worktree", "add", "--quiet", "-b", "lane/a", str(wt_a)], base)
    _git(["worktree", "add", "--quiet", "-b", "lane/b", str(wt_b)], base)

    # Anti-vacuity: the fixture must actually have produced three populated,
    # distinct working trees before any test compares them.
    for wt in (base, wt_a, wt_b):
        assert (wt / SHARED_FILE).read_text() == BASE_CONTENT, f"{wt} not seeded"
    assert len({base.resolve(), wt_a.resolve(), wt_b.resolve()}) == 3

    return Sandbox(root=root, base=base, wt_a=wt_a, wt_b=wt_b)


def _staged(worktree: Path) -> set:
    return set(_lines(_git(["diff", "--cached", "--name-only"], worktree).stdout))


def _untracked(worktree: Path) -> set:
    return set(_lines(
        _git(["ls-files", "--others", "--exclude-standard"], worktree).stdout))


def _porcelain_status(worktree: Path) -> set:
    return set(_lines(
        _git(["status", "--porcelain", "--untracked-files=all"], worktree).stdout))


# ==========================================================================
# 1. INDEX ISOLATION
# ==========================================================================


def test_worktrees_have_distinct_indexes_but_share_one_object_store(sandbox: Sandbox):
    """The structural fact everything else rests on.

    Distinct `--git-dir` (hence distinct `index` files) is what makes a
    cross-worktree sweep impossible; identical `--git-common-dir` is what
    keeps them one repository rather than three unrelated clones. Assert
    both, or "isolated" could be satisfied by an unrelated copy.
    """
    dirs = {}
    for name, wt in (("base", sandbox.base), ("A", sandbox.wt_a), ("B", sandbox.wt_b)):
        git_dir = Path(_git(["rev-parse", "--absolute-git-dir"], wt).stdout.strip())
        common = Path(_git(["rev-parse", "--path-format=absolute",
                            "--git-common-dir"], wt).stdout.strip())
        assert git_dir.is_dir(), f"{name}: {git_dir} is not a directory"
        dirs[name] = (git_dir.resolve(), common.resolve())

    git_dirs = [g for g, _ in dirs.values()]
    assert len(set(git_dirs)) == 3, f"worktrees share a git dir: {dirs}"

    index_files = [g / "index" for g in git_dirs]
    assert len(set(index_files)) == 3
    for idx in index_files:
        assert idx.exists(), f"expected a per-worktree index at {idx}"

    commons = {c for _, c in dirs.values()}
    assert len(commons) == 1, f"worktrees do not share one object store: {dirs}"


def test_staging_in_one_worktree_leaves_the_other_worktrees_index_empty(sandbox: Sandbox):
    """Hazard (b): staged files riding into another agent's commit.

    Both directions -- A's staged set must be exactly what A staged
    (non-empty, so the comparison is not vacuous), and B's must be empty.
    """
    (sandbox.wt_a / SHARED_FILE).write_text(A_EDIT + "\n" + BASE_CONTENT)
    (sandbox.wt_a / "a-only.txt").write_text("only A staged this\n")
    _git(["add", SHARED_FILE, "a-only.txt"], sandbox.wt_a)

    staged_a = _staged(sandbox.wt_a)
    assert staged_a == {SHARED_FILE, "a-only.txt"}, staged_a  # non-empty by construction

    assert _staged(sandbox.wt_b) == set()
    assert _staged(sandbox.base) == set()

    # ...and A's staging did not even touch B's working tree.
    assert (sandbox.wt_b / SHARED_FILE).read_text() == BASE_CONTENT
    assert not (sandbox.wt_b / "a-only.txt").exists()


def test_pathspec_commit_cannot_capture_another_worktrees_hunks(sandbox: Sandbox):
    """Hazard (a): the sweep, in its exact original shape.

    A and B both have uncommitted edits to the SAME-NAMED file. A commits
    with a pathspec naming that file. In a shared tree this captures B's
    hunk too (see the hazard control below). Across worktrees it cannot.
    """
    (sandbox.wt_a / SHARED_FILE).write_text(f"{A_EDIT}\nline-two\nline-three\n")
    (sandbox.wt_b / SHARED_FILE).write_text(f"line-one\nline-two\n{B_EDIT}\n")

    # Precondition: both edits really are present and uncommitted.
    assert A_EDIT in (sandbox.wt_a / SHARED_FILE).read_text()
    assert B_EDIT in (sandbox.wt_b / SHARED_FILE).read_text()
    assert _porcelain_status(sandbox.wt_b), "B has no pending change; test would be vacuous"

    _git(["add", SHARED_FILE], sandbox.wt_a)
    _git(["commit", "--quiet", "-m", "A commits its own hunk", "--", SHARED_FILE],
         sandbox.wt_a)

    committed = _git(["show", f"HEAD:{SHARED_FILE}"], sandbox.wt_a).stdout
    assert A_EDIT in committed, "A's own change was not committed -- see the compliant test"
    assert B_EDIT not in committed, (
        "A's pathspec commit captured worktree B's uncommitted hunk -- "
        "the shared-clone sweep is reachable across worktrees"
    )

    # B's work is untouched and still B's: on disk, and still pending.
    assert B_EDIT in (sandbox.wt_b / SHARED_FILE).read_text()
    assert _porcelain_status(sandbox.wt_b) == {f" M {SHARED_FILE}"}

    # B's branch tip did not move either.
    tip_a = _git(["rev-parse", "HEAD"], sandbox.wt_a).stdout.strip()
    tip_b = _git(["rev-parse", "HEAD"], sandbox.wt_b).stdout.strip()
    assert tip_a != tip_b, "A's commit advanced B's branch as well"


def test_shared_tree_pathspec_commit_does_sweep_both_edits_hazard_control(sandbox: Sandbox):
    """ANTI-VACUITY CONTROL. Not a property we want -- a property we want the
    harness to be able to SEE.

    Two 'sessions' edit one file in ONE working tree; a pathspec commit takes
    both. If this test ever passes-by-not-detecting, the isolation test above
    is worthless. It also pins the compliant half of pathspec semantics: the
    unrelated file named by no pathspec stays out of the commit.
    """
    shared = sandbox.base / SHARED_FILE
    shared.write_text(f"SESSION1-EDIT\nline-two\nSESSION2-EDIT\n")
    (sandbox.base / SIDE_FILE).write_text("side-modified-by-session3\n")

    _git(["commit", "--quiet", "-m", "pathspec commit in a shared tree",
          "--", SHARED_FILE], sandbox.base)

    committed = _git(["show", f"HEAD:{SHARED_FILE}"], sandbox.base).stdout
    assert "SESSION1-EDIT" in committed
    assert "SESSION2-EDIT" in committed, (
        "the hazard control did not reproduce the sweep -- this file's "
        "sweep-detection is not proven to work, so the isolation results "
        "above cannot be trusted"
    )
    # Pathspec scoping itself is intact: the unnamed file was not swept.
    assert _git(["show", f"HEAD:{SIDE_FILE}"], sandbox.base).stdout == "side-original\n"
    assert f" M {SIDE_FILE}" in _porcelain_status(sandbox.base)


def test_ordinary_pathspec_commit_inside_one_worktree_still_works(sandbox: Sandbox):
    """THE COMPLIANT DIRECTION, and it matters equally.

    Isolation must not cost a main the normal workflow: inside its own
    worktree a pathspec-limited commit must succeed (exit 0), must capture
    that worktree's own change, and must leave the unnamed file pending.
    """
    (sandbox.wt_a / SHARED_FILE).write_text(f"{A_EDIT}\nline-two\nline-three\n")
    (sandbox.wt_a / SIDE_FILE).write_text("side-changed-by-A\n")

    before = _git(["rev-parse", "HEAD"], sandbox.wt_a).stdout.strip()
    _git(["add", SHARED_FILE, SIDE_FILE], sandbox.wt_a)
    proc = _git(["commit", "--quiet", "-m", "normal scoped commit", "--", SHARED_FILE],
                sandbox.wt_a)
    assert proc.returncode == 0

    after = _git(["rev-parse", "HEAD"], sandbox.wt_a).stdout.strip()
    assert after != before, "the compliant pathspec commit produced no commit"
    assert A_EDIT in _git(["show", f"HEAD:{SHARED_FILE}"], sandbox.wt_a).stdout
    assert _git(["show", f"HEAD:{SIDE_FILE}"], sandbox.wt_a).stdout == "side-original\n"
    # The unnamed file is still staged and pending -- scoped, not lost.
    assert SIDE_FILE in _staged(sandbox.wt_a)


def test_one_branch_cannot_be_checked_out_in_two_worktrees(sandbox: Sandbox):
    """Lane exclusivity is enforced by git, not by convention.

    Negative: a second worktree on an already-checked-out branch is refused
    (non-zero exit, no directory created). Positive: the same command on a
    fresh branch succeeds -- the refusal is about sharing, not about adding.
    """
    dup = sandbox.root / "wtDup"
    proc = _git(["worktree", "add", str(dup), "lane/a"], sandbox.base, expect_ok=False)
    assert proc.returncode != 0, (
        "git allowed lane/a to be checked out in two worktrees at once"
    )
    assert not (dup / ".git").exists(), "a refused worktree left a checkout behind"

    fresh = _assert_sandboxed(sandbox.root / "wtFresh", sandbox.root)
    ok = _git(["worktree", "add", "--quiet", "-b", "lane/c", str(fresh)], sandbox.base)
    assert ok.returncode == 0
    assert (fresh / SHARED_FILE).read_text() == BASE_CONTENT


# ==========================================================================
# 2. UNTRACKED-PLANE ISOLATION
# ==========================================================================


def test_untracked_files_are_invisible_across_worktrees(sandbox: Sandbox):
    """Hazard (c)'s other half: untracked state does not leak between lanes.

    Symmetric, so a bug that merely mirrors one direction cannot pass:
    A's scratch file is visible in A and absent in B, and B's is visible in
    B and absent in A. Directories are checked too -- `-uall` is used so a
    directory is reported by its contained paths rather than collapsed.
    """
    a_file = "scratch-A.txt"
    b_file = "scratch-B.txt"
    (sandbox.wt_a / a_file).write_text("A scratch\n")
    (sandbox.wt_b / b_file).write_text("B scratch\n")
    (sandbox.wt_a / "adir").mkdir()
    (sandbox.wt_a / "adir" / "nested.txt").write_text("A nested\n")

    others_a = _untracked(sandbox.wt_a)
    others_b = _untracked(sandbox.wt_b)

    assert others_a, "worktree A reported no untracked files; comparison would be vacuous"
    assert others_b, "worktree B reported no untracked files; comparison would be vacuous"

    assert a_file in others_a and "adir/nested.txt" in others_a
    assert b_file in others_b

    assert a_file not in others_b
    assert "adir/nested.txt" not in others_b
    assert b_file not in others_a

    # And the files genuinely do not exist on the other side's disk.
    assert not (sandbox.wt_b / a_file).exists()
    assert not (sandbox.wt_a / b_file).exists()
    assert not (sandbox.wt_b / "adir").exists()

    # `git status` agrees with `ls-files --others` (the surface an agent reads).
    status_b = _porcelain_status(sandbox.wt_b)
    assert f"?? {b_file}" in status_b
    assert not any(a_file in ln for ln in status_b)


# ==========================================================================
# 3. BUS ROOT CANONICALITY -- the runtime plane must NOT fork
# ==========================================================================


def _print_root(script: Path, cwd: Path, *, override: Optional[str]) -> str:
    env = dict(os.environ)
    env.pop("EPYC_BUS_ROOT", None)
    if override is not None:
        env["EPYC_BUS_ROOT"] = override
    proc = subprocess.run(
        [sys.executable, str(script), "--print-root"],
        capture_output=True, text=True, cwd=str(cwd), env=env,
    )
    assert proc.returncode == 0, (
        f"{script} --print-root exited {proc.returncode}\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    out = proc.stdout.strip()
    assert out, f"{script} --print-root printed nothing (stderr: {proc.stderr})"
    return out


@pytest.fixture(scope="module")
def session_bus_script() -> Path:
    if not SESSION_BUS_PY.is_file():
        pytest.skip(f"session_bus.py not present at {SESSION_BUS_PY}")
    size = SESSION_BUS_PY.stat().st_size
    assert size >= MIN_SESSION_BUS_BYTES, (
        f"{SESSION_BUS_PY} is only {size} bytes -- that is not the real module, "
        "and asserting against a stub would pass for the wrong reason"
    )
    return SESSION_BUS_PY


def test_print_root_is_canonical_with_no_override(session_bus_script: Path):
    assert _print_root(session_bus_script, REPO_ROOT, override=None) == CANONICAL_BUS_ROOT


def test_print_root_does_not_follow_a_relocated_copy(session_bus_script: Path,
                                                     tmp_path: Path):
    """The regression this closes, stated as a physical experiment.

    A worktree checkout IS a relocated copy of this module. Copy it somewhere
    arbitrary and the answer must not move with it. The old
    `Path(__file__).resolve().parents[2]` code would have printed
    `<tmp>/coordination/session-bus`; that exact string is asserted absent, so
    the test fails loudly against the old resolution instead of merely
    "not equalling canonical" for some unrelated reason.
    """
    relocated = tmp_path / "somewhere" / "else" / "entirely" / "session_bus.py"
    relocated.parent.mkdir(parents=True)
    shutil.copy2(session_bus_script, relocated)
    assert relocated.stat().st_size == session_bus_script.stat().st_size

    file_relative_answer = str(relocated.resolve().parents[2] / "coordination" / "session-bus")
    assert file_relative_answer != CANONICAL_BUS_ROOT, "the experiment is not discriminating"

    out = _print_root(relocated, relocated.parent, override=None)
    assert out != file_relative_answer, (
        "the bus root followed the relocated copy -- __file__-relative "
        "resolution is back and five worktrees would run five buses"
    )
    assert out == CANONICAL_BUS_ROOT


def test_print_root_honours_the_env_override(session_bus_script: Path, tmp_path: Path):
    """NEGATIVE CONTROL. Without this, 'canonical' is indistinguishable from
    'prints a constant and ignores everything'."""
    fake = tmp_path / "not-the-real-bus"
    out = _print_root(session_bus_script, REPO_ROOT, override=str(fake))
    assert out == str(fake)
    assert out != CANONICAL_BUS_ROOT
    # ...and the override does not stick: the next call with it unset is canonical.
    assert _print_root(session_bus_script, REPO_ROOT, override=None) == CANONICAL_BUS_ROOT


def test_every_lane_worktrees_own_copy_prints_the_same_canonical_root():
    """The deployed claim: whichever checkout's copy answers, one bus.

    Each lane runs ITS OWN file at its own path with its own cwd. If any lane
    is on a commit predating the fix, this is where it shows up.
    """
    copies = {}
    for agent in LANE_AGENTS:
        script = LANE_WORKTREE_ROOT / agent / "scripts" / "coordination" / "session_bus.py"
        if script.is_file() and script.stat().st_size >= MIN_SESSION_BUS_BYTES:
            copies[agent] = script
    if len(copies) < 2:
        pytest.skip(
            "fewer than two lane worktrees carry session_bus.py under "
            f"{LANE_WORKTREE_ROOT}; nothing cross-checkout to compare"
        )

    roots = {agent: _print_root(script, script.parent, override=None)
             for agent, script in copies.items()}
    assert set(roots.values()) == {CANONICAL_BUS_ROOT}, (
        f"lane copies of session_bus.py disagree about the bus root: {roots}"
    )


# ==========================================================================
# 4. THE DEPLOYED LANE WORKTREES
# ==========================================================================


def _parse_worktree_list(porcelain: str) -> Dict[Path, Dict[str, str]]:
    """Parse `git worktree list --porcelain` into {path: attributes}.

    Records are blank-line separated; each line is either `key value` or a
    bare flag (`detached`, `bare`, `prunable`, `locked`).
    """
    worktrees: Dict[Path, Dict[str, str]] = {}
    current: Optional[Dict[str, str]] = None
    for raw in porcelain.splitlines():
        line = raw.rstrip("\n")
        if not line.strip():
            current = None
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current = {}
            worktrees[Path(value)] = current
        else:
            assert current is not None, f"attribute line before any worktree line: {line!r}"
            current[key] = value
    return worktrees


def _lanes_on_disk() -> Dict[str, Path]:
    """Lane worktrees that physically exist, independent of git's opinion.

    Deliberately filesystem-only. `git worktree list` is exactly the surface
    that goes blind when the shared clone's `.git/worktrees/` administrative
    data is destroyed, so it cannot be the thing that decides whether the
    environment "has" lanes -- otherwise a broken deployment skips itself
    into a green run.
    """
    if not LANE_WORKTREE_ROOT.is_dir():
        return {}
    return {agent: LANE_WORKTREE_ROOT / agent
            for agent in LANE_AGENTS
            if (LANE_WORKTREE_ROOT / agent).is_dir()}


@pytest.fixture(scope="module")
def registered_worktrees() -> Dict[Path, Dict[str, str]]:
    """Worktrees as registered by the CANONICAL CLONE.

    Queried from `/workspace` rather than from this checkout on purpose: the
    registrations live in the canonical clone's `.git/worktrees/`, so asking
    a lane about itself makes an unregistered lane un-diagnosable (git in a
    lane whose admin dir is gone cannot answer any question at all).
    """
    if not (CANONICAL_CLONE / ".git").exists():
        pytest.skip(f"{CANONICAL_CLONE} is not a git checkout on this host")
    proc = subprocess.run(
        ["git", "-C", str(CANONICAL_CLONE), "worktree", "list", "--porcelain"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        pytest.skip(
            f"git worktree list failed in the canonical clone {CANONICAL_CLONE}: "
            f"{proc.stderr.strip()}"
        )
    parsed = _parse_worktree_list(proc.stdout)
    assert parsed, (
        "git worktree list --porcelain produced no records at all -- the "
        "parser or the repo is broken; refusing to report a vacuous pass"
    )
    assert CANONICAL_CLONE in parsed or CANONICAL_CLONE.resolve() in {
        p.resolve() for p in parsed
    }, (
        f"{CANONICAL_CLONE} is not a registered worktree of its own repository; "
        "the canonical runtime plane is not where the two-plane model says"
    )
    return parsed


def test_the_five_lane_worktrees_are_registered_on_their_lane_branches(
        registered_worktrees: Dict[Path, Dict[str, str]]):
    """Phase 2's deployment assertion.

    Honest skip only when the migration has not run here at all -- i.e. no
    lane DIRECTORY exists on disk. Once the directories exist, absence from
    the registration table is a failure, not an absence: those are checkouts
    that agents are working in and git has stopped recognising.
    """
    on_disk = _lanes_on_disk()
    if not on_disk:
        pytest.skip(
            f"no lane worktree directories under {LANE_WORKTREE_ROOT} -- the "
            "worktree-per-main migration has not been run in this environment"
        )

    missing_dirs = sorted(set(LANE_AGENTS) - set(on_disk))
    assert not missing_dirs, (
        f"partial worktree rollout on disk: have {sorted(on_disk)}, missing {missing_dirs}"
    )

    unregistered = sorted(a for a, p in on_disk.items() if p not in registered_worktrees)
    assert not unregistered, (
        f"lane worktrees exist on disk but are NOT registered in "
        f"{CANONICAL_CLONE}/.git/worktrees: {unregistered}. Their checkouts are "
        "intact; git in them is dead. This is the shared-clone coupling that "
        "worktree isolation does not remove."
    )

    branches = {}
    for agent, path in on_disk.items():
        attrs = registered_worktrees[path]
        assert "detached" not in attrs, f"{agent} worktree is detached, not on a lane branch"
        branches[agent] = attrs.get("branch")

    expected = {agent: f"refs/heads/lane/{agent}" for agent in LANE_AGENTS}
    assert branches == expected, f"lane branch mismatch: {branches}"

    # One branch per lane -- the exclusivity proven structurally above,
    # observed in the live deployment.
    assert len(set(branches.values())) == len(LANE_AGENTS)

    # And they are genuinely separate working trees, not five names for one.
    assert len({p.resolve() for p in on_disk.values()}) == len(LANE_AGENTS)


def test_each_lane_worktree_is_a_functioning_git_checkout():
    """Registration is not enough -- the lane has to actually WORK.

    This is the test that catches the failure mode the registration table
    cannot describe: every lane checkout present and complete on disk, every
    `.git` pointer file intact, and every git command inside them failing
    because the target of that pointer -- which lives inside the SHARED
    clone -- was removed. Asserted per lane, from the lane, with the real
    command an agent would run.
    """
    on_disk = _lanes_on_disk()
    if not on_disk:
        pytest.skip(f"no lane worktree directories under {LANE_WORKTREE_ROOT}")

    broken: Dict[str, str] = {}
    branches: Dict[str, str] = {}
    for agent, path in on_disk.items():
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--absolute-git-dir"],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            broken[agent] = proc.stderr.strip()
            continue
        admin = Path(proc.stdout.strip())
        assert admin.is_dir(), f"{agent}: admin dir {admin} does not exist"
        head = subprocess.run(
            ["git", "-C", str(path), "symbolic-ref", "--short", "HEAD"],
            capture_output=True, text=True,
        )
        assert head.returncode == 0, f"{agent}: {head.stderr.strip()}"
        branches[agent] = head.stdout.strip()

    assert not broken, (
        "lane worktrees whose git metadata is unreachable: " + repr(broken) +
        " -- the checkouts are on disk and their .git pointers are intact, so "
        "the damage is in the shared clone's .git/worktrees/, not in the lane"
    )
    assert branches == {agent: f"lane/{agent}" for agent in on_disk}, branches


def test_lane_working_trees_live_outside_the_shared_clone():
    """Hazard (c), for the half of it that IS closed.

    A recursive delete in the shared clone can only reach paths inside the
    shared clone. The lane WORKING TREES are siblings on another filesystem
    path, so the versioned work itself is structurally out of that blast
    radius. Asserted by path containment rather than by executing a
    destructive command.
    """
    on_disk = _lanes_on_disk()
    if not on_disk:
        pytest.skip(f"no lane worktree directories under {LANE_WORKTREE_ROOT}")

    clone = CANONICAL_CLONE.resolve()
    for agent, path in on_disk.items():
        resolved = path.resolve()
        assert clone not in resolved.parents and resolved != clone, (
            f"lane worktree {agent} at {path} resolves inside the shared clone "
            f"{clone} -- a recursive clean there would take it with it"
        )


def test_lane_git_metadata_still_lives_inside_the_shared_clone_residual_coupling():
    """CHARACTERISATION OF THE GAP -- deliberately asserts the coupling that
    remains, so the isolation claim cannot silently overstate itself.

    Each lane's `.git` is a pointer FILE (not a directory) whose target is
    `<shared clone>/.git/worktrees/<agent>`. That target is inside the shared
    clone's blast radius even though the working tree is not. Consequence,
    observed live: destroying `.git/worktrees/` in the shared clone kills git
    in all five lanes at once while leaving every byte of their work intact.

    Asserted on the pointer text, so it holds whether or not the target
    currently exists. If lanes are ever moved to a genuinely separate clone,
    this test fails and forces WORKTREE_MIGRATION.md to be updated with it.
    """
    on_disk = _lanes_on_disk()
    if not on_disk:
        pytest.skip(f"no lane worktree directories under {LANE_WORKTREE_ROOT}")

    clone = CANONICAL_CLONE.resolve()
    for agent, path in on_disk.items():
        dot_git = path / ".git"
        assert dot_git.is_file(), (
            f"{agent}: expected a worktree pointer file at {dot_git}, "
            f"found {'a directory' if dot_git.is_dir() else 'nothing'}"
        )
        text = dot_git.read_text().strip()
        assert text.startswith("gitdir:"), f"{agent}: unexpected pointer {text!r}"
        target = (path / text.split(":", 1)[1].strip()).resolve()
        expect = clone / ".git" / "worktrees" / agent
        # Compared by device+inode, NOT by path string. This repository is
        # reachable as `/workspace` (bind alias) and `/mnt/raid0/llm/epyc-root`
        # (canonical); `resolve()` does not collapse the bind mount, so the two
        # spellings of ONE directory compare unequal. On 2026-08-12 the three
        # relative-gitdir worktrees were re-registered ABSOLUTE under the
        # canonical spelling and this assertion failed on the spelling while the
        # coupling it characterises was unchanged -- exactly the "one directory,
        # several names" defect class the B-series fixes. Identity is dev+inode
        # (same primitive as serialized_push.repo_key and scripts/lib/env.sh).
        assert target.exists(), (
            f"{agent}: pointer target {target} does not exist -- the lane's git "
            "admin dir is missing; do NOT run `git worktree prune`, re-register it"
        )
        assert os.stat(target).st_dev == os.stat(expect).st_dev and \
               os.stat(target).st_ino == os.stat(expect).st_ino, (
            f"{agent}: pointer resolves to {target}, which is not the same "
            f"directory as {expect} -- the residual coupling this test "
            "characterises has changed; update WORKTREE_MIGRATION.md"
        )


def test_worktree_registrations_are_identical_from_every_path_to_the_repo():
    """THE ROOT CAUSE of the residual coupling, stated as a property.

    This repository is reachable by two paths of different depth -- the
    canonical clone `/workspace` (depth 1) and `/mnt/raid0/llm/epyc-root`
    (depth 4), one directory, shared inode, and pytest.ini instructs agents
    to use the second. git records each worktree with a RELATIVE `gitdir`
    pointer of the form `../../../../<abs path minus leading slash>`, which
    resolves correctly only from the path whose depth it was written for.
    Reached by the other name, every such pointer resolves to a doubled,
    non-existent path and git reports the worktree as `prunable` -- so
    `git worktree prune`, or the `git gc` that runs it, deletes a perfectly
    live worktree's administrative data.

    That is not a hypothesis. On 2026-08-12 all five lane worktrees lost
    their admin directories this way while this file was being written:
    checkouts intact, `.git` pointer files intact, every git command in them
    dead.

    The property: the set of registered worktrees must not depend on which
    name you used to reach the repository. Both directions -- the paths must
    agree, and the listing must be non-empty so agreement is not vacuous.
    """
    if not ALT_CLONE.exists() or not (CANONICAL_CLONE / ".git").exists():
        pytest.skip("this host does not expose the repository under two paths")
    try:
        same_repo = (CANONICAL_CLONE / ".git").stat().st_ino == (ALT_CLONE / ".git").stat().st_ino
    except OSError as exc:  # pragma: no cover - environment probe
        pytest.skip(f"cannot stat both clone paths: {exc}")
    if not same_repo:
        pytest.skip(f"{CANONICAL_CLONE} and {ALT_CLONE} are not the same repository")

    listings = {}
    for clone in (CANONICAL_CLONE, ALT_CLONE):
        proc = subprocess.run(
            ["git", "-C", str(clone), "worktree", "list", "--porcelain"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"git worktree list failed in {clone}: {proc.stderr}"
        parsed = _parse_worktree_list(proc.stdout)
        assert parsed, f"{clone} reported no worktrees at all"
        listings[clone] = parsed

    # Every listing includes the clone's own working tree under its own name;
    # that entry legitimately differs. Compare the OTHER worktrees.
    others = {
        clone: {p for p in parsed if p.resolve() != clone.resolve()}
        for clone, parsed in listings.items()
    }
    assert any(others.values()), (
        "no linked worktrees registered at all -- this comparison would be vacuous"
    )
    assert others[CANONICAL_CLONE] == others[ALT_CLONE], (
        "the same repository reports DIFFERENT worktrees depending on which "
        f"path you reach it by:\n  via {CANONICAL_CLONE}: {sorted(map(str, others[CANONICAL_CLONE]))}\n"
        f"  via {ALT_CLONE}: {sorted(map(str, others[ALT_CLONE]))}\n"
        "Relative gitdir pointers resolve against the caller's path depth, so "
        "every worktree looks prunable from the deeper path and `git worktree "
        "prune` / `git gc` there destroys live worktrees' admin data."
    )

    # Same statement, from git's own mouth: nothing live may be prunable.
    for clone, parsed in listings.items():
        prunable = sorted(str(p) for p, attrs in parsed.items()
                          if "prunable" in attrs and p.is_dir())
        assert not prunable, (
            f"via {clone}, git considers these EXISTING worktrees prunable: "
            f"{prunable} -- a gc or prune from this path will delete them"
        )


def test_the_canonical_bus_root_is_a_real_single_directory():
    """The runtime plane exists, is one directory, and is inside the shared
    clone (which is what makes 'the canonical clone owns it' true rather than
    an aspiration). Skips honestly off-host."""
    root = Path(CANONICAL_BUS_ROOT)
    if not root.exists():
        pytest.skip(f"{root} does not exist on this host")
    assert root.is_dir()
    assert CANONICAL_CLONE.resolve() in root.resolve().parents
    entries = list(root.iterdir())
    assert entries, f"{root} is empty -- an empty bus is not evidence of a live bus"
