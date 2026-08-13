# mainC — Regenerate + screen the dispatch queue, reconcile counters

**You are mainC** (roster id `mainC`, lanes `[cpu, none]`, owns the queue generator). Bootstrap: run
`session_bus.py provision --agent mainC`, then `drain --agent mainC --triage`, then execute.

## Task

1. **Regenerate the dispatch queue** from your generator `scripts/coordination/backlog_queue_gen.py`.
   `tasks/BACKLOG-DISPATCH-QUEUE.md` carries a do-not-dispatch banner and is evidence-only — do not
   dispatch from it.
2. **Screen candidates** with `backlog_row_check.py`. Remember the standing lesson: a screener proves
   WELL-FORMED, not STILL-NEEDED — four of eight rows screened on 2026-08-12 were already satisfied in
   reality, so verify each row's premise against the world before emitting it.
3. **Emit** the screened dispatchable set as `task-propose` rows carrying `task_text` (the identity —
   never line numbers alone), `screened_by`, and `expected_occupancy` (`{est_h, basis, gating}`).
   Anchor rot is structural: `file.md:LINE` rots ~34.5% queue-wide.
4. **Reconcile the counter discrepancy** (handover §8): `index_state.py --summary` classified Open
   differently from a raw `grep -rhcE '^\s*- \[ \] '` over `handoffs/active/*.md`. The gap is
   mechanical (guarded/blocked boxes bucket separately). Re-derive both, state which is authoritative
   and why, and quote each with its as-of instant.

## Constraints

- lanes `[cpu, none]`: no compute, no region claims.
- **Do NOT push.** Commit locally only — push freeze pending operator ruling.

## Output

A fresh, screened dispatchable set (the other mains are waiting on this to stay saturated), plus the
counter-reconciliation note. Do not self-assign the rows you emit — they return to the queue for
coordinator dispatch.
