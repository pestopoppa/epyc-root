#!/usr/bin/env python3
"""Resolve retired handoff file names / row ids through handoffs/active/.folded.json.

The 2026-11 backlog refactor folded 176 handoffs into 29 and recorded the redirects in
``handoffs/active/.folded.json`` (``{files, ids}``; each value is a string or
``{target, track}``). Scripts that carry HISTORICAL handoff names (migrations, back-fills)
must not be rewritten; they resolve the name at runtime with this helper instead.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FOLDED_REL = Path("handoffs") / "active" / ".folded.json"


def load_folded(root: Path = ROOT) -> dict:
    path = root / FOLDED_REL
    if not path.exists():
        return {"files": {}, "ids": {}}
    data = json.loads(path.read_text())
    return {"files": data.get("files", {}), "ids": data.get("ids", {})}


def _norm(value) -> tuple[str, str | None]:
    if isinstance(value, str):
        return value, None
    return value["target"], value.get("track")


def resolve_handoff_file(
    name: str, root: Path = ROOT, folded: dict | None = None, with_anchor: bool = False
) -> str:
    """Map ``handoffs/<dir>/<file>.md`` (or a bare file name) to its current home.

    A name that still exists on disk, or is not a key in ``.folded.json``, is returned
    unchanged (a name moved to ``handoffs/completed/`` resolves there). A folded name is rewritten to ``handoffs/active/<target>`` (plus
    ``#track-<track>`` when ``with_anchor`` and the redirect carries a track).
    """
    folded = load_folded(root) if folded is None else folded
    base = name.rsplit("/", 1)[-1]
    if (root / name).exists():
        return name
    if base not in folded["files"]:
        # Not folded, but possibly archived: a completed handoff keeps its name.
        done = f"handoffs/completed/{base}"
        if name.startswith("handoffs/active/") and (root / done).exists():
            return done
        return name
    target, track = _norm(folded["files"][base])
    out = f"handoffs/active/{target}"
    if with_anchor and track:
        out += f"#track-{track}"
    return out


def resolve_row_id(row_id: str, root: Path = ROOT, folded: dict | None = None) -> str:
    """Map a retired row id to its surviving id (unchanged if not retired)."""
    folded = load_folded(root) if folded is None else folded
    if row_id not in folded["ids"]:
        return row_id
    return _norm(folded["ids"][row_id])[0]


def dedupe(routes: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for r in routes:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out
