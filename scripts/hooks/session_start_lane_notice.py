#!/usr/bin/env python3
"""SessionStart notice: tell a session, at birth, that it is in the shared clone.

WHY THIS EXISTS. `scripts/coordination/check_lane_worktree.py` has always been able
to detect this (exit 3 = shared clone). Nothing consumed it, so it only ever got run
by a session that already suspected it was in the wrong place — which is the wrong
population. Every lane-discipline incident recorded so far shares one precondition:
the session never knew it was in the shared clone.

Measured 2026-08-20, one session, one day, all four with the same root cause:
  * a peer's pre-staged file swept into four separate commits (each repair
    re-staged it, re-arming the next plain `git commit`);
  * a `git checkout -- <path>` written as a speculative "would this happen?" check
    actually ran, wiping BOTH that session's edits and a peer's uncommitted work
    (no reflog, no conflict, recovered only from an incidental copy).
In a lane worktree the working tree and index are private, so neither is reachable.

WHAT IT DOES NOT DO. It never blocks, never changes cwd, and never touches git. It
emits `additionalContext` so the model reads the constraint before its first tool
call, and exits 0 unconditionally: a hook that can fail a session start is a worse
outage than the hazard it guards. On any internal error it stays silent.

Contract: stdin = SessionStart payload JSON (unused); stdout = hook JSON or nothing.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

CHECK = "scripts/coordination/check_lane_worktree.py"
SHARED_CLONE_EXIT = 3


def repo_root() -> Path | None:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and (Path(env) / CHECK).is_file():
        return Path(env)
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except Exception:
        return None
    if top and (Path(top) / CHECK).is_file():
        return Path(top)
    return None


def main() -> int:
    root = repo_root()
    if root is None:
        return 0                                   # not our repo -> silent
    try:
        proc = subprocess.run(
            [sys.executable, str(root / CHECK), "--strict"],
            capture_output=True, text=True, timeout=20, cwd=str(root),
        )
    except Exception:
        return 0                                   # never fail a session start
    if proc.returncode != SHARED_CLONE_EXIT:
        return 0                                   # in a lane, or undeterminable -> silent

    detail = (proc.stdout or "").strip()
    notice = f"""LANE WORKTREE NOTICE — this session started in the SHARED CLONE, not a lane worktree.

{detail}

Every roster main owns /mnt/raid0/llm/worktrees/mains/<agent> on lane/<agent>. Here, the
working tree AND the git index are shared with every other session on this host, so:

  * a plain `git commit` commits whatever is in the index INCLUDING a peer's staged files;
  * `git commit -- <path>` bypasses the index and sweeps a peer's uncommitted hunks in that
    same file;
  * `git checkout/restore -- <path>` reverts a peer's uncommitted work with no conflict and
    NO REFLOG;
  * `git stash` is unsafe while daemons write to logs/ and coordination/session-bus/.

BEFORE any work-plane edit (handoffs/, progress/, scripts/, docs/, wiki/), move to your lane:

    python3 scripts/coordination/check_lane_worktree.py --strict   # 0 ok, 3 shared clone
    cd /mnt/raid0/llm/worktrees/mains/<agent>                      # your lane

Runtime-plane writes (coordination/session-bus/, logs/) are CORRECT here and need no lane.

If you have no lane (operator-spawned or ad-hoc session), you may continue — but you MUST
stage hunk-selectively and inspect `git diff -- <file>` before every commit and every revert,
because none of the protections above apply to you. Say so in your wrap-up.

Never run `git worktree prune` or `git gc` in this repo — they destroyed all five lanes on
2026-08-12."""

    json.dump({
        "suppressOutput": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": notice,
        },
    }, sys.stdout)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)                                # belt and braces: never block a start
