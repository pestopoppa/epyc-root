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

## Resolved 2026-09-26

- **OP-61** — DECIDED 2026-09-26 at the research-intake Stage-3 plan approval (intake/orch-prior-art-20260926): KTransformers runtime DECLINED for now; MI210 port investigation OPEN. Implementation: [`fable5-window2-findings-02-heterogeneous-gpu.md`](../active/fable5-window2-findings-02-heterogeneous-gpu.md) R-A10 → F7, F6. (OP-61 never reached the queue, so there is no verbatim row to preserve.)

## Resolved 2026-09-23 (row removed at the operator-invoked wrap-up of 2026-09-27, ak-ds41-main)

- **OP-53** — Resolved 2026-09-23 without a pid allowlist: the competing-inference gate was rewritten to ask whether an
  unowned INFERENCE_LIKE process did WORK during the measured span (cumulative `utime+stime` brackets, allowance pinned
  ~100x above idle), not whether one exists. Research `a46c9d3d`; DS41-C2b-gate ✅ 2026-09-23 in
  [`../completed/deepseek-v41-flash-evaluation-completed-through-2026-09-24.md`](../completed/deepseek-v41-flash-evaluation-completed-through-2026-09-24.md).
  The DS41 campaign has run on it since (runs 10-10k). The queue row survived four days after its resolution.

| ID | Decision | Owner | Open since |
|----|----------|-------|-----------|
| OP-53 | **DeepSeek-V4.1 campaign is blocked by the competing-inference gate**: it classifies any UNOWNED `llama-server` as competing and raises, and :8074 (the requested planner) sits outside every owned scope with no allowlist parameter. Either (B) add a scoped, journalled pid allowlist — a source change that weakens a gate with INC-20260731 lineage — or (C) keep the default planner and stop :8074 for the window. The operator has said the stack stays up | [deepseek-v41-flash-evaluation.md](../active/deepseek-v41-flash-evaluation.md) | 2026-09-23 |

## Resolved 2026-09-27 (row removed the same day by the root writer, workspace-8d)

- **OP-66** — APPROVED by the operator in chat on 2026-09-27 (session
  https://claude.ai/code/session_01FKXdQsgLuwnFVWQ3npGfrJ), both rules as drafted, and both are now PRE-REGISTERED
  (frozen; a later change needs a new registration):
  - (a) UFH-13 thesis rule: X = 0.75, Y = 0.50 — G = (Q_A2 − Q_A1)/(Q_A0 − Q_A1) ≥ 0.75 at consultant device-seconds
    fraction d ≤ 0.50, and G's paired-bootstrap 95% lower bound > d. Recorded in
    [`thesis-experiment-orchestrator-vs-strongest-model.md`](../active/thesis-experiment-orchestrator-vs-strongest-model.md)
    § *Decision rule*; TE-0 ✅.
  - (b) UFH-12 kill rule: recall@5, M = 0.10, n ≥ 120, paired-bootstrap lower bound > 0, cheapest arm within X = 0.05.
    Recorded in [`repl-embedding-retrieval.md`](../active/repl-embedding-retrieval.md) REPL-EMB-2.1 ✅.
  - (c) TE-1 (the default-off `/v1` escalation flag for arm A2) approved in the same decision; built by another agent,
    and its box stays open until it lands.

| ID | Decision | Owner | Open since |
|----|----------|-------|-----------|
| OP-66 | **Confirm two pre-registered decision rules (narrowed plan).** (a) UFH-13 thesis experiment: SUPPORTED if A2 closes ≥ X = 75% of the A1→A0 quality gap at ≤ Y = 50% of A0's consultant device-seconds, and the lower CI bound of the gap closed beats the cost fraction (alternatives: 90/30 stricter, 50/50 beats-random only). (b) UFH-12 kill rule: hybrid must beat grep/BM25 on recall@k = 5 by M = 0.10, else stop at lexical; the cheapest arm within X = 0.05 of the best wins. Reasoning is in each handoff; both freeze at confirmation | [thesis-experiment-orchestrator-vs-strongest-model.md](../active/thesis-experiment-orchestrator-vs-strongest-model.md) TE-0; [repl-embedding-retrieval.md](../active/repl-embedding-retrieval.md) REPL-EMB-2.1 | 2026-09-27 |
