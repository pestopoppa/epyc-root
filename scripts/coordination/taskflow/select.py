#!/usr/bin/env python3
"""taskflow/select.py — pick the next dispatchable handoff box from `handoffs/active/.box-index.json`.

Dispatcher redesign rev 2 §2.1 (DESIGN.md beside HANDOFF-STANDARD.md), handoff standard Rev 1 §4. Deterministic, no LLM,
read-only. A LIBRARY for the later taskflow build: it is NOT wired into handoff_sessions.py.

Order: `row_rank` ascending (backlog-priority.json; unranked rows last), then file, then box position (`### Backlog`
position first, file line as the tie-break). A box is admitted only when ALL hold:

  state == "open"                not frozen / roll-up / needs-owner / done
  class in DISPATCH_CLASSES      non-inference | inference (never operator-decision / blocked-external / roll-up)
  not gate_open                  every `· gate:` ref resolved
  no holds                       holds.yaml targets nothing on it
  lint.ok                        task_lint dispatch verdict (done-condition, inputs, …)
  no inputs_missing              every declared input exists
  not outside_backlog            an open box under History/Done of a standard file is a placement error
  file not excluded              handoffs already in flight (--exclude / in_flight); holds come from holds.yaml

`select()` returns (record | None, skip histogram). The histogram is the authoring-debt gauge (DESIGN §2.6).

    python3 scripts/coordination/taskflow/select.py [--json] [--top N] [--exclude file.md ...]
"""
from __future__ import annotations

import sys
import os as _os

# This file is named like the stdlib `select` module (DESIGN.md names it). Run as a script, its own directory would be
# sys.path[0] and shadow the stdlib for subprocess & co, so drop it. Import it as `taskflow.select`.
if sys.path and _os.path.abspath(sys.path[0] or ".") == _os.path.dirname(_os.path.abspath(__file__)):
    sys.path.pop(0)

import argparse
import collections
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DISPATCH_CLASSES = ("non-inference", "inference")
# Operator holds come from handoffs/active/holds.yaml ONLY (handoff standard C3): box_index puts the covering hold ids
# on each record (`holds`) and the shared predicate skips them. No private exclusion list.
EXCLUDE_FILES: tuple[str, ...] = ()


def load_index(root: Path | None = None) -> dict:
    """The box index via box_index.load() (rebuilt when stale or missing; it is gitignored)."""
    root = root or REPO_ROOT
    sys.path.insert(0, str(root / "scripts" / "handoffs"))
    import box_index
    doc = box_index.load(root)
    note = box_index.stale_note(doc, "taskflow.select")
    if note:                                     # C0.2: a stale/unavailable index is logged, never read as zero boxes
        print(note, file=sys.stderr)
    return doc


def skip_reason(rec: dict, exclude: set[str]) -> str | None:
    """Why this record is NOT dispatchable, or None -- delegates to THE shared predicate box_index.skip_reason (C0.1)."""
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "handoffs"))
    try:
        import box_index
    finally:
        sys.path.pop(0)
    return box_index.skip_reason(rec, exclude)


def order_key(key_rec: tuple[str, dict]) -> tuple:
    key, r = key_rec
    rank = r.get("row_rank")
    pos = r.get("pos_in_backlog")
    return (rank is None, rank if rank is not None else 0, r.get("file", ""),
            pos is None, pos if pos is not None else 0, r.get("line", 0), key)


def candidates(doc: dict, exclude: set[str] | None = None) -> tuple[list[tuple[str, dict]], collections.Counter]:
    """(admitted [(key, record)] in dispatch order, skip-reason histogram over all boxes)."""
    exclude = set(EXCLUDE_FILES) | set(exclude or ())
    hist: collections.Counter = collections.Counter()
    out = []
    if doc.get("boxes") and not doc.get("holds_source"):
        # C3 FAIL CLOSED: without holds.yaml no box can be shown un-held, so nothing is admitted
        hist["holds-source-missing"] = len(doc["boxes"])
        hist["admitted"] = 0
        return out, hist
    for key, rec in sorted((doc.get("boxes") or {}).items(), key=order_key):
        why = skip_reason(rec, exclude)
        if why:
            hist[why] += 1
        else:
            out.append((key, rec))
    hist["admitted"] = len(out)
    return out, hist


def select(doc: dict, exclude: set[str] | None = None, in_flight: set[str] | None = None):
    """(key, record) of the next box, or None; plus the skip histogram. `in_flight` = handoff file names that already
    have a dispatched box (cap one in flight per handoff, DESIGN §2.1 step 3)."""
    cands, hist = candidates(doc, set(exclude or ()) | set(in_flight or ()))
    return (cands[0] if cands else None), hist


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top", type=int, default=1)
    ap.add_argument("--exclude", nargs="*", default=[])
    a = ap.parse_args(argv)
    doc = load_index()
    cands, hist = candidates(doc, set(a.exclude))
    top = cands[:a.top]
    if a.json:
        print(json.dumps({"next": [{"key": k, **r} for k, r in top], "skips": dict(hist)}, indent=1, sort_keys=True))
    else:
        for k, r in top:
            print(f"{k}\t{r['file']}:{r['line']}\trank={r.get('row_rank')}\t{r['text'][:120]}")
        print("skips: " + ", ".join(f"{k}={v}" for k, v in hist.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
