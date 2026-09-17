#!/usr/bin/env python3
"""Flag index rows whose `Next action` names ONLY tasks that are already ticked.

WHY THIS EXISTS (measured 2026-09-17). `index_state.py --check` gates coverage, schema,
freshness and dead links — every structural property of a row. It cannot see the one
failure that actually mis-dispatches work: a **well-formed row pointing at finished
work**. Six rows were in that state when this script was written (EVL-13, EVL-29,
EVL-37, RTG-15, RTG-42, RTG-56); one of them had been naming a task ticked five weeks
earlier. A screener proves a row is WELL-FORMED, never that it is STILL-NEEDED
(`agents/shared/OPERATING_CONSTRAINTS.md` -> *Dispatching Backlog Work*).

THE RULE, and why it is conservative. A row is flagged only when **every** task id its
`Next action` names resolves to a box in the owning handoff and **all** of them are
ticked. A row naming one done and one open task is NOT flagged: the open one is still a
live instruction. A row naming no resolvable id is NOT flagged: prose next actions are
legitimate, and guessing at them would manufacture false positives -- which is how the
`open == 0` prune heuristic went wrong (13 of 15 candidates were false positives,
2026-08-18).

This is a REPORTER, not a gate. Exit 1 means "look at these", not "the tree is broken":
a flagged row is sometimes correct, e.g. when the next action deliberately records that
a phase closed and the operator owes a decision. Read before you rewrite.

Usage:
    python3 scripts/handoffs/stale_next_action.py            # report, exit 1 if any
    python3 scripts/handoffs/stale_next_action.py --quiet    # exit code only
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import re
import sys

ACTIVE = pathlib.Path(__file__).resolve().parents[2] / "handoffs" / "active"

# A task id as the handoffs write them: EVL-42, RTG-1f, HS-4, EPD-3-R5, TD-1c, NIB2-80,
# WP-6, ID-3, UTM-P1a.2. Deliberately tight: a bare word or a bare number is not an id.
ID_RE = re.compile(r"\b([A-Z][A-Za-z0-9]{0,7}\d*-[A-Za-z0-9]{1,8}(?:-[A-Za-z0-9]{1,8})?(?:\.\d+)?)\b")
BOX_RE = re.compile(r"^[ \t]*- \[([ xX])\][ \t]*\*\*([A-Za-z0-9.\-]+)", re.M)


def box_states(text: str) -> dict[str, set[str]]:
    """task id -> the set of checkbox states it appears with ({'x'}, {' '} or both)."""
    out: dict[str, set[str]] = collections.defaultdict(set)
    for state, raw_id in BOX_RE.findall(text):
        out[raw_id.rstrip(".-—")].add(state.lower())
    return out


def scan(active: pathlib.Path = ACTIVE) -> list[tuple[str, str, list[str], str]]:
    findings = []
    for index in sorted(active.glob("*index*.md")):
        for line in index.read_text().split("\n"):
            if not line.startswith("| ") or line.startswith("| ID"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 4:
                continue
            row_id, handoff_cell, next_action = cells[0], cells[2], cells[3]
            link = re.search(r"\(([^)]+\.md)\)", handoff_cell)
            if not link:
                continue
            handoff = (active / link.group(1)).resolve()
            if not handoff.exists():
                continue  # dead links are index_state.py --check's job, not ours
            states = box_states(handoff.read_text())
            named = [i for i in ID_RE.findall(next_action) if i in states]
            if not named:
                continue
            if all(states[i] == {"x"} for i in named):
                findings.append((index.name, row_id, named, next_action))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true", help="exit code only, no report")
    args = ap.parse_args()

    findings = scan()
    if not args.quiet:
        if not findings:
            print("stale-next-action: none — every row names at least one open task, or names none.")
        else:
            print(f"stale-next-action: {len(findings)} row(s) name only ticked tasks\n")
            for index, row_id, named, next_action in findings:
                print(f"  {row_id}  [{index}]")
                print(f"    ticked: {', '.join(named)}")
                print(f"    next:   {next_action[:120]}")
                print("    fix:    repoint at the handoff's first still-open task, or say what the row is waiting on.\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
