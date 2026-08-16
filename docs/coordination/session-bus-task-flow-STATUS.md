# Status note — `session-bus-task-flow.html` was design-ahead-of-runtime

**Written**: 2026-08-16 · **Task**: P1-5, [`handoffs/active/loop-owned-fleet-implementation.md`](../../handoffs/active/loop-owned-fleet-implementation.md)
· **Plan of record**: `docs/design/loop-owned-fleet.html`

## What this note is about

The flow document lives in the auditor worktree, not here:

```
/mnt/raid0/llm/worktrees/mains/auditor/docs/coordination/session-bus-task-flow.html
```

Last touched there at `44e8f785` (2026-08-13). It carries `AS OF 2026-08-13 UTC · implementation
through 82c1c5b4` and a red banner: **`FLEET ROLLOUT: OFF · code published through this Auditor
wrap · no daemon reload or role cutover claimed`**.

This note is a pointer and a scope marker. It does **not** edit that file — another worktree owns
it.

## What the document itself marks as not wired

The document's own legend defines four states. Counting the elements it tags:

| Legend key | Meaning per the document | Element count |
|---|---|---|
| `pushed` — solid green | Pushed / built code. "Published code evidence only; it does not mean reloaded, acknowledged, enabled, or live." | 22 |
| `local` — solid blue | Implemented locally; awaiting integration | 6 |
| `gap` — **dashed amber** | **Not yet wired** | **19** |
| `future` — gray | Protected policy / canary future | 13 |

Nineteen of sixty tagged elements are amber "not yet wired". They are not scattered: they are two
whole pipelines plus one role card.

**Section 4 — Compute blocker, graded window, lease, and execution.** Amber: `Typed blocker`,
`Inference intake`, `Window`, `Grant / deny`, `Finite dispatch`, `Run & drain`. Only
`Projection & plan` is green. The `inference` role card is the one amber role card, with the
document's own words: *"Compute planning exists; the bus loop is not wired."* The status registry
row is explicit — `Compute bus and role integration · gap · "No live compute_ready.json or
intake/window relay" · "Planner success is not an end-to-end compute workflow."`

**Section 5 — Auditor immutable-cut heavy wrap and pre-reboot barrier.** Amber: `Freeze cut`,
`Reconcile immutable cut`, `Shared docs transaction`, `Publish packet`, `Async failure`,
`Pre-reboot failure`. Only `Acquire operation lease` is green. Status registry row:
`Receipt-driven immutable-cut wrap · gap · "Typed lifecycle locally specified; manual wrap remains
current execution surface" · "Lease is real; automatic cut reconciliation/publish loop is not."`

Its own "Known gaps / audit questions" section adds: no live bus relay creates intake or window
records; delegated GPU grants stay disabled until a resource-claim provider is named; no
end-to-end immutable-cut executor replaces the manual wrap routine; daemon reload and per-role
instruction acknowledgment are unproven (`daemonReloadProven:false`,
`roleAcknowledgmentsProven:false`).

## Ruling

**The Loop-Owned Fleet plan supersedes both unwired pipelines.** The compute pipeline (section 4)
and the receipt-driven heavy-wrap pipeline (section 5) are design ahead of runtime as of
2026-08-16. They were never wired, and the plan of record replaces the design rather than
finishing it:

- Plan of record: `docs/design/loop-owned-fleet.html` — **untracked in git as of 2026-08-16**
  (`git ls-files --error-unmatch` fails on it). It exists only in this working tree until it is
  committed. Commit it before citing it as the authority from another clone or worktree.
- Implementation tasks: [`handoffs/active/loop-owned-fleet-implementation.md`](../../handoffs/active/loop-owned-fleet-implementation.md)
  — Phase 2 (`worker_runner` MVP: claim → typed brief → report) is the replacement for the amber
  dispatch/compute path, and the wrap-cadence ruling in P1-3(a) plus the per-task wrap rule govern
  the wrap path.

Do not treat an amber section of the flow document as a specification to build against. Treat it
as a record of a design that the Loop-Owned Fleet plan has since replaced.

## What should happen to the flow document

**Regenerate it from wired reality only.** The next version should contain the green/`pushed`
material and nothing else — a diagram of what the runtime actually does, with no
"planned integration" lane. A flow chart whose legend needs a fourth colour for *this part does
not exist* is a design document wearing the costume of an instrument, and the project has already
paid for reading design-ahead surfaces as status.

Conditions for the regenerated version:

1. Drop sections 4 and 5 entirely unless the Loop-Owned Fleet implementation has wired an
   equivalent — in which case draw the wired one, not the superseded one.
2. Drop the amber legend key. If a path cannot be drawn green, it does not go on the page.
3. Keep the `FLEET ROLLOUT` banner semantics: a commit is not a cutover. Publication evidence and
   runtime evidence stay separated, and `daemonReloadProven` / `roleAcknowledgmentsProven` stay
   visible.
4. The auditor worktree owns the file. Regeneration is that session's work, not a cross-worktree
   edit.

Until it is regenerated, this note is the reading instruction for it.
