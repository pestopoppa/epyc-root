# MoE-Spec — CPU Speculative-Decoding Verification with Budgeted Expert Selection

**Status**: STUB (created 2026-04-27 evening as Phase 4 of closure-inflation remediation plan; previously a research note buried in `cpu-shape-specialized-gemv-decode.md`)
**Priority**: MEDIUM
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

## Phase 0 — falsification probe (forthcoming, Phase 4 of remediation)

**Goal**: cheaply confirm or refute that MoE-Spec's expert budgeting at the verification step delivers measurable throughput on our CPU spec-dec path before committing to a full integration.

Proposed scope:
1. Read the upstream MoE-Spec arxiv:2602.16052 reference implementation (paper code or GitHub release).
2. Identify the budgeted-expert-selection logic at the verification step. Determine whether it can be ported as a llama-server scheduler change OR requires kernel-level changes (the original research-check claimed "scheduler change, not kernel").
3. Compatibility check with our existing spec-dec stack: Coder-30B (Qwen2.5-Coder-0.5B drafter) and REAP-246B (drafter TBD). Tree vs linear decoding interactions.
4. Falsification budget: 4-8 hours to read paper, identify port surface, and draft a Phase 1 prototype scope.

Phase 0 deliverables:
- Design note: where in our llama-server / spec-dec verifier the budgeted-expert selection inserts.
- Conflict analysis with CPU15 EP (master/worker drone path).
- Phase 1 prototype scope estimate.

Phase 0 gate: if integration surface looks larger than 1-2 weeks of work, escalate priority decision (compete with CPU22 work-stealing for engineer time). If 1-2 days, queue Phase 1.

## Phase 1 — prototype (TBD)

Forthcoming after Phase 0. Likely env-gated `GGML_MOE_SPEC_BUDGET=N` (default off) controlling the budgeted-expert count at verification.

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
