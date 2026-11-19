#!/usr/bin/env python3
"""quiet_host.py - the ONE "is a quiet-host grant live?" check, and the scan deferral built on it.

Origin: 2026-11-10 19:02Z, AutoKernel's quiet-host floor row ak-c10-q38fn-floor-r3-20261110 failed closed with
FAIL_FOREIGN_LOAD. The only offender was `du -sx --block-size=1 /mnt/raid0/llm/worktrees` (57% CPU, unpinned):
host_hygiene_tick.py's daily heavy phase. Its gate read region-lock, which was momentarily empty between the
grant being written and the row's regions being claimed, so the du started inside a live whole-host grant.
The disk janitor already skipped its REAPS during such a grant (bash quiet_host_grant(), 9d597d559); its scans,
and every other background scan, did not.

A quiet-host grant is a grants/<id>.grant file whose FIRST line has `holds=` covering all of q0,q1,q2,q3 and
gpu-quiet, and whose ` end=` is absent or not yet past (an expired leftover never defers anything). This is the
janitor's logic moved here unchanged; disk_janitor.sh now calls this file instead of carrying its own copy.

Rule for every background scan / maintenance job: call `defer(tag, log)` first; if it returns True, skip this
tick (it logged DEFER-QUIET-HOST). Otherwise run the scan under `scan_prefix()` (nice -n 19 ionice -c3; no CPU
pinning, so it never lands on the GPU host threads by design).

CLI (for bash callers):
    quiet_host.py grant [--flags DIR]          print the live quiet-host grant id (nothing if none); exit 0
    quiet_host.py exec TAG [--flags DIR] -- CMD...
        live grant -> print `DEFER-QUIET-HOST TAG: ...` on stderr and exit 75 (CMD not run)
        otherwise  -> exec `nice -n 19 ionice -c3 CMD...`
Env: QUIET_HOST_FLAGS overrides the flags dir (default /mnt/raid0/llm/tmp/compute-flags).
"""
from __future__ import annotations

import datetime as dt
import glob
import os
import re
import shutil
import sys

FLAGS_DEFAULT = "/mnt/raid0/llm/tmp/compute-flags"
QUIET_TOKENS = ("q0", "q1", "q2", "q3", "gpu-quiet")
DEFER_RC = 75
_HOLDS = re.compile(r".*holds=([^ ]*)")
_END = re.compile(r".* end=([^ ]*)")


def flags_dir(flags: str | None = None) -> str:
    return flags or os.environ.get("QUIET_HOST_FLAGS") or FLAGS_DEFAULT


def _epoch(s: str) -> float:
    """Parse the grant's end= stamp; unparseable -> 0 (== expired), matching the janitor's `date -d ... || echo 0`."""
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def quiet_host_grant(flags: str | None = None, now: float | None = None) -> str | None:
    """The id of a live quiet-host grant (holds all of q0-q3 + gpu-quiet, not expired), else None."""
    now = dt.datetime.now(dt.timezone.utc).timestamp() if now is None else now
    for g in sorted(glob.glob(os.path.join(flags_dir(flags), "grants", "*.grant"))):
        try:
            with open(g) as f:
                first = f.readline().rstrip("\n")
        except OSError:
            continue
        m = _HOLDS.match(first)
        holds = set((m.group(1) if m else "").split(","))
        if not all(t in holds for t in QUIET_TOKENS):
            continue
        m = _END.match(first)
        if m and m.group(1) and _epoch(m.group(1)) < now:
            continue                                   # an expired leftover must not stop anything
        return os.path.basename(g)[: -len(".grant")]
    return None


def defer(tag: str, log=None, flags: str | None = None) -> bool:
    """True (and logs DEFER-QUIET-HOST) when a quiet-host grant is live: the caller skips this tick."""
    gid = quiet_host_grant(flags)
    if gid is None:
        return False
    msg = f"DEFER-QUIET-HOST {tag}: quiet-host grant {gid} live; scan skipped this tick"
    (log or (lambda s: print(s, file=sys.stderr)))(msg)
    return True


def scan_prefix() -> list[str]:
    """nice -n 19 ionice -c3 (each only if installed). Deliberately no taskset: never pin to the GPU host threads."""
    pre: list[str] = []
    if shutil.which("nice"):
        pre += ["nice", "-n", "19"]
    if shutil.which("ionice"):
        pre += ["ionice", "-c3"]
    return pre


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv else 2
    cmd, rest = argv[0], argv[1:]
    flags = None
    tail: list[str] = []
    if "--" in rest:
        i = rest.index("--")
        rest, tail = rest[:i], rest[i + 1:]
    if "--flags" in rest:
        i = rest.index("--flags")
        flags = rest[i + 1]
        del rest[i:i + 2]
    if cmd == "grant":
        gid = quiet_host_grant(flags)
        if gid:
            print(gid)
        return 0
    if cmd == "exec":
        if not rest or not tail:
            print("usage: quiet_host.py exec TAG [--flags DIR] -- CMD...", file=sys.stderr)
            return 2
        if defer(rest[0], flags=flags):
            return DEFER_RC
        full = scan_prefix() + tail
        os.execvp(full[0], full)
    print(f"unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
