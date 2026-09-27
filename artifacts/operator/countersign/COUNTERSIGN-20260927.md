# Countersignature record — four agent-executed or unattributed ratifications (2026-09-27)

**State: CHAT-CONFIRMED; terminal countersignature PENDING.**

The state becomes COUNTERSIGNED when `artifacts/operator/countersign/COUNTERSIGN-20260927.signed.json` exists. Only
`scripts/operator/countersign_20260927.sh` writes that file, and only when the operator runs it from a terminal. No
agent has run it. Master queue row: OP-67.

## Why this record exists

A ratification across the human-amendment-only boundary is meant to prove that a **human** performed the amendment.
The typed `RATIFY` / TTY step in each ratify script is that proof. On 2026-09-26/27 the operator approved the four
ratifications below in chat. Session **workspace-8d**, the agent, then executed them: it ran the inner apply steps
or the ratify script itself. So the only record of consent on these paths is agent-written. A Fable audit on
2026-09-27 flagged all four.

The ratifications are **not** re-opened. The operator approved them, and they stand as landed. This record adds what
was missing:
1. It states plainly who approved and who executed.
2. It gives the operator a way to countersign from a terminal later. The operator works from the remote claude.ai
   app and cannot run terminal commands now.

- **Approval source (chat):** session transcript https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ
- **Executed by:** the agent, session workspace-8d (Claude), not the operator's own terminal.
- **Repair (2026-09-27):** every ratifier in `scripts/operator/` now refuses an unset `RATIFY_OPERATOR`, a system
  account (`node`, `root`, …), the invoking login (`id -un` / `$USER`) and an agent id. The shared guard is
  `scripts/operator/lib/ratify_operator.sh`. The receipt tool (`ratification_receipt.py`) now marks such a receipt
  REFUSED, so a `$USER` fallback cannot happen again.

## The four ratifications

| # | Gate id | Landed in | Approved in chat | Executed by | Operator field as recorded | Defect |
|---|---|---|---|---|---|---|
| 1 | `RATIFY-P-SERVE-SEL-1-20260926` | root `3573028b` (2026-09-26T19:49Z) | 2026-09-26 | agent (workspace-8d) | `pestopoppa (executed by Claude session workspace-8d at the operator's explicit instruction, 2026-09-26)` | The agent ran the inner apply steps, which bypassed the wrapper's typed-RATIFY TTY check |
| 2 | `RATIFY-OP63-REGION-LOCK-SCOPE-20260926` | root `cdf8232f` (2026-09-26T23:29Z) | 2026-09-26 | agent (workspace-8d) | `pestopoppa (executed by Claude session workspace-8d at the operator's explicit instruction, 2026-09-26)` | Same: executed by the agent, with no typed human step |
| 3 | `RATIFY-TRUST-BOUNDARY-RECEIPTS-FIX-20260926` | root `2850fa8c` (2026-09-26T19:48Z) | 2026-09-26 | agent (workspace-8d) | **`node`**, the container account from the `$USER` fallback | Unattributed: the receipt names no person |
| 4 | `RATIFY-DAR-LAT-3H-CRITIC-THREADS-20260926` | root `bf610d36` (2026-09-27T04:58Z) | 2026-09-27 | agent (workspace-8d) | `signed_by_uid: 1000` (no name) | The agent ran the package's ratify script (`--attest`); the receipt records a uid, not a person |

Receipts:
- `artifacts/operator/receipts/RATIFY-P-SERVE-SEL-1-20260926.json` → `artifacts/operator/ratify_p_serve_sel_1_20260926.json`
- `artifacts/operator/receipts/RATIFY-OP63-REGION-LOCK-SCOPE-20260926.json` → `artifacts/operator/ratify_op63_region_lock_scope_20260926.json`
- `artifacts/operator/receipts/RATIFY-TRUST-BOUNDARY-RECEIPTS-FIX-20260926.json` → `artifacts/operator/ratify_trust_boundary_receipts_fix_20260926.json`
- `artifacts/operator/receipts/RATIFY-DAR-LAT-3H-CRITIC-THREADS-20260926.json` (package `artifacts/operator/stack-change-dar-lat-3h-20260926/`)

## How the operator countersigns (later, from a terminal)

```bash
cd /workspace && bash scripts/operator/countersign_20260927.sh            # asks for your name, then COUNTERSIGN
cd /workspace && bash scripts/operator/countersign_20260927.sh --commit   # same, then commits the one signed file
```

The script:
- refuses when stdin is not a terminal;
- asks for your name, and refuses `node`, `root`, the login account and agent ids;
- asks you to type `COUNTERSIGN`;
- records your name, the UTC time, the uid, this file's sha256 and the four gate ids in
  `COUNTERSIGN-20260927.signed.json`.

It changes nothing else. It re-runs no ratification and touches no human-only path.

**Declining.** If you would rather not countersign one of the four, say so in chat. It is recorded here as declined.
Whether to revert that ratification is then a separate decision; a decline does not revert anything by itself.
