# CPU Inference Optimization — Active Backlog

**Purpose**: forward-looking backlog for unimplemented CPU decode/prefill throughput work on local EPYC 9655 Turin hardware.
**Scope**: CPU-only single-instance or aggregate throughput. GPU work lives in [gpu-acceleration-path.md](gpu-acceleration-path.md); routing/orchestration lives in [routing-and-optimization-index.md](routing-and-optimization-index.md); eval/quality lives in [research-evaluation-index.md](research-evaluation-index.md).
**Updated**: 2026-07-05 A7 eval-batch activation smoke pass/rollback, CPU self-draft A/B closeout, and AMD perf-counter preflight unblock.
**History**: pre-compaction detail lives in [../archived/cpu-inference-optimization-index-history-through-2026-06-19.md](../archived/cpu-inference-optimization-index-history-through-2026-06-19.md).

## Start Here

1. Use `/workspace/MEASUREMENT.md` for claim grammar and cache-state labeling.
2. Verify `kernel.numa_balancing` runtime state before benchmarking; do not trust only sysctl files.
3. Treat `--mmap 0 + numactl --interleave=all -t 96 -fa 1` as the cold-cache canonical for throughput claims unless the owning handoff says otherwise.
4. Never claim a new CPU optimization is deployable without CPU20-style repeated measurements and explicit cache-state labels.
5. Coordinate inference windows with [bulk-inference-campaign.md](bulk-inference-campaign.md); K-MEM Tulving, frontdoor/worker G11, and architect G10 are packaged/scored.

## Active Queue

| Priority | Track | Owner handoff | Next action |
|----------|-------|---------------|-------------|
| P0 | Batched decode E1/E2/E3 | [batched-decode-measurement.md](batched-decode-measurement.md) | E2 is decision-grade keep-candidate: single full `qwen36_q8_0 -np 8` is 4.858x faster than current 3-concurrent EvalTower fan-out. Orchestrator `7cb71a4e` landed the default-off `eval_batch_serving` flag and explicit EvalTower eval-batch metadata; orchestrator `e9312a17` added the launcher-only warm `eval_batch_frontdoor` hook on port `18070` plus guarded request-scoped routing; orchestrator `276a1eef` added the guarded preflight/smoke probe; the 2026-07-04 follow-up adds `scripts/benchmark/eval_batch_serving_activation_window.py`, a plan/apply/rollback wrapper for the clean-window activation. The 2026-07-05 activation smoke passed and rolled back cleanly (`status=smoke_passed_rolled_back`), the 2026-07-06 P-BENCH-3 sweep captured the full `qwen36_q8_0` `np={1,2,4,8,16}` curve, and the 2026-07-07 dense-control tail completed at `e1-pbench3-dense-control-iqk-20260707T022917Z` (`43/43` per cell, `0` errors, throughput `20.11 -> 124.62` tasks/hour, p95 `240.9s -> 674.0s`). Representative EvalTower quality/reliability/throughput telemetry is still the remaining gate before any default path change. Do not start E3 solely from the A3B result. |
| P0 | DSA / DeepSeek V3.2 PR #21149 | [llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md), [deepseek-v4-flash-cpu-port.md](deepseek-v4-flash-cpu-port.md), [glm51-reap-cpu-evaluation.md](glm51-reap-cpu-evaluation.md) | Pull/build/smoke only with explicit inference approval; this is the two-models-for-one path for DeepSeek V3.2 and GLM-5.1 DSA. |
| P1 (CLOSED MIXED; monitor only) | Embedded NEXTN same-file `-md` fix | [md-double-load-mtp-fix-brief.md](md-double-load-mtp-fix-brief.md) | Production code fix, live reload, post-reload acceptance evidence, CPU memory-delta evidence, post-reboot audit, throwaway A/B harness, matched quiet-window A/B, and adjacent legacy `LlamaCppBackend` guard are complete. CPU A/B showed embedded no-`-md` saves ~4.27 GiB PSS on the throwaway Qwen server but is ~3.8-4.1% slower than same-file `-md` under `/completion`; do not claim CPU speedup. Keep production no-`-md` for duplicate-load hygiene unless representative eval-fanout telemetry proves a sustained throughput regression. Do not remove Gemma's separate assistant-head `-md`. |
| P1 | MoE-Spec CPU spec-dec integration | [moe-spec-cpu-spec-dec-integration.md](moe-spec-cpu-spec-dec-integration.md) | Run Phase 0 against current stack before any production registry integration; prior pre-production blocker is released, but evidence is not collected. |
| P1 | CPU roofline / AMD counter calibration | [cpu-kernel-env-flags-inventory.md](cpu-kernel-env-flags-inventory.md), [deepseek-v4-flash-cpu-port.md](deepseek-v4-flash-cpu-port.md) | Research `ad9b73a` added the no-inference AMD perf-counter preflight and `bench_canonical.sh --perf` guard; research `515a50b` unblocked it after installing/exposing `linux-perf` in the devcontainer and teaching the preflight to recognize `perf list` alias rows such as `cpu-cycles OR cycles`. Current artifact `data/cpu_optimization/2026-07-03-amd-perf-counter-preflight/summary.{json,md}` is `status=ok`; all canonical Zen 5 events are visible, the smoke probe passed, and `bench_canonical.sh --perf --dry-run` prints the canonical event wrap without inference. Next action is claim-grade perf benches in the appropriate host-health/clean-window protocol. |
| P1 | Shape-specialized GEMV / AVX-512 follow-ons | [cpu-shape-specialized-gemv-decode.md](cpu-shape-specialized-gemv-decode.md) | Keep landed Q8_0 wins; follow-on only with profile-led targets such as Q6_K/Q5_K or expert-dispatch indexing. |
| P1 (CLOSED NEGATIVE; observability tail) | NUMA private node-local weights for shared-mmap quarter roles | [numa-private-weights-quarter-roles.md](numa-private-weights-quarter-roles.md) | Launcher argv plumbing is fixed/tested. The initial shared-mmap quarter-role target set is measured negative under the v6+iqk protocol: `vision_escalation` shared mmap 99.076 t/s vs private `--no-mmap` 65.760, `frontdoor` 56.203 vs 42.428, and `ingest_long_context` 57.528 vs 41.655. Leave all three `no_mmap:false`; no production flip. Remaining useful tail is `affinity_preflight.py` live `numa_maps` observability or a future materially different protocol. |
| P2 | Phase-disaggregated serving | [numa-prefill-decode-disaggregation.md](numa-prefill-decode-disaggregation.md) | Keep only the Phase 0 xGMI KV-transfer falsification gate active; do not build serving code until transfer cost is measured. |
| P2 | Sarathi / MegaBlocks / Tutel ports | [sarathi-serve-cpu-evaluation.md](sarathi-serve-cpu-evaluation.md), [large-moe-expert-parallelism.md](large-moe-expert-parallelism.md) | Reopen only when workload shift or E1/E2 batched-eval regime makes the gate relevant. |

## Closed Principles

- L3aaN is rejected for this single-socket stack unless a new mechanism beats NPS4 under canonical measurement.
- `GGML_NUMA_WEIGHTS=1` is deprecated; use the 3-flag stable stack only for opt-in research.
- NUMA_MIRROR failed its throughput gate on this hardware; reopen only for a future two-socket configuration.
- MAB tree-shape selector and hybrid SSM slot-promotion speculation are closed no-go for the measured Qwen/Gemma-era targets; see archived handoffs before reviving.

## Key References

- [inference-acceleration-index.md](inference-acceleration-index.md) — domain-level acceleration landscape.
- **Cross-cutting (2026-06-20)**: the ~633 GB raid0 free-space gate now bounds the large-MoE candidates tracked in [inference-acceleration-index.md](inference-acceleration-index.md) (GLM-5.2 escapable via IQ2 ~238 GB; Kimi-K2.7 storage-tight even at Q2_K ~373 GB). Not a CPU-kernel-throughput task — pointer only; the storage gate governs whether these GGUFs can land before any CPU bench is even possible.
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

## Progress checklist

- [ ] P0 Batched decode E2/E3: capture EvalTower quality/reliability/throughput telemetry before default path change (batched-decode-measurement.md)
- [ ] P0 DSA / DeepSeek V3.2 PR #21149: pull/build/smoke with inference approval (llama-cpp-dsa-contribution.md)
- [ ] P1 MoE-Spec CPU spec-dec: run Phase 0 against current stack (moe-spec-cpu-spec-dec-integration.md)
- [ ] P1 CPU roofline: run claim-grade AMD perf-counter benches in clean-window protocol (cpu-kernel-env-flags-inventory.md)
- [ ] P1 Shape-specialized GEMV: profile-led Q6_K/Q5_K or expert-dispatch follow-ons (cpu-shape-specialized-gemv-decode.md)
- [ ] P2 Phase-disaggregated serving: keep only xGMI KV-transfer falsification gate active (numa-prefill-decode-disaggregation.md)
