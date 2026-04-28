# CPU4 Deferred Avenues — Design Pick (2026-04-30)

**Status**: Design analysis. No code written. Picks ONE avenue to advance to prototype if user agrees.
**Parent**: [`cpu-hierarchical-barrier.md`](cpu-hierarchical-barrier.md) (CLOSED 2026-04-26 for the 2-level CCD-aware barrier variant — negative result).
**Sibling**: [`cpu-dynamic-moe-load-balancing.md`](cpu-dynamic-moe-load-balancing.md) (CLOSED 2026-04-28 for design #1 global tile-queue work-stealing — negative result; designs #2 and #3 untested).
**Source**: user direction "CPU4 sync primitive" 2026-04-30.

## Why this note exists

CPU4's original implementation (per-CCD arrival + cross-CCD aggregation, sense-flip 2-level barrier in the OpenMP path) measured -2 to -4% on Coder-30B and parity on REAP-246B. The handoff explicitly preserves a 4-design deferred list (handoff "Implications" section). On 2026-04-30 the user asked to advance "CPU4 sync primitive" alongside MAB Phase 1 and slot-promotion re-eval.

Before committing 1-3 days to prototype work, this note enumerates the actual design space, identifies which avenues are TESTED-AND-FAILED vs GENUINELY-UNTESTED, and recommends ONE to advance.

## Design space inventory

| # | Design | Source | Status | Notes |
|---|---|---|---|---|
| 1 | 2-level CCD-aware barrier (per-CCD arrival + cross-CCD aggregate, sense-flip) | CPU4 Phase 1 | **TESTED — FAILED** (-2 to -4% Coder-30B Q4_K_M, parity REAP-246B) | libgomp's `omp barrier` is highly optimized; naive replacement loses to it on EPYC NPS4 |
| 2 | Lock-free expert dispatch (global tile-queue, threads atomic-pull next chunk) | CPU22 design #1 | **TESTED — FAILED** (-2.3% Coder, -0.3% / -0.8% noise on Next-80B / REAP) | Single-atomic contention at 96 threads dominates the 15% sync-ceiling-capped gain |
| 3 | Token-to-expert runtime rebalance with bounded migration | CPU22 design #2 | **UNTESTED** | Per-token re-routing; would need profile feedback into the `ids` tensor build |
| 4 | Hybrid static+dynamic spillover (coarse static partition + dynamic correction tail) | CPU22 design #3 | **UNTESTED** | Lower atomic contention than #2 (only spillover hits the queue); preserves static cache locality |
| 5 | Cross-CCD work migration | CPU4 deferred | **UNTESTED** | Migrate work from idle CCDs to busy ones; requires runtime profiling per op |
| 6 | MoE quant layout rebalance (offline) | CPU4 deferred | **UNTESTED, OUT OF SCOPE** for in-tree change | Pre-shuffle experts so each CCD's assigned slice has balanced compute; offline tooling, not a sync primitive |
| 7 | Op-coalesced barriers (Lever B ext.) | CPU4 deferred | **UNTESTED** | Reduce the COUNT of barriers per op-graph by merging sync points across consecutive non-dependent ops; orthogonal to barrier IMPLEMENTATION |

## Constraint envelope

- 15% sync ceiling per CPU24 attribution caps imbalance-correction gain (designs #3, #4, #5) at ~7-15% on sync-bound MoE Q4_K_M class.
- Production targets: Q4_K_M sync-bound class (Coder-30B, Next-80B, REAP-246B, gemma-4-26B-A4B). Q8_0 frontdoor is bandwidth-bound, not sync-bound; out of scope.
- Build environment: clang-20 + libomp + znver5 + PGO (the v5 production stack per CPU11 closure). Any CPU4 change must be measured under this toolchain.
- CPU20 rigor gate: 5-rep proper canonical for sub-5% deltas; PPL bit-exact required.

## Recommendation: **#7 op-coalesced barriers**

Rationale:

1. **Targets a different bottleneck class than what's been falsified.** Designs #1 and #2 attacked barrier IMPLEMENTATION and DYNAMIC LOAD BALANCING — both lost. Op-coalesced barriers attack barrier COUNT — the structural number of `#pragma omp barrier` invocations per token.
2. **Lower-risk than the imbalance-correction designs (#3, #4, #5).** No topology assumptions; no per-token routing; no runtime profiling. The change is local to ggml's op scheduler.
3. **Modest LOC.** Estimated ~60-150 LOC in `ggml/src/ggml-cpu/ggml-cpu.c` op-graph compute path. No new env flag plumbing beyond `GGML_BARRIER_COALESCE=N` (default off).
4. **Orthogonal to the 15% sync ceiling.** The 15% measures wall-clock spent IN barriers; coalescing reduces the COUNT of barriers per token, which can compound with per-barrier waste even if per-barrier waste itself is irreducible.

### Mechanism

In `ggml-cpu.c::ggml_graph_compute_thread`, ops are dispatched sequentially with a `ggml_barrier(threadpool)` between each. Some op pairs are independent (e.g., RMS_NORM + scale, NORM + repeat, two parallel branches before a join). Coalescing merges the barriers between independent ops.

The transformation is op-graph local: walk the op list at compute setup time, identify maximal chains of barrier-able ops, emit a SINGLE barrier at the end of each chain. The dependency analysis is already partially encoded in `n_tasks > 1` flags + tensor source/dest tracking — needs a one-time pass to compute which ops are inter-dependent.

### Implementation sketch

```c
// One-time pass at graph setup (already-iterated structure). Per op:
// op->coalesce_with_next = !op->writes_to_input_of_next && op->n_tasks_compatible_with_next;

// At dispatch time (existing per-op loop):
ggml_compute_forward(params, &cgraph->nodes[i]);
if (i + 1 < n_nodes && cgraph->nodes[i].coalesce_with_next) {
    // skip the barrier; next op's compute can proceed
} else {
    ggml_barrier(params->threadpool);
}
```

A safety gate: only coalesce ops with identical `n_tasks` and identical work-distribution shape, so threads don't drift in their per-thread state.

### Risk areas

- **Memory ordering across coalesced ops.** Without a barrier, op N+1's reads of op N's outputs are not synchronized. Need to verify each coalesced pair's dependency graph: writes of N must be already-globally-visible to reads of N+1, OR they must be on disjoint memory regions. Conservative: only coalesce ops where N writes to a buffer that N+1 doesn't read.
- **Op kernels that internally use `params->ith == 0` for setup work.** The setup work needs to either be redundantly executed or guarded by a per-op atomic. Existing barrier provides serialization for free; coalescing breaks that.
- **PPL drift.** Any silent reordering causes accumulated drift. Bit-exact PPL on at least Coder-30B + REAP-246B 32-chunk WikiText-2 is the must-pass gate.

### Phase 0 falsification probe

Before committing to implementation:

- **Step 0.1**: Manual analysis of typical op chain on Coder-30B Q4_K_M decode. Count barriers per token; identify how many would coalesce under the safety rules above. If the count is < 10% of total per-token barriers, the gain is structurally bounded below ceiling and the work isn't worth pursuing. **~2 hours, no code changes.**
- **Step 0.2** (if Step 0.1 passes): static op-graph analysis tool that takes a model + a compute-graph dump and reports the coalescing potential. ~150 LOC throwaway. **~half day.**
- **Step 0.3** (if Step 0.2 reports ≥10% reduction in barrier count): proceed to prototype.

This Phase 0 is information-cheap and would close the design via test if the static analysis already shows the coalescing potential is too small to matter.

## Gates

| Phase | Gate | Action |
|---|---|---|
| 0.1 manual analysis | barrier-count reduction estimate ≥10% on a representative op chain | proceed to 0.2; otherwise close-via-analysis with scoped wording |
| 0.2 static graph tool | barrier-count reduction ≥10% on Coder-30B + REAP-246B + Next-80B compute graphs | proceed to prototype; otherwise close |
| 1 prototype | t/s ≥+5% on at least 2 of 3 sync-bound Q4_K_M models AND PPL bit-exact 32-chunk | ship default-off opt-in; if ≥+10% on all 3, default-on |
| 1 prototype | t/s neutral or worse on any model | revert; document failure mode |
| 1 prototype | PPL drift > noise floor on any model | revert; document drift mechanism |

## NOT recommended (and why)

- **#3 token-to-expert rebalance**: highest complexity (per-token re-routing logic), highest implementation risk (touches `ids` tensor build path), and capped at 15% sync ceiling per CPU24 attribution. Better as a long-term R&D track if other levers exhaust.
- **#4 hybrid static+dynamic spillover**: more attractive than #3, but operates in the same per-tile work-stealing space that #2 already failed in. The marginal change (only spill, don't fully replace) reduces atomic contention but is bounded by the same sync ceiling. Worth keeping in scope but second-priority to #7.
- **#5 cross-CCD work migration**: requires runtime profiling primitives that don't exist yet (~2-3 days infra alone), even before the migration mechanism. Out of scope for a single-track session.
- **#6 MoE quant layout rebalance**: offline tooling change, not a sync primitive. Belongs in a separate quantization-track handoff (`cpu-shape-specialized-gemv-decode.md` or a new entry); does not match user's "CPU4 sync primitive" framing.

## Closure-inflation discipline

If Phase 0 closes the track:

> "Static analysis on Coder-30B / REAP-246B / Next-80B compute graphs at v5 PGO build shows op-coalesced-barrier potential is below 10% of total per-token barriers under the safety rules (no read-after-write, no `ith==0` setup divergence, identical n_tasks). Op-coalesced barriers cannot deliver meaningful gain in the current llama.cpp ggml graph for Qwen3-class MoE inference; closing the avenue. Does NOT generalize to: (a) other architectures (dense, hybrid SSM, attention-only) where the op chain is shaped differently; (b) future ggml graph rewrites that introduce more parallel branches; (c) prefill (where op chains are larger). Reopen if any of these regimes change."

If Phase 1 closes via prototype regression:

> "Op-coalesced-barrier prototype at HEAD <commit> on `feature/cpu-ep-inter-process` measured no t/s gain (or PPL drift) on the production Q4_K_M lineup. The barrier-count reduction was insufficient to overcome <specific overhead from the coalescing pass>. Different coalescing rules (e.g., aggressive without per-pair dependency check) may behave differently but were not tested."

## Cross-references

- Parent: [`cpu-hierarchical-barrier.md`](cpu-hierarchical-barrier.md) Implications section
- Sibling (already-tested adjacent design): [`cpu-dynamic-moe-load-balancing.md`](cpu-dynamic-moe-load-balancing.md) — work-stealing + 2 untested designs
- CPU24 sync ceiling: [`cpu-uncore-fabric-attribution.md`](cpu-uncore-fabric-attribution.md)
- v5 toolchain: [`cpu-kernel-env-flags-inventory.md`](cpu-kernel-env-flags-inventory.md) Build-time toolchain section
