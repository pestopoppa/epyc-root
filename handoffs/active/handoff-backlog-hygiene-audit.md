---
title: Handoff backlog hygiene audit (archive-or-dereference aging handoffs)
status: stub — awaiting assignment (drafted 2026-05-27 at operator request)
created: 2026-05-27
owners: unassigned (operator to assign)
priority: LOW (housekeeping; non-inference; perform as a wrap-up action)
related:
  - handoffs/completed/bulk-inference-2026-04-packages.md   # worked example of the pass
  - handoffs/completed/cross-role-nway-contention-matrix.md # worked example (archive)
  - .claude/commands/wrap-up.md                             # Step 3 "Index hygiene" = the procedure to follow
---

# Handoff backlog hygiene audit

## Problem

`handoffs/active/` holds ~101 handoffs; `scripts/validate/check_handoff_freshness.sh` flagged **56 aging** (>14d) and 0 stale (>30d) as of 2026-05-27. Many are likely complete or overtaken but remain inline + index-referenced. Per the operator's index-discipline rule (memory `feedback_index_tracks_outstanding_only`), indices should track **outstanding TODOs only**; completed work should be archived (if genuinely done) or its index entry dereferenced/trimmed (if open work remains).

The **bulk-inference campaign orbit was already done** this way on 2026-05-27 (epyc-root commit `2b63ae1`: campaign handoff 1183→452 lines; master-index `#53` cell 6932→900 chars; `cross-role-nway-contention-matrix` archived). This handoff extends the same pass to the rest of the aging tree.

## Scope

All aging handoffs in `handoffs/active/` **except** the bulk-inference orbit (already done: `bulk-inference-campaign`, `cross-role-nway-contention-matrix`, `within-role-placement-state-machine`, `bep-dcp-falsification-harness`). Non-inference housekeeping — **no benches, no host-quiet window required** (`feedback_no_concurrent_inference` does not gate this).

## Method (this is a WRAP-UP action — surface before pruning)

1. `bash scripts/validate/check_handoff_freshness.sh` → get the current aging list.
2. For each aging handoff, classify against **actual code / tests / commits** — verify, don't trust prose (many predate the 2026-02-25 monorepo split and reference stale paths per CLAUDE.md):
   - **Genuinely complete** → `git mv` to `handoffs/completed/` + add a completion banner + repoint its sibling `.md` links to `../active/`; remove its master-index / domain-index reference.
   - **Open work remains** → keep active; trim its index entry to the open items only; move any chronology into the progress log.
3. Follow `.claude/commands/wrap-up.md` Step 3 "Index hygiene": **archive, never delete**; **list everything pruned under an `## Index pruning` heading** for operator review before it leaves the active tree.
4. Update `handoffs/active/master-handoff-index.md` (registry + priority queue) and the 5 domain sub-indices.

## Constraints

- Index changes require operator visibility — do this **as a wrap-up** and surface the prune list; do NOT prune ad-hoc mid-work.
- Do NOT archive anything with open work. When in doubt, dereference/trim rather than archive.
- Preserve git history (`git mv`); fix relative links after moves; keep historical progress-log references intact (append-only).

## Deliverable

Leaner `handoffs/active/` tree; master-index tracking outstanding TODOs only; a prune list reported for operator review.
