"""Tests for scripts/system/worktree_gate.py — temp git repos only, no network, no real worktrees.

Each verdict is pinned in both directions where it matters: the one REMOVABLE shape is removed by
`remove`, and every refusal class (unlanded, dirty, locked, keep marker, roster lane, referenced by
a live launch script, named in a live process ENVIRONMENT, ignored evidence, recent) is refused.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("worktree_gate", ROOT / "scripts/system/worktree_gate.py")
wg = importlib.util.module_from_spec(_SPEC)
sys.modules["worktree_gate"] = wg
_SPEC.loader.exec_module(wg)


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env=env).stdout


@pytest.fixture(autouse=True)
def _hermetic_reference_sources(monkeypatch):
    monkeypatch.setattr(wg, "REFERENCE_SOURCES", [])
    monkeypatch.setattr(wg, "REFERENCE_FILES", [])
    monkeypatch.setattr(wg, "REFERENCE_GLOB_FILES", [])


@pytest.fixture
def repo(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    main = tmp_path / "main"
    git(tmp_path, "clone", str(origin), str(main))
    (main / ".gitignore").write_text("out/\n")
    (main / "a.txt").write_text("a\n")
    git(main, "add", ".")
    git(main, "commit", "-m", "init")
    git(main, "push", "origin", "HEAD:main")
    git(main, "fetch", "origin")
    return main


def add_wt(repo, tmp_path, name, *, landed=True, parent="wts"):
    path = tmp_path / parent / name
    path.parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "add", "-b", f"b/{name}", str(path), "origin/main")
    (path / f"{name}.txt").write_text(name)
    git(path, "add", f"{name}.txt")
    git(path, "commit", "-m", f"work {name}")
    if landed:
        git(path, "push", "origin", f"HEAD:main")
        git(repo, "fetch", "origin")
    return path


def verdict(path, *, min_idle=0.0, probe=None):
    wt = wg._find(str(path))
    assert wt is not None
    wg.classify(wt, base="origin/main", min_idle_days=min_idle,
                probe=probe if probe is not None else wg.Probe(),
                canonical_roots=[], now=__import__("time").time())
    return wt


def test_landed_clean_is_removable_and_remove_keeps_branch(repo, tmp_path):
    p = add_wt(repo, tmp_path, "ok")
    assert verdict(p).verdict == wg.REMOVABLE
    ok, msg = wg.remove_one(str(p), base="origin/main", min_idle_days=0, fetch=False)
    assert ok, msg
    assert not p.exists()
    assert "b/ok" in git(repo, "branch", "--list", "b/ok")      # branch ref kept


def test_unlanded_is_refused(repo, tmp_path):
    p = add_wt(repo, tmp_path, "wip", landed=False)
    wt = verdict(p)
    assert wt.verdict == "UNLANDED" and wt.unlanded == 1
    ok, _ = wg.remove_one(str(p), base="origin/main", min_idle_days=0, fetch=False)
    assert not ok and p.exists()


def test_squash_landed_counts_as_landed(repo, tmp_path):
    """git cherry is patch-id based: the same patch landed under another sha is landed."""
    p = add_wt(repo, tmp_path, "sq", landed=False)
    other = tmp_path / "other"
    git(tmp_path, "clone", str(tmp_path / "origin.git"), str(other))
    (other / "sq.txt").write_text("sq")
    git(other, "add", "sq.txt")
    git(other, "commit", "-m", "same patch, different sha")
    git(other, "push", "origin", "HEAD:main")
    git(repo, "fetch", "origin")
    assert verdict(p).verdict == wg.REMOVABLE


def test_dirty_is_refused(repo, tmp_path):
    p = add_wt(repo, tmp_path, "dirty")
    (p / "untracked.txt").write_text("x")
    assert verdict(p).verdict == "DIRTY"


def test_git_lock_is_protected(repo, tmp_path):
    p = add_wt(repo, tmp_path, "locked")
    git(repo, "worktree", "lock", "--reason", "load-bearing: test", str(p))
    wt = verdict(p)
    assert wt.verdict == "PROTECTED" and "locked" in wt.reasons[0]


def test_gitdir_keep_marker_is_protected_without_dirtying(repo, tmp_path):
    p = add_wt(repo, tmp_path, "keepme")
    gd = Path(git(p, "rev-parse", "--absolute-git-dir").strip())
    (gd / "epyc-keep").write_text("DS41 EPYC_ROOT_REPO\n")
    assert git(p, "status", "--porcelain") == ""
    assert verdict(p).verdict == "PROTECTED"


@pytest.mark.parametrize("marker", wg.KEEP_MARKERS)
def test_top_level_keep_marker_is_protected(repo, tmp_path, marker):
    p = add_wt(repo, tmp_path, "mk" + marker.strip(".").replace("-", "").lower())
    (p / marker).write_text("keep")
    assert verdict(p).verdict == "PROTECTED"


def test_roster_lane_is_protected(repo, tmp_path):
    p = add_wt(repo, tmp_path, "mainZ", parent="worktrees/mains")
    assert verdict(p).verdict == "PROTECTED"


def test_reference_in_live_launch_script_is_refused(repo, tmp_path):
    """The 2026-10-04 incident: a DS41 launcher exported EPYC_ROOT_REPO=<tree>."""
    p = add_wt(repo, tmp_path, "root-main-epyc-root-repo")
    scripts = tmp_path / "llmtmp" / "ds41-scope"
    scripts.mkdir(parents=True)
    (scripts / "swap_transfer.sh").write_text(f'export EPYC_ROOT_REPO="{p}"\n')
    probe = wg.gather_probe(sources=[(str(tmp_path / "llmtmp"), (".sh",), 4, 30)], files=[],
                            glob_files=[])
    wt = verdict(p, probe=probe)
    assert wt.verdict == "REFERENCED" and "swap_transfer.sh" in wt.reasons[0]
    # a sibling whose name merely shares the prefix is NOT referenced
    q = add_wt(repo, tmp_path, "root-main")
    assert verdict(q, probe=probe).verdict == wg.REMOVABLE


def test_reference_from_inside_the_tree_itself_does_not_count(repo, tmp_path):
    p = add_wt(repo, tmp_path, "selfref")
    probe = wg.Probe()
    probe.add_text(f"cd {p}\n", str(p / "run.sh"))
    assert verdict(p, probe=probe).verdict == wg.REMOVABLE


def test_process_environment_naming_tree_is_busy(repo, tmp_path):
    p = add_wt(repo, tmp_path, "envheld")
    proc = subprocess.Popen(["sleep", "30"], env=dict(os.environ, EPYC_ROOT_REPO=str(p)),
                            cwd=str(tmp_path))
    try:
        wt = verdict(p, probe=wg.gather_probe(files=[], sources=[], glob_files=[]))
        assert wt.verdict == "BUSY" and "argv/environ" in wt.reasons[0]
    finally:
        proc.kill()
        proc.wait()


def test_process_cwd_inside_tree_is_busy(repo, tmp_path):
    p = add_wt(repo, tmp_path, "cwdheld")
    proc = subprocess.Popen(["sleep", "30"], cwd=str(p))
    try:
        assert verdict(p, probe=wg.gather_probe(files=[], sources=[], glob_files=[])).verdict == "BUSY"
    finally:
        proc.kill()
        proc.wait()


def test_ignored_evidence_file_is_refused(repo, tmp_path):
    p = add_wt(repo, tmp_path, "evid")
    (p / "out").mkdir()
    (p / "out" / "VERDICT_run1.json").write_text("{}")
    assert verdict(p).verdict == "EVIDENCE"


def test_recent_is_refused_under_min_idle(repo, tmp_path):
    p = add_wt(repo, tmp_path, "fresh")
    assert verdict(p, min_idle=7).verdict == "RECENT"


def test_evidence_regex_matches_disk_sweep():
    spec = importlib.util.spec_from_file_location("aksweep", ROOT / "scripts/system/autokernel_disk_sweep.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["aksweep"] = mod
    spec.loader.exec_module(mod)
    assert wg.EVIDENCE_RE.pattern == mod.EVIDENCE_RE.pattern


def test_report_and_from_report_token(repo, tmp_path, capsys):
    a = add_wt(repo, tmp_path, "r1")
    b = add_wt(repo, tmp_path, "r2", landed=False)
    rep = wg.build_report([str(repo)], base="origin/main", min_idle_days=0, sizes=True,
                          canonical_roots=[])
    rows = {Path(r["path"]).name: r for r in rep["worktrees"]}
    assert rows["r1"]["verdict"] == wg.REMOVABLE and rows["r2"]["verdict"] == "UNLANDED"
    assert rows["r1"]["size_bytes"] and rep["totals"]["size_bytes"] >= rows["r1"]["size_bytes"]
    out = tmp_path / "rep.json"
    out.write_text(json.dumps(rep))
    assert wg.main(["remove", "--no-fetch", "--from-report", str(out), "--confirm", "bad"]) == 2
    assert a.exists()
    assert wg.main(["remove", "--no-fetch", "--from-report", str(out),
                    "--confirm", rep["removable_token"]]) == 0
    assert not a.exists() and b.exists()


def test_should_continue_aborts_scan(repo, tmp_path):
    add_wt(repo, tmp_path, "s1")

    class Stop(Exception):
        pass

    def stop():
        raise Stop

    with pytest.raises(Stop):
        wg.build_report([str(repo)], base="origin/main", min_idle_days=0, sizes=False,
                        should_continue=stop)
