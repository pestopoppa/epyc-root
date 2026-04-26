# Sarathi-Serve / Chunked-Prefill Evaluation on EPYC NUMA

**Status**: stub (created 2026-04-26 via research intake batch)
**Categories**: inference_serving, local_inference, hardware_optimization
**Priority**: MEDIUM-HIGH (likely the cheaper architectural win compared to CPU16 NUMA-disagg, and likely obsoletes it)
**Workstream**: Inference Acceleration → CPU Optimization
**Parent index**: [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) (CPU17)
**Related**: [`numa-prefill-decode-disaggregation.md`](numa-prefill-decode-disaggregation.md) (CPU16 — pursue this stub FIRST; if it works it likely closes CPU16), [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) (DS-7 quarter-scheduler interacts with chunked-prefill scheduling)

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

## Proposed Phase 0 — Cheap Probe (no code)

1. Audit existing llama-server flags for chunked-prefill support: `--chunk-size`, `--parallel-prompt`, `--cont-batching`, etc. Document current defaults and what's exposed.
2. Construct a synthetic workload: 1 long prompt (16k tokens) arriving mid-stream against 3 in-flight decodes. Measure TBT spike on the in-flight decodes with/without chunked prefill.
3. If TBT spike reduction ≥30% at the chunk size sweet spot, advance to Phase 1.

## Proposed Phase 1 — NUMA-Pinned Shard Sweep

1. Enable chunked prefill on each of the 4×48t shards; sweep chunk size {128, 256, 512, 1024, 2048} tokens.
2. Measure: decode-stall fraction during long-prompt-mid-stream, aggregate throughput, per-iteration latency variance.
3. Compare against existing dynamic-stack-concurrency baseline (no chunking).
4. Gate: if Phase 1 shows ≥20% decode-stall reduction without aggregate-throughput regression, propose production rollout via DS-7 stack template extension.

## Proposed Phase 2 — Production Integration

1. Add `chunked_prefill` config block to DS-7 stack templates (default OFF; per-role override).
2. Wire into orchestrator scheduler so per-shard chunk size adapts to observed prefill:decode ratio.
3. PPL gate on representative prompts (no quality regression expected — chunking is iteration-level, not arithmetic).

## Notes

- This stub is a **direct outcome** of the 2026-04-26 research-intake batch (intake-458 to 472). The Tier 2b critique of disaggregated serving (recorded in intake-459/460/472 `contradicting_evidence` fields) flagged Sarathi-Serve as the natural CPU-appropriate alternative.
- Surface this stub via [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) ⚑ START HERE block (CPU17).
- Independent of L3aaN reboot — can be picked up before, during, or after.
