#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""backlog_row_check.py — screen a backlog row BEFORE dispatching or claiming it.

Owning handoff: handoffs/active/session-bus-thin-dispatcher.md
Companion:      coordination/session-bus/tasks/BACKLOG-DISPATCH-QUEUE.md

WHY THIS EXISTS. Two failure modes were measured on 2026-07-29 while working the
dispatch queue, and both cost real work:

  1. ANCHOR ROT. The queue keys rows as `file.md:NNN`, and 22 of its 201 references
     (10%) no longer pointed at a checkbox the same day it was written — 12 of them
     from ordinary fleet edits in about three hours. The queue's own rule says "line
     numbers are a hint, task text is the identity"; nothing enforced it. A rotted
     `file.md:NNN` in the runner-up bench carries NO description, so a reader cannot
     even tell what it once meant.

  2. NON-DISPATCHABLE ROWS. Reusable checklists and standing constraints were being
     served as tasks. Two boxes in a "When resuming this handoff:" pickup checklist
     were actually flipped, so the next reader will skip a step whose whole purpose is
     to re-run every time. ~25 template boxes and ~11 standing-constraint rows were
     affected, in sections titled "Update Checklist For Any …", "Rules For New Tests",
     "Reopen Checklist" — and, with no signal at all, "Outstanding Work".

The reusable lesson, learned the slow way over three separate findings: **the tell is
the BOX TEXT, not the section heading.** Heading-based screening failed twice.

This tool is ADVISORY and read-only. It changes nothing, and it is deliberately not
wired into `session_bus.py claim` — a screen that silently refuses a claim would be a
new fail-closed of its own. Run it, read it, decide.

    backlog_row_check.py --ref  model-stack-single-source-update-pipeline.md:320
    backlog_row_check.py --row  "Promote the GPU driver scripts into the repo"

Exit codes:  0 dispatchable · 2 NOT dispatchable · 3 unresolvable · 4 ambiguous
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HANDOFFS = REPO_ROOT / "handoffs" / "active"

# A standing constraint opens with a continuous imperative...
_RULE_VERB = re.compile(
    r"^\**\s*(keep|preserve|continue|avoid|maintain|never|always|do not|don't|ensure|"
    r"treat|leave|hold|retain|refrain|prefer|re-read|state the|apply the|reproduce|"
    r"choose the|work in)\b", re.I)
# ...and usually carries a standing condition. Both together is the strong signal;
# the verb alone is reported as a WEAK hint, because "Keep X out of Y" can also be a
# one-off cleanup and this tool must not mark real work undispatchable.
_RULE_COND = re.compile(
    r"\b(whenever|until|unless|only where|as migrated|each time|every time|"
    r"when resuming|before adding|opportunistically|as long as|going forward)\b", re.I)
_GUARD = re.compile(r"UNCHECKED BY DESIGN|STANDING CONSTRAINTS?|DO NOT DISPATCH", re.I)
# A section can disclaim execution by the reader without being a template. Measured
# 2026-07-29: `stale-open-audit-2026-07-18.md` § "Recommendations (follow-up tasks —
# no checkbox flips on the audited handoffs)" holds six rows, FOUR of which direct
# work at other owners and TWO of which extend the audit itself. Two separate rows
# were claimed out of it before the disclaimer was noticed.
#
# This WARNS, it does not refuse — refusing would have been wrong for the two rows
# that genuinely belong to the reader. The distinction ("does this modify an audited
# artifact, or extend the audit?") needs a human; the tool's job is to make sure the
# disclaimer is seen at all, since it lives in the HEADING and not in the row.
_OWNER_DISCLAIM = re.compile(
    r"no checkbox flips|owner is |owning lane|for the owner|hand(ed)? to the owner|"
    r"follow-up tasks|operator-gated|human-owned|recommendations?\s*\(", re.I)


def claim_key(text: str) -> str:
    """EXACTLY `session_bus.py claim`'s key: whitespace-collapsed + case-folded.

    Kept byte-identical to that function on purpose. A screening tool that suggested a
    claim string keyed differently from the claim verb would hand out commands that
    take the WRONG lock — and a failed operator-presented command is an agent defect by
    policy, not a typo.
    """
    return " ".join(text.split()).casefold()


def search_key(text: str) -> str:
    """Looser key for FINDING a row: also drops markdown emphasis and backticks.

    Search and identity are deliberately different. The queue's description column and
    the handoff body routinely differ only by `**`/`` ` ``, so matching must ignore
    them — but the CLAIM key must not, or two spellings of one row take two locks.
    Note this does NOT strip `_`: doing so turned `seeding_legacy.py` into
    `seedinglegacy.py` and produced a claim command that would have locked a
    different string than the one it printed.
    """
    return " ".join(re.sub(r"[*`]", "", text).split()).casefold()


def _boxes(path: Path) -> list[tuple[int, str, str, str]]:
    """(lineno, state, body, enclosing-heading) for every checkbox in the file."""
    out, head = [], ""
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if line.startswith("#"):
            head = line.strip("# ").strip()
        s = line.lstrip()
        m = re.match(r"- \[([ xX])\]\s*(.*)", s)
        if m:
            out.append((i, m.group(1).strip().lower(), m.group(2), head))
    return out


def section_is_guarded(path: Path, lineno: int) -> bool:
    """Does the enclosing section carry an explicit DO-NOT-FLIP guard?"""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max((i for i, l in enumerate(lines[:lineno]) if l.startswith("#")), default=0)
    return bool(_GUARD.search("\n".join(lines[start:lineno])))


def classify(path: Path, lineno: int, state: str, body: str, head: str) -> tuple[int, list[str]]:
    """(exit_code, reasons). Advisory: it explains, it does not decide for you."""
    reasons = []
    if state == "x":
        return 2, [f"already CLOSED — the box at {path.name}:{lineno} is `- [x]`"]
    if section_is_guarded(path, lineno):
        return 2, [f"the enclosing section (§ {head}) carries an explicit DO-NOT-DISPATCH guard — "
                   f"this is a reusable checklist or a standing constraint, not a task"]
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max((i for i, l in enumerate(lines[:lineno]) if l.startswith("#")), default=0)
    disclaimer = _OWNER_DISCLAIM.search("\n".join(lines[start:start + 3]))
    if disclaimer:
        reasons.append(f"OWNERSHIP: the enclosing section disclaims execution by the reader "
                       f"({disclaimer.group(0).strip()!r} in § {head}). Rows here often direct work "
                       f"at ANOTHER owner — verify it is yours before claiming. Not a refusal: such "
                       f"sections mix owner-directed rows with ones that really are yours.")
    strong = bool(_RULE_VERB.match(body)) and bool(_RULE_COND.search(body))
    if strong:
        return 2, [f"the BOX TEXT is standing-constraint shaped (continuous imperative + a standing "
                   f"condition), so it has no completion state: {body[:90]!r}",
                   "flipping it asserts that an ongoing constraint is permanently satisfied"]
    if _RULE_VERB.match(body):
        reasons.append(f"WEAK HINT: opens with a continuous imperative ({body.split()[0]!r}) but "
                       f"carries no standing condition — read it before dispatching; it may be a "
                       f"one-off cleanup rather than a rule")
    if re.search(r"human-amendment-only|operator decision|human-owned", body, re.I):
        reasons.append("mentions an operator/human-amendment gate — confirm it is yours to action")
    return 0, reasons or ["reads as a dispatchable task"]


def find_by_text(row: str) -> list[tuple[Path, int, str, str, str]]:
    key = search_key(row)
    if not key:
        return []
    hits = []
    for p in sorted(HANDOFFS.glob("*.md")):
        for lineno, state, body, head in _boxes(p):
            nb = search_key(body)
            if key == nb or key in nb or nb in key:
                hits.append((p, lineno, state, body, head))
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ref", help="file.md:LINE, as the dispatch queue writes it")
    g.add_argument("--row", help="the task TEXT — the durable identity")
    args = ap.parse_args(argv)

    if args.row:
        hits = find_by_text(args.row)
        if not hits:
            print(f"UNRESOLVABLE: no open or closed box in {HANDOFFS} matches that text.",
                  file=sys.stderr)
            return 3
        if len({(p, n) for p, n, *_ in hits}) > 1:
            print("AMBIGUOUS — that text matches several boxes; be more specific:", file=sys.stderr)
            for p, n, st, body, _ in hits:
                print(f"  {p.name}:{n} [{st or ' '}] {body[:70]}", file=sys.stderr)
            return 4
        path, lineno, state, body, head = hits[0]
    else:
        m = re.match(r"([^:]+):(\d+)$", args.ref.strip())
        if not m:
            print("REFUSING: --ref must look like file.md:LINE", file=sys.stderr)
            return 3
        path, lineno = HANDOFFS / m.group(1), int(m.group(2))
        if not path.exists():
            print(f"UNRESOLVABLE: {path} does not exist.", file=sys.stderr)
            return 3
        boxes = {n: (st, b, h) for n, st, b, h in _boxes(path)}
        if lineno not in boxes:
            # THE MEASURED FAILURE, reported as itself rather than as "not found".
            print(f"ANCHOR ROT: {path.name}:{lineno} is no longer a checkbox — the file has been "
                  f"edited since the queue was written.\n"
                  f"  Measured 2026-07-29: 10% of the queue's anchors were dead the same day.\n"
                  f"  Re-run with --row '<task text>'; text is the identity, the line is a hint.",
                  file=sys.stderr)
            return 3
        state, body, head = boxes[lineno]

    code, reasons = classify(path, lineno, state, body, head)
    verdict = {0: "DISPATCHABLE", 2: "NOT DISPATCHABLE"}[code]
    print(f"{verdict}  {path.name}:{lineno}")
    print(f"  section : § {head}")
    print(f"  state   : [{state or ' '}]")
    print(f"  text    : {body[:100]}")
    for r in reasons:
        print(f"  - {r}")
    if code == 0:
        # The RAW body, not a normalised form: `claim` normalises internally, and
        # printing a pre-mangled string is how a suggested command locks the wrong row.
        print(f"\n  claim it by TEXT, not by line:\n"
              f"    session_bus.py claim --agent <id> --row {body!r}")
    return code


if __name__ == "__main__":
    sys.exit(main())
