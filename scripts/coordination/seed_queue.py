#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""seed_queue.py — propose real backlog work onto the session bus.

Owning handoff: handoffs/active/session-bus-thin-dispatcher.md

WHY THIS IS BOUNDED AND NOT A BULK IMPORT. There are ~983 open checkboxes across
171 active handoffs. Dumping them would make the M3 advisory-accuracy comparison
meaningless (advice against a wall of noise proves nothing) and would fill the
queue with items that are conditional, operator-decisions, or unclassifiable. So
this takes a NAMED handoff, classifies what it can, and reports what it skipped
and why. Widening is then a deliberate choice per source, not an accident.

CLASSIFICATION IS HEURISTIC AND SAYS SO. `lane`/`gating` are inferred from the
checkbox text, and every proposal records `classification: heuristic` so nothing
downstream mistakes it for a measured or declared fact. Anything ambiguous is
SKIPPED rather than guessed: a wrongly-classified row is worse than a missing one,
because an inference task labelled `lane: none` would be scheduled onto a busy
host and poison whatever else is running.

It writes ONLY `task-propose` messages to the proposing agent's own outbox —
never `queue.jsonl`, which belongs to the coordinator-daemon. Admission is a
separate, deliberate step: `session_bus_coordinator.py intake`.

EVERY PROPOSAL CARRIES ITS TWO RECEIPTS (2026-08-12). The daemon's automatic
dispatch refuses any row without `screened_by` and a resolvable
`expected_occupancy`, and before this the live queue had ZERO rows with either —
so the gate would have refused everything for ever. Both are derived here, at
birth, by `row_intake` (one rule, three birth sites). A row whose screen does not
come back DISPATCHABLE is not proposed; a row whose occupancy cannot be derived
honestly is proposed WITHOUT the field, so the gate refuses it and a human
dispatches it by hand. See `row_intake.estimate_occupancy` for the four rules.

Usage:
    seed_queue.py --handoff agent-file-prose-compression.md --dry-run
    seed_queue.py --handoff agent-file-prose-compression.md --limit 12 --agent claude-main
    seed_queue.py --list                       # candidate handoffs by open count
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import row_intake  # noqa: E402  (path-relative sibling, same directory)

REPO_ROOT = Path(__file__).resolve().parents[2]
HANDOFFS = REPO_ROOT / "handoffs" / "active"
BUS_ROOT = REPO_ROOT / "coordination" / "session-bus"

OPEN_BOX = re.compile(r"^\s*-\s*\[ \]\s*(?P<text>.+)$")
# An explicit task token the handoff already uses, e.g. `**AFC-P5.0 — …` or `**M4 —`.
TOKEN = re.compile(r"^\*\*(?P<tok>[A-Z][A-Za-z0-9]*(?:[-.][A-Za-z0-9]+)*)\s*[—–-]")

# Needs real compute. Ordered: GPU markers win over CPU ones.
GPU_MARKERS = re.compile(r"\b(mi210|rocm|hip|gpu|vram|hbm|gfx90a|--device\s*ROCm)\b", re.I)
CPU_INFERENCE = re.compile(
    r"\b(bench(mark)?|llama-bench|llama-cli|llama-server|decode|prefill|throughput|t/s|tok/s"
    r"|soak|recert|re-?measure|sweep|eval suite|perplexity|quantiz)", re.I)
# Doc/code work that occupies no inference lane.
NONE_MARKERS = re.compile(
    r"\b(document|write|record|flip|checkbox|update|audit|refactor|wire|spec|index|rename"
    r"|comment|docstring|README|handoff|compress|de-?duplicate|delete|extract|lint|schema)\b", re.I)
# Not seedable: it is a decision or is conditional on one.
CONDITIONAL = re.compile(
    r"\b(operator (choose|decide|decision|approval|interest)|optional spike|gate on operator"
    r"|if the operator|await operator|pending operator|do not start|GATED)\b", re.I)


def classify(text: str) -> tuple[str | None, str | None, str]:
    """(lane, gating, reason). lane None => skip."""
    plain = re.sub(r"`[^`]*`", " ", text)          # code spans carry paths, not intent
    plain = re.sub(r"\*\*|\[|\]\([^)]*\)", " ", plain)

    if CONDITIONAL.search(plain):
        return None, None, "conditional on an operator decision — not autonomously schedulable"
    if len(plain.strip()) < 25:
        return None, None, "too terse to classify confidently"
    gpu, cpu, none = GPU_MARKERS.search(plain), CPU_INFERENCE.search(plain), NONE_MARKERS.search(plain)
    if gpu and cpu:
        return "gpu", "gpu", f"gpu marker {gpu.group(0)!r} + compute verb {cpu.group(0)!r}"
    if gpu:
        return "gpu", "gpu", f"gpu marker {gpu.group(0)!r}"
    if cpu:
        return "cpu", "cpu", f"compute verb {cpu.group(0)!r}"
    if none:
        return "none", "none", f"doc/code verb {none.group(0)!r}"
    return None, None, "no confident lane signal — neither a compute verb nor a doc/code verb"


def extract(handoff: Path) -> list[dict]:
    slug = handoff.stem
    out, n = [], 0
    for lineno, line in enumerate(handoff.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        m = OPEN_BOX.match(line)
        if not m:
            continue
        n += 1
        text = m.group("text").strip()
        tok = TOKEN.match(text)
        # Always suffix the line number. Handoffs reuse short tokens (two items
        # both labelled `P2` is common), and intake is idempotent on task_id, so a
        # collision would SILENTLY drop the second item rather than erroring.
        stem = tok.group("tok") if tok else f"{n:03d}"
        task_id = f"{slug}--{stem}-L{lineno}"
        task_id = re.sub(r"[^A-Za-z0-9._-]", "-", task_id)[:120]
        lane, gating, reason = classify(text)
        summary = re.sub(r"\s+", " ", re.sub(r"\*\*|`", "", text))[:180]
        out.append({"task_id": task_id, "line_no": lineno, "summary": summary,
                    "lane": lane, "gating": gating, "reason": reason,
                    "spec_ref": f"handoffs/active/{handoff.name}#L{lineno}"})
    return out


def cmd_list(args: argparse.Namespace) -> int:
    rows = []
    for f in sorted(HANDOFFS.glob("*.md")):
        items = extract(f)
        ok = [i for i in items if i["lane"]]
        if items:
            rows.append((len(ok), len(items), f.name))
    rows.sort(reverse=True)
    print(f"{'classifiable':>12} {'open':>6}  handoff")
    for ok, tot, name in rows[:25]:
        print(f"{ok:>12} {tot:>6}  {name}")
    print(f"\n{sum(r[0] for r in rows)} classifiable of {sum(r[1] for r in rows)} open, "
          f"across {len(rows)} handoffs")
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    handoff = HANDOFFS / args.handoff
    if not handoff.exists():
        print(f"no such handoff: {handoff}", file=sys.stderr)
        return 64
    items = extract(handoff)
    seedable = [i for i in items if i["lane"]]
    skipped = [i for i in items if not i["lane"]]
    if args.limit:
        seedable = seedable[: args.limit]

    # THE TWO RECEIPTS, derived at birth. The screener's stderr is NOT captured
    # anywhere on this path (row_intake.screen inherits it) — swallowing it is the
    # exact defect fixed on 2026-08-12, because `2>/dev/null` makes a rotted anchor
    # read identically to a clean pass.
    admitted, refused = [], []
    for i in seedable:
        result = row_intake.screen(row=i["summary"])
        i["screen"] = result
        if not result.ready:
            refused.append(i)
            continue
        # None when no rule applies. Left OFF the payload in that case — never a
        # fabricated 0.0. The daemon then refuses the row and a human dispatches it.
        i["expected_occupancy"] = row_intake.estimate_occupancy(
            i["summary"], lane=i["lane"], gating=i["gating"])
        admitted.append(i)
    seedable = admitted

    print(f"{handoff.name}: {len(items)} open, {len(seedable)} to propose, "
          f"{len(skipped)} unclassifiable, {len(refused)} refused by the screener\n")
    for i in seedable:
        print(f"  + {i['task_id']:<52} lane={i['lane']:<5} gating={i['gating']:<5} — {i['reason']}")
        print(f"      screen: {i['screen'].verdict} · {row_intake.occupancy_note(i['expected_occupancy'])}")
    if refused:
        print()
        print(f"  {len(refused)} row(s) NOT proposed — the screener did not return "
              f"{row_intake.READY_VERDICT}:")
        for i in refused:
            tail = " (needs re-anchoring by a human)" if i["screen"].needs_reanchor else ""
            print(f"  ! {i['task_id']:<52} {i['screen'].verdict}{tail}")
    if skipped:
        print()
        for i in skipped[: args.show_skipped]:
            print(f"  - {i['task_id']:<52} SKIP: {i['reason']}")
        if len(skipped) > args.show_skipped:
            print(f"  … {len(skipped) - args.show_skipped} more skipped "
                  f"(--show-skipped N to see them)")

    if args.dry_run:
        print("\nNothing written (--dry-run).")
        return 0
    if not seedable:
        # Do not so much as TOUCH the outbox. Appending nothing still creates the
        # file, and an empty outbox that did not exist before reads as "this agent
        # proposed and everything was consumed" to anything that folds the bus.
        print("\nNothing to propose — no row passed the screener.")
        return 0

    out = BUS_ROOT / "outbox" / f"{args.agent}.jsonl"
    existing = len([l for l in out.read_text().splitlines() if l.strip()]) if out.exists() else 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with out.open("a", encoding="utf-8") as fh:
        for n, i in enumerate(seedable, start=1):
            fh.write(json.dumps({
                "schema_version": "session_bus.msg.v1",
                "id": f"msg-{stamp}-{existing + n}-{args.agent}", "ts": now,
                "from": args.agent, "to": "coordinator-daemon", "kind": "task-propose",
                "task_id": i["task_id"],
                "payload": {"lane": i["lane"], "gating": i["gating"],
                            "spec_ref": i["spec_ref"], "summary": i["summary"],
                            "task_text": i["summary"],
                            "priority": args.priority,
                            "priority_class": "background-churn",
                            "contention_class": "resumable",
                            "screened_by": i["screen"].receipt,
                            # ABSENT, not zero, when no rule applies — see
                            # row_intake.estimate_occupancy rule 4.
                            **({"expected_occupancy": i["expected_occupancy"]}
                               if i["expected_occupancy"] else {}),
                            "classification": f"heuristic: {i['reason']}"}}) + "\n")
    print(f"\nproposed {len(seedable)} task(s) into outbox/{args.agent}.jsonl")
    print("Admit them with:  scripts/coordination/session_bus_coordinator.py intake --dry-run")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="seed_queue.py", description=__doc__.split("\n")[0])
    p.add_argument("--list", action="store_true", help="candidate handoffs by classifiable count")
    p.add_argument("--handoff", help="handoff filename under handoffs/active/")
    p.add_argument("--agent", default="claude-main", help="proposing agent (writes ITS own outbox)")
    p.add_argument("--limit", type=int, help="cap how many are proposed")
    p.add_argument("--priority", default="P2")
    p.add_argument("--show-skipped", type=int, default=6)
    p.add_argument("--dry-run", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        return cmd_list(args)
    if not args.handoff:
        print("need --handoff NAME or --list", file=sys.stderr)
        return 64
    return cmd_seed(args)


if __name__ == "__main__":
    sys.exit(main())
