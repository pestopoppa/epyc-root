# Architect Model Comparison Benchmark

**Status (2026-07-20): SPEC'd — GATED, not yet runnable.** Waiting on three sequential gates
(§Gating). All prep that requires no inference is done this session (spec, evidence note, arm-GGUF
confirmation); the AIME'25 adapter build can proceed anytime; the inference runs are operator/
quiet-window-gated **and** sequenced *after* v7 promotion and the `inference-batch-loop.md` backlog.

**One-line purpose:** decide, decision-grade, **which model holds the `architect` role** (deep
reasoning / multi-step planning) — because the only local quality signal we have for the GPU-resident
candidate (AXA-1's Δ0.0pp IQ2≈Q4 parity) is **statistically powerless on reasoning** (n≈4/hard-suite),
and every published benchmark of the exact models is unreliable.

**Rationale + full evidence:** [`../../docs/reference/architect-model-selection-2026-07-20.md`](../../docs/reference/architect-model-selection-2026-07-20.md)
(two theses w/ cited numbers, the AXA-1 gap analysis, the decision tree). **Read it first.**

## Open decisions (operator to confirm)
- **[ ] OD-1 — Phase-2 planning-task design.** Phase 1 (AIME'25 + GPQA-Diamond + MMLU-Pro control) is
  the **decisive reasoning core and can proceed as specified** — it settles the reasoning-depth question
  (H1/H2/H3) on its own. **Phase 2 (tool-using multi-step planning) is NOT hard-committed:** the
  recommended default is **SWE-bench-Verified in agentic mode, scored by its FAIL_TO_PASS test oracle**
  (objective, no model-judge), but the alternative is bespoke tasks mined from real architect
  orchestration logs (only viable if an objective success criterion exists). **Confirm the Phase-2
  design before building its scorer.** Rationale for keeping it open: model-as-judge scoring is
  near-random (reviewer control-plane finding), so Phase 2 must have an objective oracle or be dropped.
- **[ ] OD-2 — whether Phase 2 runs at all.** If Phase 1 is unambiguous, Phase 2 may be unnecessary;
  the operator decides whether the tool-use validation layer is worth the extra inference budget.

## Why this bench exists (the gap, in one paragraph)
The architect wants **large-total + moderate-active** (active⇒reasoning, total⇒knowledge —
2505.09388 / 2508.18672), which makes the **122B-A10B** the literature default. Its GPU-resident IQ2
form (AXA-1: 43.7 t/s single / 148.7 agg@B32, 2.2×/~8–9× over the ~20 t/s CPU-Q4 incumbent) passed a
**212-question paired eval Δ0.0pp** — but that pool was **instruction-following (84) + factual QA (72)
dominated with only ~4 questions each from gpqa/math/usaco/livecodebench** (~11% hard reasoning), and
the LLM-rubric gate was deferred. The literature (2505.02390, **our exact GGUF+Unsloth toolchain on a
DeepSeek-class MoE**) says 2-bit leaves **knowledge ~99% intact while halving reasoning** (uniform Q2:
V3 AIME 38→15) — *but dynamic UD holds*. So the IQ2 architect is **not reasoning-certified**, and the
answer is genuinely unknown. This bench measures it at full power.

## Hypotheses
- **H1 (primary, open):** IQ2 preserves the 122B's *reasoning* (A1 ≈ A2 on AIME/GPQA, not just on
  knowledge). Dynamic-UD + a large model *may* hold, contra the small-model quant literature — or not.
- **H2 (challenger):** dense-27B-Q8's max active width out-reasons the 122B on *hard* tasks (near-parity
  in the literature — genuinely open on our workload).
- **H3 (baseline/control):** 35B-A3B (3B active) trails both → confirms frontdoor ≠ architect.

## Arms

| Arm | Model / quant | Device | GGUF (on disk ✅) | Isolates |
|---|---|---|---|---|
| **A1** | Qwen3.5-122B-A10B **UD-IQ2_M** | MI210 | `…/Qwen3.5-122B-A10B-MTP-GGUF/UD-IQ2_M/…UD-IQ2_M.gguf` | vs A2 → **IQ2 reasoning penalty** (H1) |
| **A2** | Qwen3.5-122B-A10B **UD-Q4_K_M** (incumbent) | CPU | `…122B-A10B-UD-Q4_K_M-00001-of-00003.gguf` | quant-control + vs A3 → arch/depth |
| **A3** | Qwen3.6-27B **dense** Q8 | MI210 | `Qwen_Qwen3.6-27B-Q8_0.gguf` | vs A2 → active-width/depth (H2) |
| **A4** | Qwen3.6-35B-A3B Q8 | MI210/CPU | `Qwen_Qwen3.6-35B-A3B-Q8_0.gguf` | shallow-reasoner baseline (H3) |
| **A5** *(conditional)* | 122B-A10B **dynamic 3-bit** (Q3_K_M / DQ3-style) | MI210 | *build if triggered* | **graceful-degradation fallback** — run ONLY if A1 shows IQ2 tanks reasoning but Q4 won't fit the GPU (2505.02390: DQ3 ≈ Q4) |

Model roots: `/mnt/raid0/llm/models/`. (27B/35B also have `-MTP-` and EAGLE3 variants — use the plain
Q8 for the quality bench unless throughput is being measured, then use the production MTP variant.)

## Evals — objective-scored ONLY (no model-as-judge; the reviewer work proved that's near-random)
- **Phase 1 (decisive on reasoning depth):**
  - **AIME'25** (objective numeric answers) — *new adapter needed* (see task list).
  - **GPQA-Diamond** (objective MC) — **reuse** the registered `gpqa` adapter in `v7_quality_gate_runner.py`.
  - **MMLU-Pro knowledge control** — **reuse** the `mmlu_pro` adapter. *The control is the point:* it
    should show IQ2 ≈ Q4 on knowledge **while** AIME/GPQA reveal any reasoning gap — the asymmetry the
    Δ0.0pp pool was too knowledge-heavy to expose.
- **Phase 2 (tool-using multi-step planning) — DESIGN TBD (operator to confirm; deferred "other point"):**
  recommended default = **SWE-bench-Verified in agentic/tool-using mode**, scored by its **FAIL_TO_PASS
  test oracle** (objective pass/fail — "does it plan+execute with tools" without a judge).
  Dataset on disk: `/mnt/raid0/llm/datasets/swe-bench-verified/`. Alternative (bespoke tasks mined from
  real architect orchestration logs) only if an objective success criterion exists. **Phase 1 alone is
  decisive on the reasoning-depth question**; Phase 2 is the tool-use validation layer.

## Protocol (MEASUREMENT.md)
- **Seed-pinned, production sampling** (temp+seed42 per `feedback_production_sampling_seed_not_temp0` —
  these are sampling-sensitive reasoning suites). No-think vs think per suite convention; `enable_thinking`
  via `/v1/chat/completions` for the Qwen3.x arms (`feedback_enable_thinking_requires_chat_completions_path`).
- **Quality (accuracy) is the PRIMARY output and is device-independent** → decision-grade via the
  eval-tower scorer. **Throughput is secondary**; GPU-row t/s stays **observation-grade until `P-GPU-1`
  certifies on `production-consolidated-v7`** (post-promotion). Era-stamp every result.
- **Same questions across arms** (paired, like the AXA-1 parity) so per-arm deltas are McNemar-testable.

## Decision tree (exit criteria)
1. **A1 ≈ A2 on AIME/GPQA** → 122B-A10B stays architect, **GPU-resident at IQ2** (AXA-1 win reasoning-certified).
2. **A1 ≪ A2, A2 strong** → IQ2 out; run **A5** — DQ3 ≈ Q4 & GPU-fits → 122B-DQ3 GPU architect; else architect = **Q4-122B on CPU**, GPU slot → Qwable/vision/drafter.
3. **A3 out-reasons the 122B arms on hard tasks + GPU-cheap** → reconsider **27B-dense as GPU architect** (weigh lost knowledge headroom vs tool access).
4. **A4 trails** (expected) → 35B-A3B not an architect; frontdoor unchanged.

> **Deployment-robustness input (operator, 2026-07-20) — the choice isn't purely the quality number.**
> A **GPU-only** architect (27B-dense, ~4.4 t/s on CPU → no viable self-home) carries a real operating
> cost the dual-resident 122B does not: it has **no self-fallback** (needs a *substitute* architect —
> 122B-Q4 / 35B — for drains/GPU-failure) and is effectively **pinned**, monopolizing the single GPU
> slot. So a **dual-resident 122B is cheaper to operate at equal quality.** If branch 3 fires (A3 wins
> on reasoning), weigh this cost before deploying — **assess after the bench**, not before. See the
> "GPU accelerates, CPU guarantees" fallback design in [heterogeneous-slot-fabric-residency.md](heterogeneous-slot-fabric-residency.md).

## Gating (sequenced — do NOT start inference until ALL clear)
1. **[ ] v7 promoted to production** (`production-consolidated-v7`) → GPU arms become `P-GPU-1`-eligible. Tracked in [`v7-promotion.md`](v7-promotion.md).
2. **[ ] `inference-batch-loop.md` outstanding tests complete** — the parallel agent runs that backlog first, on the current orchestration stack. See [`inference-batch-loop.md`](inference-batch-loop.md).
3. **[ ] Operator quiet-window inference approval** (`feedback_no_concurrent_inference`) — GPU arms **one-at-a-time** (single MI210), CPU arm (A2) may run concurrently in a detected quiet window (`inference_load_check.py`).

## Prioritized task list
### Prep (no inference — can proceed now)
- [x] Handoff spec authored ✅ 2026-07-20
- [x] Evidence/decision-tree note authored (`docs/reference/architect-model-selection-2026-07-20.md`) ✅ 2026-07-20
- [x] All 4 base-arm GGUFs confirmed on disk ✅ 2026-07-20
- [ ] **Build the AIME'25 adapter** and register it in `ADAPTER_SUITES` (`epyc-inference-research/scripts/benchmark/v7_quality_gate_runner.py`); fixture-test on 1 item. Mirror the existing `gpqa`/`mmlu_pro` adapters.
- [ ] Confirm GPQA-Diamond + MMLU-Pro adapters run against the arm servers (dry-run, no full sweep).
- [ ] (Phase 2, if approved) build/validate the SWE-bench-Verified agentic scorer → FAIL_TO_PASS pass/fail.

### Gated inference (after all three gates)
- [ ] **Phase 1** — A1–A4 × {AIME'25, GPQA-Diamond, MMLU-Pro control}, paired, seed-pinned, MEASUREMENT-stamped.
- [ ] Resolve the decision tree from Phase 1; **(conditional) build + run A5** if branch 2 fires.
- [ ] **Phase 2** (if run) — tool-using planning on the surviving 1–2 arms.
- [ ] **Record the architect decision** (checkbox-flip here) → route to AXA-1 (`mi210-big-model-and-acceleration-roadmap.md`) + the model registry.

## Dependency graph
`Prep (AIME adapter)` ∥ `Gate1 v7-promotion` → `Gate2 inference-batch-loop` → `Gate3 operator quiet window`
→ `Phase 1 (A1–A4)` → {decision | conditional A5} → `Phase 2` → `record decision`.
Prep is independent of the gates; the inference is not.

## Cross-cutting concerns
- **This is the reasoning re-gate that AXA-1 deferred** (LLM-rubric gate). A pass here *upgrades* AXA-1's
  IQ2 residency from knowledge-parity to reasoning-certified; a fail *changes the GPU-slot plan*.
- **No stack/production change** is made by this bench — it is measurement only. The architect deployment
  change (if any) is a *separate* operator-gated action informed by the result.
- **Instrument discipline:** pre-`P-GPU-1`-cert GPU numbers are OBSERVATIONS. The *quality* verdict
  (accuracy, device-independent) is decision-grade; the *throughput* rows are not until post-promotion.

## Reporting instructions
Per arm×suite: write the paired result (n, pass count, Δ vs A2, McNemar p) with a MEASUREMENT stamp.
At Phase 1 completion: flip the Phase-1 checkbox, record which decision-tree branch fired, and update
this Status line. On a final architect decision: flip the record checkbox here, append the verdict to
AXA-1, and open a registry-change note (do NOT edit the live registry — that's operator-gated).

## Key file locations
- Eval runner (reuse + extend): `epyc-inference-research/scripts/benchmark/v7_quality_gate_runner.py` (`gpqa`,`mmlu_pro` adapters; add `aime`).
- Arm GGUFs: `/mnt/raid0/llm/models/` (paths in the Arms table).
- Phase-2 dataset: `/mnt/raid0/llm/datasets/swe-bench-verified/` (FAIL_TO_PASS oracle).
- Evidence: `docs/reference/architect-model-selection-2026-07-20.md`.
- Related handoffs: [`mi210-big-model-and-acceleration-roadmap.md`](mi210-big-model-and-acceleration-roadmap.md) (AXA-1),
  [`reviewer-model-ablations.md`](reviewer-model-ablations.md) (H5, model-role selection sibling),
  [`v7-promotion.md`](v7-promotion.md) (gate 1), [`inference-batch-loop.md`](inference-batch-loop.md) (gate 2).

## Intake (research provenance — persisted 2026-07-20)
6 papers deep-dived read-only; see `research/intake_index.yaml`: net-new `2508.18672`, `2505.11574`,
`2505.02390` (highest-priority — exact toolchain), `2604.07035`; promoted-from-reference `2504.04823`;
already-integrated `2505.09388` (intake-074).
