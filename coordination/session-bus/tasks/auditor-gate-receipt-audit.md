# auditor — Governance audit: ratified-receipt gates + counter reconciliation

**You are auditor** (roster id `auditor`, reviewer). Bootstrap: `drain --agent auditor --triage`,
then execute.

## Task 1 — verify the six ratified-but-unchecked gates (read-only)

`tokens/token-queue.md` carries a daemon "spent-gate-notice" naming six gates that each have a
receipt on disk reading `status: ratified` while their checkbox still reads `[ ]`:

`RATIFY-P-BENCH-4-FG4B-AFFINITY-20260729`, `RATIFY-E8-FINAL-C1-RETRY-CAPACITYFIX-20260729`,
`RATIFY-CONSOLIDATED-ERA-ROWS-20260811`, `RATIFY-ANNEXG-V9-CURRENCY-20260811`,
`RATIFY-V9-CPU-BENCH-ERA-ADVANCE-20260811`, `RATIFY-CPU-BENCH-BINARY-VERSION-20260811`.

For each: confirm the receipt exists at `artifacts/operator/receipts/<gate>.json` and reads
`ratified`, and confirm the tree reflects the ratified state (e.g. era rows, annex-G pin, binary
version). Do **not** tick any checkbox — only the operator ticks. Produce a one-screen table:
gate → receipt path → status → tree-reflects-ratified-state (yes/no + one-line evidence).

## Task 2 — independently re-derive the counter discrepancy

`index_state.py --summary` (read-only) vs raw `grep -rhcE '^\s*- \[ \] ' handoffs/active/*.md` give
different open/closed totals. Re-derive both, explain the mechanical cause, state which is
authoritative for dashboard purposes, and quote every number with an as-of instant.

## Wrap-up at the audit boundary — REQUIRED

On completing this audit pass, run the standard wrap-up routine (`agents/commands/wrap-up.md`) to
checkpoint the verdict, evidence, and handoff follow-ups: flip/add `- [ ]`→`- [x]` checkboxes for
anything you record as done, write the verdict with its receipt paths, and commit. The narrow
standing exception in `agents/auditor-main.md` workflow step 4 authorizes this audit-pass
checkpoint — persist the verdict before the next audit.

## Constraints

- lanes `[none]`; reviewer role. Read-only: tick nothing, sign nothing, edit no trust-boundary file,
  no region claims, no compute.
- **Push policy (operator ruling 2026-08-13): pushes to docs/handoffs are now PERMITTED** — commit
  and push your governance/handoff/progress updates at wrap-up. Still do NOT push kernel or
  orchestrator code changes.

## Note

`fleet_watch` briefly logged you as STUCK-INPUT with unsubmitted text `'Implement {feature}'` (~17:38Z);
`tmux_adapter.py pending` now reads clean. If that text was not yours, flag it — a composer that
held stray text is a finding, not noise.
