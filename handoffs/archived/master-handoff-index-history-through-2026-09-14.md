# Master handoff index — operator queue history through 2026-09-14

Rows removed from the operator decision queue at the operator-invoked wrap-up of 2026-09-14 (session noninf-20260914). Preserved verbatim for provenance; the older sibling `master-handoff-index-history-through-2026-08-10.md` is immutable.

## Resolutions

- **OP-3** — Resolved moot 2026-09-14: the code the batch decided about is gone — `dispatch_swarm_fanout` was deleted in epyc-orchestrator `771348c8` (2026-06-16, "delete dead DAR-6 swarm_fanout module"). Loose thread filed: `src/features.py:211,563` still carries an orphan default-off `swarm_fanout` FeatureSpec.
- **OP-19** — Resolved 2026-08-27 by `artifacts/operator/ruling_op19_e8_chain_20260827.json` (E8 chain retired; reseed gate re-anchored to the promotion boundary and scoped; replay 18 corpora / 5,324 re-scored / 0 divergences).

## Removed rows (verbatim)

| ID | Decision | Owner | Open since |
|----|----------|-------|-----------|
| OP-3 | Zero-inference decision batch — residual `dispatch_swarm_fanout` items | [routing-and-optimization-index.md](routing-and-optimization-index.md) | 2026-07-14 |
| OP-19 | Rule the E8 chain retired (or not): B9/B10 are BLOCKED-AND-LIKELY-MOOT — their source evidence was destroyed and the era advanced to E9 on 2026-08-11, so both boxes wait on this ruling alone. **Widened 2026-08-16**: the same ruling must also restate the `CURRENT-CAMPAIGN.md:103,106` reseed gate against E9 — as written it blocks every stack/lineup/registry change on an E8-form reseed that can no longer be satisfied (the file contains zero occurrences of "E9"), and 8 further handoffs assert the same gate | [autopilot-decision-plane-audit-2026-07-22.md](autopilot-decision-plane-audit-2026-07-22.md) | 2026-08-12 |

## Resolved 2026-09-15

- **OP-20** — RULED 2026-09-15 at the research-intake Stage-3 plan approval (session noninf-20260914, plan S3-OP-01): option (a) — non-infra `task_failed` → WRONG in both producers, infra → EXCLUDED in both. Implementation: `autopilot-continuous-optimization.md` AP-64.

| ID | Decision | Owner | Open since |
|----|----------|-------|-----------|
| OP-20 | One ruling on `task_failed` scoring applied to BOTH producers (`eval_tower:1339` excludes it; the seeding path scores it WRONG) — until it lands, quality numbers are not comparable across producers. Auditor recommends: non-infra → WRONG in both, infra → EXCLUDED in both | [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) | 2026-08-12 |
