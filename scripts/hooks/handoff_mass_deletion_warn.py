#!/usr/bin/env python3
"""Warn-only pre-commit check: a staged change that deletes a large share of a handoff.

WHY: commit 465954bc0 (2026-10-07) was titled as adding one task to
handoffs/active/kv-unified-stack-rollout.md but changed it +12/-892 (1234 -> 354 lines): a stale-base
overwrite that silently dropped about 50 task bodies. Nothing flagged it, and the ids dangled for two weeks.

RULE: for every staged MODIFIED handoffs/active/*.md, warn when the commit deletes more than
THRESHOLD (30%) of the file's lines (and at least MIN_DELETED lines) and fewer than that many of the deleted
lines reappear as added lines in handoffs/completed|archived/ files of the same commit (a legitimate move).
Never blocks: always exits 0. Bypass is not needed because nothing is refused.
"""
from __future__ import annotations

import subprocess
import sys
from collections import Counter

THRESHOLD = 0.30
MIN_DELETED = 40
MOVE_DIRS = ("handoffs/completed/", "handoffs/archived/")


def evaluate(old_line_count: int, deleted: int, moved: int) -> str | None:
    """Return a warning string, or None. `moved` = deleted lines re-added under completed/archived."""
    if old_line_count <= 0 or deleted < MIN_DELETED:
        return None
    unexplained = max(deleted - moved, 0)
    if unexplained / old_line_count <= THRESHOLD:
        return None
    return (f"deletes {deleted} of {old_line_count} lines ({deleted / old_line_count:.0%}); "
            f"only {moved} reappear under handoffs/completed|archived in this commit")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout


def _diff_lines(path: str) -> tuple[list[str], list[str]]:
    removed, added = [], []
    for ln in _git("diff", "--cached", "-U0", "--", path).splitlines():
        if ln.startswith("---") or ln.startswith("+++"):
            continue
        if ln.startswith("-"):
            removed.append(ln[1:])
        elif ln.startswith("+"):
            added.append(ln[1:])
    return removed, added


def main() -> int:
    names = _git("diff", "--cached", "--name-status", "--diff-filter=MD").splitlines()
    mod = [n.split("\t", 1)[1] for n in names
           if n.startswith("M") and n.split("\t", 1)[1].startswith("handoffs/active/")
           and n.endswith(".md")]
    if not mod:
        return 0
    pool: Counter = Counter()
    for n in _git("diff", "--cached", "--name-only").splitlines():
        if n.startswith(MOVE_DIRS):
            pool.update(_diff_lines(n)[1])
    for path in mod:
        removed, _ = _diff_lines(path)
        old_n = len(_git("show", f"HEAD:{path}").splitlines())
        moved = sum(1 for ln in removed if ln.strip() and pool[ln] > 0)
        msg = evaluate(old_n, len(removed), moved)
        if msg:
            print(f"WARNING (handoff-mass-deletion, warn-only): {path} {msg}. If this is a stale-base "
                  f"overwrite, restore with: git show HEAD:{path} (compare before committing).",
                  file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # warn-only: an internal failure must never block a commit
        print(f"WARNING (handoff-mass-deletion, warn-only): check skipped: {exc!r}", file=sys.stderr)
    sys.exit(0)
