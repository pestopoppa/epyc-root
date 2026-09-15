"""Unit tests for scripts/system/autokernel_disk_sweep.py against temp git repos and a fake /proc.

No real process is spawned or signalled: liveness comes from a synthetic proc tree.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("aksweep", ROOT / "scripts/system/autokernel_disk_sweep.py")
sweep = importlib.util.module_from_spec(_SPEC)
sys.modules["aksweep"] = sweep
_SPEC.loader.exec_module(sweep)
_REAL_CONFIRM = sweep.operator_confirm

@pytest.fixture(autouse=True)
def _operator_confirms(monkeypatch):
    """Model the operator typing the sha prefix; test_apply_requires_operator_confirmation undoes it."""
    monkeypatch.setattr(sweep, "operator_confirm", lambda todo, sha: True)


GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
}


def sh(*args, cwd=None):
    env = dict(os.environ, **GIT_ENV)
    r = subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True)
    assert r.returncode == 0, (args, r.stderr)
    return r.stdout


def fake_proc(root: Path, pid: int, ppid: int, cmd: str, cwd: Path | None, fds: list[Path] = (),
              unreadable: bool = False) -> None:
    d = root / str(pid)
    d.mkdir(parents=True)
    (d / "stat").write_text(f"{pid} ({cmd.split()[0][-15:]}) S {ppid} 0 0 0")
    (d / "cmdline").write_bytes(b"\x00".join(a.encode() for a in cmd.split()) + b"\x00")
    if unreadable:
        (d / "cwd").mkdir()  # readlink on a non-symlink raises: models EACCES
    elif cwd is not None:
        (d / "cwd").symlink_to(cwd)
    (d / "fd").mkdir()
    for i, f in enumerate(fds):
        (d / "fd" / str(i)).symlink_to(f)


@pytest.fixture()
def world(tmp_path):
    base = Path(os.path.realpath(tmp_path))
    origin = base / "origin.git"
    repo = base / "repo"
    sh("git", "init", "-q", "--bare", "-b", "main", str(origin))
    sh("git", "clone", "-q", str(origin), str(repo))
    # model a network remote: tracking refs come from `fork`, whose URL is https (never contacted)
    sh("git", "remote", "add", "fork", "https://example.invalid/fork.git", cwd=repo)
    (repo / ".gitignore").write_text("results/\nnode_modules/\n")
    (repo / "README").write_text("x\n")
    sh("git", "add", ".gitignore", "README", cwd=repo)
    sh("git", "commit", "-q", "-m", "init", cwd=repo)
    sh("git", "push", "-q", "origin", "HEAD:main", cwd=repo)
    sh("git", "fetch", "-q", "origin", cwd=repo)
    sh("git", "update-ref", "refs/remotes/fork/main", "origin/main", cwd=repo)

    acc = base / "wt" / "acceptance"
    mains = base / "wt" / "mains"
    tmp = base / "tmp"
    for d in (acc, mains, tmp):
        d.mkdir(parents=True)

    def wt(path: Path, branch: str | None = None):
        if branch:
            sh("git", "worktree", "add", "-q", "-b", branch, str(path), "origin/main", cwd=repo)
        else:
            sh("git", "worktree", "add", "-q", "--detach", str(path), "origin/main", cwd=repo)
        return path

    trees = {
        "clean": wt(acc / "clean-pushed-tree", "lane/clean-pushed-tree"),
        "dirty": wt(acc / "dirty-tree-0001"),
        "unpushed": wt(acc / "unpushed-tree-0001", "lane/unpushed-tree-0001"),
        "cited": wt(acc / "cited-tree-0001"),
        "live": wt(acc / "live-tree-0001"),
        "session": wt(acc / "session-cwd-tree"),
        "evidence": wt(acc / "evidence-tree-0001"),
        "roster": wt(mains / "akx-roster-main"),
        "tasklane": wt(mains / "autokernel-task-20990101"),
        "notak": wt(mains / "unrelated-main-lane"),
    }
    (trees["dirty"] / "scratch.patch").write_text("wip\n")
    (trees["clean"] / "node_modules" / "icons").mkdir(parents=True)
    (trees["clean"] / "node_modules" / "icons" / "receipt.json").write_text("{}")  # not evidence
    (repo / "README").write_text("landed\n")
    sh("git", "commit", "-q", "-am", "landed change", cwd=repo)
    sh("git", "push", "-q", "origin", "HEAD:main", cwd=repo)
    sh("git", "fetch", "-q", "origin", cwd=repo)
    sh("git", "update-ref", "refs/remotes/fork/main", "origin/main", cwd=repo)
    landed = wt(acc / "landed-dirty-tree")
    sh("git", "checkout", "-q", "HEAD~1", cwd=landed)
    (landed / "README").write_text("landed\n")  # same blob as origin/main: dirty but landed
    (trees["unpushed"] / "new.txt").write_text("n\n")
    sh("git", "add", "new.txt", cwd=trees["unpushed"])
    sh("git", "commit", "-q", "-m", "local only", cwd=trees["unpushed"])
    (trees["evidence"] / "results").mkdir()
    (trees["evidence"] / "results" / "VERDICT.json").write_text("{}")

    plains = {
        "plain": tmp / "aku-plain-removable",
        "receipt": tmp / "aku-evidence-dir",
        "nested": tmp / "autokernel-nested-git",
        "state": tmp / "aku12a-store-in-loop-state",
        "other": tmp / "not-a-candidate",
        "livestore": tmp / "aku77-demo-loop-store",
        "sibling": tmp / "aku77-demo-loop-builds",
        "statref": tmp / "aku-stateref-target-dir",
    }
    for p in plains.values():
        p.mkdir()
        (p / "data.bin").write_bytes(b"0" * 4096)
    (plains["receipt"] / "fold-receipt.json").write_text("{}")
    (plains["livestore"] / "loop-status.json").write_text(json.dumps({"x": str(plains["statref"])}))
    (plains["plain"] / "seal-30b-accuracy.json").write_text("{}")  # SEAL paper copy: not evidence
    (plains["nested"] / "inner").mkdir()
    (plains["nested"] / "inner" / ".git").mkdir()

    handoffs = base / "handoffs"
    handoffs.mkdir()
    (handoffs / "h.md").write_text(f"Evidence lives at `{trees['cited']}` (do not lose).\n")
    state = base / "state"
    state.mkdir()
    (state / "loop-status.json").write_text(json.dumps({"store": str(plains["state"])}))

    bus = base / "bus"
    (bus / "heartbeats").mkdir(parents=True)
    (bus / "heartbeats" / "inference.json").write_text(json.dumps(
        {"agent": "inference", "state": "working", "task_id": "task-20990101"}))
    (bus / "config.yaml").write_text("roster:\n  - {id: inference, role: inference-main}\n  - {id: akx-roster-main, role: service}\n")

    proc = base / "proc"
    proc.mkdir()
    fake_proc(proc, 100, 1, "/usr/bin/codex", base)  # session root; cwd=base is an ancestor of all
    fake_proc(proc, 101, 100, "cmake --build build", trees["session"])
    fake_proc(proc, 200, 1, "python3 bench.py", base, fds=[trees["live"] / "README"])
    fake_proc(proc, 201, 1, "python3 -m loop", base, fds=[plains["livestore"] / "loop-status.json"])

    out = base / "out"
    common = [
        "--out-dir", str(out), "--recency-hours", "0", "--jobs", "2",
        "--worktree-glob", str(acc / "*"), "--worktree-glob", str(mains / "*"),
        "--tmp-glob", str(tmp / "aku*"), "--tmp-glob", str(tmp / "autokernel-*"),
        "--mains-root", str(mains), "--allowed-root", str(base / "wt"), "--allowed-root", str(tmp),
        "--proc-root", str(proc), "--path-alias", "/nonexistent-alias=/nowhere",
        "--bus-root", str(bus), "--lock-dir", str(base / "nolocks"),
        "--live-git-source", "/nonexistent:HEAD:.", "--cite-git-source", "/nonexistent:HEAD:.",
        "--retention-git-source", "/nonexistent:HEAD:.",
        "--cite-file-glob", str(handoffs / "*.md"), "--state-path", str(state),
    ]
    return dict(base=base, repo=repo, trees=trees, plains=plains, proc=proc, out=out, common=common)


def run_scan(world, extra=()):
    rc = sweep.main([*world["common"], *extra])
    assert rc == 0
    manifests = sorted(world["out"].glob("autokernel-disk-sweep-manifest-*.json"))
    m = manifests[-1]
    data = m.read_bytes()
    return m, hashlib.sha256(data).hexdigest(), json.loads(data)


@pytest.fixture()
def neutral_codex(world):
    cwd = world["base"] / "codex-home"
    cwd.mkdir()
    (world["proc"] / "100" / "cwd").unlink()
    (world["proc"] / "100" / "cwd").symlink_to(cwd)
    for pid in ("200", "201"):
        (world["proc"] / pid / "cwd").unlink()
        (world["proc"] / pid / "cwd").symlink_to(cwd)
    return world


def verdicts(manifest):
    return {os.path.basename(r["path"]): r["verdict"] for r in manifest["rows"]}


def test_scan_classifies_every_rule(neutral_codex):
    w = neutral_codex
    mpath, sha, m = run_scan(w)
    v = verdicts(m)
    assert m["process_probe"]["state"] == "COMPLETE"
    assert v["clean-pushed-tree"] == "REMOVE"
    assert v["dirty-tree-0001"] == "KEEP-dirty"
    rows = {os.path.basename(r["path"]): r for r in m["rows"]}
    assert rows["dirty-tree-0001"]["dirty_landed"]["all_landed"] is False
    assert v["landed-dirty-tree"] == "KEEP-dirty"  # annotation never changes the verdict
    assert rows["landed-dirty-tree"]["dirty_landed"]["all_landed"] is True
    assert v["unpushed-tree-0001"] == "KEEP-unpushed"
    assert v["cited-tree-0001"] == "KEEP-referenced"
    assert v["live-tree-0001"] == "KEEP-live"
    assert v["session-cwd-tree"] == "KEEP-active-session"
    assert v["evidence-tree-0001"] == "ARCHIVE-evidence"
    assert v["akx-roster-main"] == "KEEP-referenced"  # roster lane, rule (e)
    assert v["autokernel-task-20990101"] == "KEEP-active-session"  # active task lane
    assert "unrelated-main-lane" not in v  # mains filtered by name regex
    assert v["aku-plain-removable"] == "REMOVE"
    assert v["aku-evidence-dir"] == "ARCHIVE-evidence"
    assert v["autokernel-nested-git"] == "KEEP-unverifiable"
    assert v["aku12a-store-in-loop-state"] == "KEEP-referenced"
    assert "not-a-candidate" not in v
    assert v["aku77-demo-loop-store"] == "KEEP-live"
    assert v["aku77-demo-loop-builds"] == "KEEP-referenced"   # name family of a held store
    assert v["aku-stateref-target-dir"] == "KEEP-referenced"  # named in a held store's state
    assert Path(str(mpath) + ".sha256").read_text().split()[0] == sha
    assert m["summary"]["REMOVE"]["count"] == 2


def test_recency_guard_keeps_recent_trees(neutral_codex):
    _, _, m = run_scan(neutral_codex, ["--recency-hours", "1"])
    assert set(verdicts(m).values()) <= {"KEEP-active-session"}


def test_session_cwd_ancestor_keeps_everything_below(world):
    # codex cwd == base, an ancestor of every candidate: literal rule => all KEEP-active-session
    _, _, m = run_scan(world)
    assert set(verdicts(m).values()) == {"KEEP-active-session"}
    assert any("ancestor of a scan root" in x for x in m["active_session"]["warnings"])


def test_apply_refuses_wrong_sha(neutral_codex):
    w = neutral_codex
    mpath, sha, _ = run_scan(w)
    rc = sweep.main(["--apply", "--manifest", str(mpath), "--manifest-sha", "0" * 64])
    assert rc == 2
    assert w["trees"]["clean"].exists() and w["plains"]["plain"].exists()


def test_apply_removes_only_remove_rows_and_rechecks(neutral_codex):
    w = neutral_codex
    mpath, sha, m = run_scan(w)
    # between review and apply the clean tree becomes dirty: the per-row re-check must catch it
    (w["trees"]["clean"] / "late.txt").write_text("late\n")
    rc = sweep.main(["--apply", "--manifest", str(mpath), "--manifest-sha", sha, "--recency-hours", "0"])
    assert rc == 0
    assert not w["plains"]["plain"].exists()          # REMOVE row, still clean -> removed
    assert w["trees"]["clean"].exists()               # re-check found it dirty -> skipped
    for key in ("dirty", "unpushed", "cited", "live", "session", "evidence", "roster", "tasklane"):
        assert w["trees"][key].exists(), key
    for key in ("receipt", "nested", "state", "other"):
        assert w["plains"][key].exists(), key
    receipts = list(w["out"].glob("*.apply-*.jsonl"))
    events = [json.loads(line) for line in receipts[0].read_text().splitlines()]
    assert any(e["event"] == "skip" and e["path"].endswith("clean-pushed-tree") for e in events)


def test_apply_worktree_uses_git_worktree_remove(neutral_codex):
    w = neutral_codex
    mpath, sha, _ = run_scan(w)
    rc = sweep.main(["--apply", "--manifest", str(mpath), "--manifest-sha", sha, "--recency-hours", "0"])
    assert rc == 0
    assert not w["trees"]["clean"].exists()
    listing = sh("git", "worktree", "list", "--porcelain", cwd=w["repo"])
    assert "clean-pushed-tree" not in listing
    assert "dirty-tree-0001" in listing
    # the branch survives worktree removal (no ref deletion, no prune)
    assert "lane/clean-pushed-tree" in sh("git", "branch", "--list", cwd=w["repo"])


def test_apply_recency_recheck_at_apply_time(neutral_codex):
    w = neutral_codex
    mpath, sha, _ = run_scan(w)
    rc = sweep.main(["--apply", "--manifest", str(mpath), "--manifest-sha", sha, "--recency-hours", "1"])
    assert rc == 0
    assert w["trees"]["clean"].exists() and w["plains"]["plain"].exists()


def test_apply_refuses_whole_run_on_partial_probe(neutral_codex):
    w = neutral_codex
    mpath, sha, _ = run_scan(w)
    fake_proc(w["proc"], 300, 1, "some other agent", None, unreadable=True)
    rc = sweep.main(["--apply", "--manifest", str(mpath), "--manifest-sha", sha])
    assert rc == 3
    assert w["trees"]["clean"].exists() and w["plains"]["plain"].exists()


def test_apply_refuses_when_heartbeat_unknown(neutral_codex):
    w = neutral_codex
    mpath, sha, _ = run_scan(w)
    (w["base"] / "bus" / "heartbeats" / "inference.json").unlink()
    rc = sweep.main(["--apply", "--manifest", str(mpath), "--manifest-sha", sha])
    assert rc == 3
    assert w["plains"]["plain"].exists()


def test_probe_skips_kernel_threads_and_zombies(tmp_path):
    proc = tmp_path / "proc"
    fake_proc(proc, 2, 0, "kthreadd", None, unreadable=True)
    fake_proc(proc, 50, 2, "kworker", None, unreadable=True)
    fake_proc(proc, 60, 1, "ok", tmp_path)
    z = proc / "70"
    z.mkdir()
    (z / "stat").write_text("70 (zomb) Z 1 0 0")
    snap = sweep.probe_processes(str(proc), [])
    assert snap.state == "COMPLETE"
    assert set(snap.procs) == {60}


def test_probe_unknown_when_proc_unlistable(tmp_path):
    snap = sweep.probe_processes(str(tmp_path / "missing"), [])
    assert snap.state == "UNKNOWN"


def test_short_basenames_match_only_as_pairs():
    idx = sweep.RefIndex()
    idx.add_text("cite", "see /mnt/raid0/llm/worktrees/inf70/champion2/build-cpu/bin and b3 elsewhere", "h")
    assert idx.lookup("/mnt/raid0/llm/worktrees/inf70/champion2") == {"cite": "h"}
    assert idx.lookup("/mnt/raid0/llm/worktrees/inf70/b3") == {}


def test_apply_requires_operator_confirmation(neutral_codex, monkeypatch):
    w = neutral_codex
    mpath, sha, _ = run_scan(w)
    monkeypatch.setattr(sweep, "operator_confirm", _REAL_CONFIRM)
    monkeypatch.setattr(sys, "stdin", open(os.devnull))  # not a TTY: an agent harness
    rc = sweep.main(["--apply", "--manifest", str(mpath), "--manifest-sha", sha, "--recency-hours", "0"])
    assert rc == 4
    assert w["trees"]["clean"].exists() and w["plains"]["plain"].exists()


def test_local_path_remote_is_not_pushed(tmp_path):
    assert sweep.is_network_url("https://github.com/x/y.git")
    assert sweep.is_network_url("git@github.com:x/y.git")
    assert not sweep.is_network_url("/mnt/raid0/llm/tmp/ak-loop-tree")
    assert not sweep.is_network_url("file:///mnt/raid0/llm/llama.cpp")
    assert not sweep.is_network_url("../llama.cpp")


def test_only_local_remotes_means_unpushed(neutral_codex):
    w = neutral_codex
    sh("git", "remote", "remove", "fork", cwd=w["repo"])  # origin is a local path
    _, _, m = run_scan(w)
    assert verdicts(m)["clean-pushed-tree"] == "KEEP-unpushed"
