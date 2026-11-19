#!/usr/bin/env python3
"""owner_check.py — flag scratch/trash entries the janitor cannot reclaim because they are not ours.

Origin (coordinator, 2026-11-07): inf75-quantizer-7cdd7c97/build-e5efhhdt (~42 GB) was left ROOT-owned and
mode 555 by a build job; trash-sweep could not delete it as `node` and the operator had to `sudo rm`. Every
such tree is a byte leak no automatic path can close, so it is (a) flagged here every janitor pass and
(b) prevented at the source: a row's scratch must be left owned by the row's uid and writable (reclaim_row.py
repairs modes it owns at filing; a root-owned residue is reported, never silently skipped).

    owner_check.py [--roots DIR ...] [--depth 3] [--uid N] [--json] [--log FILE] [--fix-modes]

Read-only by default. A path is FLAGGED when (lstat, never following symlinks) its uid differs from --uid
(default: our own) OR it is a directory/file we cannot write (os.access W_OK false) — either makes
guarded_rm.sh / trash-sweep.sh fail on it. --fix-modes runs `chmod u+rwX` on flagged paths WE OWN (a
mode-only problem is ours to fix); foreign-uid paths are only ever reported (fixing those is `sudo chown -R
node:node <path>`, printed verbatim for the operator). Walk is depth-limited; the first flagged entry of a
subtree is reported with its total size, not every descendant. Exit 0 always; the SUMMARY line carries counts.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time

DEFAULT_ROOTS = ["/mnt/raid0/llm/tmp", "/mnt/raid0/llm/.trash", "/mnt/raid0/llm/.trash-reap",
                 "/mnt/raid0/llm/worktrees"]
SIZE_WALK_CAP = 300_000


def _size(path: str) -> int:
    total, n = 0, 0
    try:
        st = os.lstat(path)
    except OSError:
        return 0
    if not stat.S_ISDIR(st.st_mode):
        return st.st_size
    for dp, dn, fn in os.walk(path, onerror=lambda e: None):
        for f in fn:
            n += 1
            if n > SIZE_WALK_CAP:
                return total
            try:
                total += os.lstat(os.path.join(dp, f)).st_size
            except OSError:
                pass
    return total


def _flag(path: str, uid: int) -> str | None:
    try:
        st = os.lstat(path)
    except OSError as exc:
        return f"lstat failed: {exc.strerror}"
    if stat.S_ISLNK(st.st_mode):
        return None
    if st.st_uid != uid:
        return f"uid {st.st_uid} != {uid} (mode {oct(st.st_mode & 0o777)})"
    if not stat.S_ISDIR(st.st_mode):
        return None            # a read-only FILE in a writable dir deletes fine; only its dir's bits matter
    if not os.access(path, os.W_OK | os.X_OK, follow_symlinks=False):
        return f"dir not writable/searchable by uid {uid} (mode {oct(st.st_mode & 0o777)})"
    return None


def scan(roots: list[str], *, depth: int = 3, uid: int | None = None, fix_modes: bool = False,
         emit=print) -> dict:
    uid = os.getuid() if uid is None else uid
    rows: list[dict] = []
    fixed = 0
    for root in roots:
        if not os.path.isdir(root):
            continue
        stack = [(root, 0)]
        while stack:
            d, lvl = stack.pop()
            try:
                names = sorted(os.listdir(d))
            except OSError:
                continue
            for name in names:
                p = os.path.join(d, name)
                why = _flag(p, uid)
                if why:
                    foreign = "uid " in why and "!=" in why
                    row = {"path": p, "why": why, "bytes": _size(p), "foreign": foreign, "fixed": False}
                    if fix_modes and not foreign:
                        try:
                            st = os.lstat(p)
                            os.chmod(p, (st.st_mode & 0o777) | 0o700 if stat.S_ISDIR(st.st_mode) else (st.st_mode & 0o777) | 0o600)
                            row["fixed"] = _flag(p, uid) is None
                            fixed += row["fixed"]
                        except OSError as exc:
                            row["why"] += f"; chmod failed: {exc.strerror}"
                    rows.append(row)
                    emit(f"OWNER-FLAG path={p} bytes={row['bytes']} why='{why}' "
                         f"fix='{'sudo chown -R ' + str(uid) + ' ' + p if foreign else 'chmod -R u+rwX ' + p}'"
                         f"{' fixed=yes' if row['fixed'] else ''}")
                    continue   # the first flagged entry of a subtree is enough
                if lvl + 1 < depth:
                    try:
                        if stat.S_ISDIR(os.lstat(p).st_mode):
                            stack.append((p, lvl + 1))
                    except OSError:
                        pass
    foreign = [r for r in rows if r["foreign"]]
    res = {"roots": roots, "flagged": len(rows), "foreign": len(foreign),
           "bytes_foreign": sum(r["bytes"] for r in foreign), "bytes_flagged": sum(r["bytes"] for r in rows),
           "fixed": fixed, "rows": rows}
    emit(f"OWNER-CHECK SUMMARY roots={len(roots)} flagged={res['flagged']} foreign_uid={res['foreign']} "
         f"bytes_foreign={res['bytes_foreign']} bytes_flagged={res['bytes_flagged']} fixed={fixed}")
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS)
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--uid", type=int)
    ap.add_argument("--fix-modes", action="store_true", help="chmod u+rwX flagged paths we own")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--log")
    a = ap.parse_args(argv)
    logf = open(a.log, "a") if a.log else None

    def emit(s: str) -> None:
        print(s, flush=True)
        if logf:
            logf.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {s}\n")
            logf.flush()

    res = scan(a.roots, depth=a.depth, uid=a.uid, fix_modes=a.fix_modes, emit=emit)
    if logf:
        logf.close()
    if a.json:
        print(json.dumps(res, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
