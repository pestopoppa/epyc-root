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
