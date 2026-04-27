# MoE-Spec — CPU Speculative-Decoding Verification with Budgeted Expert Selection

**Status**: STUB — **LIVE ALGORITHMIC LEVER, NOT EXHAUSTED, NOT CLOSED**. Phase 0 falsification probe NOT yet run as of 2026-04-27 evening. Re-flagged 2026-04-27 after peer-review pass #2 noted that "all software paths exhausted" framing in upstream indices was incompatible with this stub's existence. Created 2026-04-27 evening as Phase 4 of closure-inflation remediation plan; previously a research note buried in `cpu-shape-specialized-gemv-decode.md`.
**Priority**: MEDIUM (algorithmic; competes with future hardware-acceleration work for engineer-time, NOT with closed CPU kernel/runtime tracks)
**Categories**: moe_optimization, speculative_decoding, inference_serving, hardware_optimization
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md), [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md)
**Related**:
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) — research note that surfaced this technique (Session 2026-04-27)
- [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) (CPU15) — interaction analysis pending: MoE-Spec changes the verification step's expert dispatch pattern, which CPU15 EP is also modifying
- [`research/intake_index.yaml`](../../research/intake_index.yaml) — intake entry to be added (forthcoming)

## Background

MoE-Spec ([arxiv:2602.16052](https://arxiv.org/html/2602.16052v1), Feb 2026) is a training-free expert-budgeting technique that integrates with speculative decoding's verification step. The draft model proposes K candidate tokens; instead of running all experts during verification, MoE-Spec selects a budgeted subset of top-scoring experts per token for the verification pass. Reports **10-30% throughput improvement over EAGLE-3** at comparable quality on GPU benchmarks.

Adjacent prior art (also surfaced in the 2026-04-27 research check):
- **OD-MoE shadow networks** — ~84-91% expert-prediction accuracy with single-layer lookahead; >99% with separate shadow networks. More complex (requires training a small auxiliary model).
- **MoE Pathfinder** ([arxiv:2512.18425](https://arxiv.org/abs/2512.18425), Dec 2025) — Trajectory-driven expert pruning; treats expert selection as global path-planning across the layer graph.
- **REAP (Router-weighted Expert Activation Pruning)** ([arxiv:2510.13999](https://arxiv.org/abs/2510.13999)) — ALREADY DEPLOYED as the technique behind our REAP-246B model (Cerebras-pruned 480B → 246B). MoE-Spec is the inference-time analog.
- **Dynamic Skipping** — per-token, layer-calibrated `β` threshold for expert ratio comparison.

## Why this exists

Most published MoE-Spec / OD-MoE / Pathfinder work is GPU-focused. CPU adaptation requires a llama-server scheduler change at the spec-dec verification step, NOT a kernel change. We already run spec-dec on Coder-30B and REAP-246B in production. If MoE-Spec ports cleanly, the expected gain is **5-15% on Coder-30B and REAP-246B decode** per the original research-check estimate.

This is independent of CPU2 (SIMD kernels), CPU15 (EP sharding), CPU22 (work-stealing). It operates at a different layer of the stack (scheduler vs kernel vs sharding).

## Conflict / overlap analysis

| Track | Interaction with MoE-Spec |
|---|---|
| CPU2 SIMD kernels (Q8_0/Q6_K/Q4_K AVX-512BW) | Neutral — MoE-Spec changes which experts run, kernels are the same |
| CPU15 EP inter-process | CONFLICT POTENTIAL — both modify the verification-step expert dispatch path; need to either pick one or design integration carefully |
| CPU22 work-stealing | Neutral — work-stealing operates at the load-balancing layer below MoE-Spec's expert-selection layer |
| Existing spec-dec stack (`--draft-max`, `--p-split`, tree decoding) | Direct interaction — MoE-Spec adds a budgeted-expert dimension on top of K-token spec-dec |

## Phase 0 — falsification probe spec (detailed)

**Goal**: cheaply confirm or refute that MoE-Spec's expert budgeting at the verification step delivers measurable throughput on our CPU spec-dec path before committing to a full integration.

### Step 0.1 — Reference implementation review (1-2 hours)

- Read the upstream MoE-Spec arXiv:2602.16052 paper end-to-end. Pay special attention to: section 3 (algorithm details), section 4 (experimental setup — what was the baseline they compared against?), section 5 (results — distinguish absolute throughput gains from relative-vs-EAGLE-3 framing).
- Search GitHub for the reference code release. As of 2026-04-27 the paper says "code coming soon". If unreleased, work from the algorithmic description.
- Capture in a design note: (a) the exact expert-selection function (likely a top-K over routing scores at verification step), (b) the budget parameter B (= number of experts kept; default in paper TBD), (c) the integration point (where in the spec-dec verifier loop the budgeting fires).

### Step 0.2 — Trace our existing spec-dec verifier path (1-2 hours)

- Read `tools/server/server.cpp` spec-dec path: where the draft tokens are verified against the target model, where the target model's MoE expert dispatch is invoked.
- Read `ggml/src/ggml-cpu/ggml-cpu.c` `ggml_compute_forward_mul_mat_id` (the MoE expert dispatch op). Identify where the routing scores are computed and where the expert subset is selected.
- Output: a numbered list of insertion points where MoE-Spec's budgeted-expert selection logic could attach.

### Step 0.3 — Compatibility check vs CPU15 EP and CPU22 (1-2 hours)

- CPU15 EP master/worker drone path: workers receive the full src1+ids broadcast and run `ggml_compute_forward_mul_mat_id` independently. If MoE-Spec budgets at the routing-score selection step, each worker would need to apply the same budget — straightforward but requires the budget signal to flow through the IPC ring.
- CPU22 work-stealing (Phase 3 of remediation): operates at the expert-tile load-balancing layer below MoE-Spec's expert-selection layer. Should be orthogonal — MoE-Spec selects WHICH experts run, work-stealing balances HOW the selected experts' tiles are distributed across threads. No conflict; potentially compounding.
- Existing spec-dec stack (`--draft-max N`, `--p-split` for tree, etc.): MoE-Spec adds a budgeted-expert dimension on top. Tree spec-dec branches won't compound naively — each branch's verification step independently budgets. Linear spec-dec is simpler — single verification path, single budget.

### Step 0.4 — Phase 1 prototype scope estimate (1-2 hours)

Output an explicit estimate:
- LOC estimate (target: <500 lines for the budgeting logic + env-flag wiring)
- Files to modify (likely: `ggml/src/ggml-cpu/ggml-cpu.c` mul_mat_id, a new `ggml_moe_spec.{h,cpp}` for the budget logic, optional `tools/server/server.cpp` for spec-dec wiring if budget needs to flow through HTTP request)
- Risk classification (LOW: pure scheduler change, no kernel rewrite. MEDIUM: needs to coordinate with CPU15 EP if production frontdoor uses both. HIGH: needs custom kernel — flagged for handoff escalation).
- Falsification budget: total 4-8 hours for Steps 0.1-0.4.

### Phase 0 gate

- If integration surface looks LOW risk + ≤500 LOC + ≤1-2 days prototype → queue Phase 1 immediately.
- If MEDIUM risk + 1-2 weeks prototype → escalate priority decision (compete with CPU22 work-stealing for engineer time).
- If HIGH risk OR >2 weeks prototype → defer; prefer CPU22 work-stealing first.

## Phase 1 — prototype scope (forthcoming after Phase 0)

Likely env-gated `GGML_MOE_SPEC_BUDGET=N` (default 0 = off; 0 < N < expert_count = budget the verification-step expert selection to top-N by routing score) controlling the budgeted-expert count at verification.

Implementation sketch (subject to Phase 0 refinement):
1. Add an `extra` field to ggml_tensor for `mul_mat_id` ops carrying the budget B. (Or use a thread-local global like `ggml_moe_spec_budget` set per request.)
2. In `ggml_compute_forward_mul_mat_id`, when B > 0 and B < n_experts, after the routing scores are computed but BEFORE the selected-expert loop runs, sort the routing scores and pick top-B. Replace the current "use all selected experts" with "use only the top-B by score".
3. Quality validation: ensure the spec-dec verifier still rejects mismatched draft tokens correctly. Since MoE-Spec changes the target's expert subset at verification, the target's logits will differ from a no-budget baseline — but spec-dec already tolerates this kind of variation (it accepts/rejects based on the target's distribution, whatever that is).
4. Throughput measurement: per-token decode rate at `--draft-max 16 --draft-min 4` with B sweep over {0 (off), n_experts/4, n_experts/2, n_experts*3/4}.

## Measurement gates (Phase 1 binding)

1. Throughput: ≥5% on at least one of Coder-30B or REAP-246B decode (relaxed from 10-15% literature claim because GPU→CPU port typically halves expected gains).
2. Quality: PPL bit-exact OR ≤1e-3 drift vs no-MoE-Spec baseline. Spec-dec already produces bit-exact output by construction (verifier rejects mismatched draft tokens), so MoE-Spec quality should be governed by the same property.
3. Stability: 5-min sustained run, no crash/deadlock.
4. Compatibility: works alongside existing tree/linear spec-dec config without conflict.

## Risk areas

- MoE-Spec's expert-budget selection might trigger different MoE expert activation patterns, potentially reducing the spec-dec acceptance rate. Need to measure acceptance-rate impact alongside throughput.
- CPU15 EP partial overlap: if both are enabled simultaneously, the verification-step expert dispatch is double-modified. Phase 0 must clarify the integration story.
- Reference implementation may be GPU-specific in non-trivial ways (CUDA kernels for the scoring step). Falsification probe must check this.

## Integration effort estimate

- Phase 0 falsification: 4-8 hours (read paper, identify port surface, design note)
- Phase 1 prototype (if Phase 0 says feasible): 1-2 weeks
- Validation: 2-3 days

Multi-week effort overall. Prioritize against CPU22 work-stealing during Phase 4 of the remediation plan.

## Sources

- [MoE-Spec arXiv 2602.16052](https://arxiv.org/html/2602.16052v1) — primary technique
- [MoE Pathfinder arXiv 2512.18425](https://arxiv.org/abs/2512.18425) — trajectory-driven pruning (alternative)
- [REAP arXiv 2510.13999](https://arxiv.org/abs/2510.13999) — already deployed (REAP-246B)
- [Awesome MoE Inference](https://github.com/MoE-Inf/awesome-moe-inference/) — collection
- [Discovering Important Experts NeurIPS 2025](https://neurips.cc/virtual/2025/poster/119676)
- Surfaced in: `cpu-shape-specialized-gemv-decode.md` (Session 2026-04-27 research check)
