#!/usr/bin/env python3
"""D9 commit-size guard (operator-approved 2026-11-18) for Codex handoff-lane commits.

Scope: the branch is `h-*` or `lane/h-*`, or EPYC_CODEX_WRAPUP=1 (set by scripts/coordination/churn/wrapup.py on its
wrap-up commit). Any other commit passes untouched.

Refuses a commit that
  (a) adds the same blob content at 2+ new paths;
  (b) adds a single file over MAX_FILE_LINES lines;
  (c) adds more than MAX_EVIDENCE_LINES lines in total under evidence/packet-like paths (EVIDENCE_PATTERNS).
Origin: 53249a8a5 (one 13,422-line llama.cpp source copied 3x into data/vidya/.../packet/source), 4795cb2dd and
169788167 (hundreds of capture/native-run files under data/vidya/). Generated files in EXEMPT are never counted.
Reads exactly the index being committed (git sets GIT_INDEX_FILE for pathspec and private-index commits).
"""
from __future__ import annotations

import fnmatch
import os
import subprocess
import sys

MAX_FILE_LINES = 2000
MAX_EVIDENCE_LINES = 20000
DUP_MIN_LINES = 2  # rule (a) ignores blobs of <= 2 lines: 4795cb2dd has 37 empty stderr files sharing blob e69de29
EVIDENCE_PATTERNS = ("*/packet/*", "packet/*", "*/evidence/*", "evidence/*", "artifacts/compute/*", "data/vidya/*",
                     "*/capture/*", "*/native-run/*", "*/receipts/*", "*/failed-qualification-*/*")
EXEMPT = ("handoffs/active/.index-*.json", "wiki/source_manifest.json")
BRANCH_PATTERNS = ("h-*", "lane/h-*")
HINT = ("Cite the file by repo path + SHA-256 (or the source repo commit) instead of copying it into the commit.")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout


def in_scope(branch: str, env=None) -> bool:
    env = os.environ if env is None else env
    return env.get("EPYC_CODEX_WRAPUP") == "1" or any(fnmatch.fnmatchcase(branch, p) for p in BRANCH_PATTERNS)


def exempt(path: str) -> bool:
    return any(fnmatch.fnmatchcase(path, p) for p in EXEMPT)


def evidence(path: str) -> bool:
    return any(fnmatch.fnmatchcase(path, p) for p in EVIDENCE_PATTERNS)


def staged() -> list[tuple[str, str, int, int]]:
    """(status, path, added_lines, blob) rows; blob is the staged object id for A, '' otherwise."""
    blobs = {}
    raw = _git("diff", "--cached", "--raw", "--no-renames", "--diff-filter=AM", "-z").split("\0")
    i = 0
    while i + 1 < len(raw):
        meta, path = raw[i].lstrip(":"), raw[i + 1]
        parts = meta.split()
        if len(parts) >= 5:
            blobs[path] = (parts[4], parts[3])  # status, new blob
        i += 2
    rows = []
    for l in _git("diff", "--cached", "--numstat", "--no-renames", "--diff-filter=AM", "-z").split("\0"):
        f = l.split("\t", 2)
        if len(f) != 3 or f[2] not in blobs:
            continue
        add = int(f[0]) if f[0].isdigit() else 0  # '-' = binary
        st, blob = blobs[f[2]]
        rows.append((st, f[2], add, blob))
    return rows


def check(rows) -> list[str]:
    errs, by_blob, ev_total, ev_files = [], {}, 0, 0
    for st, path, add, blob in rows:
        if exempt(path):
            continue
        if st == "A" and add > DUP_MIN_LINES:  # empty / 1-2 line markers (rc files, empty stderr) are not copies
            by_blob.setdefault(blob, []).append(path)
        if add > MAX_FILE_LINES:
            errs.append(f"(b) {path} adds {add} lines > {MAX_FILE_LINES}")
        if evidence(path):
            ev_total += add
            ev_files += 1
    for blob, paths in by_blob.items():
        if len(paths) >= 2:
            errs.append(f"(a) identical content (blob {blob[:12]}) added at {len(paths)} new paths: " + ", ".join(paths[:6]))
    if ev_total > MAX_EVIDENCE_LINES:
        errs.append(f"(c) {ev_total} lines added under evidence/packet paths in {ev_files} file(s) > {MAX_EVIDENCE_LINES}")
    return errs


def main(argv=None) -> int:
    branch = _git("symbolic-ref", "--short", "-q", "HEAD").strip()
    if not in_scope(branch):
        return 0
    errs = check(staged())
    if not errs:
        return 0
    print(f"check_commit_bloat: REFUSED commit on {branch or '(detached)'} (D9 commit-size guard):", file=sys.stderr)
    for e in errs:
        print(f"  {e}", file=sys.stderr)
    print(f"  {HINT}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
