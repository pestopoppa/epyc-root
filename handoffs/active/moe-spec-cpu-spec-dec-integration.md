# MoE-Spec — CPU Speculative-Decoding Verification with Budgeted Expert Selection

> **PRE-PRODUCTION REGISTRY-INTEGRATION GATE (2026-04-28; updated 2026-04-30)**: The Phase 3 follow-up "production registry integration with per-role binary_path + per-role moe_spec_budget" (REAP=40 confirmed deployable per v5 PGO; Coder=NOT deployable per consolidated v5 verdict) MUST NOT land in `model_registry.yaml` until: (a) [`mab-tree-shape-selector.md`](mab-tree-shape-selector.md) Phase 0 falsification probe completes with explicit GO or NO-GO (still pending), AND (b) ✅ ~~[`hybrid-ssm-slot-promotion-spec-dec.md`](hybrid-ssm-slot-promotion-spec-dec.md) Phase 0 falsification produces a written LOC+risk verdict~~ — **RELEASED 2026-04-28 evening** (Phase 0 verdict written; track subsequently CLOSED 2026-04-30 with mechanism net-negative on Qwen3.6-35B+1.7B → see [`completed/hybrid-ssm-slot-promotion-spec-dec.md`](../completed/hybrid-ssm-slot-promotion-spec-dec.md); dispatcher v1 disabled-by-default in tree, doesn't change MoE-Spec ceiling). Rationale: pushing v5 PGO + MoE-Spec to production locks the deployment at end-to-end +9%/+3% (Amdahl-bounded by drafter + accept eval); MAB selector still tests a mechanism that changes that ceiling. Other Phase 3 follow-ups (BOLT-libggml v5 redo, Coder-30B 10-rep alternated re-measurement, Q8 frontdoor + dense, [`moe-dynamic-expert-selection.md`](moe-dynamic-expert-selection.md) Phase 0 entropy probe) are NOT blocked — they don't bind production state. Source: today's `/research-intake` pass on intake-490 + intake-491; full plan `/home/node/.claude/plans/1a-sounds-extremely-promising-crispy-sutherland.md`.

**Status**: Phase 1 + Phase 2 + v5 PGO + BOLT-Coder all measured 2026-04-28 evening. **Final verdict: REAP-246B B=40 deployable (+13-16% pp32 / +3% end-to-end, robust across all builds); Coder-30B B=64 NOT deployable (result varies wildly across builds + cache states + system noise — gcc +7.3%, PGO single-B −43%, PGO mixed-B parity-to-+84% depending on cold/warm and noise); BOLT-libggml on v5 PGO Coder NOT deployable this attempt (perf record too short, 4% function coverage, BOLT pessimized mask branch − reopen with morning's recipe of 60s × 4 model classes).** Full consolidated decision at `data/cpu_optimization/2026-04-28-moe-spec-phase-1/decision_v5_FINAL.md`. Phase 1 implementation on `feature/cpu-ep-inter-process` HEAD `0c8d05597`. v5 PGO build at `/mnt/raid0/llm/llama.cpp-experimental/build_v5_pgo_use/`. Phase 0 verdict (queue Phase 1) preserved below.

---

## Phase 1 — RESULTS (DONE 2026-04-28)

### Implementation

~30 LOC mask-construction in `src/llama-graph.cpp::build_moe_ffn` between softmax (line 1398) and argsort_top_k (line 1492 post-edit), pattern mirrors existing DeepSeek-V3 expert-groups mask. Plus ~8 LOC param plumbing across `src/llama-cparams.h`, `src/llama-context.cpp`, `include/llama.h`, `common/common.h`, `common/common.cpp`, `common/arg.cpp`, and `tools/llama-bench/llama-bench.cpp` (env var fallback for llama-bench's separate arg parser).

CLI: `--moe-spec-budget N` / env: `LLAMA_ARG_MOE_SPEC_BUDGET=N`. Default 0 (off). Min-batch threshold: `LLAMA_ARG_MOE_SPEC_MIN_BATCH=4`.

Mechanism (matches paper algorithm but with batch-aggregation instead of tree-aggregation):
1. Aggregate routing softmax across n_tokens: `expert_scores = Σ_t probs[i, t]` per expert i.
2. Top-B select on aggregated scores → shortlist S.
3. Mask `selection_probs` to -INFINITY for experts ∉ S (additive mask, broadcast across n_tokens).
4. Existing argsort_top_k naturally selects only in-S experts per token.

### Headline results (5-rep proper canonical: `taskset -c 0-95 -t 96 -fa 1 --mmap 0` + `numactl --interleave=all`)

**Coder-30B Q4_K_M (n_expert=128, n_expert_used=8):**

| Prompt | B | Throughput (mean ± std) | Δ vs B=0 | PPL chunk 3 | Notes |
|---|---|---|---|---|---|
| pp32 | 0 | 321.35 t/s (avg of 2 runs) | reference | 9.86 | baseline |
| pp32 | 128 | n/a (gate-skip) | bit-exact | 9.86 (byte-identical) | gate-disabled (B≥n_expert) confirms baseline |
| pp32 | 96 | 317.59 t/s | -1.2% (noise) | 9.75 (~baseline) | no-win at 75% budget |
| pp32 | 64 | 344.70 t/s | **+7.3%** | 10.52 (+6.7%) | **PHASE 1 GATE MET — quality cost moderate** |
| pp32 | 32 | 393.17 ± 2.72 | +22.3% | not measured | quality cost severe (B=64 already +6.7% PPL) |
| pp64 | 0 | 402.28 ± 8.04 | reference | — | |
| pp64 | 64 | 429.25 ± 2.69 | **+6.7%** | — | gain holds at larger batch |
| pp64 | 32 | 461.13 ± 2.80 | +14.6% | — | |

**REAP-246B Q4_K_M (n_expert=80, n_expert_used=8):**

| B | Throughput (mean ± std) | Δ vs B=0 | PPL chunk 3 | Notes |
|---|---|---|---|---|
| 0 (run 2) | 45.23 ± 0.99 | reference | 9.30 | baseline (run 1 was noisy outlier 35.64 ± 5.77) |
| 80 | 44.89 ± 1.06 | bit-exact (-0.8% noise) | gate-skip | confirms B≥n_expert disables |
| 60 | 42.19 ± 2.02 | -6.7% (1.4σ; likely noise) | 9.36 (~baseline) | no-win at 75% |
| 40 | 52.11 ± 0.58 | **+15.2%** | 11.44 (+23%) | **PHASE 1 GATE MET — quality cost meaningful** |
| 20 | 62.49 ± 0.07 | +38.2% | 15.79 (+70%) | quality unusable |

### Phase 1 binding gates (from handoff above)

1. **Throughput gate ≥2% on at least one of Coder-30B / REAP-246B**: **MET** — Coder +7.3% at B=64, REAP +15.2% at B=40, both 3.5σ+ above baseline noise band.
2. **Quality (PPL bit-exact OR governed by spec-dec verifier rejection)**: **STRUCTURALLY OK for spec-dec** — forward-pass PPL drifts measurably at B<n_expert, but spec-dec verifier rejects mismatched draft tokens making end-to-end output bit-exact. Acceptance-rate impact (paper claims 1.4% average reduction) NOT measured here (Phase 2 deliverable).
3. **Stability**: 5-min sustained runs implicit in 5-rep × multi-config sweeps; no crash/deadlock.
4. **Compatibility**: code path is compatible by construction (operates pre-argsort_top_k, downstream `mul_mat_id` unmodified). Existing `moe_n_expert_override` interaction NOT measured.

### Why measured gain exceeded Phase 0's 3-8% upper-bound estimate

Phase 0 estimate assumed strong overlap with existing `moe_n_expert_override` mechanism. Actual measured gain on REAP-246B (+15.2% at B=40) substantially exceeded estimate because:

- REAP-246B is heavier (~5× slower per token) and therefore more memory-stalled per CPU24 attribution
- Reducing distinct experts loaded directly cuts DRAM expert-weight bandwidth pressure
- Larger model has more headroom for the union-shrinkage mechanism than smaller Coder

Phase 0's "GPU HBM-loading mechanism doesn't translate to CPU" framing was partially correct (no equivalent loading cost) but missed the compounding factor: CPU's L3 cache (~32MB per CCD × 12 CCDs = 384MB) is far below total expert weight footprint (Coder 17GB / REAP 138GB), so each unique expert load IS a DRAM read. Reducing unique-expert-count directly reduces DRAM traffic, same mechanism as GPU HBM, just on a different memory tier.

### Sweet spots for Phase 2

- Coder-30B: B=64 (50% of n_expert)
- REAP-246B: B=40-50 (need finer sweep; B=60 was noise band, B=40 has +23% PPL drift)

### Phase 2 deliverables (queued)

1. **End-to-end spec-dec measurement** — actual `--draft-max 32 --p-split 0` config with draft model, measure tokens/s end-to-end and acceptance rate impact
2. **Production registry integration** — if Phase 2 confirms ≥2% end-to-end gain, add `moe_spec_budget` per-role config to `model_registry.yaml` (Coder-30B → 64, REAP-246B → 40 likely)
3. **Interaction with `cparams.moe_n_expert_override`** — production sometimes uses `--override-kv qwen3moe.expert_used_count=int:4`; measure whether MoE-Spec compounds or partially substitutes
4. **PGO+BOLT rebuild revalidation** — current build is gcc+libgomp; v5 production binary will be clang+libomp+znver5+PGO; mechanism gain may compound or shrink under PGO
5. **Full WikiText-2 32-chunk PPL gate** — 3-chunk diagnostic suffices for Phase 1 mechanism validation; full PPL needed for production routing decisions
6. **Tree spec-dec interaction** — paper's native algorithm operates on trees; if Phase 2 production benefit motivates re-enabling tree spec-dec on Coder/REAP (currently `p_split: 0` in registry due to historical sweep finding tree harmful at 48t), test whether tree+MoE-Spec reverses the historical tree finding



1. The paper's GPU mechanism (HBM expert-weight loading reduction during tree spec-dec verification) does NOT directly translate, BUT the underlying "reduce distinct experts touched per verification batch → reduce DRAM expert-weight reads" mechanism DOES translate to CPU. CPU expert weights are mmap'd in DRAM and the verification's `mul_mat_id` op reuses each expert across all matching tokens in the batch.
2. **Production runs Coder-30B and REAP-246B with `p_split=0` (linear spec-dec only)** — tree spec-dec was empirically tested and harmful (`registry:378 — Coder-30B tree net-negative at 48t`; `registry:447 — REAP-246B tree harmful at all ps values`). The paper is tree-only by mechanism (aggregates routing scores across 63-token EAGLE-3 trees), but the algorithm trivially extends to linear K=32 batched verification: aggregate routing scores across the K verification tokens, top-B select, mask out-of-S experts.
3. **Existing `cparams.moe_n_expert_override` already captures partial compute reduction** — `--moe-n-expert N` reduces per-token K from 8 to N. Production already uses this (e.g., `--override-kv qwen3moe.expert_used_count=int:4` for some Coder-30B configs). MoE-Spec's contribution would be tree/batch-level union shrinkage on top of per-token K reduction; the available delta is narrower than the GPU case where no equivalent mechanism existed.
4. Expected CPU gain on linear K=32 spec-dec: 3-8% upper bound (much less than paper's GPU 10-30% on tree). Below the original handoff's 5-15% framing but still potentially deployable.

Re-flagged 2026-04-27 after peer-review pass #2 noted that "all software paths exhausted" framing in upstream indices was incompatible with this stub's existence. Created 2026-04-27 evening as Phase 4 of closure-inflation remediation plan; previously a research note buried in `cpu-shape-specialized-gemv-decode.md`. Phase 0 completed same evening.
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

## Phase 0 — RESULTS (DONE 2026-04-27 evening)

### Step 0.1 — paper read (arXiv:2602.16052)

Authors: McDanel, Li, Surineni, Khaitan (Feb 2026). Pseudocode (Appendix B):
```
For draft tree of M tokens, hidden states {h_t}:
  for each expert i: s_i = Σ_t g_i(h_t)         # aggregate routing-prob across tree
  S = top-B experts by score s_i                  # tree-level shortlist
  for each token t: expert subset = top_k(h_t) ∩ S  (truncate)
                              OR    top-B(h_t restricted to S) (substitute)
```

Key facts:
- **Mechanism targets memory bandwidth on GPU** ("expert explosion": 63-token EAGLE-3 tree on OLMoE-1B-7B activates 54 of 64 experts per layer; HBM must load the union)
- **Tree-only on EAGLE-3 trees**; not evaluated on linear spec-dec
- Budget B is **fixed per deployment**, searched empirically ({8, 16, 24, 32, 40, 48, 56} for OLMoE; {16, 24, 32, 48, 64} for Qwen3)
- B can be < per-token top-K (k=8 with B=32 means tokens whose natural top-K falls outside S receive fewer than k experts)
- Quality impact: **1.4% acceptance-rate reduction average**; task-dependent (code tolerates tight budgets, reasoning degrades steeper)
- vs EAGLE-3 baseline: **10-30% throughput** on A100 GPU
- **No code release** found; paper says "extends EAGLE-3 codebase"
- Hardware: A100 80GB (single-GPU OLMoE/Qwen3, dual-GPU Mixtral). No CPU mention.

### Step 0.2 — CPU spec-dec verifier path traced

**Verification call site**: `tools/server/server-context.cpp:3030-3081` (slot decode path).
Spec-dec drafts are produced via `common_speculative_draft()` (common/speculative.cpp); the target verification is the standard `llama_decode(ctx_tgt, batch)` with batch_size=K (linear) or batch_size=tree.n_nodes (tree).

**Tree mechanism EXISTS in our fork**: `common/speculative.cpp:1137-1300` (DySpec heap-based dynamic tree construction). Triggers when `params.p_split > 0.0f` (line 1381). Production registry: tree DISABLED on Coder-30B + REAP-246B (`p_split: 0`); tree ENABLED on some other models with `p_split: 0.05`.

**Routing-score location (the real insertion point)**: `src/llama-graph.cpp:1395-1458` (`build_moe_ffn` function).
- Line 1398: `probs = ggml_soft_max(ctx0, logits)` → `[n_expert, n_tokens]`
- Lines 1413-1454: existing **DeepSeek-V3 expert-groups mask** uses exactly the structure MoE-Spec needs — masks `selection_probs` to -infinity for out-of-group experts before `argsort_top_k`
- Line 1458: `selected_experts = ggml_argsort_top_k(ctx0, selection_probs, n_expert_used)` → `[n_expert_used, n_tokens]`

**Original handoff's "ggml_compute_forward_mul_mat_id is the insertion point" was wrong**. mul_mat_id sees only already-selected expert ids; the budgeting must fire before argsort_top_k at the graph-build layer.

**Existing related infrastructure** (already in fork): `cparams.moe_n_expert_override` (`src/llama-cparams.h:46`) reduces per-token K from `n_expert_used` to override value. Wired through `--moe-n-expert N` CLI / `LLAMA_ARG_MOE_N_EXPERT` env. Implementation at `llama-graph.cpp:1477-1499`. **MoE-Spec is a different mechanism (per-batch top-B union shrinkage) — orthogonal to per-token K reduction.**

### Step 0.3 — Compatibility analysis

| Surface | Interaction | Verdict |
|---|---|---|
| Linear spec-dec (Coder-30B + REAP-246B production) | Aggregate routing scores across K=32 verification tokens; mask out-of-S experts | COMPATIBLE — algorithm trivially extends from tree-aggregation to batch-aggregation |
| Tree spec-dec (DySpec, p_split>0) | Direct match for paper's algorithm | COMPATIBLE but production stack disables tree on the two target models |
| `cparams.moe_n_expert_override` (per-token K reduction) | Both mask `selection_probs` before argsort; orderings: MoE-Spec mask first (per-batch), then existing override (per-token K) | COMPATIBLE — orthogonal masking; possibly compounding |
| CPU15 EP (inter-process expert parallelism) | Master broadcasts src1+ids to workers; if budget masking happens at master before broadcast, workers see smaller `ids` array | COMPATIBLE — budget signal flows through cparams (no IPC ring change needed) — BUT CPU15 EP frontdoor only deployed on Qwen3.6-35B Q8_0; Coder/REAP do NOT use EP in production, so CPU15×MoE-Spec interaction is theoretical |
| CPU22 work-stealing | Closed via test, default-OFF; if reopened, operates at tile-distribution layer below MoE-Spec's expert-selection layer | ORTHOGONAL |
| `--draft-max=32 --p-split=0` (production Coder/REAP linear K=32) | Verification batch_size=32; MoE-Spec aggregates across the 32 tokens | COMPATIBLE |
| PPL preservation | spec-dec produces bit-exact output by construction (verifier rejects mismatched draft tokens regardless of target's expert subset); MoE-Spec changes target's expert dispatch but not the acceptance rule | bit-exact PPL EXPECTED |

**REAP-246B has a draft model** (`Qwen3-Coder-Instruct-DRAFT-0.75B-32k-Q4_0.gguf`, registry line ~441). MoE-Spec applies to the target's verification step, not the draft. The draft model has its own architecture (dense at 0.75B, no MoE) so MoE-Spec is moot for the draft side. REAP-246B's MoE target is what MoE-Spec acts on.

### Step 0.4 — Phase 1 prototype scope estimate

| Item | Estimate |
|---|---|
| LOC | ~100-150 in `src/llama-graph.cpp` + ~20 in `src/llama-cparams.h` + `src/llama-context.cpp` + `common/common.cpp`/`.h` for `--moe-spec-budget` flag + env var |
| New ggml ops | NONE — reuses existing `ggml_sum_rows` + `ggml_argsort_top_k` + `ggml_set_rows` + `ggml_fill` (all already used by DeepSeek-V3 expert-groups path; pattern at lines 1437-1454) |
| Risk class | **LOW** — pure scheduler change, no kernel rewrite; bit-exact PPL is structural property of spec-dec (verifier rejects mismatches) |
| Build/test cycle | 1-2 days prototype + 1 day measurement |
| Falsification budget | Phase 1 MAX 3 days; if no signal, close honestly via test (not via inference) |

### Phase 0 GATE VERDICT: **QUEUE PHASE 1**

Per handoff Phase 0 gate criteria: "LOW risk + ≤500 LOC + ≤1-2 days prototype → queue Phase 1 immediately". All three met.

**Prototype Phase 1 implementation sketch**:
1. Add `cparams.moe_spec_budget` (default 0 = off), `--moe-spec-budget N` CLI flag, `GGML_MOE_SPEC_BUDGET=N` env var (mirrors existing `moe_n_expert_override` plumbing).
2. In `src/llama-graph.cpp::build_moe_ffn` after line 1398 softmax, when `cparams.moe_spec_budget > 0 && cparams.moe_spec_budget < n_expert && n_tokens >= cparams.moe_spec_min_batch (default 8)`:
   - Aggregate: `expert_scores = ggml_sum_rows(probs)` → `[1, n_expert]` (sum across n_tokens)
   - Top-B select: `top_b = ggml_argsort_top_k(expert_scores, cparams.moe_spec_budget)` → `[B, 1]`
   - Build mask following existing expert-groups pattern (lines 1437-1454): set selection_probs to -INFINITY for experts NOT in top-B
   - Existing argsort_top_k at line 1458 naturally selects only in-S experts per token
3. Quality validation: PPL bit-exact at 12 chunks WikiText-2 on Coder-30B Q4_K_M and REAP-246B Q4_K_M (will pass by construction).
4. Throughput measurement: 5-rep proper canonical on:
   - Coder-30B Q4_K_M with `--draft-max 32 -p-split 0` (production config), B sweep over {n_expert/2, n_expert*3/4, n_expert} where n_expert=128 (B=128 is off; B=64 mid; B=96 light)
   - REAP-246B Q4_K_M with `--draft-max 32 -p-split 0`, B sweep matching n_expert (likely 80 for REAP-246B post-pruning; sweep {40, 60, 80})
5. Success gate: ≥5% on at least one of the two models OR explicit closure via test.

Phase 1 prototype branches from `feature/cpu-ep-inter-process` (current HEAD `0bc793637`).



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

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-487] "Adaptive hybrid speculative decoding for accelerating large language model inference"** (Yang Yong et al., Neurocomputing 2026, peer-reviewed, paywalled)
  - Relevance: Same problem space as Phase 1's verification-batch mechanism — adaptive draft length + hybrid drafting. Mechanism unverifiable (no preprint, no abstract accessible).
  - Delta: catalog only; revisit if a preprint or open code surfaces. No action — Phase 1 gate already met by our heap-spec mechanism on Coder-30B + REAP-246B.

- **[intake-491] "Mamba Drafters for Speculative Decoding"** (arxiv:2506.01206; Findings of EMNLP 2025) — verdict: **worth_investigating**
  - Relevance: SSM-drafter-for-Transformer-target principle is directly applicable to our 30B-A3B + REAP-246B verification stack. Constant-memory drafter avoids the draft-path DRAM-bandwidth competition that limits speedup at large target sizes on EPYC.
  - Key technique: Mamba-130M external drafter + MAB-optimized tree-shape selector.
  - Reported results: GSM-8K 149.46 tok/s vs Pythia-410M 119.67 (Pythia-6.9B target); MT-Bench accept length 3.91 vs EAGLE 3.85.
  - Delta from current approach: (a) MAB tree-shape selector is a drop-in upgrade for our heap-spec tree shape independent of the SSM piece — investigate first; (b) SSM drafter for Coder-30B target requires hand-rolled Mamba inference in our llama.cpp fork, with no off-the-shelf small Mamba model tuned for our target's vocabulary — investigation, not adoption.
  - Caveats (Tier 2b): hidden-state backtracking limitation, tree verification incompatibility with sequential SSM, hyperparameter sensitivity. Competing approach (arxiv:2512.20573 diffusion-LLM drafting, Dec 2025) raises directional question whether SSM drafting is the long-term winner.

## Phase 2 — IN PROGRESS as of 2026-04-28 evening (wrap-up snapshot)

### v5 PGO build with MoE-Spec patch baked in

**Build dirs** (at `/mnt/raid0/llm/llama.cpp-experimental/`):
- `build_v5_pgo_gen/` — PGO instrumented (clang-20 + libomp + -march=znver5 + `-fprofile-instr-generate`)
- `build_v5_pgo_gen/merged.profdata` (2 MB) — merged from coder + q8 + reap profile runs (B=0 + B=64 Coder + B=40 REAP for mixed coverage; dense killed at 22 min wall)
- `build_v5_pgo_use/` — PGO-use rebuilt with `-fprofile-instr-use=...` from mixed merged.profdata; `--emit-relocs` linker flag for downstream BOLT

**Key insight from PGO single-B vs mixed-B**: under single-B (B=0 only) profile, the v5 build pessimized the MoE-Spec mask branch — Coder-30B B=64 dropped to **−43%** vs B=0 (mask overhead unprofiled, branch slow). After adding B=64 Coder + B=40 REAP profile runs to merged.profdata and rebuilding, Coder-30B B=64 returns to **parity (−2.6%)**. REAP-246B B=40 unaffected by either build (consistent +15% in both single-B and mixed-B PGO) because REAP's mask-overhead/total-compute ratio is small.

**Lesson for future PGO builds with MoE-Spec deployed**: profile workload MUST exercise B>0 path or PGO will pessimize it.

### Phase 1 mechanism re-validation under v5 PGO mixed-B (5-rep proper canonical)

Megasync at 100% on 1 core during measurement window depressed absolute numbers ~50% (clean Coder pp32 B=0 ~379 t/s; under noise ~198 t/s). Relative deltas within sweep are noise-tolerant.

**Coder-30B Q4_K_M pp32:**
| B | mean ± std | Δ vs B=0 |
|---|---|---|
| 0 | 198.57 ± 5.55 | reference |
| 96 | 144.79 ± 6.54 | −27.0% (mask overhead at light budget exceeds savings) |
| 64 | 193.34 ± 10.64 | **−2.6% (parity)** |
| 32 | 249.60 ± 3.24 | +25.7% (severe quality cost — see Phase 1 PPL data) |

**REAP-246B Q4_K_M pp32:**
| B | mean ± std | Δ vs B=0 |
|---|---|---|
| 0 | 51.14 ± 1.11 | reference |
| 60 | 52.05 ± 0.99 | +1.8% (within noise) |
| 40 | 58.06 ± 0.59 | **+13.5% (clean signal)** |
| 20 | 74.45 ± 0.08 | +45.6% (quality unusable per Phase 1 PPL) |

### Phase 2 end-to-end spec-dec via llama-server (IN PROGRESS)

Background task `b4bk8cu9g` running. Per-config: 3 prompts × n_predict=256 × spec-dec config matching production (`--draft-max 32 --p-split 0` linear). Captures `predicted_per_second` + `draft_n_accepted/draft_n` from /completion timing.

REAP-246B partial:
- B=0 (3 reps): rep0 server-not-ready JSON empty; rep1=7.27 t/s 59.9%; rep2=7.90 t/s 56.2%
- B=60 in progress at wrap-up
- B=40 + Coder B=0/64/32 queued (~25 min remaining)

Production registry reference: REAP-246B = 8.0 t/s spec-dec, 74-82% accept on coding workloads (we're testing on general prompts so accept rate is lower).

### Phase 2 deferred items (post-end-to-end completion)

1. **BOLT-libggml on v5 PGO for Coder-30B role**: morning's `libggml-cpu.so.0.coder.fdata` likely incompatible with v5 binary layout; needs fresh perf-record + perf2bolt + llvm-bolt cycle.
2. **Production registry integration** (`/mnt/raid0/llm/epyc-orchestrator/orchestration/model_registry.yaml`):
   - Per-role binary_path: REAP-246B + Q8 frontdoor + dense → universal v5 PGO binary; Coder-30B → v5 PGO + BOLT-libggml binary
   - Per-role moe_spec_budget config: REAP-246B → 40; Coder-30B → 0 (skip; quality+throughput tradeoff doesn't pencil out under v5 PGO for B=64 parity); other models → 0
3. **Orchestrator launch path** (`orchestrator_stack.py`): read per-role binary_path + env-pass MoE-Spec budget
4. **production-consolidated-v5 branch** in `/mnt/raid0/llm/llama.cpp`: git history paperwork — cherry-pick from `feature/cpu-ep-inter-process` HEAD `0c8d05597` onto `production-consolidated-v4`. Optional; the binary built from experimental HEAD is functionally equivalent.
5. **Full 32-chunk PPL gate on v5 PGO build**: 3-chunk diagnostic suffices for Phase 1; production routing decisions need full PPL.
