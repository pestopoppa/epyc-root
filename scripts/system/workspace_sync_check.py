#!/usr/bin/env python3
"""workspace_sync_check.py — read-only, zero-token check of the shared /workspace clone (NIB2-99).

Reports how far the clone's local `main` is BEHIND and AHEAD of `origin/main` (its own
remote-tracking ref). It never fetches, never checks out, never syncs: it only runs
`git rev-list --left-right --count` and `git status --porcelain=v1`. The remote-tracking ref is as
fresh as the last fetch, so the report carries that ref's age; a stale ref UNDER-counts behind.

Usage: workspace_sync_check.py [--repo /workspace] [--json]
Exit 0 always (warn-only); the alarm lives in host_hygiene_tick.py `workspace_sync`.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def _git(repo: str, *args: str) -> str | None:
    try:
        cp = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return cp.stdout if cp.returncode == 0 else None


def workspace_sync_status(repo: str = "/workspace", branch: str = "main",
                          remote_ref: str = "origin/main") -> dict:
    """Return {ok, behind, ahead, dirty_tracked, head_branch, ref_age_s, error?}. Read-only."""
    out = _git(repo, "rev-list", "--left-right", "--count", f"{remote_ref}...{branch}")
    if out is None:
        return {"ok": False, "error": f"cannot compare {branch} with {remote_ref} in {repo}"}
    try:
        behind, ahead = (int(x) for x in out.split())
    except ValueError:
        return {"ok": False, "error": f"unparseable rev-list output {out!r}"}
    st = _git(repo, "status", "--porcelain=v1", "--untracked-files=no") or ""
    head = (_git(repo, "rev-parse", "--abbrev-ref", "HEAD") or "").strip()
    age = None
    gitdir = (_git(repo, "rev-parse", "--git-common-dir") or "").strip()
    if gitdir:
        ref = Path(repo) / gitdir / "refs" / "remotes" / remote_ref
        try:
            age = int(time.time() - ref.stat().st_mtime)
        except OSError:
            pass  # packed ref: age unknown
    return {"ok": True, "behind": behind, "ahead": ahead, "dirty_tracked": len(st.splitlines()),
            "head_branch": head, "ref_age_s": age}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default="/workspace")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    s = workspace_sync_status(a.repo)
    if a.json:
        print(json.dumps(s))
    elif not s["ok"]:
        print(f"workspace-sync: {s['error']}")
    else:
        print(f"workspace-sync: {a.repo} main is {s['behind']} behind / {s['ahead']} ahead of origin/main "
              f"(HEAD {s['head_branch']}, {s['dirty_tracked']} dirty tracked, ref age {s['ref_age_s']}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
