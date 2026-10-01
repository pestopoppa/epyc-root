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

## Resolved 2026-09-28 (row removed by the root writer, workspace-8d)

- **OP-68** — SIGNED by the operator from a terminal on 2026-09-28 (02:52:34Z; `signed_by: pestopoppa`,
  `signature_channel: terminal`), receipt
  [`artifacts/operator/receipts/RATIFY-ARCHSWAP-20260927.json`](../../artifacts/operator/receipts/RATIFY-ARCHSWAP-20260927.json),
  options O-2 `follow-model`, O-3 `B1`. Applied the same day: the lanes merged (orchestrator with A-3 fix `9a4785e1`,
  research `76cecec4`, root `ec7748aa`) and the B1 API-only reload was done. Recorded in
  [`thesis-experiment-orchestrator-vs-strongest-model.md`](../active/thesis-experiment-orchestrator-vs-strongest-model.md)
  ARCHSWAP-1 ✅ to ARCHSWAP-3; the P1-P3 proofs are ARCHSWAP-3b.

| ID | Decision | Owner | Open since |
|----|----------|-------|-----------|
| OP-68 | **ARCHSWAP-20260927 signature (terminal).** The architect role swap (Flash-Next → `architect_general` for escalation; the 27B → `architect_critic`, keeping review and plan decomposition) was approved in chat as amended (A-1..A-5); `--validate-only` returns VALID. The auto-mode classifier blocks agent execution under your name, so run from a terminal: `cd /mnt/raid0/llm/tmp/archswap-20260927/root/artifacts/operator/stack-change-archswap-20260927 && RATIFY_OPERATOR="pestopoppa" THINKING_OPTION=follow-model BRINGUP_OPTION=B1 ./ratify_archswap_20260927.sh --attest RATIFY-ARCHSWAP-20260927`. Gates the UFH-13 bring-up (ARCHSWAP-2/3 → TE-pilot). | [thesis-experiment-orchestrator-vs-strongest-model.md](../active/thesis-experiment-orchestrator-vs-strongest-model.md) → ARCHSWAP-1 | 2026-09-27 |

## Resolved 2026-09-29 (row removed by the root writer, workspace-8d)

- **OP-67** — COUNTERSIGNED by the operator (Daniele) at an interactive terminal on 2026-09-29T10:25:56Z:
  [`artifacts/operator/countersign/COUNTERSIGN-20260927.signed.json`](../../artifacts/operator/countersign/COUNTERSIGN-20260927.signed.json)
  covers RATIFY-P-SERVE-SEL-1-20260926, RATIFY-OP63-REGION-LOCK-SCOPE-20260926,
  RATIFY-TRUST-BOUNDARY-RECEIPTS-FIX-20260926 and RATIFY-DAR-LAT-3H-CRITIC-THREADS-20260926.

| ID | Decision | Owner | Open since |
|----|----------|-------|-----------|
| OP-67 | **Terminal countersignature for four agent-executed or unattributed ratifications.** They are P-SERVE-SEL-1, OP-63, TRUST-BOUNDARY-RECEIPTS-FIX (it recorded `operator: "node"`) and DAR-LAT-3h. Each was approved in chat on 2026-09-26/27 and executed by the agent (workspace-8d). They stand as CHAT-CONFIRMED. To countersign, run from a terminal: `bash scripts/operator/countersign_20260927.sh` (it asks you to type COUNTERSIGN). | [COUNTERSIGN-20260927.md](../../artifacts/operator/countersign/COUNTERSIGN-20260927.md) | 2026-09-27 |

## Resolved 2026-09-29 (row removed by the root writer)

- **OP-69** — DECIDED (a) and LANDED. The operator approved landing in chat on 2026-09-29: orch `e0787feb` on main,
  flag `thinking_roles_chat_lane` enabled in production at `a504ba28`, derived `c62fcadd`, API-only reload. Live
  serving proof 2026-09-29 15:04Z (`/mnt/raid0/llm/tmp/archswap-20260927/serving-proof-20260929T150402Z/`). Closes
  `routing-intelligence.md` RI-22, RI-23 and RI-23a (receipt `RATIFY-RI23A-20260929`, root `05e13e75`).

| ID | Decision | Owner | Open since |
|----|----------|-------|-----------|
| OP-69 | **Land the RI-23 thinking-on chat lane** (decided (a), 2026-09-29). orch lane/orch-ri23-8d @ e0787feb, flag thinking_roles_chat_lane default OFF; RI-23b A/B supports it (flag OFF the review verdict never parses; ON both verdicts correct). gitnexus flags 4 HIGH/CRITICAL symbols -> operator landing approval; then API-only reload + flag flip. | [routing-intelligence.md](routing-intelligence.md) → RI-23 | 2026-09-29 |

## Resolved 2026-10-01 (row removed by the root writer)

- **OP-70** — RATIFIED. The operator approved it in chat on 2026-10-01 from the remote app ("approved: apply
  artifacts/operator/lessons-20260929-operating-constraints.patch to OPERATING_CONSTRAINTS.md and push"); applied
  unchanged by workspace-8d. The four rules are now in `agents/shared/OPERATING_CONSTRAINTS.md`: capture a gate's rc
  before any push; a peer CPU window means stop on anything but `open`; test checks on real artifacts before a scarce
  window; hand TTY-gated scripts over for a separate terminal. Origins: INC-20260929-*. Standing: CHAT-CONFIRMED (no
  terminal receipt), like the OP-67 set.

| ID | Decision | Owner | Open since |
|----|----------|-------|-----------|
| OP-70 | Ratify four 2026-09-29 lesson rules into agents/shared/OPERATING_CONSTRAINTS.md (human-only): peer CPU window stop-on-closing, test checks on live artifacts before a scarce window, capture gate rc before push, TTY scripts in a separate terminal — prepared patch | [INCIDENT_LOG.md](../../docs/reference/agent-config/INCIDENT_LOG.md) INC-20260929-*; artifacts/operator/lessons-20260929-operating-constraints.patch | 2026-09-29 |
