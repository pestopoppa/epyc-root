#!/usr/bin/env python3
"""Age the ROCm comgr JIT cache: /tmp/.<hex>-00000000.so files (operator 2026-11-07).

comgr writes one ~13 MB `.<hash>-00000000.so` into /tmp per JIT'd kernel; 2270 of them held 12 GiB. They are
regenerable caches on /tmp (outside raid0's trash FS, so guarded_rm.sh's trash does not apply: direct unlink).

A file is removed only if ALL hold: a regular file (not a symlink) directly in --dir whose name matches
`^\\.[0-9a-f]+-00000000\\.so$`, owned by our uid, mtime older than --min-age-days (default 3), and no process has
it mapped (/proc/*/maps) or open (/proc/*/fd). Unlinking a mapped file would not break the mapping, but a
file in use is skipped anyway. Default is a dry-run; --apply deletes. Prints one summary line.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time

NAME_RE = re.compile(r"^\.[0-9a-f]+-00000000\.so$")


def in_use(proc: str = "/proc") -> tuple[set[tuple[int, int]], set[str], int]:
    """(dev,ino) pairs and path strings referenced by any process; third value = unreadable pids."""
    inos: set[tuple[int, int]] = set()
    paths: set[str] = set()
    unreadable = 0
    for pid in os.listdir(proc):
        if not pid.isdigit():
            continue
        ok = True
        try:
            with open(f"{proc}/{pid}/maps") as fh:
                for line in fh:
                    parts = line.split(None, 5)
                    if len(parts) == 6 and parts[5].startswith("/"):
                        paths.add(parts[5].rstrip("\n").removesuffix(" (deleted)"))
        except FileNotFoundError:
            continue
        except OSError:
            ok = False
        try:
            fd_dir = f"{proc}/{pid}/fd"
            for fd in os.listdir(fd_dir):
                try:
                    st = os.stat(f"{fd_dir}/{fd}")
                    inos.add((st.st_dev, st.st_ino))
                except OSError:
                    pass
        except FileNotFoundError:
            continue
        except OSError:
            ok = False
        if not ok:
            unreadable += 1
    return inos, paths, unreadable


def reap(directory: str, min_age_days: float, apply: bool, now: float | None = None,
         proc: str = "/proc") -> dict:
    now = time.time() if now is None else now
    cutoff = now - min_age_days * 86400
    inos, paths, unreadable = in_use(proc)
    uid = os.getuid()
    res = {"considered": 0, "removed": 0, "removed_bytes": 0, "in_use": 0, "unreadable_pids": unreadable,
           "applied": apply}
    for name in sorted(os.listdir(directory)):
        if not NAME_RE.match(name):
            continue
        p = os.path.join(directory, name)
        try:
            st = os.lstat(p)
        except OSError:
            continue
        if not os.path.isfile(p) or os.path.islink(p) or st.st_uid != uid or st.st_mtime >= cutoff:
            continue
        res["considered"] += 1
        if (st.st_dev, st.st_ino) in inos or p in paths or os.path.realpath(p) in paths:
            res["in_use"] += 1
            continue
        if apply:
            try:
                os.unlink(p)
            except OSError:
                continue
        res["removed"] += 1
        res["removed_bytes"] += st.st_size
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default="/tmp")
    ap.add_argument("--min-age-days", type=float, default=3.0)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    r = reap(a.dir, a.min_age_days, a.apply)
    print(f"comgr-cache {'removed' if a.apply else 'would remove'} {r['removed']} files "
          f"{r['removed_bytes'] / (1 << 30):.2f} GiB; in_use={r['in_use']} considered={r['considered']} "
          f"unreadable_pids={r['unreadable_pids']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
