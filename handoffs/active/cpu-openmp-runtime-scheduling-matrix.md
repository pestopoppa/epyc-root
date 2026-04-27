# CPU21 — OpenMP Runtime And Scheduling Matrix

**Status**: ACTIVE — libgomp affinity/wait-policy submatrix complete (universal +3-8% landed); libomp runtime + chunks 8/16 PENDING (closure-inflation correction applied 2026-04-27 evening per peer review).
**Priority**: HIGH
**Categories**: hardware_optimization, inference_serving, runtime_tuning
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) (CPU21)
**Related**: [`cpu-benchmark-rigor-and-revalidation.md`](cpu-benchmark-rigor-and-revalidation.md) (CPU20 gate), [`cpu-hierarchical-barrier.md`](cpu-hierarchical-barrier.md) (single variant falsified), [`cpu-dynamic-moe-load-balancing.md`](cpu-dynamic-moe-load-balancing.md) (CPU22 follow-on)

## Objective

Test whether sync-heavy Q4_K_M regressions are recoverable by OpenMP runtime/scheduling choices before doing deeper kernel surgery.

## Status summary (added 2026-04-27 evening after peer review)

**Submatrix complete**: libgomp × Phase A affinity (close/spread × cores/threads, master, false) × Phase B partial schedule (static/dynamic/guided × chunk={1,4}) × Phase C wait policy (active/passive). The `OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active` stack delivers a **universal +3-8% on all sync-bound Q4_K_M models tested** (Coder-30B, Qwen3.6-35B Q8 included for comparison, REAP-246B). This finding is preserved as a real, deployable lever.

**Submatrix incomplete** (does NOT void the partial wins; just narrows the closure scope):
- libomp comparison: NOT measured. Only libgomp tested. libomp may yield different chunk/affinity/wait behavior on Zen 5.
- Schedule chunks 8 and 16: NOT measured. Only chunks 1 and 4 tested.
- Dense/hybrid model (Qwen3.5/3.6-27B): NOT measured. The +3-8% finding is stated in MoE-Q4_K_M terms but should generalize to dense per process-wide affinity mechanics. Phase 2.6 of the remediation plan adds this.

**Honest closure scope**: "libgomp affinity/wait-policy submatrix exhausted on MoE Q4_K_M with universal +3-8% deployable stack". Broader claim "the runtime/scheduling matrix is exhausted" requires the libomp + chunks 8/16 + dense fills below.

## Why this exists

CPU4 showed one hierarchical barrier variant is net-negative. That does **not** close the sync-class. The remaining low-cost branch is runtime-level tuning:
- `libgomp` vs `libomp`
- schedule policy/chunking
- affinity/bind permutations
- spin/yield behaviors

## Scope

Target models:
- Qwen3-Coder-30B-A3B Q4_K_M
- Qwen3-Next-80B-A3B Q4_K_M
- REAP-246B-A35B Q4_K_M
- gemma-4-26B-A4B-it Q4_K_M

Out of scope:
- algorithmic load balancing (CPU22)
- >150B root-cause attribution counters (CPU24)

## Matrix

1. Runtime: `libgomp`, `libomp`
2. Schedule: `static`, `dynamic`, `guided`
3. Chunk: `1`, `4`, `8`, `16`
4. Affinity: `OMP_PROC_BIND={false,close,spread}`, `OMP_PLACES={cores,threads}`
5. Wait policy: runtime defaults + explicit spin/yield knobs when available

## Protocol requirements

All runs must follow CPU20 protocol:
- canonical baseline rerun first
- process hygiene snapshots
- LD path identity proof
- replicated measurements (`r >= 3` for >2% claims)

## Gates

1. If any config yields >=5% gain on at least 2 of 4 sync-bound models with no quality drift:
   keep runtime profile as deployable tune and feed CPU22 with updated bottleneck shape.
2. If all configs are <=2% or regress:
   mark runtime branch exhausted and move to CPU22 directly.

## Deliverables

- `data/cpu_optimization/<date>-cpu21-openmp-matrix/` artifacts
- table of top 5 configurations by model
- recommended default runtime profile (or explicit "no deployable profile")

## Remediation TODO (Phase 2.1 of closure-inflation remediation plan) — IN PROGRESS

User decision: **install libomp + run chunks 8/16** (full matrix completion).

### Chunks 8/16 — DONE 2026-04-28

Bundle: `data/cpu_optimization/2026-04-28-cpu21-libomp-chunks/`. Key finding:

- **`OMP_SCHEDULE=guided,16` is a real, statistically-significant (+3.6%, 3.5σ) win on Coder-30B Q4_K_M** at 5-rep verification (50.01 ± 0.38 vs 48.28 ± 0.11 CPU21-best baseline).
- **Win is MODEL-SPECIFIC**: Qwen3.6-35B Q8_0 -0.6%, REAP-246B Q4_K_M neutral. Likely mechanism: thinner per-thread row-shard tiles on Coder-30B-A3B (3.3B activated params) benefit from finer-grained guided scheduling; larger MoE and BW-bound classes don't.
- **Recommendation**: do NOT default `OMP_SCHEDULE=guided,16` system-wide. The CPU21-best universal stack remains `OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active` (no `OMP_SCHEDULE`). For Coder-30B-A3B-Instruct workloads specifically, the orchestrator may opt-in `OMP_SCHEDULE=guided,16` per-role.

### libomp comparison — DEFERRED, awaiting user authorization

- `libomp.so.5` runtime IS installed on the host. But LD_PRELOAD substitution from libgomp to libomp FAILS catastrophically (0.35 t/s in smoke; symbol conflicts when both runtimes load).
- Clean libomp build requires `apt install clang-20`. **Sandbox blocked this** (system-package modification needs user authorization). Surfaced; awaiting decision.
- If authorized: ~2-3 hours to build_libomp/ + replicate Phase A/B/C under libomp + write comparison.
- If not: Phase 2.1 closes with the partial scope "libgomp matrix exhausted; libomp explicitly deferred" — narrows the closure language but doesn't void the +3-8% affinity-stack finding or the +3.6% guided,16 finding for Coder-30B.

Phase 2.6 (separate sub-task) will add the dense/hybrid Qwen3.5/3.6-27B affinity-stack confirmation for finding #11 closure.
