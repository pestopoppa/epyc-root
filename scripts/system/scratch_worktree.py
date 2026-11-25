#!/usr/bin/env python3
"""scratch_worktree.py - create a SPARSE, marker-carrying scratch worktree of epyc-root.

    python3 scripts/system/scratch_worktree.py add <name> [--ref origin/main] [--full] [--purpose TEXT]
                                                [--repo DIR] [--root DIR]

Why: a full epyc-root checkout is ~1.2 GB (artifacts/ ~0.8 GB) and sessions created one per task and
rarely removed them (disk leak, 2026-11-25). The default checkout is sparse (cone mode) and EXCLUDES
artifacts/ (except operator/ top-level files), benchmarks/ and data/; --full keeps the whole tree.

The worktree gets a `.scratch-worktree` marker (created_by, created_at, purpose). worktree_gate.py and
safety/worktree_reaper.py treat a marked tree as reclaimable once clean, landed and idle 30 min.
The marker is git-excluded so it never dirties the tree. Remove with:
    python3 scripts/system/worktree_gate.py remove <path>
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import subprocess
import sys
import time

MARKER = ".scratch-worktree"
EXCLUDED = ("artifacts", "benchmarks", "data")
# Non-cone patterns: everything except the heavy dirs, plus the TOP-LEVEL files of artifacts/operator/
# (commit hooks such as the observer registry check read ratify_* files there; subdirs hold the bulk).
SPARSE_PATTERNS = ["/*"] + [f"!/{d}/" for d in EXCLUDED] + ["/artifacts/operator/*", "!/artifacts/operator/*/"]
DEFAULT_ROOT = "/mnt/raid0/llm/worktrees"
DEFAULT_REPO = "/mnt/raid0/llm/epyc-root"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _git(cwd, *args):
    cp = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr.strip()[:300]}")
    return cp.stdout


def add(name, *, repo=DEFAULT_REPO, root=DEFAULT_ROOT, ref="origin/main", full=False,
        purpose="", created_by=None):
    if not NAME_RE.match(name):
        raise ValueError(f"bad worktree name {name!r}")
    path = os.path.join(root, name)
    if os.path.exists(path):
        raise FileExistsError(path)
    os.makedirs(root, exist_ok=True)
    _git(repo, "worktree", "add", "--no-checkout", "-b", f"scratch/{name}", path, ref)
    if not full:
        _git(path, "sparse-checkout", "set", "--no-cone", *SPARSE_PATTERNS)
    _git(path, "checkout")
    # keep the marker out of `git status` (info/exclude is read from the common dir)
    common = _git(path, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    exc = os.path.join(common, "info", "exclude")
    os.makedirs(os.path.dirname(exc), exist_ok=True)
    cur = open(exc).read() if os.path.exists(exc) else ""
    if f"/{MARKER}" not in cur.splitlines():
        with open(exc, "a") as fh:
            fh.write(("" if cur.endswith("\n") or not cur else "\n") + f"/{MARKER}\n")
    meta = {"created_by": created_by or os.environ.get("EPYC_AGENT") or getpass.getuser(),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "purpose": purpose or "scratch", "sparse": not full}
    with open(os.path.join(path, MARKER), "w") as fh:
        json.dump(meta, fh)
        fh.write("\n")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("name")
    a.add_argument("--ref", default="origin/main")
    a.add_argument("--full", action="store_true")
    a.add_argument("--purpose", default="")
    a.add_argument("--repo", default=DEFAULT_REPO)
    a.add_argument("--root", default=DEFAULT_ROOT)
    a.add_argument("--created-by", default=None)
    ns = ap.parse_args(argv)
    try:
        print(add(ns.name, repo=ns.repo, root=ns.root, ref=ns.ref, full=ns.full,
                  purpose=ns.purpose, created_by=ns.created_by))
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"scratch_worktree: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
