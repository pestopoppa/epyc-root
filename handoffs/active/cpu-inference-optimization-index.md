# CPU Inference Optimization — Active Backlog

**Purpose**: forward-looking backlog for unimplemented CPU decode/prefill throughput work on local EPYC 9655 Turin hardware.
**Scope**: CPU-only single-instance or aggregate throughput. GPU work lives in [gpu-acceleration-path.md](gpu-acceleration-path.md); routing/orchestration lives in [routing-and-optimization-index.md](routing-and-optimization-index.md); eval/quality lives in [research-evaluation-index.md](research-evaluation-index.md).
**Updated**: 2026-07-14 backlog ROI audit — added post-reboot canonical decode bench P0, re-led GEMV row with the fusion A/B, re-gated MoE-Spec, DSA to MED with snapshot-refresh precondition, Sarathi converted to E4 gate-evaluation, and relocated the two CLOSED rows out of the Active Queue. (Prior: 2026-07-05 A7 eval-batch activation smoke pass/rollback, CPU self-draft A/B closeout, and AMD perf-counter preflight unblock.)
**History**: pre-compaction detail lives in [../archived/cpu-inference-optimization-index-history-through-2026-06-19.md](../archived/cpu-inference-optimization-index-history-through-2026-06-19.md).

## Start Here

1. Use `/workspace/MEASUREMENT.md` for claim grammar and cache-state labeling.
2. Verify `kernel.numa_balancing` runtime state before benchmarking; do not trust only sysctl files.
3. Treat `--mmap 0 + numactl --interleave=all -t 96 -fa 1` as the cold-cache canonical for throughput claims unless the owning handoff says otherwise.
4. Never claim a new CPU optimization is deployable without CPU20-style repeated measurements and explicit cache-state labels.
5. Coordinate inference windows with [bulk-inference-campaign.md](bulk-inference-campaign.md); K-MEM Tulving, frontdoor/worker G11, and architect G10 are packaged/scored.

## Active Queue

**2026-07-18 reframe (v7 lever audit).** CPU **decode** is bandwidth-exhausted, measured not
asserted (Qwen3.6-27B Q8 decode @96t = 0.17 IPC, **96.6% of cycles memory-stalled**; `vec_dot`
72% / `ggml_barrier` 22%). Every decode-side SIMD/ALU lever is dead on that roofline (VNNI,
8×8 repack at multi-thread, Q6_K/Q5_K default-ON, shape-specialized GEMV catalog, manual
prefetch — see [../archived/cpu-inference-optimization-index-history-through-2026-06-19.md](../archived/cpu-inference-optimization-index-history-through-2026-06-19.md)
and the GEMV handoff). **The ONLY live CPU decode lever is Q8_0 barrier-count operator/graph
fusion** (P1 row below; +2.6% measured → +10–15% graph-rewrite → +72% absolute ceiling if BW-util
matches dense). **The untapped large-model regime is prefill-compute** — prefill is compute-bound
(not BW-killed) and dominates GLM-5.2 / 122B-architect long-context turns → new track
[cpu-prefill-compute-large-models.md](cpu-prefill-compute-large-models.md) (profile-first; PC-0).

| Priority | Track | Owner handoff | Next action |
|----------|-------|---------------|-------------|
| P0 | Clean post-reboot canonical decode bench | [v6-iqk-promotion.md](v6-iqk-promotion.md) (Phase J) | The only formal gate left on the v6+iqk cutover. Operator reboot gate — waits on an operator-owned host reboot, then a clean-window canonical decode bench per MEASUREMENT.md. Should share the reboot/quiet window with the claim-grade AMD perf-counter benches (CPU roofline row below) and the Q8_0 fusion A/B (GEMV row below); see master-handoff-index §A00 OP-2 for the shared-window batching. |
| P0 | Batched decode E1/E2/E3 | [batched-decode-measurement.md](batched-decode-measurement.md) | E2 is decision-grade keep-candidate: single full `qwen36_q8_0 -np 8` is 4.858x faster than current 3-concurrent EvalTower fan-out. Orchestrator `7cb71a4e` landed the default-off `eval_batch_serving` flag and explicit EvalTower eval-batch metadata; orchestrator `e9312a17` added the launcher-only warm `eval_batch_frontdoor` hook on port `18070` plus guarded request-scoped routing; orchestrator `276a1eef` added the guarded preflight/smoke probe; the 2026-07-04 follow-up adds `scripts/benchmark/eval_batch_serving_activation_window.py`, a plan/apply/rollback wrapper for the clean-window activation. The 2026-07-05 activation smoke passed and rolled back cleanly (`status=smoke_passed_rolled_back`), the 2026-07-06 P-BENCH-3 sweep captured the full `qwen36_q8_0` `np={1,2,4,8,16}` curve, and the 2026-07-07 dense-control tail completed at `e1-pbench3-dense-control-iqk-20260707T022917Z` (`43/43` per cell, `0` errors, throughput `20.11 -> 124.62` tasks/hour, p95 `240.9s -> 674.0s`). Representative EvalTower quality/reliability/throughput telemetry is still the remaining gate before any default path change; the packaged EvalTower window runner (orchestrator `8d36aa1e`, `scripts/benchmark/eval_batch_serving_evaltower_window.py`) is the execution path for that gate. With dense-control E1 complete (2026-07-07, `e1-pbench3-dense-control-iqk-20260707T022917Z`): (a) the E3 go/no-go per-thread-BW headroom analysis is decision-actionable NOW from existing data (zero inference), and (b) waypoint E4's doc-only CPU17 chunked-prefill / CPU18 MegaBlocks re-promotion-or-re-close decisions are actionable. Do not start E3 solely from the A3B result. |
| MED (was P0; aligned to master index 2026-07-14) | DSA / DeepSeek V3.2 PR #21149 | [llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md), [deepseek-v4-flash-cpu-port.md](deepseek-v4-flash-cpu-port.md), [glm51-reap-cpu-evaluation.md](glm51-reap-cpu-evaluation.md) | Precondition: refresh the PR #21149 snapshot first — the owning snapshot is dated 2026-04-29 and the PR has been dormant since 2026-05-28. Then pull/build/smoke only with explicit inference approval; this is the two-models-for-one path for DeepSeek V3.2 and GLM-5.1 DSA. Priority aligned to MED per master index (DSA D1 smoke queued at MED; P0 was unsupported). |
| P1 (GATED) | MoE-Spec CPU spec-dec integration | [moe-spec-cpu-spec-dec-integration.md](moe-spec-cpu-spec-dec-integration.md) | Re-tagged GATED: the 2026-07-04 owning-handoff refresh supersedes the earlier "blocker released" framing — mechanism is proven but there is NO consumer (REAP role removed, Coder B=64 not robust, frontdoor/architect run v6 embedded MTP self-draft). Reopen chain = fable5 G1/N5 live self-draft measurement + a live MoE verifier path. 2026-07-14 audit note: a reopen ASSESSMENT is now decision-ready using the 2026-07-03 live-α report (`mtp_acceptance_report_20260703T114323Z`: frontdoor α=0.6582, worker α=0.8256 — embedded-MTP verification batches ARE live consumer candidates); the assessment is cheap (zero inference) and decides re-sweep vs formal close. |
| P1 | CPU roofline / AMD counter calibration | [cpu-kernel-env-flags-inventory.md](cpu-kernel-env-flags-inventory.md), [deepseek-v4-flash-cpu-port.md](deepseek-v4-flash-cpu-port.md) | Research `ad9b73a` added the no-inference AMD perf-counter preflight and `bench_canonical.sh --perf` guard; research `515a50b` unblocked it after installing/exposing `linux-perf` in the devcontainer and teaching the preflight to recognize `perf list` alias rows such as `cpu-cycles OR cycles`. Current artifact `data/cpu_optimization/2026-07-03-amd-perf-counter-preflight/summary.{json,md}` is `status=ok`; all canonical Zen 5 events are visible, the smoke probe passed, and `bench_canonical.sh --perf --dry-run` prints the canonical event wrap without inference. Next action is claim-grade perf benches in the appropriate host-health/clean-window protocol. |
| P1 | Shape-specialized GEMV / AVX-512 follow-ons | [cpu-shape-specialized-gemv-decode.md](cpu-shape-specialized-gemv-decode.md) | Lead with the frontdoor Q8_0 barrier-count fusion A/B (fuse expert gate+up, attn QKV cluster; cheapest test = llama-bench tg128 fusion on/off in one window; est +10-15% decode, one cluster already measured +2.6%; **absolute ceiling +72% (4.42→7.6 t/s) if BW-util matches dense**; re-elevated 2026-07-03 by findings-05 as the #1 CPU decode lever; **v7-audit LANE B B1 — bundle into the OP-2 quiet window**). Keep landed Q8_0 wins. Q6_K/Q5_K SIMD follow-ons are explicitly DEPRIORITIZED per the roofline finding. |
| P1 (NEW) | Prefill-compute for large models | [cpu-prefill-compute-large-models.md](cpu-prefill-compute-large-models.md) | Decode is BW-exhausted but prefill is compute-bound and dominates GLM/architect long-context. Start with **PC-0 profile-first** (`perf record` prefill on a long-context large-model shape; confirm compute-bound before any kernel) — bundle the perf-record into the OP-2 window. Candidate levers: prefill Q8→f16 convert-skip (~+15%), high-batch norm-tail fusion, per-SSM-block fusion. |
| P2 | Phase-disaggregated serving | [numa-prefill-decode-disaggregation.md](numa-prefill-decode-disaggregation.md) | Keep only the Phase 0 xGMI KV-transfer falsification gate active; do not build serving code until transfer cost is measured. |
| P2 | Sarathi / MegaBlocks / Tutel ports — gate evaluation | [sarathi-serve-cpu-evaluation.md](sarathi-serve-cpu-evaluation.md), [large-moe-expert-parallelism.md](large-moe-expert-parallelism.md) | The reopen gate has arguably FIRED: E2 is a keep-candidate 4.858x eval-batch regime since 2026-07-03, and the sarathi handoff itself names exactly this trigger. Run the explicit gate evaluation — decide reopen-vs-re-close citing E1/E2 evidence. This is batched-decode waypoint E4 (doc-only, zero inference). |

## Closed Rows (relocated from Active Queue 2026-07-14, per outstanding-TODOs-only convention)

- **Embedded NEXTN same-file `-md` fix — CLOSED MIXED, monitor only** ([md-double-load-mtp-fix-brief.md](../completed/md-double-load-mtp-fix-brief.md)): production code fix, live reload, post-reload acceptance evidence, CPU memory-delta evidence, post-reboot audit, throwaway A/B harness, matched quiet-window A/B, and adjacent legacy `LlamaCppBackend` guard are complete. CPU A/B showed embedded no-`-md` saves ~4.27 GiB PSS on the throwaway Qwen server but is ~3.8-4.1% slower than same-file `-md` under `/completion`; do not claim CPU speedup. Keep production no-`-md` for duplicate-load hygiene unless representative eval-fanout telemetry proves a sustained throughput regression. Do not remove Gemma's separate assistant-head `-md`.
- **NUMA private node-local weights for shared-mmap quarter roles (N12) — CLOSED NEGATIVE, observability tail** ([numa-private-weights-quarter-roles.md](../completed/numa-private-weights-quarter-roles.md)): launcher argv plumbing is fixed/tested. The initial shared-mmap quarter-role target set is measured negative under the v6+iqk protocol: `vision_escalation` shared mmap 99.076 t/s vs private `--no-mmap` 65.760, `frontdoor` 56.203 vs 42.428, and `ingest_long_context` 57.528 vs 41.655. Leave all three `no_mmap:false`; no production flip. Remaining useful tail is `affinity_preflight.py` live `numa_maps` observability or a future materially different protocol.

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

- [ ] P0 Post-reboot canonical decode bench: run clean-window canonical decode bench after operator reboot — the last formal v6+iqk cutover gate; share the reboot/quiet window with the AMD perf-counter benches and the Q8_0 fusion A/B (v6-iqk-promotion.md Phase J; master-index §A00 OP-2)
- [ ] P0 Batched decode E2/E3: capture EvalTower quality/reliability/throughput telemetry before default path change, via `eval_batch_serving_evaltower_window.py` (batched-decode-measurement.md)
- [x] P0 Batched decode E3 go/no-go: E3 no-go/closed for now. Existing E1/E2 evidence shows a serving/topology win, while the later CPU roofline says decode-side SIMD/ALU work is BW-killed; do not write the 8x8 GEMM SIMD body. ✅ 2026-07-18
- [x] P0 Batched decode waypoint E4 (doc-only): CPU17/Sarathi reopens only to the measurement gate for long-prompt mid-stream TBT; CPU18/MegaBlocks remains gated pending a padding/capacity-factor cost profile. ✅ 2026-07-18
- [ ] MED DSA / DeepSeek V3.2 PR #21149: refresh PR snapshot (owning snapshot 2026-04-29, PR dormant since 2026-05-28), then pull/build/smoke with inference approval (llama-cpp-dsa-contribution.md)
- [x] P1 MoE-Spec CPU spec-dec (GATED): zero-inference assessment completed; reopen for a current live-MTP MoE verifier B-sweep, but keep registry integration blocked until current speed/acceptance/quality evidence exists. ✅ 2026-07-18
- [ ] P1 CPU roofline: run claim-grade AMD perf-counter benches in clean-window protocol (cpu-kernel-env-flags-inventory.md)
- [ ] P1 Shape-specialized GEMV: run the frontdoor Q8_0 barrier-count fusion A/B (llama-bench tg128 fusion on/off, one window) — Q6_K/Q5_K SIMD follow-ons deprioritized per roofline finding (cpu-shape-specialized-gemv-decode.md)
- [ ] P2 Phase-disaggregated serving: keep only xGMI KV-transfer falsification gate active (numa-prefill-decode-disaggregation.md)
- [ ] P1 (NEW) Prefill-compute for large models: run PC-0 profile-first premise check (`perf record` long-context prefill; confirm compute-bound) before any kernel (cpu-prefill-compute-large-models.md)
