#!/usr/bin/env python3
"""Tests for scripts/coordination/serialized_push.py.

EVERY assertion in this file lives inside a module-level `test_*` function, so
`pytest --collect-only` counts it and a whole-repo run is honestly red when one
breaks. That is not decoration: a suite already shipped in this tree whose entry
points asserted only inside `main()`, which the reporter does not count — it looked
like coverage and provided none. There is deliberately no `main()` here.

Nothing is mocked. Every repository state the tool must refuse is CONSTRUCTED FOR
REAL in a throwaway repo under the pytest tmp dir: a real conflicted cherry-pick, a
real interrupted rebase, a real detached HEAD, a real index carrying stage-1/2/3
entries. The push paths run against a real `git init --bare` remote on local disk,
so `--push` is exercised end to end without any network and without touching origin.

Both directions are covered throughout: the guard refuses what it must refuse AND
lets the compliant path through. A guard that also blocks correct usage gets disabled
by the first person it inconveniences, so "clean repo pushes and exits 0" is a
first-class test here, not an afterthought.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.coordination.serialized_push import (  # noqa: E402
    EXIT_LOCKED,
    EXIT_OK,
    EXIT_PREFLIGHT,
    EXIT_PUSH_FAILED,
    LockCorruptError,
    LockHeldError,
    NotHolderError,
    PreflightError,
    SerializedPushError,
    acquire,
    build_manifest,
    describe_holder,
    force_release,
    lock_path,
    preflight,
    read_lock,
    release,
    render_manifest,
    repo_key,
    subject_prefix,
    validate_lock_name,
)

SCRIPT = REPO_ROOT / "scripts" / "coordination" / "serialized_push.py"


# ---------------------------------------------------------------------------
# fixtures / helpers  (leading underscore: not collected as tests)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _hermetic_git_env(monkeypatch):
    """No global/system git config, and ONE committer identity for every commit.

    The single identity is not a shortcut — it reproduces the condition that makes
    this tool necessary: on this host every session commits as the same person, so
    `git log --format=%an` carries no provenance.
    """
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", os.devnull)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "agentbot")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "bot@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "agentbot")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "bot@example.invalid")
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    monkeypatch.delenv("SERIALIZED_PUSH_LOCK_DIR", raising=False)


def _git(cwd, *args, check=True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise AssertionError(f"fixture git {args} failed: {proc.stderr}")
    return proc


def _write_commit(work: Path, rel: str, content: str, message: str) -> None:
    target = Path(work) / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(work, "add", rel)
    _git(work, "commit", "-q", "-m", message)


def _plain_repo(tmp_path: Path, name: str = "plain") -> Path:
    """A working tree with one commit and NO remote."""
    work = tmp_path / name
    work.mkdir()
    _git(work, "init", "-q", "-b", "main", ".")
    _write_commit(work, "f.txt", "a\n", "base")
    return work


def _clone_with_remote(tmp_path: Path, name: str = "shared") -> tuple[Path, Path]:
    """(work, bare) — a working tree whose `main` tracks a local bare remote."""
    bare = tmp_path / f"{name}-origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    work = tmp_path / name
    work.mkdir()
    _git(work, "init", "-q", "-b", "main", ".")
    _write_commit(work, "f.txt", "a\n", "base")
    _git(work, "remote", "add", "origin", str(bare))
    _git(work, "push", "-q", "-u", "origin", "main")
    return work, bare


def _bare_ref(bare: Path) -> str:
    return _git(bare, "rev-parse", "refs/heads/main").stdout.strip()


def _head(work: Path) -> str:
    return _git(work, "rev-parse", "HEAD").stdout.strip()


def _cli(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *argv],
                          capture_output=True, text=True)


def _dead_pid() -> int:
    """A PID that is definitely not running, found without spawning or killing
    anything (this host is shared; process management is out of bounds here)."""
    for pid in range(4_000_000, 4_000_400):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return pid
        except OSError:
            continue
    pytest.skip("could not find an unused PID on this host")


def _plant_lock(lock_dir: Path, key: str, agent: str, pid: int, **extra) -> Path:
    lock_dir.mkdir(parents=True, exist_ok=True)
    path = lock_path(lock_dir, key)
    rec = {"agent": agent, "pid": pid, "host": os.uname().nodename,
           "ts": "2026-08-12T00:00:00+00:00", "repo_key": key, "repo_path": "/planted"}
    rec.update(extra)
    path.write_text(json.dumps(rec, sort_keys=True) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# 1. LOCK: acquired when free, refused when held
# ---------------------------------------------------------------------------


def test_lock_acquired_when_free(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    rec = acquire(lock_dir, key, "mainA", str(work))
    assert rec["agent"] == "mainA"
    assert rec["pid"] == os.getpid()
    assert rec["repo_key"] == key
    on_disk = read_lock(lock_path(lock_dir, key))
    assert on_disk == rec, "the lock record on disk must be exactly what acquire() returned"


def test_lock_record_carries_holder_pid_timestamp_and_repo(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    rec = acquire(lock_dir, repo_key(work), "mainA", str(work))
    for field in ("agent", "pid", "ts", "repo_path", "repo_key", "host"):
        assert field in rec, f"lock record must record {field}"
    assert rec["ts"].startswith("20") and "T" in rec["ts"], "timestamp must be ISO-8601"
    assert rec["repo_path"] == str(work)


def test_second_acquirer_is_refused_and_the_holder_is_named(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    acquire(lock_dir, key, "mainA", str(work))
    with pytest.raises(LockHeldError) as exc:
        acquire(lock_dir, key, "mainB", str(work))
    assert exc.value.condition == "lock-held"
    assert exc.value.holder["agent"] == "mainA"
    assert "mainA" in str(exc.value), "the refusal must NAME the holder"
    assert "2026" in str(exc.value) or "since" in str(exc.value), \
        "the refusal must say since when"


def test_refused_acquirer_does_not_steal_or_modify_the_lock(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    acquire(lock_dir, key, "mainA", str(work))
    before = lock_path(lock_dir, key).read_bytes()
    with pytest.raises(LockHeldError):
        acquire(lock_dir, key, "mainB", str(work))
    assert lock_path(lock_dir, key).read_bytes() == before, \
        "a refused acquirer must leave the holder's lock byte-identical"


def test_same_agent_same_pid_is_idempotent_not_a_collision(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    first = acquire(lock_dir, key, "mainA", str(work))
    again = acquire(lock_dir, key, "mainA", str(work))
    assert again["agent"] == "mainA" and again["ts"] == first["ts"]


def test_same_agent_from_a_different_live_process_is_refused(tmp_path):
    """Two live processes sharing one roster id are exactly the concurrency this stops."""
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    _plant_lock(lock_dir, key, "mainA", os.getppid())  # a different, live PID
    with pytest.raises(LockHeldError) as exc:
        acquire(lock_dir, key, "mainA", str(work))
    assert exc.value.condition == "lock-held-same-agent"


def test_a_corrupt_lock_is_treated_as_held_not_as_free(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    lock_dir.mkdir(parents=True)
    lock_path(lock_dir, key).write_text("{ this is not json", encoding="utf-8")
    with pytest.raises(LockCorruptError) as exc:
        acquire(lock_dir, key, "mainB", str(work))
    assert exc.value.condition == "lock-corrupt"
    assert lock_path(lock_dir, key).exists(), "a corrupt lock must not be deleted"


# ---------------------------------------------------------------------------
# 2. RELEASE: holder yes, non-holder no
# ---------------------------------------------------------------------------


def test_release_by_the_holder_works(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    acquire(lock_dir, key, "mainA", str(work))
    assert release(lock_dir, key, "mainA") is True
    assert not lock_path(lock_dir, key).exists()
    assert read_lock(lock_path(lock_dir, key)) is None


def test_release_by_a_non_holder_is_refused(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    acquire(lock_dir, key, "mainA", str(work))
    with pytest.raises(NotHolderError) as exc:
        release(lock_dir, key, "mainB")
    assert exc.value.condition == "not-holder"
    assert "mainA" in str(exc.value)
    assert lock_path(lock_dir, key).exists(), "a refused release must leave the lock in place"


def test_release_refuses_a_live_sibling_process_of_the_same_agent(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    _plant_lock(lock_dir, key, "mainA", os.getppid())
    with pytest.raises(NotHolderError) as exc:
        release(lock_dir, key, "mainA")
    assert exc.value.condition == "not-holder-live-sibling"
    assert lock_path(lock_dir, key).exists()


def test_release_of_your_own_dead_residue_is_allowed(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    _plant_lock(lock_dir, key, "mainA", _dead_pid())
    assert release(lock_dir, key, "mainA") is True
    assert not lock_path(lock_dir, key).exists()


def test_release_when_nothing_is_held_reports_false(tmp_path):
    work = _plain_repo(tmp_path)
    assert release(tmp_path / "locks", repo_key(work), "mainA") is False


# ---------------------------------------------------------------------------
# 3. STALE PID: evidence, not proof. Reported, never auto-expired.
# ---------------------------------------------------------------------------


def test_stale_pid_is_reported_as_possible_residue(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    _plant_lock(lock_dir, key, "mainA", _dead_pid())
    with pytest.raises(LockHeldError) as exc:
        acquire(lock_dir, key, "mainB", str(work))
    message = str(exc.value)
    assert "is not running" in message
    assert "residue" in message
    assert "--force-release mainA" in message, \
        "the refusal must tell the caller the deliberate way out, naming the holder"


def test_stale_lock_is_not_auto_expired(tmp_path):
    """Auto-expiry would destroy the single-writer property O_EXCL buys."""
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    planted = _plant_lock(lock_dir, key, "mainA", _dead_pid())
    before = planted.read_bytes()
    for _ in range(3):
        with pytest.raises(LockHeldError):
            acquire(lock_dir, key, "mainB", str(work))
    assert planted.exists(), "a stale lock must survive a refused acquire"
    assert planted.read_bytes() == before, "a stale lock must not be rewritten"


def test_stale_lock_of_your_own_agent_is_reclaimed(tmp_path):
    """Your own residue must not lock you out of the work you are holding."""
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    _plant_lock(lock_dir, key, "mainA", _dead_pid())
    rec = acquire(lock_dir, key, "mainA", str(work))
    assert rec["pid"] == os.getpid()


def test_describe_holder_states_the_liveness_verdict(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    _plant_lock(lock_dir, key, "mainA", _dead_pid())
    text = describe_holder(read_lock(lock_path(lock_dir, key)))
    assert "mainA" in text and "gone" in text and "not auto-expired" in text.lower()


def test_a_lock_held_via_acquire_is_not_mistaken_for_residue(tmp_path):
    """`--acquire` exits immediately by design, so its PID is dead within a second.
    Reported naively, the most deliberate hold in the system reads as the stalest
    residue and invites exactly the displacement it was taken to prevent."""
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    _plant_lock(lock_dir, key, "mainA", _dead_pid(), mode="hold")
    text = describe_holder(read_lock(lock_path(lock_dir, key)))
    assert "EXPECTED" in text
    assert "NOT evidence of residue" in text
    assert "--acquire" in text


def test_a_push_mode_lock_with_a_dead_pid_is_still_called_residue(tmp_path):
    """The other direction of the same distinction: the 'hold' carve-out must not
    swallow the case the residue report exists for."""
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    _plant_lock(lock_dir, key, "mainA", _dead_pid(), mode="push")
    text = describe_holder(read_lock(lock_path(lock_dir, key)))
    assert "residue" in text and "NOT evidence of residue" not in text


def test_lock_records_its_mode_and_acquire_marks_it_held(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    lock_dir = tmp_path / "locks"
    assert acquire(lock_dir, repo_key(work), "mainA", str(work))["mode"] == "push"
    release(lock_dir, repo_key(work), "mainA")
    assert _cli("--agent", "mainA", "--repo", str(work), "--acquire",
                "--lock-dir", str(lock_dir)).returncode == EXIT_OK
    assert read_lock(lock_path(lock_dir, repo_key(work)))["mode"] == "hold"


def test_holder_description_reports_the_lock_age(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    _plant_lock(lock_dir, key, "mainA", os.getpid(), ts="2026-08-11T00:00:00+00:00")
    assert "h ago)" in describe_holder(read_lock(lock_path(lock_dir, key)))


def test_liveness_is_undecidable_from_another_host_and_says_so(tmp_path):
    """A PID from another host (or PID namespace) must not be judged dead here."""
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    _plant_lock(lock_dir, key, "mainA", _dead_pid(), host="some-other-host")
    text = describe_holder(read_lock(lock_path(lock_dir, key)))
    assert "not checkable from here" in text
    with pytest.raises(LockHeldError):
        acquire(lock_dir, key, "mainB", str(work))


# ---------------------------------------------------------------------------
# 4. FORCE-RELEASE: deliberate, attributable, journaled
# ---------------------------------------------------------------------------


def test_force_release_requires_naming_the_actual_holder(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    _plant_lock(lock_dir, key, "mainA", _dead_pid())
    with pytest.raises(NotHolderError) as exc:
        force_release(lock_dir, key, "mainB", "mainC")   # named the wrong holder
    assert exc.value.condition == "holder-mismatch"
    assert lock_path(lock_dir, key).exists(), "a mis-named displacement must not break the lock"


def test_force_release_with_the_right_holder_displaces_and_journals(tmp_path):
    work = _plain_repo(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    _plant_lock(lock_dir, key, "mainA", _dead_pid())
    rec = force_release(lock_dir, key, "mainB", "mainA")
    assert rec["agent"] == "mainA"
    assert not lock_path(lock_dir, key).exists()
    journal = [json.loads(ln) for ln in
               (lock_dir / "displacements.jsonl").read_text(encoding="utf-8").splitlines()]
    assert journal[-1]["by_agent"] == "mainB"
    assert journal[-1]["displaced"]["agent"] == "mainA"


def test_force_release_on_a_free_lock_is_refused(tmp_path):
    work = _plain_repo(tmp_path)
    with pytest.raises(NotHolderError) as exc:
        force_release(tmp_path / "locks", repo_key(work), "mainB", "mainA")
    assert exc.value.condition == "no-lock"


# ---------------------------------------------------------------------------
# 5. REPO IDENTITY: one repository, one lock, however you reach it
# ---------------------------------------------------------------------------


def test_repo_key_is_identical_through_a_symlinked_path(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    link = tmp_path / "via-symlink"
    link.symlink_to(work)
    assert repo_key(work) == repo_key(link)


def test_lock_filename_carries_no_path_basename(tmp_path):
    """The basename differs per view ('workspace' vs 'epyc-root'); if it leaked into
    the lock filename the same repo would get two locks and serialize nothing."""
    work, _ = _clone_with_remote(tmp_path, "some-distinctive-name")
    name = lock_path(tmp_path / "locks", repo_key(work)).name
    assert "some-distinctive-name" not in name
    assert name.startswith("push-") and name.endswith(".json")


def test_two_different_repos_get_two_different_locks(tmp_path):
    a = _plain_repo(tmp_path, "a")
    b = _plain_repo(tmp_path, "b")
    assert repo_key(a) != repo_key(b)


@pytest.mark.skipif(not (Path("/workspace/.git").exists()
                         and Path("/mnt/raid0/llm/epyc-root/.git").exists()),
                    reason="the two real views of epyc-root are not both present")
def test_real_bind_mounted_views_of_epyc_root_share_one_lock_key():
    """The finding this design turns on, asserted against the real host.

    /workspace and /mnt/raid0/llm/epyc-root are ONE repository reached two ways, but
    they are a bind mount rather than a symlink — so `realpath` does NOT collapse
    them and a path-keyed lock would hand out two locks for one repo. Read-only.
    """
    a, b = Path("/workspace"), Path("/mnt/raid0/llm/epyc-root")
    assert os.path.realpath(a / ".git") != os.path.realpath(b / ".git"), \
        "if realpath ever collapses these, this test's premise changed — re-read the design"
    assert repo_key(a) == repo_key(b), \
        "the two views of epyc-root must contend for the SAME push lock"


# ---------------------------------------------------------------------------
# 6. FAIL CLOSED, BY NAME — every state constructed for real
# ---------------------------------------------------------------------------


def test_preflight_refuses_a_path_that_is_not_a_git_repo(tmp_path):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    with pytest.raises(PreflightError) as exc:
        preflight(outside)
    assert exc.value.condition == "not-a-git-repo"


def test_preflight_refuses_no_upstream_and_names_it(tmp_path):
    work = _plain_repo(tmp_path)
    with pytest.raises(PreflightError) as exc:
        preflight(work)
    assert exc.value.condition == "no-upstream"
    assert "no-upstream" in str(exc.value) and "main" in str(exc.value)


def test_preflight_refuses_detached_head_and_names_it(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    _git(work, "checkout", "-q", "--detach", "HEAD")
    assert _git(work, "symbolic-ref", "--quiet", "HEAD", check=False).returncode != 0, \
        "fixture must really be detached"
    with pytest.raises(PreflightError) as exc:
        preflight(work)
    assert exc.value.condition == "detached-head"
    assert "detached" in str(exc.value)


def test_preflight_refuses_mid_cherry_pick_and_names_the_cherry_pick(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    _git(work, "checkout", "-q", "-b", "side")
    _write_commit(work, "f.txt", "side\n", "side change")
    _git(work, "checkout", "-q", "main")
    _write_commit(work, "f.txt", "mainline\n", "main change")
    _git(work, "cherry-pick", "side", check=False)
    assert (work / ".git" / "CHERRY_PICK_HEAD").exists(), \
        "fixture must really be mid-cherry-pick"
    with pytest.raises(PreflightError) as exc:
        preflight(work)
    assert exc.value.condition == "mid-cherry-pick", \
        "a conflicted cherry-pick also leaves unmerged paths; the CAUSE must be named"
    assert "cherry-pick" in str(exc.value)


def test_preflight_refuses_mid_merge_and_names_the_merge(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    _git(work, "checkout", "-q", "-b", "side")
    _write_commit(work, "f.txt", "side\n", "side change")
    _git(work, "checkout", "-q", "main")
    _write_commit(work, "f.txt", "mainline\n", "main change")
    _git(work, "merge", "side", check=False)
    assert (work / ".git" / "MERGE_HEAD").exists(), "fixture must really be mid-merge"
    with pytest.raises(PreflightError) as exc:
        preflight(work)
    assert exc.value.condition == "mid-merge"


def test_preflight_refuses_mid_rebase_naming_the_rebase_not_the_detached_head(tmp_path):
    """A rebase detaches HEAD as a matter of course. Naming 'detached-head' here
    would report a symptom and send the reader to the wrong fix."""
    work, _ = _clone_with_remote(tmp_path)
    _git(work, "checkout", "-q", "-b", "side")
    _write_commit(work, "f.txt", "side\n", "side change")
    _git(work, "checkout", "-q", "main")
    _write_commit(work, "f.txt", "mainline\n", "main change")
    env = dict(os.environ, GIT_EDITOR="true")
    subprocess.run(["git", "-C", str(work), "rebase", "side"],
                   capture_output=True, text=True, env=env)
    assert (work / ".git" / "rebase-merge").exists(), "fixture must really be mid-rebase"
    assert _git(work, "symbolic-ref", "--quiet", "HEAD", check=False).returncode != 0, \
        "and HEAD really is detached, which is why ordering matters"
    with pytest.raises(PreflightError) as exc:
        preflight(work)
    assert exc.value.condition == "mid-rebase"


def test_preflight_refuses_unmerged_paths_with_no_operation_in_progress(tmp_path):
    """Stage-1/2/3 index entries with no MERGE_HEAD — a real index state (a
    conflicted `git stash pop` or `git checkout -m` leaves exactly this)."""
    work, _ = _clone_with_remote(tmp_path)
    blobs = []
    for text in ("one\n", "two\n", "three\n"):
        proc = subprocess.run(["git", "-C", str(work), "hash-object", "-w", "--stdin"],
                              input=text, capture_output=True, text=True, check=True)
        blobs.append(proc.stdout.strip())
    index_info = "".join(
        f"100644 {sha} {stage}\tconflict.txt\n" for stage, sha in enumerate(blobs, start=1))
    subprocess.run(["git", "-C", str(work), "update-index", "--index-info"],
                   input=index_info, capture_output=True, text=True, check=True)
    assert _git(work, "ls-files", "--unmerged").stdout.strip(), \
        "fixture must really have unmerged paths"
    for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge"):
        assert not (work / ".git" / marker).exists(), \
            "fixture must isolate unmerged paths from any in-progress operation"
    with pytest.raises(PreflightError) as exc:
        preflight(work)
    assert exc.value.condition == "unmerged-paths"
    assert "conflict.txt" in str(exc.value)


def test_preflight_refuses_a_bare_repository(tmp_path):
    _, bare = _clone_with_remote(tmp_path)
    with pytest.raises(PreflightError) as exc:
        preflight(bare)
    assert exc.value.condition == "bare-repository"


def test_preflight_refuses_an_unfetched_upstream_ref(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    _git(work, "update-ref", "-d", "refs/remotes/origin/main")
    with pytest.raises(PreflightError) as exc:
        preflight(work)
    assert exc.value.condition == "upstream-ref-not-fetched"
    assert "--fetch" in str(exc.value)


def test_preflight_passes_on_a_clean_tracking_branch(tmp_path):
    """THE COMPLIANT PATH at the unit level: the guard must not refuse correct usage."""
    work, _ = _clone_with_remote(tmp_path)
    pf = preflight(work)
    assert pf["branch"] == "main"
    assert pf["remote"] == "origin"
    assert pf["remote_branch"] == "main"
    assert pf["upstream_ref"] == "refs/remotes/origin/main"
    assert pf["have_upstream"] is True


# ---------------------------------------------------------------------------
# 7. THE PUBLISH MANIFEST
# ---------------------------------------------------------------------------


def test_manifest_counts_commits_and_changed_files(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    _write_commit(work, "scripts/b.py", "b\n", "fix(bus): repair b")
    _write_commit(work, "z.txt", "z\n", "no prefix at all")
    man = build_manifest(work, preflight(work))
    assert man["ahead"] == 3
    assert man["behind"] == 0
    assert man["changed_file_count"] == 3
    assert len(man["commits"]) == 3


def test_manifest_groups_by_top_level_path(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    _write_commit(work, "docs/b.md", "b\n", "docs: add b")
    _write_commit(work, "scripts/c.py", "c\n", "feat: add c")
    man = build_manifest(work, preflight(work))
    assert man["by_top_level_path"]["docs"] == 2
    assert man["by_top_level_path"]["scripts"] == 1


def test_manifest_groups_by_subject_prefix(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    _write_commit(work, "scripts/b.py", "b\n", "fix(bus): repair b")
    _write_commit(work, "z.txt", "z\n", "no prefix at all")
    man = build_manifest(work, preflight(work))
    assert man["by_subject_prefix"]["docs"] == 1
    assert man["by_subject_prefix"]["fix"] == 1
    assert man["by_subject_prefix"]["(no prefix)"] == 1


def test_subject_prefix_parsing():
    assert subject_prefix("docs: x") == "docs"
    assert subject_prefix("fix(bus): x") == "fix"
    assert subject_prefix("feat!: x") == "feat"
    assert subject_prefix("Freeze production consolidated v9") == "(no prefix)"


def test_manifest_render_says_authorship_is_not_recoverable(tmp_path):
    """`git log --format=%an` is a constant on this host; the manifest must say so
    instead of letting a reader read the author column as provenance."""
    work, _ = _clone_with_remote(tmp_path)
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    _write_commit(work, "scripts/b.py", "b\n", "fix: b")
    pf = preflight(work)
    text = render_manifest(pf, build_manifest(work, pf))
    assert "AUTHORSHIP IS NOT RECOVERABLE FROM GIT ON THIS HOST" in text
    assert "%an" in text


def test_manifest_render_warns_that_a_push_publishes_the_whole_branch(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    pf = preflight(work)
    text = render_manifest(pf, build_manifest(work, pf))
    assert "WHOLE branch" in text
    assert "never reviewed and cannot vouch for" in text


def test_manifest_reports_being_behind_the_upstream(tmp_path):
    work, bare = _clone_with_remote(tmp_path)
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(bare), str(other))
    _write_commit(other, "remote-side.txt", "r\n", "remote: landed elsewhere")
    _git(other, "push", "-q", "origin", "main")
    _write_commit(work, "local.txt", "l\n", "local: mine")
    _git(work, "fetch", "-q", "origin", "main:refs/remotes/origin/main")
    man = build_manifest(work, preflight(work))
    assert man["behind"] == 1 and man["ahead"] == 1
    assert "non-fast-forward" in render_manifest(preflight(work), man)


def test_manifest_on_an_up_to_date_branch_reports_nothing_to_publish(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    pf = preflight(work)
    man = build_manifest(work, pf)
    assert man["ahead"] == 0 and man["changed_file_count"] == 0
    assert "Nothing to publish" in render_manifest(pf, man)


# ---------------------------------------------------------------------------
# 8. CLI: dry-run is the default, --push is the only thing that publishes
# ---------------------------------------------------------------------------


def test_dry_run_is_the_default_and_does_not_push(tmp_path):
    work, bare = _clone_with_remote(tmp_path)
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    before = _bare_ref(bare)
    res = _cli("--agent", "mainA", "--repo", str(work), "--lock-dir", str(tmp_path / "locks"))
    assert res.returncode == EXIT_OK, res.stderr
    assert "PUBLISH MANIFEST" in res.stdout
    assert "DRY RUN" in res.stdout
    assert _bare_ref(bare) == before, "the remote ref must be untouched by a dry run"
    assert before != _head(work), "and the dry run really did have something to push"


def test_explicit_dry_run_flag_also_does_not_push(tmp_path):
    work, bare = _clone_with_remote(tmp_path)
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    before = _bare_ref(bare)
    res = _cli("--agent", "mainA", "--repo", str(work), "--dry-run",
               "--lock-dir", str(tmp_path / "locks"))
    assert res.returncode == EXIT_OK, res.stderr
    assert _bare_ref(bare) == before


def test_dry_run_leaves_no_lock_behind(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    lock_dir = tmp_path / "locks"
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    _cli("--agent", "mainA", "--repo", str(work), "--lock-dir", str(lock_dir))
    assert not lock_path(lock_dir, repo_key(work)).exists()


def test_dry_run_reports_that_another_session_holds_the_lock(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    lock_dir = tmp_path / "locks"
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    _plant_lock(lock_dir, repo_key(work), "mainB", os.getpid())
    res = _cli("--agent", "mainA", "--repo", str(work), "--lock-dir", str(lock_dir))
    assert res.returncode == EXIT_OK
    assert "mainB" in res.stderr and "racing their push" in res.stderr


def test_push_actually_publishes_and_exits_zero(tmp_path):
    """THE COMPLIANT PATH, end to end: clean repo, upstream configured, no
    contention -> it pushes and exits 0."""
    work, bare = _clone_with_remote(tmp_path)
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    lock_dir = tmp_path / "locks"
    before = _bare_ref(bare)
    res = _cli("--agent", "mainA", "--repo", str(work), "--push", "--lock-dir", str(lock_dir))
    assert res.returncode == EXIT_OK, res.stdout + res.stderr
    assert "REFUSING" not in res.stderr
    assert _bare_ref(bare) == _head(work), "the remote must now point at our HEAD"
    assert _bare_ref(bare) != before
    assert "PUBLISH MANIFEST" in res.stdout, "a push must still print what it published"


def test_push_releases_the_lock_afterwards(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    lock_dir = tmp_path / "locks"
    assert _cli("--agent", "mainA", "--repo", str(work), "--push",
                "--lock-dir", str(lock_dir)).returncode == EXIT_OK
    assert not lock_path(lock_dir, repo_key(work)).exists(), \
        "a completed push must not leave the fleet locked out"


def test_push_is_refused_while_another_agent_holds_the_lock(tmp_path):
    """The race, closed: a concurrent pusher is refused and publishes nothing."""
    work, bare = _clone_with_remote(tmp_path)
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    lock_dir = tmp_path / "locks"
    _plant_lock(lock_dir, repo_key(work), "mainB", os.getpid())   # a live holder
    before = _bare_ref(bare)
    res = _cli("--agent", "mainA", "--repo", str(work), "--push", "--lock-dir", str(lock_dir))
    assert res.returncode == EXIT_LOCKED
    assert "mainB" in res.stderr
    assert _bare_ref(bare) == before, "a refused push must publish NOTHING"


def test_push_with_nothing_to_publish_is_a_no_op_zero(tmp_path):
    work, bare = _clone_with_remote(tmp_path)
    before = _bare_ref(bare)
    res = _cli("--agent", "mainA", "--repo", str(work), "--push",
               "--lock-dir", str(tmp_path / "locks"))
    assert res.returncode == EXIT_OK
    assert "Nothing to push" in res.stdout
    assert _bare_ref(bare) == before


def test_non_fast_forward_push_fails_loudly_and_frees_the_lock(tmp_path):
    work, bare = _clone_with_remote(tmp_path)
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(bare), str(other))
    _write_commit(other, "remote-side.txt", "r\n", "remote: landed elsewhere")
    _git(other, "push", "-q", "origin", "main")
    _write_commit(work, "local.txt", "l\n", "local: mine")
    lock_dir = tmp_path / "locks"
    remote_before = _bare_ref(bare)
    res = _cli("--agent", "mainA", "--repo", str(work), "--push", "--fetch",
               "--lock-dir", str(lock_dir))
    assert res.returncode == EXIT_PUSH_FAILED, res.stdout + res.stderr
    assert "push-rejected" in res.stderr
    assert _bare_ref(bare) == remote_before, "a rejected push must not have changed the remote"
    assert not lock_path(lock_dir, repo_key(work)).exists(), \
        "a FAILED push must still free the lock; a wedged lock blocks the whole fleet"


def test_cli_fail_closed_conditions_exit_three_and_name_the_cause(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    _git(work, "checkout", "-q", "--detach", "HEAD")
    res = _cli("--agent", "mainA", "--repo", str(work), "--push",
               "--lock-dir", str(tmp_path / "locks"))
    assert res.returncode == EXIT_PREFLIGHT
    assert "detached-head" in res.stderr
    assert "REFUSING" in res.stderr


def test_cli_acquire_hold_then_push_then_release(tmp_path):
    """--acquire holds the lock across processes so a review window is protected,
    and the subsequent --push (a different PID, same agent) is not locked out."""
    work, bare = _clone_with_remote(tmp_path)
    _write_commit(work, "docs/a.md", "a\n", "docs: add a")
    lock_dir = tmp_path / "locks"
    common = ["--repo", str(work), "--lock-dir", str(lock_dir)]
    assert _cli("--agent", "mainA", *common, "--acquire").returncode == EXIT_OK
    assert lock_path(lock_dir, repo_key(work)).exists()
    blocked = _cli("--agent", "mainB", *common, "--push")
    assert blocked.returncode == EXIT_LOCKED and "mainA" in blocked.stderr
    assert _cli("--agent", "mainA", *common, "--push").returncode == EXIT_OK
    assert _bare_ref(bare) == _head(work)


def test_cli_status_reports_free_and_held(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    lock_dir = tmp_path / "locks"
    common = ["--repo", str(work), "--lock-dir", str(lock_dir)]
    free = _cli("--agent", "mainA", *common, "--status")
    assert free.returncode == EXIT_OK and "FREE" in free.stdout
    _plant_lock(lock_dir, repo_key(work), "mainB", os.getpid())
    held = _cli("--agent", "mainA", *common, "--status")
    assert held.returncode == EXIT_OK and "HELD" in held.stdout and "mainB" in held.stdout


def test_cli_release_by_non_holder_exits_locked(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    lock_dir = tmp_path / "locks"
    _plant_lock(lock_dir, repo_key(work), "mainB", os.getpid())
    res = _cli("--agent", "mainA", "--repo", str(work), "--release",
               "--lock-dir", str(lock_dir))
    assert res.returncode == EXIT_LOCKED
    assert "mainB" in res.stderr
    assert lock_path(lock_dir, repo_key(work)).exists()


def test_cli_force_release_requires_the_holder_name(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    lock_dir = tmp_path / "locks"
    _plant_lock(lock_dir, repo_key(work), "mainB", _dead_pid())
    common = ["--repo", str(work), "--lock-dir", str(lock_dir)]
    wrong = _cli("--agent", "mainA", *common, "--force-release", "mainZ")
    assert wrong.returncode == EXIT_LOCKED and "holder-mismatch" in wrong.stderr
    right = _cli("--agent", "mainA", *common, "--force-release", "mainB")
    assert right.returncode == EXIT_OK and "FORCE-RELEASED" in right.stdout
    assert not lock_path(lock_dir, repo_key(work)).exists()


def test_lock_dir_env_var_is_honoured(tmp_path, monkeypatch):
    """The fleet gets ONE shared lock dir without every caller passing --lock-dir."""
    work, _ = _clone_with_remote(tmp_path)
    lock_dir = tmp_path / "env-locks"
    monkeypatch.setenv("SERIALIZED_PUSH_LOCK_DIR", str(lock_dir))
    assert _cli("--agent", "mainA", "--repo", str(work), "--acquire").returncode == EXIT_OK
    assert lock_path(lock_dir, repo_key(work)).exists()


def test_cli_refuses_push_and_dry_run_together(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    res = _cli("--agent", "mainA", "--repo", str(work), "--push", "--dry-run")
    assert res.returncode != EXIT_OK
    assert "not allowed with" in res.stderr


# ---------------------------------------------------------------------------
# Named leases (--lock-name) — the wrap-up lease, phase 3 task C3
# ---------------------------------------------------------------------------


def test_named_leases_are_independent_of_the_push_lock(tmp_path):
    """Holding the wrap-up lease must not block a push, and vice versa.

    They serialize DIFFERENT things: the wrap-up lease covers the shared-surface
    edits and the promotion merge (minutes), the push lock covers one push
    (seconds). Collapsing them into one lock would make every wrap-up a fleet-wide
    push freeze, which is exactly the 15-minute commit freeze this program exists
    to remove.
    """
    work, _ = _clone_with_remote(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    acquire(lock_dir, key, "mainA", str(work), mode="hold", name="wrapup")
    # A different agent may still take the push lock.
    acquire(lock_dir, key, "mainB", str(work), mode="hold", name="push")
    assert lock_path(lock_dir, key, "wrapup").exists()
    assert lock_path(lock_dir, key, "push").exists()
    assert lock_path(lock_dir, key, "wrapup") != lock_path(lock_dir, key, "push")


def test_named_lease_refuses_a_second_holder(tmp_path):
    """The whole point: two lane worktrees cannot hold the wrap-up lease at once."""
    work, _ = _clone_with_remote(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    acquire(lock_dir, key, "mainA", str(work), mode="hold", name="wrapup")
    with pytest.raises(LockHeldError) as exc:
        acquire(lock_dir, key, "mainB", str(work), mode="hold", name="wrapup")
    assert "wrapup lock" in str(exc.value)


def test_two_worktrees_of_one_clone_contend_for_the_same_lease(tmp_path):
    """Lane worktrees are DIFFERENT PATHS to ONE repository.

    A lock keyed on the path would give each lane its own lease and serialize
    nothing. The key is the git common dir's device+inode, so both worktrees
    resolve the same lock file.
    """
    work, _ = _clone_with_remote(tmp_path)
    lane = tmp_path / "lane-a"
    _git(work, "worktree", "add", "-b", "lane/mainA", str(lane))
    assert repo_key(lane) == repo_key(work)
    lock_dir = tmp_path / "locks"
    acquire(lock_dir, repo_key(work), "mainA", str(work), mode="hold", name="wrapup")
    with pytest.raises(LockHeldError):
        acquire(lock_dir, repo_key(lane), "mainB", str(lane), mode="hold", name="wrapup")


def test_release_only_drops_the_named_lease(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    lock_dir = tmp_path / "locks"
    key = repo_key(work)
    acquire(lock_dir, key, "mainA", str(work), mode="hold", name="wrapup")
    acquire(lock_dir, key, "mainA", str(work), mode="hold", name="push")
    assert release(lock_dir, key, "mainA", name="wrapup") is True
    assert not lock_path(lock_dir, key, "wrapup").exists()
    assert lock_path(lock_dir, key, "push").exists()


def test_cli_named_lease_roundtrip_and_status(tmp_path):
    work, _ = _clone_with_remote(tmp_path)
    lock_dir = tmp_path / "locks"
    common = ["--repo", str(work), "--lock-dir", str(lock_dir), "--lock-name", "wrapup"]
    got = _cli("--agent", "mainA", *common, "--acquire")
    assert got.returncode == EXIT_OK and "acquired wrapup lock" in got.stdout
    st = _cli("--agent", "mainB", *common, "--status")
    assert "wrapup lock: HELD" in st.stdout
    # The push lock over the same repo is untouched and reads FREE.
    st2 = _cli("--agent", "mainB", "--repo", str(work), "--lock-dir", str(lock_dir), "--status")
    assert "push lock: FREE" in st2.stdout
    rel = _cli("--agent", "mainA", *common, "--release")
    assert rel.returncode == EXIT_OK and "released wrapup lock" in rel.stdout


def test_cli_refuses_to_push_under_a_non_push_lock_name(tmp_path):
    """A lock nobody else checks is worse than no lock: it reports success."""
    work, _ = _clone_with_remote(tmp_path)
    res = _cli("--agent", "mainA", "--repo", str(work), "--lock-name", "wrapup", "--push")
    assert res.returncode == EXIT_PREFLIGHT
    assert "serialize against nobody" in res.stderr


@pytest.mark.parametrize("bad", ["../evil", "/abs", "Wrapup", "", "a" * 40, "wrap up"])
def test_lock_name_cannot_escape_the_lock_directory(bad):
    with pytest.raises(SerializedPushError):
        validate_lock_name(bad)
