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

## Related

- Checkbox discipline and the dashboard axiom: `agents/shared/SESSION_LIFECYCLE.md`
- On handoff completion: extract findings to docs, `git mv` to `handoffs/completed/`, and **delete** its
  index row — terminal rows do not stay in the queue (`agents/shared/WORKFLOWS.md`)
- Operator decisions go in the master index's operator queue, because a form-screen cannot detect
  "this needs a human choice" and a decision buried in a handoff body gets missed.
