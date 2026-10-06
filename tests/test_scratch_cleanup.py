"""Tests for scripts/system/scratch_cleanup.py — temp repos and temp scratch roots only."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/system"))
_SPEC = importlib.util.spec_from_file_location("scratch_cleanup", ROOT / "scripts/system/scratch_cleanup.py")
sc = importlib.util.module_from_spec(_SPEC)
sys.modules["scratch_cleanup"] = sc
_SPEC.loader.exec_module(sc)
wg = sc.wg


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env=env).stdout


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(wg, "REFERENCE_SOURCES", [])
    monkeypatch.setattr(wg, "REFERENCE_FILES", [])
    monkeypatch.setattr(wg, "REFERENCE_GLOB_FILES", [])
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    repo = tmp_path / "repo"
    git(tmp_path, "clone", str(origin), str(repo))
    (repo / "a").write_text("a")
    git(repo, "add", "a")
    git(repo, "commit", "-m", "init")
    git(repo, "push", "origin", "HEAD:main")
    git(repo, "fetch", "origin")
    monkeypatch.setattr(wg, "DEFAULT_REPOS", [str(repo)])
    scratch = tmp_path / "llmtmp" / "hx-42"
    scratch.mkdir(parents=True)
    wts = tmp_path / "worktrees"
    wts.mkdir()
    trash = tmp_path / "trash"
    rm = tmp_path / "guarded_rm.sh"
    rm.write_text(f'#!/bin/bash\nset -e\nmkdir -p {trash}\nfor t in "$@"; do mv "$t" {trash}/; done\n')
    rm.chmod(0o755)
    monkeypatch.setattr(sc, "ALLOWED_PARENTS", (str(tmp_path / "llmtmp") + "/", str(wts) + "/"))
    return {"repo": repo, "scratch": scratch, "wts": wts, "trash": trash, "rm": rm, "tmp": tmp_path}


def add_wt(env, name, landed=True):
    p = env["wts"] / name
    git(env["repo"], "worktree", "add", "-b", f"b/{name}", str(p), "origin/main")
    (p / f"{name}.txt").write_text(name)
    git(p, "add", ".")
    git(p, "commit", "-m", name)
    if landed:
        git(p, "push", "origin", "HEAD:main")
        git(env["repo"], "fetch", "origin")
    return p


def decl(env):
    return sc.Decl(dirs=[str(env["scratch"])], worktree_globs=[str(env["wts"] / "hx-42-*")])


def verdicts(entries):
    return {Path(e.path).name: e.verdict for e in entries}


# --------------------------------------------------------------------------- declaration
def test_parse_scratch_field():
    d = sc.parse_scratch("# T\n\n**Status**: x\n**Scratch**: `/mnt/raid0/llm/tmp/hx-42/` · "
                         "worktrees: `/mnt/raid0/llm/worktrees/hx-42-*`\n")
    assert d.dirs == ["/mnt/raid0/llm/tmp/hx-42"]
    assert d.worktree_globs == ["/mnt/raid0/llm/worktrees/hx-42-*"]
    assert d.errors == []
    assert sc.parse_scratch("**Scratch**: none (docs only)\n").none
    assert sc.parse_scratch("# no field\n") is None


@pytest.mark.parametrize("value,needle", [
    ("/home/node/scratch", "must live under"),
    ("/mnt/raid0/llm/tmp/", "too broad"),
    ("/mnt/raid0/llm/tmp/x", "too broad"),
    ("/mnt/raid0/llm/worktrees/*", "too broad"),
    ("somewhere", "declares no path"),
])
def test_invalid_declarations(value, needle):
    d = sc.parse_scratch(f"**Scratch**: {value}\n")
    assert any(needle in e for e in d.errors), d.errors


def test_handoff_without_field_is_refused(tmp_path):
    h = tmp_path / "h.md"
    h.write_text("# handoff\n**Status**: active\n")
    assert sc.main(["plan", "--handoff", str(h)]) == 2


# --------------------------------------------------------------------------- plan
def test_plan_classifies_every_shape(env):
    s = env["scratch"]
    (s / "build").mkdir()
    (s / "build" / "o.bin").write_text("x")
    (s / "pinned").mkdir()
    (s / "pinned" / "KEEP").write_text("DS41 launcher state, keep until the campaign ends")
    (s / "big.gguf").write_text("x")
    (s / "big.gguf.epyc-keep").write_text("reason")
    (s / "results").mkdir()
    (s / "results" / "VERDICT_run.json").write_text("{}")
    add_wt(env, "hx-42-done")
    add_wt(env, "hx-42-wip", landed=False)
    v = verdicts(sc.build_plan(decl(env), repos=[str(env["repo"])], probe=wg.Probe()))
    assert v["build"] == "REMOVE"
    assert v["pinned"] == "KEEP-MARKED"
    assert v["big.gguf"] == "KEEP-MARKED"
    assert v["results"] == "KEEP-EVIDENCE"
    assert v["hx-42-done"] == "REMOVE"
    assert v["hx-42-wip"] == "KEEP-UNLANDED"


def test_reference_from_outside_the_roots_keeps(env):
    p = add_wt(env, "hx-42-launched")
    (env["scratch"] / "state").mkdir()
    probe = wg.Probe()
    probe.add_text(f"export EPYC_ROOT_REPO={p}\nSTATE={env['scratch']}/state\n", "/mnt/raid0/llm/tmp/ds41/run.sh")
    v = verdicts(sc.build_plan(decl(env), repos=[str(env["repo"])], probe=probe))
    assert v["hx-42-launched"] == "KEEP-REFERENCED"
    assert v["state"] == "KEEP-REFERENCED"


def test_in_root_reference_from_a_removed_sibling_does_not_keep(env):
    p = add_wt(env, "hx-42-tree")
    (env["scratch"] / "old.sh").write_text(f"cd {p}\n")
    probe = wg.Probe()
    probe.add_text(f"cd {p}\n", str(env["scratch"] / "old.sh"))
    v = verdicts(sc.build_plan(decl(env), repos=[str(env["repo"])], probe=probe))
    assert v == {"hx-42-tree": "REMOVE", "old.sh": "REMOVE"}


def test_in_root_reference_chain_from_a_kept_entry_keeps_transitively(env):
    """running watchdog -> launcher it calls -> worktree the launcher exports: all kept."""
    p = add_wt(env, "hx-42-tree")
    s = env["scratch"]
    (s / "watchdog").mkdir()
    (s / "watchdog" / "KEEP").write_text("live watchdog")
    (s / "launch.sh").write_text("x")
    probe = wg.Probe()
    probe.add_text(f"bash {s}/launch.sh\n", str(s / "watchdog" / "wd.sh"))
    probe.add_text(f"export EPYC_ROOT_REPO={p}\n", str(s / "launch.sh"))
    v = verdicts(sc.build_plan(decl(env), repos=[str(env["repo"])], probe=probe))
    assert v == {"watchdog": "KEEP-MARKED", "launch.sh": "KEEP-REFERENCED", "hx-42-tree": "KEEP-REFERENCED"}


def test_busy_scratch_is_kept(env):
    d = env["scratch"] / "live"
    d.mkdir()
    proc = subprocess.Popen(["sleep", "30"], cwd=str(d))
    try:
        v = verdicts(sc.build_plan(decl(env), repos=[str(env["repo"])],
                                   probe=wg.gather_probe(sources=[], files=[], glob_files=[])))
        assert v["live"] == "KEEP-BUSY"
    finally:
        proc.kill()
        proc.wait()


# --------------------------------------------------------------------------- apply
def test_apply_removes_through_gate_and_trash(env):
    s = env["scratch"]
    (s / "build").mkdir()
    (s / "keepme").mkdir()
    (s / "keepme" / ".epyc-keep").write_text("why")
    done = add_wt(env, "hx-42-done")
    wip = add_wt(env, "hx-42-wip", landed=False)
    d = decl(env)
    entries = sc.apply_plan(sc.build_plan(d, repos=[str(env["repo"])], probe=wg.Probe()), d,
                            guarded_rm=env["rm"], fetch=False)
    assert not (s / "build").exists() and (env["trash"] / "build").exists()
    assert (s / "keepme").exists()
    assert not done.exists() and wip.exists()
    assert "b/hx-42-done" in git(env["repo"], "branch", "--list", "b/hx-42-done")
    assert {Path(e.path).name for e in entries if e.verdict.startswith("KEEP")} == {"keepme", "hx-42-wip"}


def test_apply_removes_nested_worktree_then_its_dir_and_empty_root(env):
    s = env["scratch"]
    nested_parent = s / "cmp"
    nested_parent.mkdir()
    git(env["repo"], "worktree", "add", "--detach", str(nested_parent / "research"), "origin/main")
    d = sc.Decl(dirs=[str(s)])
    plan = sc.build_plan(d, repos=[str(env["repo"])], probe=wg.Probe())
    assert verdicts(plan)["cmp"] == "REMOVE-AFTER-WORKTREES"
    sc.apply_plan(plan, d, guarded_rm=env["rm"], fetch=False)
    assert not nested_parent.exists()
    assert not s.exists()                                    # emptied declared root: rmdir
    assert str(nested_parent / "research") not in git(env["repo"], "worktree", "list")


def test_apply_without_trash_script_refuses_plain_scratch(env, tmp_path):
    (env["scratch"] / "build").mkdir()
    d = sc.Decl(dirs=[str(env["scratch"])])
    entries = sc.apply_plan(sc.build_plan(d, repos=[str(env["repo"])], probe=wg.Probe()), d,
                            guarded_rm=tmp_path / "missing.sh", fetch=False)
    assert (env["scratch"] / "build").exists()
    assert entries[0].verdict == "KEEP-NO-TRASH"


def test_declared_dir_that_is_a_worktree_is_one_entry_never_enumerated(env):
    p = add_wt(env, "hx-42-whole", landed=False)
    d = sc.Decl(dirs=[str(p)])
    entries = sc.build_plan(d, repos=[str(env["repo"])], probe=wg.Probe())
    assert [(Path(e.path).name, e.kind, e.verdict) for e in entries] == [("hx-42-whole", "worktree", "KEEP-UNLANDED")]


@pytest.mark.parametrize("marker", wg.KEEP_MARKERS)
def test_keep_marker_on_declared_root_protects_root_and_contents(env, monkeypatch, marker):
    root = env["scratch"]
    marker_path = root / marker
    marker_path.write_text("load-bearing scratch root")
    child = root / "ordinary-source.txt"
    child.write_text("preserve these bytes")
    called = env["tmp"] / "guarded-rm-called"
    guard = env["tmp"] / "guarded-rm-record.sh"
    guard.write_text(f'#!/bin/bash\nprintf "called\\n" >> "{called}"\n')
    guard.chmod(0o755)
    monkeypatch.setattr(wg, "gather_probe", lambda **kwargs: wg.Probe())

    d = sc.Decl(dirs=[str(root)])
    entries = sc.build_plan(d, repos=[str(env["repo"])], probe=wg.Probe())
    assert [(Path(e.path).name, e.verdict) for e in entries] == [(root.name, "KEEP-MARKED")]
    sc.apply_plan(entries, d, guarded_rm=guard, fetch=False)

    assert marker_path.read_text() == "load-bearing scratch root"
    assert child.read_text() == "preserve these bytes"
    assert not called.exists()


def test_sibling_keep_marker_on_declared_root_protects_whole_root(env, monkeypatch):
    root = env["scratch"]
    child = root / "ordinary-source.txt"
    child.write_text("preserve these bytes")
    side_marker = Path(str(root) + ".epyc-keep")
    side_marker.write_text("load-bearing scratch root")
    called = env["tmp"] / "guarded-rm-called"
    guard = env["tmp"] / "guarded-rm-record.sh"
    guard.write_text(f'#!/bin/bash\nprintf "called\\n" >> "{called}"\n')
    guard.chmod(0o755)
    monkeypatch.setattr(wg, "gather_probe", lambda **kwargs: wg.Probe())

    d = sc.Decl(dirs=[str(root)])
    entries = sc.build_plan(d, repos=[str(env["repo"])], probe=wg.Probe())
    assert [(Path(e.path).name, e.verdict) for e in entries] == [(root.name, "KEEP-MARKED")]
    sc.apply_plan(entries, d, guarded_rm=guard, fetch=False)

    assert side_marker.read_text() == "load-bearing scratch root"
    assert child.read_text() == "preserve these bytes"
    assert not called.exists()


def test_mixed_declared_roots_keep_marked_root_and_remove_unmarked_sibling(env, monkeypatch):
    parent = env["tmp"] / "llmtmp"
    marked_root = parent / "hx-42-marked"
    plain_root = parent / "hx-42-marked-extra"
    marked_root.mkdir(parents=True)
    plain_root.mkdir()
    (marked_root / "KEEP").write_text("evidence custody")
    sentinel = marked_root / "source.txt"
    sentinel.write_text("preserve")
    removable = plain_root / "plain.txt"
    removable.write_text("remove through trash")
    monkeypatch.setattr(wg, "gather_probe", lambda **kwargs: wg.Probe())

    outside_wt = add_wt(env, "hx-42-outside", landed=False)
    d = sc.Decl(dirs=[str(marked_root), str(plain_root)],
                worktree_globs=[str(env["wts"] / "hx-42-*")])
    entries = sc.build_plan(d, repos=[str(env["repo"])], probe=wg.Probe())
    assert {(Path(e.path).name, e.verdict) for e in entries} == {
        (marked_root.name, "KEEP-MARKED"), (removable.name, "REMOVE"),
        (outside_wt.name, "KEEP-UNLANDED")}
    sc.apply_plan(entries, d, guarded_rm=env["rm"], fetch=False)

    assert sentinel.read_text() == "preserve"
    assert marked_root.exists()
    assert not plain_root.exists()
    assert outside_wt.exists()                  # marker does not cover a worktree outside its root
    assert (env["trash"] / removable.name).read_text() == "remove through trash"


def test_root_marked_after_plan_protects_planned_children_before_any_removal(env, monkeypatch):
    root = env["tmp"] / "llmtmp" / "hx-42-late-marker"
    root.mkdir(parents=True)
    sentinel = root / "source.txt"
    sentinel.write_text("preserve exact bytes")
    wt = root / "hx-42-nested-wt"
    git(env["repo"], "worktree", "add", "--detach", str(wt), "origin/main")
    called = env["tmp"] / "guarded-rm-called"
    guard = env["tmp"] / "guarded-rm-record.sh"
    guard.write_text(f'#!/bin/bash\nprintf "called\\n" >> "{called}"\n')
    guard.chmod(0o755)
    monkeypatch.setattr(wg, "gather_probe", lambda **kwargs: wg.Probe())
    monkeypatch.setattr(
        wg, "remove_one",
        lambda *args, **kwargs: pytest.fail("marked descendant worktree reached remove_one"),
    )

    d = sc.Decl(dirs=[str(root)], worktree_globs=[str(root / "hx-42-*")])
    entries = sc.build_plan(d, repos=[str(env["repo"])], probe=wg.Probe())
    assert {(Path(e.path).name, e.verdict) for e in entries} == {
        (sentinel.name, "REMOVE"), (wt.name, "REMOVE")}
    (root / "KEEP").write_text("marked after planning; protect all descendants")

    sc.apply_plan(entries, d, guarded_rm=guard, fetch=False)

    assert all(e.verdict == "KEEP-MARKED" for e in entries)
    assert sentinel.read_text() == "preserve exact bytes"
    assert wt.exists()
    assert not called.exists()


def test_marked_root_coalesces_overlapping_declared_root_and_worktree_glob(env, monkeypatch):
    root = env["tmp"] / "llmtmp" / "hx-42-protected"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "KEEP").write_text("preserve descendants")
    sentinel = nested / "source.txt"
    sentinel.write_text("preserve exact bytes")
    wt = nested / "hx-42-nested-wt"
    git(env["repo"], "worktree", "add", "--detach", str(wt), "origin/main")
    called = env["tmp"] / "guarded-rm-called"
    guard = env["tmp"] / "guarded-rm-record.sh"
    guard.write_text(f'#!/bin/bash\nprintf "called\\n" >> "{called}"\n')
    guard.chmod(0o755)
    monkeypatch.setattr(wg, "gather_probe", lambda **kwargs: wg.Probe())

    d = sc.Decl(dirs=[str(root), str(nested)],
                worktree_globs=[str(nested / "hx-42-*")])
    entries = sc.build_plan(d, repos=[str(env["repo"])], probe=wg.Probe())
    assert [(Path(e.path).name, e.verdict) for e in entries] == [(root.name, "KEEP-MARKED")]
    sc.apply_plan(entries, d, guarded_rm=guard, fetch=False)

    assert sentinel.read_text() == "preserve exact bytes"
    assert wt.exists()
    assert not called.exists()


def test_marked_nested_root_protects_ancestor_candidate_but_trashes_sibling(env, monkeypatch):
    parent = env["tmp"] / "llmtmp" / "hx-42-parent"
    container = parent / "container"
    kept_root = container / "kept"
    kept_root.mkdir(parents=True)
    (kept_root / "KEEP").write_text("preserve marked descendant")
    sentinel = kept_root / "source.txt"
    sentinel.write_text("preserve exact bytes")
    removable = parent / "unmarked-sibling.txt"
    removable.write_text("remove unrelated sibling")
    monkeypatch.setattr(wg, "gather_probe", lambda **kwargs: wg.Probe())

    d = sc.Decl(dirs=[str(parent), str(kept_root)])
    entries = sc.build_plan(d, repos=[], probe=wg.Probe())
    assert {(Path(e.path).name, e.verdict) for e in entries} == {
        (container.name, "KEEP-MARKED"), (kept_root.name, "KEEP-MARKED"),
        (removable.name, "REMOVE")}
    sc.apply_plan(entries, d, guarded_rm=env["rm"], fetch=False)

    assert sentinel.read_text() == "preserve exact bytes"
    assert (kept_root / "KEEP").read_text() == "preserve marked descendant"
    assert container.exists()
    assert not removable.exists()
    assert (env["trash"] / removable.name).read_text() == "remove unrelated sibling"


def test_parent_declaring_sidecar_marked_root_preserves_marker_file(env, monkeypatch):
    parent = env["tmp"] / "llmtmp" / "hx-42-parent"
    root = parent / "hx-42-custody"
    root.mkdir(parents=True)
    sentinel = root / "source.txt"
    sentinel.write_text("preserve exact bytes")
    side_marker = Path(str(root) + ".epyc-keep")
    side_marker.write_text("load-bearing root")
    removable = parent / "unmarked-sibling.txt"
    removable.write_text("remove unrelated sibling")
    monkeypatch.setattr(wg, "gather_probe", lambda **kwargs: wg.Probe())

    d = sc.Decl(dirs=[str(parent), str(root)])
    entries = sc.build_plan(d, repos=[], probe=wg.Probe())
    assert {(Path(e.path).name, e.verdict) for e in entries} == {
        (root.name, "KEEP-MARKED"), (side_marker.name, "KEEP-MARKED"),
        (removable.name, "REMOVE")}
    sc.apply_plan(entries, d, guarded_rm=env["rm"], fetch=False)

    assert side_marker.read_text() == "load-bearing root"
    assert sentinel.read_text() == "preserve exact bytes"
    assert root.exists()
    assert not removable.exists()
    assert (env["trash"] / removable.name).read_text() == "remove unrelated sibling"


def test_standalone_clone_with_unpushed_commits_is_kept(env):
    clone = env["scratch"] / "clone"
    git(env["tmp"], "clone", "-q", str(env["tmp"] / "origin.git"), str(clone))
    (clone / "x").write_text("x")
    git(clone, "add", "x")
    git(clone, "commit", "-m", "local only")
    v = verdicts(sc.build_plan(decl(env), repos=[str(env["repo"])], probe=wg.Probe()))
    assert v["clone"] == "KEEP-UNLANDED-CLONE"
    git(clone, "push", "-q", "origin", "HEAD:main")
    git(clone, "fetch", "-q", "origin")
    v = verdicts(sc.build_plan(decl(env), repos=[str(env["repo"])], probe=wg.Probe()))
    assert v["clone"] == "REMOVE"
