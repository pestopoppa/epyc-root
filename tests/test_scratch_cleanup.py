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
