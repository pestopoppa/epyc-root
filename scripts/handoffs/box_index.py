#!/usr/bin/env python3
"""box_index.py — build `handoffs/active/.box-index.json` (schema `epyc.box-index.v1`, handoff standard Rev 1 §4).

Generated, never hand-written. Called by `index_state.py` (regen path writes it; `--check` warns when stale).
Sources: the live handoff files, `backlog-priority.json` (row rank), `holds.yaml` if present (first existing path in
HOLDS_CANDIDATES). Deterministic: no wall-clock field, sorted keys, stable key derivation. (Field f path existence
reads the filesystem and the origin/main tree, as `task_lint` does.)

KEY: the box's `**ID**` when that ID names exactly one indexed box; otherwise `<file>#<text_sha>` (ids are not yet
unique in legacy handoffs). IDENTITY: `text_sha` = sha256 of the normalised first line (checkbox marker and a trailing
`✅ …` tick suffix removed, whitespace collapsed), truncated to TEXT_SHA_LEN hex chars.

`gate_open` = True when at least one `· gate:` ref is still unresolved, i.e. the box is BLOCKED (spec §2.2: blocked is
derived from open gates, not a marker). A ref resolves when it names an index row whose handoff has no open/blocked
box, or a box id with no open box left. A ref that names nothing known stays open and is listed in `gate_unknown`.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import task_lint as TL  # noqa: E402
import task_lint_core as L1  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "coordination"))
from flip_checkbox import parse_tick  # noqa: E402  (shared reader of the ONE tick suffix + legacy forms)

SCHEMA = "epyc.box-index.v1"
TEXT_SHA_LEN = 16          # hex chars of sha256 kept as identity
TEXT_MAX = 240             # chars of the first line stored in `text` (identity is text_sha, never the truncation)
INCLUDE_DONE = False       # ticked boxes (6k+) are omitted to keep the artefact small; flip to index them as `done`
HOLDS_CANDIDATES = ("handoffs/active/holds.yaml", "coordination/holds.yaml")

_TRACK = re.compile(r"^##\s+Track:\s*(.+?)\s*#*\s*$")
_H2 = re.compile(r"^#{1,2}\s")
_H3 = re.compile(r"^###\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```+|~~~+)")
_TICK_SUFFIX = re.compile(r"\s*✅.*$")
_ROW_ID = re.compile(r"^[A-Z]{3}-\d+$")


def text_sha(first_line: str) -> str:
    m = L1.CHECKBOX.match(first_line)
    body = m.group(3) if m else first_line
    body = " ".join(_TICK_SUFFIX.sub("", body).split())
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:TEXT_SHA_LEN]


def sections(lines: list[str]) -> list[tuple[str | None, bool, int]]:
    """Per line (0-based): (track name or None, under `### Backlog`?, backlog section start). Fence-aware."""
    out, track, backlog, start, fence = [], None, False, -1, None
    for i, line in enumerate(lines):
        f = _FENCE.match(line)
        if f:
            mark = f.group(1)[0]
            fence = mark if fence is None else (None if fence == mark else fence)
        elif fence is None:
            m = _TRACK.match(line)
            if m:
                track, backlog = m.group(1), False
            elif _H2.match(line):
                track, backlog = None, False
            else:
                h = _H3.match(line)
                if h:
                    backlog = h.group(1).strip().lower() == "backlog"
                    start = i
        out.append((track, backlog, start))
    return out


def load_holds(root: Path) -> list[dict]:
    for rel in HOLDS_CANDIDATES:
        p = root / rel
        if not p.exists():
            continue
        try:
            import yaml
            doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001 — a broken holds file degrades to no holds, never a crash
            return []
        items = doc.get("holds", doc) if isinstance(doc, dict) else doc
        if isinstance(items, dict):
            items = [{"id": k, **(v if isinstance(v, dict) else {})} for k, v in items.items()]
        out = []
        for h in items or []:
            if isinstance(h, dict) and h.get("id"):
                out.append({"id": str(h["id"]),
                            "targets": {str(x) for k in ("handoffs", "rows", "boxes", "files") for x in (h.get(k) or [])}})
        return out
    return []


def build(root: Path, files: dict[str, Path], handoff_rows: dict[str, str | None],
          row_open: dict[str, bool], priority: dict) -> dict:
    """files: {name: path}; handoff_rows: {name: row id}; row_open: {row id: has open work}; priority: backlog doc."""
    holds = load_holds(root)
    prows = priority.get("rows", {}) if isinstance(priority, dict) else {}
    recs, open_ids, known_ids = [], set(), set()
    for name, path in sorted(files.items()):
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        sec = sections(lines)
        pos: dict[int, int] = {}
        for i, line in enumerate(lines):
            m = L1.CHECKBOX.match(line)
            if not m:
                continue
            idm = TL.BOX_ID.match(line)
            if idm:
                known_ids.add(idm.group(1))
            st = m.group(2)
            if st in "xX" and not INCLUDE_DONE:
                continue
            txt, ch = L1.block(lines, i)
            r = TL.dispatch_result(txt, ch)
            if st not in "xX" and idm:
                open_ids.add(idm.group(1))
            track, in_backlog, bstart = sec[i]
            p = None
            if in_backlog and st not in "xX" and len(m.group(1)) == 0:
                pos[bstart] = pos.get(bstart, 0) + 1
                p = pos[bstart]
            row = handoff_rows.get(name)
            rec = {"file": str(path.relative_to(root)), "line": i + 1, "track": track,
                   "text_sha": text_sha(line), "text": " ".join(line.split())[:TEXT_MAX],
                   "id": r["id"], "class": r["class"], "class_basis": r["class_basis"], "standard": r["standard"],
                   "done_when": r["done_when"], "gate": r["gate"], "inputs": r["inputs"],
                   "inputs_missing": r["inputs_missing"], "tier": r["tier"], "owner": r["owner"],
                   "state": r["state"], "lint": {"ok": r["ok"], "fails": r["fails"]},
                   "row": row, "row_rank": (prows.get(row) or {}).get("rank") if row else None,
                   "pos_in_backlog": p, "cont_lines": len(txt.split("\n")) - 1, "frozen_until": r["frozen_until"],
                   "holds": sorted(h["id"] for h in holds if {name, row, r["id"]} & h["targets"])}
            if st in "xX":
                t = parse_tick(line) or {}
                rec["ticked"] = {"date": t.get("date"), "belief": t.get("belief"), "verdict": t.get("verdict") or None,
                                 "form": t.get("form")}
                rec["state"] = "done"
            recs.append(rec)
    for rec in recs:
        unresolved, unknown = [], []
        for g in rec["gate"]:
            if g in row_open:
                if row_open[g]:
                    unresolved.append(g)
            elif g in open_ids:
                unresolved.append(g)
            elif g not in known_ids:
                unresolved.append(g)
                unknown.append(g)
        rec["gate_open"] = bool(unresolved)
        rec["gate_unknown"] = unknown
    ids: dict[str, int] = {}
    for rec in recs:
        if rec["id"]:
            ids[rec["id"]] = ids.get(rec["id"], 0) + 1
    boxes, counts = {}, {}
    for rec in recs:
        key = rec["id"] if rec["id"] and ids[rec["id"]] == 1 else f"{rec['file']}#{rec['text_sha']}"
        n, k = 2, key
        while k in boxes:
            k, n = f"{key}~{n}", n + 1
        boxes[k] = rec
        counts[rec["state"]] = counts.get(rec["state"], 0) + 1
    counts["blocked"] = sum(1 for r in recs if r["gate_open"])
    counts["lint_ok"] = sum(1 for r in recs if r["lint"]["ok"])
    counts["total"] = len(recs)
    return {"schema": SCHEMA, "include_done": INCLUDE_DONE, "counts": counts, "limits": limit_findings(files, recs, root),
            "holds_source": next((h for h in HOLDS_CANDIDATES if (root / h).exists()), None), "boxes": boxes}


def limit_findings(files: dict[str, Path], recs: list[dict], root: Path) -> list[str]:
    """Size-limit warnings (operator decision 4): open boxes per track, continuation lines per box, lines per file."""
    out, per_track = [], {}
    for r in recs:
        if r["state"] != "done":
            per_track[(r["file"], r["track"])] = per_track.get((r["file"], r["track"]), 0) + 1
        if r.get("cont_lines", 0) > TL.MAX_CONTINUATION_LINES:
            out.append(f"box {r['file']}:{r['line']} has {r['cont_lines']} continuation lines > {TL.MAX_CONTINUATION_LINES}")
    for (f, t), n in sorted(per_track.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
        if t and n > TL.MAX_OPEN_PER_TRACK:
            out.append(f"track {f}#{t} has {n} open boxes > {TL.MAX_OPEN_PER_TRACK}")
    for name, path in sorted(files.items()):
        n = path.read_text(encoding="utf-8", errors="replace").count("\n")
        if n > TL.SPLIT_HANDOFF_LINES:
            out.append(f"file {path.relative_to(root)} has {n} lines > {TL.SPLIT_HANDOFF_LINES}: split by track")
        elif n > TL.MAX_HANDOFF_LINES:
            out.append(f"file {path.relative_to(root)} has {n} lines > {TL.MAX_HANDOFF_LINES}: compact History")
    return out


def dumps(doc: dict) -> str:
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
