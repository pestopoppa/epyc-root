#!/usr/bin/env python3
"""worktree_salvage.py — retire a git worktree the operator-approved way: SALVAGE, TRASH, DEREGISTER.

Shared by scripts/system/worktree_reaper.py (agent worktrees, TTL) and
scripts/coordination/job_templates/row_worktree.py (row-owned worktrees, released at filing).
Origin: operator 2026-11-07 ("we can't have so much disk leak"): a dirty or unlanded worktree is no
longer parked forever — its work is salvaged (patch bundle + salvage branch), the directory is
trashed through guarded_rm.sh (recoverable until trash-sweep ages it out), and the registration is
dropped with `git worktree remove <path>` on the now-missing path (works without --force: verified
2026-11-07, rc=0, registration gone). NEVER `--force`, NEVER `git worktree prune`, NEVER `git gc`.

    retire(path, apply=False)   -> plan only (dict)
    retire(path, apply=True)    -> salvage -> guarded_rm -> worktree remove

What is salvaged (bundle dir <salvage_dir>/<name>-<UTC>/):
    HEAD            the commit the tree was at
    BRANCH          its branch (or "(detached)")
    diff.patch      `git diff --binary HEAD` (tracked modifications, staged or not)
    untracked.tar   every `git ls-files --others --exclude-standard` path (ignored files are NOT
                    salvaged: build output is reproducible; evidence-shaped ignored files make the
                    gate refuse the tree before we get here)
    manifest.json   sha256 + size of each, counts, the salvage branch name
and `git branch salvage/<name>-<UTC> <HEAD>` in the owning repo, so unlanded commits keep a ref.
A tree that is clean AND landed gets no bundle and no branch: there is nothing to salvage.

REFUSALS (the dict carries `refused`): not a registered linked worktree of a known repo; locked;
a KEEP marker at its top level; a process has its cwd in it or names it (worktree_gate probe);
a live reference file names it. Any git failure during salvage refuses BEFORE anything is trashed:
nothing is deleted unless the bundle is complete and verified on disk.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import worktree_gate as wg  # noqa: E402

REPO_ROOT = HERE.parent.parent
GUARDED_RM = str(REPO_ROOT / "scripts" / "safety" / "guarded_rm.sh")
DEFAULT_SALVAGE_DIR = f"{wg.LLM}/archive/worktree-salvage"


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git(args: list[str], cwd: str, timeout: int = 600) -> subprocess.CompletedProcess:
    return wg._git(args, cwd, timeout=timeout)


def _locked(wt: wg.Worktree) -> bool:
    cp = _git(["worktree", "list", "--porcelain"], cwd=wt.repo)
    cur, locked = None, False
    for ln in cp.stdout.splitlines():
        if ln.startswith("worktree "):
            cur = os.path.realpath(ln[9:])
        elif ln.startswith("locked") and cur == os.path.realpath(wt.path):
            locked = True
    return locked


def _keep_marker(path: str) -> str | None:
    for m in wg.KEEP_MARKERS:
        if os.path.exists(os.path.join(path, m)):
            return m
    git_dir = wg._gitdir(path)
    if git_dir is not None and (git_dir / "epyc-keep").exists():
        return "epyc-keep (git admin dir)"
    return None


def plan(path: str, *, probe: wg.Probe | None = None, base: str = wg.DEFAULT_BASE) -> dict:
    """Classify `path` for retirement. Returns a dict with `refused` (str|None) and `state`."""
    out = {"path": path, "repo": None, "branch": None, "head": None, "refused": None, "state": None,
           "dirty": None, "unlanded": None}
    wt = wg._find(path)
    if wt is None:
        out["refused"] = "not a registered linked worktree of a known repo"
        return out
    out.update(repo=wt.repo, branch=wt.branch or "(detached)", head=wt.head)
    if not os.path.isdir(path):
        out["refused"] = "directory missing (registration only; nothing to salvage)"
        return out
    if os.path.realpath(path) in {os.path.realpath(r) for r in wg.DEFAULT_REPOS} or \
            os.path.realpath(path) in {os.path.realpath(p) for p in ("/workspace", f"{wg.LLM}/epyc-root")}:
        out["refused"] = "canonical root"
        return out
    if _locked(wt):
        out["refused"] = "locked (git worktree lock)"
        return out
    km = _keep_marker(path)
    if km:
        out["refused"] = f"KEEP marker {km}"
        return out
    pr = wg._protected_reason(wt, ["/workspace", f"{wg.LLM}/epyc-root"])
    if pr:
        out["refused"] = pr
        return out
    probe = probe if probe is not None else wg.gather_probe()
    busy = probe.busy(path)
    if busy:
        out["refused"] = f"busy: {busy}"
        return out
    ref = probe.referenced(path)
    if ref:
        out["refused"] = f"referenced: {ref}"
        return out
    st = _git(["status", "--porcelain", "--untracked-files=normal"], cwd=path)
    if st.returncode != 0:
        out["refused"] = f"git status failed: {st.stderr.strip()[:200]}"
        return out
    out["dirty"] = bool(st.stdout.strip())
    ch = _git(["cherry", base, "HEAD"], cwd=path)
    if ch.returncode != 0:
        out["refused"] = f"git cherry {base} failed: {ch.stderr.strip()[:200]}"
        return out
    out["unlanded"] = sum(1 for ln in ch.stdout.splitlines() if ln.startswith("+"))
    out["state"] = "clean-landed" if not out["dirty"] and not out["unlanded"] else "needs-salvage"
    return out


def salvage(path: str, info: dict, *, salvage_dir: str = DEFAULT_SALVAGE_DIR, now: float | None = None) -> dict:
    """Write the bundle and create the salvage branch. Raises RuntimeError on any failure (nothing trashed)."""
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(now if now is not None else time.time()))
    name = os.path.basename(path.rstrip("/"))
    bundle = os.path.join(salvage_dir, f"{name}-{ts}")
    os.makedirs(bundle, exist_ok=False)
    head = _git(["rev-parse", "HEAD"], cwd=path)
    if head.returncode != 0:
        raise RuntimeError(f"rev-parse HEAD failed: {head.stderr.strip()[:200]}")
    head_sha = head.stdout.strip()
    Path(bundle, "HEAD").write_text(head_sha + "\n")
    Path(bundle, "BRANCH").write_text(str(info.get("branch") or "(detached)") + "\n")
    patch = os.path.join(bundle, "diff.patch")
    with open(patch, "wb") as fh:
        cp = subprocess.run(["git", "diff", "--binary", "HEAD"], cwd=path, stdout=fh, stderr=subprocess.PIPE, timeout=1800)
    if cp.returncode != 0:
        raise RuntimeError(f"git diff failed: {cp.stderr.decode(errors='replace')[:200]}")
    ls = _git(["ls-files", "--others", "--exclude-standard", "-z"], cwd=path)
    if ls.returncode != 0:
        raise RuntimeError(f"ls-files failed: {ls.stderr.strip()[:200]}")
    untracked = [p for p in ls.stdout.split("\0") if p]
    tarf = os.path.join(bundle, "untracked.tar")
    if untracked:
        listf = os.path.join(bundle, "untracked.list")
        with open(listf, "wb") as fh:
            fh.write(b"\0".join(p.encode() for p in untracked) + b"\0")
        cp = subprocess.run(["tar", "-C", path, "--null", "-T", listf, "-cf", tarf],
                            capture_output=True, text=True, timeout=3600)
        if cp.returncode != 0:
            raise RuntimeError(f"tar failed: {cp.stderr.strip()[:200]}")
    else:
        Path(tarf).write_bytes(b"")
    branch = f"salvage/{name}-{ts}"
    cp = _git(["branch", branch, head_sha], cwd=info["repo"])
    if cp.returncode != 0:
        raise RuntimeError(f"salvage branch failed: {cp.stderr.strip()[:200]}")
    files = {}
    for fn in ("HEAD", "BRANCH", "diff.patch", "untracked.tar"):
        p = os.path.join(bundle, fn)
        files[fn] = {"sha256": _sha256(p), "bytes": os.path.getsize(p)}
    man = {"schema": "epyc.worktree_salvage.v1", "path": path, "repo": info["repo"], "head": head_sha,
           "branch": info.get("branch"), "salvage_branch": branch, "untracked": len(untracked),
           "dirty": info.get("dirty"), "unlanded": info.get("unlanded"), "at": ts, "files": files}
    with open(os.path.join(bundle, "manifest.json"), "w") as fh:
        json.dump(man, fh, indent=1, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    # verify the bundle is what we think it is before anything is trashed
    for fn, meta in files.items():
        p = os.path.join(bundle, fn)
        if not os.path.isfile(p) or os.path.getsize(p) != meta["bytes"]:
            raise RuntimeError(f"bundle verification failed for {fn}")
    return {"bundle": bundle, "salvage_branch": branch, "head": head_sha, "untracked": len(untracked),
            "patch_bytes": files["diff.patch"]["bytes"]}


def retire(path: str, *, apply: bool = False, salvage_dir: str = DEFAULT_SALVAGE_DIR,
           guarded_rm: str = GUARDED_RM, probe: wg.Probe | None = None, base: str = wg.DEFAULT_BASE,
           trash_root: str | None = None) -> dict:
    """salvage (if needed) -> guarded_rm -> `git worktree remove <missing path>`. Dry by default."""
    info = plan(path, probe=probe, base=base)
    info.update(apply=apply, action=None, salvage=None, trashed=None, deregistered=None, error=None)
    if info["refused"]:
        info["action"] = "REFUSED"
        return info
    info["action"] = "REMOVE" if info["state"] == "clean-landed" else "SALVAGE+TRASH+REMOVE"
    if not apply:
        return info
    try:
        if info["state"] == "clean-landed":
            cp = _git(["worktree", "remove", path], cwd=info["repo"], timeout=1800)   # never --force
            if cp.returncode != 0:
                raise RuntimeError(f"git worktree remove failed: {cp.stderr.strip()[:300]}")
            info["deregistered"] = True
            return info
        info["salvage"] = salvage(path, info, salvage_dir=salvage_dir)
        env = dict(os.environ)
        if trash_root:
            env["TRASH_ROOT"] = trash_root
        cp = subprocess.run(["bash", guarded_rm, path], capture_output=True, text=True, timeout=3600, env=env)
        if cp.returncode != 0 or os.path.exists(path):
            raise RuntimeError(f"guarded_rm failed rc={cp.returncode}: {(cp.stderr or cp.stdout).strip()[:300]}")
        info["trashed"] = cp.stdout.strip().splitlines()[-1][:300] if cp.stdout.strip() else "trashed"
        cp = _git(["worktree", "remove", path], cwd=info["repo"], timeout=600)      # missing path: deregisters
        if cp.returncode != 0:
            raise RuntimeError(f"git worktree remove (missing path) failed: {cp.stderr.strip()[:300]}")
        info["deregistered"] = True
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        info["error"] = str(exc)[:400]
    return info


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="retire a worktree: salvage, trash (guarded_rm), deregister")
    ap.add_argument("path", nargs="+")
    ap.add_argument("--apply", action="store_true", help="default is a plan only")
    ap.add_argument("--salvage-dir", default=DEFAULT_SALVAGE_DIR)
    ap.add_argument("--base", default=wg.DEFAULT_BASE)
    a = ap.parse_args(argv)
    rc = 0
    probe = wg.gather_probe()
    for p in a.path:
        r = retire(os.path.abspath(p), apply=a.apply, salvage_dir=a.salvage_dir, probe=probe, base=a.base)
        print(json.dumps(r, sort_keys=True))
        if r["refused"] or r["error"]:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
