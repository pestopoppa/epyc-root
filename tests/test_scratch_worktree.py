"""scratch_worktree.py (sparse + marker) and the 30-minute fast reclaim of marked trees in worktree_gate."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/system/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


wg = _load("worktree_gate")
sw = _load("scratch_worktree")


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch):
    monkeypatch.setattr(wg, "REFERENCE_SOURCES", [])
    monkeypatch.setattr(wg, "REFERENCE_FILES", [])
    monkeypatch.setattr(wg, "REFERENCE_GLOB_FILES", [])


@pytest.fixture
def repo(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    main = tmp_path / "main"
    git(tmp_path, "clone", str(origin), str(main))
    for d in ("artifacts", "benchmarks", "data", "scripts", "docs"):
        (main / d).mkdir()
        (main / d / "f.txt").write_text(d)
    (main / "artifacts" / "operator").mkdir()
    (main / "artifacts" / "operator" / "ratify_x.sh").write_text("x")
    (main / "artifacts" / "operator" / "sub").mkdir()
    (main / "artifacts" / "operator" / "sub" / "big.bin").write_text("b")
    (main / "README.md").write_text("r")
    git(main, "add", ".")
    git(main, "commit", "-m", "init")
    git(main, "push", "origin", "HEAD:main")
    git(main, "fetch", "origin")
    return main


def _verdict(path):
    wt = wg._find(str(path))
    wg.classify(wt, base="origin/main", min_idle_days=1.0, probe=wg.Probe(), canonical_roots=[],
                now=time.time())
    return wt


def _age(path, minutes):
    t = time.time() - minutes * 60
    gd = Path(git(path, "rev-parse", "--path-format=absolute", "--git-dir").strip())
    for p in (Path(path), gd / "HEAD", gd / "index", gd / "logs" / "HEAD"):
        if p.exists():
            os.utime(p, (t, t))


def test_sparse_excludes_heavy_dirs_and_full_keeps_them(repo, tmp_path):
    p = Path(sw.add("s1", repo=str(repo), root=str(tmp_path / "wts")))
    assert (p / "scripts" / "f.txt").exists() and (p / "README.md").exists()
    for d in ("benchmarks", "data"):
        assert not (p / d).exists()
    assert not (p / "artifacts" / "f.txt").exists() and not (p / "artifacts" / "operator" / "sub").exists()
    assert (p / "artifacts" / "operator" / "ratify_x.sh").exists()   # hooks read these
    f = Path(sw.add("s2", repo=str(repo), root=str(tmp_path / "wts"), full=True))
    for d in sw.EXCLUDED:
        assert (f / d / "f.txt").exists()


def test_marker_contents_and_tree_stays_clean(repo, tmp_path):
    p = Path(sw.add("s3", repo=str(repo), root=str(tmp_path / "wts"), purpose="unit", created_by="tester"))
    text = (p / sw.MARKER).read_text()
    for k in ("created_by", "created_at", "purpose", "tester", "unit"):
        assert k in text
    assert git(p, "status", "--porcelain").strip() == ""


def test_marked_landed_idle_tree_is_removable_unmarked_keeps_old_rule(repo, tmp_path):
    marked = Path(sw.add("m", repo=str(repo), root=str(tmp_path / "wts")))
    plain = tmp_path / "wts" / "u"
    git(repo, "worktree", "add", "-b", "b/u", str(plain), "origin/main")
    _age(marked, 45)
    _age(plain, 45)
    assert _verdict(marked).verdict == wg.REMOVABLE
    assert _verdict(plain).verdict == "RECENT"          # 45 min < the 1-day default rule


def test_marked_tree_idle_under_30_min_is_recent(repo, tmp_path):
    marked = Path(sw.add("m2", repo=str(repo), root=str(tmp_path / "wts")))
    _age(marked, 10)
    assert _verdict(marked).verdict == "RECENT"


def test_marked_but_unlanded_is_never_removable(repo, tmp_path):
    marked = Path(sw.add("m3", repo=str(repo), root=str(tmp_path / "wts")))
    (marked / "x.txt").write_text("x")
    git(marked, "add", "x.txt")
    git(marked, "commit", "-m", "unlanded")
    _age(marked, 120)
    assert _verdict(marked).verdict == "UNLANDED"
