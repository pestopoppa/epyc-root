"""Tests for scripts/system/worktree_reaper.py and worktree_salvage.py — temp git repos only."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/system"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/system/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


wg = _load("worktree_gate")
ws = _load("worktree_salvage")
wr = _load("worktree_reaper")

ENV = dict(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def git(cwd, *args, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True,
                          env=dict(os.environ, **ENV)).stdout


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch, tmp_path):
    monkeypatch.setattr(wg, "REFERENCE_SOURCES", [])
    monkeypatch.setattr(wg, "REFERENCE_FILES", [])
    monkeypatch.setattr(wg, "REFERENCE_GLOB_FILES", [])
    monkeypatch.setenv("SAFETY_AUDIT_LOG", str(tmp_path / "safety_audit.log"))
    for k, v in ENV.items():
        monkeypatch.setenv(k, v)


IDLE: dict[str, float] = {}


@pytest.fixture
def env(tmp_path, monkeypatch):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    main = tmp_path / "main"
    git(tmp_path, "clone", str(origin), str(main))
    (main / "a.txt").write_text("a\n")
    git(main, "add", ".")
    git(main, "commit", "-m", "init")
    git(main, "push", "origin", "HEAD:main")
    git(main, "fetch", "origin")
    monkeypatch.setattr(wg, "DEFAULT_REPOS", [str(main)])
    IDLE.clear()
    monkeypatch.setattr(wg, "_idle_days", lambda wt, now: IDLE.get(os.path.realpath(wt.path), 0.0))
    return main


def add_wt(env, tmp_path, name, *, landed=True, idle=10.0, sub="wts"):
    path = tmp_path / sub / name
    path.parent.mkdir(parents=True, exist_ok=True)
    git(env, "worktree", "add", "-b", f"b/{name}", str(path), "origin/main")
    (path / f"{name}.txt").write_text(name)
    git(path, "add", ".")
    git(path, "commit", "-m", f"work {name}")
    if landed:
        git(path, "push", "origin", "HEAD:main")
        git(env, "fetch", "origin")
    IDLE[os.path.realpath(path)] = idle
    return path


def make_dirty(path):
    (path / "a.txt").write_text("a\nmodified\n")
    (path / "new_untracked.txt").write_text("untracked payload\n")


def run(tmp_path, *, apply=True, max_actions=20, probe=None):
    out: list[str] = []
    res = wr.reap(roots=[str(tmp_path / "wts")], ttl_clean=3, ttl_dirty=7,
                  salvage_dir=str(tmp_path / "salvage"), apply=apply, max_actions=max_actions,
                  base="origin/main", probe=probe if probe is not None else wg.Probe(),
                  trash_root=str(tmp_path / "trash"), emit=out.append)
    return res, out


def registered(env):
    return git(env, "worktree", "list", "--porcelain")


def row(res, path):
    return next(r for r in res["rows"] if os.path.realpath(r["path"]) == os.path.realpath(path))


# (1)
def test_clean_landed_idle_removed(env, tmp_path):
    p = add_wt(env, tmp_path, "c1", idle=5)
    res, out = run(tmp_path)
    assert row(res, p)["action"] == "REMOVE", out
    assert not p.exists()
    assert str(p) not in registered(env)
    assert "b/c1" in git(env, "branch", "--list", "b/c1")
    assert out[-1].startswith("WT-REAP SUMMARY") and "remove=1" in out[-1]


# (2)
def test_clean_landed_recent_kept(env, tmp_path):
    p = add_wt(env, tmp_path, "c2", idle=1)
    res, _ = run(tmp_path)
    assert row(res, p)["action"] == "KEEP-RECENT"
    assert p.exists() and str(p) in registered(env)


# (3)
def test_dirty_unlanded_salvaged(env, tmp_path):
    p = add_wt(env, tmp_path, "d1", landed=False, idle=9)
    make_dirty(p)
    head = git(p, "rev-parse", "HEAD").strip()
    res, out = run(tmp_path)
    r = row(res, p)
    assert r["action"] == "SALVAGE", out
    bundles = list((tmp_path / "salvage").iterdir())
    assert len(bundles) == 1
    b = bundles[0]
    for fn in ("HEAD", "BRANCH", "diff.patch", "untracked.tar", "manifest.json"):
        assert (b / fn).is_file(), fn
    man = json.loads((b / "manifest.json").read_text())
    assert (b / "HEAD").read_text().strip() == head
    assert git(env, "rev-parse", man["salvage_branch"]).strip() == head
    assert man["salvage_branch"].startswith("salvage/d1-")
    assert not p.exists()
    assert any("d1" in str(x) for x in (tmp_path / "trash").rglob("d1*"))
    assert str(p) not in registered(env)
    # patch reproduces the modification on a fresh checkout of HEAD
    fresh = tmp_path / "fresh"
    git(env, "worktree", "add", "--detach", str(fresh), head)
    git(fresh, "apply", str(b / "diff.patch"))
    assert (fresh / "a.txt").read_text() == "a\nmodified\n"
    with tarfile.open(b / "untracked.tar") as t:
        assert "new_untracked.txt" in t.getnames()
        assert t.extractfile("new_untracked.txt").read() == b"untracked payload\n"


# (4) negative controls
def test_keep_marker_never_touched(env, tmp_path):
    p = add_wt(env, tmp_path, "k1", landed=False, idle=99)
    make_dirty(p)
    (p / "KEEP").write_text("")
    res, _ = run(tmp_path)
    assert row(res, p)["action"] == "SKIP"
    assert p.exists() and not (tmp_path / "salvage").exists()


def test_locked_never_touched(env, tmp_path):
    p = add_wt(env, tmp_path, "l1", idle=99)
    git(env, "worktree", "lock", str(p))
    res, _ = run(tmp_path)
    assert row(res, p)["action"] == "SKIP"
    assert p.exists() and str(p) in registered(env)


def test_mains_never_touched(env, tmp_path):
    p = add_wt(env, tmp_path, "m1", idle=99, sub="wts/mains")
    res, _ = run(tmp_path)
    assert row(res, p)["action"] == "SKIP"
    assert p.exists()


def test_busy_never_touched(env, tmp_path):
    p = add_wt(env, tmp_path, "busy1", landed=False, idle=99)
    make_dirty(p)

    class BusyProbe(wg.Probe):
        def busy(self, wt_path):
            return "pid 4242 has cwd there"

    res, _ = run(tmp_path, probe=BusyProbe())
    assert row(res, p)["action"] == "KEEP-BUSY"
    assert p.exists() and not (tmp_path / "salvage").exists()


def test_dry_run_changes_nothing(env, tmp_path):
    c = add_wt(env, tmp_path, "dc", idle=99)
    d = add_wt(env, tmp_path, "dd", landed=False, idle=99)
    make_dirty(d)
    before = (registered(env), git(env, "branch", "-a"), git(d, "status", "--porcelain"))
    res, out = run(tmp_path, apply=False)
    assert row(res, c)["action"] == "REMOVE" and row(res, d)["action"] == "SALVAGE"
    assert all(ln.startswith("WT-REAP-DRYRUN") for ln in out)
    assert c.exists() and d.exists()
    assert (registered(env), git(env, "branch", "-a"), git(d, "status", "--porcelain")) == before
    assert not (tmp_path / "salvage").exists() and not (tmp_path / "trash").exists()


def test_max_one(env, tmp_path):
    ps = [add_wt(env, tmp_path, f"x{i}", idle=99) for i in range(3)]
    res, _ = run(tmp_path, max_actions=1)
    assert res["counts"]["remove"] == 1
    assert sum(p.exists() for p in ps) == 2
    assert sum(r["action"] == "KEEP-BUDGET" for r in res["rows"]) == 2


# (5)
def test_salvage_failure_trashes_nothing(env, tmp_path, monkeypatch):
    p = add_wt(env, tmp_path, "f1", landed=False, idle=99)
    make_dirty(p)

    def boom(*a, **k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(ws, "salvage", boom)
    res, _ = run(tmp_path)
    r = row(res, p)
    assert r["action"] == "REFUSED" and "disk full" in r["result"]
    assert p.exists() and str(p) in registered(env)
    assert not (tmp_path / "trash").exists()
    assert res["counts"]["errors"] == 1


def test_fetch_failure_skips_repo(env, tmp_path):
    p = add_wt(env, tmp_path, "nf", idle=99)
    git(env, "remote", "set-url", "origin", str(tmp_path / "nope.git"))
    res, _ = run(tmp_path)
    assert row(res, p)["action"] == "SKIP" and p.exists()


# salvage module directly
def test_salvage_plan_states_and_refusals(env, tmp_path):
    c = add_wt(env, tmp_path, "pc")
    d = add_wt(env, tmp_path, "pd", landed=False)
    assert ws.plan(str(c), probe=wg.Probe())["state"] == "clean-landed"
    pd = ws.plan(str(d), probe=wg.Probe())
    assert pd["state"] == "needs-salvage" and pd["unlanded"] == 1
    assert ws.plan(str(tmp_path), probe=wg.Probe())["refused"]
    (d / ".epyc-keep").write_text("")
    r = ws.retire(str(d), apply=True, salvage_dir=str(tmp_path / "s"), probe=wg.Probe(),
                  trash_root=str(tmp_path / "t"))
    assert r["action"] == "REFUSED" and d.exists()


def test_retire_clean_landed_no_bundle(env, tmp_path):
    c = add_wt(env, tmp_path, "rc")
    r = ws.retire(str(c), apply=True, salvage_dir=str(tmp_path / "s"), probe=wg.Probe(),
                  trash_root=str(tmp_path / "t"))
    assert r["deregistered"] and not c.exists() and not (tmp_path / "s").exists()


def test_cli_usage_error():
    assert wr.main(["--max", "notanint"]) == 2
