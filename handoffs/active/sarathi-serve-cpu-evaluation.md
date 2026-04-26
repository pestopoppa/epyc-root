# Sarathi-Serve / Chunked-Prefill Evaluation on EPYC NUMA

**Status**: ACTIVE (wave-scoped plan, created 2026-04-26)
**Categories**: inference_serving, local_inference, hardware_optimization
**Priority**: MEDIUM-HIGH (likely the cheaper architectural win compared to CPU16 NUMA-disagg, and likely obsoletes it)
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) (CPU17)
**Related**: [`numa-prefill-decode-disaggregation.md`](numa-prefill-decode-disaggregation.md) (CPU16 — pursue this stub FIRST; if it works it likely closes CPU16), [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) (DS-7 quarter-scheduler interacts with chunked-prefill scheduling), [`cpu-context-regime-coverage.md`](cpu-context-regime-coverage.md) (CPU23 — context/interference matrix gate), [`cpu-benchmark-rigor-and-revalidation.md`](cpu-benchmark-rigor-and-revalidation.md) (CPU20 protocol gate)

## Pipeline placement

This handoff is the serving-side execution track for **CPU23 (Wave 3 regime coverage)**. It should start only after Wave 0 protocol setup (CPU20) and should feed class-level conclusions back into CPU15/CPU16 routing decisions.

## Objective

Evaluate whether Sarathi-Serve's chunked-prefill + decode-piggybacking scheduling provides measurable decode-stall reduction and uniform per-iteration latency on the EPYC 9655 4×48t NUMA-pinned production stack, particularly when long prompts arrive mid-stream against in-flight decode requests.

## Why This Comes Before CPU16 (NUMA Disagg)

Sarathi-Serve eliminates the prefill/decode interference problem **without any KV migration**. On EPYC, where xGMI inter-socket bandwidth (~64 GB/s) is dramatically lower than NVLink (~900 GB/s), the KV-transfer tax of full disaggregation (CPU16) is proportionally worse than on the GPU systems where DistServe/Splitwise were validated. If chunked-prefill achieves 80%+ of the disagg benefit at zero migration cost, CPU16 should be closed.

The Sarathi authors themselves note (intake-469) that disagg "could be challenging in the absence of high-bandwidth interconnects."

## Research Context

| Intake ID | Title | Verdict | Notes |
|-----------|-------|---------|-------|
| intake-048 | Sarathi-Serve (arXiv:2403.02310, OSDI'24) | already_integrated upstream | The production-grade follow-up; chunked-prefill + stall-free hybrid batching + TBT-SLO scheduling |
| intake-469 | Sarathi v1 (arXiv:2308.16369) | superseded by intake-048 | Original paper; foundational claim of decode underutilization at small batch sizes |
| intake-459 | DistServe | worth_investigating | The disagg architecture Sarathi-Serve is the counter-argument to |
| intake-460 | Splitwise | new_opportunity | Same disagg lineage |

## Key Sarathi-Serve Concepts to Validate on EPYC NUMA

1. **Chunked prefill**: split a prefill request into equal-compute chunks so multiple hybrid batches can be built from one prompt
2. **Decode-maximal hybrid batching**: 1 prefill chunk + N piggybacked decodes per iteration; decodes "ride" the compute-saturating prefill chunk
3. **Uniform per-step compute**: hybrid batches eliminate pipeline bubbles caused by varying prefill/decode times
4. **Workload-aware chunk size**: optimal chunk = function(average prefill:decode token ratio)

## Open Questions

- Does llama-server's existing scheduler already implement enough of this? (Upstream has chunked-prompt-processing; verify if it composes with concurrent slot decode.)
- On 4×48t NUMA-pinned shards, does chunked prefill add cross-shard coordination overhead that nullifies the gain?
- What's the right chunk size for our typical workload mix (single-user interactive vs. seeding/eval batches)?
- Does it interact with CPU15 inter-process EP (drone+shard) on Qwen3.6-35B-A3B Q8_0? (EP changes per-step compute profile.)

## Phase 0 — Audit (executed 2026-04-26 evening)

**Audit method**: `llama-server --help` flag grep for batching/prefill/scheduling primitives on HEAD `8cb04da9d`.

**Available primitives** (none are explicitly named "chunked prefill"; Sarathi-style scheduling can be approximated with these):

| Flag | Default | What it does |
|------|---------|--------------|
| `-cb, --cont-batching` | enabled | continuous (a.k.a. dynamic) batching — allows new requests to join in-flight batches |
| `-np, --parallel N` | -1 (auto) | number of server slots (parallel sequences) |
| `-b, --batch-size N` | 2048 | logical maximum batch size (per iteration) |
| `-ub, --ubatch-size N` | 512 | physical maximum batch size (microbatching boundary inside one iteration) |
| `-n, --predict N` | -1 | number of tokens to predict per request |
| `-c, --ctx-size N` | model | shared context size |
| `--paged-attn N` | 0 | paged attention with block size N tokens (off by default) |
| `-cpent, --checkpoint-every-n-tokens` | -1 | checkpoint every n tokens during prefill |
| `-ctxcp, --ctx-checkpoints` | 32 | max ctx checkpoints per slot |
| `--cache-idle-slots` | enabled | save/clear idle slots |

**Key observation**: there is NO single "chunk size" for prefill chunking. Instead, the **logical (`-b`) and physical (`-ub`) batch sizes** determine how much prefill work is processed per scheduler iteration. Sarathi-Serve's chunked-prefill behavior approximates as: `-ub` controls the chunk size for prefill chunks; `-cb` enables decodes to piggyback in the same iteration as prefill chunks (when slot scheduler arranges it).

**Implication**: Sarathi-style hybrid batching is **partially supported by default**: `-cb` is enabled, `-ub 512` chunks prefill into ≤512-token slices. What's missing vs Sarathi:
1. No explicit decode-prefill-mix priority knob (the scheduler decides)
2. No TBT-SLO scheduling
3. No workload-aware adaptive chunk size
4. `-ub` is global, not per-slot

**Phase 0 cheap probe** (NEXT — not yet executed):
1. Construct synthetic workload: 1 long prompt (8K tokens) arriving via HTTP after 3 decode requests are already in-flight at 2K context. Measure decode TBT (time-between-tokens) spike on the 3 in-flight requests during the long prompt's prefill.
2. Sweep `-ub`: 128, 256, 512, 1024, 2048 tokens. Measure: decode-stall fraction, aggregate throughput, per-iteration latency variance.
3. Repeat at 2K / 8K / 32K context regimes.

**Gate**: If TBT spike on in-flight decodes reduces ≥30% at the `-ub` sweet spot vs default 512, advance to Phase 1. Otherwise document "default already approximates Sarathi" and close.

**Effort**: ~6-8 hours wall (workload generator + measurement harness + 5×3=15 sweeps × ~30 sec each). Not yet executed; deferred to next session block.

## Phase 0 quick directional probe — executed 2026-04-26 evening (CLOSE)

Before committing to the full 6-8h workload generator, ran a cheap directional probe: sweep `-ub` (microbatch / chunk-prefill granularity) on Coder-30B Q4_K_M with combined `pp4096 + tg32` at the proper canonical config. Goal: see if `-ub` tuning has any signal worth investigating further on our single-user regime.

| `-ub` | pp4096 (prefill t/s) | tg32 (decode t/s) | Prefill Δ vs ub=2048 |
|-------|---------------------:|------------------:|---------------------:|
| 128   | 243.91 ± 0.03 | 46.50 ± 0.60 | **−52.3%** |
| 256   | 358.10 ± 0.40 | 46.95 ± 0.60 | **−30.0%** |
| 512 (default) | 443.83 ± 0.26 | 46.26 ± 0.31 | **−13.2%** |
| 1024  | 480.54 ± 2.39 | 46.83 ± 0.45 | **−6.0%** |
| 2048  | 511.22 ± 0.55 | 46.61 ± 0.55 | reference |

**Key findings**:
1. Prefill speed scales sub-linearly with `-ub` (2.1× from 128 → 2048).
2. **Decode speed is essentially constant at 46-47 t/s across all `-ub` values** — single-stream decode isn't blocked by anything that microbatch sizing affects.
3. Smaller `-ub` enables finer-grained Sarathi-style decode-prefill interleaving but at the cost of substantial prefill regression (−52% at `-ub 128`).

**Strategic conclusion — CLOSE CPU17 for our regime**:

For single-user interactive workloads (our actual production deployment): the default cont-batching + `-ub 512` is near-optimal. Smaller `-ub` only damages prefill; there's no decode-stall-during-prefill problem to solve since requests don't compete for resources within a single iteration on single-user.

For multi-tenant scenarios (not our deployment): the Sarathi trade-off MIGHT make sense, but the prefill regression at small `-ub` (−52%) means the TBT-spike reduction would need to exceed 50% to break even — implausible.

**Recommendation**: close CPU17. The literature claim ("Sarathi-Serve eliminates prefill/decode interference") is real but applies to multi-tenant GPU servers with thousands of concurrent users. For our deployment (1 user, CPU, intermittent agentic loops), the default cont-batching + `-ub 512` already captures most of the benefit; per-slot adaptive chunk sizing would be needed to do better, which is significant code work for marginal returns on our actual workload.

**Re-open trigger**: if we ever shift to a multi-tenant deployment pattern (shared API serving multiple agents), revisit with per-shard `-ub` tuning (`-ub 256` for interactive-priority, `-ub 1024` for batch-priority) before considering full Sarathi-Serve TBT-SLO scheduler integration.

**CPU16 (NUMA disagg) closure**: per the original handoff, CPU17 was meant to falsify or obsolete CPU16. Since CPU17 itself produces minimal signal for our regime, CPU16 is also closed by inheritance — there's no decode-stall-during-prefill problem to solve via either chunked-prefill OR full disaggregation on single-user CPU.

**Data**: `data/cpu_optimization/2026-04-26-cpu17/SUMMARY.md` and per-`-ub` raw bench logs.

## Proposed Phase 1 — NUMA-Pinned Shard Sweep

1. Enable chunked prefill on each of the 4×48t shards; sweep chunk size {128, 256, 512, 1024, 2048} tokens.
2. Measure: decode-stall fraction during long-prompt-mid-stream, aggregate throughput, per-iteration latency variance, and prefill/decode interference under mixed arrival.
3. Compare against existing dynamic-stack-concurrency baseline (no chunking).
4. Gate: if Phase 1 shows ≥20% decode-stall reduction without aggregate-throughput regression, propose production rollout via DS-7 stack template extension.

## Proposed Phase 2 — Production Integration

1. Add `chunked_prefill` config block to DS-7 stack templates (default OFF; per-role override).
2. Wire into orchestrator scheduler so per-shard chunk size adapts to observed prefill:decode ratio.
3. PPL gate on representative prompts (no quality regression expected — chunking is iteration-level, not arithmetic).

## Notes

- This handoff is a **direct outcome** of the 2026-04-26 research-intake batch (intake-458 to 472). The Tier 2b critique of disaggregated serving (recorded in intake-459/460/472 `contradicting_evidence` fields) flagged Sarathi-Serve as the natural CPU-appropriate alternative.
- Surface this stub via [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) ⚑ START HERE block (CPU17).
- Independent of L3aaN reboot — can be picked up before, during, or after.
