#!/usr/bin/env python3
"""smoke_verdict.py - a smoke that reached a TERMINAL verdict is the row's RESULT, not a dry-run defect.

AK row-robustness RCA 2026-11-24 item 2 (F4 / RC7): ak-gvfattn-q4kv-gpu-20261124's smoke ran one real scored unit on the
exact argv, wrote out-smoke/RESULT.json `complete: true, verdict: FUTILITY_CORRECTNESS` (ON arm q4_0_ok 10 vs OFF 12) in
37 s and exited rc 3. The keeper filed it FAIL-1 / incomplete_run / "fix dry-run failure" - churn on the one row that did
everything right. This module decides, from files only, whether a failed smoke actually ended with a terminal verdict.

Pure + read-only: no rowflow import (rowflow imports this)."""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re

# FUTILITY_* / FAIL_* / PASS* (PASS, PASS_CORRECTNESS, ...). A bare "FAIL" is NOT terminal: it is what TERMINAL-smoke.json
# says for any crash, and it names no decision.
TERMINAL_RX = re.compile(r"^(FUTILITY_[A-Z0-9_]+|FAIL_[A-Z0-9_]+|PASS[A-Z0-9_]*)$")
RESULT_NAMES = ("RESULT.json",)


def is_terminal(verdict) -> bool:
    return isinstance(verdict, str) and bool(TERMINAL_RX.match(verdict.strip().upper()))


def candidate_paths(d: dict) -> list[str]:
    """Where a smoke writes its result: <scratch_root|workdir>/out-smoke/RESULT.json, then the row's own result_path
    when it is a literal .json file."""
    out = []
    for root in (d.get("scratch_root"), d.get("workdir")):
        if root:
            out += [os.path.join(str(root), "out-smoke", n) for n in RESULT_NAMES]
    rp = str(d.get("result_path") or "")
    if rp.endswith(".json") and not glob.has_magic(rp):
        out.append(rp if os.path.isabs(rp) or not d.get("workdir") else os.path.join(str(d["workdir"]), rp))
    return list(dict.fromkeys(out))


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def terminal_smoke_result(d: dict, t0: float | None) -> dict | None:
    """{path, sha256, verdict, at} for the first candidate RESULT written by THIS smoke (mtime >= t0) that says
    complete: true with a terminal verdict; else None. Never raises."""
    for p in candidate_paths(d or {}):
        try:
            if t0 is not None and os.path.getmtime(p) < float(t0):
                continue
            with open(p) as f:
                r = json.load(f)
        except (OSError, ValueError, TypeError):
            continue
        if not isinstance(r, dict) or r.get("complete") is not True:
            continue
        v = r.get("verdict") or r.get("status")
        if is_terminal(v):
            try:
                sha = _sha(p)
            except OSError:
                continue
            return {"path": p, "sha256": sha, "verdict": str(v).strip(), "at": r.get("at")}
    return None


def is_decided(r) -> bool:
    """A RESULT that decided: complete is True AND it carries a "polar" field, whatever the verdict text
    (CEILING_OPEN, ANSWERED, ...); or complete with a terminal verdict. AK bug 2026-11-24 (rc=75 on CEILING_OPEN)."""
    if not isinstance(r, dict) or r.get("complete") is not True:
        return False
    return "polar" in r or is_terminal(r.get("verdict") or r.get("status"))


def complete_result(d: dict) -> dict | None:
    """{path, verdict, polar} for the row's real (non-smoke) RESULT that is complete with a polar field; else None.
    Looks at <scratch_root|workdir>/out/RESULT.json, then a literal .json result_path. Never raises."""
    d = d or {}
    paths = [os.path.join(str(r), "out", n) for r in (d.get("scratch_root"), d.get("workdir")) if r for n in RESULT_NAMES]
    rp = str(d.get("result_path") or "")
    if rp.endswith(".json") and not glob.has_magic(rp):
        paths.append(rp if os.path.isabs(rp) or not d.get("workdir") else os.path.join(str(d["workdir"]), rp))
    for p in dict.fromkeys(paths):
        try:
            with open(p) as f:
                r = json.load(f)
        except (OSError, ValueError, TypeError):
            continue
        if isinstance(r, dict) and r.get("complete") is True and "polar" in r and r.get("smoke") is not True:
            return {"path": p, "verdict": str(r.get("verdict") or ""), "polar": r.get("polar")}
    return None
