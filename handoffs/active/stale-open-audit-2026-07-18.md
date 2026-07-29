# Stale-Open Backlog Audit — 2026-07-18

**Status**: ACTIVE/REFRESHING — initial 22-handoff audit completed 2026-07-18; current-inventory reconciliation and exact-partition follow-up opened 2026-07-29.
**Priority**: HIGH
**Created**: 2026-07-18
**Categories**: governance, measurement, handoff-hygiene
**Parent index**: [`master-handoff-index.md`](master-handoff-index.md)

**Trigger**: operator question — *"if the inference-batch-loop consolidation is only 11 checkboxes, what are the remaining ~660 open tasks about?"* The board's headline open-task count (678 active+blocked, 2026-07-18) treats **every unchecked box as live work**. This audit measures how much of that is actually **stale-open**: work that landed, was superseded, deprioritized, parked, or is owned by another handoff — but whose boxes were never flipped (deprioritized ≠ done, so they were correctly never checked; they just shouldn't read as live backlog).

## Method

For each flagged handoff: read the full file, get git last-touch, classify the leading **Status**/**Priority** verbs, skim every open `- [ ]`, and cross-ref any "owned by / claim X there / superseded by" pointer to confirm where the work really lives. Verdict ∈ `LIVE | PARKED | SUPERSEDED | LANDED | DUPLICATE | MIXED`; each handoff gets a `live_open` vs `stale_open` split. **No checkbox flips** — recommendations are re-anchor / close / split / reactivate / add-`Lifecycle`-override.

Scope = the 22 handoffs the board's status-signal scan flagged (parked/landed keyword in Status or Priority). This is the *candidate* net; the board's own dimming signal is deliberately narrower (5 cards) to avoid ever dimming a live handoff.

## Headline (all 22 flagged handoffs)

| | Open tasks | Genuinely live | Stale-open |
|---|---:|---:|---:|
| Batch A (kernel/GPU, 8) | 64 | 14 | 50 |
| Batch B (routing/eval/RAG, 7) | 81 | 19 | 62 |
| Batch C (stack/infra, 7) | 28 | 6 | 22 |
| **Total (22)** | **173** | **39** | **134 (77%)** |

**Historical 2026-07-18 finding:** 77% of the open tasks in the flagged handoffs (134 of 173) were stale-open — landed, superseded, deprioritized, parked, or frozen behind an unfired gate. The then-derived `≈544` was a dated heuristic, not a current board count.

Caveat: this audits only the **22 flagged** handoffs (those whose Status/Priority carried a park/landed keyword). The other ~105 open handoffs were not individually audited. The current dispatch inventory, not this historical heuristic, is the source for current raw counts.

## Per-handoff verdicts

### Batch A — kernel / GPU

| Handoff | Open | Live | Verdict | Recommendation |
|---|---:|---:|---|---|
| [cpu-shape-specialized-gemv-decode](cpu-shape-specialized-gemv-decode.md) | 38 | 2 | MIXED | re-anchor — kernel LANDED 2026-04-24, SIMD Phase 0–5 deprioritized; box only the 2 live graph-fusion tasks |
| [gemma-challenge-kernel-techniques-v7](gemma-challenge-kernel-techniques-v7.md) | 9 | 6 | LIVE | keep — split K28 out (owned in mi210 roadmap); correctly NOT board-flagged |
| [llamacpp-v6-consolidation](llamacpp-v6-consolidation.md) | 6 | 1 | SUPERSEDED | close → completed (v6 cutover shipped 2026-06-26); re-anchor 5 items to v7 |
| [llama-cpp-dsa-contribution](llama-cpp-dsa-contribution.md) | 4 | 4 | **LIVE** | **add `Lifecycle: live` override** — board over-flags it "superseded" (only the *original* objective was); D2/D3 re-anchored + live. GLM-5.2 box co-owned by glm51-reap |
| [qwen36-27b-cpu-feasibility](qwen36-27b-cpu-feasibility.md) | 4 | 0 | PARKED | keep parked (CPU foreclosed) **+ cross-link the MI210 GPU campaign** (see callout) so it doesn't read as "dead model"; consider close |
| [gpu-drafter-mi200-investigation](gpu-drafter-mi200-investigation.md) | 1 | 0 | LIVE | re-anchor — Stage 4 box blocked on Stages 1–3 (failed economics 2026-07-17); add drafter-redesign task |
| [sarathi-serve-cpu-evaluation](sarathi-serve-cpu-evaluation.md) | 1 | 0 | PARKED | **reactivate** — multi-tenant trigger may have fired via batched-decode E1/E2 (active) |
| [agent-file-prose-compression](agent-file-prose-compression.md) | 1 | 1 | LIVE | keep — single operator rollout decision pending |

### Batch B — routing / eval / RAG

| Handoff | Open | Live | Verdict | Recommendation |
|---|---:|---:|---|---|
| [decision-aware-routing](decision-aware-routing.md) | 26 | 3 | PARKED | re-anchor — core FROZEN/closed in routing-truth-restoration W8; keep only Factory-ai/URE backlog |
| [learned-routing-controller](learned-routing-controller.md) | 17 | 2 | MIXED | split — live BGE+MLP rollout decision vs FROZEN Phase 1.5+ expansion |
| [glm51-reap-cpu-evaluation](glm51-reap-cpu-evaluation.md) | 11 | 9 | LIVE | keep — real work; true blocker = operator-approved GLM inference runs |
| [colbert-reranker-web-research](colbert-reranker-web-research.md) | 10 | 2 | PARKED | re-anchor — close S5 request-path NO-GO; keep inference-gated LateOn/DenseOn latency+A/B |
| [internal-kb-rag](internal-kb-rag.md) | 8 | 0 | LANDED | re-anchor — K1–K7 CERTIFIED 2026-06-13; keep only deferred K8 + optional Hy-MT2 |
| [minddr-deep-research-mode](minddr-deep-research-mode.md) | 8 | 2 | LIVE | keep — MD-9 A/B inference-gated. **Reactivate note**: Phase-2 hardware gate flipped (DGX→MI210 present) |
| [x-mas-text-routing](x-mas-text-routing.md) | 1 | 1 | LANDED | re-anchor — enforce enabled (`d4a6c927`); convert to standing telemetry-watch |

### Batch C — stack / infra

| Handoff | Open | Live | Verdict | Recommendation |
|---|---:|---:|---|---|
| [model-stack-single-source-update-pipeline](model-stack-single-source-update-pipeline.md) | 7 | 0 | PARKED | re-anchor as the authoritative consumer-SSoT contract; reconcile the stale X-MAS default-off box (enforce already enabled) |
| [standardized-stack-update-pipeline-finalization](standardized-stack-update-pipeline-finalization.md) | 3 | 0 | **DUPLICATE** | consolidate/close into `stack-change-governance-pipeline`; core landed |
| [per-request-reasoning-budget](per-request-reasoning-budget.md) | 4 | 4 | LIVE | keep — llama.cpp implementation genuinely pending (inference window + experimental branch) |
| [unified-trace-memory-service](unified-trace-memory-service.md) | 3 | 0 | PARKED | split — close landed T1–T6 nav parent; keep T7 (Hermes-daily-use gate, unfired) + consolidation parked |
| [frontier-f2-self-running-lab](frontier-f2-self-running-lab.md) | 2 | 2 | LIVE | keep — W3 accumulating now (real quiet-window batches producing verdicts), W4 sequenced |
| [sliders-local-validation](sliders-local-validation.md) | 8 | 0 | PARKED | **reactivate signal** — KB-RAG K7 reopen precondition FIRED 2026-06-13; surface to operator (still needs explicit ask; else keep parked, LOW/speculative) |
| [security-review-skill](security-review-skill.md) | 1 | 0 | PARKED | close — skill shipped + in production; keep CI-gate as a deferred backlog note |

## Cross-cutting findings

1. **Reopen-triggers that already fired (REACTIVATE candidates).** MI210 GPU installed 2026-07-02 flipped hardware gates that predate it: `gpu-drafter-mi200` (fired; Stages 1–2 ran + failed economics), `minddr` Phase-2 (DGX abandoned → MI210 training-viability smoke now possible), `sarathi-serve` (multi-tenant trigger via active batched-decode E1/E2). These read as "parked" but their premise changed.

2. **The Qwen3.6-27B fragmentation error (exemplar).** `qwen36-27b-cpu-feasibility` is correctly parked *on CPU* (BW-roofline ~7.5–9 t/s, GDN spec-dec wall) — but the **same model was characterized extensively on the MI210 GPU** in the operator-launched 2026-07-03 speed campaign (`progress/2026-07/2026-07-03-mi210-qwen36-27b-speed-campaign.md`): plain Q8 29.5 → **40.4 t/s (+37%)** via embedded-NEXTN MTP + MMVQ→MMQ fix (`de447119f`), EAGLE-3 tested (no-go), GDN-MFMA profiled+killed. That banked "dense-Q8 +37%" win in `v7-promotion.md` is this model. **The parked CPU handoff never cross-links the GPU campaign** — so reading it alone wrongly implies the model is dead. A single research thread's work is split across a parked handoff and a thriving one that it doesn't reference. This is why the raw open count both over-counts backlog *and* mis-reads liveness.

3. **Frozen-behind-an-unfired-gate is the dominant stale pattern.** The largest stale masses (decision-aware-routing 23, learned-routing-controller 15, GEMV 36) are all work correctly halted by an explicit gate whose reopen trigger has been tested and NOT fired (DAR-1 replay 0.00%; GEMV kernel-ceiling proven barrier-bound). Boxes are honestly unchecked; they simply aren't live.

4. **Board signal reconciliation.** The live board dims only 5 cards (high-precision). This audit's wider net (22) surfaces LANDED/SUPERSEDED/frozen cases the conservative heuristic intentionally skips (e.g. `internal-kb-rag` LANDED, `decision-aware-routing` frozen). Fix path: encode audited verdicts as explicit `**Lifecycle**:` fields (authoritative over the heuristic) — including a `Lifecycle: live` override on `llama-cpp-dsa-contribution`, which the heuristic over-flags.

5. **A five-handoff duplicate cluster on the stack-update pipeline.** `model-stack-single-source-update-pipeline` (N11a), `standardized-stack-update-pipeline-finalization` (N11), `model-stack-update-pipeline-audit`, `model-stack-change-standardization-audit`, and `stack-change-governance-pipeline` all describe the **same landed pipeline**. `model-stack-update-pipeline-audit` self-demotes to "historical-detail support"; the routing index already merges N11 + governance into one row. **Authoritative pair**: `model-stack-single-source-update-pipeline` (consumer-SSoT) + `stack-change-governance-pipeline` (command/gates). **Redundant**: `standardized-stack-update-pipeline-finalization` + the two audit docs. Core work is landed; every remaining open box across the cluster is opportunistic-on-new-finding or evergreen discipline — none actionable now. Consolidating this cluster is the single highest-leverage backlog cleanup. **2026-07-18 execution correction (on verification):** the "retire 3" framing was too coarse — only `standardized-stack-update-pipeline-finalization` is cleanly retirable (its sole live box, W4 swap-CI, is co-tracked in both authoritative docs); `model-stack-update-pipeline-audit` has 2 **orphan-live** boxes (`ctx_model_max`, tap/policy-hint) tracked in *neither* authoritative doc, so it stays LIVE until they migrate; `model-stack-change-standardization-audit` is a repeatable **runbook**, not done-work. Soft-consolidation (Lifecycle + pointer notes) applied 2026-07-18; hard-archive + orphan-box migration + index repointing is operator-gated.

## Recommendations (follow-up tasks — no checkbox flips on the audited handoffs)

- [x] Add `**Lifecycle**: live` to `llama-cpp-dsa-contribution` (board over-flags it superseded) ✅ 2026-07-18
- [x] Cross-link the MI210 GPU speed campaign into `qwen36-27b-cpu-feasibility` (parked-on-CPU ≠ dead model) ✅ 2026-07-18
- [x] Surface the fired reopen-triggers (gpu-drafter MI210-gate, minddr DGX→MI210, sarathi batched-decode E1/E2) with dated notes + reactivate `- [ ]` tasks in each handoff ✅ 2026-07-18
- [ ] Re-anchor GEMV to its 2 live graph-fusion tasks; move the deprioritized SIMD Phase 0–5 plan to a closed appendix
- [ ] Close/relocate the LANDED/SUPERSEDED handoffs (v6-consolidation → completed; kb-rag K1–K7 certified; x-mas → telemetry-watch)
- [ ] Split `learned-routing-controller` and `decision-aware-routing`: live rollout/backlog vs frozen-behind-unfired-gate expansion
- [x] Stack-cluster soft-consolidation (corrected on verification — NOT a clean "retire 3"): superseded `standardized-stack-update-pipeline-finalization` (W4 co-tracked); kept `model-stack-update-pipeline-audit` LIVE (2 orphan boxes); flagged `model-stack-change-standardization-audit` as a repeatable runbook ✅ 2026-07-18
- [ ] Stack-cluster HARD-archive (operator-gated): git-mv the superseded + runbook docs to `completed/`, migrate the audit's 2 orphan-live boxes (`ctx_model_max`, tap/policy-hint) into the SSoT, repoint the ~10 inbound index links
- [x] Surface the SLIDERS reopen precondition (KB-RAG K7 certified 2026-06-13) as a fired-but-needs-operator-decision note ✅ 2026-07-18
- [x] **Publish the current dispatch-inventory baseline ✅ 2026-07-29**: [`BACKLOG-DISPATCH-QUEUE.md`](../../coordination/session-bus/tasks/BACKLOG-DISPATCH-QUEUE.md) reports **1,103 unchecked active-handoff tasks at sweep start** and **~232 none-lane, unblocked tasks dispatchable now**. This supersedes the historical `≈544` heuristic; it is an inventory count, not an exact audited live/stale partition. The exact partition remains open below.
- [ ] **NEW 2026-07-29 — Extend the stale-open audit to an exact current live/stale partition, then present a derived dashboard field with audit date and source.** The original 22 audited handoffs now contain 208 open tasks (vs 173 at audit time); current lifecycle parsing identifies only 58 high-precision parked/superseded rows, so neither source can certify the remaining 949-or-fewer tasks as live.
- [ ] Extend the audit to the ~105 un-flagged open handoffs to convert "≤544" into an exact live count

> All verdicts above are **observations** for backlog-hygiene decisions, not measurement-gating numbers. No production kernel, registry, or handoff checkbox was modified by this audit.
