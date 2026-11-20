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
    python3 scripts/handoffs/stale_next_action.py --compare-generated   # C6: hand vs generated, 7-day drop verdict
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
# WP-6, ID-3, UTM-P1a.2, VB-KVQ-V10-DICT. Deliberately tight: a bare word or a bare number is
# not an id. Any number of trailing dash parts: capping them at one truncated 4-part ids
# (VB-KVQ-V10-DICT read as VB-KVQ-V10), so a row naming an open 4-part task was flagged when
# its 3-part prefix was ticked, and a row naming a ticked one was skipped (2026-09-29 wrap-up).
ID_RE = re.compile(r"\b([A-Z][A-Za-z0-9]{0,7}\d*-[A-Za-z0-9]{1,12}(?:-[A-Za-z0-9]{1,12})*(?:\.\d+)?)\b")
BOX_RE = re.compile(r"^[ \t]*- \[([ xX])\][ \t]*\*\*([A-Za-z0-9.\-]+)", re.M)


def box_states(text: str) -> dict[str, set[str]]:
    """task id -> the set of checkbox states it appears with ({'x'}, {' '} or both).

    Handoff standard Stage B: ids come from THE shared rule (task_lint_core.head_id, the same one .box-index.json
    keys on) and boxes quoted inside code fences are ignored."""
    import sys as _sys
    _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import task_lint_core as _l1
    out: dict[str, set[str]] = collections.defaultdict(set)
    lines = text.split("\n")
    fenced = _l1.fenced_lines(lines)
    for i, line in enumerate(lines):
        if i in fenced:
            continue
        m = BOX_RE.match(line)
        if not m:
            continue
        bid = _l1.head_id(line) or m.group(2).rstrip(".-—")
        out[bid].add(m.group(1).lower())
    return out


def scan(active: pathlib.Path = ACTIVE) -> list[tuple[str, str, list[str], str]]:
    findings = []
    for index in sorted(active.glob("*index*.md")):
        text = re.sub(r"<!-- generated:start -->.*?<!-- generated:end -->", "", index.read_text(), flags=re.S)
        for line in text.split("\n"):
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


DEFAULT_LEDGER = "/mnt/raid0/llm/tmp/compute-flags/handoff-standard-c6-compare.jsonl"
C6_DAYS, C6_AGREE = 7, 0.90


def _rows(text: str, generated: bool) -> dict[str, tuple[str, str]]:
    """{row id: (handoff file, Next action cell)} from the hand table (generated=False) or the generated block."""
    m = re.search(r"<!-- generated:start -->(.*?)<!-- generated:end -->", text, flags=re.S)
    body = (m.group(1) if m else "") if generated else re.sub(
        r"<!-- generated:start -->.*?<!-- generated:end -->", "", text, flags=re.S)
    out = {}
    for line in body.split("\n"):
        if not line.startswith("| ") or line.startswith("| ID"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        hcell, nxt = (cells[1], cells[2]) if generated else (cells[2], cells[3])
        link = re.search(r"\(([^)]+\.md)\)", hcell)
        if link:
            out[cells[0]] = (link.group(1), nxt)
    return out


def compare_generated(active: pathlib.Path = ACTIVE, boxes: dict | None = None) -> dict:
    """C6 criteria, one sample: per row, does the GENERATED Next action agree with the hand cell (it names a box the
    hand cell names) or is it strictly fresher (every box the hand cell names is ticked / not dispatchable / absent)?
    Also: generated cells naming a lint-failing box (must be 0), and active handoffs missing **Row**/**Domain**."""
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import box_index as _bi
    boxes = boxes if boxes is not None else (_bi.load(active.parents[1], regenerate=False).get("boxes") or {})
    by_id = {r.get("id"): r for r in boxes.values() if r.get("id")}
    rows, agree, fresher, lint_bad = [], 0, 0, []
    for index in sorted(active.glob("*index*.md")):
        text = index.read_text()
        hand, gen = _rows(text, False), _rows(text, True)
        for rid, (hf, hcell) in hand.items():
            if rid not in gen:
                continue
            gcell = gen[rid][1]
            gids = [i for i in ID_RE.findall(gcell) if i in by_id]
            hids = [i for i in ID_RE.findall(hcell) if i in by_id or i in box_states((active / hf).read_text()
                                                                                  if (active / hf).exists() else "")]
            for g in gids:
                if not (by_id[g].get("lint") or {}).get("ok"):
                    lint_bad.append(f"{rid}:{g}")
            if set(gids) & set(hids) or (not gids and not hids):
                agree += 1
                verdict = "agree"
            elif hids and all(not _bi.dispatchable(by_id[h]) if h in by_id else True for h in hids):
                fresher += 1
                verdict = "fresher"
            else:
                verdict = "disagree"
            rows.append({"row": rid, "verdict": verdict, "hand": hcell[:120], "generated": gcell[:120]})
    missing = []
    for f in sorted(active.glob("*.md")):
        if "index" in f.name or f.name in ("CURRENT-CAMPAIGN.md",):
            continue
        head = "\n".join(f.read_text(errors="replace").split("\n")[:60])
        if not re.search(r"^\*\*Row\*\*:", head, re.M) or not re.search(r"^\*\*Domain\*\*:", head, re.M):
            missing.append(f.name)
    n = len(rows)
    import datetime as _d
    return {"at": _d.datetime.now(_d.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "rows": n, "agree": agree,
            "fresher": fresher, "agree_or_fresher_share": round((agree + fresher) / n, 3) if n else None,
            "generated_lint_failing": lint_bad, "missing_row_domain_headers": missing,
            "disagree": [r for r in rows if r["verdict"] == "disagree"]}


def c6_verdict(samples: list[dict]) -> dict:
    """The 7-consecutive-day hand-row-drop criteria over the ledger: every UTC day of the last 7 has a sample, and in
    each: agree-or-fresher >= 90 %, zero lint-failing generated cells, zero handoffs missing **Row**/**Domain**."""
    import datetime as _d
    days = {}
    for s in samples:
        days.setdefault(s["at"][:10], []).append(s)
    today = _d.datetime.now(_d.timezone.utc).date()
    want = [(today - _d.timedelta(days=k)).isoformat() for k in range(C6_DAYS)]
    per = {}
    for d in want:
        ss = days.get(d) or []
        per[d] = bool(ss) and all((s.get("agree_or_fresher_share") or 0) >= C6_AGREE and not s["generated_lint_failing"]
                                  and not s["missing_row_domain_headers"] for s in ss)
    return {"days": per, "pass": all(per.values())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true", help="exit code only, no report")
    ap.add_argument("--compare-generated", action="store_true",
                    help="C6: sample hand vs generated Next action agreement, append it to --ledger, print the "
                         "7-day hand-row-drop verdict (exit 0 = criteria met)")
    ap.add_argument("--ledger", default=DEFAULT_LEDGER)
    args = ap.parse_args()
    if args.compare_generated:
        import json
        sample = compare_generated()
        try:
            with open(args.ledger, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(sample, sort_keys=True) + "\n")
            samples = [json.loads(l) for l in open(args.ledger, encoding="utf-8") if l.strip()]
        except OSError as exc:
            print(f"WARN ledger {args.ledger}: {exc}", file=sys.stderr)
            samples = [sample]
        v = c6_verdict(samples)
        if not args.quiet:
            print(json.dumps({k: sample[k] for k in ("at", "rows", "agree", "fresher", "agree_or_fresher_share")}
                             | {"generated_lint_failing": len(sample["generated_lint_failing"]),
                                "missing_row_domain_headers": sample["missing_row_domain_headers"],
                                "disagree": [d["row"] for d in sample["disagree"]], "c6": v}, indent=1))
        return 0 if v["pass"] else 1

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
