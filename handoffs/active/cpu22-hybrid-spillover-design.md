# CPU22 #3 — Hybrid Static+Dynamic Spillover Design Analysis (Phase 0)

**Status**: Phase 0 design analysis only. No code.
**Date**: 2026-04-29
**Source**: User direction "investigate both [CPU22 #3 + wdata-aware MUL_MAT] in sequence" 2026-04-29.
**Parent**: [`cpu-dynamic-moe-load-balancing.md`](cpu-dynamic-moe-load-balancing.md) (closed via test for #1 global tile-queue 2026-04-28; #2 token-to-expert and #3 hybrid spillover untested).
**Sibling Phase 0**: [`wdata-aware-mul-mat-coalescing-design.md`](wdata-aware-mul-mat-coalescing-design.md)

## Phase 0 lesson applied

Per CPU4 Phase 1 finding (2026-04-29), Phase 0 manual analyses MUST check **buffer-sharing constraints** in addition to dependency-graph independence. This note explicitly checks `params->wdata`, `params->wsize`, and threadpool atomics for shared mutable state.

## Existing infrastructure — what's already dynamic

`ggml_compute_forward_mul_mat_id` at `ggml-cpu.c:1798-2281` already does **per-expert dynamic chunk-stealing**:

```c
for (int cur_a = 0; cur_a < n_as; ++cur_a) {           // outer: every thread iterates all experts in order
    int current_chunk = eff_ith;
    atomic_int * current_chunk_ctr = atomic_current_chunk + cur_a;  // per-expert atomic
    while (current_chunk < nchunk0 * nchunk1) {
        ggml_compute_forward_mul_mat_id_one_chunk(...);
        if (eff_nth >= nchunk0 * nchunk1) break;
        current_chunk = atomic_fetch_add_explicit(current_chunk_ctr, 1, ...);  // dynamic chunk-pull
    }
}
```

Key observations:
- The OUTER loop (cur_a iteration) is statically ordered — every thread walks through all experts in the same order.
- The INNER chunk-pulling is dynamic via per-expert atomic counter.
- Per-expert atomic contention is bounded — only threads working on this expert hit this atomic.
- IDLE TIME emerges between experts: when expert A has fewer chunks than nth (`eff_nth >= nchunk0 * nchunk1`), threads beyond chunk_count don't grab any chunks; they immediately move to expert A+1.

So the IMBALANCE already captured by the existing path: for any single expert with `chunk_count >= nth`, all threads work simultaneously. Imbalance only manifests when expert sizes vary widely (some experts small).

## CPU22 #1 (global tile-queue) closure recap

CPU22 #1 (CLOSED 2026-04-28 at -2.3% Coder, -0.3% Next-80B noise, -0.8% REAP noise):
- Single global atomic `s_ws_next` indexes a flat tile array spanning all experts × all chunks.
- All 96 threads contend on this single atomic.
- Coder-30B Q4_K_M tg32 has ~12K tiles per token; at 96 threads × 30 ns per atomic = ~3.6 ms additional atomic latency per token. At ~50 ms/token baseline = +7% overhead. Combined with the ~15% sync-ceiling-capped gain from imbalance correction = expected ~+5-8%, but actual was -2.3%. Atomic contention dominated.

## CPU22 #3 design space

### Variant A: per-expert chunk-stealing + cross-expert spillover

Mechanism:
1. Maintain existing per-expert path EXACTLY as is (no changes to dynamic chunk-stealing within expert).
2. Add a separate **idle-thread queue** (`atomic_int s_idle_count`) that threads atomically increment when they finish all chunks of the current expert AND the next expert's chunk-count < nth (would have idled).
3. Idle threads spillover: pull from a small queue of "experts that need more help" — only experts where chunk-count >> nth and all threads are still working (expert is the bottleneck).

Estimated LOC: 150-250 (track expert progress + spillover queue + thread idle accounting).

### Variant B: priority-ordered work-stealing

Mechanism:
1. Pre-compute per-expert "criticality score" = chunks × log(remaining experts).
2. Threads pull experts by criticality, not by sequential cur_a order.
3. Per-expert chunk-stealing within (same as existing).

Estimated LOC: 100-150 (just changes the outer iteration order based on scoring).

### Variant C: bounded-atomic spillover

Mechanism:
1. Existing per-expert path runs as is.
2. After all experts processed once, a SECOND pass with global tile-queue runs over UNFINISHED chunks only.
3. The second pass only activates if imbalance > threshold.

Estimated LOC: 200-300 (track unfinished chunks across experts + second-pass tile queue).

## Buffer-sharing constraint check (CPU4 lesson)

| Buffer | Existing per-expert path | Variant A | Variant B | Variant C |
|---|---|---|---|---|
| `params->wdata` (src1 quantization) | shared, written by ith==0..nth before internal barrier; read in chunk loop | unchanged — wdata write happens BEFORE chunk-stealing entry; spillover only happens AFTER all threads passed the wdata-write barrier | same as existing | same as existing |
| `current_chunk_ctr[cur_a]` (per-expert atomic) | per-expert; bounded contention | unchanged + new spillover atomic | unchanged | unchanged + new global atomic for second pass |
| `s_idle_count` / `s_ws_next` (new atomics) | n/a | yes — new contention | n/a | yes — new contention (but only on second pass = lower frequency than #1) |

All three variants AVOID the wdata race that killed CPU4 Phase 1's MUL_MAT coalescing. The wdata write happens within the `mul_mat_id` op BEFORE any chunk-stealing; the new atomics only synchronize chunk distribution AFTER wdata is set.

## Gain ceiling analysis

CPU24 attribution: 15% sync-share. The existing per-expert path captures most of that within-expert. Cross-expert idle time (when expert chunk-count < nth) is the remaining slice — empirically ~3-7% of decode time on the typical Coder/Next/REAP MoE topology.

Variant A gain estimate: 2-5% (recovery of cross-expert idle time, minus overhead).
Variant B gain estimate: 1-3% (just reordering, no new work).
Variant C gain estimate: 3-7% (catches all imbalance, but second-pass overhead).

**All three variants are below the 5% threshold most of the time, with high variance.**

## Risk areas

- **Single atomic still appears**: spillover atomic (Variant A & C) still has 96-thread contention when imbalance triggers it. Will hit similar overhead profile as CPU22 #1.
- **Reordering ops in Variant B**: changes which thread writes which output rows. Need to verify the per-expert-row writes are commutative (they are — each thread writes disjoint rows); but ANY indeterminism could break PPL bit-exact.
- **Second-pass overhead in Variant C**: requires tracking remaining chunks across experts, additional barrier between phases, additional atomic contention.

## LOC estimate vs gain — composite

| Variant | LOC | Gain estimate | Gain/LOC |
|---|---|---|---|
| A | 150-250 | 2-5% | ~0.02% per LOC |
| B | 100-150 | 1-3% | ~0.02% per LOC |
| C | 200-300 | 3-7% | ~0.02% per LOC |

All three have similar low gain-per-LOC. None are strongly compelling on this metric.

## Phase 0 honest verdict

**Variant C (bounded-atomic spillover) has highest gain ceiling (3-7%) but also highest LOC (200-300) and similar risk profile to CPU22 #1**. The existing per-expert path is already capturing most of the in-expert imbalance gain; the residual cross-expert idle time is a small target.

**Recommend NOT advancing to Phase 1** unless:
- A more clever mechanism emerges (e.g., predictive reordering using historical per-expert chunk counts)
- The 15% sync ceiling is revised UP by new attribution work
- A different model architecture creates more pronounced cross-expert imbalance

If forced to pick one, **Variant C** is the highest-ceiling option but likely lands in the 3-7% noise band given CPU22 #1's overhead pattern.

## Comparison with sibling Phase 0 (wdata-aware MUL_MAT coalescing)

See [`wdata-aware-mul-mat-coalescing-design.md`](wdata-aware-mul-mat-coalescing-design.md) for the sibling analysis. Comparing gain-per-LOC between this and the sibling will inform which (if either) advances to Phase 1.

## Files

- This design note (paper analysis only, no code).
- No measurement bundle yet.
- Phase 1 prototype deferred behind sibling-comparison decision.
