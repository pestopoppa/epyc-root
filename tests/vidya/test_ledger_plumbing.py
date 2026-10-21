"""2026-10-21 plumbing: one canonical ledger, serialized writers, always-current sync, hook.

Everything runs against tmp paths (VIDYA_STATE_DIR / --ledger); the real canonical ledger is never
touched.
"""
import multiprocessing as mp
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))

import frames as fr  # noqa: E402
import ledger_home  # noqa: E402
import sync as vsync  # noqa: E402
from ledger import Ledger  # noqa: E402

NOW = "2026-10-21T00:00:00Z"
CLI = REPO / "scripts" / "vidya" / "cli.py"


def _frame(i):
    return fr.make_frame(
        frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
        assertion={"claim_id": f"clm-{i}", "evidence_id": f"evd-{i}",
                   "grade": {"Q": "Judged", "T": "Anchored"}},
        provenance={"method": "test", "anchor": f"anchor:{i}"},
        actor="test", authority_scope="test", created_at=NOW)


def _small_index(path, n=3):
    text = (REPO / "research" / "intake_index.yaml").read_text()
    starts = [m.start() for m in re.finditer(r"^- id: intake-", text, re.M)]
    path.write_text(text[starts[0]:starts[n]])
    return path


# ---- canonical path resolution ------------------------------------------------------------

def test_default_is_canonical_not_worktree_local(monkeypatch, tmp_path):
    monkeypatch.delenv("VIDYA_LEDGER", raising=False)
    monkeypatch.delenv("VIDYA_SCRATCH", raising=False)
    monkeypatch.delenv("VIDYA_STATE_DIR", raising=False)
    wt = tmp_path / "some-worktree"
    got = ledger_home.default_ledger_path(wt)
    assert got == Path("/mnt/raid0/llm/state/vidya/ledger.jsonl")
    assert wt not in got.parents


def test_state_dir_env_scratch_and_explicit_overrides(monkeypatch, tmp_path):
    monkeypatch.delenv("VIDYA_LEDGER", raising=False)
    monkeypatch.setenv("VIDYA_STATE_DIR", str(tmp_path / "st"))
    assert ledger_home.default_ledger_path(tmp_path) == tmp_path / "st" / "ledger.jsonl"
    monkeypatch.setenv("VIDYA_SCRATCH", "1")
    assert ledger_home.default_ledger_path(tmp_path) == tmp_path / ".vidya" / "ledger.jsonl"
    monkeypatch.setenv("VIDYA_LEDGER", str(tmp_path / "x.jsonl"))
    assert ledger_home.default_ledger_path(tmp_path) == tmp_path / "x.jsonl"


def test_cli_from_a_worktree_resolves_to_canonical_and_scratch_flag_is_local(tmp_path):
    env = {**os.environ, "VIDYA_STATE_DIR": str(tmp_path / "state")}
    env.pop("VIDYA_LEDGER", None)
    env.pop("VIDYA_SCRATCH", None)
    # run from an unrelated cwd: resolution must not depend on cwd or repo-local .vidya
    out = subprocess.run([sys.executable, str(CLI), "--json", "sync", "--check",
                          "--index", str(_small_index(tmp_path / "idx.yaml"))],
                         cwd=tmp_path, env=env, capture_output=True, text=True)
    assert out.returncode == 1, out.stderr  # stale, and it names the canonical (tmp) ledger
    assert str(tmp_path / "state" / "ledger.jsonl") in out.stdout
    out = subprocess.run([sys.executable, str(CLI), "--scratch", "--json", "sync", "--check",
                          "--index", str(tmp_path / "idx.yaml")],
                         cwd=tmp_path, env=env, capture_output=True, text=True)
    assert str(REPO / ".vidya" / "ledger.jsonl") in out.stdout


def test_checkpoints_stay_with_repo_for_canonical_default(monkeypatch, tmp_path):
    monkeypatch.setenv("VIDYA_STATE_DIR", str(tmp_path))
    assert ledger_home.checkpoint_dir_for(tmp_path / "ledger.jsonl", REPO) == REPO / ".vidya" / "checkpoints"
    other = tmp_path / "elsewhere" / "l.jsonl"
    assert ledger_home.checkpoint_dir_for(other, REPO) == other.parent / "checkpoints"


# ---- concurrent append safety -------------------------------------------------------------

def _worker(path, wid, n):
    led = Ledger(path)  # each process has its own object and its own head cache
    for i in range(n):
        led.append(_frame(wid * 1000 + i))


def test_concurrent_appends_keep_the_hash_chain_intact(tmp_path):
    path = tmp_path / "ledger.jsonl"
    Ledger(path).append(_frame(-1))
    procs = [mp.get_context("fork").Process(target=_worker, args=(path, w, 25)) for w in range(4)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(60)
        assert p.exitcode == 0
    led = Ledger(path)
    assert len(led.read_all()) == 1 + 4 * 25
    assert led.verify() == []


def test_write_lock_is_reentrant_and_excludes_other_processes(tmp_path):
    path = tmp_path / "ledger.jsonl"
    led = Ledger(path)
    with led.write_lock():
        with Ledger(path).write_lock():  # nested, other object: must not self-deadlock
            led.append(_frame(1))
        probe = subprocess.run(
            [sys.executable, "-c",
             "import fcntl,sys;fd=open(sys.argv[1]+'.lock','a');\n"
             "try:\n fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);print('GOT')\n"
             "except BlockingIOError:\n print('BLOCKED')", str(path)],
            capture_output=True, text=True)
        assert probe.stdout.strip() == "BLOCKED"
    probe = subprocess.run(
        [sys.executable, "-c",
         "import fcntl,sys;fd=open(sys.argv[1]+'.lock','a');"
         "fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);print('GOT')", str(path)],
        capture_output=True, text=True)
    assert probe.stdout.strip() == "GOT"


# ---- sync: stale -> incremental, idempotent, append-only ------------------------------------

def test_sync_is_incremental_idempotent_and_preserves_existing_frames(tmp_path):
    led_path = tmp_path / "ledger.jsonl"
    seed = Ledger(led_path)
    seed.append(_frame(99))  # a measurement-like frame that a rebuild would have dropped
    before = led_path.read_bytes()
    idx = _small_index(tmp_path / "idx.yaml", 3)

    assert vsync.status(led_path, idx)["fresh"] is False
    rep = vsync.sync(led_path, idx, as_of=NOW)
    assert rep["action"] == "ingested" and rep["frames_emitted"] > 0
    assert led_path.read_bytes().startswith(before), "existing chain must be a byte-identical prefix"
    assert vsync.status(led_path, idx)["fresh"] is True
    size = led_path.stat().st_size
    assert vsync.sync(led_path, idx, as_of=NOW)["action"] == "skipped-fresh"
    assert led_path.stat().st_size == size

    _small_index(idx, 5)  # the index grew: stale again, only the delta is appended
    assert vsync.status(led_path, idx)["fresh"] is False
    rep2 = vsync.sync(led_path, idx, as_of=NOW)
    assert rep2["action"] == "ingested" and rep2["frames_emitted"] > 0
    assert Ledger(led_path).verify() == []
    # an older index revision (other branch) stays 'seen': no ping-pong
    _small_index(idx, 3)
    assert vsync.status(led_path, idx)["fresh"] is True


def test_cli_sync_check_exit_codes(tmp_path):
    idx = _small_index(tmp_path / "idx.yaml")
    led = tmp_path / "l.jsonl"
    run = lambda *a: subprocess.run([sys.executable, str(CLI), "--ledger", str(led), "sync", *a,
                                     "--index", str(idx)], capture_output=True, text=True)
    assert run("--check").returncode == 1
    assert run("--as-of", NOW).returncode == 0
    assert run("--check").returncode == 0


# ---- the post-commit/post-merge safety net --------------------------------------------------

def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


def _hook_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "scripts" / "vidya").mkdir(parents=True)
    (repo / "research").mkdir()
    # stub cli: proves the hook invoked `sync --quiet` in this repo, without ingesting anything
    (repo / "scripts" / "vidya" / "cli.py").write_text(
        "import sys,os\nopen(os.environ['VIDYA_STATE_DIR']+'/called','a').write(' '.join(sys.argv[1:])+'\\n')\n")
    hook = repo / "scripts" / "vidya" / "hook_sync.sh"
    hook.write_text((REPO / "scripts" / "vidya" / "hook_sync.sh").read_text())
    _git(repo, "init", "-q", "-b", "main")
    (repo / "research" / "intake_index.yaml").write_text("- id: intake-001\n")
    (repo / "other.txt").write_text("x\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    return repo


def _wait(path, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if path.exists():
            return True
        time.sleep(0.05)
    return False


def test_hook_ingests_only_when_main_commit_touches_the_index(tmp_path):
    repo = _hook_repo(tmp_path)
    state = tmp_path / "state"
    state.mkdir()
    env = {**os.environ, "VIDYA_STATE_DIR": str(state)}
    run = lambda ev: subprocess.run(["bash", "scripts/vidya/hook_sync.sh", ev], cwd=repo, env=env,
                                    capture_output=True, text=True)
    called = state / "called"

    # HEAD touched the index -> detached sync, hook returns 0 immediately
    assert run("post-commit").returncode == 0
    assert _wait(called) and called.read_text().strip() == "sync --quiet"
    called.unlink()

    # a commit that does not touch the index -> nothing
    (repo / "other.txt").write_text("y\n")
    _git(repo, "commit", "-qam", "unrelated")
    assert run("post-commit").returncode == 0
    time.sleep(0.5)
    assert not called.exists()

    # a lane branch (not main) -> nothing, even if the index changed
    _git(repo, "checkout", "-qb", "lane/x")
    (repo / "research" / "intake_index.yaml").write_text("- id: intake-001\n- id: intake-002\n")
    _git(repo, "commit", "-qam", "lane index")
    assert run("post-commit").returncode == 0
    time.sleep(0.5)
    assert not called.exists()


def test_hook_never_fails_a_git_operation_when_cli_is_missing(tmp_path):
    repo = _hook_repo(tmp_path)
    (repo / "scripts" / "vidya" / "cli.py").unlink()
    env = {**os.environ, "VIDYA_STATE_DIR": str(tmp_path / "s")}
    r = subprocess.run(["bash", "scripts/vidya/hook_sync.sh", "post-commit"], cwd=repo, env=env)
    assert r.returncode == 0


def test_installer_is_idempotent_and_block_runs_hook(tmp_path):
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "post-commit").write_text("#!/bin/sh\necho existing\nexit 0\n")
    inst = REPO / "scripts" / "vidya" / "install_sync_hook.sh"
    for _ in range(2):
        subprocess.run(["bash", str(inst), str(hooks)], check=True, capture_output=True)
    for ev in ("post-commit", "post-merge"):
        text = (hooks / ev).read_text()
        assert text.count(">>> vidya-sync hook >>>") == 1
        assert text.startswith("#!/bin/sh")
    assert "echo existing" in (hooks / "post-commit").read_text()
    assert os.access(hooks / "post-merge", os.X_OK)


# ---- default source = origin/main's index --------------------------------------------------

def _origin_setup(tmp_path):
    """bare origin + a clone whose worktree index is DIFFERENT from origin/main's."""
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    pub = tmp_path / "pub"
    (pub / "research").mkdir(parents=True)
    _small_index(pub / "research" / "intake_index.yaml", 3)
    _git(pub, "init", "-q", "-b", "main")
    _git(pub, "add", "-A")
    _git(pub, "commit", "-qm", "i")
    _git(pub, "remote", "add", "origin", str(origin))
    _git(pub, "push", "-q", "origin", "main")
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", "-q", str(origin), str(clone))
    return origin, pub, clone


def test_default_source_is_fetched_origin_main_not_the_stale_worktree(tmp_path):
    origin, pub, clone = _origin_setup(tmp_path)
    led = tmp_path / "l.jsonl"
    # origin/main advances to 5 entries; the clone's worktree still has 3
    _small_index(pub / "research" / "intake_index.yaml", 5)
    _git(pub, "commit", "-qam", "more")
    _git(pub, "push", "-q", "origin", "main")
    data, note = vsync.load_index(repo=clone)
    assert note == "origin/main"
    assert len(re.findall(r"^- id: intake-", data.decode(), re.M)) == 5
    wt, wnote = vsync.load_index(from_worktree=True, repo=clone)
    assert len(re.findall(r"^- id: intake-", wt.decode(), re.M)) == 3 and wnote.startswith("worktree:")
    # end to end through the CLI from the clone: marker keyed on the origin blob
    run = lambda *a: subprocess.run([sys.executable, str(CLI), "--ledger", str(led), *a],
                                    cwd=clone, capture_output=True, text=True)
    assert run("sync", "--check").returncode == 1


def test_fetch_failure_falls_back_to_last_fetched_origin_main_and_says_so(tmp_path):
    origin, pub, clone = _origin_setup(tmp_path)
    _git(clone, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    data, note = vsync.load_index(repo=clone)  # origin/main ref from the clone's initial fetch
    assert "fetch FAILED" in note and b"intake-" in data


def test_explicit_file_and_no_fetch_never_touch_git(tmp_path):
    idx = _small_index(tmp_path / "i.yaml", 2)
    data, note = vsync.load_index(idx, repo=tmp_path / "not-a-repo")
    assert note.startswith("file:") and data == idx.read_bytes()
