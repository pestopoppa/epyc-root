"""Tests for scripts/coordination/churn/reclaim_row.py — tmp_path only (fake flags, fake tmp root, temp trash)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in ("scripts/coordination/churn", "scripts/coordination/job_templates", "scripts/system"):
    sys.path.insert(0, str(ROOT / p))
import reclaim_row as rr  # noqa: E402
import row_worktree as rw  # noqa: E402
import worktree_gate as wg  # noqa: E402

RID = "R-1"


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout


@pytest.fixture
def env(tmp_path, monkeypatch):
    tmproot = tmp_path / "tmproot"
    scratch = tmproot / "row-r1"
    flags = tmp_path / "flags"
    for d in ("ready", "grants", "filing-done"):
        (flags / d).mkdir(parents=True)
    scratch.mkdir(parents=True)
    trash = tmp_path / "trash"
    monkeypatch.setenv("RECLAIM_TMP_ROOT", str(tmproot))
    monkeypatch.setenv("RECLAIM_TRASH_ROOT", str(trash))
    monkeypatch.setenv("SAFETY_AUDIT_LOG", str(tmp_path / "audit.log"))
    monkeypatch.setattr(wg, "REFERENCE_SOURCES", [])
    monkeypatch.setattr(wg, "REFERENCE_FILES", [])
    monkeypatch.setattr(wg, "REFERENCE_GLOB_FILES", [])
    monkeypatch.setattr(wg, "DEFAULT_REPOS", [])
    monkeypatch.setattr(rr, "open_fd_under", lambda root, proc_root="/proc": None)

    class E:
        pass
    e = E()
    e.tmp, e.tmproot, e.scratch, e.flags, e.trash = tmp_path, tmproot, scratch, flags, trash

    def manifest(**kw):
        m = {"schema": "epyc.row.v3", "id": RID, "scratch_root": str(scratch), "keep": ["keepme/*"],
             "result_path": str(scratch / "out" / "result.json"), "notes": ""}
        m.update(kw)
        m = {k: v for k, v in m.items() if v is not None}
        mp = flags / "ready" / f"{RID}.json"
        mp.write_text(json.dumps(m))
        old = time.time() - 3600
        os.utime(mp, (old, old))       # manifest mtime = INPUT RULE cutoff fallback
        return mp

    def end(started=None, filed=True, age_s=0):
        ep = flags / "grants" / f"{RID}.ended"
        ep.write_text("rc=0 reason=complete\n" + (f"started={started}\n" if started else ""))
        if age_s:
            t = time.time() - age_s
            os.utime(ep, (t, t))
        if filed:
            (flags / "filing-done" / f"{RID}.FILED").write_text("FILED\n")

    def run(*args):
        return rr.main([RID, "--flags", str(flags), *args])

    def receipt():
        return json.loads((flags / "filing-done" / f"{RID}.reclaim.json").read_text())

    e.manifest, e.end, e.run, e.receipt = manifest, end, run, receipt
    return e


def write(p: Path, text="x" * 100, old=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    if old:
        t = time.time() - 7200
        os.utime(p, (t, t))
    return p


def trashed(e) -> list[str]:
    out = []
    for dp, dn, fn in os.walk(e.trash):
        out += fn + dn
    return out


def test_no_scratch_root_exit6(env, capsys):
    env.manifest(scratch_root=None)
    env.end()
    assert env.run("--apply") == 6
    assert "REFUSED R-1: no scratch_root" in capsys.readouterr().out
    assert not (env.flags / "filing-done" / f"{RID}.reclaim.json").exists()


def test_scratch_root_outside_tmp_root_exit6(env):
    env.manifest(scratch_root=str(env.tmp / "elsewhere"))
    env.end()
    assert env.run("--apply") == 6


def test_no_end_record_exit2_and_unfiled_exit6(env):
    env.manifest(raw=["raw/*"])
    assert env.run("--apply") == 2
    env.end(filed=False)
    assert env.run("--apply") == 6
    assert env.run("--pre-filed") == 0


def test_no_raw_moves_nothing(env):
    env.manifest()
    env.end()
    f = write(env.scratch / "raw" / "big.bin")
    assert env.run("--apply") == 0
    assert f.exists() and not env.trash.exists()
    assert env.receipt()["state"] == "NO-RAW"


def test_raw_glob_reaps_only_raw(env):
    env.manifest(raw=["raw/*", "keepme/*", "out/*", "inputs/*"])
    env.end()
    raw1 = write(env.scratch / "raw" / "a.bin")
    raw2 = write(env.scratch / "raw" / "sub" / "b.bin")
    keep = write(env.scratch / "keepme" / "k.txt")
    res = write(env.scratch / "out" / "result.json", "{}")
    inp = write(env.scratch / "inputs" / "in.json", old=True)
    other = write(env.scratch / "other.log")
    assert env.run("--apply") == 0
    assert not raw1.exists() and not raw2.exists()
    assert keep.exists() and res.exists() and inp.exists() and other.exists()
    r = env.receipt()
    assert r["apply"] is True and r["state"] == "RECLAIMED"
    assert {os.path.basename(c["path"]) for c in r["candidates"]} == {"a.bin", "sub"}
    assert r["bytes_reclaimed"] == 200
    whys = {os.path.basename(k["path"]): k["why"] for k in r["kept"]}
    assert whys["k.txt"] == "keep-glob" and whys["result.json"] == "result" and whys["in.json"] == "input"
    assert any(n.endswith("-a.bin") for n in trashed(env))


def test_raw_from_notes(env):
    env.manifest(notes="blah raw_globs=raw/*,scratch.tmp more")
    env.end()
    a = write(env.scratch / "raw" / "a.bin")
    b = write(env.scratch / "scratch.tmp")
    assert env.run("--apply") == 0
    assert not a.exists() and not b.exists()


def test_negative_keep_marker_two_levels_down_keeps_dir(env):
    env.manifest(raw=["raw*"])
    env.end()
    d = env.scratch / "rawdir"
    write(d / "x.bin")
    write(d / "l1" / "l2" / "KEEP", "")
    assert env.run("--apply") == 0
    assert (d / "x.bin").exists() and (d / "l1" / "l2" / "KEEP").exists()
    assert env.receipt()["kept"][0]["why"] == "holds-keep-marker"


def test_negative_evidence_inside_raw_is_kept(env):
    env.manifest(raw=["raw"])
    env.end()
    write(env.scratch / "raw" / "junk.bin")
    v = write(env.scratch / "raw" / "VERDICT.json", "{}")
    assert env.run("--apply") == 0
    assert v.exists() and (env.scratch / "raw" / "junk.bin").exists()


def test_negative_dotdot_glob_refused(env):
    env.manifest(raw=["../row-other/*"])
    env.end()
    victim = write(env.tmproot / "row-other" / "x.bin")
    assert env.run("--apply") == 6
    assert victim.exists()
    env.manifest(raw=["/etc/*"])
    assert env.run("--apply") == 6


def test_negative_symlink_out_of_root_kept(env):
    env.manifest(raw=["raw/*"])
    env.end()
    victim = write(env.tmproot / "row-other" / "x.bin")
    (env.scratch / "raw").mkdir()
    (env.scratch / "raw" / "ln").symlink_to(victim)
    assert env.run("--apply") == 0
    assert victim.exists() and (env.scratch / "raw" / "ln").is_symlink()


def test_busy_does_nothing(env, monkeypatch):
    env.manifest(raw=["raw/*"])
    env.end()
    f = write(env.scratch / "raw" / "a.bin")
    monkeypatch.setattr(wg, "gather_probe", lambda *a, **k: wg.Probe(cwds={str(env.scratch.resolve()): "4242"}))
    assert env.run("--apply") == 0
    assert f.exists() and env.receipt()["state"] == "BUSY"


def test_open_fd_busy(env, monkeypatch):
    env.manifest(raw=["raw/*"])
    env.end()
    f = write(env.scratch / "raw" / "a.bin")
    monkeypatch.setattr(rr, "open_fd_under", lambda root, proc_root="/proc": "pid 1 fd -> x")
    assert env.run("--apply") == 0
    assert f.exists() and env.receipt()["state"] == "BUSY"


def test_shared_unfiled_root_blocks(env):
    env.manifest(raw=["raw/*"])
    env.end()
    f = write(env.scratch / "raw" / "a.bin")
    (env.flags / "ready" / "R-2.json").write_text(json.dumps({"id": "R-2", "scratch_root": str(env.scratch)}))
    assert env.run("--apply") == 0
    assert f.exists() and env.receipt()["state"] == "SHARED"


def test_dry_run_moves_nothing_writes_receipt(env, capsys):
    env.manifest(raw=["raw/*"])
    env.end()
    f = write(env.scratch / "raw" / "a.bin")
    assert env.run() == 0
    assert f.exists() and not env.trash.exists()
    r = env.receipt()
    assert r["apply"] is False and len(r["candidates"]) == 1
    out = capsys.readouterr().out
    assert "RECLAIM-DRYRUN row=R-1" in out and "verdict=REAP" in out and "SUMMARY" in out


def test_retention_hold(env):
    env.manifest(retention={"raw_days": 3}, raw=["raw/*"])
    env.end()
    f = write(env.scratch / "raw" / "a.bin")
    assert env.run("--apply") == 0
    assert f.exists() and env.receipt()["state"] == "HOLD"
    env.manifest(notes="raw_days=3 raw_globs=raw/*")
    env.end(age_s=4 * 86400)
    assert env.run("--apply") == 0
    assert not f.exists()


def test_started_line_is_input_cutoff(env):
    env.manifest(raw=["raw/*"])
    env.end(started="2099-01-01T00:00:00Z")     # every file predates the start -> all inputs
    f = write(env.scratch / "raw" / "a.bin")
    assert env.run("--apply") == 0
    assert f.exists()


# ---- row-owned worktrees -------------------------------------------------------------------------------------
@pytest.fixture
def repo(env, monkeypatch):
    origin = env.tmp / "origin.git"
    git(env.tmp, "init", "--bare", "-b", "main", str(origin))
    repo = env.tmp / "repo"
    git(env.tmp, "clone", str(origin), str(repo))
    (repo / "a").write_text("a")
    git(repo, "add", "a")
    git(repo, "commit", "-m", "init")
    git(repo, "push", "origin", "main")
    git(repo, "fetch", "origin")
    monkeypatch.setattr(wg, "DEFAULT_REPOS", [str(repo)])
    return repo


def registered(repo) -> list[str]:
    return [os.path.realpath(w.path) for w in wg.list_worktrees(str(repo))]


def test_clean_landed_row_worktree_removed(env, repo):
    env.manifest()
    env.end()
    wt = env.scratch / "worktrees" / "wt"
    git(repo, "worktree", "add", "--detach", str(wt), "origin/main")
    assert env.run("--apply", "--salvage-dir", str(env.tmp / "salv")) == 0
    assert not wt.exists() and registered(repo) == []
    r = env.receipt()
    assert r["worktrees"][0]["action"] == "REMOVE" and r["worktrees"][0]["deregistered"] is True


def test_dirty_row_worktree_salvaged_trashed_deregistered(env, repo):
    env.manifest(raw=["worktrees/*"])          # the raw glob must NOT trash a registered worktree directly
    env.end()
    wt = env.scratch / "worktrees" / "wt"
    git(repo, "worktree", "add", "--detach", str(wt), "origin/main")
    (wt / "new.txt").write_text("dirty")
    salv = env.tmp / "salv"
    assert env.run("--apply", "--salvage-dir", str(salv)) == 0
    assert not wt.exists() and registered(repo) == []
    w = env.receipt()["worktrees"][0]
    assert w["action"] == "SALVAGE+TRASH+REMOVE" and w["deregistered"] and not w["error"]
    bundle = Path(w["salvage"]["bundle"])
    assert (bundle / "manifest.json").exists() and (bundle / "untracked.tar").stat().st_size > 0
    assert w["salvage"]["salvage_branch"] in git(repo, "branch", "--list", "salvage/*")
    assert env.receipt()["kept"][0]["why"] == "worktree"
