# llama.cpp DSA Contribution — DSA LANDED upstream (#23346); remaining CPU-perf sub-tracks (D2/D3)

**Status**: RE-AUDITED 2026-07-17 — **generic DSA support LANDED via upstream #23346** for DeepSeek32, NOT the tracked draft #21149 -> the "track #21149 to merge" objective and D1 are SUPERSEDED. Important correction closed: pre-fix source registered `LLM_ARCH_GLM_DSA` and loaded GLM DSA tensors but did not instantiate `llama_kv_cache_dsa` for GLM; experimental-v7 commit `3dee86a5a` now wires GLM to the DSA cache/runtime path, aliases the DeepSeek32 DSA graph, requires live GLM indexer tensors, and force-builds GLM indexer Hadamard rotation tensors. Runtime GLM-5.2 fixed-`indexer_top_k=32` scaling now classifies the landed path as **DSA-DENSE-MASK**: generic DSA top-k/indexer engages in prompt processing, but final attention still scales with full KV. Live remnants: D2 sparse final-attention implementation/profiling + D3 CPU AVX-512 Lightning-Indexer, re-anchored to the landed code and re-gated on fresh profiling. All inference gated per `feedback_no_concurrent_inference.md`.
**Created**: 2026-04-29 (via research-intake of intake-506 + PR #21149 audit)
**Lifecycle**: live — audit override (2026-07-18): the original #21149-merge objective is SUPERSEDED, but the D2/D3 CPU sub-tracks are genuinely live (re-anchored to landed code, gated on fresh profiling). Prevents the dashboard heuristic from dimming this as "superseded". See [`stale-open-audit-2026-07-18.md`](stale-open-audit-2026-07-18.md).
**Updated**: 2026-07-17 — DSA landed audit reset + GLM cache/runtime wiring fix + runtime `DSA-DENSE-MASK` classification recorded; prior 2026-05-28 deepseek4 section retained as adjacent history.
**Categories**: kv_cache, inference_serving, hardware_optimization, local_inference
**Workstream**: Inference Acceleration + CPU Engineering (cross-cuts)
**Parent indices**:
- [`inference-research-index.md`](inference-research-index.md) (architectural research)
- [`inference-research-index.md`](inference-research-index.md) (kernel engineering)
**Related**:
- [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) — GLM-5.2 active target; generic DSA landed and GLM cache/runtime wiring closed on experimental-v7 `3dee86a5a`; sparse final-attention and quality gates remain open
- [`multiscreen-attention-evaluation.md`](multiscreen-attention-evaluation.md) — sub-quadratic attention survey, intake-506 documented under same-day-expansion sub-section
- [`triattention-kv-selection.md`](triattention-kv-selection.md) — retrofit selection (Expected Attention) for comparison vs DSA's integrated selection
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) — Phase 5 candidate (CPU26) AVX-512BW Lightning Indexer kernel; **D3 sub-track lives here**
- [`llama-cpp-kernel-push-rebase.md`](../completed/llama-cpp-kernel-push-rebase.md) — archived 2026-06-12; superseded but format template
- intake-506 (DeepSeek-V3.2 paper, arxiv:2512.02556)
- [V3.2 deep-dive](../../research/deep-dives/deepseek-v32-dsa-llamacpp-pr21149.md) — full mechanism analysis + "How we'd contribute" section

## 2026-07-16 Audit Reset — DSA has LANDED (this handoff's premise is superseded)

**The tracked PR #21149 is no longer the path.** DSA support reached our v6 fork via a DIFFERENT upstream PR — **#23346, "DeepseekV32ForCausalLM with generic DeepSeek Sparse Attention (DSA) implementation."** Verified in v6 (2026-07-16):
- Arch enums registered: **`LLM_ARCH_DEEPSEEK32` ("deepseek32")** AND **`LLM_ARCH_GLM_DSA` ("glm-dsa")**.
- `src/models/glm-dsa.cpp` is present and loads GLM lightning-indexer tensors; `src/llama-kv-cache-dsa.cpp` implements the Lightning-indexer KV cache.
- Pre-fix source model-memory setup created `llama_kv_cache_dsa` only for `LLM_ARCH_DEEPSEEK32`; `LLM_ARCH_GLM_DSA` fell through to ordinary `llama_kv_cache`. Experimental-v7 `3dee86a5a` now routes GLM through `llama_kv_cache_dsa` and the DeepSeek32 DSA graph; current-source synthetic tests and exact `READY` GLM smoke passed.

**What this changes:**
- **D1 (pull draft #21149 / build / smoke) — SUPERSEDED.** The code is in production v6; the smoke-test now lives in the model-eval handoff [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) → **GLM-5.2** (the active DSA target; V3.2 not planned — GLM-5.2 covers this niche), not as a "pull the draft" task.
- **Monitoring PR #21149 weekly — MOOT.** DSA landed; stop tracking that PR to merge.
- **D2 (sparse-compute reality check) + D3 (CPU AVX-512 indexer) — RE-ANCHORED to landed #23346 code, not the fairydreaming draft.** Static audit (2026-07-17) found generic DSA `top_k` selection is built for both prompt processing and decode, but final attention still appears dense/mask-based. The GLM cache/runtime prerequisite is now closed by `3dee86a5a`; runtime GLM-5.2 scaling confirmed **DSA-DENSE-MASK** (`23.81 -> 21.04 -> 17.28 t/s` as prompt tokens grew `2900 -> 5906 -> 11921` under fixed `indexer_top_k=32`). D2 now needs sparse final-attention implementation/profiling, not more activation proof. D3 still needs a landed-code profile to decide compute-bound vs bandwidth-bound.
  - **2026-07-19 note — D2 is also the LONG-CONTEXT GLM-quality enabler.** GLM-5.2 emits malformed output past ~12K prompt tokens (32K needle FAILS) because the `indexer_top_k` cap doesn't scale with context; only hand-tuned next-power-of-two caps stay coherent (`2048`≤2K, `4096`≤3K, `16384`≤12K). Finishing D2 (a real sparse/indexed final-attention path with a correct, length-scaling top-k) is the **durable fix** for >12K GLM coherence. **But it is ORTHOGONAL to GLM's reviewer/judge quality** — those prompts fit ≤12K and are being tested NOW on external ground-truth benchmarks (see [`glm52-reviewer-capability-gates.md`](glm52-reviewer-capability-gates.md) 2026-07-19 directive). Do not gate the reviewer-quality verdict on D2.

## Objective (revised 2026-07-16)

Generic DSA is landed upstream (#23346) and present in v6/v7. The objective is no longer "track a draft PR to merge" — it is: (1) use the now-wired **GLM-5.2** DSA cache/runtime path (`3dee86a5a`) as the active large-MoE DSA testbed — **DeepSeek-V3.2 is NOT a planned eval** (GLM-5.2 covers the DSA large-MoE niche; V3.2 stays a supported-arch fact/fallback, not worth a second ~380 GB download + inference window), and (2) evaluate whether the two CPU-performance contribution opportunities (D2 sparse-compute attention reality, D3 AVX-512BW Lightning-Indexer kernel) are still real against the LANDED code, and pursue them upstream only if the re-gating checks pass. Original PR-#21149 tracking context is retained below as history.

### 2026-07-16 static D2 audit

Read-only landed-code audit found:
- Prompt and decode both route through the same `decode()`/`process_ubatch()`/`build_graph()` path; the main distinction is `ubatch.n_tokens`, not a separate DSA graph.
- DSA input tensors are built per `ubatch`, with no decode-only `n_tokens == 1` gate.
- `top_k` selection is computed for all tokens in the current ubatch.
- The selected `top_k` is applied by editing a dense KQ mask before standard attention.
- The final attention call still appears dense: `ggml_flash_attn_ext(...)` over full `k/v`, or `ggml_mul_mat(k, q)` plus softmax mask.

GLM correction (2026-07-17): this conclusion applies to the generic DSA path once a DSA cache exists. Pre-fix `LLM_ARCH_GLM_DSA` source loaded DSA metadata/tensors but did not instantiate `llama_kv_cache_dsa`; experimental-v7 `3dee86a5a` closes that cache/runtime gap. Older GLM >64K run artifacts came from a stale `build-hip` binary and should not be treated as current-source long-context proof.

Conclusion: current generic DSA code appears to do top-k selection in both prompt processing and decode, but static inspection does not prove sparse-compute attention. Runtime closeout on GLM-5.2 UD-IQ2_M later confirmed **DSA-DENSE-MASK**: with fixed `indexer_top_k=32`, Lightning/indexer caches engaged at 4K/8K/16K, but prompt throughput declined with context length (`/mnt/raid0/llm/tmp/glm52-current-source-kv-scaling-20260717T130222Z/runtime_summary.md`).

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

### D1 — Pull / Build / Smoke Test (SUPERSEDED; historical #21149 path)

**Effort**: ~1 day
**Visibility**: Medium (first CPU data point on a CUDA-dominated PR)
**Risk**: Low (read-only contribution; just observation)
**Inference gate**: REQUIRED per `feedback_no_concurrent_inference.md`

**Work items**:

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D1.1 | Verify disk space for V3.2 Q4_K_M GGUF (~380 GB) on `/mnt/raid0` (3.7 TB total per `user_hardware`) | SUPERSEDED | V3.2 is no longer the planned first DSA eval target. |
| D1.2 | Pull PR #21149 as feature branch in `llama.cpp-experimental` | SUPERSEDED | DSA reached v6 through #23346; do not pull the old draft as the live path. |
| D1.3 | Build on EPYC with our standard CPU-build flags | SUPERSEDED | Use current v6/experimental-v7 code for checks. |
| D1.4 | Download V3.2-Exp Q4_K_M GGUF | SUPERSEDED | GLM-5.2 is the active large-MoE DSA target. |
| D1.5 | Convert if no Q4_K_M available — `convert_hf_to_gguf.py` per PR's `add_bos_token=true` requirement | SUPERSEDED | Historical #21149 context only. |
| D1.6 | **Quality gate**: GSM8K + GPQA-Diamond at 32K context, replicate "V3.2-Exp ≈ V3.1-Terminus" | SUPERSEDED | Replace with GLM-5.2 load/smoke + long-context DSA probe. |
| D1.7 | **Throughput gate**: t/s at 16K / 64K / 128K context, V3.2 with DSA active vs MLA-only baseline | SUPERSEDED | Reprofile D2/D3 only after landed-code GLM evidence. |
| D1.8 | Post results as comment on PR #21149 | SUPERSEDED | No live PR comment action. |

**Decision gate replacement**: GLM-5.2 now loads coherently, the landed DSA path processed a stale-binary true >64K prompt with `Lightning Indexer enabled` (`/mnt/raid0/llm/tmp/glm52-dsa-true64k-probe-20260717T0125/`), and current-source `3dee86a5a` smokes prove GLM cache/runtime wiring (`/mnt/raid0/llm/tmp/glm52-current-source-ready-smoke-20260717T092344/`). Current-source fixed-`indexer_top_k=32` KV scaling (`/mnt/raid0/llm/tmp/glm52-current-source-kv-scaling-20260717T130222Z/runtime_summary.md`) confirmed D2 is live: final attention behaves as dense-mask. If the CPU Lightning-Indexer is compute-bound, D3 may also be live.

### D2 — Sparse-compute reality check / possible follow-on PR

**Effort**: ~1-2 weeks
**Visibility**: HIGH (real upstream contribution, closes the long-context-speedup gap that's currently the PR's biggest known limitation)
**Risk**: Medium (kernel work; CUDA + CPU paths both involved)

Historical #21149 context said sparse path applied only to **token generation** (`batch_size=1`) and prompt processing remained dense. Landed-code static audit does **not** show that exact split: top-k selection appears in both prompt processing and decode. The live question is whether the final attention op is still dense-mask compute in both paths, which would explain why long-context speedups may remain unrealized.

Author's note (paraphrased): *"separate PR needed for advanced sparse fattn kernel optimization"*

**Work items**:

| ID | Task | Status | Notes |
|----|------|--------|-------|
| D2.1 | Read the landed #23346 sparse path — identify whether DSA is prompt-only, decode-only, or shared | DONE | Static audit: top-k selection is shared across prompt/decode; final attention appears dense/mask-based. ✅ 2026-07-16 |
| D2.2 | Runtime closeout: profile one prefill batch and one single-token decode with a DSA model | DONE | Current-source GLM fixed-top-k run completed 4K/8K/16K with `max_tokens=1`; Lightning/indexer caches engaged and prompt throughput declined with KV length. ✅ 2026-07-17 |
| D2.3 | Vary KV length while keeping `indexer_top_k` fixed | DONE | Full-KV scaling observed: `23.81 -> 21.04 -> 17.28 t/s` at `2900 -> 5906 -> 11921` prompt tokens, classification `DSA-DENSE-MASK`. ✅ 2026-07-17 |
| D2.4 | If dense-mask scaling is confirmed, design sparse-fattn extension | SCOPED | 2026-07-18 source prep: existing `ggml_get_rows()` is not sufficient because KV positions sit on dim2; useful path is a new indexed DSA attention op with CPU oracle and fused GPU implementation, guarded behind fallback. Prep note: `/mnt/raid0/llm/epyc-inference-research/docs/reference/benchmarks/glm_mtp_sparse_attention_prep_20260718.md`. ✅ 2026-07-18 |
| D2.5 | Implement CPU path first if a real dense-mask bottleneck is confirmed | PENDING | `tests/test-backend-ops.cpp` existing + new PP tests; validate PPL bit-exact. |
| D2.6 | Throughput gate: PP/decode t/s improvement at 32K / 64K / 128K | **GATED on user inference approval** | Must show real sparse-compute speedup, not just preservation. |
| D2.7 | CUDA path follow-on (optional; can split as separate PR) | PENDING | Author has CUDA expertise; we don't necessarily need to implement. |
| D2.8 | Open as a separate upstream PR or current-master patch if the gap still exists | PENDING | Do not target the superseded #21149 draft as the live integration path. |

**Decision gate before starting D2 implementation**: closed 2026-07-17. The GLM-5.2 landed-code smoke shows the DSA cache/runtime path is real, and runtime scaling shows final attention work still scales with full KV despite top-k selection. D2 implementation can now be scoped as real sparse final-attention work.

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
| D3.1 | Profile current CPU `GGML_OP_LIGHTNING_INDEXER` with `perf record` to confirm compute-bound | CLOSED NO-GO ✅ 2026-07-19 | OP-2/B4 profile on GLM-5.2 `p5906`, `indexer_top_k=2048` measured `ggml_compute_forward_lightning_indexer` at only `1.08%` of cycle samples; quantized dot products, flash-attn, and OpenMP/runtime frames dominate. Artifact: `/mnt/raid0/llm/epyc-inference-research/data/op2_canonical_window/op2_b4_dsa_d3_profile_20260719T075142/b4-dsa-d3/summary.md`. |
| D3.2 | If compute-bound: design AVX-512BW kernel for indexer dot-product + top-k selection | DEFERRED | Do not start from current evidence; reopen only if D2 real-sparse final-attention or a materially different serving shape makes Lightning Indexer cycle share material. |
| D3.3 | Implement kernel with `vpmaddubsw`+`vpmaddwd` (NOT VPDPBUSD, per Zen 5 finding) | PENDING | ~300-500 LOC est. |
| D3.4 | Correctness gate: PPL bit-exact vs scalar baseline | PENDING | Standard test-backend-ops + 32-chunk PPL pattern |
| D3.5 | Throughput benchmark: indexer-time fraction before/after at 96 threads | **GATED on user inference approval** | Falsify "indexer FP8 kills CPU advantage" |
| D3.6 | Auto-mbind the indexer key cache buffer (if it's a separate allocation) per `feedback_repack_buffer_numa_mbind` | PENDING | Only if profile shows multi-thread NUMA pressure |
| D3.7 | Open upstream PR against current master if profiling justifies it | PENDING | Specifically scoped to "ggml-cpu/arch/x86 LIGHTNING_INDEXER kernel" |

**Decision gate after D3.1**: current landed-code profile says D3 is not worth immediate SIMD work. The Lightning Indexer path is active, but only `1.08%` of cycle samples on the OP-2/B4 GLM-5.2 8K profile. Redirect effort to D2/sparse-final-attention or higher-share CPU bottlenecks unless a later serving shape changes the profile.

## 2-Models-for-1 Leverage Statement

Both V3.2 (671B-class) and the GLM-MoE-DSA family use DSA with identical indexer + KV cache infrastructure. **This unlock has now HAPPENED in two steps: generic DSA landed via #23346, registering `deepseek32` + `glm-dsa` in v6, and experimental-v7 `3dee86a5a` wired GLM into the DSA cache/runtime path**. V3.2, GLM-5.1, and GLM-5.2 are now supported by the same DSA infrastructure, exactly the multi-model-for-one-effort payoff this handoff bet on.

This is the core reason this handoff exists as a strategic tracker rather than a single-model evaluation. Effort here pays off twice (or more, as DSA propagates to future DeepSeek / GLM model families).

Cross-ref: [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) is the GLM-5.1 evaluation tracker; it's been gated on this exact DSA implementation work.

## Decision Gates

| Gate | Trigger | Action |
|------|---------|--------|
| **D1 START** | OBE — DSA landed via #23346 | Do not pull/build the superseded draft PR as the live path |
| **D2 START** | GLM-5.2 current-source cache/runtime smoke succeeds + prompt processing is still dense/unimproved | Begin D2 design |
| **D3 START** | GLM-5.2 current-source cache/runtime smoke succeeds + D3.1 profile confirms compute-bound | Begin D3 kernel work |
| **D2 / D3 PARALLEL** | Both above gates met | Can run concurrently — different code paths |
| **PR #21149 MERGED** | OBE for this handoff | No action; landed-code path is #23346/current upstream |
| **GLM-5.2 ACTIVATION** | OBE — no longer gated on a V3.2 validation: DSA landed (#23346); activation = GLM-5.2 UD-IQ2_M download + smoke-test | Hand off to `glm51-reap-cpu-evaluation.md` (GLM-5.2 plan) |
| **DEPRIORITIZE** | Author abandons PR OR upstream rejects DSA design | Re-evaluate; possibly maintain a fork-only path |

## Monitoring Cadence

| Target | Cadence | Signal |
|--------|---------|--------|
| PR #21149 commits | MOOT | Stop tracking for merge-readiness; retained as historical context |
| PR #21149 description | MOOT | Stop tracking for merge-readiness; re-check landed code instead |
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

## Adjacent Upstream Arch Work — deepseek4 (DeepSeek-V4-Flash)

Tracked as a sibling effort, NOT folded into this handoff. V4 is a fundamentally new arch (CSA + HCA + indexer + compressor + manifold-constrained Hyper-Connections), not a DSA derivative — porting it is a multi-thousand-line arch addition, not an ops-add.

- **Upstream issue**: ggml-org/llama.cpp#22319 (model request, open)
- **WIP discussion**: ggml-org/llama.cpp#22376 (4+ community forks: nisparks `wip/deepseek-v4-support`, draft PR #22378 "no intent to merge", cdome94, Fringe210, antirez/llama.cpp-deepseek-v4-flash)
- **RESOLVED 2026-08-09**: `deepseek4` **merged upstream** as PR #24162 (`8c146a836`) and is present in `production-consolidated-v8` (`src/llama-arch.cpp:81`). Our out-of-tree port is moot — the ik_llama branch `feature/deepseek4-port` is dead and the port handoff is closed ([`../completed/deepseek-v4-flash-cpu-port.md`](../completed/deepseek-v4-flash-cpu-port.md)). Live successor work — 0731 weights + a `draft-dspark` spec type — is in [`deepseek-v4-flash-0731-dspark.md`](deepseek-v4-flash-0731-dspark.md).
- <s>**Our port**: experimental branch `feature/deepseek4-port` off ik_llama production tree</s> — superseded, see above
- **Watch trigger**: if a core contributor (fairydreaming or similar) opens a deepseek4 upstream PR, our role mirrors D1 (CPU benchmark contribution against canonical NPS4 stack); roll back our experimental branch in favor of the upstream PR for review and merge.

## Notes

The "we'd need to write a fork patch" framing in earlier glm51 handoff text was generated by extrapolation from a stale handoff line ("indexer not yet supported") that was true for PR #19460 in February but no longer reflects upstream state. The active reframe is: **track + test + selectively contribute**, not **write from scratch**.

`feedback_no_concurrent_inference.md` rule applies to every benchmark execution in this handoff. The `[GATED]` markers above are explicit; the experimental-kernel agent should not run any inference without per-run user approval.

## Research Intake Update — 2026-06-20

### GLM-5.2 raises the stakes on the DSA forward pass (intake-699)

- **GLM-5.2 (754B GLM-MoE-DSA) is now the PRIMARY GLM target** (intake-699: unsloth dynamic quants of `zai-org/GLM-5.2`, MIT, 1M context; supersedes GLM-5.1). 2026-07-16 correction: the old "PR #21149 is the gating dependency" statement is superseded; v6 contains generic DSA via #23346. The live gate is now GLM-5.2 UD-IQ2_M completion, integrity verification, load-smoke, and long-context DSA-indexer engagement.
- **Note**: #19460 remains a superseded tensor-loading PR, and #21149 remains useful historical design context, but neither is the current activation blocker. See [`glm51-reap-cpu-evaluation.md`](glm51-reap-cpu-evaluation.md) for the GLM-side disposition.

## 2026-07-25 v8-audit note — HIP LIGHTNING_INDEXER bf16 backend-op failure CLASSIFIED (pre-existing baseline, flaky)

During v8-candidate gating (`experimental-v8-refresh-20260724`), `test-backend-ops -o
LIGHTNING_INDEXER -p type_K=bf16` fails on MI210 HIP with ERR≈1.0 (vs 1e-6 tol) — and the
paired differential proves it is **NOT a v8 delta**: production v7 failed 8/12 bf16 configs,
candidate 6/12 (identical clean-env invocation); isolated 5-rep single-config runs show it is
**flaky** (production failed rep 5/5, candidate 0/5). Durable evidence:
`epyc-inference-research/data/kernel-v8-candidate/lightning-indexer-v7-v8-{baseline,isolated}/`.
This is a real pre-existing HIP bf16 LIGHTNING_INDEXER kernel bug in the landed #23346 code —
not a promotion blocker, but it means the DSA indexer's bf16 K-cache path is numerically
untrustworthy on gfx90a until root-caused.

- [ ] **D4 — root-cause the HIP bf16 LIGHTNING_INDEXER numerical failure** (flaky, ERR≈1.0,
  6-8/12 configs, both v7 and v8): suspect reduction-order/precision in the WMMA-era kernel on
  gfx90a or a bf16 staging issue; f16 configs pass. Low priority (no production lineup uses a
  bf16 indexer K-cache today) but file upstream if confirmed in current master. Evidence paths
  above; classification work done 2026-07-25.

## Progress checklist

- [x] D1 pull/build/smoke PR #21149 — SUPERSEDED: DSA landed in v6 via generic-DSA #23346 (`deepseek32` + `glm-dsa` archs present); no draft-PR pull needed; smoke-test moved to the model-eval handoffs. ✅ 2026-07-16
- [x] Weekly monitoring of PR #21149 to merge-readiness — MOOT: DSA landed via #23346; stopped tracking #21149. ✅ 2026-07-16
- [x] Re-anchor D2/D3 to the LANDED #23346 code, not the fairydreaming draft. ✅ 2026-07-16
- [x] Run the static D2 landed-code audit: top-k selection is shared across prompt/decode, but final attention appears dense/mask-based. ✅ 2026-07-16
- [x] Close D2 with runtime evidence: current-source GLM-5.2 fixed-`indexer_top_k=32` KV-length scaling classified final attention as `DSA-DENSE-MASK` ✅ 2026-07-17
- [x] Re-run D3.1 "is the CPU indexer compute-bound?" profiling check on landed code before any contribution work — CLOSED NO-GO; `ggml_compute_forward_lightning_indexer` was only `1.08%` of cycle samples in the OP-2/B4 GLM-5.2 profile. ✅ 2026-07-19
- [ ] D2 sparse-attention contribution — only if runtime profiling shows dense-mask attention still scales with full KV despite top-k
- [ ] D3 AVX-512BW Lightning Indexer CPU kernel — deferred because D3.1 did not show material indexer share; reopen only after D2 real-sparse or a different shape changes the profile.
- [ ] GLM-5.2 (754B GLM-MoE-DSA) activation — DSA forward-pass blocker now cleared in code; pending the GLM-5.2 UD-IQ2_M download + smoke-test in `glm51-reap-cpu-evaluation.md`
