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
_REAL_SOURCES = list(wg.REFERENCE_SOURCES)   # the autouse fixture blanks the module's copy


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



@pytest.fixture(params=["external", "bare"])
def unusual_common_repo(repo, tmp_path, request):
    origin = tmp_path / "origin.git"
    common = tmp_path / ("private.git" if request.param == "external" else "bare-store")
    if request.param == "external":
        main = tmp_path / "external-main"
        git(tmp_path, "clone", "--separate-git-dir", str(common), str(origin), str(main))
        git(main, "config", "core.worktree", str(main))
        assert git(main, "config", "--bool", "core.bare").strip() == "false"
    else:
        git(tmp_path, "clone", "--bare", str(origin), str(common))
        git(common, "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*")
        git(common, "fetch", "origin")
        main = common
    assert Path(git(main, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()).samefile(common)
    return main


def test_unusual_common_registration_and_removal(unusual_common_repo, tmp_path):
    repo = unusual_common_repo
    p = add_wt(repo, tmp_path, "common-ok")
    assert wg._find(str(repo)) is None  # the main repository is never a linked candidate
    assert verdict(p).verdict == wg.REMOVABLE
    ok, msg = wg.remove_one(str(p), base="origin/main", min_idle_days=0, fetch=False)
    assert ok, msg
    assert not p.exists()
    assert "b/common-ok" in git(repo, "branch", "--list", "b/common-ok")


def test_unusual_common_refusals(unusual_common_repo, tmp_path):
    repo = unusual_common_repo
    dirty = add_wt(repo, tmp_path, "common-dirty")
    (dirty / "untracked").write_text("x")
    unlanded = add_wt(repo, tmp_path, "common-unlanded", landed=False)
    kept = add_wt(repo, tmp_path, "common-keep")
    (Path(git(kept, "rev-parse", "--absolute-git-dir").strip()) / "epyc-keep").write_text("keep")
    for path, expected in [(dirty, "DIRTY"), (unlanded, "UNLANDED"), (kept, "PROTECTED")]:
        assert verdict(path).verdict == expected
        ok, _ = wg.remove_one(str(path), base="origin/main", min_idle_days=0, fetch=False)
        assert not ok and path.exists()


def test_owning_repo_fails_closed_for_unknown_and_mismatched_context(repo, tmp_path, monkeypatch):
    bogus = tmp_path / "bogus"
    bogus.mkdir()
    assert wg._find(str(bogus)) is None
    assert wg._find(str(repo)) is None
    nested = repo / "nested"
    nested.mkdir()
    assert wg._find(str(nested)) is None
    original = wg._git
    def mismatched(args, cwd, timeout=60):
        if Path(cwd) == repo:
            return subprocess.CompletedProcess(args, 0, str(tmp_path / "other") + "\n", "")
        return original(args, cwd, timeout)
    monkeypatch.setattr(wg, "_git", mismatched)
    assert wg._owning_repo(str(nested)) is None

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


def _aged(path, days):
    t = os.stat(path).st_mtime - days * 86400
    os.utime(path, (t, t))


def _ref_verdict(repo, tmp_path, name, fname, days_old, *, suffixes=(".sh", ".env", ".bash", ".bak"),
                 max_age=None):
    """A worktree named by one file of the given age in a scratch root; return the verdict."""
    p = add_wt(repo, tmp_path, name)
    root = tmp_path / f"scratch-{name}"
    root.mkdir()
    f = root / fname
    f.write_text(f'export EPYC_ROOT_REPO="{p}"\n')
    _aged(f, days_old)
    probe = wg.gather_probe(sources=[(str(root), suffixes or None, 4, max_age)], files=[], glob_files=[])
    return verdict(p, probe=probe)


def test_fresh_env_reference_still_blocks_and_stale_one_ages_out(repo, tmp_path):
    # NEGATIVE CONTROL first: a live .env reference must still block removal.
    assert _ref_verdict(repo, tmp_path, "envlive", "run.env", 1).verdict == "REFERENCED"
    assert _ref_verdict(repo, tmp_path, "envold", "run.env", wg.BASH_ENV_MAX_AGE_DAYS + 3).verdict == wg.REMOVABLE


def test_fresh_bash_reference_still_blocks_and_stale_one_ages_out(repo, tmp_path):
    assert _ref_verdict(repo, tmp_path, "bashlive", "run.bash", 1).verdict == "REFERENCED"
    assert _ref_verdict(repo, tmp_path, "bashold", "run.bash", wg.BASH_ENV_MAX_AGE_DAYS + 3).verdict == wg.REMOVABLE


def test_stale_bak_is_ignored_but_fresh_bak_still_blocks(repo, tmp_path):
    for fname in ("launch.sh.bak", "launch.bak-20261001", "x.bak"):
        n = fname.replace(".", "-")
        live = _ref_verdict(repo, tmp_path, f"live-{n}", fname, 1, suffixes=None)
        assert live.verdict == "REFERENCED", fname
        stale = _ref_verdict(repo, tmp_path, f"stale-{n}", fname, wg.BAK_STALE_DAYS + 2, suffixes=None)
        assert stale.verdict == wg.REMOVABLE, fname


def test_a_file_merely_containing_bak_in_a_word_is_not_a_backup(repo, tmp_path):
    # a name that only resembles a backup ("kebab.sh") is a live script and must still block
    v = _ref_verdict(repo, tmp_path, "notbak", "kebab.sh", wg.BAK_STALE_DAYS + 2, suffixes=None)
    assert v.verdict == "REFERENCED"


def test_campaign_input_reference_ages_out_with_default_sources(repo, tmp_path):
    row = [r for r in _REAL_SOURCES if r[0].endswith("campaigns/*/inputs")][0]
    assert row[3] == wg.CAMPAIGN_INPUT_MAX_AGE_DAYS   # the shipped table carries the cap
    p = add_wt(repo, tmp_path, "campin")
    root = tmp_path / "campaigns" / "c1" / "inputs"
    root.mkdir(parents=True)
    f = root / "cfg.json"
    f.write_text(str(p))
    _aged(f, 1)
    live = wg.gather_probe(sources=[(str(root), None, 4, row[3])], files=[], glob_files=[])
    assert verdict(p, probe=live).verdict == "REFERENCED"
    _aged(f, row[3] + 5)
    old = wg.gather_probe(sources=[(str(root), None, 4, row[3])], files=[], glob_files=[])
    assert verdict(p, probe=old).verdict == wg.REMOVABLE


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
