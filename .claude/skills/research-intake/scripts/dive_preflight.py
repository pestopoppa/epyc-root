#!/usr/bin/env python3
"""Stage-2 dive preflight (ID-RI-LANE-HEAD). Run by main BEFORE dispatching a dive.

Asserts the named root is a lane worktree (a linked worktree, not the shared clone) and that its
HEAD is not behind origin/main. Prints the full `lane_head` SHA the dive must echo in its YAML.
Exit 0 = ok, 1 = refused (typed reason on stdout).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _git(root: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def preflight(root: Path, upstream: str = "origin/main") -> tuple[bool, str, str | None]:
    """Returns (ok, reason, lane_head)."""
    rc, top = _git(root, "rev-parse", "--show-toplevel")
    if rc != 0:
        return False, "not_a_git_root", None
    rc1, gitdir = _git(root, "rev-parse", "--absolute-git-dir")
    rc2, common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if rc1 != 0 or rc2 != 0:
        return False, "git_dir_unresolvable", None
    if Path(gitdir).resolve() == Path(common).resolve():
        return False, "shared_clone_not_lane_worktree", None
    rc, head = _git(root, "rev-parse", "HEAD")
    if rc != 0:
        return False, "no_head", None
    rc, behind = _git(root, "rev-list", "--count", f"HEAD..{upstream}")
    if rc != 0:
        return False, f"upstream_unresolvable:{upstream}", head
    if int(behind) > 0:
        return False, f"head_behind_{upstream}_by_{behind}", head
    return True, "ok", head


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--upstream", default="origin/main")
    ap.add_argument("--fetch", action="store_true", help="git fetch the upstream remote first")
    a = ap.parse_args()
    if a.fetch:
        _git(a.root, "fetch", "-q", a.upstream.split("/")[0])
    ok, reason, head = preflight(a.root, a.upstream)
    print(f"{'OK' if ok else 'REFUSED'}: {reason}" + (f" lane_head={head}" if head else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
