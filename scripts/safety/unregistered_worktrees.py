#!/usr/bin/env python3
"""unregistered_worktrees.py - classify UNREGISTERED directories under /mnt/raid0/llm/worktrees (read-only).

    unregistered_worktrees.py [--root DIR] [--min-idle-h 24] [--out FILE]

Never deletes. Classes (first match wins): MAINS (worktrees/mains, never touched), REGISTERED (skipped), PENDING
(pending_refs keep rule), BUSY (live cwd inside), RECENT (newest mtime < --min-idle-h; future mtimes are SKEW, untrusted),
then, for a dir with a `.git`:
  ORPHAN-GIT-CLEAN-PUSHED   standalone `.git` dir (or a gitdir that exists), clean tree, 0 commits outside remote refs
  ORPHAN-GIT-UNVERIFIABLE   `.git` file whose gitdir is gone, or any git error: cannot prove pushed -> keep
  GIT-UNPUSHED / GIT-DIRTY  keep
and for a plain dir: PLAIN-MATCHES-PUSHED when EVERY file equals (same relative path, same blob) a file of origin/main of
one of the 4 repos (and the dir has files), else UNKNOWN (keep). Only *-PUSHED / PLAIN-MATCHES-PUSHED are reclaimable.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pending_refs  # noqa: E402
import worktree_reaper as wr  # noqa: E402

ROOT = "/mnt/raid0/llm/worktrees"
FILE_CAP = 100000
BYTE_CAP = 1 << 30   # hash at most 1 GiB per plain dir
RECLAIMABLE = ("ORPHAN-GIT-CLEAN-PUSHED", "PLAIN-MATCHES-PUSHED")


def registered_paths(repos):
    s = set()
    for r in repos:
        for w in wr.list_worktrees(r):
            if w["path"]:
                s.add(os.path.realpath(w["path"]))
    return s


def du(path):
    r = subprocess.run(["du", "-sk", path], capture_output=True, text=True)
    try:
        return int(r.stdout.split()[0]) * 1024
    except (IndexError, ValueError):
        return 0


def origin_blobs(repos):
    """{(relpath, blob)} over origin default branch of every repo (lazy per repo)."""
    out = {}
    for r in repos:
        base = wr.base_ref(r)
        if not base:
            continue
        rc, txt, _ = wr.git(r, "ls-tree", "-r", base, timeout=300)
        if rc == 0:
            out[r] = {(ln.split("\t", 1)[1], ln.split()[2]) for ln in txt.splitlines() if "\t" in ln}
    return out


def plain_matches(path, blobs):
    files, total = [], 0
    for dp, dns, fns in os.walk(path):
        for f in fns:
            fp = os.path.join(dp, f)
            files.append(os.path.relpath(fp, path))
            try:
                total += os.lstat(fp).st_size
            except OSError:
                return False
            if len(files) > FILE_CAP or total > BYTE_CAP:
                return False   # too big to prove cheaply: stays UNKNOWN (keep)
    if not files:
        return False
    r = subprocess.run(["git", "hash-object", "--stdin-paths"], input="\n".join(os.path.join(path, f) for f in files),
                       capture_output=True, text=True, cwd=path)
    if r.returncode != 0:
        return False
    hs = r.stdout.split()
    if len(hs) != len(files):
        return False
    mine = set(zip(files, hs))
    return any(mine <= b for b in blobs.values())


def classify(path, *, registered, pending, now, min_idle_s, blobs, root=ROOT, proc_root="/proc"):
    rp = os.path.realpath(path)
    if rp == os.path.realpath(os.path.join(root, "mains")):
        return "MAINS", "worktrees/mains is never touched"
    if rp in registered:
        return "REGISTERED", "registered worktree (reaper's scope)"
    pr = pending.check(path)
    if pr:
        return "PENDING", pr
    gitp = os.path.join(path, ".git")
    newest, future = wr.tree_mtimes(path, now, None)
    if future:
        return "SKEW", "mtime in the future; untrusted"
    if (now - newest) < min_idle_s:
        return "RECENT", f"idle {(now - newest) / 3600:.1f}h"
    if wr.cwd_inside(path, proc_root):
        return "BUSY", "live cwd inside"
    if os.path.lexists(gitp):
        if os.path.isfile(gitp):
            gd = open(gitp).read().strip().replace("gitdir:", "").strip()
            if not os.path.isabs(gd):
                gd = os.path.normpath(os.path.join(path, gd))   # a relative gitdir is relative to the worktree, not to our cwd
            if not os.path.isdir(gd):
                return "ORPHAN-GIT-UNVERIFIABLE", "gitdir file points at a missing dir"
        rc, out, _ = wr.git(path, "status", "--porcelain")
        if rc != 0:
            return "ORPHAN-GIT-UNVERIFIABLE", "git status failed"
        if out.strip():
            return "GIT-DIRTY", f"{len(out.splitlines())} entries"
        rc, out, _ = wr.git(path, "rev-list", "--count", "HEAD", "--not", "--remotes")
        if rc != 0:
            return "ORPHAN-GIT-UNVERIFIABLE", "rev-list failed"
        if out.strip() != "0":
            return "GIT-UNPUSHED", f"{out.strip()} commits outside remote refs"
        return "ORPHAN-GIT-CLEAN-PUSHED", "clean, 0 unpushed"
    if plain_matches(path, blobs):
        return "PLAIN-MATCHES-PUSHED", "every file equals a blob of origin's default branch"
    return "UNKNOWN", "plain dir not provably in a pushed commit"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--min-idle-h", type=float, default=24.0)
    ap.add_argument("--out")
    ap.add_argument("--flags", default=pending_refs.DEFAULT_FLAGS)
    a = ap.parse_args(argv)
    repos = [r for r in wr.DEFAULT_REPOS if os.path.isdir(r)]
    reg = registered_paths(repos)
    pend = pending_refs.PendingIndex(flags=a.flags)
    blobs = origin_blobs(repos)
    now = time.time()
    rows, tot = [], {}
    for n in sorted(os.listdir(a.root)):
        p = os.path.join(a.root, n)
        if not os.path.isdir(p) or os.path.islink(p):
            continue
        v, why = classify(p, registered=reg, pending=pend, now=now, min_idle_s=a.min_idle_h * 3600, blobs=blobs, root=a.root)
        if v in ("REGISTERED",):
            continue
        sz = du(p)
        rows.append((v, p, sz, why))
        tot[v] = tot.get(v, 0) + sz
    lines = [f"UNREG {v} {p} bytes={sz} :: {why}" for v, p, sz, why in rows]
    lines += [f"UNREG-TOTAL {v} {b / 2**30:.1f}G{' RECLAIMABLE' if v in RECLAIMABLE else ''}" for v, b in sorted(tot.items())]
    text = "\n".join(lines)
    if a.out:
        open(a.out, "w").write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
