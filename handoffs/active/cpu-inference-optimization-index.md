# CPU Inference Optimization — Active Backlog

**Purpose**: forward-looking backlog for unimplemented CPU decode/prefill throughput work on local EPYC 9655 Turin hardware.
**Scope**: CPU-only single-instance or aggregate throughput. GPU work lives in [gpu-acceleration-path.md](gpu-acceleration-path.md); routing/orchestration lives in [routing-and-optimization-index.md](routing-and-optimization-index.md); eval/quality lives in [research-evaluation-index.md](research-evaluation-index.md).
**Updated**: 2026-07-19 OP-2 live v6+iqk verification and clean canonical CPU gate COMPLETE:
live preflight/role smokes passed and P-BENCH-1 frontdoor Q8 tg128 recorded; B1 was skipped
as not staged and B4 closed no-go. Stack servers and AutoPilot remain stopped by the runner.
Prior: 2026-07-19 OP-2 gate was corrected to bench-clean quiet-window execution: reboot
only if preflight flags multi-day throttle, with no production-v6 edits/builds, full-stack
reload, or AutoPilot restart. Prior: 2026-07-18 B7 prefill-compute scoping closed; track is now
profile-gated on PC-0 with a concrete 122B architect `bench_canonical.sh`
`p8192/n1` perf-stat + `perf record` first cell. Prior: 2026-07-14 backlog ROI
audit added the canonical decode bench P0, re-led GEMV row with the
fusion A/B, re-gated MoE-Spec, DSA to MED with snapshot-refresh precondition,
Sarathi converted to E4 gate-evaluation, and relocated the two CLOSED rows out
of the Active Queue.
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
(not BW-killed) and dominates GLM-5.2 / 122B-architect long-context turns → scoped track
[cpu-prefill-compute-large-models.md](cpu-prefill-compute-large-models.md) (B7 scoping closed;
PC-0 operator-window profile gate remains open).

| Priority | Track | Owner handoff | Next action |
|----------|-------|---------------|-------------|
| P0 | Bench-clean canonical decode bench | [v6-iqk-promotion.md](../completed/v6-iqk-promotion.md) (Phase J) | **COMPLETE 2026-07-19**: live v6+iqk preflight PASS, role smokes 6/6, process blockers 0, and clean P-BENCH-1 frontdoor Q8 tg128 `avg_ts=12.442712`, `stddev_ts=0.010877`, build `91745611f`/`9774`, `n=10`, `96` threads, with `GGML_IQK=1` and iqk activation stderr. Strict sentinel `avg_ts=19.1828`, warnings/blockers empty. B1 skipped (not staged); B4 closed no-go. Evidence: research `038fb35`, report `docs/data/op2_canonical_bench_window_20260719_live5.md`, raw root `data/op2_canonical_bench_window/op2-canonical-bench-window-20260719-live5`. |
| P0 | Batched decode E1/E2/E3 | [batched-decode-measurement.md](batched-decode-measurement.md) | E2 is decision-grade keep-candidate: single full `qwen36_q8_0 -np 8` is 4.858x faster than current 3-concurrent EvalTower fan-out. Orchestrator `7cb71a4e` landed the default-off `eval_batch_serving` flag and explicit EvalTower eval-batch metadata; orchestrator `e9312a17` added the launcher-only warm `eval_batch_frontdoor` hook on port `18070` plus guarded request-scoped routing; orchestrator `276a1eef` added the guarded preflight/smoke probe; the 2026-07-04 follow-up adds `scripts/benchmark/eval_batch_serving_activation_window.py`, a plan/apply/rollback wrapper for the clean-window activation. The 2026-07-05 activation smoke passed and rolled back cleanly (`status=smoke_passed_rolled_back`), the 2026-07-06 P-BENCH-3 sweep captured the full `qwen36_q8_0` `np={1,2,4,8,16}` curve, and the 2026-07-07 dense-control tail completed at `e1-pbench3-dense-control-iqk-20260707T022917Z` (`43/43` per cell, `0` errors, throughput `20.11 -> 124.62` tasks/hour, p95 `240.9s -> 674.0s`). Representative EvalTower quality/reliability/throughput telemetry is still the remaining gate before any default path change; the packaged EvalTower window runner (orchestrator `8d36aa1e`, `scripts/benchmark/eval_batch_serving_evaltower_window.py`) is the execution path for that gate. With dense-control E1 complete (2026-07-07, `e1-pbench3-dense-control-iqk-20260707T022917Z`): (a) the E3 go/no-go per-thread-BW headroom analysis is decision-actionable NOW from existing data (zero inference), and (b) waypoint E4's doc-only CPU17 chunked-prefill / CPU18 MegaBlocks re-promotion-or-re-close decisions are actionable. Do not start E3 solely from the A3B result. |
| MED (was P0; aligned to master index 2026-07-14) | DSA / DeepSeek V3.2 legacy PR #21149 path | [llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md), [deepseek-v4-flash-cpu-port.md](deepseek-v4-flash-cpu-port.md), [glm51-reap-cpu-evaluation.md](glm51-reap-cpu-evaluation.md) | This row no longer gates GLM-5.2: generic DSA landed via upstream #23346 and experimental v7 wires GLM-5.2 `glm-dsa` cache/runtime. Keep PR #21149 only as a legacy DeepSeek V3.2 / GLM-5.1 snapshot question; refresh the dormant 2026-04-29 snapshot before any pull/build/smoke, and run only with explicit inference approval. |
| P1 (GATED) | MoE-Spec CPU spec-dec integration | [moe-spec-cpu-spec-dec-integration.md](moe-spec-cpu-spec-dec-integration.md) | Zero-inference assessment closed 2026-07-18: the 2026-07-03 live-α report proves current verification-batch consumers exist (`frontdoor` α=0.6582, `worker_general` α=0.8256, `architect_general` α=0.6854, failed MTP roles `[]`). Reopen only to a current live-MTP MoE verifier B-sweep with speed, acceptance, and quality/bit-exact guard. Registry integration remains blocked until that sweep exists. |
| P1 | CPU roofline / AMD counter calibration | [cpu-kernel-env-flags-inventory.md](cpu-kernel-env-flags-inventory.md), [deepseek-v4-flash-cpu-port.md](deepseek-v4-flash-cpu-port.md) | Research `ad9b73a` added the no-inference AMD perf-counter preflight and `bench_canonical.sh --perf` guard; research `515a50b` unblocked it after installing/exposing `linux-perf` in the devcontainer and teaching the preflight to recognize `perf list` alias rows such as `cpu-cycles OR cycles`. Current artifact `data/cpu_optimization/2026-07-03-amd-perf-counter-preflight/summary.{json,md}` is `status=ok`; all canonical Zen 5 events are visible, the smoke probe passed, and `bench_canonical.sh --perf --dry-run` prints the canonical event wrap without inference. Next action is claim-grade perf benches in the appropriate host-health/clean-window protocol. |
| P1 | Shape-specialized GEMV / AVX-512 follow-ons | [cpu-shape-specialized-gemv-decode.md](cpu-shape-specialized-gemv-decode.md) | Lead with the frontdoor Q8_0 barrier-count fusion A/B (fuse expert gate+up, attn QKV cluster; cheapest test = llama-bench tg128 fusion on/off in one window; est +10-15% decode, one cluster already measured +2.6%; **absolute ceiling +72% (4.42→7.6 t/s) if BW-util matches dense**; re-elevated 2026-07-03 by findings-05 as the #1 CPU decode lever; **v7-audit LANE B B1 — bundle into the OP-2 quiet window**). Keep landed Q8_0 wins. Q6_K/Q5_K SIMD follow-ons are explicitly DEPRIORITIZED per the roofline finding. |
| P1 | Prefill-compute for large models | [cpu-prefill-compute-large-models.md](cpu-prefill-compute-large-models.md) | B7 design/scoping is closed; PC-1 sized the prompt-wall fraction and PC-2 scoped fusion targets. A first CPU-only `perf record` artifact now exists (`p8192/n1`, `107.621 t/s`, max RSS `73.55 GiB`) but is observation-only. Remaining gate is still **PC-0 profile-first** in an operator window: add paired `bench_canonical.sh -p 8192 -n 1 -r 3 --perf` / `perf stat` counters plus `perf record`, then classify compute-bound vs BW-bound before any kernel. Candidate levers stay blocked: prefill Q8→f16 convert-skip, high-batch norm-tail fusion, and per-SSM-block fusion. |
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

- [x] P0 Bench-clean canonical decode bench: live v6+iqk preflight and 6/6 role smokes passed; strict clean sentinel was `status=ok`, then P-BENCH-1 frontdoor Q8 tg128 completed with `avg_ts=12.442712` / `stddev_ts=0.010877` (`n=10`, `96` threads, build `91745611f`/`9774`, `GGML_IQK=1`) ✅ 2026-07-19
- [x] OP-2 bench-window package drafted: concrete approval/preflight/artifact/abort plan now exists for the bench-clean canonical bench, AMD perf-counter checks, B1 barrier-fusion A/B, and B4 DSA-D3 profile-first stage; it explicitly does not authorize production-v6 edits/builds, full-stack reload, or AutoPilot restart ✅ 2026-07-18
- [ ] P0 Batched decode E2/E3: capture EvalTower quality/reliability/throughput telemetry before default path change, via `eval_batch_serving_evaltower_window.py` (batched-decode-measurement.md)
- [x] P0 Batched decode E3 go/no-go: E3 no-go/closed for now. Existing E1/E2 evidence shows a serving/topology win, while the later CPU roofline says decode-side SIMD/ALU work is BW-killed; do not write the 8x8 GEMM SIMD body. ✅ 2026-07-18
- [x] P0 Batched decode waypoint E4 (doc-only): CPU17/Sarathi reopens only to the measurement gate for long-prompt mid-stream TBT; CPU18/MegaBlocks remains gated pending a padding/capacity-factor cost profile. ✅ 2026-07-18
- [ ] MED DSA / DeepSeek V3.2 legacy PR #21149: refresh PR snapshot only if the legacy DeepSeek V3.2 / GLM-5.1 path remains in scope; GLM-5.2 is now tracked through the experimental-v7 GLM-DSA/quality gates instead (llama-cpp-dsa-contribution.md)
- [x] P1 MoE-Spec CPU spec-dec (GATED): zero-inference assessment completed; reopen for a current live-MTP MoE verifier B-sweep, but keep registry integration blocked until current speed/acceptance/quality evidence exists. ✅ 2026-07-18
- [ ] P1 CPU roofline: run claim-grade AMD perf-counter benches in clean-window protocol (cpu-kernel-env-flags-inventory.md)
- [ ] P1 Shape-specialized GEMV: B1 frontdoor Q8_0 barrier-count fusion A/B was skipped because no current immutable on/off binary pair was staged; reopen only with a staged pair (Q6_K/Q5_K SIMD follow-ons remain deprioritized) (cpu-shape-specialized-gemv-decode.md)
- [ ] P2 Phase-disaggregated serving: keep only xGMI KV-transfer falsification gate active (numa-prefill-decode-disaggregation.md)
- [x] P1 Prefill-compute B7 scoping: existing PC-1 sizing + PC-2 design detail are enough to close agent-zero-inference scoping; first PC-0 command/artifact plan is recorded in the owner handoff. ✅ 2026-07-18
- [ ] P1 Prefill-compute PC-0: complete the operator-approved first profile cell (122B architect `p8192/n1`, paired `bench_canonical.sh --perf`/`perf stat` + `perf record`; confirm compute-bound) before any kernel. Observation-only `perf record` artifact exists from 2026-07-18 but does not close the gate.
