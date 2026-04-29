# llama.cpp DSA Contribution — PR #21149 Stabilization + Three Sub-Tracks

**Status**: ACTIVE TRACKING — three sub-tracks defined, all gated on user inference approval per `feedback_no_concurrent_inference.md`
**Created**: 2026-04-29 (via research-intake of intake-506 + PR #21149 audit)
**Updated**: 2026-04-29 (initial)
**Categories**: kv_cache, inference_serving, hardware_optimization, local_inference
**Workstream**: Inference Acceleration + CPU Engineering (cross-cuts)
**Parent indices**:
- [`inference-acceleration-index.md`](inference-acceleration-index.md) (architectural research)
- [`cpu-inference-optimization-index.md`](cpu-inference-optimization-index.md) (kernel engineering)
**Related**:
- [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) — **2-models-for-1 leverage** (DSA infrastructure unlocks GLM-5.1 simultaneously)
- [`multiscreen-attention-evaluation.md`](multiscreen-attention-evaluation.md) — sub-quadratic attention survey, intake-506 documented under same-day-expansion sub-section
- [`triattention-kv-selection.md`](triattention-kv-selection.md) — retrofit selection (Expected Attention) for comparison vs DSA's integrated selection
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) — Phase 5 candidate (CPU26) AVX-512BW Lightning Indexer kernel; **D3 sub-track lives here**
- [`llama-cpp-kernel-push-rebase.md`](llama-cpp-kernel-push-rebase.md) — superseded but format template
- intake-506 (DeepSeek-V3.2 paper, arxiv:2512.02556)
- [V3.2 deep-dive](../../research/deep-dives/deepseek-v32-dsa-llamacpp-pr21149.md) — full mechanism analysis + "How we'd contribute" section

## Objective

Track upstream PR #21149 (DeepSeek V3.2 + DSA support) by **fairydreaming** to merge-readiness, and contribute upstream where our hardware + expertise fit. The PR is a draft as of 2026-04-29 with active commits (last 2026-04-28). One stabilized PR unlocks BOTH DeepSeek-V3.2 (671B-class MoE) AND GLM-5.1-555B-A14B (same DSA architecture) on our 1.1 TB EPYC.

## PR State Snapshot (2026-04-29)

| Property | Value |
|----------|-------|
| PR # | [#21149](https://github.com/ggml-org/llama.cpp/pull/21149) |
| Author | fairydreaming |
| State | **DRAFT, ACTIVE** |
| Opened | 2026-03-29 |
| Last commit | 2026-04-28 |
| Commits | 58+ |
| Backends working | CPU ✅, CUDA ✅ (WMMA), Vulkan ✅ (after #22177 fix); Metal ❌ not mentioned |
| Author's caveat | *"Due to the way it's currently implemented it doesn't improve long context performance yet"* |
| Author's help requests | (1) benchmark verification on GPU clusters, (2) Vulkan debugging, (3) implicit gap: CPU benchmarks |
| Models supported | DeepseekV32ForCausalLM (V3.2 Exp, V3.2, V3.2 Speciale) |

### What's in the PR

- New ggml ops: `GGML_OP_HADAMARD`, `GGML_OP_LIGHTNING_INDEXER`
- New KV cache classes: `llama_kv_cache_dsa`, `llama_ik_cache` (indexer keys)
- Specialized flash-attention MMA kernel sparse path (token generation)
- Conversion tooling: requires `add_bos_token=true` in tokenizer_config.json before conversion
- ~1000+ LOC across multiple files (model/architecture + ggml ops + KV cache + tests + benchmarks)

### What's NOT in the PR yet (per author)

- Long-context speedup not yet realized — sparse path applies to token generation only, not prompt processing
- Author flagged a separate follow-on PR for "advanced sparse fattn kernel optimization" (extending sparse path to PP)
- No CPU-only benchmarks published — all reported numbers are CUDA WMMA
- Metal backend support

## Three Contribution Sub-Tracks

### D1 — Pull / Build / Smoke Test (lowest-hanging fruit) [GATED]

**Effort**: ~1 day
**Visibility**: Medium (first CPU data point on a CUDA-dominated PR)
**Risk**: Low (read-only contribution; just observation)
**Inference gate**: REQUIRED per `feedback_no_concurrent_inference.md`

**Work items**:

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D1.1 | Verify disk space for V3.2 Q4_K_M GGUF (~380 GB) on `/mnt/raid0` (3.7 TB total per `user_hardware`) | PENDING | `df -h /mnt/raid0` — should be straightforward |
| D1.2 | Pull PR #21149 as feature branch in `llama.cpp-experimental` | PENDING | `git fetch upstream pull/21149/head:dsa-21149` |
| D1.3 | Build on EPYC with our standard CPU-build flags | PENDING | `cmake -B build_dsa -DGGML_CUDA=OFF -DGGML_NATIVE=ON ...` |
| D1.4 | Download V3.2-Exp Q4_K_M GGUF | PENDING | Likely from HF; check community quants of `deepseek-ai/DeepSeek-V3.2-Exp` |
| D1.5 | Convert if no Q4_K_M available — `convert_hf_to_gguf.py` per PR's `add_bos_token=true` requirement | PENDING | Only if Q4_K_M doesn't exist already |
| D1.6 | **Quality gate**: GSM8K + GPQA-Diamond at 32K context, replicate "V3.2-Exp ≈ V3.1-Terminus" | **GATED on user inference approval** | Use canonical baseline: `taskset -c 0-95 -t 96 -fa 1 --mmap 0 numactl --interleave=all` |
| D1.7 | **Throughput gate**: t/s at 16K / 64K / 128K context, V3.2 with DSA active vs MLA-only baseline | **GATED on user inference approval** | Falsify hypothesis: indexer FP8 emulation kills CPU advantage |
| D1.8 | Post results as comment on PR #21149 | PENDING | Follows D1.6 + D1.7 |

**Decision gate after D1**: if quality holds AND throughput is reasonable on CPU, proceed to D2/D3. If indexer is the CPU bottleneck → D3 priority. If quality fails → file issue on PR, deprioritize until upstream fixes.

### D2 — Prompt-Processing Sparse Path Follow-On PR

**Effort**: ~1-2 weeks
**Visibility**: HIGH (real upstream contribution, closes the long-context-speedup gap that's currently the PR's biggest known limitation)
**Risk**: Medium (kernel work; CUDA + CPU paths both involved)

The PR's current sparse path applies only to **token generation** (batch_size=1). Prompt processing still uses dense attention despite the same DSA top-k mask being available. **This is the actual root cause of "long-context performance not improved yet."**

Author's note (paraphrased): *"separate PR needed for advanced sparse fattn kernel optimization"*

**Work items**:

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D2.1 | Read current sparse path in PR #21149 — identify token-gen-only call sites | PENDING | `src/llama-graph.cpp` DSA attention graph building |
| D2.2 | Design extension: route DSA top-k mask to PP attention path | PENDING | Decision: invasive `ggml_get_rows()` change vs new sparse-fattn variant |
| D2.3 | Implement CPU path first (mirrors our existing kernel work), validate PPL bit-exact | PENDING | `tests/test-backend-ops.cpp` existing + new PP tests |
| D2.4 | Throughput gate: PP t/s improvement at 32K / 64K / 128K | **GATED on user inference approval** | Must show real PP speedup, not just preservation |
| D2.5 | CUDA path follow-on (optional; can split as separate PR) | PENDING | Author has CUDA expertise; we don't necessarily need to implement |
| D2.6 | Open as separate upstream PR or as comment+patch on #21149 | PENDING | Coordinate with fairydreaming on review path |

**Decision gate before starting D2**: D1 must show V3.2 quality is preserved on CPU. Otherwise we're optimizing a broken path.

### D3 — AVX-512BW Lightning Indexer (Zen 5 SIMD)

**Effort**: ~1 week
**Visibility**: HIGH (first CPU SIMD optimization on the DSA path)
**Risk**: Medium (profile may show indexer is BW-bound; if so, SIMD is a no-op)

**Cross-track**: Lives in `cpu-shape-specialized-gemv-decode.md` Phase 5 candidate (CPU26). This handoff tracks the strategic context; the SIMD work itself happens in the kernel handoff.

Author commit (2026-04-28): *"ggml : optimized GGML_OP_LIGHTNING_INDEXER (added WMMA kernel >= Ampere)"* — CUDA path got WMMA optimization. CPU path is presumably scalar.

Our angle (per `project_zen5_vnni_vs_maddubs` + `project_q8_8x8_avx512bw_outcome` memories): we have established Zen 5 SIMD expertise. The Lightning Indexer's FP8 head-weighted scoring with block-64 quantized key cache is the kind of operation our existing AVX-512BW work targets.

**Work items**:

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D3.1 | Profile current CPU `GGML_OP_LIGHTNING_INDEXER` with `perf record` to confirm compute-bound | PENDING | Per `feedback_cpu_decode_bw_bound`, BW-bound work doesn't benefit from SIMD |
| D3.2 | If compute-bound: design AVX-512BW kernel for indexer dot-product + top-k selection | PENDING | Template from `gemv_q8_0_8x8_q8_0_avx512bw` in `arch/x86/repack.cpp` |
| D3.3 | Implement kernel with `vpmaddubsw`+`vpmaddwd` (NOT VPDPBUSD, per Zen 5 finding) | PENDING | ~300-500 LOC est. |
| D3.4 | Correctness gate: PPL bit-exact vs scalar baseline | PENDING | Standard test-backend-ops + 32-chunk PPL pattern |
| D3.5 | Throughput benchmark: indexer-time fraction before/after at 96 threads | **GATED on user inference approval** | Falsify "indexer FP8 kills CPU advantage" |
| D3.6 | Auto-mbind the indexer key cache buffer (if it's a separate allocation) per `feedback_repack_buffer_numa_mbind` | PENDING | Only if profile shows multi-thread NUMA pressure |
| D3.7 | Open upstream PR or contribute as patch-comment on #21149 | PENDING | Specifically scoped to "ggml-cpu/arch/x86 LIGHTNING_INDEXER kernel" |

**Decision gate after D3.1**: if profile shows BW-bound, deprioritize D3 and redirect effort to D2. Don't write SIMD code that won't move the needle.

## 2-Models-for-1 Leverage Statement

Both V3.2 (671B-class) and GLM-5.1-555B-A14B use DSA architecture. The same indexer + KV cache infrastructure is reused identically. **When PR #21149 stabilizes — with or without our contribution — GLM-5.1 unblocks the same week.**

This is the core reason this handoff exists as a strategic tracker rather than a single-model evaluation. Effort here pays off twice (or more, as DSA propagates to future DeepSeek / GLM model families).

Cross-ref: [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) is the GLM-5.1 evaluation tracker; it's been gated on this exact DSA implementation work.

## Decision Gates

| Gate | Trigger | Action |
|------|---------|--------|
| **D1 START** | (a) Disk space verified, AND (b) user approves inference benchmark window | Pull PR, build, run smoke test |
| **D2 START** | D1 complete + quality validated + author hasn't already merged a PP-extension PR | Begin D2 design |
| **D3 START** | D1 complete + D3.1 profile confirms compute-bound | Begin D3 kernel work |
| **D2 / D3 PARALLEL** | Both above gates met | Can run concurrently — different code paths |
| **PR #21149 MERGED** | Upstream maintainer merges (or fairydreaming flips draft → ready) | Cherry-pick into our `production-consolidated-v3` branch via `llama-cpp-kernel-push-rebase.md` pattern |
| **GLM-5.1 ACTIVATION** | DSA path validated on V3.2 (D1 complete + quality OK) | Hand off to `glm51-reap-cpu-evaluation.md` Phase 1 |
| **DEPRIORITIZE** | Author abandons PR OR upstream rejects DSA design | Re-evaluate; possibly maintain a fork-only path |

## Monitoring Cadence

| Target | Cadence | Signal |
|--------|---------|--------|
| PR #21149 commits | Weekly | New optimizations / "ready for review" / merge | 
| PR #21149 description | Weekly | Author lifts "long-context performance not improved yet" caveat |
| Issue #20363 (tracking) | Monthly | Status changes |
| Issue #21458 (`GGML_OP_GATED`) | Monthly | Supporting infrastructure status |
| GLM-5.1 GGUF availability | Monthly | Community Q4_K_M release |

Optional: schedule a weekly background agent via `/schedule` to check PR state and notify on caveat removal.

## Cross-References

- **Parent intake**: intake-506 (DeepSeek-V3.2 paper, arxiv:2512.02556) — full mechanism details
- **Sibling intake**: intake-502 (KSA) — explicitly cites V3.2 as same first-principle of sequence-level KV compression
- **Architecture parent**: arxiv:2502.11089 (NSA — DSA's parent paper, Native Sparse Attention)
- **Deep dive**: `/workspace/research/deep-dives/deepseek-v32-dsa-llamacpp-pr21149.md` — full PR audit + "How we'd contribute" expansion
- **Existing fork commit**: `1c0d9081f` (DeepSeek v3.2 chat parser, already on `production-consolidated-v3`)
- **Comparison axis**: `triattention-kv-selection.md` S1 PPL-at-50%-eviction gate template — reusable for D1.6 quality validation

## Notes

The "we'd need to write a fork patch" framing in earlier glm51 handoff text was generated by extrapolation from a stale handoff line ("indexer not yet supported") that was true for PR #19460 in February but no longer reflects upstream state. The active reframe is: **track + test + selectively contribute**, not **write from scratch**.

`feedback_no_concurrent_inference.md` rule applies to every benchmark execution in this handoff. The `[GATED]` markers above are explicit; the experimental-kernel agent should not run any inference without per-run user approval.
