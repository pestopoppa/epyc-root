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
import time
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


def test_campaign_input_reference_never_ages_out_with_default_sources(repo, tmp_path):
    row = [r for r in _REAL_SOURCES if r[0].endswith("campaigns/*/inputs")][0]
    assert row[3] is None   # the shipped table carries no cap
    p = add_wt(repo, tmp_path, "campin")
    root = tmp_path / "campaigns" / "c1" / "inputs"
    root.mkdir(parents=True)
    f = root / "cfg.json"
    f.write_text(str(p))
    _aged(f, 400)
    probe = wg.gather_probe(sources=[(str(root),) + tuple(row[1:])], files=[], glob_files=[])
    assert verdict(p, probe=probe).verdict == "REFERENCED"


def test_campaign_env_never_ages_out_but_tmp_env_does(repo, tmp_path):
    # NEGATIVE CONTROL: a 20-day-old launch.env in a campaign dir (shipped source rows) still protects.
    camp_row = [r for r in _REAL_SOURCES if r[0].endswith("autokernel/campaigns/*")][0]
    tmp_row = [r for r in _REAL_SOURCES if r[0].endswith("/tmp")][0]
    age = wg.BASH_ENV_MAX_AGE_DAYS + 6
    p = add_wt(repo, tmp_path, "campenv")
    cdir = tmp_path / "campaigns" / "c1"
    cdir.mkdir(parents=True)
    f = cdir / "launch.env"
    f.write_text(f'export EPYC_ROOT_REPO="{p}"\n')
    _aged(f, age)
    probe = wg.gather_probe(sources=[(str(cdir),) + tuple(camp_row[1:])], files=[], glob_files=[])
    assert verdict(p, probe=probe).verdict == "REFERENCED"
    # the same file in the {LLM}/tmp-shaped source ages out
    q = add_wt(repo, tmp_path, "tmpenv")
    tdir = tmp_path / "llmtmp2"
    tdir.mkdir()
    g = tdir / "launch.env"
    g.write_text(f'export EPYC_ROOT_REPO="{q}"\n')
    _aged(g, age)
    probe2 = wg.gather_probe(sources=[(str(tdir),) + tuple(tmp_row[1:])], files=[], glob_files=[])
    assert verdict(q, probe=probe2).verdict == wg.REMOVABLE


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


# ---- per-repo base resolution (kernel tree has no origin/main) ------------------------------

@pytest.fixture
def kernel_repo(tmp_path):
    """A kernel-shaped repo: origin is 'upstream' with master, NO origin/main; frozen
    production-consolidated-v1 (branch AND a same-named tag, as in llama.cpp) + ak/champion/x."""
    up = tmp_path / "up.git"
    git(tmp_path, "init", "--bare", "-b", "master", str(up))
    k = tmp_path / "kernel"
    git(tmp_path, "clone", str(up), str(k))
    (k / "a.txt").write_text("a\n")
    git(k, "add", ".")
    git(k, "commit", "-m", "init")
    git(k, "push", "origin", "HEAD:master")
    git(k, "fetch", "origin")
    git(k, "branch", "production-consolidated-v1")
    git(k, "tag", "production-consolidated-v1")
    git(k, "branch", "ak/champion/x")
    return k


def kwt(kernel, tmp_path, name, *, to_champion=False):
    path = tmp_path / "wts" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    git(kernel, "worktree", "add", "-b", f"experimental/{name}", str(path), "ak/champion/x")
    (path / f"{name}.txt").write_text(name)
    git(path, "add", f"{name}.txt")
    git(path, "commit", "-m", f"work {name}")
    if to_champion:   # champion advances by a patch-equivalent commit (cherry-pick)
        git(kernel, "worktree", "add", "--detach", str(tmp_path / "wts" / f"champ-{name}"), "ak/champion/x")
        cw = tmp_path / "wts" / f"champ-{name}"
        git(cw, "cherry-pick", f"experimental/{name}")
        git(cw, "branch", "-f", "ak/champion/x", "HEAD")
        git(kernel, "worktree", "remove", str(cw))
    return path


def kverdict(kernel, path):
    wt = wg._find(str(path))
    bases, _ = wg.resolve_bases(str(kernel))
    wg.classify(wt, base=bases, min_idle_days=0.0, probe=wg.Probe(),
                canonical_roots=[], now=time.time() + 86400 * 30)
    return wt


def test_kernel_tree_bases_are_frozen_tip_plus_champions(kernel_repo):
    bases, _ = wg.resolve_bases(str(kernel_repo))
    assert bases == ["refs/heads/production-consolidated-v1", "refs/heads/ak/champion/x"]
    # origin/main does not exist here: the old default would have been UNVERIFIABLE
    assert wg.resolve_bases(str(kernel_repo), "origin/main")[0] == ["origin/main"]


def test_experimental_head_on_champion_tip_is_removable(kernel_repo, tmp_path):
    p = tmp_path / "wts" / "e0"
    git(kernel_repo, "worktree", "add", "-b", "experimental/e0", str(p), "ak/champion/x")
    assert kverdict(kernel_repo, p).verdict == wg.REMOVABLE


def test_experimental_patch_folded_into_champion_is_removable(kernel_repo, tmp_path):
    p = kwt(kernel_repo, tmp_path, "e1", to_champion=True)
    assert kverdict(kernel_repo, p).verdict == wg.REMOVABLE


def test_NEG_unfolded_kernel_commit_is_unlanded(kernel_repo, tmp_path):
    p = kwt(kernel_repo, tmp_path, "e2")
    v = kverdict(kernel_repo, p)
    assert v.verdict == "UNLANDED" and v.unlanded == 1


def test_NEG_frozen_only_match_does_not_make_unfolded_work_landed(kernel_repo, tmp_path):
    # commit on top of the champion that exists on NO accepted base, even though the tree's
    # fork point is an ancestor of the frozen tip: must stay UNLANDED
    p = kwt(kernel_repo, tmp_path, "e3")
    git(p, "commit", "--allow-empty", "-m", "more")
    assert kverdict(kernel_repo, p).verdict == "UNLANDED"


def test_NEG_unknown_base_fails_closed(tmp_path):
    r = tmp_path / "bare"
    git(tmp_path, "init", "-b", "main", str(r))
    (r / "a").write_text("a")
    git(r, "add", ".")
    git(r, "commit", "-m", "i")
    p = tmp_path / "wts" / "w"
    p.parent.mkdir()
    git(r, "worktree", "add", "-b", "w", str(p), "HEAD")
    bases, _ = wg.resolve_bases(str(r))
    assert bases == []
    wt = wg._find(str(p))
    wg.classify(wt, base=bases, min_idle_days=0.0, probe=wg.Probe(),
                canonical_roots=[], now=time.time() + 86400 * 30)
    assert wt.verdict == "UNVERIFIABLE"
    ok, _ = wg.remove_one(str(p), base="auto", min_idle_days=0, fetch=False)
    assert not ok and p.exists()


def test_NEG_unresolvable_champion_ref_is_dropped_not_trusted(kernel_repo):
    git(kernel_repo, "branch", "-D", "ak/champion/x")
    bases, _ = wg.resolve_bases(str(kernel_repo))
    assert bases == ["refs/heads/production-consolidated-v1"]


def test_report_records_resolved_bases(kernel_repo, tmp_path):
    kwt(kernel_repo, tmp_path, "e4")
    rep = wg.build_report([str(kernel_repo)], base="auto", min_idle_days=0, sizes=False,
                          probe=wg.Probe(), canonical_roots=[])
    assert rep["bases"]["kernel"][0] == "refs/heads/production-consolidated-v1"
    assert [w["verdict"] for w in rep["worktrees"] if "e4" in w["path"]] == ["UNLANDED"]

def test_close_lane_selects_only_ticket_lane_class_and_goes_through_gate(repo, tmp_path):
    ok = add_wt(repo, tmp_path, "codex-ni-TKT777-a")
    dirty = add_wt(repo, tmp_path, "ni08-TKT777-b")
    (dirty / "untracked").write_text("x")
    other_ticket = add_wt(repo, tmp_path, "codex-ni-TKT888-c")
    other_class = add_wt(repo, tmp_path, "scratch-TKT777-d")
    # dry-run touches nothing and names the retained tree
    rc, lines = wg.close_lane("TKT777", [str(repo)], base="origin/main", apply=False, fetch=False)
    assert rc == 1 and ok.exists()
    assert any(l.startswith("WOULD-REMOVE") and str(ok) in l for l in lines)
    assert any(l.startswith("RETAINED") and str(dirty) in l and "DIRTY" in l for l in lines)
    rc, lines = wg.close_lane("TKT777", [str(repo)], base="origin/main", apply=True, fetch=False)
    assert rc == 1
    assert not ok.exists() and dirty.exists()          # dirty refused by the gate, never forced
    assert other_ticket.exists() and other_class.exists()


def test_close_lane_refuses_prefix_only_selection(repo, tmp_path):
    p = add_wt(repo, tmp_path, "codex-ni-TKT999-a")
    rc, lines = wg.close_lane("ni", [str(repo)], base="origin/main", apply=True, fetch=False)
    assert rc == 2 and p.exists()
    assert wg.main(["close-lane", "--ticket", "codex"]) == 2
