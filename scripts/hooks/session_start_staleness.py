#!/usr/bin/env python3
"""SessionStart notice: say when this checkout is far behind origin/main (AK audit C5, 2026-11-20).

Evidence (audit section 2.4): sessions in a stale shared clone ran tools and read docs that
origin/main had already replaced, then reasoned from the old copies. One line at birth:

    checkout is N commits behind origin/main; use the hub view for tools

emitted as additionalContext only when N > THRESHOLD (default 50, env EPYC_STALE_THRESHOLD).
Uses the LOCAL origin/main ref (no fetch: a SessionStart hook must stay fast and offline-safe),
so N is a lower bound. WARN ONLY: never blocks, never touches the tree, exits 0 on every path,
silent on any error or when the repo has no origin/main.
"""
import json
import os
import subprocess
import sys

THRESHOLD = 50


def behind(cwd):
    """Commits on origin/main not in HEAD, or None when undeterminable."""
    try:
        out = subprocess.run(["git", "-C", cwd, "rev-list", "--count", "HEAD..origin/main"],
                             capture_output=True, text=True, timeout=5)
    except Exception:
        return None
    if out.returncode != 0:
        return None
    try:
        return int(out.stdout.strip())
    except ValueError:
        return None


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    cwd = (payload.get("cwd") if isinstance(payload, dict) else None) or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        threshold = int(os.environ.get("EPYC_STALE_THRESHOLD", THRESHOLD))
    except ValueError:
        threshold = THRESHOLD
    n = behind(cwd)
    if n is None or n <= threshold:
        return 0
    json.dump({"suppressOutput": True, "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": (f"STALE CHECKOUT: checkout is {n} commits behind origin/main (local ref; "
                              f"run `git fetch` for the true count); use the hub view (origin/main) for tools "
                              f"and docs, and do not reason from this tree's copies until you are on a fresh "
                              f"worktree."),
    }}, sys.stdout)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
