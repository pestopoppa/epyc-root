# MoE — Dynamic Expert Selection (post-MoE-Spec follow-up)

**Status**: STUB created 2026-04-28 evening. **Phase 0 (research check + entropy probe)** queued. Sibling to [`moe-spec-cpu-spec-dec-integration.md`](moe-spec-cpu-spec-dec-integration.md) which delivered Phase 1 WIN on the per-batch top-B union-shrinkage mechanism.
**Priority**: MEDIUM — explores per-token dynamic K reduction (orthogonal axis to MoE-Spec's per-batch mask). Could compound or supplant.
**Categories**: moe_optimization, hardware_optimization, inference_serving
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`inference-acceleration-index.md`](inference-acceleration-index.md), [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md)
**Related**:
- [`moe-spec-cpu-spec-dec-integration.md`](moe-spec-cpu-spec-dec-integration.md) — per-batch top-B mask (orthogonal layer; landed 2026-04-28 +7-15% on verification batch shape)
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) — CPU2 SIMD kernels (compute layer; orthogonal)
- [`large-moe-expert-parallelism.md`](large-moe-expert-parallelism.md) — CPU15 EP (compute distribution layer; orthogonal)

## Why this exists

MoE-Spec (arXiv:2602.16052) Phase 1 measured a +7-15% verification-batch throughput gain via per-batch top-B union shrinkage. User raised a valid follow-up: **could a more sophisticated per-token dynamic mechanism — vary K per token instead of fixing K=8 — deliver additional gain on top of MoE-Spec's batch-level mask?**

The two axes are orthogonal:
- **MoE-Spec**: per-batch top-B shortlist masks the EXPERT axis (which experts can be picked)
- **Dynamic K**: per-token vary K masks the K axis (how many experts each token picks)

Both reduce DRAM expert-weight read pressure (the dominant cost on CPU per CPU24 attribution). MoE-Spec already exploits the batch-level union shrinkage; dynamic K would exploit per-token routing-distribution shape.

Production runs Coder-30B and REAP-246B with default top-K=8 (no static expert reduction in registry). MoE-Spec already applies on top. Dynamic K is a research question worth probing before implementation.

## Candidate mechanisms (4 surfaced from MoE-Spec Phase 0 research check + user-suggested entropy gate)

### 1. Dynamic Skipping (per-token β threshold)

Drop experts where `prob[i, t] < β × max(prob[:, t])` per token. Continuous knob (β ∈ [0, 1]); β layer-calibrated possibly.

**Testability**: MEDIUM. Adding the routing-side mask is ~30 LOC, but `argsort_top_k` always returns K=8 indices regardless of mask, and `mul_mat_id` always processes them. To get actual compute reduction need either (a) custom variable-K argsort, or (b) `mul_mat_id` modification to skip near-zero-weight rows. ~100 LOC total. 1-2 days.

**Risk class**: MEDIUM. Custom op or `mul_mat_id` patch is invasive.

**Phase 0 gate**: empirically measure expected K-distribution under various β values on a sample workload; if median K < 6 across tokens, the mechanism has headroom.

### 2. OD-MoE — Single-layer lookahead (NOT shadow-network variant)

Use previous layer's hidden state to predict NEXT layer's expert routing. Avoids running the routing softmax at the target layer. 84-91% accuracy in published paper.

**Testability**: EASY. ~50 LOC. Zero training. Cache previous-layer routing scores; project them onto next-layer expert space via a learned linear (or just identity if architectures align).

**Risk class**: LOW.

**Phase 0 gate**: confirm prediction-accuracy claim holds on Coder-30B/REAP-246B by logging actual vs predicted routing decisions on a sample workload. ≥80% match → worth implementing. <80% → close.

**NOT testing**: the full shadow-network variant (>99% accuracy) requires GPU training of an aux model. Out of scope for current CPU-only work.

### 3. MoE Pathfinder (arXiv:2512.18425) — DEPRIORITIZED

Trajectory-driven pruning; treats expert selection as global path-planning across the layer graph. Paper uses offline path-search.

**Testability for runtime online use**: NOT VIABLE. Path-search runtime cost likely matches or exceeds the MoE compute it's pruning. Single-user CPU regime makes the offline-precompute-with-cluster-cache adaptation a research-grade project.

**Verdict**: deprioritized as published. Reopen ONLY if a cheap online path-search algorithm emerges.

### 4. Entropy-gated K — quick diagnostic probe FIRST

When routing distribution is low-entropy (peaked, few experts dominate), use full K. When high-entropy (flat, no expert stands out), use lower K (since marginal experts contribute proportionally less).

**Testability of the diagnostic probe**: EASY. ~30 LOC + analysis script. Add temporary debug logging in `build_moe_ffn` after softmax to dump per-layer-per-token routing entropy on a sample workload. Compute histogram across ~1K tokens. **No model code change needed for the probe** — just a logging probe.

**Phase 0 gate**: bimodal entropy distribution → real knob worth implementing (~150 LOC). Unimodal → skip implementation.

**Implementation effort if probe positive**: medium-complexity (similar to Dynamic Skipping — needs variable-K mechanism in mul_mat_id or custom op).

## Phase 0 — research/diagnostic queue (pre-implementation)

| Step | Mechanism | Action | Effort |
|---|---|---|---|
| 0.1 | Entropy-gated K | Add debug entropy logger in `build_moe_ffn`, run on Coder-30B + REAP-246B sample workloads (256-1024 tokens), histogram analysis | 1-2 hours |
| 0.2 | OD-MoE lookahead | Log layer-N-1 routing scores + layer-N routing decisions, measure prediction accuracy | 1-2 hours |
| 0.3 | Dynamic Skipping | Compute per-token effective-K distribution at various β values from the entropy probe data | 30 min (analysis only) |
| 0.4 | MoE Pathfinder | NO PROBE — deprioritized. Park research note. | 0 |

After Phase 0, decide which (if any) of mechanisms 1, 2, 4 to implement based on probe data.

## Phase 1 — prototype (forthcoming after Phase 0 probes)

Decision tree:
- Entropy histogram bimodal AND OD-MoE accuracy ≥80% → implement OD-MoE lookahead first (lower risk; routing-saving but no expert-saving)
- Entropy histogram bimodal AND OD-MoE accuracy <80% → implement Entropy-gated K (full implementation, ~150 LOC)
- Entropy histogram unimodal AND OD-MoE accuracy ≥80% → still implement OD-MoE (saves routing compute; small but real)
- Both negative → close track

Compatibility with MoE-Spec: orthogonal layer (per-token vs per-batch). Implementations should be compatible without conflict — both modify routing layer, neither modifies `mul_mat_id` (in their basic form).

Compatibility with CPU15 EP: same as MoE-Spec — modifications happen at the master before broadcast; workers see modified ids regardless of source.

## Measurement gates (Phase 1, if pursued)

1. Throughput: ≥2% on at least one of Coder-30B Q4_K_M or REAP-246B Q4_K_M (matches MoE-Spec gate)
2. Quality: PPL bit-exact within spec-dec verifier rejection envelope; same structural property as MoE-Spec
3. Stability: 5-min sustained run, no crash
4. Compatibility: works alongside MoE-Spec budget (test compounding)

## Risk areas

- Dynamic K mechanisms typically need `mul_mat_id` modification → invasive vs MoE-Spec which only touched routing.
- Per-token mechanisms add per-token overhead that MAY exceed savings on small models — measure carefully.
- OD-MoE lookahead saves routing compute (cheap layer) not expert compute (expensive layer). Real-world gain may be <1%.

## Sources

- [MoE-Spec arXiv 2602.16052](https://arxiv.org/abs/2602.16052) — sibling mechanism; per-batch
- [OD-MoE](TBD — surfaced in MoE-Spec Phase 0 research check) — lookahead expert prediction
- [MoE Pathfinder arXiv 2512.18425](https://arxiv.org/abs/2512.18425) — global trajectory pruning (DEPRIORITIZED)
- Entropy-gated K — user-suggested, no published paper as of 2026-04-28
- [Dynamic Skipping] — generic technique; surfaced in MoE-Spec Phase 0 review

## Phase 0 deliverable

`data/cpu_optimization/2026-04-28-moe-dynamic-expert-selection-phase-0/` (forthcoming):
- `entropy_histogram.csv` — per-layer per-token routing entropy on sample workload
- `od_moe_accuracy.csv` — layer-N-1 → layer-N routing prediction accuracy
- `decision.md` — which (if any) of 4 candidates progresses to Phase 1 prototype
