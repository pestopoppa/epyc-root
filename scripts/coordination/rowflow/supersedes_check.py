#!/usr/bin/env python3
"""supersedes_check.py - computed `supersedes` at publish (AK row-robustness RCA 2026-11-24 item 4 / F7).

`supersedes` was a hand-typed id: ak-gvfattn-served-gpu-20261124-r3 named r2 (already smoke-FAILed and unpublished) but
not r1, which an audit still saw GRANTABLE with a PASS hours later. The publisher now DERIVES the predecessor set: every
live row (ready manifest, queued smoke / unpublished manifest, or a dry-run PASS) of the same family prefix with a lower
-rN, plus - transitively through ready/.superseded/ markers - anything those predecessors superseded that is still live.
The spec may only ADD to it. WARN-first (operator rule: new checks warn first); SUPERSEDES_ENFORCE flips it to a refusal.

Read-only over the flags dir; no rowflow import."""
from __future__ import annotations

import glob
import json
import os
import re

SUPERSEDES_ENFORCE = False

_REV = re.compile(r"^(?P<fam>.+?)(?:-r(?P<n>\d+))?$")


def family_rev(rid: str):
    """('ak-x-20261124', 1) for the bare id, ('ak-x-20261124', 3) for ...-r3."""
    m = _REV.match(str(rid))
    return m.group("fam"), int(m.group("n") or 1)


def _load(p):
    try:
        with open(p) as f:
            v = json.load(f)
        return v if isinstance(v, dict) else None
    except (OSError, ValueError):
        return None


def _sup_list(d):
    s = (d or {}).get("supersedes")
    return [s] if isinstance(s, str) and s else [x for x in (s or []) if isinstance(x, str) and x] if isinstance(s, list) else []


def _done(flags, rid):
    return any(os.path.exists(p) for p in (os.path.join(flags, "grants", rid + ".complete"),
                                            os.path.join(flags, "grants", rid + ".ended"),
                                            os.path.join(flags, "filing-done", rid + ".FILED"),
                                            os.path.join(flags, "dryrun", rid, "SMOKE-RESULT.json")))


def live_ids(flags) -> dict:
    """{row id: why-live} over ready/*.json, dryrun/*/unpublished.json, dryrun/*/*SMOKE-QUEUED.json, dryrun/*/PASS.json;
    a row that is done (ended/complete/FILED/smoke RESULT) is not live."""
    out = {}
    for p in glob.glob(os.path.join(flags, "ready", "*.json")):
        out.setdefault(os.path.basename(p)[:-5], "manifest")
    for pat, why in (("unpublished.json", "queued"), ("*SMOKE-QUEUED.json", "queued"), ("PASS.json", "PASS")):
        for p in glob.glob(os.path.join(flags, "dryrun", "*", pat)):
            out.setdefault(os.path.basename(os.path.dirname(p)), why)
    return {r: w for r, w in out.items() if not _done(flags, r)}


def superseded_markers(flags) -> dict:
    """{predecessor: successor} from ready/.superseded/<pred>.json {by}."""
    out = {}
    for p in glob.glob(os.path.join(flags, "ready", ".superseded", "*.json")):
        b = (_load(p) or {}).get("by")
        if b:
            out[os.path.basename(p)[:-5]] = str(b)
    return out


def derived_predecessors(flags, rid: str, live=None, markers=None) -> dict:
    """{predecessor id: why} that publishing `rid` must supersede."""
    live = live_ids(flags) if live is None else live
    markers = superseded_markers(flags) if markers is None else markers
    fam, n = family_rev(rid)
    lower = {r for r in set(live) | set(markers) | set(markers.values())
             if r != rid and family_rev(r)[0] == fam and family_rev(r)[1] < n}
    # transitive through .superseded/: a marker whose successor is a (lower) family member names a predecessor too
    changed = True
    while changed:
        changed = False
        for pred, by in markers.items():
            if by in lower and pred not in lower and pred != rid:
                lower.add(pred)
                changed = True
    return {r: live[r] for r in sorted(lower) if r in live}


def check(spec: dict, flags: str):
    """(missing {id: why}, message or None). Message is None when the declared supersedes covers every live predecessor."""
    rid = str(spec.get("id") or "")
    if not rid:
        return {}, None
    declared = set(_sup_list(spec))
    missing = {r: w for r, w in derived_predecessors(flags, rid).items() if r not in declared}
    if not missing:
        return {}, None
    return missing, (f"SUPERSEDES-INCOMPLETE: {rid} supersedes {sorted(declared) or '[]'} but omits live predecessor(s) "
                     + ", ".join(f"{r} ({w})" for r, w in missing.items())
                     + "; add them to spec.supersedes")
