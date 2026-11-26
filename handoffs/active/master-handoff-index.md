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
| OP-WT-NEEDS-HUMAN | DECIDED 2026-11-11 (salvage+remove, keep 2 llama): 16 of 18 trees salvaged to fork `salvage/*-20261111` and removed (~11 GiB). Remaining: ak-lanes lane2 and lane5 refuse removal (untracked >5 MB disassembly dumps not salvaged); operator deletes or forces them. Kept: llama.cpp-experimental, preserved-20260724 (path absent). | [engineering-hygiene-backlog.md](engineering-hygiene-backlog.md) | 2026-11-06 |
| OP-HOSTMEM | Apply RATIFY-HOST-MEMORY-RULES-20261021 (3 host-safety rules + INC entry) from a fresh origin/main worktree, then the printed host earlyoom drop-in (dry-run gate first). | [non-inference-backlog.md](engineering-hygiene-backlog.md) NIB2-98 | 2026-10-21 |
| OP-OPCONST-3C4 | After OP-HOSTMEM lands: ratify two one-line OPERATING_CONSTRAINTS additions (compute-filler guide pointer; subagent close-out wires measurements into the belief kernel). Main prepares the bundle. | [CURRENT-CAMPAIGN.md](CURRENT-CAMPAIGN.md) operator items | 2026-10-21 |
| OP-75 | Ratify the coherence instrument eras as ONE package: OC1-coherence-gate-v1 + CLS1 (INF-70 harness1 synthetic-id labels) into orchestrator instrument_eras.yaml. The ratify script is being prepared (TD-30e); CLS1 `from:` = patch-04 commit time. Annex B B-COH-1 only if the paired gate is made mandatory for promotion | [typed-decision-plane.md](routing-program.md#track-typed-decision-plane) TD-30e | 2026-10-04 |
| OP-HSOD4 | Choose A shared request generation budget (recommended if reliable usage accounting), B reject explicit fields temporarily, or C retain turn-count interpretation. [Context, compatibility and effort](../../docs/design/hs-od-4-max-tokens-decision-prep-20261006.md). Default 1024 changes from per-call to total under A. | [harness-selection-and-integration.md](harness-program.md#track-harness-selection-and-integration) HS-OD-4 | 2026-10-06 |
| OP-LR8 | Choose A retain daemon/inactive duty, or B coordinated owner-boundary handover (recommended). [Exact candidate, cron delta and rollback](../../artifacts/operator/decisions/LR8-event-duty-handover-20261006/README.md). Earlier OP73 approval does not select this change. | [non-inference-backlog.md](engineering-hygiene-backlog.md) LR-8 | 2026-10-06 |
| OP-NIB2-71 | Choose archival retention (recommended) or deletion after independent durable custody; useful CH-8 guidance is already on main. [Concrete package](../../artifacts/operator/decisions/NIB2-71-rescue-disposition-20261006/README.md). | [non-inference-backlog.md](engineering-hygiene-backlog.md) NIB2-71 | 2026-10-06 |
| OP-72 | Sign STACKCHG-HYGIENE-20261003 (KVU-16a measured 38.03 GiB; SCG-PRIORS-WARM seeding scope; DRAFT-SEL-2 drafters form). `--validate-only` VALID, 68 pins; argv 11/11 unchanged, no relaunch. Command: `RATIFY_OPERATOR="<name>" bash /mnt/raid0/llm/tmp/stack-change-hygiene-20261003/ratify_stackchg_hygiene_20261003.sh --attest RATIFY-STACKCHG-HYGIENE-20261003` (operator terminal) Note: 38.03 GiB is the LOAD-time non-KV; :8083 grows +7.2 GiB while serving (KVU-16h/16i), which this package does not change. | [stack-change-governance-pipeline.md](stack-lifecycle-program.md) → SCG-PRIORS-WARM, DRAFT-SEL-2; [kv-unified-stack-rollout.md](kv-cache-program.md#track-kv-unified-stack-rollout) → KVU-16a | 2026-10-04 |
| OP-59 | opencode store: (a) global snapshot:false (per-call configs already carry it; global would disable TUI undo; recommend per-call only), (b) retention policy for opencode.db (10.8 GB live + 10.9 GB WAL; VACUUM cannot shrink it; recommend ageing out headless actor sessions) | [autokernel-orchestrator-actor-backend.md](autokernel-loop.md#track-autokernel-orchestrator-actor-backend) → OAB-15 | 2026-09-25 |
| OP-57 | Choose the actual contact address/URL and confirm launch readiness; dedicated existing email recommended. [Options, tradeoffs, copy and retained screenshots](../../artifacts/operator/decisions/WEB1-contact-publication-20261007/README.md). Default remains unpublished. | [amd-ai-lab-website-publication.md](engineering-hygiene-backlog.md#track-amd-ai-lab-website-publication) WEB-1 | 2026-09-25 |
| OP-1 | P0.1–P0.3 sign-off bundle | [autopilot-program.md](autopilot-program.md#track-orchestration-robustness-audit-2026-07-11) | 2026-07-11 |
| OP-5 | Reviewer control-plane decision bundle (P-REV-1 amendment) | [reviewer-control-plane-index.md](reviewer-control-plane-index.md) | 2026-07-16 |
| OP-33 | Disk reclaim: minimal set + GLM-5.2 + the 22-artifact zero-consumer purge all EXECUTED (743 G free). REMAINING: 7 ambiguous artifacts (~128 G) needing a call — chiefly a 70 G Qwen3.5-122B copy the lean registry calls PRODUCTION while the served path points elsewhere (a registry defect, not a disk question); plus the 4 rollback-anchor holds. `opencode.db` **RESOLVED 2026-09-07: 236.1 GB → 11.4 GB** (event change-feed pruned to 7-day retention, content tables untouched, `quick_check` ok, +225 GB reclaimed) | [2026-08-31-disk-reclaim-menu.md](../../progress/2026-08/2026-08-31-disk-reclaim-menu.md) §EXECUTED | 2026-08-31 |
| OP-42 | Admit BEAM 128K and Tulving 200ch/100K as M-12's instruments and grant one inference window: M-12a (Tulving) first, M-12b (BEAM) second. Eval-pool registration is a separate decision from adoption as an instrument (CJ-GATE precedent; MEASUREMENT.md is human-amendment-only) | [memory-program.md](memory-program.md) M-12 | 2026-09-07 |
| OP-AKU-HELD | Approve the additional versioned provider-held-cost lifecycle event and replay/settlement recovery (HIGH: 22 upstream, three processes). Descendant-event approval is already granted but does not include this addition; no live grant or measurement-policy change. | [autokernel-unified-surface-program.md](autokernel-loop.md#track-autokernel-unified-surface-program) → AKU-07j | 2026-09-09 |
| OP-AKU-CONTROLS | Choose whether to prepare a narrowly scoped control-only bootstrap policy for ratification, or require an existing qualified same-frame panel. No provisional PASS, candidate ranking or promotion authority is granted by this request; raw preparation and discovery continue. | [autokernel-unified-surface-program.md](autokernel-loop.md#track-autokernel-unified-surface-program) → AKU-07x | 2026-09-09 |
| OP-25 | After C5-3 produces a live gfx90a correctness run, choose whether to leave SOL scoring disabled or port measured gfx90a constants for k215 only. Recommendation: k215-only if scoring is needed; never present the four >100×-headroom seeds as speed-of-light objectives | [agentic-rocm-kernel-authoring.md](rocm-kernel-authoring.md#track-agentic-rocm-kernel-authoring) C5 | 2026-08-16 |
| OP-29 | Scope decision: is video generation a product need? Gates the 165 GB MiniMax-H3 Ref2VA + 10Eros-Max download (volume at 92%, 291 GB free) | [model-evaluation-queue.md](model-evaluation-queue.md#track-minimax-h3-video-generation-evaluation) EVL-02 | 2026-08-30 |
| OP-83 | DHM-4: label the 30-item pilot (the private pilot set), then run dhm4_pilot_check.py; the other 70 only if it prints PROCEED_TO_70. | [dev-harness-trace-mining.md](memory-program.md#track-dev-harness-trace-mining) DHM-4 | 2026-10-22 |
| OP-AK-HOLD | AutoKernel launch hold, kept in force (operator 2026-10-24, reconfirmed 2026-11-09). Blocks new AK search launches, CH-27 Q38FN floors, AK-Q38FN-64K-FLOOR and the C1-05 rollback merge; a named row may run only under an explicit operator exception, as AK-C9-Q38FN-FLOOR did. | [workspace-58-champion-calibration.md](workspace-58-champion-calibration.md) CH-27 | 2026-10-24 |
| OP-HOOK-REFACTOR | Review the cloud audit session's `refactor/containment-scanner` and `claude/vigilant-thompson-shpyh0` (epyc-root `scripts/hooks/check_filesystem_containment.sh` + scanner): they change the guard that enforces 'do not touch anything outside /mnt/raid0/llm/'. A safety boundary: land only with operator review. | [non-inference-backlog.md](engineering-hygiene-backlog.md) | 2026-10-24 |
| OP-W1-PR | Open the upstream PR from fork branch `w1-cpu-sparse-fa-prefill` @ `70ba79110` via the GitHub web UI (`gh pr create` refused: no CreatePullRequest permission). Text prepared in long-context-program.md; the W1 patch is also folded into the next composite after C16. | [long-context-program.md](long-context-program.md) | 2026-11-19 |

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
| inference-research | 13 | 585 | 25 | 2026-11-07 |
| pipeline-integration | 1 | 2 | 0 | 2026-11-17 |
| research-evaluation | 4 | 257 | 2 | 2026-11-20 |
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
