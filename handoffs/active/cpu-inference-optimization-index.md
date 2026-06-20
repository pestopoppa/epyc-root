# CPU Inference Optimization — Active Backlog

**Purpose**: forward-looking backlog for unimplemented CPU decode/prefill throughput work on local EPYC 9655 Turin hardware.
**Scope**: CPU-only single-instance or aggregate throughput. GPU work lives in [gpu-acceleration-path.md](gpu-acceleration-path.md); routing/orchestration lives in [routing-and-optimization-index.md](routing-and-optimization-index.md); eval/quality lives in [research-evaluation-index.md](research-evaluation-index.md).
**Updated**: 2026-06-20 active-lane refresh.
**History**: pre-compaction detail lives in [../archived/cpu-inference-optimization-index-history-through-2026-06-19.md](../archived/cpu-inference-optimization-index-history-through-2026-06-19.md).

## Start Here

1. Use `/workspace/MEASUREMENT.md` for claim grammar and cache-state labeling.
2. Verify `kernel.numa_balancing` runtime state before benchmarking; do not trust only sysctl files.
3. Treat `--mmap 0 + numactl --interleave=all -t 96 -fa 1` as the cold-cache canonical for throughput claims unless the owning handoff says otherwise.
4. Never claim a new CPU optimization is deployable without CPU20-style repeated measurements and explicit cache-state labels.
5. Coordinate inference windows with [bulk-inference-campaign.md](bulk-inference-campaign.md); K-MEM Tulving and frontdoor/worker G11 are packaged, and the next throughput-sensitive factual-risk lane is architect G10 when `architect_general` is idle/clean.

## Active Queue

| Priority | Track | Owner handoff | Next action |
|----------|-------|---------------|-------------|
| P0 | Batched decode E1/E2/E3 | [batched-decode-measurement.md](batched-decode-measurement.md) | Run decision-grade E1 CPU14 `-np` sweep and E2 single-instance eval A/B in a reboot/host-health quiet window; only start E3 8x8 GEMM SIMD if E1/E2 prove the need. |
| P0 | DSA / DeepSeek V3.2 PR #21149 | [llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md), [deepseek-v4-flash-cpu-port.md](deepseek-v4-flash-cpu-port.md), [glm51-reap-cpu-evaluation.md](glm51-reap-cpu-evaluation.md) | Pull/build/smoke only with explicit inference approval; this is the two-models-for-one path for DeepSeek V3.2 and GLM-5.1 DSA. |
| P1 | MoE-Spec CPU spec-dec integration | [moe-spec-cpu-spec-dec-integration.md](moe-spec-cpu-spec-dec-integration.md) | Run Phase 0 against current stack before any production registry integration; prior pre-production blocker is released, but evidence is not collected. |
| P1 | CPU roofline / AMD counter calibration | [cpu-kernel-env-flags-inventory.md](cpu-kernel-env-flags-inventory.md), [deepseek-v4-flash-cpu-port.md](deepseek-v4-flash-cpu-port.md) | Complete Phase 0 AMD counter calibration before any Phase 2 inference run; the old Intel-event draft is invalid on this host. |
| P1 | Shape-specialized GEMV / AVX-512 follow-ons | [cpu-shape-specialized-gemv-decode.md](cpu-shape-specialized-gemv-decode.md) | Keep landed Q8_0 wins; follow-on only with profile-led targets such as Q6_K/Q5_K or expert-dispatch indexing. |
| P2 | Phase-disaggregated serving | [numa-prefill-decode-disaggregation.md](numa-prefill-decode-disaggregation.md) | Keep only the Phase 0 xGMI KV-transfer falsification gate active; do not build serving code until transfer cost is measured. |
| P2 | Sarathi / MegaBlocks / Tutel ports | [sarathi-serve-cpu-evaluation.md](sarathi-serve-cpu-evaluation.md), [large-moe-expert-parallelism.md](large-moe-expert-parallelism.md) | Reopen only when workload shift or E1/E2 batched-eval regime makes the gate relevant. |

## Closed Principles

- L3aaN is rejected for this single-socket stack unless a new mechanism beats NPS4 under canonical measurement.
- `GGML_NUMA_WEIGHTS=1` is deprecated; use the 3-flag stable stack only for opt-in research.
- NUMA_MIRROR failed its throughput gate on this hardware; reopen only for a future two-socket configuration.
- MAB tree-shape selector and hybrid SSM slot-promotion speculation are closed no-go for the measured Qwen/Gemma-era targets; see archived handoffs before reviving.

## Key References

- [inference-acceleration-index.md](inference-acceleration-index.md) — domain-level acceleration landscape.
- [../completed/cpu-benchmark-rigor-and-revalidation.md](../completed/cpu-benchmark-rigor-and-revalidation.md) — historical CPU20 protocol record; living protocol is `/workspace/MEASUREMENT.md`.
- [../completed/cpu-optimization-thesis-pause-2026-04-26.md](../completed/cpu-optimization-thesis-pause-2026-04-26.md) — methodology/conclusion correction ledger.
- [../completed/numa-mirror-integration.md](../completed/numa-mirror-integration.md) — NUMA_MIRROR closure.
- [../completed/hybrid-ssm-slot-promotion-spec-dec.md](../completed/hybrid-ssm-slot-promotion-spec-dec.md) and [../completed/mab-tree-shape-selector.md](../completed/mab-tree-shape-selector.md) — closed spec-dec reopeners.

## Reporting

After completing a CPU queue item:

1. Update the owning handoff first.
2. Update this index only when priority, gate, or next-action routing changes.
3. Append `progress/YYYY-MM/YYYY-MM-DD.md` with measurement protocol, cache state, hardware state, and commit/artifact IDs.
4. If the work changes the stack, update [routing-and-optimization-index.md](routing-and-optimization-index.md) and the relevant stack-change handoff.
