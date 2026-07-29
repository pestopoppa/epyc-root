#!/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
"""backlog_queue_gen.py — generate the dispatchable bench, and audit a hand-written one.

Owning handoff: handoffs/active/session-bus-thin-dispatcher.md
Companion:      coordination/session-bus/tasks/BACKLOG-DISPATCH-QUEUE.md
Screen:         scripts/coordination/backlog_row_check.py (this reuses its classifier)

WHY THIS EXISTS. `BACKLOG-DISPATCH-QUEUE.md` is hand-maintained and keys its rows as
`file.md:LINE`. Audited box-by-box on 2026-07-29, across the 73 unique refs in its
swap-in and runner-up lists:

    48% already closed · 27% anchor rot · 5% blocked · 19% actually dispatchable

and its top-40 "fire at an idle main immediately" bench was down to ONE dispatchable
row out of the nine it still listed as open. Its "straight swap-ins" list — headed
"verified still open at 2026-07-29 verification" — was 0 of 8 valid.

The queue is not badly maintained; it is maintained in the wrong shape. Line anchors
rot within HOURS of an ordinary edit wave (12 of 22 measured rots happened in about
three hours), and no human refresh cadence catches that. So:

    the DURABLE identity is the task TEXT; the line number is a display hint.

That is already the queue's own stated rule. Nothing enforced it, so nothing followed
it. This tool enforces it by generating the bench instead of transcribing it, which
removes the anchor-rot and stale-closure classes outright — together 75% of the
measured defect — and leaves only the genuine judgement calls (blocked, guarded,
standing constraint), which is where a human should be spending attention.

WHAT "DISPATCHABLE" MEANS HERE, precisely, because the count invites misreading: the
row is open, unguarded, unblocked, and not a standing constraint. That is a screen on
FORM. It says nothing about whether the work is still WANTED — read-certification of
two stratified samples put liveness at 47% (n=19) and 29% (n=45). So a generated bench
of ~900 rows is NOT a ~900-task backlog, and quoting it as one would restate the exact
over-count this queue already suffers from.

DELIBERATELY NOT INFERRED: lane (`none`/`cpu`/`gpu`), size, and parallel-safety. Those
need real knowledge of whether a row wants an inference window, and a keyword guess
that mislabels a `cpu`-lane row as `none` would send a main at a task it cannot run.
They stay human-authored in the queue; this tool never overwrites them.

    backlog_queue_gen.py --generate            # the dispatchable bench, text-keyed
    backlog_queue_gen.py --check <queue.md>    # audit an existing queue's refs
    backlog_queue_gen.py --summary             # verdict counts only

Exit codes:  0 clean · 1 the checked queue has rotted refs · 3 usage error
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HANDOFFS = REPO_ROOT / "handoffs" / "active"

_SPEC = importlib.util.spec_from_file_location(
    "brc", Path(__file__).resolve().parent / "backlog_row_check.py")
brc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(brc)

# `file.md:LINE`, as the queue writes it.
_REF = re.compile(r"`([A-Za-z0-9._-]+\.md):(\d+)`")

# A ref the queue has ALREADY dispositioned is correctly maintained, not rotted.
# Without this, `--check` reported 65 unusable refs on a queue where a third of them
# were rows struck through and annotated minutes earlier — a checker that cannot see
# its own subject's bookkeeping reports the maintainer's work as the defect.
_DISPOSITIONED = re.compile(
    r"~~|✅\s*CLOSED|⛔\s*BLOCKED|DO NOT DISPATCH|TEMPLATE|WITHDRAWN", re.I)


def verdicts(handoffs: Path = HANDOFFS) -> list[dict]:
    """Classify every OPEN box under `handoffs`. Closed boxes are not work."""
    out = []
    for path in sorted(handoffs.glob("*.md")):
        for lineno, state, body, head in brc._boxes(path):
            if state == "x":
                continue
            code, reasons = brc.classify(path, lineno, state, body, head)
            out.append({
                "file": path.name, "line": lineno, "text": body, "head": head,
                "dispatchable": code == 0, "reasons": reasons,
                "kind": _reason_kind(code, reasons),
            })
    return out


def _reason_kind(code: int, reasons: list[str]) -> str:
    if code == 0:
        return "warned" if reasons != ["reads as a dispatchable task"] else "clean"
    first = reasons[0]
    if "BLOCKED BY A CHILD BOX" in first:
        return "blocked"
    if "DO-NOT-DISPATCH guard" in first:
        return "guarded"
    if "standing-constraint shaped" in first:
        return "standing-constraint"
    return "other"


def check_queue(queue: Path, handoffs: Path = HANDOFFS) -> tuple[int, list[str]]:
    """Audit every `file.md:LINE` a hand-written queue cites. (rotted, lines)."""
    if not queue.exists():
        return 0, [f"REFUSING: {queue} does not exist"]
    report, rotted, seen, skipped = [], 0, set(), 0
    for text in queue.read_text(encoding="utf-8", errors="replace").splitlines():
        dispositioned = bool(_DISPOSITIONED.search(text))
        for m in _REF.finditer(text):
            name, lineno = m.group(1), int(m.group(2))
            if (name, lineno) in seen:
                continue
            seen.add((name, lineno))
            if dispositioned:
                skipped += 1
                continue
            line = _check_ref(handoffs, name, lineno)
            if line:
                report.append(line)
                rotted += 1
    if skipped:
        report.append(f"  ({skipped} ref(s) skipped — the queue already marks them "
                      f"closed/blocked/withdrawn)")
    return rotted, report


def _check_ref(handoffs: Path, name: str, lineno: int) -> str | None:
    """One ref. Returns a report line if it is unusable, else None."""
    path = handoffs / name
    if not path.exists():
        return f"  MISSING-FILE   {name}:{lineno}"
    boxes = {n: (st, b, h) for n, st, b, h in brc._boxes(path)}
    if lineno not in boxes:
        return f"  ANCHOR-ROT     {name}:{lineno} — no checkbox on that line"
    state, body, head = boxes[lineno]
    if state == "x":
        return f"  ALREADY-CLOSED {name}:{lineno} — {body[:64]}"
    code, reasons = brc.classify(path, lineno, state, body, head)
    if code != 0:
        return f"  {_reason_kind(code, reasons).upper():<14} {name}:{lineno} — {body[:56]}"
    return None


def render(rows: list[dict]) -> str:
    """The generated bench. Text first, because text is the identity."""
    live = [r for r in rows if r["dispatchable"]]
    by_file: dict[str, list[dict]] = {}
    for r in live:
        by_file.setdefault(r["file"], []).append(r)
    out = ["# Dispatchable bench — GENERATED, do not hand-edit",
           "",
           "Regenerate with `scripts/coordination/backlog_queue_gen.py --generate`.",
           "",
           "Rows are keyed on TASK TEXT, which is durable. The `L###` is a display hint and",
           "may drift within hours of an edit wave — claim by text:",
           "",
           "    session_bus.py claim --agent <id> --row '<task text>'",
           "",
           "Lane, size and parallel-safety are NOT inferred here — a keyword guess that",
           "mislabels a `cpu`-lane row as `none` sends a main at a task it cannot run. Those",
           "stay human-authored in BACKLOG-DISPATCH-QUEUE.md.",
           "",
           f"**{len(live)} rows dispatchable IN SHAPE, across {len(by_file)} files.**",
           "",
           "That number is not a backlog estimate and must not be quoted as one. It counts",
           "rows that are open, unguarded, unblocked and not standing constraints — a",
           "mechanical screen on FORM. Whether the work is still WANTED is a separate axis",
           "this tool cannot see: read-certification of two stratified samples put liveness",
           "at 47% (n=19) and 29% (n=45), so the real live backlog is plausibly a third of",
           "the rows below. Certification is a human read; only that can close a dead row.", ""]
    for name in sorted(by_file):
        out.append(f"## {name} ({len(by_file[name])})")
        for r in by_file[name]:
            warn = "" if r["kind"] == "clean" else "  ⚠"
            out.append(f"- L{r['line']}{warn} — {r['text'][:150]}")
            if r["kind"] == "warned":
                for reason in r["reasons"]:
                    out.append(f"    - {reason[:170]}")
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--generate", action="store_true", help="emit the dispatchable bench")
    g.add_argument("--summary", action="store_true", help="verdict counts only")
    g.add_argument("--check", metavar="QUEUE.md", help="audit a hand-written queue's refs")
    args = ap.parse_args(argv)

    if args.check:
        rotted, report = check_queue(Path(args.check))
        print(f"{Path(args.check).name}: {rotted} unusable reference(s)")
        for line in report:
            print(line)
        return 1 if rotted else 0

    rows = verdicts()
    if args.summary:
        counts = Counter(r["kind"] for r in rows)
        print(f"open boxes: {len(rows)}")
        for kind, n in counts.most_common():
            print(f"  {kind:<20} {n:5d}  ({n / len(rows) * 100:.1f}%)")
        return 0

    print(render(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
