#!/usr/bin/env python3
"""worktree_reaper.py - deterministic, no-LLM reaper for LANDED, CLEAN, IDLE git worktrees.

    worktree_reaper.py [--apply] [--min-idle-h 24] [--repo DIR ...] [--only-list FILE] [--keep-list FILE]
                       [--protect-prefix DIR ...] [--fetch] [--max N] [--json]

Dry run by default; --apply acts. Operator 2026-11-21 ("Safe-now + guards"). A registered linked worktree is
REMOVED only when EVERY check passes; the first failing check is the reported reason and the tree is left alone:

  PROTECTED   path under a --protect-prefix (default /mnt/raid0/llm/worktrees/mains), or on a --keep-list, or locked,
              or the repo's own main checkout
  MISSING     registered but absent on disk (reported, never pruned)
  PENDING     referenced by pending work (pending_refs.referenced_by_pending): a ready/parked/held/armed/dryrun row spec,
              a handoff box, a pre-arm/hold file or launcher, or an unfiled row id naming its path, basename or branch
              (prepped tasks waiting on a reboot / hold release look stale but are not; operator 2026-11-21)
  UNLANDED    HEAD is NOT an ancestor of the repo's origin default branch AND (the branch is not on origin OR commits
              exist that no remote-tracking ref contains)
  DIRTY       `git status --porcelain` (untracked INCLUDED) is not empty
  SKEW        a file mtime lies in the future (> now + 5 min): reported, never trusted (the clock-skewed tree whose
              mtime said 2030 would otherwise read as "never idle" or, trusted the other way, "idle for years")
  RECENT      newest mtime anywhere in the tree (and its git admin dir) is younger than --min-idle-h (default 24)
  BUSY        a live process has its cwd inside the tree (/proc/*/cwd), or the reaper itself is inside it
  REAP        all of the above passed

--apply removes with `git -C <repo> worktree remove <path>` (NEVER --force, NEVER `worktree prune`), then deletes the
local branch with `git branch -d` only when it is merged (-d, never -D). Unregistered plain directories are out of scope.
--fetch runs `git fetch origin` per repo first (timeout 300 s; a failed fetch skips that repo: fail closed).
--only-list restricts candidates to the listed absolute paths (one per line). Exit 0 on a completed pass.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pending_refs  # noqa: E402

DEFAULT_REPOS = ["/workspace", "/mnt/raid0/llm/epyc-inference-research", "/mnt/raid0/llm/epyc-orchestrator",
                 "/mnt/raid0/llm/llama.cpp"]
DEFAULT_PROTECT = ["/mnt/raid0/llm/worktrees/mains"]
SKEW_SLACK_S = 300


def git(repo, *args, timeout=120):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def under(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root.rstrip("/") + "/")


def list_worktrees(repo):
    """[{path, head, branch|None, locked, prunable}] for every worktree except the first (the main checkout)."""
    rc, out, _ = git(repo, "worktree", "list", "--porcelain")
    if rc != 0:
        return []
    blocks, cur = [], {}
    for ln in out.splitlines() + [""]:
        if not ln.strip():
            if cur:
                blocks.append(cur)
            cur = {}
            continue
        k, _, v = ln.partition(" ")
        cur[k] = v
    res = []
    for b in blocks[1:]:
        br = b.get("branch")
        res.append({"path": b.get("worktree"), "head": b.get("HEAD"),
                    "branch": br[len("refs/heads/"):] if br and br.startswith("refs/heads/") else None,
                    "locked": "locked" in b, "prunable": "prunable" in b})
    return res


def base_ref(repo):
    rc, out, _ = git(repo, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    if rc == 0 and out.strip():
        return out.strip()
    for c in ("origin/main", "origin/master"):
        if git(repo, "rev-parse", "-q", "--verify", c)[0] == 0:
            return c
    return None


def landed(repo, wt, base):
    """(ok, why). Merged into origin's default branch, or branch on origin with no unpushed commits."""
    if base and git(repo, "merge-base", "--is-ancestor", wt["head"], base)[0] == 0:
        return True, f"ancestor of {base}"
    br = wt["branch"]
    if br and git(repo, "rev-parse", "-q", "--verify", f"refs/remotes/origin/{br}")[0] == 0:
        rc, out, _ = git(wt["path"], "rev-list", "--count", "HEAD", "--not", "--remotes")
        if rc == 0 and out.strip() == "0":
            return True, f"branch {br} on origin, 0 unpushed"
        return False, f"{out.strip() or '?'} unpushed commits"
    return False, "not merged and branch not on origin"


def dirty(wt_path):
    r = subprocess.run(["git", "--no-optional-locks", "-C", wt_path, "status", "--porcelain"], capture_output=True, text=True, timeout=600)
    rc, out, err = r.returncode, r.stdout, r.stderr
    if rc != 0:
        return f"status failed: {err.strip()[:80]}"
    return out.strip() or None


def tree_mtimes(path, now, gitdir=None):
    """(newest non-future mtime, newest future mtime or None). Walks the whole tree incl. .git entry and git admin dir."""
    newest, future = 0.0, None

    def see(t):
        nonlocal newest, future
        if t > now + SKEW_SLACK_S:
            future = max(future or 0.0, t)
        else:
            newest = max(newest, t)

    roots = [path] + ([gitdir] if gitdir and os.path.isdir(gitdir) else [])
    for root in roots:
        if root != gitdir:   # the git admin dir's own mtime moves whenever index.lock is created: not activity
            try:
                see(os.lstat(root).st_mtime)
            except OSError:
                continue
        for dp, dns, fns in os.walk(root, followlinks=False):
            for n in dns + fns:
                if root == gitdir and dp == gitdir and n in ("index", "index.lock"):
                    continue   # `git status` (ours or anyone's) rewrites the index: its mtime is not activity
                try:
                    see(os.lstat(os.path.join(dp, n)).st_mtime)
                except OSError:
                    pass
    return newest, future


def cwd_inside(path, proc_root="/proc"):
    """First 'pid:cwd' whose cwd is inside path (own pid and its ancestors excluded only when not inside), else None."""
    rp = os.path.realpath(path)
    try:
        pids = [p for p in os.listdir(proc_root) if p.isdigit()]
    except OSError:
        return None
    for pid in pids:
        try:
            c = os.readlink(f"{proc_root}/{pid}/cwd")
        except OSError:
            continue
        if c == rp or c.startswith(rp + "/"):
            return f"{pid}:{c}"
    return None


def read_list(p):
    out = set()
    if p:
        with open(p) as fh:
            for ln in fh:
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    out.add(os.path.realpath(ln))
    return out


def classify(repo, wt, base, *, now, min_idle_s, protect, keep, only, proc_root="/proc", pending=None):
    """-> (verdict, reason, extra dict)."""
    p = wt["path"]
    if only is not None and os.path.realpath(p) not in only:
        return "OUT-OF-SCOPE", "not in --only-list", {}
    if not os.path.isdir(p):
        return "MISSING", "registered path absent on disk (stale registration; not pruned)", {}
    rp = os.path.realpath(p)
    for pr in protect:
        if under(p, pr):
            return "PROTECTED", f"under {pr}", {}
    if rp in keep:
        return "PROTECTED", "on keep list", {}
    if wt["locked"]:
        return "PROTECTED", "locked worktree", {}
    if pending is not None:
        pr = pending.check(p, wt["branch"])
        if pr:
            return "PENDING", pr, {}
    ok, why = landed(repo, wt, base)
    if not ok:
        return "UNLANDED", why, {}
    rc, gd, _ = git(p, "rev-parse", "--git-dir")
    gitdir = os.path.realpath(os.path.join(p, gd.strip())) if rc == 0 else None
    newest, future = tree_mtimes(p, now, gitdir)
    if future:
        return "SKEW", f"mtime in the future ({time.strftime('%Y-%m-%d', time.gmtime(future))}); untrusted, not acted on", {}
    d = dirty(p)
    if d:
        return "DIRTY", f"{len(d.splitlines())} porcelain entries: {d.splitlines()[0][:80]}", {}
    idle_h = (now - newest) / 3600
    if idle_h < min_idle_s / 3600:
        return "RECENT", f"idle {idle_h:.1f}h < {min_idle_s / 3600:g}h", {"idle_h": round(idle_h, 1)}
    me = cwd_inside(p, proc_root)
    if me:
        return "BUSY", f"live cwd {me}", {}
    if rp == os.path.realpath(os.getcwd()) or os.path.realpath(os.getcwd()).startswith(rp + "/"):
        return "BUSY", "reaper cwd inside", {}
    return "REAP", f"{why}; clean; idle {idle_h:.1f}h", {"idle_h": round(idle_h, 1)}


def remove(repo, wt, base):
    """git worktree remove (no --force), then branch -d when merged. -> (ok, note)."""
    rc, _, err = git(repo, "worktree", "remove", wt["path"], timeout=1800)
    if rc != 0 or os.path.exists(wt["path"]):
        return False, f"worktree remove failed rc={rc}: {err.strip()[:200]}"
    note = "removed"
    br = wt["branch"]
    if br:
        merged = base and git(repo, "merge-base", "--is-ancestor", f"refs/heads/{br}", base)[0] == 0
        if merged:
            r2, _, e2 = git(repo, "branch", "-d", br)
            note += " +branch-d" if r2 == 0 else f" (branch -d refused: {e2.strip()[:80]})"
        else:
            note += " (branch kept: not merged)"
    return True, note


def run(repos, *, apply=False, min_idle_h=24.0, protect=None, keep=None, only=None, fetch=False, max_n=None,
        now=None, proc_root="/proc", log=print, pending=None):
    now = time.time() if now is None else now
    protect = DEFAULT_PROTECT if protect is None else protect
    recs, removed = [], 0
    for repo in repos:
        if not os.path.isdir(repo):
            continue
        if fetch:
            try:
                rc, _, err = git(repo, "fetch", "--quiet", "origin", timeout=300)
            except subprocess.TimeoutExpired:
                rc, err = 1, "timeout"
            if rc != 0:
                log(f"WTREAP-FETCH-FAILED {repo}: {err.strip()[:120]}; repo skipped (fail closed)")
                continue
        base = base_ref(repo)
        for wt in list_worktrees(repo):
            v, why, extra = classify(repo, wt, base, now=now, min_idle_s=min_idle_h * 3600, protect=protect,
                                     keep=keep or set(), only=only, proc_root=proc_root, pending=pending)
            if v == "OUT-OF-SCOPE":
                continue
            rec = {"repo": repo, "path": wt["path"], "branch": wt["branch"], "verdict": v, "reason": why, "result": "kept", **extra}
            if v == "REAP":
                if max_n is not None and removed >= max_n:
                    rec["verdict"], rec["reason"] = "KEEP-MAXCAP", f"--max {max_n} reached"
                elif apply:
                    ok, note = remove(repo, wt, base)
                    rec["result"] = note if ok else "FAILED " + note
                    removed += 1 if ok else 0
                else:
                    rec["result"] = "would-remove"
            recs.append(rec)
            log(f"WTREAP{'' if apply else '-DRYRUN'} {rec['verdict']} {wt['path']} :: {rec['reason']} -> {rec['result']}")
    return recs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-idle-h", type=float, default=24.0)
    ap.add_argument("--repo", action="append")
    ap.add_argument("--only-list")
    ap.add_argument("--keep-list", action="append", default=[])
    ap.add_argument("--protect-prefix", action="append")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--max", type=int)
    ap.add_argument("--flags", default=pending_refs.DEFAULT_FLAGS, help="compute-flags dir scanned by the pending-work keep rule")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    keep = set()
    for k in a.keep_list:
        keep |= read_list(k)
    only = read_list(a.only_list) if a.only_list else None
    pending = pending_refs.PendingIndex(flags=a.flags)
    recs = run(a.repo or DEFAULT_REPOS, apply=a.apply, min_idle_h=a.min_idle_h,
               protect=a.protect_prefix if a.protect_prefix is not None else DEFAULT_PROTECT,
               keep=keep, only=only, fetch=a.fetch, max_n=a.max, pending=pending, log=(lambda s: None) if a.json else print)
    n_rm = sum(1 for r in recs if r["result"].startswith("removed"))
    n_would = sum(1 for r in recs if r["result"] == "would-remove")
    summ = f"WTREAP SUMMARY apply={a.apply} considered={len(recs)} removed={n_rm} would_remove={n_would} " \
           f"failed={sum(1 for r in recs if r['result'].startswith('FAILED'))}"
    if a.json:
        print(json.dumps({"records": recs, "summary": summ}, indent=1))
    else:
        print(summ)
    return 0


if __name__ == "__main__":
    sys.exit(main())
