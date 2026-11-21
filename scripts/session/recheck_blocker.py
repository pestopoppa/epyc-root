#!/usr/bin/env python3
"""recheck_blocker.py -- re-probe a blocker before repeating it to the operator (steering report 2026-11-21, item 7).

Stale blockers repeated as current (Codex login, gdb, rocprofv3, python3.13, model weights gone) cost operator
turns. Run this before saying "blocked on X" again:

    recheck_blocker.py codex-login                     # `codex login status`
    recheck_blocker.py which <binary> [<binary> ...]   # installed on PATH
    recheck_blocker.py python <version>                # e.g. 3.13 -> python3.13 exists and reports 3.13.x
    recheck_blocker.py model <path-or-glob>            # model file exists, non-empty
    recheck_blocker.py disk <min-free-GiB> [<path>]    # free space at <path> (default /mnt/raid0) >= threshold
    recheck_blocker.py row <row-id> [--want STATE]     # a rowflow row's live state (queue_status --json bucket)

Exit 0 = CLEAR (the blocker no longer holds: stop reporting it), 1 = STILL BLOCKED (report it, with this line as the
evidence and its timestamp), 2 = could not check. One line out, prefixed CLEAR / BLOCKED / UNKNOWN. `--json` emits
{kind, args, verdict, detail, checked_at}. Zero compute, read-only.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

CLEAR, BLOCKED, UNKNOWN = 0, 1, 2
NAMES = {CLEAR: "CLEAR", BLOCKED: "BLOCKED", UNKNOWN: "UNKNOWN"}
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QUEUE_STATUS = os.path.join(ROOT, ".claude/skills/inference-backlog-scheduling/scripts/queue_status.py")
OK_ROW_STATES = ("RUNNING", "GRANTABLE", "SMOKE-QUEUED")


def _run(cmd: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, f"{cmd[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, f"{cmd[0]}: timed out after {timeout}s"


def codex_login() -> tuple[int, str]:
    if not shutil.which("codex"):
        return BLOCKED, "codex CLI not on PATH"
    rc, out = _run(["codex", "login", "status"])
    first = out.splitlines()[0] if out else ""
    if rc == 0 and not re.search(r"not logged in|logged out", out, re.I):
        return CLEAR, f"codex login status: {first or 'rc=0'}"
    return BLOCKED, f"codex login status rc={rc}: {first}"


def which(bins: list[str]) -> tuple[int, str]:
    found = {b: shutil.which(b) for b in bins}
    miss = [b for b, p in found.items() if not p]
    if miss:
        return BLOCKED, "not installed: " + ", ".join(miss)
    return CLEAR, "installed: " + ", ".join(f"{b}={p}" for b, p in found.items())


def python(ver: str) -> tuple[int, str]:
    if not re.fullmatch(r"3\.\d+", ver):
        return UNKNOWN, f"version must look like 3.13, got {ver!r}"
    exe = shutil.which(f"python{ver}")
    if not exe:
        return BLOCKED, f"python{ver} not on PATH"
    rc, out = _run([exe, "-V"])
    if rc == 0 and out.split()[-1].startswith(ver + "."):
        return CLEAR, f"{exe}: {out}"
    return BLOCKED, f"{exe} -V rc={rc}: {out}"


def model(pat: str) -> tuple[int, str]:
    hits = [p for p in glob.glob(pat) if os.path.isfile(p)] if any(c in pat for c in "*?[") else \
        ([pat] if os.path.isfile(pat) else [])
    good = [p for p in hits if os.path.getsize(p) > 0]
    if good:
        gib = sum(os.path.getsize(p) for p in good) / 2**30
        return CLEAR, f"{len(good)} file(s), {gib:.1f} GiB: {good[0]}" + (" ..." if len(good) > 1 else "")
    if hits:
        return BLOCKED, f"present but empty: {hits[0]}"
    return BLOCKED, f"no file matches {pat}"


def disk(min_gib: float, path: str = "/mnt/raid0") -> tuple[int, str]:
    try:
        st = os.statvfs(path)
    except OSError as e:
        return UNKNOWN, f"statvfs {path}: {e}"
    free = st.f_bavail * st.f_frsize / 2**30
    v = CLEAR if free >= min_gib else BLOCKED
    return v, f"{path} free {free:.0f} GiB vs threshold {min_gib:.0f} GiB"


def row(rid: str, want: str | None = None, qjson: dict | None = None) -> tuple[int, str]:
    if qjson is None:
        rc, out = _run([sys.executable, QUEUE_STATUS, "--json"], timeout=60)
        try:
            qjson = json.loads(out[out.index("{"):])
        except (ValueError, json.JSONDecodeError):
            return UNKNOWN, f"queue_status --json failed rc={rc}"
    buckets = qjson.get("buckets") or {}
    for b in ("RUNNING", "GRANTABLE", "SMOKE-QUEUED", "NEEDS-REPUBLISH", "FAILED", "PARKED", "BLOCKED", "NOT-A-ROW"):
        for x in buckets.get(b) or []:
            if x.get("id") == rid:
                ok = (b == want.upper()) if want else (b in OK_ROW_STATES)
                return (CLEAR if ok else BLOCKED), f"row {rid} is {b}: {str(x.get('reason') or '')[:160]}"
    return BLOCKED if want else UNKNOWN, f"row {rid} not in any live bucket (done, withdrawn or never published)"


def check(kind: str, args: list[str], want: str | None = None) -> tuple[int, str]:
    try:
        if kind == "codex-login":
            return codex_login()
        if kind == "which":
            return which(args) if args else (UNKNOWN, "which needs a binary name")
        if kind == "python":
            return python(args[0])
        if kind == "model":
            return model(args[0])
        if kind == "disk":
            return disk(float(args[0]), args[1] if len(args) > 1 else "/mnt/raid0")
        if kind == "row":
            return row(args[0], want)
    except (IndexError, ValueError) as e:
        return UNKNOWN, f"bad arguments for {kind}: {e}"
    return UNKNOWN, f"unknown kind {kind!r}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("kind", choices=("codex-login", "which", "python", "model", "disk", "row"))
    ap.add_argument("args", nargs="*")
    ap.add_argument("--want", help="row: the state that counts as CLEAR (default RUNNING/GRANTABLE/SMOKE-QUEUED)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    v, detail = check(a.kind, a.args, a.want)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if a.json:
        print(json.dumps({"kind": a.kind, "args": a.args, "verdict": NAMES[v], "detail": detail, "checked_at": ts}))
    else:
        print(f"{NAMES[v]} {a.kind} @ {ts}: {detail}")
    return v


if __name__ == "__main__":
    sys.exit(main())
