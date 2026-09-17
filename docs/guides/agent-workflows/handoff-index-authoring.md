# Handoff Index Authoring

Extracted 2026-07-30 from CLAUDE.md (authoring-time-only content; AFC-P6 restructure).
**Rewritten 2026-08-10** — the thin-row contract replaces task extraction.

## The row contract

An index is a **dispatch surface**: it answers *where is this work and what is the next step*, in as
few lines as possible. It is not a status report and not an evidence ledger.

Exactly one table shape, in every domain index:

```
| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| INF-07 | deepseek v4 flash 0731 dspark | [<handoff>.md](<handoff>.md) | Q8 baseline on production v8 before any kernel work | — |
```

- **`ID`** — `<DOMAIN>-NN`, stable and never reused. Cite the ID, not a line number: line anchors rot
  within hours of an ordinary edit wave (measured: 12 of 22 rots in ~3 hours,
  `scripts/coordination/backlog_row_check.py`). Retiring a row retires its ID with it.
- **`Track`** — short human label, the sub-area within the domain.
- **`Handoff`** — exactly one markdown link to the owning handoff.
- **`Next action`** — one imperative line, **≤ 140 characters**. Seed it from the handoff's own first
  open dispatchable task. **Not** status, **not** history, **not** evidence.
  **Re-pointing it to a different target? Put the reason in the commit message, never in the row:**
  `Repoint-Reason: INF-06: <why the previous target was abandoned>` (one line per row).
  `scripts/handoffs/build_handoff_timeline.py` records every re-point (old text, new text, reason) in
  `data/handoff_timeline.json` → `next_action_repoints`, so the next session does not re-walk a
  rejected path. Without the line, the reason falls back to the commit subject, which is weaker.
- **`Deps`** — bare IDs, comma-separated, or `—`. These are the graph edges; a renderer needs nothing else.

**Escape any literal `|` inside a cell as `\|`.** The checker splits on unescaped pipes.

## The three rules that keep it thin

1. **One owner.** Every active handoff appears in **exactly one** index, in exactly one row. Cross-domain
   relevance is a `Deps` edge or a line in `## Cross-domain` — **never a second row.** Duplication was
   measured at 78 of 172 handoffs (45%) before this contract; one fact then cost N edits and drifted N ways.
2. **Status is generated, never written.** Open/closed counts, `last_advanced`, blocked and guarded counts
   come from `scripts/handoffs/index_state.py` into `handoffs/active/.index-state.json` and the rollup
   block in the master index. Hand-written status is what rots.
3. **History leaves the index.** Closed rows, superseded narration, and retracted content move to
   `handoffs/archived/<index>-history-through-YYYY-MM-DD.md` with a "historical ledger only" banner.
   Delete the row from the index; never strike it through in place.

## Promote or inline? (a checkbox vs its own handoff + row)

Derived 2026-09-16 (RTG-46) on the *shape* of intake-1309#record's table, with **our own constants**.
The "size" is a top-level checkbox's line count: the box line plus its indented continuation lines.
Measured over the 1,635 open top-level boxes in 173 active handoffs:

| Lines | Open boxes | Handoffs | Rule |
|---|---|---|---|
| 1–3 (≤ p50) | 919 | 149 | **Inline.** Promote only on the isolation criterion (4). |
| 4–11 (≤ p90) | 562 | 86 | **Inline** unless a signal from (2) applies. |
| 12–31 | 136 | 43 | **Ambiguous band**: apply (2), then the tie-break (3). |
| ≥ 32 (≥ p99) | 18 | 11 | **Promote.** A box this long is already an embedded handoff. |

(Continuation-line percentiles for open boxes: p50 3, p75 6, p90 11, p95 16, p99 32, max 160. Only
70 of 1,635 open boxes carry nested sub-boxes. Re-measure with the same definition before changing
these bands. Do not use intake-1309#record's 10/40 constants: they are unmeasured and count Lean proof lines.)

1. **Size metric.** Use the table above.
2. **Promotion signals for the ambiguous band.** Any one is enough:
   - it has, or needs, its own nested sub-boxes;
   - another row would list it in `Deps`, or it waits on a different row than its parent does;
   - a different session or lane would own it;
   - it keeps accumulating narrative or evidence inside the box, which is history living in a row
     in all but name;
   - other handoffs link to it specifically.
3. **Tie-break: promote when unsure.** intake-1309#record inlines when unsure because an uploaded theorem is
   immutable and an inlined lemma can still be promoted later. That asymmetry does not hold here:
   our rows and handoffs are freely editable and deletable, so both directions can be undone. What
   stays asymmetric is **visibility**. An inlined item has no graph node, so it gets no `readiness`,
   no liveness and no `Deps` edge, and a wrong inline fails silently. A wrong promotion shows up as a
   tiny node on the hub. Fold it back when that happens: a handoff with ≤ 2 checkboxes is a
   candidate to inline (10 of 173 active handoffs on 2026-09-16).
4. **Failure isolation, independent of reuse.** Promote at any size when the item can be *blocked
   on something its parent is not*, or its failure must not stall the parent. `readiness` is
   derived per node, so a gate on an inline box either blocks the whole parent or is invisible.

## What this replaces, and why

The previous contract required indices to *"extract all outstanding tasks from linked handoffs, ordered
by priority and dependency"*. With ~1,300 open checkboxes across ~172 active handoffs that is
unmaintainable by hand, so rows degraded into narration: a single cell reached ~2,000 characters, one
index preserved a **retracted** row verbatim, and the master index opened with ~60 lines of campaign
banner before its own routing table.

The extraction mandate was the root cause, not anyone's discipline. Tasks now stay in the handoff, which
is their single source of truth; the index carries one pointer and one next step per handoff.

## Verification

```bash
python3 scripts/handoffs/index_state.py           # regenerate sidecar + master rollup
python3 scripts/handoffs/index_state.py --check    # coverage, schema, freshness (non-zero on failure)
```

`--check` fails on: a handoff in two indices, a handoff in none, a dead handoff link, a malformed row, a
`Next action` over 140 chars, a `Deps` entry that resolves to no row, and a stale generated block.

Run it after **any** index edit and before committing. The wrap-up routine (Step 3) and the
research-intake pipeline (Stage 4) both run it.

## The check `--check` cannot do: a well-formed row pointing at finished work

`--check` gates every *structural* property of a row. It cannot tell whether the row is still
NEEDED — and a row that names a task someone ticked weeks ago is well-formed, passes every gate,
and mis-dispatches the next session that reads it. This is the row-level face of the standing rule
that a screener proves WELL-FORMED, never STILL-NEEDED
([`OPERATING_CONSTRAINTS.md` → *Dispatching Backlog Work*](../../../agents/shared/OPERATING_CONSTRAINTS.md#dispatching-backlog-work--the-task-text-is-the-identity)).

```bash
python3 scripts/handoffs/stale_next_action.py      # reporter; exit 1 if any row names only ticked tasks
```

It flags a row only when **every** task id its `Next action` names resolves to a box in the owning
handoff and **all** of them are ticked. A row naming one done and one open task is not flagged — the
open one is still a live instruction. A row naming no resolvable id is not flagged either, because
prose next actions are legitimate and guessing at them manufactures false positives (the way the
`open == 0` prune heuristic did: 13 of 15 candidates were wrong, 2026-08-18).

It is a **reporter, not a gate**: a flagged row is occasionally correct, e.g. when the next action
deliberately records that a phase closed and an operator decision is owed. Read the handoff before
rewriting the cell. Measured on introduction (2026-09-17): 7 of the then-current rows were stale,
one of them naming a task ticked five weeks earlier.

## Related

- Checkbox discipline and the dashboard axiom: `agents/shared/SESSION_LIFECYCLE.md`
- Whether a ticked box is TRUE (its cited code exists on main), which `--check` cannot see:
  `docs/guides/agent-workflows/handoff-closure-audit.md`
- On handoff completion: extract findings to docs, `git mv` to `handoffs/completed/`, and **delete** its
  index row — terminal rows do not stay in the queue (`agents/shared/WORKFLOWS.md`)
- Operator decisions go in the master index's operator queue, because a form-screen cannot detect
  "this needs a human choice" and a decision buried in a handoff body gets missed.
