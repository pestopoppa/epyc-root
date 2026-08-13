"""Two mains wrapping up AT THE SAME TIME must not overwrite each other.

THE ACCEPTANCE TEST for worktree adoption phase 3. The operator's complaint,
stated mechanically, was three separate mechanisms firing at once:

  1. every main appended to ONE `progress/YYYY-MM/YYYY-MM-DD.md` (ten wrap-up
     commits hit one 368 KB file on 2026-08-12);
  2. `git commit -- <path>` commits the WORKING TREE of that path, not the
     index, so each of those commits swept whatever the other four had
     half-written into the same file (proven by `dada0bbc`);
  3. the genuinely shared, GENERATED surfaces (the master-index block,
     `wiki/source_manifest.json`, `wiki/.last_compile`) are rewritten wholesale,
     so two concurrent regens mean one is simply lost.

Phase 3's answers are, respectively: a per-agent daily progress file, a private
working tree per lane, and a wrap-up lease around the shared-surface steps and
the promotion merge.

This test runs the whole thing for real -- two lane worktrees of one clone, two
concurrent OS processes, the production `serialized_push.py` lease with its real
O_EXCL primitive and real repo-key derivation, and the real `/wrap-up` step 7
detach-merge promotion pattern -- against a throwaway repository, so it can
assert the outcome instead of describing it.

It carries its own NEGATIVE CONTROL (`test_without_the_lease_a_write_is_lost`):
the identical scenario with the lease removed must LOSE one main's shared-surface
write. Without that, this file would pass just as happily if the lease did
nothing at all -- a check that passes for a reason unrelated to what it tests is
the failure mode this repository catalogues most often.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LEASE_CLI = REPO_ROOT / "scripts" / "coordination" / "serialized_push.py"

AGENTS = ("mainC", "mainD")
DAY = "2026-08-12"
MONTH = "2026-08"

# Long enough that the two workers genuinely overlap inside the critical section
# if the lease is not doing its job -- the negative control depends on it.
CRITICAL_SECTION_SLEEP_S = "1.5"


# ---------------------------------------------------------------------------
# fixture: a throwaway clone with an "origin" and two lane worktrees
# ---------------------------------------------------------------------------


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(cwd), *args],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} in {cwd}: {proc.stderr or proc.stdout}")
    return proc.stdout.strip()


@pytest.fixture
def fleet(tmp_path: Path) -> dict:
    """origin (bare) + a shared clone on `main` + one lane worktree per agent."""
    env = {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x",
    }
    os.environ.update(env)

    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)],
                   check=True, capture_output=True)

    shared = tmp_path / "shared"
    subprocess.run(["git", "init", "-b", "main", str(shared)], check=True, capture_output=True)
    _git(shared, "config", "user.email", "t@x")
    _git(shared, "config", "user.name", "t")
    # Hooks off: this test is about concurrency, not about the pre-commit suite.
    _git(shared, "config", "core.hooksPath", str(tmp_path / "no-hooks"))

    (shared / "progress" / MONTH).mkdir(parents=True)
    (shared / "wiki").mkdir()
    # The stand-in for a GENERATED shared surface: rewritten wholesale from
    # current state, exactly like the master-index block and source_manifest.json.
    (shared / "wiki" / "source_manifest.json").write_text(
        json.dumps({"compiled_by": []}, indent=2) + "\n", encoding="utf-8")
    _git(shared, "add", "-A")
    _git(shared, "commit", "-m", "seed")
    _git(shared, "remote", "add", "origin", str(origin))
    _git(shared, "push", "-u", "origin", "main")

    lanes = {}
    for agent in AGENTS:
        lane = tmp_path / f"lane-{agent}"
        _git(shared, "worktree", "add", "-b", f"lane/{agent}", str(lane), "main")
        _git(shared, "push", "origin", f"lane/{agent}")
        lanes[agent] = lane

    return {"tmp": tmp_path, "origin": origin, "shared": shared, "lanes": lanes,
            "lock_dir": tmp_path / "push-locks"}


# ---------------------------------------------------------------------------
# the worker: ONE main's wrap-up, as the contract in agents/commands/wrap-up.md
# describes it. Run in a separate OS process, twice, concurrently.
# ---------------------------------------------------------------------------

_WORKER = textwrap.dedent(r'''
    import json, os, subprocess, sys, time
    from pathlib import Path

    agent, lane, lock_dir, lease_cli, use_lease, sleep_s = sys.argv[1:7]
    lane = Path(lane)
    day, month = "%(DAY)s", "%(MONTH)s"

    def git(*a, check=True):
        p = subprocess.run(["git", "-C", str(lane), *a], capture_output=True, text=True)
        if check and p.returncode != 0:
            raise SystemExit(f"{agent}: git {' '.join(a)}: {p.stderr or p.stdout}")
        return p

    def lease(*a):
        return subprocess.run(
            [sys.executable, lease_cli, "--agent", agent, "--repo", str(lane),
             "--lock-dir", lock_dir, "--lock-name", "wrapup", *a],
            capture_output=True, text=True)

    # ---- STEP 1: the per-agent daily progress file. No lease: nobody shares it.
    prog = lane / "progress" / month / f"{day}-{agent}.md"
    prog.parent.mkdir(parents=True, exist_ok=True)
    prog.write_text(f"# {day} {agent}\n\nwrapped up.\n", encoding="utf-8")
    git("add", str(prog.relative_to(lane)))
    git("commit", "-m", f"progress: {agent}")

    # ---- take the lease for the shared surface + the promotion merge
    if use_lease == "1":
        deadline = time.time() + 60
        while True:
            r = lease("--acquire")
            if r.returncode == 0:
                break
            if time.time() > deadline:
                raise SystemExit(f"{agent}: never got the lease: {r.stderr}")
            time.sleep(0.25)

    try:
        # ---- SYNC FIRST: build on whoever went before you. A generated file is
        #      rewritten wholesale, so regenerating from a stale lane and then
        #      promoting overwrites the previous holder's answer with an older one.
        git("fetch", "origin", "--quiet")
        git("merge", "--no-edit", "origin/main")

        # ---- the shared surface: read-modify-write, with a deliberate gap.
        surf = lane / "wiki" / "source_manifest.json"
        data = json.loads(surf.read_text(encoding="utf-8"))
        time.sleep(float(sleep_s))            # the window a lost update needs
        data["compiled_by"] = sorted(set(data.get("compiled_by", [])) | {agent})
        surf.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        git("add", "wiki/source_manifest.json")
        git("commit", "-m", f"wiki: compiled by {agent}")

        # ---- PUSH the lane BEFORE promoting. /wrap-up step 7 pushes the branch
        #      first and the promotion merges `origin/lane/<agent>`; promoting
        #      before pushing merges a stale remote tip and silently lands nothing.
        git("push", "origin", f"lane/{agent}")

        # ---- PROMOTE, via /wrap-up step 7's isolated detach-merge. Never touches
        #      the live lane or its branch; aborts and reports on conflict.
        wt = Path(os.environ["WRAPUP_TMP"]) / f"promote-{agent}"
        git("worktree", "add", "--detach", str(wt), "origin/main")
        m = subprocess.run(["git", "-C", str(wt), "merge", "--no-ff", "-m",
                            f"Merge lane/{agent} into main (wrap-up promotion {day})",
                            f"origin/lane/{agent}"], capture_output=True, text=True)
        if m.returncode == 0:
            subprocess.run(["git", "-C", str(wt), "push", "origin", "HEAD:main"],
                           capture_output=True, text=True, check=True)
            print(f"{agent}: PROMOTED")
        else:
            subprocess.run(["git", "-C", str(wt), "merge", "--abort"],
                           capture_output=True, text=True)
            print(f"{agent}: PROMOTION BLOCKED")
        git("worktree", "remove", str(wt), "--force")   # remove, NEVER prune
    finally:
        if use_lease == "1":
            lease("--release")
''') % {"DAY": DAY, "MONTH": MONTH}


def _run_worker(args: tuple) -> subprocess.CompletedProcess:
    worker_path, agent, lane, lock_dir, use_lease, tmp = args
    env = dict(os.environ)
    env["WRAPUP_TMP"] = tmp
    return subprocess.run(
        [sys.executable, worker_path, agent, lane, lock_dir, str(LEASE_CLI),
         use_lease, CRITICAL_SECTION_SLEEP_S],
        capture_output=True, text=True, env=env)


def _wrap_up_concurrently(fleet: dict, use_lease: str) -> list:
    worker = fleet["tmp"] / "worker.py"
    worker.write_text(_WORKER, encoding="utf-8")
    jobs = [(str(worker), a, str(fleet["lanes"][a]), str(fleet["lock_dir"]),
             use_lease, str(fleet["tmp"])) for a in AGENTS]
    with ProcessPoolExecutor(max_workers=len(jobs)) as ex:
        return list(ex.map(_run_worker, jobs))


def _main_state(fleet: dict) -> tuple[dict, list[str]]:
    """(the shared surface on main, the file list on main)."""
    read = fleet["tmp"] / "read-main"
    if read.exists():
        subprocess.run(["rm", "-rf", str(read)], check=True)
    _git(fleet["shared"], "fetch", "origin", "--quiet")
    _git(fleet["shared"], "worktree", "add", "--detach", str(read), "origin/main")
    surface = json.loads((read / "wiki" / "source_manifest.json").read_text(encoding="utf-8"))
    files = _git(read, "ls-files").splitlines()
    _git(fleet["shared"], "worktree", "remove", str(read), "--force")
    return surface, files


# ---------------------------------------------------------------------------
# THE ACCEPTANCE TEST
# ---------------------------------------------------------------------------


def test_two_concurrent_wrapups_neither_sweeps_the_other(fleet):
    results = _wrap_up_concurrently(fleet, use_lease="1")
    for agent, res in zip(AGENTS, results):
        assert res.returncode == 0, f"{agent} wrap-up failed:\n{res.stdout}\n{res.stderr}"
        assert "PROMOTED" in res.stdout, f"{agent} did not promote:\n{res.stdout}{res.stderr}"

    surface, files = _main_state(fleet)

    # 1. BOTH promotions landed on main.
    assert "PROMOTION BLOCKED" not in "".join(r.stdout for r in results)

    # 2. Neither main's progress file was swept: they are DIFFERENT FILES, which
    #    is the whole point of the per-agent convention.
    for agent in AGENTS:
        assert f"progress/{MONTH}/{DAY}-{agent}.md" in files, \
            f"{agent}'s progress file is missing from main: {files}"
    assert f"progress/{MONTH}/{DAY}.md" not in files, \
        "the shared five-writer progress file must not be recreated"

    # 3. The GENERATED shared surface carries BOTH sessions' contribution. This is
    #    the one the lease exists for: a wholesale rewrite loses the other writer
    #    unless the second holder regenerates on top of the first's promotion.
    assert sorted(surface["compiled_by"]) == sorted(AGENTS), (
        f"a shared-surface write was lost: {surface['compiled_by']}"
    )


def test_without_the_lease_a_write_is_lost(fleet):
    """NEGATIVE CONTROL. Remove the lease and the same run must lose something.

    Without this the acceptance test above would pass identically if the lease
    were a no-op, and would then be evidence of nothing.
    """
    results = _wrap_up_concurrently(fleet, use_lease="0")
    surface, files = _main_state(fleet)
    blocked = "PROMOTION BLOCKED" in "".join(r.stdout for r in results)
    lost = sorted(surface.get("compiled_by", [])) != sorted(AGENTS)
    assert blocked or lost, (
        "unleased concurrent wrap-ups completed cleanly — the critical section is "
        "not actually contended, so the positive test proves nothing. Widen "
        "CRITICAL_SECTION_SLEEP_S or check that both workers really overlap."
    )


def test_the_lease_is_one_lease_across_every_lane_of_one_clone(fleet):
    """Two lane worktrees are two PATHS to one repository.

    A lock keyed on the path would give each lane its own lease and serialize
    nothing at all. Asserted here as well as in test_serialized_push.py because
    this is the property the whole acceptance test rests on.
    """
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.coordination.serialized_push import repo_key  # noqa: E402

    keys = {a: repo_key(fleet["lanes"][a]) for a in AGENTS}
    assert len(set(keys.values())) == 1, keys
    assert repo_key(fleet["shared"]) == next(iter(keys.values()))
