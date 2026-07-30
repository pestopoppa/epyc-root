# CPU Inference Optimization — Active Backlog

**Purpose**: forward-looking backlog for unimplemented CPU decode/prefill throughput work on local EPYC 9655 Turin hardware.
**Scope**: CPU-only single-instance or aggregate throughput. GPU work lives in [gpu-acceleration-path.md](gpu-acceleration-path.md); routing/orchestration lives in [routing-and-optimization-index.md](routing-and-optimization-index.md); eval/quality lives in [research-evaluation-index.md](research-evaluation-index.md).
**Updated**: 2026-07-20 PC-4o closed: the
`GGML_CPU_CONCAT_DIM0_ROWS=1` experimental, default-off CONCAT dim0 row
partition is committed and pushed in `llama.cpp-experimental` as post-candidate
research (`93d945885`, `Add default-off CPU CONCAT dim0 row partition`). The
package touched only `ggml/src/ggml-cpu/ops.cpp` and
`tests/test-backend-ops.cpp`, keeps the path env-gated/default-off, tightens
support to exact matching tensor types, and does not change frozen v7
candidate `6ad45fa3ff`. Post-commit validation passed `git diff --check`,
focused CPU `CONCAT` env-off/env-on (`210/210` both ways), and env-on
`test-recurrent-state-rollback` with the experimental DSO path pinned. PC-4o
then reran the clean-detached admission cell: `p8192/n1` improved `+7.771%`,
`p8192/tg16` improved `+34.948%`, and batched `pl=2` prompt speed improved
`+22.031%`, while tg-only regressed `-5.775%`. Decision: keep the path
default-off/env-gated as a prefill/batched-prefill tuning candidate, not a
default-on or frozen-v7 update. Prior: PC-4m source hardening
closed for the same candidate; unsupported shapes stay on existing concat
kernels through an explicit support predicate. Prior: PC-4l repeat/shape gate
was positive and carried the candidate forward:
repeat qwen35moe `p8192/n1` improved pp8192 `95.531624 -> 104.210589 t/s`
(`+9.0849%`), generated-token `pp8192+tg16` improved
`88.838786 -> 93.782587 t/s` (`+5.5649%`), and batched `pl=2` prompt speed
improved `169.369247 -> 261.157013 t/s` (`+54.1939%`).
Prior: PC-4k default-off CONCAT dim0 row-partition probe reduced the target
`CONCAT` barrier sum `2196940708 -> 17871828 us` (`-99.1865%`). Prior: PC-4j CPU-backend
node/barrier attribution closed:
qwen35moe CPU-only `p8192/n1` barrier attribution is dominated by
`CONCAT`/`conv_input-*` in shared `build_conv_state()` (`36.9%` of top-16
barrier time), while `MUL_MAT_ID` remains the main compute sink. Prior: PC-4i
scheduler-split attribution closed no-go:
qwen35moe CPU-only `p8192/n1` is one CPU scheduler split (`4471` nodes,
`0` inputs), so PC-4 now moves to CPU-backend node/barrier attribution (PC-4j)
instead of scheduler split/copy prototypes. Prior: 2026-07-19 OP-2 live v6+iqk verification and clean canonical CPU gate COMPLETE:
live preflight/role smokes passed and P-BENCH-1 frontdoor Q8 tg128 recorded; B1 was skipped
as not staged and B4 closed no-go. Stack servers and AutoPilot remain stopped by the runner.
Prior: 2026-07-19 OP-2 gate was corrected to bench-clean quiet-window execution: reboot
only if preflight flags multi-day throttle, with no production-v6 edits/builds, full-stack
reload, or AutoPilot restart. Prior: 2026-07-18 B7 prefill-compute scoping closed; track is now
past PC-0 premise profiling and PC-3 target selection: the OP-2 `(deleted)` hot mapping is
LLVM OpenMP worker spin/pause, so the next implementation gate is a default-off qwen35
prefill barrier/graph-fusion prototype in experimental only. Prior: 2026-07-14 backlog ROI
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
PC-0 first cell and PC-3 target selection closed positive; PC-4 experimental prototype remains open).

| Priority | Track | Owner handoff | Next action |
|----------|-------|---------------|-------------|
| P0 | **NUMA placement defect + topology cutover (LIVE DAMAGE, fix written in-tree)** | [numa-placement-defect-20260730.md](numa-placement-defect-20260730.md) (diagnosis, N24), [numa-topology-cutover-resume-20260730.md](numa-topology-cutover-resume-20260730.md) (landing, N25) | `stack_numa.py`'s `NUMA_NODE0`/`NUMA_NODE1` are **NPS2-era names that each straddle two NPS4 nodes**; `frontdoor` (8070) and `ingest_long_context` (8085) launched on them with **no `numactl` policy**, serving at **46%** and **54%** of canonical (`10.83 ± 0.04` vs `23.36 ± 0.11` tok/s, `llama-bench` tg128 r=10, `P-BENCH-PLACEMENT-1`, era `production-consolidated-v8` @ `67a433bf4`). **Exactly two roles** — `worker_general` and `architect_general` were already canonical; do **not** restate fleet-wide. Undetectable by warm A/B because `--interleave` binds at **first touch only**. Second mechanism: the GGUF is **mmap'd**, so pages are placed **once** by whichever instance faults first and later instances inherit it regardless of `--membind` (25.6% vs 100% local; fleet decode 40.91 → 52.13 tok/s) — fleet throughput was **nondeterministic across reboots**. **Fix is written in the tree, uncommitted**: quarters retired → 1 full + 2 halves, declared policy on every instance, `-t` == physical cores, `no_mmap: true` on six roles. **Next action: N25 P0-1** — 30 net-new test failures across 14 files, 2 in `PROMOTION_GATE_TARGETS`, so the stack cannot start; then cold-start → re-bench the contention matrix (its topology hash moved to `bc28e15d`) → commit. **This supersedes the N12 closed-negative `no_mmap` row below** — that verdict was reached under inherited mmap placement, i.e. it measured the confound. |
| P0 | **`ngram-mod` speculation — never-deployed 2.80× CPU decode lever** | [speculative-decoding-mtp-refresh.md](speculative-decoding-mtp-refresh.md) (NG1–NG5) | Production runs `--spec-type draft-mtp` alone; the master registry carries `ngram_candidate_spec_type: ngram-mod,draft-mtp` as a never-deployed candidate. On realistic text (10.6% repeated 5-grams): Qwen3.6-35B-A3B `24.92 → 69.89` tok/s at 14,059 tokens (**2.80×**, acceptance `.505 → .755`), `12.46 → 18.71` at 53,730. Qwen3-Next-80B `17.40 → 20.06` — and since its SSM hybrid has **no draft-model path**, `ngram-mod` is the **only** speculation that role can have. gemma4-26B and the 122B gain **nothing**. PRINCIPLE: **benefit is inversely proportional to the incumbent drafter's acceptance rate.** Next action: NG1 quality/bit-exactness pass, then a one-field registry change — sequenced **after** the N25 cutover commit, since it forces a second recompile + contention re-bench. ⚠ every ngram claim must carry its corpus and repeated-5-gram fraction (synthetic filler inflated the same measurement to a near-meaningless `2.52×`). |
| P0 | **iqk IQ-quant enablement (live defect)** | [iqk-iquant-enablement.md](iqk-iquant-enablement.md) | `GGML_IQK=1` dispatches per quant type and `iqk_typeA_supported` whitelisted only K-quants/legacy, with `iqk_set_kernels_iquants`/`iqk_convert_iquants_q80_r8` as linker stubs — so every IQ-quant model ran its weight bulk on the stock kernel, silently. Affects all four registry IQ models: GLM-5.2 221 tensors, Qwen3.5-122B 143, **Qwen3-Next-80B 433 (54% of 807)**, Hy3-IQ1_M 157. Code complete and pushed on `iqk/enable-iquants-v7-20260721` @ `f78ec18fe` (fresh off `production-consolidated-v7` `6ad45fa3f`); **NOT BUILT, NOT VALIDATED** — B1 build, B2 per-model coherence, B3 `llama-bench`, B4 non-IQ regression, B5 promote all need a quiet window. Also carries B6 (still-stubbed 1bit family) and the KT/trellis sequencing T1-T3 folded from tq3. |
| P0 | Bench-clean canonical decode bench | [v6-iqk-promotion.md](../completed/v6-iqk-promotion.md) (Phase J) | **COMPLETE 2026-07-19**: live v6+iqk preflight PASS, role smokes 6/6, process blockers 0, and clean P-BENCH-1 frontdoor Q8 tg128 `avg_ts=12.442712`, `stddev_ts=0.010877`, build `91745611f`/`9774`, `n=10`, `96` threads, with `GGML_IQK=1` and iqk activation stderr. Strict sentinel `avg_ts=19.1828`, warnings/blockers empty. B1 skipped (not staged); B4 closed no-go. Evidence: research `038fb35`, report `docs/data/op2_canonical_bench_window_20260719_live5.md`, raw root `data/op2_canonical_bench_window/op2-canonical-bench-window-20260719-live5`. |
| P0 | Batched decode E1/E2/E3 | [batched-decode-measurement.md](batched-decode-measurement.md) | E2 is decision-grade keep-candidate: single full `qwen36_q8_0 -np 8` is 4.858x faster than current 3-concurrent EvalTower fan-out. Orchestrator `7cb71a4e` landed the default-off `eval_batch_serving` flag and explicit EvalTower eval-batch metadata; orchestrator `e9312a17` added the launcher-only warm `eval_batch_frontdoor` hook on port `18070` plus guarded request-scoped routing; orchestrator `276a1eef` added the guarded preflight/smoke probe; the 2026-07-04 follow-up adds `scripts/benchmark/eval_batch_serving_activation_window.py`, a plan/apply/rollback wrapper for the clean-window activation. The 2026-07-05 activation smoke passed and rolled back cleanly (`status=smoke_passed_rolled_back`), the 2026-07-06 P-BENCH-3 sweep captured the full `qwen36_q8_0` `np={1,2,4,8,16}` curve, and the 2026-07-07 dense-control tail completed at `e1-pbench3-dense-control-iqk-20260707T022917Z` (`43/43` per cell, `0` errors, throughput `20.11 -> 124.62` tasks/hour, p95 `240.9s -> 674.0s`). Representative EvalTower quality/reliability/throughput telemetry is still the remaining gate before any default path change; the packaged EvalTower window runner (orchestrator `8d36aa1e`, `scripts/benchmark/eval_batch_serving_evaltower_window.py`) is the execution path for that gate. With dense-control E1 complete (2026-07-07, `e1-pbench3-dense-control-iqk-20260707T022917Z`): (a) the E3 go/no-go per-thread-BW headroom analysis is decision-actionable NOW from existing data (zero inference), and (b) waypoint E4's doc-only CPU17 chunked-prefill / CPU18 MegaBlocks re-promotion-or-re-close decisions are actionable. Do not start E3 solely from the A3B result. |
| MED (was P0; aligned to master index 2026-07-14) | DSA / DeepSeek V3.2 legacy PR #21149 path | [llama-cpp-dsa-contribution.md](llama-cpp-dsa-contribution.md), [deepseek-v4-flash-cpu-port.md](deepseek-v4-flash-cpu-port.md), [glm51-reap-cpu-evaluation.md](glm51-reap-cpu-evaluation.md) | This row no longer gates GLM-5.2: generic DSA landed via upstream #23346 and experimental v7 wires GLM-5.2 `glm-dsa` cache/runtime. Keep PR #21149 only as a legacy DeepSeek V3.2 / GLM-5.1 snapshot question; refresh the dormant 2026-04-29 snapshot before any pull/build/smoke, and run only with explicit inference approval. |
| P1 (GATED) | MoE-Spec CPU spec-dec integration | [moe-spec-cpu-spec-dec-integration.md](moe-spec-cpu-spec-dec-integration.md) | Zero-inference assessment closed 2026-07-18: the 2026-07-03 live-α report proves current verification-batch consumers exist (`frontdoor` α=0.6582, `worker_general` α=0.8256, `architect_general` α=0.6854, failed MTP roles `[]`). Reopen only to a current live-MTP MoE verifier B-sweep with speed, acceptance, and quality/bit-exact guard. Registry integration remains blocked until that sweep exists. |
| P1 | CPU roofline / AMD counter calibration | [cpu-kernel-env-flags-inventory.md](cpu-kernel-env-flags-inventory.md), [deepseek-v4-flash-cpu-port.md](deepseek-v4-flash-cpu-port.md) | Research `ad9b73a` added the no-inference AMD perf-counter preflight and `bench_canonical.sh --perf` guard; research `515a50b` unblocked it after installing/exposing `linux-perf` in the devcontainer and teaching the preflight to recognize `perf list` alias rows such as `cpu-cycles OR cycles`. Current artifact `data/cpu_optimization/2026-07-03-amd-perf-counter-preflight/summary.{json,md}` is `status=ok`; all canonical Zen 5 events are visible, the smoke probe passed, and `bench_canonical.sh --perf --dry-run` prints the canonical event wrap without inference. Next action is claim-grade perf benches in the appropriate host-health/clean-window protocol. |
| P1 | Shape-specialized GEMV / AVX-512 follow-ons | [cpu-shape-specialized-gemv-decode.md](cpu-shape-specialized-gemv-decode.md) | Lead with the frontdoor Q8_0 barrier-count fusion A/B (fuse expert gate+up, attn QKV cluster; cheapest test = llama-bench tg128 fusion on/off in one window; est +10-15% decode, one cluster already measured +2.6%; **absolute ceiling +72% (4.42→7.6 t/s) if BW-util matches dense**; re-elevated 2026-07-03 by findings-05 as the #1 CPU decode lever; **v7-audit LANE B B1 — bundle into the OP-2 quiet window**). Keep landed Q8_0 wins. Q6_K/Q5_K SIMD follow-ons are explicitly DEPRIORITIZED per the roofline finding. |
| P1 | Prefill-compute for large models | [cpu-prefill-compute-large-models.md](cpu-prefill-compute-large-models.md) | B7 design/scoping, PC-0 premise profiling, and PC-3 target selection are closed. PC-4c through PC-4h rejected recurrent-GDN-first, compact routed-view/add aggregation, and router/top-k/weights prototypes. PC-4i rejected scheduler split/copy logic. PC-4j mapped CPU-backend barrier attribution to `CONCAT`/`conv_input-*` in shared `build_conv_state()`, PC-4k proved the default-off row-partition candidate, PC-4l repeated/expanded it positive (`+9.0849%` pp8192, `+5.5649%` pp8192+tg16, `+54.1939%` batched pl=2 prompt speed), PC-4m source-hardened/expanded correctness coverage (`210/210` CONCAT env-off/env-on plus recurrent rollback env-off/env-on), PC-4n committed the default-off package as post-candidate experimental work (`llama.cpp-experimental` `93d945885`), and PC-4o admitted it only as a default-off prefill/batched-prefill tuning candidate after a clean-detached repeat (`+7.771%` p8192, `+34.948%` p8192+tg16, `+22.031%` batched pl=2 prompt speed, `-5.775%` tg-only). No default-on or frozen-v7 candidate change without a fresh exact-tip final smoke and a decode-exposure policy decision. |
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
- [x] P0 iqk IQ-quant enablement: build + per-model coherence/speed gates B1-B5 in a quiet window; blast radius is 4 registry models so a no-regression claim needs per-model evidence (iqk-iquant-enablement.md) ✅ 2026-07-29 — CLOSED as a stale index pointer by `auditor`. The owner `iqk-iquant-enablement.md` has **B1–B5 all `[x]`** (B1 build ✅ 2026-07-25 `b8ad9d292`; B2 correctness ✅ 2026-07-25, *exact 6-arm/24-task three-model attestation* — which is the per-model evidence this row asked for; B3 speed ✅; B4 non-IQ regression ✅; B5 promote ✅ 2026-07-26) and its Status reads **PROMOTED AND FROZEN IN v8**. The work this row tracks completed four days ago; the pointer simply never followed.
- [ ] P1 iqk 1bit family (B6): scope whether `iqk_set_kernels_1bit`/`iqk_convert_1bit_q80_r8` are as cheap to un-stub as the IQ-quant pair; sole beneficiary is Hy3-IQ1_M-mtp (82 IQ1_M tensors). Do not let it block B5 (iqk-iquant-enablement.md)
- [ ] P2 KT/trellis (T1-T3): gate IQ4_KT vs Q4_K_M before any port — our tree can neither produce nor load a KT GGUF (0 refs in ggml.h enum / ggml.c type_traits / llama-quantize). Drop permanently if IQ4_KT < 95% of Q4_K_M tg128 (iqk-iquant-enablement.md)
- [x] P0 Batched decode E2/E3: capture EvalTower quality/reliability/throughput telemetry before default path change, via `eval_batch_serving_evaltower_window.py` (batched-decode-measurement.md) ✅ 2026-07-29 — CLOSED as a stale index pointer by `auditor`. The owner `batched-decode-measurement.md` has **E2 `[x]` twice** — including the row that names this exact script, *“E2 — eval-tower window runner (same lane): `scripts/benchmark/eval_batch_serving_evaltower…`”* — and **E3 `[x]` marked NO-GO / CLOSED**. Its Status records *“A3B E1 and E2 decision-grade evidence landed 2026-07-03”*. Both halves of the E2/E3 pointer are resolved at the owner.
- [x] P0 Batched decode E3 go/no-go: E3 no-go/closed for now. Existing E1/E2 evidence shows a serving/topology win, while the later CPU roofline says decode-side SIMD/ALU work is BW-killed; do not write the 8x8 GEMM SIMD body. ✅ 2026-07-18
- [x] P0 Batched decode waypoint E4 (doc-only): CPU17/Sarathi reopens only to the measurement gate for long-prompt mid-stream TBT; CPU18/MegaBlocks remains gated pending a padding/capacity-factor cost profile. ✅ 2026-07-18
- [x] MED DSA / DeepSeek V3.2 legacy PR #21149: no snapshot refresh — the legacy DeepSeek V3.2 / GLM-5.1 path is no longer in scope. The owner records #21149 monitoring/description as MOOT, says generic DSA landed via #23346/current upstream, and names GLM-5.2 as the active target with its own landed-code gates (llama-cpp-dsa-contribution.md §§ Decision Gates, Monitoring Cadence, Research Intake Update). ✅ 2026-07-29
- [x] P1 MoE-Spec CPU spec-dec (GATED): zero-inference assessment completed; reopen for a current live-MTP MoE verifier B-sweep, but keep registry integration blocked until current speed/acceptance/quality evidence exists. ✅ 2026-07-18
- [ ] P1 CPU roofline: run claim-grade AMD perf-counter benches in clean-window protocol (cpu-kernel-env-flags-inventory.md)
- [ ] P1 Shape-specialized GEMV: B1 frontdoor Q8_0 barrier-count fusion A/B was skipped because no current immutable on/off binary pair was staged; reopen only with a staged pair (Q6_K/Q5_K SIMD follow-ons remain deprioritized) (cpu-shape-specialized-gemv-decode.md)
- [ ] P2 Phase-disaggregated serving: keep only xGMI KV-transfer falsification gate active (numa-prefill-decode-disaggregation.md)
- [x] P1 Prefill-compute B7 scoping: existing PC-1 sizing + PC-2 design detail are enough to close agent-zero-inference scoping; first PC-0 command/artifact plan is recorded in the owner handoff. ✅ 2026-07-18
- [x] P1 Prefill-compute PC-0: operator-window first profile cell completed positive on 122B architect `p8192/n1`; OP-2 production-v6 row recorded `112.730698 t/s`, `1.09` IPC, `68.597` CPUs, and `46.47%` resolved `libggml-cpu` DSO samples. ✅ 2026-07-19
- [x] P1 Prefill-compute PC-3: resolved the OP-2 `(deleted)` mapping to LLVM OpenMP worker spin/pause; target selection now points to barrier/graph-fusion first, not low-level dot-kernel work. ✅ 2026-07-19
- [x] P1 Prefill-compute PC-4a: default-off qwen35/qwen35moe graph-node trace scaffold prepared and build-validated in `llama.cpp-experimental`; llama.cpp patch remains uncommitted pending explicit operator review/commit approval. ✅ 2026-07-19
- [x] P1 Prefill-compute PC-4b: traced qwen35moe `p8192/n1`; recurrent `linear_attn` is the high-delta island, but no implementation yet. ✅ 2026-07-19
- [x] P1 Prefill-compute PC-4c: recurrent `linear_attn` sublayer trace completed; recurrent graph-node pressure was real but did not override timing evidence. ✅ 2026-07-20
- [x] P1 Prefill-compute PC-4d/4e/4f/4g/4h: target-selection and routed-MoE diagnostics completed; recurrent-GDN-first, compact routed-view/add aggregation, and router/top-k/weights prototypes rejected by evidence. ✅ 2026-07-20
- [x] P1 Prefill-compute PC-4i: scheduler split attribution completed; qwen35moe `p8192/n1` is one CPU scheduler split, so PC-4 moves to CPU-backend node/barrier attribution. ✅ 2026-07-20
- [x] P1 Prefill-compute PC-4j: CPU-backend node/barrier attribution completed; `CONCAT`/`conv_input-*` in shared `build_conv_state()` is the first source-level barrier target. ✅ 2026-07-20
- [x] P1 Prefill-compute PC-4k/4l/4m: default-off `GGML_CPU_CONCAT_DIM0_ROWS=1` proved positive, repeated/expanded positive, then source-hardened with broader backend correctness and recurrent rollback coverage. ✅ 2026-07-20
- [x] P1 Prefill-compute PC-4n: operator-approved experimental commit/package completed in `llama.cpp-experimental` commit `93d945885`; package is default-off, post-candidate, and excluded from frozen v7 `6ad45fa3ff`. ✅ 2026-07-20
- [x] P1 Prefill-compute PC-4o: clean-detached admission repeat kept `GGML_CPU_CONCAT_DIM0_ROWS=1` as a default-off prefill/batched-prefill tuning candidate; no default-on or frozen-v7 candidate change without a fresh exact-tip final smoke. ✅ 2026-07-20
