#!/usr/bin/env python3
"""holds.py — THE reader/writer of `handoffs/active/holds.yaml` for the dispatcher side (handoff standard Stage C, C3).

holds.yaml is the single operator-exclusion source (operator decision 3). Shape = F4's FLAT form (publish_row.load_holds
documents it): each hold has `id`, `scope` (loop-launch | all-rows | boxes), flat target keys
`sessions / handoffs / rows / boxes / files`, optional `row_prefixes`, `since`, `by`, `reason`.

Readers here: token_guards (session launch gate = a hold whose `sessions` names the slug, any scope), handoff_sessions
(`gate` / `unpark` WRITE holds.yaml; the registry `operator_gate` field is a CACHE synced from it by `sync_registry`).
publish_row keeps its own F4 loader (installed without this file); box_index reads the same keys.
"""
from __future__ import annotations

import os
import re
import sys

REL = "handoffs/active/holds.yaml"
SCOPES = ("loop-launch", "all-rows", "boxes")
TARGET_KEYS = ("sessions", "handoffs", "rows", "boxes", "files")
OWNER_PREFIX_RX = re.compile(r"^(handoff-|h-)")
CACHE_SOURCE = "holds.yaml"
HEADER = """# Operator holds -- the single exclusion source (handoff standard decision 3; schema: scripts/coordination/holds.py).
# Written by the operator and by `handoff_sessions.py gate|unpark`; every reader derives from this file.
#
# Keys per hold: id, scope, sessions, handoffs, rows, boxes (ID or text_sha), files, row_prefixes, since, by, reason.
# Scope semantics PER READER:
#   dispatcher (handoff_sessions launch gate, taskflow/select, generated index rows, backlog_row_check):
#       EVERY scope holds -- a held session is never spawned, a held handoff/box is never selected.
#       EXCEPT `launch_only: true` (loop-launch only): the hold gates launching/relaunching the loop -- its sessions
#       and any launch box named in `boxes` -- and does NOT propagate to the boxes of its handoffs/rows/files
#       (provenance only). Boxes keep their own [operator] / gate. (operator ruling 2026-11-22, AK holds)
#   rowflow publish_row (F4): loop-launch admits a row by its OWN owner (refused only when the owner is a held
#       session, or the row names no owner); all-rows also refuses every row whose handoff/id/box is a target;
#       row_prefixes refuse any matching row id whatever its scope. Release: operator-ratify/<hold id>.json.
# FAIL CLOSED: a missing or unreadable file never means "no holds" -- registry gates + default row prefixes stay,
# every box is marked HOLDS-UNAVAILABLE and `index_state.py --check` fails with BAD HOLD.
# CAVEAT: during a holds outage publish_row enforces only the registry gates + default row prefixes, so a
# FILE-ONLY hold (one with no registry operator_gate twin, e.g. rocm-kernel-authoring) does not refuse rows
# until the file parses again; the dispatcher side (select, generated rows) still holds everything.
"""


def slug_of(x) -> str:
    return OWNER_PREFIX_RX.sub("", str(x or ""))


def path(root: str | None = None) -> str:
    """root pinned (or $EPYC_HOLDS_ROOT) -> <root>/handoffs/active/holds.yaml; else the HUB VIEW first
    (toolroot.resolve, F5: /mnt/raid0/llm/views/epyc-root-main tracks origin/main), never a stale shared checkout."""
    root = root or os.environ.get("EPYC_HOLDS_ROOT") or None
    if root:
        return os.path.join(root, REL)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import toolroot
        return toolroot.resolve(REL, __file__)
    except Exception:  # noqa: BLE001
        return os.path.join("/workspace", REL)
    finally:
        sys.path.pop(0)


def load(root: str | None = None) -> list[dict] | None:
    """The hold list, or None when the file is MISSING or UNREADABLE. FAIL CLOSED: None means "no source", never
    "no holds" -- callers keep the registry gate cache and DEFAULT_GATED_ROW_PREFIXES and log HOLDS-SOURCE-MISSING."""
    p = path(root)
    if not os.path.exists(p):
        print(f"HOLDS-SOURCE-MISSING: {p} absent; keeping registry gates + default prefixes", file=sys.stderr)
        return None
    try:
        import yaml
        doc = yaml.safe_load(open(p, encoding="utf-8").read())
        if not isinstance(doc, dict) or not isinstance(doc.get("holds"), list):
            raise ValueError("no top-level `holds:` list")
    except Exception as e:  # noqa: BLE001
        print(f"HOLDS-SOURCE-MISSING: {p} unreadable ({type(e).__name__}: {e}); keeping registry gates + default "
              f"prefixes", file=sys.stderr)
        return None
    items = doc.get("holds")
    if isinstance(items, dict):
        items = [{"id": k, **(v if isinstance(v, dict) else {})} for k, v in items.items()]
    return [h for h in (items or []) if isinstance(h, dict) and h.get("id")]


def held_sessions(holds: list[dict] | None) -> dict[str, dict]:
    """{session slug: hold} for every hold naming sessions (handoff-/h- prefixes normalised)."""
    out = {}
    for h in holds or []:
        for s in h.get("sessions") or []:
            if slug_of(s):
                out.setdefault(slug_of(s), h)
    return out


def validate(holds: list[dict] | None) -> list[str]:
    """Schema problems (index_state --check BAD HOLD reuses these)."""
    errs, seen = [], set()
    for h in holds or []:
        hid = str(h.get("id"))
        if hid in seen:
            errs.append(f"duplicate hold id {hid}")
        seen.add(hid)
        if str(h.get("scope") or "loop-launch") not in SCOPES:
            errs.append(f"hold {hid}: scope {h.get('scope')!r} not in {SCOPES}")
        if not any(h.get(k) for k in TARGET_KEYS) and not h.get("row_prefixes"):
            errs.append(f"hold {hid}: no targets")
        lo = h.get("launch_only")
        if lo is not None and not isinstance(lo, bool):
            errs.append(f"hold {hid}: launch_only must be a bool")
        if lo is True and str(h.get("scope") or "loop-launch") != "loop-launch":
            errs.append(f"hold {hid}: launch_only requires scope loop-launch")
        if lo is True and not (h.get("sessions") or h.get("boxes")):
            errs.append(f"hold {hid}: launch_only needs sessions or launch boxes to gate")
        for k in TARGET_KEYS + ("row_prefixes",):
            if h.get(k) is not None and not isinstance(h.get(k), list):
                errs.append(f"hold {hid}: {k} must be a list")
    return errs


def _write(holds: list[dict], root: str | None) -> str:
    import yaml
    p = path(root)
    tmp = f"{p}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(HEADER)
        f.write(yaml.safe_dump({"holds": holds}, sort_keys=False, allow_unicode=True))
    os.replace(tmp, p)
    return p


def add_session_hold(slug: str, reason: str, since: str, by: str = "handoff_sessions gate",
                     handoff: str | None = None, root: str | None = None) -> str:
    holds = load(root) or []
    if not os.path.isdir(os.path.dirname(path(root))):
        raise FileNotFoundError(path(root))
    if slug in held_sessions(holds):
        return path(root)
    h = {"id": slug, "scope": "loop-launch", "sessions": [slug], "since": since, "by": by, "reason": reason}
    if handoff:
        h["handoffs"] = [os.path.basename(handoff)]
    return _write(holds + [h], root)


def remove_session_hold(slug: str, root: str | None = None) -> bool:
    """Drop every hold whose ONLY target is this session (a hold that also names other targets keeps them)."""
    holds = load(root)
    if holds is None:
        return False
    out, changed = [], False
    for h in holds:
        ss = [s for s in h.get("sessions") or [] if slug_of(s) != slug]
        if len(ss) != len(h.get("sessions") or []):
            changed = True
            others = any(h.get(k) for k in ("rows", "boxes", "files")) or h.get("row_prefixes")
            if not ss and not others:
                continue
            h = {**h, "sessions": ss}
        out.append(h)
    if changed:
        _write(out, root)
    return changed


def sync_registry(reg: dict, holds: list[dict] | None) -> list[str]:
    """Make registry `operator_gate` a cache of holds.yaml: a held session gets `operator_gate` (source holds.yaml); a
    cached gate whose hold is gone is dropped -- ONLY gates this function derived (source holds.yaml); gates set by the
    `gate` subcommand (source operator) and legacy gates are never dropped here. FAIL CLOSED: no-op when the file is
    missing or unreadable (holds is None). Returns the slugs changed."""
    if holds is None:
        return []
    hs = held_sessions(holds)
    changed = []
    for slug, e in (reg.get("sessions") or {}).items():
        if not isinstance(e, dict):
            continue
        g = e.get("operator_gate")
        if slug in hs:
            h = hs[slug]
            if not g:
                e["operator_gate"] = {"reason": h.get("reason") or f"hold {h['id']}", "since": h.get("since"),
                                      "source": CACHE_SOURCE, "hold": h["id"]}
                changed.append(slug)
            elif isinstance(g, dict) and g.get("hold") != h["id"]:
                g["hold"] = h["id"]
        elif isinstance(g, dict) and g.get("source") == CACHE_SOURCE:
            e.pop("operator_gate", None)
            changed.append(slug)
    return changed
