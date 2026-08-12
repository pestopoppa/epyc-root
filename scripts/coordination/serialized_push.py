#!/usr/bin/env python3
"""Serialized, evidence-producing `git push` for a clone shared by parallel sessions.

THE PROBLEM THIS CLOSES (measured 2026-08-11/12, not hypothetical).
Several agent sessions share ONE clone per repo and all work on `main`. `git push`
publishes the WHOLE shared branch, not "your" commits. On the day this was written
epyc-root stood 29 commits ahead of origin and only a handful belonged to any one
session; 349 commits landed across all sessions in a single day. Two consequences,
both real:

  1. PUBLICATION WITHOUT REVIEW. An unserialized push from session X publishes work
     from sessions Y and Z that X has never read and cannot vouch for.
  2. A RACE. Two sessions pushing concurrently interleave: one force-fetches or
     resets under the other.

So pushing is treated as a critical section with an audit trail:

  * an EXCLUSIVE LOCK, taken with O_EXCL, before any network operation;
  * a PUBLISH MANIFEST printed before the push, so the pusher sees exactly what
    they are about to publish on everyone else's behalf;
  * DRY-RUN BY DEFAULT — publishing requires the explicit `--push` flag;
  * FAIL CLOSED and by NAME on every ambiguous repository state.

WHY O_EXCL AND WHY NO AUTO-EXPIRY. Same discipline as the session-bus claim scheme
(`session_bus.py: cmd_claim`): the create either succeeds (you own it) or fails
(somebody else does), and there is no window between checking and taking because
there is no check. A lock has exactly one writer for its whole life. Consequently a
holder whose PID is gone is reported as *evidence* — "may be residue" — and never
auto-released: an idle owner is not an absent one, and auto-expiry would destroy the
single-writer property that makes the whole scheme sound. Displacing a holder is
possible but must be deliberate and attributable: `--force-release <holder-id>`
requires you to NAME the agent you are displacing, and is journaled.

WHY THE LOCK IS KEYED ON (st_dev, st_ino) AND NOT ON A PATH. Measured on this host:

    /workspace/.git                 realpath /workspace/.git                 inode 96604699
    /mnt/raid0/llm/epyc-root/.git   realpath /mnt/raid0/llm/epyc-root/.git   inode 96604699

One repository, two paths, and `os.path.realpath` does NOT collapse them — they are a
bind mount, not a symlink, so each path is its own realpath. (`/workspace/repos/*` ARE
symlinks, so realpath collapses those.) A path-keyed lock would therefore hand out two
locks for one repo to two sessions and serialize nothing, precisely between the two
views this fleet actually uses. The device+inode pair is the identity the repo itself
has — which is also the identity check the project guide prescribes for these trees
(`stat -c %i`) — so that is the key. Nothing human-readable goes in the lock FILENAME
for the same reason: the basename differs per view ("workspace" vs "epyc-root") and
would re-split the key. The observed paths are recorded INSIDE the lock record instead.

WHAT THIS DELIBERATELY DOES NOT DO: it never commits, never resets, never rebases,
never fetches unless asked (`--fetch`), and never force-pushes. It publishes the shared
branch as it stands, or it refuses.

USAGE
    serialized_push.py --agent mainA --repo /workspace                  # dry run (default)
    serialized_push.py --agent mainA --repo /workspace --status         # who holds the lock
    serialized_push.py --agent mainA --repo /workspace --acquire        # hold across a review
    serialized_push.py --agent mainA --repo /workspace --push           # publish, under lock
    serialized_push.py --agent mainA --repo /workspace --release
    serialized_push.py --agent mainB --repo /workspace --force-release mainA

EXIT CODES
    0 ok            1 usage         2 lock contention
    3 preflight refused (repo state not publishable)    4 push failed
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_LOCKED = 2
EXIT_PREFLIGHT = 3
EXIT_PUSH_FAILED = 4

DEFAULT_LOCK_DIR = Path(__file__).resolve().parents[2] / "coordination" / "push-locks"

# ---------------------------------------------------------------------------
# Errors. Every one carries a machine-readable `condition`, because "fail loud"
# means naming the specific cause: a generic "repo not clean" tells the next
# session nothing about what to fix.
# ---------------------------------------------------------------------------


class SerializedPushError(Exception):
    condition = "unknown"

    def __init__(self, message: str, condition: str | None = None):
        super().__init__(message)
        if condition is not None:
            self.condition = condition


class PreflightError(SerializedPushError):
    """Repository state is not publishable. Named, never generic."""


class LockHeldError(SerializedPushError):
    """Somebody else holds the push lock. Never stolen, only refused."""

    def __init__(self, message: str, holder: dict | None = None,
                 condition: str = "lock-held"):
        super().__init__(message, condition)
        self.holder = holder or {}


class LockCorruptError(SerializedPushError):
    """A lock file exists but cannot be read. Fail closed: a lock we cannot
    parse is still a lock somebody took."""


class NotHolderError(SerializedPushError):
    """Refusing to release a lock the caller does not own."""


class PushFailedError(SerializedPushError):
    """`git push` itself was rejected (non-fast-forward, hook, auth, ...)."""


# ---------------------------------------------------------------------------
# git plumbing
# ---------------------------------------------------------------------------


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git(repo: os.PathLike | str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True,
    )
    if check and proc.returncode != 0:
        raise SerializedPushError(
            f"git {' '.join(args)} failed in {repo}: {proc.stderr.strip() or proc.stdout.strip()}",
            condition="git-command-failed",
        )
    return proc


def git_dirs(repo: os.PathLike | str) -> tuple[Path, Path]:
    """(git_dir, git_common_dir), both absolute.

    `git_dir` is per-worktree (where CHERRY_PICK_HEAD/MERGE_HEAD live);
    `git_common_dir` is shared by all worktrees of one repository and is what the
    lock key is derived from — two worktrees of the same clone push the same branch
    to the same remote and must contend for one lock.

    Deliberately does NOT ask for `--show-toplevel`: that fails in a BARE repository,
    which would make every bare repo report "not-a-git-repo" — a wrong condition name,
    and the whole point of this module is that the condition name is true.
    """
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--path-format=absolute",
         "--git-dir", "--git-common-dir"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise PreflightError(
            f"not-a-git-repo: {repo} is not inside a git repository "
            f"({proc.stderr.strip()})",
            condition="not-a-git-repo",
        )
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if len(lines) < 2:
        raise PreflightError(
            f"not-a-git-repo: could not resolve git directories for {repo}",
            condition="not-a-git-repo",
        )
    return Path(lines[0]), Path(lines[1])


def repo_key(repo: os.PathLike | str) -> str:
    """Identity of the REPOSITORY, stable across every path that reaches it.

    See the module docstring: neither the path nor its realpath is stable across
    the bind-mounted views this fleet uses, so the key is the device+inode of the
    git common directory.
    """
    _, common = git_dirs(repo)
    st = os.stat(common)
    return f"{st.st_dev}-{st.st_ino}"


# ---------------------------------------------------------------------------
# The lock
# ---------------------------------------------------------------------------


def lock_path(lock_dir: os.PathLike | str, key: str) -> Path:
    return Path(lock_dir) / f"push-{key}.json"


def read_lock(path: os.PathLike | str) -> dict | None:
    """The lock record, or None if free. Raises LockCorruptError if present but
    unreadable — an unparseable lock is treated as HELD, never as free."""
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise LockCorruptError(
            f"lock-unreadable: {p} exists but cannot be read ({exc}); "
            f"refusing — an unreadable lock is still a lock",
            condition="lock-unreadable",
        ) from exc
    try:
        rec = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LockCorruptError(
            f"lock-corrupt: {p} is not valid JSON ({exc}); refusing. "
            f"Inspect it and use --force-release naming the holder if it is residue.",
            condition="lock-corrupt",
        ) from exc
    if not isinstance(rec, dict):
        raise LockCorruptError(
            f"lock-corrupt: {p} does not contain a lock record", condition="lock-corrupt")
    return rec


def pid_liveness(rec: dict) -> tuple[str, str]:
    """(state, human explanation) for the holder's PID.

    States: 'running' | 'gone' | 'unknown'. 'unknown' is returned whenever the
    answer cannot be established from HERE — a different host, or a PID namespace
    we are not in — because a liveness check that silently answers for the wrong
    process is worse than no check.
    """
    pid = rec.get("pid")
    host = rec.get("host")
    if not isinstance(pid, int):
        return "unknown", "holder record carries no usable PID"
    me = socket.gethostname()
    if host and host != me:
        return "unknown", (f"holder PID {pid} was recorded on host {host!r}, not {me!r}; "
                           f"liveness is not checkable from here")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return "gone", (f"holder PID {pid} is not running; lock may be residue "
                        f"(this is evidence, not proof — an idle owner is not an absent one)")
    except PermissionError:
        return "running", f"holder PID {pid} is running (owned by another user)"
    except OSError as exc:
        return "unknown", f"holder PID {pid} liveness undetermined ({exc})"
    return "running", f"holder PID {pid} is running"


def lock_age_hours(rec: dict) -> float | None:
    try:
        return (datetime.now(timezone.utc)
                - datetime.fromisoformat(rec["ts"])).total_seconds() / 3600.0
    except (KeyError, TypeError, ValueError):
        return None


def describe_holder(rec: dict) -> str:
    """Everything a blocked reader needs to decide what to do — and nothing that
    would let them decide wrongly.

    The `mode` distinction matters and was a real defect before it existed. A lock
    taken with `--acquire` is held ACROSS invocations: the process that took it exits
    immediately by design, so its PID is dead within a second. Reported naively, the
    strongest, most deliberate hold in the system reads as the stalest residue and
    invites exactly the displacement it was taken to prevent. So for a held lock the
    dead PID is reported as EXPECTED, and age becomes the residue signal instead.
    """
    state, why = pid_liveness(rec)
    mode = rec.get("mode", "push")
    age = lock_age_hours(rec)
    age_txt = f"  ({age:.1f}h ago)" if age is not None else "  (unparseable timestamp)"
    lines = [
        f"  holder : {rec.get('agent')!r}",
        f"  since  : {rec.get('ts')}{age_txt}",
        f"  pid    : {rec.get('pid')} on {rec.get('host')}  [{state}]",
        f"  repo   : {rec.get('repo_path')}  (key {rec.get('repo_key')})",
        f"  mode   : {mode}" + ("  (held across invocations via --acquire)"
                                if mode == "hold" else "  (taken for a single push)"),
    ]
    if state == "gone" and mode == "hold":
        lines.append(f"  note   : holder PID {rec.get('pid')} is not running, which is EXPECTED "
                     f"for a lock held via --acquire —")
        lines.append("           the taking process exits by design, so this is NOT evidence of "
                     "residue. Age is the")
        lines.append(f"           only residue signal here: {age_txt.strip() or 'unknown'}.")
    else:
        lines.append(f"  note   : {why}")
    if state == "gone":
        lines.append("  action : NOT auto-expired. If this is residue, displace it deliberately:")
        lines.append(f"           --force-release {rec.get('agent')}")
    return "\n".join(lines)


def acquire(lock_dir, key, agent: str, repo_path: str, pid: int | None = None,
            mode: str = "push") -> dict:
    """Take the push lock with O_EXCL, or raise LockHeldError naming the holder.

    Reuse rules, and why each one:
      * same agent, same PID  -> already yours; idempotent (a retry is not a race).
      * same agent, other PID that is RUNNING -> REFUSED. Two live processes sharing
        one roster id are exactly the concurrency this exists to stop.
      * same agent, other PID that is GONE -> reclaimed, loudly. Your own residue
        must not lock you out of the work you hold (session-bus precedent: re-claiming
        your OWN row is not a collision).
      * different agent -> ALWAYS refused, running or not. Never stolen.
    """
    pid = os.getpid() if pid is None else pid
    lock_dir = Path(lock_dir)
    path = lock_path(lock_dir, key)
    rec = {
        "agent": agent,
        "pid": pid,
        "host": socket.gethostname(),
        "ts": _utcnow_iso(),
        "repo_key": key,
        "repo_path": str(repo_path),
        # "push" = taken for the duration of one push; a dead PID is real evidence of
        # residue. "hold" = taken by --acquire and held across invocations; a dead PID
        # is EXPECTED and evidence of nothing. See describe_holder().
        "mode": mode,
    }
    lock_dir.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        held = read_lock(path) or {}
        if held.get("agent") == agent:
            if held.get("pid") == pid:
                return held
            state, why = pid_liveness(held)
            if state == "running" or state == "unknown":
                raise LockHeldError(
                    f"lock-held: your own agent id {agent!r} already holds this lock from a "
                    f"different process.\n{describe_holder(held)}",
                    holder=held, condition="lock-held-same-agent",
                )
            # Own residue: reclaim, but say so.
            path.unlink()
            print(f"serialized_push: reclaiming your own lock ({why})", file=sys.stderr)
            return acquire(lock_dir, key, agent, repo_path, pid=pid, mode=mode)
        raise LockHeldError(
            f"lock-held: refusing to push — {held.get('agent')!r} holds the push lock "
            f"for this repo.\n{describe_holder(held)}",
            holder=held, condition="lock-held",
        )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, sort_keys=True)
            fh.write("\n")
    except BaseException:
        # Never leave a half-written lock: it would be unparseable, and an
        # unparseable lock is treated as held by nobody-knows-whom.
        try:
            path.unlink()
        except OSError:
            pass
        raise
    return rec


def release(lock_dir, key, agent: str) -> bool:
    """Drop a lock you hold. False if there was nothing to drop.

    Ownership is the AGENT id: a session that restarted must be able to clean up
    after itself. But a different, RUNNING process under the same id is refused —
    releasing a live pusher's lock mid-push is the race, wearing a helpful face.
    """
    path = lock_path(lock_dir, key)
    rec = read_lock(path)
    if rec is None:
        return False
    if rec.get("agent") != agent:
        raise NotHolderError(
            f"not-holder: {agent!r} may not release a lock held by {rec.get('agent')!r}.\n"
            f"{describe_holder(rec)}\n"
            f"  If you must displace it, say so explicitly: --force-release {rec.get('agent')}",
            condition="not-holder",
        )
    if rec.get("pid") != os.getpid():
        state, why = pid_liveness(rec)
        if state in ("running", "unknown"):
            raise NotHolderError(
                f"not-holder: {agent!r} holds this lock from a different process "
                f"that is still live.\n{describe_holder(rec)}\n"
                f"  Refusing to release another running process's lock. Use "
                f"--force-release {agent} if you are certain.",
                condition="not-holder-live-sibling",
            )
        print(f"serialized_push: releasing your own residue ({why})", file=sys.stderr)
    path.unlink()
    return True


def force_release(lock_dir, key, agent: str, named_holder: str) -> dict:
    """Displace a holder — deliberately, and on the record.

    You must NAME the holder you are displacing. Naming the wrong one is refused,
    which makes it impossible to blind-break a lock whose owner you never looked at.
    Every displacement is journaled next to the lock.
    """
    path = lock_path(lock_dir, key)
    rec = read_lock(path)
    if rec is None:
        raise NotHolderError(
            f"no-lock: nothing to force-release for repo key {key}",
            condition="no-lock",
        )
    holder = rec.get("agent")
    if holder != named_holder:
        raise NotHolderError(
            f"holder-mismatch: you named {named_holder!r} but the lock is held by "
            f"{holder!r}.\n{describe_holder(rec)}\n"
            f"  Displacement must name the agent actually being displaced.",
            condition="holder-mismatch",
        )
    journal = Path(lock_dir) / "displacements.jsonl"
    entry = {
        "ts": _utcnow_iso(),
        "by_agent": agent,
        "by_pid": os.getpid(),
        "host": socket.gethostname(),
        "displaced": rec,
    }
    try:
        with journal.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError as exc:  # journal failure must not silently swallow the act
        print(f"serialized_push: WARNING could not journal displacement: {exc}",
              file=sys.stderr)
    path.unlink()
    return rec


# ---------------------------------------------------------------------------
# Preflight: fail closed, and name the condition
# ---------------------------------------------------------------------------

# Each entry: (marker path relative to the per-worktree git dir, condition, explanation)
_IN_PROGRESS = [
    ("CHERRY_PICK_HEAD", "mid-cherry-pick",
     "a cherry-pick is in progress; git refuses partial commits and the tree is not publishable"),
    ("REVERT_HEAD", "mid-revert",
     "a revert is in progress; the tree is not publishable"),
    ("MERGE_HEAD", "mid-merge",
     "a merge is in progress; the tree is not publishable"),
    ("rebase-merge", "mid-rebase",
     "a rebase is in progress; HEAD is a transient state, not something to publish"),
    ("rebase-apply", "mid-rebase",
     "a rebase or `git am` is in progress; HEAD is a transient state, not something to publish"),
    ("BISECT_LOG", "mid-bisect",
     "a bisect is in progress; HEAD is a bisect probe, not a branch tip"),
]


def preflight(repo: os.PathLike | str, *, require_fetched: bool = True) -> dict:
    """Everything that must be unambiguously true before publishing.

    Order is deliberate. An interrupted operation is checked BEFORE detached HEAD
    because a rebase detaches HEAD as a matter of course, and reporting "detached
    HEAD" for a rebase would name a symptom instead of the cause.
    """
    git_dir, common_dir = git_dirs(repo)

    if git(repo, "rev-parse", "--is-bare-repository").stdout.strip() == "true":
        raise PreflightError(
            f"bare-repository: {git_dir} is a bare repository; there is no working "
            f"branch here to publish",
            condition="bare-repository",
        )
    toplevel = Path(git(repo, "rev-parse", "--path-format=absolute",
                        "--show-toplevel").stdout.strip())

    for marker, condition, why in _IN_PROGRESS:
        if (git_dir / marker).exists():
            raise PreflightError(
                f"{condition}: {why} (found {git_dir / marker}). "
                f"Finish or abort it, then push.",
                condition=condition,
            )

    head = subprocess.run(
        ["git", "-C", str(repo), "symbolic-ref", "--quiet", "--short", "HEAD"],
        capture_output=True, text=True,
    )
    if head.returncode != 0 or not head.stdout.strip():
        sha = git(repo, "rev-parse", "--verify", "HEAD", check=False).stdout.strip() or "unknown"
        raise PreflightError(
            f"detached-head: HEAD is detached at {sha[:12]}; there is no branch to "
            f"publish. Check out the branch you mean to push.",
            condition="detached-head",
        )
    branch = head.stdout.strip()

    unmerged = git(repo, "ls-files", "--unmerged").stdout.strip()
    if unmerged:
        paths = sorted({ln.split("\t", 1)[-1] for ln in unmerged.splitlines()})
        raise PreflightError(
            f"unmerged-paths: the index has {len(paths)} unmerged path(s) "
            f"({', '.join(paths[:5])}{' ...' if len(paths) > 5 else ''}); "
            f"the repository state is not publishable",
            condition="unmerged-paths",
        )

    remote = git(repo, "config", "--get", f"branch.{branch}.remote", check=False).stdout.strip()
    merge_ref = git(repo, "config", "--get", f"branch.{branch}.merge", check=False).stdout.strip()
    if not remote or not merge_ref:
        raise PreflightError(
            f"no-upstream: branch {branch!r} has no upstream configured "
            f"(branch.{branch}.remote={remote or '<unset>'}, "
            f"branch.{branch}.merge={merge_ref or '<unset>'}). "
            f"Refusing to guess where this should be published.",
            condition="no-upstream",
        )
    if git(repo, "remote", "get-url", remote, check=False).returncode != 0:
        raise PreflightError(
            f"unknown-remote: branch {branch!r} tracks remote {remote!r}, which is not "
            f"configured in this repository",
            condition="unknown-remote",
        )

    remote_branch = merge_ref.split("refs/heads/", 1)[-1]
    upstream_ref = f"refs/remotes/{remote}/{remote_branch}"
    have_upstream = git(repo, "rev-parse", "--verify", "--quiet", upstream_ref,
                        check=False).returncode == 0
    if require_fetched and not have_upstream:
        raise PreflightError(
            f"upstream-ref-not-fetched: {upstream_ref} does not exist locally, so what "
            f"would be published cannot be computed. Re-run with --fetch (it runs under "
            f"the lock), or fetch it yourself.",
            condition="upstream-ref-not-fetched",
        )

    return {
        "toplevel": str(toplevel),
        "git_dir": str(git_dir),
        "common_dir": str(common_dir),
        "branch": branch,
        "remote": remote,
        "remote_branch": remote_branch,
        "merge_ref": merge_ref,
        "upstream_ref": upstream_ref,
        "have_upstream": have_upstream,
    }


# ---------------------------------------------------------------------------
# The publish manifest
# ---------------------------------------------------------------------------

_PREFIX_RE = re.compile(r"^([A-Za-z0-9_.\-]{1,20})(\([^)]{0,40}\))?!?:\s")


def subject_prefix(subject: str) -> str:
    m = _PREFIX_RE.match(subject)
    return m.group(1).lower() if m else "(no prefix)"


def build_manifest(repo: os.PathLike | str, pf: dict) -> dict:
    """Exactly what a push WOULD publish.

    The one thing this cannot tell you is WHO wrote it: every session on this host
    commits under the same git identity, so `git log --format=%an` is a constant and
    proves nothing about provenance. The manifest therefore groups by things that are
    real — changed top-level path and commit-subject prefix — and says so in the
    rendered output rather than letting a reader assume the author column means
    something.
    """
    rng = f"{pf['upstream_ref']}..HEAD"
    counts = git(repo, "rev-list", "--left-right", "--count",
                 f"{pf['upstream_ref']}...HEAD").stdout.split()
    behind, ahead = (int(counts[0]), int(counts[1])) if len(counts) == 2 else (0, 0)

    commits: list[dict] = []
    if ahead:
        raw = git(repo, "log", "--format=%H%x1f%s%x1f%cI%x1f%an", rng).stdout
        for line in raw.splitlines():
            if not line.strip():
                continue
            sha, subject, ts, author = (line.split("\x1f") + ["", "", ""])[:4]
            commits.append({"sha": sha, "subject": subject, "ts": ts, "author": author,
                            "prefix": subject_prefix(subject)})

    changed: list[str] = []
    if ahead:
        changed = [ln for ln in git(repo, "diff", "--name-only",
                                    f"{pf['upstream_ref']}..HEAD").stdout.splitlines() if ln]

    by_top: dict[str, int] = {}
    for path in changed:
        top = path.split("/", 1)[0] if "/" in path else f"{path} (root file)"
        by_top[top] = by_top.get(top, 0) + 1
    by_prefix: dict[str, int] = {}
    for c in commits:
        by_prefix[c["prefix"]] = by_prefix.get(c["prefix"], 0) + 1

    return {
        "range": rng,
        "ahead": ahead,
        "behind": behind,
        "commits": commits,
        "changed_files": changed,
        "changed_file_count": len(changed),
        "by_top_level_path": dict(sorted(by_top.items(), key=lambda kv: (-kv[1], kv[0]))),
        "by_subject_prefix": dict(sorted(by_prefix.items(), key=lambda kv: (-kv[1], kv[0]))),
        "distinct_authors": sorted({c["author"] for c in commits}),
    }


def render_manifest(pf: dict, man: dict, limit: int = 40) -> str:
    out: list[str] = []
    a = out.append
    a("=" * 78)
    a("PUBLISH MANIFEST — what a push WOULD publish")
    a("=" * 78)
    a(f"repo        : {pf['toplevel']}")
    a(f"branch      : {pf['branch']}  ->  {pf['remote']}/{pf['remote_branch']}")
    a(f"range       : {man['range']}")
    a(f"commits     : {man['ahead']}")
    a(f"files       : {man['changed_file_count']} changed")
    if man["behind"]:
        a(f"BEHIND      : {man['behind']} commit(s) on {pf['upstream_ref']} are not in HEAD — "
          f"a plain push will be REJECTED as non-fast-forward")
    if man["ahead"] == 0:
        a("")
        a("Nothing to publish: HEAD is not ahead of its upstream.")
        return "\n".join(out)

    a("")
    a("-- SHARED-BRANCH WARNING ------------------------------------------------")
    a(f"A push publishes the WHOLE branch. You are about to publish {man['ahead']} commit(s)")
    a("from a clone shared by several sessions. Any of these may be work you have")
    a("never reviewed and cannot vouch for.")
    if len(man["distinct_authors"]) <= 1:
        who = man["distinct_authors"][0] if man["distinct_authors"] else "<none>"
        a(f"AUTHORSHIP IS NOT RECOVERABLE FROM GIT ON THIS HOST: all {man['ahead']} commit(s)")
        a(f"carry the same git identity ({who!r}), so `git log --format=%an` cannot tell")
        a("you which commits are yours. The groupings below are the real signal.")
    else:
        a(f"NOTE: git identities present: {', '.join(man['distinct_authors'])} — but on this")
        a("host sessions share an identity, so this is not a provenance signal.")

    a("")
    a("-- by changed top-level path --------------------------------------------")
    for top, n in man["by_top_level_path"].items():
        a(f"  {n:5d}  {top}")
    a("")
    a("-- by commit subject prefix ---------------------------------------------")
    for pre, n in man["by_subject_prefix"].items():
        a(f"  {n:5d}  {pre}")

    a("")
    a("-- commits ---------------------------------------------------------------")
    for c in man["commits"][:limit]:
        a(f"  {c['sha'][:12]}  {c['ts'][:19]}  {c['subject'][:88]}")
    if man["ahead"] > limit:
        a(f"  ... and {man['ahead'] - limit} more")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------


def do_push(repo: os.PathLike | str, pf: dict) -> str:
    """Plain, non-forcing push of the current branch to its configured upstream.

    No --force, no --force-with-lease, no refspec guessing: the destination comes
    from the branch's own upstream config, verified in preflight.
    """
    proc = subprocess.run(
        ["git", "-C", str(repo), "push", pf["remote"], f"HEAD:{pf['merge_ref']}"],
        capture_output=True, text=True,
    )
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        raise PushFailedError(
            f"push-rejected: git push {pf['remote']} HEAD:{pf['merge_ref']} exited "
            f"{proc.returncode}\n{output}",
            condition="push-rejected",
        )
    return output


def do_fetch(repo: os.PathLike | str, remote: str, remote_branch: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "fetch", remote,
         f"+refs/heads/{remote_branch}:refs/remotes/{remote}/{remote_branch}"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise SerializedPushError(
            f"fetch-failed: git fetch {remote} {remote_branch} exited {proc.returncode}\n"
            f"{(proc.stdout + proc.stderr).strip()}",
            condition="fetch-failed",
        )
    return (proc.stdout + proc.stderr).strip()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="serialized_push.py",
        description="Serialized, evidence-producing git push for a shared clone. "
                    "DRY RUN IS THE DEFAULT; publishing requires --push.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--agent", required=True,
                   help="your roster id; recorded as the lock holder")
    p.add_argument("--repo", default=".", help="path inside the repository (default: cwd)")
    p.add_argument("--lock-dir", default=os.environ.get("SERIALIZED_PUSH_LOCK_DIR",
                                                        str(DEFAULT_LOCK_DIR)),
                   help="where push locks live (default: %(default)s)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true",
                   help="explicit form of the default: show the manifest, publish nothing")
    g.add_argument("--push", action="store_true",
                   help="actually publish, under the lock. Without this, nothing is pushed.")
    g.add_argument("--acquire", action="store_true",
                   help="take the lock and hold it across invocations (for a review window)")
    g.add_argument("--release", action="store_true", help="drop a lock you hold")
    g.add_argument("--force-release", metavar="HOLDER",
                   help="displace the named holder; must match the recorded holder exactly")
    g.add_argument("--status", action="store_true", help="report lock state and exit")
    p.add_argument("--fetch", action="store_true",
                   help="update the upstream ref first (a network op: runs under the lock)")
    p.add_argument("--limit", type=int, default=40, help="commits to list (default: %(default)s)")
    return p


def _print_lock_state(path: Path) -> dict | None:
    rec = read_lock(path)
    if rec is None:
        print(f"push lock: FREE  ({path})")
    else:
        print(f"push lock: HELD  ({path})")
        print(describe_holder(rec))
    return rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = Path(args.repo)

    try:
        key = repo_key(repo)
    except (PreflightError, SerializedPushError) as exc:
        print(f"serialized_push: REFUSING — {exc}", file=sys.stderr)
        return EXIT_PREFLIGHT
    path = lock_path(args.lock_dir, key)

    # ---- pure lock operations ------------------------------------------------
    try:
        if args.status:
            _print_lock_state(path)
            return EXIT_OK

        if args.release:
            if release(args.lock_dir, key, args.agent):
                print(f"released push lock for {repo} (key {key})")
            else:
                print(f"(no push lock held for {repo})")
            return EXIT_OK

        if args.force_release:
            rec = force_release(args.lock_dir, key, args.agent, args.force_release)
            print(f"FORCE-RELEASED push lock held by {rec.get('agent')!r} since "
                  f"{rec.get('ts')}; displacement journaled by {args.agent!r}")
            return EXIT_OK
    except (NotHolderError, LockCorruptError) as exc:
        print(f"serialized_push: REFUSING — {exc}", file=sys.stderr)
        return EXIT_LOCKED

    # ---- plan (default) ------------------------------------------------------
    if not args.push and not args.acquire:
        try:
            held = read_lock(path)
        except LockCorruptError as exc:
            print(f"serialized_push: REFUSING — {exc}", file=sys.stderr)
            return EXIT_LOCKED
        if held is not None and held.get("agent") != args.agent:
            print("serialized_push: NOTE another session holds the push lock right now; "
                  "this plan is racing their push.", file=sys.stderr)
            print(describe_holder(held), file=sys.stderr)
        try:
            pf = preflight(repo)
            man = build_manifest(repo, pf)
        except PreflightError as exc:
            print(f"serialized_push: REFUSING — {exc}", file=sys.stderr)
            return EXIT_PREFLIGHT
        print(render_manifest(pf, man, args.limit))
        print("")
        print("DRY RUN — nothing was published. Re-run with --push to publish, "
              "which takes the lock first.")
        return EXIT_OK

    # ---- lock-holding operations (acquire / push) ---------------------------
    try:
        acquire(args.lock_dir, key, args.agent, str(repo),
                mode="hold" if args.acquire else "push")
    except (LockHeldError, LockCorruptError) as exc:
        print(f"serialized_push: REFUSING — {exc}", file=sys.stderr)
        return EXIT_LOCKED

    if args.acquire:
        print(f"acquired push lock for {repo} (key {key}) as {args.agent!r}")
        print("Hold it while you review, then --push (or --release to give it up).")
        return EXIT_OK

    try:
        try:
            pf = preflight(repo, require_fetched=not args.fetch)
        except PreflightError as exc:
            print(f"serialized_push: REFUSING — {exc}", file=sys.stderr)
            return EXIT_PREFLIGHT
        if args.fetch:
            print(do_fetch(repo, pf["remote"], pf["remote_branch"]) or "(fetch: up to date)")
            try:
                pf = preflight(repo)
            except PreflightError as exc:
                print(f"serialized_push: REFUSING — {exc}", file=sys.stderr)
                return EXIT_PREFLIGHT
        man = build_manifest(repo, pf)
        print(render_manifest(pf, man, args.limit))
        if man["ahead"] == 0:
            print("\nNothing to push.")
            return EXIT_OK
        print("")
        print(f"PUSHING as {args.agent!r} under the push lock ...")
        print(do_push(repo, pf))
        print(f"published {man['ahead']} commit(s) to {pf['remote']}/{pf['remote_branch']}")
        return EXIT_OK
    except (PushFailedError, SerializedPushError) as exc:
        print(f"serialized_push: FAILED — {exc}", file=sys.stderr)
        return EXIT_PUSH_FAILED
    finally:
        # Always give the lock back, success or failure: a wedged lock blocks the
        # whole fleet, and a failed push is exactly when the next session needs it.
        try:
            release(args.lock_dir, key, args.agent)
        except (NotHolderError, LockCorruptError) as exc:
            print(f"serialized_push: WARNING lock not released: {exc}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
