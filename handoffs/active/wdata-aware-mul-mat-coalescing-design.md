# wdata-aware MUL_MAT Coalescing Design Analysis (Phase 0)

**Status**: Phase 0 design analysis only. No code.
**Date**: 2026-04-29
**Source**: User direction "investigate both [CPU22 #3 + wdata-aware MUL_MAT] in sequence" 2026-04-29.
**Parent**: [`cpu4-deferred-avenues-design-note.md`](cpu4-deferred-avenues-design-note.md) — CPU4 Phase 1 closure (2026-04-29) introduced this variant.
**Sibling Phase 0**: [`cpu22-hybrid-spillover-design.md`](cpu22-hybrid-spillover-design.md)

## Why this variant exists

CPU4 Phase 1 (2026-04-29) discovered that op-coalesced barriers cannot include MUL_MAT/MUL_MAT_ID due to the shared `params->wdata` buffer used for src1 quantization. Excluding MUL_MAT shrinks per-token barrier-count reduction from Phase 0's 24-29% estimate to ~5% (only 1 ROPE-Q→RMS_NORM-K coalescable per layer).

This variant proposes an architectural change: give each MUL_MAT op its own wdata SEGMENT so coalescing two MUL_MATs no longer races. With per-op wdata, the high-value Q/K/V chain coalescing (3 inter-op barriers → 1) becomes safe.

## Current architecture (`ggml_graph_plan`)

At `ggml-cpu.c:3428-3651`:
- Iterates all nodes, computes per-node `cur` work_size requirement.
- `work_size = MAX(work_size, cur)` — **single shared buffer sized for the LARGEST single op**.
- All ops share the SAME `cplan->work_data` pointer at compute time.
- Each op kernel reads `params->wdata` (= `cplan->work_data`) directly.

The shared-buffer strategy is space-efficient (single max allocation) but FORCES sync between ops that both write wdata.

## Proposed architecture: per-op wdata segments

### Step 1: graph analysis pass at plan time

Walk `cgraph->nodes[]` once. Build a list of **coalescable chains**: maximal consecutive op sequences where (a) each op's src[] doesn't include the previous op's output, AND (b) each op is in the safe-when-non-shared-wdata allowlist.

Example chain for Qwen3 MoE attention block:
- Q-MUL_MAT (writes Qcur, wdata-A)
- K-MUL_MAT (writes Kcur, wdata-B) — independent of Q, but shares wdata-A under current scheme
- V-MUL_MAT (writes Vcur, wdata-C) — independent of Q+K

Under per-op wdata: Q uses wdata-A, K uses wdata-B, V uses wdata-C. No overlap.

### Step 2: cplan extension

Add per-node wdata offset:

```c
struct ggml_cplan {
    int n_threads;
    size_t work_size;
    uint8_t * work_data;
    int * node_wdata_offset;   // NEW: per-node offset into work_data, length cgraph->n_nodes
    ggml_threadpool * threadpool;
    bool use_ref;
};
```

`work_size` becomes: sum of segment-sizes for each coalescable chain (max-within-chain becomes sum-across-chain). Per-chain segment offset starts where previous chain's max ended.

For non-coalescable ops (singletons): segment is reused with prior op (current behavior).

### Step 3: per-op wdata redirection

Each kernel that reads `params->wdata` redirects to `params->wdata + cplan->node_wdata_offset[current_node_idx]`. Need to thread `node_idx` through `ggml_compute_params`.

Sites to change (per grep earlier):
- `ggml_compute_forward_mul_mat` (line ~1467, ~1491, ~1834)
- `ggml_compute_forward_mul_mat_id` (line ~1893, ~2118, ~2133, ~2220, ~2272)
- `ggml_compute_forward_rope` (uses wdata for cosine cache)
- `ggml_compute_forward_softmax`, `_norm`, `_rms_norm` (when GGML_RMS_NORM_PARALLEL=1) — already partial users
- `ggml_compute_forward_count_equal`, `_top_k`, `_flash_attn_*`, `_conv_*` — many ops use wdata

Each redirection is mechanical: replace `params->wdata` with `params->wdata + params->node_wdata_offset` (or equivalent per-node offset access).

### Step 4: coalesce-skip logic at compute loop

Same as CPU4 Phase 1, but with MUL_MAT/MUL_MAT_ID NOW BACK in the allowlist (since per-op wdata removes the race).

## LOC estimate

| Component | LOC |
|---|---|
| Graph-analysis pass at `ggml_graph_plan` (build node_wdata_offset[]) | 80-120 |
| `cplan` struct extension + allocation/free | 30-50 |
| Per-op wdata redirection (~10 sites × 5 LOC) | 50-80 |
| Compute-loop skip logic (extend CPU4 Phase 1 with MUL_MAT in allowlist) | 50-80 |
| Tests + integration (PPL gate + smoke + multi-arch sanity) | 50-80 |
| **Total** | **~260-410 LOC** |

## Buffer-sharing constraint check (CPU4 lesson)

| Buffer | Behavior under per-op wdata segments |
|---|---|
| `params->wdata` segment for op N | Disjoint from op N+1's segment when coalesced. SAFE for Q/K/V chain. |
| `params->wsize` (total buffer size) | Now sum-of-chain-sums instead of max-of-op-sizes. Larger but bounded. |
| `current_chunk_ctr[cur_a]` (per-expert atomic) | Per-op state; coalescing doesn't change this. |
| `threadpool->workers[].cpumask` | Per-thread state; not affected by op coalescing. |
| `s_ws_*` static (CPU22 #1 work-stealing globals) | Mutually exclusive with this design (different code paths). |

**Result**: with per-op wdata, the wdata race that killed CPU4 Phase 1 is structurally eliminated for MUL_MAT pairs.

## Risk areas

### A. ABI change to `struct ggml_cplan`

`ggml_cplan` is part of the ggml public API (declared in `ggml.h`). Adding a field changes the struct layout. This means:
- Need to bump ggml ABI version OR add the field at the end of the struct (less clean).
- Downstream consumers (other ggml backends in the same fork) may have to be updated.
- Upstream coordination if the change is meant to be merged back.

This is the LARGEST risk. It's not a compile-flag-gated change — it's structural.

Mitigation: prototype on a feature branch, env-gate the new path so old behavior is the default, only flip default-on after extensive testing.

### B. wdata size growth

Current: `work_size = max(per_op)`. Worst-case op is typically a large MUL_MAT_ID (REAP-246B can have ~110 GB CPU_REPACK buffer per the cpu-kernel-env-flags-inventory note, but that's the model weight repack — different from wdata).

For decode-time wdata: dominated by src1 quantization for the largest MUL_MAT. On Coder-30B Q4_K_M decode: per-op wdata ~5-50 KB. Sum of a 3-op Q/K/V chain: 15-150 KB. Sum across all coalescable chains in a token: ~few MB. Comfortably small.

For prefill (n_tokens=2048+) or large batch: per-op wdata grows linearly. Sum-of-chain still bounded by sum-of-tokens × per-token-wdata; a few MB to tens of MB. Manageable.

### C. Per-op wdata redirection touches many kernels

10+ kernel sites need the wdata-pointer redirection. Each is a mechanical change but the surface area is large. PPL bit-exact gate must pass on all kernels — any missed redirection causes silent wrong output.

### D. The CPU4 Phase 1 per-iteration check overhead

CPU4 Phase 1 measured -19.7% on Coder under safe (non-MUL_MAT) coalescing. Theory: per-iteration dependency check (10 pointer comparisons × 1000 ops × 96 threads) outweighed the small barrier savings.

For wdata-aware version: SAME check overhead applies, but now the savings are larger (Q/K/V chain coalescing is 2-3 saved barriers per layer × 48 layers = 96-144 saved barriers per token). If the per-iteration check costs ~10-20 ms per token (per CPU4 Phase 1 indication), and saving 100+ MUL_MAT barriers saves more than that, NET positive.

But this needs MEASUREMENT, not estimation. CPU4 Phase 1 was the wake-up call that paper analysis is unreliable here.

### E. MUL_MAT internal barrier still required

`ggml_compute_forward_mul_mat` has an internal barrier at line 1487 BEFORE the chunk-loop. This is for thread coordination (all threads must reach chunk-loop entry simultaneously). With per-op wdata, this internal barrier is still needed.

Implication: we save the BETWEEN-OP barrier (skipped) but each MUL_MAT still has its INTERNAL barrier. Coalescing 3 MUL_MATs eliminates 2 between-op barriers but preserves 3 internal barriers. So per-3-MUL_MAT chain: 5 barriers (2 between + 3 internal) → 3 barriers (3 internal). Savings: 2 barriers per chain.

Per-layer savings: ~2-3 barriers (Q/K/V chain + maybe gate/up chain).
Per-token savings: 96-144 barriers across 48 layers.
As fraction of total ~1012 per-token barriers: 9.5-14%.

## Gain ceiling analysis

| Scope | Coalescable per-layer | Per-token reduction | Estimated t/s gain |
|---|---|---|---|
| CPU4 Phase 1 (no MUL_MAT) | 1 | 4.7% of barriers | -10 to -20% (per check overhead) |
| **wdata-aware (with MUL_MAT)** | **2-3** | **9.5-14% of barriers** | **2-7% (estimate, NEEDS MEASUREMENT)** |

Risk: even at 9.5-14% barrier reduction, the per-iteration check overhead might still cancel the gain (CPU4 Phase 1's dependency check costs scale with op count, not with savings). Could land neutral.

## Phase 0 honest verdict

**Estimated gain**: 2-7% on Coder + REAP + Next-80B at v5 PGO build.
**LOC**: 260-410.
**Risk**: HIGH (ABI change, 10+ kernel sites, dependency-check overhead might dominate).

**Gain/LOC**: ~0.01-0.03% per LOC. Similar to CPU22 #3 variants.

**Verdict**: technically feasible but NOT strongly compelling on gain-per-LOC. The architectural change (cplan ABI, per-kernel redirection) is invasive for a 2-7% expected gain. Better than CPU22 #3 on gain ceiling (9.5-14% barrier reduction vs 3-7% for CPU22 #3 imbalance recovery), but architectural cost is much higher.

**Recommend NOT advancing to Phase 1** unless:
- A simpler implementation surfaces (e.g., per-op wdata segments without ABI change, perhaps via a thread-local override)
- The CPU4 Phase 1 per-iteration overhead is independently mitigated (e.g., by precomputing coalesce_with_next at graph-plan time)
- A different architectural change (e.g., upstream graph rewrite to fuse Q/K/V) makes coalescing trivial

If forced to advance: this design is genuinely interesting research. The expected 2-7% would be the largest CPU-software gain since CPU2's NUMA auto-mbind. But the implementation complexity is real.

## Comparison vs sibling Phase 0 (CPU22 #3 hybrid spillover)

| Dimension | CPU22 #3 hybrid spillover | wdata-aware MUL_MAT coalescing |
|---|---|---|
| Gain ceiling | 3-7% (15% sync ceiling × imbalance fraction) | 9.5-14% barrier reduction → 2-7% t/s |
| LOC estimate | 100-300 | 260-410 |
| ABI implications | None (internal flag/atomic) | YES (`cplan` struct extension) |
| Risk profile | Moderate (atomic contention déjà-vu of CPU22 #1) | High (architectural change + dependency-check overhead unknown) |
| Cross-arch generality | Likely Q4_K_M-specific (sync-bound class) | Universal — any model with parallel branches |
| Revisitability if Phase 1 fails | Low (designs #1 already failed; similar contention class) | Moderate (different per-iteration check avoids -19.7% overhead) |

**Both have similar expected gain (~3-7%) but different risk profiles**: CPU22 #3 inherits failure mode of its sibling #1 (atomic contention); wdata-aware is genuinely new territory but architecturally invasive.

**Neither is a strong Phase 1 candidate.** If pressed to advance one, wdata-aware has higher gain ceiling and broader applicability — but the ABI change is a real cost.

## Combined recommendation

Given:
- CPU4 Phase 1 already closed via test (-19.7% on Coder)
- Slot-promotion + MAB selector both closed via test (no per-request CPU optimization gains)
- These two design space candidates (CPU22 #3 + wdata-aware) both expected to land in 0-5% range, not the +10% needed for production push

**Recommend pausing the CPU optimization track.** The remaining design space has structural ceilings (15% sync, ~10% barrier reduction) that the implementation overhead likely consumes. Better-leverage activities:

1. **Multi-arch coverage**: test the existing v5 PGO + CPU2 mbind + CPU1 stack on dense models, hybrid SSM, attention-only models. Different arch may show different bottleneck class where these tools' costs become net-positive.
2. **Workload-shape coverage**: prefill, multi-tenant batching, long-context — different op-chain shapes where coalescing potential differs.
3. **Different toolchain frontier**: investigate aggressive PGO+BOLT-libomp under new compiler versions, or platform-specific levers (e.g., AMX on Intel hardware if a test box becomes available).
4. **Higher-level mechanism research**: model-level optimizations (different quant layouts, fused layer ops at the model-builder level rather than the ggml level).

If the user prioritizes a specific mechanism candidate, this design note serves as the ready Phase 0 document for it.

## Files

- This design note (paper analysis only, no code).
- No measurement bundle yet.
- Phase 1 prototype deferred behind sibling-comparison decision.
