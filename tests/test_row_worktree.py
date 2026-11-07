"""Tests for scripts/coordination/job_templates/row_worktree.py — tmp_path only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in ("scripts/coordination/churn", "scripts/coordination/job_templates", "scripts/system"):
    sys.path.insert(0, str(ROOT / p))
import row_worktree as rw  # noqa: E402
import worktree_gate as wg  # noqa: E402


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout


@pytest.fixture
def env(tmp_path, monkeypatch):
    tmproot = tmp_path / "tmproot"
    scratch = tmproot / "row-w"
    scratch.mkdir(parents=True)
    flags = tmp_path / "flags"
    (flags / "ready").mkdir(parents=True)
    (flags / "ready" / "W-1.json").write_text(json.dumps({"id": "W-1", "scratch_root": str(scratch)}))
    (flags / "ready" / "W-NS.json").write_text(json.dumps({"id": "W-NS"}))
    monkeypatch.setenv("RECLAIM_TMP_ROOT", str(tmproot))
    monkeypatch.setenv("RECLAIM_TRASH_ROOT", str(tmp_path / "trash"))
    monkeypatch.setenv("SAFETY_AUDIT_LOG", str(tmp_path / "audit.log"))
    for k in ("REFERENCE_SOURCES", "REFERENCE_FILES", "REFERENCE_GLOB_FILES"):
        monkeypatch.setattr(wg, k, [])
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    repo = tmp_path / "repo"
    git(tmp_path, "clone", str(origin), str(repo))
    (repo / "a").write_text("a")
    git(repo, "add", "a")
    git(repo, "commit", "-m", "init")
    git(repo, "push", "origin", "main")
    git(repo, "fetch", "origin")
    monkeypatch.setattr(wg, "DEFAULT_REPOS", [str(repo)])
    return dict(tmp=tmp_path, scratch=scratch, flags=flags, repo=repo)


def test_scratch_root_error():
    t = "/mnt/raid0/llm/tmp"
    assert rw.scratch_root_error(None, t) == "no scratch_root"
    assert rw.scratch_root_error("rel/x", t) == "no scratch_root"
    assert rw.scratch_root_error("/mnt/raid0/llm/tmp", t)
    assert rw.scratch_root_error("/mnt/raid0/llm/tmp/../x", t)
    assert rw.scratch_root_error("/mnt/raid0/llm/tmp/compute-flags/x", t) == "scratch_root protected"
    assert rw.scratch_root_error("/mnt/raid0/llm/tmp/row-x", t) is None


def test_add_creates_detached_worktree_under_scratch_and_refuses_overwrite(env, capsys):
    args = ["add", "--row", "W-1", "--repo", str(env["repo"]), "--flags", str(env["flags"])]
    assert rw.main(args) == 0
    dest = env["scratch"] / "worktrees" / "wt"
    assert capsys.readouterr().out.strip() == str(dest)
    assert (dest / "a").exists()
    assert [os.path.realpath(w.path) for w in rw.row_worktrees(str(env["scratch"]))] == [os.path.realpath(dest)]
    assert rw.main(args) == 3


def test_add_refuses_without_scratch_root(env):
    assert rw.main(["add", "--row", "W-NS", "--repo", str(env["repo"]), "--flags", str(env["flags"])]) == 6


def test_release_dry_then_apply(env):
    fl = ["--flags", str(env["flags"])]
    assert rw.main(["add", "--row", "W-1", "--repo", str(env["repo"]), *fl]) == 0
    dest = env["scratch"] / "worktrees" / "wt"
    assert rw.main(["release", "--row", "W-1", *fl]) == 0
    assert dest.exists()
    assert rw.main(["release", "--row", "W-1", "--apply", *fl, "--salvage-dir", str(env["tmp"] / "s")]) == 0
    assert not dest.exists() and wg.list_worktrees(str(env["repo"])) == []


def test_release_ignores_worktrees_outside_scratch(env):
    other = env["tmp"] / "elsewhere"
    git(env["repo"], "worktree", "add", "--detach", str(other), "origin/main")
    res = rw.release_row_worktrees(str(env["scratch"]), apply=True, salvage_dir=str(env["tmp"] / "s"))
    assert res == [] and other.exists()
