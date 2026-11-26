# EPYC Handoff — Master Index

**Purpose**: **routing only.** Find your domain index, then your row. This file owns no backlog rows —
it is the cheapest hop, so it stays short. Work lives in the domain indices; history lives in `progress/`
and `handoffs/completed|archived/`.

> **Live campaign state** (autopilot posture, freeze status, active lanes):
> [`CURRENT-CAMPAIGN.md`](CURRENT-CAMPAIGN.md) — read it before starting anything that touches the
> production stack.

> **UFH-13, the thesis experiment, is PARKED (operator, 2026-09-28)** until an autopilot run trains escalation on the
> swapped stack (after the 2nd MI210;
> [`thesis-experiment-orchestrator-vs-strongest-model.md`](thesis-experiment-orchestrator-vs-strongest-model.md)).
> Until then: infrastructure and design work, and Jev techniques (`typed-decision-plane.md` operator rulings).
> Boxes marked `❄ FROZEN 2026-09-27` stay frozen for inference-bearing steps only. Posture: `CURRENT-CAMPAIGN.md`.

## Domain indices

| Domain | Index | Scope |
|--------|-------|-------|
| Inference research | [inference-research-index.md](inference-research-index.md) | Kernels, quantization, serving performance, models (CPU **and** GPU) |
| Routing / autopilot / stack | [routing-and-optimization-index.md](routing-and-optimization-index.md) | Orchestrator, registry, stack lifecycle, autopilot, fleet coordination |
| Research & evaluation | [research-evaluation-index.md](research-evaluation-index.md) | Benchmarks, scorers, audits, research programs |
| User-facing harness | [user-facing-harness-index.md](user-facing-harness-index.md) | REPL/UX, prompting, memory, output compression (surface, not an implementation commitment) |
| Pipelines & integration | [pipeline-integration-index.md](pipeline-integration-index.md) | Ingestion, document/RAG pipelines, knowledge base |
| Reviewer control plane | [reviewer-control-plane-index.md](reviewer-control-plane-index.md) | Reviewer roles, capability gates, control-plane policy |

**Exactly one index owns each handoff.** A handoff listed twice is a defect — `index_state.py --check`
fails on it. Cross-domain relevance is a `Deps` edge, never a second row.

## Operator decision queue

Decisions only the operator can make. **This is the one hand-maintained list in this file** — it exists
because a form-screen cannot detect "needs a human choice", and a decision buried in a handoff body gets
missed (measured: G9-disk sat unnoticed for two weeks and governed 227 GB).

| ID | Decision | Owner | Open since |
|----|----------|-------|-----------|
| OP-TOKEN-DISPATCHER-RESTART | Dispatcher stays STOPPED (doctrine already ratified 2026-11-06). Before any restart: `handoff_sessions.py preflight-restart` must pass, unpark sessions as needed, Codex reset 2026-11-11. | [engineering-hygiene-backlog.md](engineering-hygiene-backlog.md) TOKEN-DISPATCHER-RESTART-GATE | 2026-11-06 |
| OP-WT-NEEDS-HUMAN | DECIDED 2026-11-26: force-remove the ak-lanes lane2 and lane5 worktrees (dumps regenerable). pipeline-mgmt applies. | — | 2026-11-26 |
| OP-75 | NOT YET THE OPERATOR'S (2026-11-26 check): the TD-30e ratify script does not exist; an agent must write it from docs/coherence-gate.md §1a and analysis/classifier-rectify/07-instrument-era-row.DRAFT.yaml, then the operator signs. | [routing-program.md](routing-program.md) TD-30e | 2026-11-26 |
| OP-HSOD4 | DECIDED 2026-11-26: **A**, one shared request generation budget for `max_tokens`. Owner implements per the package. | [package](../../docs/design/hs-od-4-max-tokens-decision-prep-20261006.md) | 2026-11-26 |
| OP-LR8 | DECIDED 2026-11-26: **B**, coordinated owner-boundary handover of the event duty. Owner implements. | [package](../../artifacts/operator/decisions/LR8-event-duty-handover-20261006/README.md) | 2026-11-26 |
| OP-72 | Sign STACKCHG-HYGIENE-20261003 (KVU-16a measured 38.03 GiB; SCG-PRIORS-WARM seeding scope; DRAFT-SEL-2 drafters form). `--validate-only` VALID, 68 pins; argv 11/11 unchanged, no relaunch. Command: `RATIFY_OPERATOR="<name>" bash /mnt/raid0/llm/tmp/stack-change-hygiene-20261003/ratify_stackchg_hygiene_20261003.sh --attest RATIFY-STACKCHG-HYGIENE-20261003` (operator terminal) Note: 38.03 GiB is the LOAD-time non-KV; :8083 grows +7.2 GiB while serving (KVU-16h/16i), which this package does not change. | [stack-change-governance-pipeline.md](stack-lifecycle-program.md) → SCG-PRIORS-WARM, DRAFT-SEL-2; [kv-unified-stack-rollout.md](kv-cache-program.md#track-kv-unified-stack-rollout) → KVU-16a | 2026-10-04 |
| OP-59 | DECIDED 2026-11-26: approve per-call `snapshot:false` only (TUI undo kept) and age out headless actor sessions in opencode.db. Owner applies. | — | 2026-11-26 |
| OP-1 | PARTLY APPLIED 2026-11-26: W-34 blacklist purge on orchestrator main (59a1d469). Remaining: W-33 P2 amendment bundle has no text yet; an agent drafts RATIFY-AUTOPILOT-P2 from a refreshed `model_gate_report.py` run, then the operator signs. | [autopilot-program.md](autopilot-program.md) | 2026-11-26 |
| OP-33 | DECIDED 2026-11-26: release the 4 old rollback-anchor holds (v9 archive is the only anchor); pipeline-mgmt brings a keep/delete list for the ~128 G of ambiguous artifacts. The Qwen3.5-122B PRODUCTION label is a registry defect for the registry owner. | [2026-08-31-disk-reclaim-menu.md](../../progress/2026-08/2026-08-31-disk-reclaim-menu.md) | 2026-11-26 |
| OP-42 | APPLIED 2026-11-26: P-MEMEVAL-1 ratified (3ba9500c8). Remaining for the memory-program owner: book ONE inference window after the host reboot, M-12a (Tulving) then M-12b (BEAM); re-pin the judge recipe first; pin BEAM's headline ability list in the run receipt. | [memory-program.md](memory-program.md) M-12 | 2026-11-26 |
| OP-AKU-CONTROLS | Choose whether to prepare a narrowly scoped control-only bootstrap policy for ratification, or require an existing qualified same-frame panel. No provisional PASS, candidate ranking or promotion authority is granted by this request; raw preparation and discovery continue. | [autokernel-unified-surface-program.md](autokernel-loop.md#track-autokernel-unified-surface-program) → AKU-07x | 2026-09-09 |
| OP-25 | After C5-3 produces a live gfx90a correctness run, choose whether to leave SOL scoring disabled or port measured gfx90a constants for k215 only. Recommendation: k215-only if scoring is needed; never present the four >100×-headroom seeds as speed-of-light objectives | [agentic-rocm-kernel-authoring.md](rocm-kernel-authoring.md#track-agentic-rocm-kernel-authoring) C5 | 2026-08-16 |
| OP-29 | OPEN (operator 2026-11-26: keep open, no downloads now). Video generation, 165 GB download. | EVL-32 | 2026-11-26 |
| OP-83 | DHM-4: label the 30-item pilot (the private pilot set), then run dhm4_pilot_check.py; the other 70 only if it prints PROCEED_TO_70. | [dev-harness-trace-mining.md](memory-program.md#track-dev-harness-trace-mining) DHM-4 | 2026-10-22 |
| OP-AK-HOLD | AutoKernel launch hold, kept in force (operator 2026-10-24, reconfirmed 2026-11-09; reconfirmed again 2026-11-26: NOT lifted). Blocks new AK search launches, CH-27 Q38FN floors, AK-Q38FN-64K-FLOOR and the C1-05 rollback merge; a named row may run only under an explicit operator exception, as AK-C9-Q38FN-FLOOR did. | [workspace-58-champion-calibration.md](workspace-58-champion-calibration.md) CH-27 | 2026-10-24 |

Full text for OP-1..OP-6 (including the closed OP-2 and the superseded narration) is preserved in
[`../archived/master-handoff-index-history-through-2026-08-10.md`](../archived/master-handoff-index-history-through-2026-08-10.md).
OP-3, OP-19, OP-53, OP-66, OP-67, OP-68, OP-69 and OP-70 (resolved) are preserved in
[`../archived/master-handoff-index-history-through-2026-09-14.md`](../archived/master-handoff-index-history-through-2026-09-14.md).
OP-64 (the HS-19 harness↔orchestrator interface discussion) was DECIDED by the operator on 2026-09-27, when the
narrowed plan was adopted:
- HS-19a is done, and HS-19d.0, the design, stays done.
- HS-19b, HS-19c and HS-19d P1–P6 are frozen behind UFH-13.

Recorded in [harness-selection-and-integration.md](harness-program.md#track-harness-selection-and-integration) → HS-19d.
OP-61 (OD-A, KTransformers) was DECIDED by the operator at the 2026-09-26 research-intake plan approval, before it
reached the queue: KTransformers runtime declined for now; MI210 port investigation open. Recorded in
[fable5-window2-findings-02-heterogeneous-gpu.md](../completed/mi210-serving-program.md#track-fable5-window2-findings-02-heterogeneous-gpu) → R-A10; the follow-on is its F7.
OP-TOC-RD-1A (DECIDED 2026-10-06, choice 1B: both credential fixtures stay scanned) and OP-80 (DECIDED 2026-10-07:
wire `check_cpu_fa_real_mask_identity` into `run.py`) were pruned from the queue at the 2026-10-22 operator `/wrap-up`.
OP-73 (APPLIED 2026-10-06, option 2A host activation) was pruned from the queue at the 2026-10-23 operator /wrap-up. Recorded in [non-inference-backlog.md](engineering-hygiene-backlog.md) → LR-6a.
Recorded in [tool-output-compression.md](context-and-token-economy.md#track-tool-output-compression) → TOC-RD-1a and
[autokernel-all-devices-all-dimensions.md](autokernel-akx-program.md#track-autokernel-all-devices-all-dimensions) → AKX-ALL-11 (OP80 settled).
OP-SEC-ART-POST-b (APPLIED 2026-10-24, operator ratify, root receipt `522f7fd33`) was pruned from the queue at the 2026-10-24 operator /wrap-up. Recorded in [model-artifact-integrity.md](stack-lifecycle-program.md#track-model-artifact-integrity) → SEC-ART-POST-b.
OP-CTXCKPT-RERUN (APPLIED, operator re-ran the ratify script, root receipt `b5934d982`) was pruned from the queue at the 2026-10-25 operator /wrap-up. Recorded in [kv-prefix-fork-and-paged-attention.md](kv-cache-program.md#track-kv-prefix-fork-and-paged-attention) → KPF-64.4.
OP-KPF64-ARM was DECIDED by the operator on 2026-10-22: compute-filler jobs may export `WINDOW_CONFIRMED=1` inside a
calendar-granted window. This unblocks s5-kpf64-replay, s5-akrsg-shakedown, s5-hsprof1-beam and s5-cme7-poker-smoke.
Recorded in [kv-prefix-fork-and-paged-attention.md](kv-cache-program.md#track-kv-prefix-fork-and-paged-attention) → KPF-64 and `docs/guides/agent-workflows/compute-fillers.md`.

## Standing contracts

`/workspace/MEASUREMENT.md` (adopted) · `instrument_eras.yaml` (epyc-orchestrator `orchestration/`) ·
current architecture review: [fable5-findings-00-executive-summary.md](../completed/fable5-findings-00-executive-summary.md)
(COMPLETE 2026-06-12 — standing reference, not an open row) ·
cross-domain governance: [stale-open-audit-2026-07-18.md](../completed/frontier-lab-automation.md#track-stale-open-audit-2026-07-18).

## Backlog state (generated)

Regenerate with `python3 scripts/handoffs/index_state.py`. Per-handoff detail — open/closed counts,
`last_advanced`, blocked/guarded — lives in `handoffs/active/.index-state.json`.

**`last_advanced` is the date a checkbox last changed**, not the file mtime and not the last commit:
prose edits and typo fixes are not progress. A domain whose oldest advance is months back has handoffs
nobody is moving.

<!-- BEGIN GENERATED index_state -->
| Domain | Handoffs | Open | Blocked | Oldest advance |
|--------|----------|------|---------|----------------|
| inference-research | 13 | 582 | 25 | 2026-11-07 |
| pipeline-integration | 1 | 2 | 0 | 2026-11-17 |
| research-evaluation | 4 | 258 | 2 | 2026-11-20 |
| reviewer-control-plane | 1 | 19 | 8 | 2026-11-24 |
| routing-and-optimization | 9 | 495 | 12 | 2026-11-05 |
| user-facing-harness | 2 | 110 | 1 | 2026-10-03 |
<!-- END GENERATED index_state -->

## Reporting

On completing a row: flip the checkbox in the owning **handoff**, update the row's `Next action` in its
domain index, append to `progress/YYYY-MM/`. Then run `python3 scripts/handoffs/index_state.py` to
refresh generated state and `--check` before committing. Numbers use the claim grammar in
[`MEASUREMENT_POLICY.md`](../../agents/shared/MEASUREMENT_POLICY.md).

Row contract (what may and may not go in a row):
[`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).
