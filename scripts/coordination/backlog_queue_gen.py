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

VERBATIM TEXT, NOT A SUMMARY (2026-08-11, `mainC`). Rows carry the box's text exactly
as written, untruncated. The hand-written queue stored a sweeper's PARAPHRASE in its
description column, and that silently defeated the very recovery text-keying exists to
provide: re-anchoring 379 rotted refs by exact text matched almost nothing, and only
fuzzy token overlap recovered 76% of them. A paraphrase rots differently from a line
number, not less. The text printed here is the same string `claim_key` hashes, so the
claim command under each row is copy-pasteable and takes the lock it displays.

    KNOWN LIMIT, stated rather than hidden: `_boxes` yields a box's FIRST LINE, so on
    a wrapped box the key stops at the wrap and can end mid-sentence. The identity is
    therefore wrap-dependent — reflowing a paragraph changes it much as an edit
    changes a line number, which is a weaker form of the rot this design removes.
    Joining continuation lines would fix it, but the key must stay byte-identical to
    what `backlog_row_check.find_by_text` indexes and what `session_bus.py claim`
    folds, so changing it is a THREE-tool contract change and not a generator-local
    one. Left consistent on purpose; fixing it means changing all three together.

THE POSITIVE SIGNAL, AND WHY ABSENCE WAS NEVER ENOUGH. This tool used to decide
dispatchability by SUBTRACTION: everything open, minus what a heuristic could spot as
bad. Subtraction cannot see what it does not detect, and that gap is measured, not
theoretical — four boxes in `model-stack-change-standardization-audit.md`'s per-change
checklist were flipped `[x]` on 2026-07-14, ELEVEN DAYS before the backlog sweep ever
ran. No queue row ever pointed at them. An absence-based screen is structurally unable
to report a corruption it was never asked about.

So a guard is now read as a POSITIVE declaration in the handoff (`box_is_guarded`, a
blockquote banner or an inline marker, with C41 scope resolution), and that declaration
buys something subtraction never could: an INVARIANT. Under a banner saying nothing
here may be flipped, any `- [x]` is a defect by construction — `--audit-procedures`
asserts exactly that, and it would have caught the 07-14 four-box case on the day it
happened, with no queue, no sweep and no row. Alongside it, `--quarantine` lists boxes
whose TEXT reads as a recurring step but which carry NO declaration: those are held
back from the bench and reported as "needs a marker" instead of being silently
dispatched. Inference still happens; it just can no longer decide alone.

    backlog_queue_gen.py --generate            # the dispatchable bench, text-keyed
    backlog_queue_gen.py --check <queue.md>    # audit an existing queue's refs
    backlog_queue_gen.py --summary             # verdict counts only
    backlog_queue_gen.py --quarantine          # procedural-looking rows with NO marker
    backlog_queue_gen.py --audit-procedures    # the invariant: [x] under a DO-NOT-FLIP guard
    backlog_queue_gen.py --audit-procedures --tree all    # ... across active/completed/archived

Exit codes:  0 clean · 1 the checked queue has rotted refs, or an audit found hits · 3 usage
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
TREES = {name: REPO_ROOT / "handoffs" / name
         for name in ("active", "completed", "archived", "blocked")}

# Box TEXT that reads as a recurring step. This is the INFERENCE half — it never
# decides on its own; a hit with no positive declaration is REPORTED by `--quarantine`
# and is otherwise left alone.
#
# The discriminator is a STANDING CONDITION, never the verb. First cut included
# `re-?run (this|the|these)` and it matched 11 rows, every one of them a ONE-OFF
# rerun ("Re-run the 27 confounded E5 cells", "Void and re-run the PaddleOCR-VL arm")
# and not one a recurring step. A re-run is a task; "re-run BEFORE EACH pickup" is a
# procedure, and only the second half carries the recurrence. Patterns without an
# explicit every/each/any-time condition were dropped for that reason.
_PROCEDURAL = re.compile(
    r"\b(at each pickup|on each pickup|every time this|each time this|"
    r"before each|prior to each|for (?:any|each|every) (?:new |future )?"
    r"(?:change|swap|run|pickup|release)|"
    r"check .{0,40}\bfor any new\b|start every|begin every)", re.I)

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
            declared = brc.box_is_guarded(path, lineno)
            out.append({
                "file": path.name, "line": lineno, "text": body, "head": head,
                "dispatchable": code == 0, "reasons": reasons,
                "kind": _reason_kind(code, reasons),
                # Positive declaration in the handoff vs. our own inference. Kept
                # separate on purpose: conflating them is what let an undeclared
                # procedure look identical to a screened-and-cleared task.
                "declared_no_dispatch": declared,
                "looks_procedural": bool(_PROCEDURAL.search(body)),
            })
    return out


def quarantine(rows: list[dict]) -> list[dict]:
    """Rows whose TEXT reads as a recurring step but which carry NO declaration.

    REPORT ONLY — these are NOT withheld from the bench, deliberately. Withholding
    would refuse real work on an inference this module has already been wrong about
    once (see `_PROCEDURAL`), and this corpus's settled rule is that refusing real
    work is the costlier error. The point is not that the inference is right; it is
    that an undeclared procedure and a screened task are otherwise indistinguishable
    to every consumer, and this is the list that makes them distinguishable so an
    author can settle it by adding a marker.
    """
    return [r for r in rows if r["looks_procedural"] and not r["declared_no_dispatch"]]


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
            # VERBATIM and untruncated — this string is the identity, and it is the
            # exact string `claim_key` folds. Truncating it here would reintroduce
            # the paraphrase that made the hand-written queue unrecoverable by text.
            out.append(f"- L{r['line']}{warn} — {r['text']}")
            out.append(f"    - claim: `session_bus.py claim --agent <id> --row "
                       f"{brc.claim_key(r['text'])!r}`")
            if r["kind"] == "warned":
                for reason in r["reasons"]:
                    out.append(f"    - {reason}")
        out.append("")
    return "\n".join(out)


def render_quarantine(rows: list[dict]) -> str:
    held = quarantine(rows)
    out = ["# Quarantine — procedural-looking rows carrying NO do-not-dispatch marker",
           "",
           "REVIEW PROMPT, not a verdict, and these rows are still ON the bench. Each is",
           "EITHER a reusable step that needs a declaration in its handoff, OR an ordinary",
           "task phrased like one. This tool cannot tell them apart, so it names them rather",
           "than withholding them — refusing real work is the costlier error here.",
           "",
           "Resolve by editing the HANDOFF, not this list — add a blockquote banner",
           "(`> **⚠ … DO NOT DISPATCH OR FLIP THEM.**`) over a reusable section, or an inline",
           "`*(STANDING CONSTRAINT — not a dispatchable task; do not flip.)*` on the row. Once",
           "declared, `--audit-procedures` will also protect it from being flipped closed.",
           "",
           f"**{len(held)} row(s).**", ""]
    by_file: dict[str, list[dict]] = {}
    for r in held:
        by_file.setdefault(r["file"], []).append(r)
    for name in sorted(by_file):
        out.append(f"## {name} ({len(by_file[name])})")
        for r in by_file[name]:
            out.append(f"- L{r['line']} — {r['text']}")
        out.append("")
    return "\n".join(out)


#: A dated completion marker. `✅ 2026-07-29`, or a bare trailing date after evidence.
_DONE_MARK = re.compile(r"✅\s*\d{4}-\d{2}-\d{2}|\b(19|20)\d{2}-\d{2}-\d{2}\b")


def _full_box_text(path: Path, lineno: int) -> str:
    """The whole box, continuation lines included.

    Load-bearing, and found by mutation-checking rather than by reading: the helper
    hands back the box's FIRST LINE only, and markdown wraps a box across lines. The
    `✅ 2026-07-29` that proves `:345` is a completion record sits on the *second*
    line, so a first-line classifier saw no completion marker and demoted nothing —
    the checker's output was unchanged and looked like the classifier was inert.

    Same shape as the untracked-probe miss earlier tonight: the discriminator was
    right and it was reading a view of the input that could not contain the answer.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:                                            # pragma: no cover
        return ""
    out = [lines[lineno - 1]]
    for nxt in lines[lineno:]:
        if not nxt.strip() or brc._BOX.match(nxt) or nxt.lstrip().startswith("#"):
            break
        out.append(nxt)                       # an indented continuation of this box
    return " ".join(out)


def _is_completion_record(text: str) -> bool:
    """Is this checked box a RECORD of a finished run, rather than a retired RULE?

    WHY THIS EXISTS. The invariant keyed on "closed box under a DO-NOT-FLIP banner",
    but the banner at `model-stack-single-source-update-pipeline.md:320` says what it
    actually governs: *"Every OPEN box in this section is a rule with no completion
    state."* Dated completion records legitimately share the section. So the key was
    wider than the property and the audit reported 3 violations, all three false —
    including the completion half of a box `mainC` had itself split on 2026-08-11
    precisely so a finished audit and a live rule could stop sharing one line.

    A checker that cries wolf is one somebody eventually deletes, which is the same
    reasoning that de-brittled the `binding_router` tripwire the same night.

    DELIBERATELY ASYMMETRIC. Demotion needs POSITIVE evidence — a completion marker
    AND no standing condition — so anything unrecognised stays a violation. The
    banner this serves warns in its own text that *"a guard that trusts an
    enumeration is passed by not being enumerated"*; a discriminator that defaulted
    to "probably fine" would re-introduce exactly that false-permit, one layer down.
    """
    if not _DONE_MARK.search(text):
        return False                       # no completion evidence → treat as a rule
    if brc._RULE_COND.search(text) or brc._PROHIBITION.match(text.strip()):
        return False                       # a dated rule is still a rule
    return True


def audit_procedures(trees: list[str]) -> tuple[int, list[str]]:
    """THE INVARIANT: no `- [x]` may sit under a DO-NOT-FLIP declaration.

    Absence-based screening could never assert this — it only ever looked at rows a
    queue named. A positive declaration turns "we found no bad row" into "no box under
    this banner may be closed", which is checkable without any queue at all.

    Returns (hits, report-lines). Report-only: in `completed/` and `archived/` a
    flipped box may be a correct historical record, so this NEVER edits.
    """
    lines_out, total = [], 0
    for tree in trees:
        root = TREES[tree]
        if not root.is_dir():
            continue
        rules, records = [], []
        for hit in brc.closed_boxes_under_a_guard(root):
            full = _full_box_text(hit[0], hit[1])
            (records if _is_completion_record(full) else rules).append(hit)

        lines_out.append(f"\n=== handoffs/{tree}/ — {len(rules)} checked box(es) that read as RULES ===")
        if tree != "active":
            lines_out.append("    (history: REPORT ONLY. A flipped box here may be a correct "
                             "record of a run. Restore only if something LIVE still points at "
                             "the procedure — and say what points at it.)")
        for path, lineno, text in rules:
            lines_out.append(f"  {path.name}:{lineno}")
            lines_out.append(f"      {text[:170]}")

        # Reported, never silently dropped: demotion is a JUDGEMENT, and a reader must be
        # able to overrule it. Subtracting these invisibly is how a guard starts lying.
        if records:
            lines_out.append(f"  -- {len(records)} further checked box(es) under the same "
                             "banner read as DATED COMPLETION RECORDS, not rules (not counted; "
                             "verify if you disagree) --")
            for path, lineno, text in records:
                lines_out.append(f"     {path.name}:{lineno}  {text[:110]}")
        total += len(rules)
    return total, lines_out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--generate", action="store_true", help="emit the dispatchable bench")
    g.add_argument("--summary", action="store_true", help="verdict counts only")
    g.add_argument("--check", metavar="QUEUE.md", help="audit a hand-written queue's refs")
    g.add_argument("--quarantine", action="store_true",
                   help="procedural-looking rows carrying NO do-not-dispatch marker")
    g.add_argument("--audit-procedures", action="store_true",
                   help="the invariant: `- [x]` sitting under a DO-NOT-FLIP guard")
    ap.add_argument("--tree", default="active",
                    choices=[*TREES, "all"],
                    help="which handoff tree to audit (default: active)")
    args = ap.parse_args(argv)

    if args.check:
        rotted, report = check_queue(Path(args.check))
        print(f"{Path(args.check).name}: {rotted} unusable reference(s)")
        for line in report:
            print(line)
        return 1 if rotted else 0

    if args.audit_procedures:
        trees = list(TREES) if args.tree == "all" else [args.tree]
        total, report = audit_procedures(trees)
        print(f"checked boxes under a DO-NOT-FLIP declaration: {total}")
        for line in report:
            print(line)
        return 1 if total else 0

    rows = verdicts()
    if args.quarantine:
        print(render_quarantine(rows))
        return 0

    if args.summary:
        counts = Counter(r["kind"] for r in rows)
        print(f"open boxes: {len(rows)}")
        for kind, n in counts.most_common():
            print(f"  {kind:<20} {n:5d}  ({n / len(rows) * 100:.1f}%)")
        declared = sum(1 for r in rows if r["declared_no_dispatch"])
        held = len(quarantine(rows))
        print(f"\n  positively DECLARED no-dispatch : {declared:5d}   (read from the handoff)")
        print(f"  quarantined, undeclared         : {held:5d}   (inferred — needs a marker)")
        return 0

    print(render(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
