"""DP-4: sequencer-state guard for git writes in shared child clones (scan + hook)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))
import git_sequencer_scan as scan  # noqa: E402

HOOK = HOOKS / "check_git_sequencer.sh"
ID = ["-c", "user.name=t", "-c", "user.email=t@t"]


def g(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *ID, *args], check=check,
                          capture_output=True, text=True)


@pytest.fixture()
def root(tmp_path: Path, monkeypatch) -> Path:
    r = tmp_path / "llm"
    r.mkdir()
    monkeypatch.setenv("SEQUENCER_GUARD_ROOT", str(r))
    return r


def _make(root: Path, name: str = "child") -> Path:
    r = root / name
    r.mkdir()
    g(r, "init", "-q", "-b", "main")
    (r / "f").write_text("base\n")
    g(r, "add", "f")
    g(r, "commit", "-qm", "base")
    return r


def _conflict_cherry_pick(r: Path) -> None:
    g(r, "checkout", "-qb", "other")
    (r / "f").write_text("other\n")
    g(r, "commit", "-qam", "other")
    g(r, "checkout", "-q", "main")
    (r / "f").write_text("main\n")
    g(r, "commit", "-qam", "main")
    assert g(r, "cherry-pick", "other", check=False).returncode != 0


@pytest.fixture()
def busy(root: Path) -> Path:
    r = _make(root)
    _conflict_cherry_pick(r)
    return r


def test_clean_shared_clone_allows(root: Path) -> None:
    r = _make(root)
    assert scan.classify("git add f", str(r)) == "allow"


def test_cherry_pick_in_flight_blocks_writes(busy: Path) -> None:
    for cmd in ("git add f", "git commit -m x", "git checkout main", "git -C {r} add -u"):
        v = scan.classify(cmd.format(r=busy), str(busy))
        assert v.startswith("block:sequencer:"), (cmd, v)
        assert "CHERRY_PICK_HEAD" in v and "unmerged-paths(1)" in v


def test_framing_cd_dash_C_and_subshell(busy: Path, tmp_path: Path) -> None:
    elsewhere = str(tmp_path)
    assert scan.classify(f"cd {busy} && git add f", elsewhere).startswith("block:sequencer:")
    assert scan.classify(f"git -C {busy} commit -m x", elsewhere).startswith("block:sequencer:")
    assert scan.classify(f"bash -c 'cd {busy}; git add f'", elsewhere).startswith("block:sequencer:")
    assert scan.classify("git add f", elsewhere) == "allow"           # cwd elsewhere
    # symlink reach (repos/<name> -> shared clone)
    link = tmp_path / "repos"
    link.mkdir()
    (link / "child").symlink_to(busy)
    assert scan.classify("git add f", str(link / "child")).startswith("block:sequencer:")


def test_reads_controls_and_override_pass(busy: Path) -> None:
    for cmd in ("git status", "git diff", "git log", "git cherry-pick --continue",
                "git cherry-pick --abort", "git stash list",
                "SEQUENCER_OWNER=1 git add f"):
        assert scan.classify(cmd, str(busy)) == "allow", cmd


def test_state_markers_each_detected(root: Path) -> None:
    r = _make(root)
    gd = Path(g(r, "rev-parse", "--absolute-git-dir").stdout.strip())
    for name in ("MERGE_HEAD", "REBASE_HEAD"):
        (gd / name).write_text("0" * 40 + "\n")
        assert name in scan.classify("git commit -m x", str(r)), name
        (gd / name).unlink()
    (gd / "rebase-merge").mkdir()
    assert "rebase-merge" in scan.classify("git add f", str(r))
    (gd / "rebase-merge").rmdir()
    assert scan.classify("git add f", str(r)) == "allow"


def test_unmerged_paths_alone_block(busy: Path) -> None:
    gd = Path(g(busy, "rev-parse", "--absolute-git-dir").stdout.strip())
    (gd / "CHERRY_PICK_HEAD").unlink()           # leave only the unmerged index entries
    v = scan.classify("git add f", str(busy))
    assert v.startswith("block:sequencer:") and "unmerged-paths" in v and "CHERRY" not in v


def test_linked_worktree_and_non_shared_repo_not_guarded(root: Path, tmp_path: Path) -> None:
    r = _make(root)
    wt = root / "worktrees" / "wt"
    g(r, "worktree", "add", "-q", "-b", "lane", str(wt))
    _conflict_cherry_pick(r)                     # busy shared clone; lane worktree is clean
    assert scan.classify("git add f", str(wt)) == "allow"
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    g(outside, "init", "-q", "-b", "main")
    (outside / "f").write_text("a\n")
    g(outside, "add", "f")
    g(outside, "commit", "-qm", "b")
    _conflict_cherry_pick_noop = None            # non-shared repo with a marker still allowed
    gd = Path(g(outside, "rev-parse", "--absolute-git-dir").stdout.strip())
    (gd / "MERGE_HEAD").write_text("0" * 40 + "\n")
    assert scan.classify("git add f", str(outside)) == "allow"


def _hook(cmd: str, cwd: Path, root: Path) -> subprocess.CompletedProcess:
    import os
    payload = json.dumps({"tool_name": "Bash", "cwd": str(cwd), "tool_input": {"command": cmd}})
    env = {**os.environ, "SEQUENCER_GUARD_ROOT": str(root)}
    return subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True,
                          text=True, env=env)


def test_hook_exit_codes(busy: Path, root: Path) -> None:
    r = _hook("git add f", busy, root)
    assert r.returncode == 2 and "CHERRY_PICK_HEAD" in r.stderr and "SEQUENCER_OWNER=1" in r.stderr
    assert _hook("git status", busy, root).returncode == 0
    assert _hook("SEQUENCER_OWNER=1 git add f", busy, root).returncode == 0
    assert _hook("ls -la", busy, root).returncode == 0
