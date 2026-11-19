#!/usr/bin/env python3
"""SHARED-SCRATCH GUARD (coordinator 2026-11-07): never reclaim a dir a LIVE row still uses.

Several lineages share one scratch dir across their -rN attempts, so a superseded attempt's reclaim would delete the live
attempt's data. `live_overlap(flags, rid, root)` returns the first NON-TERMINAL row (a manifest under ready/ or ready/*/
-- armed, queued, running -- with no grants/<id>.ended|.complete) whose scratch_root, workdir, `--workdir` argument or
result_path directory resolves (realpath) to the same dir, a parent or a child of `root`; else None.
`pinned(flags, rid)` honours <flags>/filing-no-reclaim.globs (one fnmatch id glob per line, `#` comments): rows whose
successor is not published yet (so no manifest can protect the dir) are pinned by hand and are never reclaimed.
Used by reclaim_row.py and the keeper's REAP pass. Stdlib only; read-only.
"""
from __future__ import annotations

import fnmatch
import glob
import json
import os
import re

TMP_ROOT = os.environ.get("RECLAIM_TMP_ROOT", "/mnt/raid0/llm/tmp")
_WORKDIR = re.compile(r"--workdir[=\s]+(/[^\s\"'\\]+)")


def _real(p):
    return os.path.realpath(p)


def _too_broad(p):
    """A path at or above the tmp root would overlap everything; it names no row-specific dir."""
    t = _real(TMP_ROOT)
    return p == t or t.startswith(p.rstrip("/") + "/") or p == "/"


def overlaps(a, b):
    a, b = _real(a), _real(b)
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def manifest_paths(m):
    """Every directory a manifest says it writes or reads: scratch_root, workdir, --workdir args, result_path's dir."""
    out = []
    for k in ("scratch_root", "workdir"):
        v = m.get(k)
        if isinstance(v, str) and os.path.isabs(v):
            out.append(v)
    rp = m.get("result_path")
    if isinstance(rp, str) and os.path.isabs(rp):
        cut = min([i for i in (rp.find(c) for c in "*?[") if i >= 0] or [len(rp)])
        base = rp[:cut]
        out.append(base if cut < len(rp) and base.endswith("/") else os.path.dirname(base))
    try:
        out += _WORKDIR.findall(json.dumps(m))
    except (TypeError, ValueError):
        pass
    seen, res = set(), []
    for p in out:
        r = _real(p)
        if r not in seen and not _too_broad(r):
            seen.add(r)
            res.append(r)
    return res


def _terminal(flags, rid):
    g = os.path.join(flags, "grants")
    return any(os.path.exists(os.path.join(g, rid + s)) for s in (".ended", ".complete"))


def live_overlap(flags, rid, root):
    """-> 'ID (path)' of the first non-terminal OTHER row overlapping `root`, else None."""
    root = _real(root)
    for p in sorted(glob.glob(os.path.join(flags, "ready", "*.json")) + glob.glob(os.path.join(flags, "ready", "*", "*.json"))):
        try:
            with open(p) as fh:
                m = json.load(fh)
        except (OSError, ValueError):
            continue
        oid = m.get("id") if isinstance(m, dict) else None
        if not oid or oid == rid or _terminal(flags, oid):
            continue
        for q in manifest_paths(m):
            if overlaps(q, root):
                return f"{oid} ({q})"
    return None


def pinned(flags, rid):
    """-> the matching glob if <flags>/filing-no-reclaim.globs pins this row id, else None."""
    try:
        with open(os.path.join(flags, "filing-no-reclaim.globs")) as fh:
            for ln in fh:
                g = ln.split("#", 1)[0].strip()
                if g and fnmatch.fnmatch(rid, g):
                    return g
    except OSError:
        pass
    return None
