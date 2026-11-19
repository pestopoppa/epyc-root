#!/usr/bin/env python3
"""scratch_release.py — prompt scratch release (scratch-lease Phase 2/3 minimal; operator-directed 2026-11-04).

WHY. Row family akxall8-c5-declared-floor-v9..v37 published 29 versions in ~3 h; each scratch_root held a 2.0 GB
`owned-research/` snapshot (a git worktree of the research repo pinned by RESEARCH-SHA256SUMS) and <1 MB of real
output. The keeper reaper only frees after a filing receipt + REAP_DAYS idle, then via trash + hourly sweep: 58 GB
leaked. This module is a LIBRARY used by the existing step-6 pass (no new reaper loop):

1. INPUTS vs OUTPUTS. A row may declare `scratch_inputs` (list of {path, kind, manifest?, source?}, paths relative to
   scratch_root); when it does not, derive_inputs() finds them: every direct child of scratch_root that is a git
   worktree (`.git` file). An input is VERIFIABLY RE-DERIVABLE (verify_input) when
     kind=git-worktree: HEAD is contained in a ref of its source repo; no untracked file; every modified tracked file is
       pinned (path + sha256) by a `*SHA256SUMS*` manifest in scratch_root and matches it.
     kind=sha-manifest: every regular file under it is pinned by the declared manifest, matches, and the declared
       `source` dir still holds the same bytes.
   A verified input is freed DIRECTLY (git worktree remove --force / rmtree, no trash) as soon as the row is released.
   A DECLARED input that fails verification goes through guarded_rm (trash); a DERIVED one that fails stays put.
2. RELEASE (row_released): grants/<id>.ended (the JOB outcome, any rc; never the smoke's dryrun/<id>/ended), or a newer published version
   of the same base id (supersession: <base>-vN+1 / -rN+1) while the row has no open grant.
3. DEDUP AT SOURCE: link_snapshot() builds a snapshot of pinned paths by hardlinking from a content-addressed store
   (tmp/.scratch-cas/<sha[:2]>/<sha>, files 0444) instead of copying; versions of one row family then share bytes.
4. BUDGET: budget_refusal() is the admission check the allocator applies (rowflow.disk_budget_refusal mirrors it).

CLI:  scratch_release.py plan <scratch_root>           (read-only: derived inputs + verification)
      scratch_release.py snapshot-link --src DIR --dest DIR --paths PATHS.json [--store DIR] [--prefix P]
Tests: tests/test_scratch_release.py (temp dirs only).
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

TMP = "/mnt/raid0/llm/tmp"
DEFAULT_STORE = os.path.join(TMP, ".scratch-cas")
DISK_FLOOR_GIB = 150.0
_VER = re.compile(r"^(?P<base>.+?)-(?P<kind>[vr])(?P<n>\d+)(?P<tail>(?:[-_]\d{8}(?:T\d{4,6}Z?)?)?)$", re.I)


# ------------------------------------------------------------------ helpers
def sha256(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _git(cwd: str, *args: str, timeout: int = 120) -> tuple[int, str]:
    r = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout


def read_manifests(scratch_root: str, names: list[str] | None = None) -> dict[str, str]:
    """{relpath under scratch_root: sha256} from `*SHA256SUMS*` files at scratch_root top level (or the named ones)."""
    pins: dict[str, str] = {}
    files = [os.path.join(scratch_root, n) for n in names] if names else sorted(glob.glob(os.path.join(scratch_root, "*SHA256SUMS*")))
    for mf in files:
        with open(mf, errors="replace") as f:
            for line in f:
                m = re.match(r"^([0-9a-f]{64})\s+\*?(.+?)\s*$", line)
                if m:
                    pins[os.path.normpath(m.group(2))] = m.group(1)
    return pins


# ------------------------------------------------------------------ 1. inputs
def derive_inputs(scratch_root: str) -> list[dict]:
    out = []
    try:
        ents = sorted(os.scandir(scratch_root), key=lambda e: e.name)
    except OSError:
        return out
    for e in ents:
        if e.is_dir(follow_symlinks=False) and os.path.isfile(os.path.join(e.path, ".git")):
            out.append({"path": e.name, "kind": "git-worktree", "derived": True})
    return out


def row_inputs(row: dict) -> list[dict]:
    decl = row.get("scratch_inputs")
    if isinstance(decl, list) and decl:
        return [dict(d, derived=False) for d in decl if isinstance(d, dict) and valid_rel(d.get("path"))]
    return derive_inputs(row.get("scratch_root") or "")


def valid_rel(p) -> bool:
    return isinstance(p, str) and bool(p) and not os.path.isabs(p) and ".." not in p.split("/") and p not in (".",)


def _worktree_common(wt: str) -> str | None:
    rc, out = _git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return os.path.realpath(out.strip()) if rc == 0 and out.strip() else None


def verify_input(scratch_root: str, decl: dict) -> tuple[bool, str]:
    """(re-derivable?, why). Never raises for ordinary failures; any doubt => False."""
    try:
        rel = decl.get("path")
        if not valid_rel(rel):
            return False, "bad input path"
        p = os.path.join(scratch_root, rel)
        if os.path.islink(p) or not os.path.isdir(p):
            return False, "not a real directory"
        kind = decl.get("kind")
        pins = read_manifests(scratch_root, decl.get("manifest") and [decl["manifest"]])
        if kind == "git-worktree":
            if not os.path.isfile(os.path.join(p, ".git")):
                return False, "no .git file (not a linked worktree)"
            common = _worktree_common(p)
            if not common or not os.path.isdir(common):
                return False, "source repo missing"
            rc, head = _git(p, "rev-parse", "HEAD")
            if rc or not head.strip():
                return False, "no HEAD"
            rc, refs = _git(os.path.dirname(common), "for-each-ref", "--count=1", "--contains", head.strip(),
                            "refs/heads", "refs/remotes", "refs/tags")
            if rc or not refs.strip():
                return False, "HEAD %s on no ref of the source repo" % head.strip()[:12]
            rc, st = _git(p, "status", "--porcelain", "--untracked-files=all")
            if rc:
                return False, "git status failed"
            for line in st.splitlines():
                code, path = line[:2], line[3:]
                if code != " M":
                    return False, "uncommitted state %r %s" % (code, path)
                key = os.path.normpath(os.path.join(rel, path))
                if pins.get(key) != sha256(os.path.join(p, path)):
                    return False, "modified %s not pinned by a SHA256SUMS manifest" % path
            return True, "git-worktree at %s on a ref, %d pinned modification(s)" % (head.strip()[:12], len(st.splitlines()))
        if kind == "sha-manifest":
            src = decl.get("source")
            if not (isinstance(src, str) and os.path.isdir(src)):
                return False, "declared source missing"
            n = 0
            for dp, dn, fn in os.walk(p):
                for f in fn:
                    fp = os.path.join(dp, f)
                    if os.path.islink(fp):
                        continue
                    sub = os.path.relpath(fp, p)
                    key = os.path.normpath(os.path.join(rel, sub))
                    want = pins.get(key)
                    if not want or sha256(fp) != want:
                        return False, "%s unpinned or changed" % key
                    sp = os.path.join(src, sub)
                    if not os.path.isfile(sp) or sha256(sp) != want:
                        return False, "source lost %s" % sub
                    n += 1
            return True, "%d files pinned and present in source" % n
        return False, "unknown kind %r" % kind
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        return False, "verify error %r" % (e,)


def free_input(scratch_root: str, decl: dict) -> None:
    """Direct free of a VERIFIED input. Caller must have called verify_input() and the process guards."""
    p = os.path.join(scratch_root, decl["path"])
    if decl.get("kind") == "git-worktree":
        common = _worktree_common(p)
        r = subprocess.run(["git", "-C", os.path.dirname(common), "worktree", "remove", "--force", p],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise OSError("git worktree remove failed: %s" % r.stderr.strip()[:200])
        return
    for dp, dn, fn in os.walk(p):   # snapshot files may be 0444 / dirs 0555
        for x in dn:
            try:
                os.chmod(os.path.join(dp, x), 0o755)
            except OSError:
                pass
    shutil.rmtree(p)


# ------------------------------------------------------------------ 2. release / supersession
def version_of(rid: str) -> tuple[str, str, int] | None:
    """('base', 'v'|'r', n) or None. akxall8-c5-declared-floor-v9-20261104 -> ('akxall8-c5-declared-floor', 'v', 9)."""
    m = _VER.match(rid or "")
    return (m.group("base"), m.group("kind").lower(), int(m.group("n"))) if m else None


def superseded_by(rid: str, ids) -> str | None:
    v = version_of(rid)
    if not v:
        return None
    best = None
    for o in ids:
        w = version_of(o)
        if w and w[0] == v[0] and w[1] == v[1] and w[2] > v[2] and (best is None or w[2] > version_of(best)[2]):
            best = o
    return best


def _kv(path: str) -> dict:
    try:
        with open(path, errors="replace") as f:
            return dict(re.findall(r"(\w+)=(\S+)", f.read()))
    except OSError:
        return {}


def row_released(flags: str, rid: str, ids) -> tuple[bool, str]:
    g = os.path.join(flags, "grants", rid)
    if os.path.exists(g + ".grant"):
        return False, "open grant"
    if os.path.isfile(g + ".ended") or os.path.isfile(g + ".complete"):
        return True, "grants/%s.ended" % rid
    # dryrun/<id>/ended is only the smoke; the job outcome is grants/<id>.ended (coordinator 2026-11-04)
    s = superseded_by(rid, ids)
    if s:
        return True, "superseded by %s" % s
    return False, "not ended"


def all_superseded(ids, all_ids) -> bool:
    return bool(ids) and all(superseded_by(i, all_ids) for i in ids)


# ------------------------------------------------------------------ 3. dedup at source
def link_snapshot(src: str, dest: str, paths: list[str], store: str = DEFAULT_STORE, prefix: str = "") -> dict:
    """Materialise `paths` (relative to src, optionally prefixed by `prefix` as written in a SHA256SUMS manifest) under
    dest by HARDLINKING from a content-addressed store. Store files are 0444 so a job cannot edit them in place
    (an edit tool that rewrites a file replaces the link, leaving the store intact). Falls back to copy across devices.
    Returns {linked, stored, copied, sums} where sums is SHA256SUMS text with paths as given."""
    os.makedirs(store, exist_ok=True)
    res = {"linked": 0, "stored": 0, "copied": 0, "sums": []}
    for rp in paths:
        rel = rp[len(prefix):].lstrip("/") if prefix and rp.startswith(prefix) else rp
        if not valid_rel(rel):
            raise ValueError("bad path %r" % rp)
        sp = os.path.join(src, rel)
        h = sha256(sp)
        cas = os.path.join(store, h[:2], h)
        if not os.path.exists(cas):
            os.makedirs(os.path.dirname(cas), exist_ok=True)
            tmp = cas + ".part.%d" % os.getpid()
            shutil.copyfile(sp, tmp)
            os.chmod(tmp, 0o444)
            os.replace(tmp, cas)
            res["stored"] += 1
        dp = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        try:
            os.link(cas, dp)
            res["linked"] += 1
        except OSError:
            shutil.copyfile(cas, dp)
            res["copied"] += 1
        res["sums"].append("%s  %s" % (h, rp))
    return res


# ------------------------------------------------------------------ 4. admission budget
def budget_refusal(free_gib: float, live_budgets_gib: float, row_budget_gib: float, floor_gib: float = DISK_FLOOR_GIB) -> str | None:
    head = free_gib - live_budgets_gib - row_budget_gib
    if head < floor_gib:
        return ("disk budget: free %.0f GiB - live budgets %.0f GiB - this row %.0f GiB = %.0f GiB < %.0f GiB floor"
                % (free_gib, live_budgets_gib, row_budget_gib, head, floor_gib))
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("scratch_root")
    s = sub.add_parser("snapshot-link")
    s.add_argument("--src", required=True)
    s.add_argument("--dest", required=True)
    s.add_argument("--paths", required=True, help="JSON list of paths (e.g. RESEARCH-SNAPSHOT-PATHS.json)")
    s.add_argument("--store", default=DEFAULT_STORE)
    s.add_argument("--prefix", default="")
    s.add_argument("--sums-out")
    a = ap.parse_args(argv)
    if a.cmd == "plan":
        for d in derive_inputs(a.scratch_root):
            ok, why = verify_input(a.scratch_root, d)
            print("%s\t%s\t%s\t%s" % ("REDERIVABLE" if ok else "KEEP", d["kind"], d["path"], why))
        return 0
    with open(a.paths) as f:
        paths = json.load(f)
    r = link_snapshot(a.src, a.dest, paths, a.store, a.prefix)
    if a.sums_out:
        with open(a.sums_out, "w") as f:
            f.write("\n".join(r["sums"]) + "\n")
    print("linked=%d stored=%d copied=%d" % (r["linked"], r["stored"], r["copied"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
