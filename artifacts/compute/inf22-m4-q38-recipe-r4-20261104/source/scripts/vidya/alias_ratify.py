#!/usr/bin/env python3
"""Interactive R4b alias-pair ratification pass for the vidya belief kernel.

Presents each `pending` row of an alias worksheet, records a `same`/`different` verdict,
and leaves the worksheet resumable (non-pending rows are skipped). Only the operator's
judgment writes; the generator's scores are never promoted into decisions.

Usage:  python3 scripts/vidya/alias_ratify.py [--worksheet .vidya/aliases-worksheet.yaml]

Exit codes: 0 = pass complete (no rows left pending), 2 = quit early, 3 = nothing pending.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

import yaml

WS_SCHEMA = "epyc.vidya/alias-worksheet/v1"


def load(path: Path) -> dict:
    doc = yaml.safe_load(path.read_text())
    if not isinstance(doc, dict) or doc.get("schema") != WS_SCHEMA:
        sys.exit(f"not a {WS_SCHEMA} worksheet: {path}")
    return doc


def save(path: Path, doc: dict) -> None:
    path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100))


def verdict_for(row: dict) -> str:
    a, b = row["claim_a"], row["claim_b"]
    flags = []
    if row.get("same_source"):
        flags.append("SAME SOURCE — two entries for one source; aliasing is identity, NOT corroboration; "
                     "usually means a duplicate index entry worth merging")
    if row.get("linked"):
        flags.append("LINKED — the two entries cite each other; a restatement, not a second witness")
    print("=" * 100)
    print(f"[{a}]  score={row['score']:.3f}")
    print(f"    {row['text_a']}")
    print(f"[{b}]")
    print(f"    {row['text_b']}")
    for f in flags:
        print(f"    !! {f}")
    while True:
        ans = _ask("same [s] / different [d] / leave pending [p] / quit [q]? ").strip().lower()
        if ans in ("s", "same"):
            return "same"
        if ans in ("d", "different"):
            return "different"
        if ans in ("p", "pending", ""):
            return "pending"
        if ans in ("q", "quit"):
            return "quit"


def _ask(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        print("\ninput closed — aborting without writing")
        sys.exit(2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--worksheet", default=".vidya/aliases-worksheet.yaml")
    args = ap.parse_args()

    path = Path(args.worksheet)
    if not path.exists():
        sys.exit(f"worksheet not found: {path}  (generate it with: "
                 f"python3 scripts/vidya/cli.py alias-candidates --out {path} "
                 f"--at <ISO-8601> --index research/intake_index.yaml)")
    doc = load(path)

    rows = [r for r in doc.get("rows", []) if r.get("decision") == "pending"]
    if not rows:
        print("no pending rows — pass complete")
        return 3

    reviewer = _ask(f"reviewer name (default {getpass.getuser()}): ").strip() or getpass.getuser()

    same = different = 0
    for row in rows:
        verdict = verdict_for(row)
        if verdict == "quit":
            save(path, doc)
            print(f"quitting: {same} same / {different} different recorded so far; "
                  f"{sum(1 for r in doc['rows'] if r.get('decision') == 'pending')} still pending")
            return 2
        if verdict == "pending":
            continue
        row["decision"] = verdict
        row["reviewer"] = reviewer
        if verdict == "same":
            same += 1
        else:
            different += 1
        save(path, doc)  # resume-safe: one durable write per verdict

    print("=" * 100)
    print(f"pass complete: {same} same / {different} different / "
          f"{sum(1 for r in doc['rows'] if r.get('decision') == 'pending')} pending")
    print(f"worksheet: {path}  (reviewer: {reviewer})")
    print("next:  bash scripts/vidya/ratify_aliases.sh  (dry-run, then real emit + verify)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
