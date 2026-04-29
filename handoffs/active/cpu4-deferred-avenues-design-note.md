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
| 7 | Op-coalesced barriers (Lever B ext.) | CPU4 deferred | **TESTED — FAILED 2026-04-29** | Phase 0 estimated 24-29% barrier-count reduction. Phase 1 implementation (smoke discovered MUL_MAT wdata race, allowlist tightened) measured net-negative on all 3 sync-bound Q4_K_M models (Coder -10 to -20%, Next-80B -6.2%, REAP -2.3%). Phase 0 was empirically WRONG due to missed wdata-shared-buffer hazard. Code stays in tree disabled-by-default. |

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


---

## Phase 0 RESULT (2026-04-29) — GATE PASSED

Manual op-chain analysis on Qwen3 MoE architecture (Coder-30B-A3B + REAP-246B-A35B targets) at v5 PGO build identifies **24-29% per-token barrier-count reduction** under the conservative op-coalescing rule. Well above the 10% Phase 0 gate threshold.

### Per-layer breakdown

- **Attention block: 11 barriers, 5 skippable (45%)** — Q/K/V projections collapse from 3 to 1, Q-norm/K-norm collapse from 2 to 1, RoPE-Q/RoPE-K collapse from 2 to 1.
- **MoE FFN block: 10 barriers, 0-1 skippable (~5%)** — mostly serialized (each op consumes prior op's output).
- **Per-layer aggregate: 21 barriers, 5-6 skippable (24-29%)**.
- **Per-token (Coder 48 layers + final): ~1012 total barriers, 240-288 skippable**.

### Why it's sound

1. ggml MUL_MAT writes to fresh dst tensor (not in-place) → Q/K/V reading same input is race-free.
2. MUL_MAT internal barrier at ggml-cpu.c:1487 is PRESERVED by coalescing — per-op thread-coordination sync point remains.
3. Existing Phase 1.4 (`GGML_BARRIER_LOCAL_BETWEEN_OPS`) only downgrades partitioned→elementwise pairs; coalescing catches MUL_MAT→MUL_MAT pairs Phase 1.4 misses. Gain is INCREMENTAL over Phase 1.4.

### Recommended Phase 1

~150 LOC, 1-2 days implementation + 1 day measurement:
- Graph-setup-time dependency pass marking `coalesce_with_next` per node
- Compute-loop skip at ggml-cpu.c:3709-3782 when `coalesce_with_next` is true
- `GGML_BARRIER_COALESCE=1` env gate (default off)

Phase 1 gates (binding):
- PPL bit-exact 32-chunk WikiText-2 on Coder-30B + REAP-246B Q4_K_M.
- 5-rep canonical t/s ≥ +5% on at least 2 of 3 sync-bound Q4_K_M models.

CPU20 bundle: [`data/cpu_optimization/2026-04-29-cpu4-op-coalesced-barriers-phase0/`](../../epyc-inference-research/data/cpu_optimization/2026-04-29-cpu4-op-coalesced-barriers-phase0/) (analysis + Phase 0 GO decision).

**Status**: Phase 0 GO. Phase 1 implementation pending user pick.


---

## Phase 1 RESULT (2026-04-29) — NO-GO via test (REVISED 2026-04-29 evening — Remediation Phase A)

> **2026-04-29 EVENING UPDATE — Remediation Phase A**: the original measurement below was POISONED by a missing OMP env stack (`OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active`). Re-measured under FULL canonical recipe (bundle [`2026-04-29-remediation-phase-A-cpu4/`](../../epyc-inference-research/data/cpu_optimization/2026-04-29-remediation-phase-A-cpu4/)): Coder-30B Q4_K_M tg64 5-rep COALESCE=0 = **46.96 ± 0.16**, COALESCE=1 = **47.05 ± 0.16**, COALESCE=0 recheck = **47.00 ± 0.09**. **Δ = +0.19% (NEUTRAL, within noise)**. The original "-19.7%" finding was a measurement artifact: under broken-OMP, sleeping barriers were unusually expensive and the coalesce code's barrier-skipping interacted asymmetrically. Under proper canonical, both arms behave well and coalescing is essentially a no-op for throughput on this allowlist.
>
> **Disposition unchanged**: gate criterion was ≥+5% (or ≥10% per binding spec); +0.19% doesn't meet the bar, so still NO-GO for shipping. But the FRAMING materially changes: the patch is **HARMLESS** (not a regression). MUL_MAT wdata race finding stands (correctness, independent of perf). Future work — expanding the coalesce allowlist beyond the conservative MUL_MAT-excluded set — is now a cleaner exploration since the conservative path is verified neutral, not destructive.

### Original Phase 1 measurement (2026-04-29 morning — POISONED by broken OMP env)

Bundle: [`data/cpu_optimization/2026-04-29-cpu4-op-coalesced-barriers-phase1/`](../../epyc-inference-research/data/cpu_optimization/2026-04-29-cpu4-op-coalesced-barriers-phase1/)

### Implementation

~80 LOC patch in `ggml-cpu.c` (compute-loop op-iteration), env-gated `GGML_BARRIER_COALESCE=1` (default off). Logic: for each adjacent op pair (N, N+1), skip the between-op barrier when (a) next op's `src[]` does NOT contain cur node, AND (b) both ops are in the safe allowlist.

### Critical discovery: MUL_MAT wdata race

Smoke test at COALESCE=1 with MUL_MAT in the allowlist produced **garbled output**: "Failed to parse input at pos 0: GD Sw\n…\nCompatibility几..."

Root cause: `ggml_compute_forward_mul_mat` writes src1 quantization to the shared `params->wdata` buffer BEFORE its internal barrier (`ggml-cpu.c:1467-1487`). Coalescing two MUL_MATs lets op N+1 clobber wdata while op N's chunk-loop still reads it. Phase 0 static analysis missed this constraint.

**Allowlist tightened to exclude MUL_MAT/MUL_MAT_ID**: `RMS_NORM`, `NORM`, `ROPE`, `MUL`, `ADD`, `SCALE`, `UNARY`, `GLU`. Smoke at this allowlist passes bit-exact (Coder PPL chunk-3 = 9.8567 ± 1.23745 identical).

### Phase 0 was 5× over-estimated

After excluding MUL_MAT, the achievable per-token barrier-count reduction drops from Phase 0's 24-29% to **~5%** (1 skippable barrier per layer in attention block: ROPE-Q → RMS_NORM-K is the only IND pair under safe allowlist; MoE FFN block has 0 skippable). The mechanism's gain ceiling is structurally bounded below the +5% gate.

### Measurement

| Model | n_total | Δ_pct | Note |
|---|---|---|---|
| Coder-30B Q4_K_M | 20 reps (5 first-pass + 15 replication) | -10 to -20% (high CV) | Mean -19.7% across 3 alternated trials × 5 reps |
| Next-80B Q4_K_M | 5 reps | -6.2% | High noise (CV 30%) |
| REAP-246B Q4_K_M | 5 reps | -2.3% | Clean signal (CV <1%) |

PPL bit-exact verified on Coder + REAP. Throughput gate (≥+5% on 2 of 3 sync-bound models) NOT MET.

### Why net-negative (theories)

1. Phase 0 over-estimated coalesce potential by 5× (wdata constraint missed).
2. Skipped barriers are CHEAP barriers (ROPE/RMS_NORM are tiny; cross-CCD sync cost is small).
3. Per-thread overhead from the per-iteration dependency check (10 pointer comparisons × 1000 ops × 96 threads).
4. Memory-ordering / cache effects when threads desync across op boundaries.

### Operational disposition

- Patch stays in tree disabled-by-default. Same treatment as slot-promotion dispatcher v1. Costs nothing at default.
- Re-evaluate only if: (a) different barrier implementation makes per-iteration check cost-free, (b) a **wdata-aware MUL_MAT coalescing variant** (per-op wdata segments) is designed and unlocks Q/K/V chain coalescing, (c) a different model architecture with different op-chain shape is benchmarked.

### Lesson for future Phase 0 analyses

**Phase 0 manual op-chain analyses MUST check buffer-sharing constraints, not just dependency-graph independence.** Specifically: does cur op write to a shared mutable buffer (params->wdata, params->wsize, threadpool state)? Does next op read from the same buffer? If yes, coalescing is unsafe even when direct src/dst dependency is absent. This gate was missed in the original Phase 0 design note.

### Other deferred avenues remain open

The 5 other designs in this note's design space (token-to-expert rebalance, hybrid static+dynamic spillover, cross-CCD work migration, MoE quant layout rebalance, **plus the new wdata-aware MUL_MAT coalescing variant** introduced by this Phase 1 finding) are still UNTESTED and could be advanced in future sessions.
