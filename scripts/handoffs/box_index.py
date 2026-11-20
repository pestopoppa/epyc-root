#!/usr/bin/env python3
"""box_index.py — build `handoffs/active/.box-index.json` (schema `epyc.box-index.v1`, handoff standard Rev 1 §4).

Generated, never hand-written. Called by `index_state.py` (regen path writes it; `--check` warns when stale).
Sources: the live handoff files, `backlog-priority.json` (row rank), `holds.yaml` if present (first existing path in
HOLDS_CANDIDATES). Deterministic: no wall-clock field, sorted keys, stable key derivation. (Field f path existence
reads the filesystem and the origin/main tree, as `task_lint` does.)

KEY: the box's `**ID**` when that ID names exactly one indexed box; otherwise `<file>#<text_sha>` (ids are not yet
unique in legacy handoffs). IDENTITY: `text_sha` = sha256 of the normalised first line (checkbox marker and a trailing
`✅ …` tick suffix removed, whitespace collapsed), truncated to TEXT_SHA_LEN hex chars. The tick suffix is
`✅ <date> [belief: …|no-belief: …] <verdict>` (flip_checkbox.tick_suffix) and always comes AFTER the task text, so
stripping from the first `✅` leaves the identity unchanged when a box is ticked. (A `✅` inside the task text itself
would truncate the identity; the first line is immutable, so the sha stays stable either way.)

Ticked boxes are omitted (INCLUDE_DONE) but their ids stay in known_ids so a gate on a finished box resolves; the
belief-tag ratio over ticks therefore cannot come from this file — read it with flip_checkbox.parse_tick over the
handoffs (belief_capture_check / verdict_count do).

STORAGE: gitignored, rebuilt on read by load() (Stage B decision; see load()).

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


_TRACK_FROZEN = re.compile(r"^\s*(?:[-*]\s*)?❄\s*frozen until\s*:\s*(.+?)\s*$", re.I)
_FILE_FROZEN = re.compile(r"^\*\*Status\*\*:\s*FROZEN\b.*?(?:frozen until\s*:\s*(.+?))?(?:\s*\(was:.*)?$", re.I)


def file_frozen(lines: list[str]) -> str | None:
    """`**Status**: FROZEN …` in the header (first 60 lines) -> the until-event (or "FROZEN"), else None."""
    for line in lines[:60]:
        m = _FILE_FROZEN.match(line.strip())
        if m:
            return (m.group(1) or "FROZEN").strip()
    return None


def sections(lines: list[str]) -> list[tuple[str | None, bool, int, str | None, bool]]:
    """Per line (0-based): (track or None, under `### Backlog`?, backlog section start, track frozen_until, fenced?).

    Fence-aware (a box inside ``` is an example, never a task). A track-level `❄ frozen until: X` line (written by
    `handoff_box.py freeze --track`) sits between the `## Track:` heading and its first `###`; its event is
    inherited by every box of that track."""
    out, track, backlog, start, fence, tfrozen, before_h3 = [], None, False, -1, None, None, False
    for i, line in enumerate(lines):
        f = _FENCE.match(line)
        if f:
            mark = f.group(1)[0]
            fence = mark if fence is None else (None if fence == mark else fence)
            out.append((track, backlog, start, tfrozen, True))
            continue
        if fence is None:
            m = _TRACK.match(line)
            if m:
                track, backlog, tfrozen, before_h3 = m.group(1), False, None, True
            elif _H2.match(line):
                track, backlog, tfrozen, before_h3 = None, False, None, False
            else:
                h = _H3.match(line)
                if h:
                    backlog = h.group(1).strip().lower() == "backlog"
                    start, before_h3 = i, False
                elif track and before_h3:
                    fm = _TRACK_FROZEN.match(line)
                    if fm:
                        tfrozen = fm.group(1)
        out.append((track, backlog, start, tfrozen, fence is not None))
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
          row_open: dict[str, bool], priority: dict, track_open: dict[str, bool] | None = None) -> dict:
    """files: {name: path}; handoff_rows: {name: row id}; row_open: {row id: has open work}; priority: backlog doc."""
    holds = load_holds(root)
    prows = priority.get("rows", {}) if isinstance(priority, dict) else {}
    recs, open_ids, known_ids = [], set(), set()
    for name, path in sorted(files.items()):
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        sec = sections(lines)
        ffrozen = file_frozen(lines)
        has_backlog = any(s_[1] for s_ in sec)
        pos: dict[int, int] = {}
        for i, line in enumerate(lines):
            if sec[i][4]:
                continue                        # fenced: an example, not a box
            m = L1.CHECKBOX.match(line)
            if not m:
                continue
            bid = L1.head_id(line)
            if bid:
                known_ids.add(bid)
            st = m.group(2)
            if st in "xX" and not INCLUDE_DONE:
                continue
            txt, ch = L1.block(lines, i)
            r = TL.dispatch_result(txt, ch)
            if st not in "xX" and bid:
                open_ids.add(bid)
            track, in_backlog, bstart, tfrozen, _ = sec[i]
            inherited = r["frozen_until"] or tfrozen or ffrozen
            state = r["state"]
            if inherited and state in ("open", "needs-owner"):
                state = "frozen"                # track / whole-file freeze propagates to its boxes (review S2)
            own_txt, _nums = L1.own_block(lines, i)
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
                   "state": state, "lint": {"ok": r["ok"], "fails": list(r["fails"])},
                   "row": row, "row_rank": (prows.get(row) or {}).get("rank") if row else None,
                   "pos_in_backlog": p, "cont_lines": len(own_txt.split("\n")) - 1, "frozen_until": inherited,
                   "outside_backlog": bool(has_backlog and not in_backlog and st not in "xX"),
                   "holds": sorted(h["id"] for h in holds if {name, row, r["id"]} & h["targets"])}
            if rec["outside_backlog"]:
                rec["lint"]["warn"] = ["outside-backlog"]
            if st in "xX":
                t = parse_tick(line) or {}
                rec["ticked"] = {"date": t.get("date"), "belief": t.get("belief"), "verdict": t.get("verdict") or None,
                                 "form": t.get("form")}
                rec["state"] = "done"
            recs.append(rec)
    topen = {k.lower(): v for k, v in (track_open or {}).items()}
    for rec in recs:
        unresolved, unknown = [], []
        for g in rec["gate"]:
            if "#" in g and g.lower() in topen:          # ROW#track ref, resolved through .index-state.json tracks
                if topen[g.lower()]:
                    unresolved.append(g)
            elif g in row_open:
                if row_open[g]:
                    unresolved.append(g)
            elif g in open_ids:
                unresolved.append(g)
            elif g not in known_ids:
                unknown.append(g)                        # review S3: a lint failure, NOT an open gate
        rec["gate_open"] = bool(unresolved)
        rec["gate_unknown"] = unknown
        if unknown and rec["state"] != "done":
            rec["lint"]["fails"].append("g-gate-unknown")
            rec["lint"]["ok"] = False
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
    counts["outside_backlog"] = sum(1 for r in recs if r.get("outside_backlog"))
    return {"schema": SCHEMA, "include_done": INCLUDE_DONE, "counts": counts, "limits": limit_findings(files, recs, root),
            "holds_source": next((h for h in HOLDS_CANDIDATES if (root / h).exists()), None), "boxes": boxes}


DISPATCH_CLASSES = ("non-inference", "inference")


def skip_reason(rec: dict, exclude: set[str] | frozenset = frozenset()) -> str | None:
    """THE dispatchable predicate (handoff standard Stage C, C0.1): why this record is NOT dispatchable, or None.
    Shared by taskflow/select.py and index_state.generated_next_action so a generated row never names a box the
    dispatcher would refuse."""
    if Path(rec.get("file", "")).name in exclude:
        return "excluded-file"
    st = rec.get("state")
    if st != "open":
        return f"state-{st}"
    if rec.get("proposed_by"):
        return "proposal-pending"
    if rec.get("class") not in DISPATCH_CLASSES:
        return f"class-{rec.get('class')}"
    if rec.get("holds"):
        return "held"
    if rec.get("gate_open"):
        return "gate-open"
    if rec.get("inputs_missing"):
        return "inputs-missing"
    if rec.get("outside_backlog"):
        return "outside-backlog"
    if not (rec.get("lint") or {}).get("ok"):
        return "lint-fail"
    return None


def dispatchable(rec: dict, exclude: set[str] | frozenset = frozenset()) -> bool:
    return skip_reason(rec, exclude) is None


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


FRESHNESS_SOURCES = ("handoffs/active", "handoffs/blocked")
FRESHNESS_FILES = ("handoffs/active/backlog-priority.json", "handoffs/active/.index-state.json") + HOLDS_CANDIDATES
INDEX_REL = "handoffs/active/.box-index.json"


def _newest_source_mtime(root: Path) -> float:
    m = 0.0
    for d in FRESHNESS_SOURCES:
        p = root / d
        if p.is_dir():
            for f in p.glob("*.md"):
                try:
                    m = max(m, f.stat().st_mtime)
                except OSError:
                    pass
    for rel in FRESHNESS_FILES:
        try:
            m = max(m, (root / rel).stat().st_mtime)
        except OSError:
            pass
    return m


LOCK_REL = "handoffs/active/.box-index.json.lock"
BUILD_TIMEOUT_S = 120


def load(root: Path | str | None = None, regenerate: bool = True) -> dict:
    """THE reader entry point. `.box-index.json` is gitignored (decision, Stage B: a committed 1.3 MB artefact made
    46k-line diffs on every regen and would trip the commit-bloat guard); it is rebuilt here whenever it is missing
    or older than any handoff / priority / state / holds source.

    C0.2 (Stage C): the rebuild runs `index_state.py --box-index`, which is the box build ONLY (~5 s, no classify,
    no pickaxe, no ledger), under an exclusive flock on `.box-index.json.lock` -- concurrent callers wait for the one
    build and then re-check freshness instead of building again. On any failure the LAST copy is returned with
    `"stale": true` (and `"stale_reason"`) instead of `{}`; `{}` only when no copy has ever been built. Callers must
    check `doc.get("stale")` and log `box-index stale/unavailable` (see `stale_note`)."""
    import fcntl
    import subprocess
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    p = root / INDEX_REL

    def _fresh() -> bool:
        try:
            return p.exists() and p.stat().st_mtime >= _newest_source_mtime(root)
        except OSError:
            return False

    reason = None
    if regenerate and not _fresh():
        try:
            with open(root / LOCK_REL, "a+") as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                try:
                    if not _fresh():                     # another caller may have built it while we waited
                        r = subprocess.run([sys.executable, str(root / "scripts/handoffs/index_state.py"), "--box-index"],
                                           cwd=str(root), capture_output=True, text=True, timeout=BUILD_TIMEOUT_S)
                        if r.returncode != 0:
                            reason = f"build rc={r.returncode}: {(r.stderr or r.stdout).strip()[-300:]}"
                finally:
                    fcntl.flock(lk, fcntl.LOCK_UN)
        except Exception as exc:  # noqa: BLE001 -- a failed rebuild degrades to the last copy, never to {}
            reason = f"build failed: {type(exc).__name__}: {exc}"
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"stale": True, "stale_reason": reason or f"unreadable: {type(exc).__name__}", "boxes": {},
                "counts": {}} if reason or p.exists() else {}
    if reason or not _fresh():
        doc["stale"] = True
        doc["stale_reason"] = reason or "older than its sources (regenerate=False or concurrent edit)"
    return doc


def stale_note(doc: dict, who: str) -> str | None:
    """One log line for a caller that got a stale/unavailable index, else None."""
    if not doc or not doc.get("boxes"):
        return f"{who}: box-index unavailable ({(doc or {}).get('stale_reason', 'never built')})"
    if doc.get("stale"):
        return f"{who}: box-index stale ({doc.get('stale_reason')}); using last copy"
    return None


def dumps(doc: dict) -> str:
    return json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
