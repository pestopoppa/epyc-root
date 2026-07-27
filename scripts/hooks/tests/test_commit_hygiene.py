#!/usr/bin/env python3
"""Tests for scripts/hooks/check_commit_hygiene.py (rider R7a).

The interesting cases are the false-positive ones: a commit MESSAGE that
mentions -A, --all or -a must not be mistaken for the flag. The first draft of
this hook used regex and failed exactly there, which is why the implementation
tokenises with shlex.

Usage: scripts/hooks/tests/test_commit_hygiene.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "scripts" / "hooks" / "check_commit_hygiene.py"
FRESH = {"EPYC_FETCH_MAX_AGE_S": "999999999"}   # neutralise rule B for rule-A cases
STALE = {"EPYC_FETCH_MAX_AGE_S": "0"}           # force rule B


def run(cmd: str, env: dict | None = None) -> int:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
        capture_output=True, text=True, cwd=str(REPO_ROOT),
        env={**os.environ, "CLAUDE_PROJECT_DIR": str(REPO_ROOT), **(env or {})},
    ).returncode


# (command, expected_rc, env, description)
CASES: list[tuple[str, int, dict, str]] = [
    # ---- rule A: wholesale staging must BLOCK ----
    ("git add -A", 2, FRESH, "git add -A"),
    ("git add --all", 2, FRESH, "git add --all"),
    ("git add .", 2, FRESH, "git add ."),
    ("git add -u", 2, FRESH, "git add -u"),
    ("git -C /workspace add -A", 2, FRESH, "-C shared repo + add -A"),
    ('git commit -am "msg"', 2, FRESH, "git commit -am"),
    ('git commit -a -m "msg"', 2, FRESH, "git commit -a -m"),
    ('git commit --all -m "msg"', 2, FRESH, "git commit --all"),
    ("cd /workspace && git add -A", 2, FRESH, "cd into shared repo then add -A"),

    # ---- FALSE POSITIVES the regex draft got wrong: must ALLOW ----
    ('git commit -m "add -A to the docs"', 0, FRESH, "message mentions -A"),
    ('git commit -m "stage -a everything, we discussed"', 0, FRESH, "message mentions -a"),
    ('git commit -m "use --all sparingly"', 0, FRESH, "message mentions --all"),
    ('git commit -m "git add . is banned"', 0, FRESH, "message contains the whole banned form"),
    ("git commit --amend --no-edit", 0, FRESH, "--amend must not match the -a cluster"),

    # ---- ordinary work must ALLOW ----
    ("git add path/one path/two", 0, FRESH, "explicit paths"),
    ("git add ./scripts/foo.py", 0, FRESH, "relative path starting with ./"),
    ('git commit -m "msg"', 0, FRESH, "plain commit, fresh fetch"),
    ("git status", 0, FRESH, "git status"),
    ("git diff --cached --name-only", 0, FRESH, "inspecting the staged set"),
    ("git log --oneline -3", 0, FRESH, "git log"),
    ("git add -p", 0, FRESH, "patch-mode add is not wholesale"),

    # ---- sandbox / non-shared repos must ALLOW ----
    ("cd /tmp/sandbox && git add -A", 0, FRESH, "sandbox repo: add -A allowed"),
    ("git -C /tmp/sandbox add -A", 0, FRESH, "-C sandbox: add -A allowed"),
    ('cd /tmp/sb && git commit -am "x"', 0, FRESH, "sandbox: commit -am allowed"),

    # ---- rule B: an in-command fetch satisfies freshness ----
    ("git fetch && git commit -m \"x\"", 0, STALE, "fetch THEN commit in one command is allowed"),
    ("git fetch -q && git add a b && git commit -m \"x\"", 0, STALE, "fetch, add, commit chain"),
    ("git -C /workspace fetch && git -C /workspace commit -m \"x\"", 0, STALE,
     "explicit -C on both"),
    ("git commit -m \"x\" && git fetch", 2, STALE, "fetch AFTER commit does not count"),
    ('git commit -m \"remember to git fetch first\"', 2, STALE,
     "a fetch mentioned in the MESSAGE does not count"),
    ("git -C /mnt/raid0/llm/epyc-orchestrator fetch && git commit -m \"x\"", 2, STALE,
     "fetching a DIFFERENT repo does not satisfy this one"),

    # ---- rule B: stale fetch ----
    ('git commit -m "msg"', 2, STALE, "commit with stale fetch blocks"),
    ("git add path/one", 0, STALE, "add is unaffected by fetch age"),
    ("git status", 0, STALE, "status unaffected by fetch age"),
]


def main() -> int:
    failures: list[str] = []
    for cmd, expect, env, why in CASES:
        rc = run(cmd, env)
        ok = rc == expect
        print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want={expect}  {why}")
        if not ok:
            failures.append(f"{why} ({cmd!r})")

    rc = run("git add -A", {**FRESH, "EPYC_ALLOW_COMMIT_HYGIENE_BYPASS": "1"})
    ok = rc == 0
    print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want=0  explicit operator override")
    if not ok:
        failures.append("override")

    # Malformed quoting must not crash or block.
    rc = run('git commit -m "unterminated', FRESH)
    ok = rc == 0
    print(f"  {'PASS' if ok else 'FAIL'}  rc={rc} want=0  malformed quoting degrades open")
    if not ok:
        failures.append("malformed quoting")

    print(f"\n{'FAILED: ' + '; '.join(failures) if failures else 'all checks passed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
