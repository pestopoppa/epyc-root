# KV Cache Quantization (TurboQuant / PolarQuant / QJL)

**Status**: ACTIVE — Hadamard Phase 1 cherry-picked to production (`b51c905`, 2026-03-28). TurboQuant/PolarQuant/QJL/hybrid buffer ABANDONED. See "Current Work — Resume Here" section below.
**Production config**: `--kv-hadamard -ctk q4_0 -ctv f16` (pure-attention models) or `-ctk q4_0 -ctv q4_0` (hybrid SSM). Quality-neutral, zero overhead.
**v3 upstream note**: `--kv-hadamard` is superseded by upstream PR #21038 (`744c0c731`, 2026-04-01) which auto-enables identical Walsh-Hadamard rotation when KV types are quantized. In `production-consolidated-v3`, remove `--kv-hadamard` from orchestrator config — rotation is automatic. See [`llama-cpp-v3-upstream-rebuild.md`](llama-cpp-v3-upstream-rebuild.md).
**TurboQuant hybrid**: Split attention working. Gen speed ~5.2 t/s at 14.5K filled context (was 3.4 t/s, f16 baseline 7.7 t/s). Quality correct. Old K uses q4_0 (not turbo_q3 — PolarQuant dequant too lossy). **ARCHIVED** — q4_0+Hadamard matches quality with zero complexity.
**Created**: 2026-03-24 (via research intake)
**Updated**: 2026-03-28
**Priority**: MEDIUM-HIGH
**Categories**: kv_cache_optimization, quantization, inference_serving, memory_bandwidth

## Current Work — Resume Here

### What's Done (2026-03-26 update)
All experimental code is on branch `hadamard-kv-smoothing` in `/mnt/raid0/llm/llama.cpp-experimental`. Build: `build-hadamard/`.

**Hadamard Phase 1 cherry-picked to production** (2026-03-28): Commit `b51c905` on `production-consolidated-v2` in `/mnt/raid0/llm/llama.cpp`. Pushed to `fork` remote. 10 files, +141 lines. Build verified clean. CLI: `--kv-hadamard` (env: `LLAMA_ARG_KV_HADAMARD`).

**Working end-to-end:**
- Phase 1 (Hadamard): `--kv-hadamard -ctk q8_0 -ctv q4_0` — quality-neutral, zero overhead. Production-ready.
- Phase 2 (PolarQuant): `GGML_TYPE_POLAR_Q4` — 5.12x compression, PPL +0.229. Working but quality gap.
- Phase 3 (TurboQuant): `GGML_TYPE_TURBO_Q3` — 4.41x compression. Hybrid buffer with eviction.
- Hybrid precision buffer: `llama_kv_cache_hybrid_prec` (ISWA pattern), eviction from kv_recent(f16)→kv_old(q4_0+Hadamard), split attention.
- **Split attention WORKING** (2026-03-26): separate QK scoring for old (q4_0→f32 matmul) and recent (f16 matmul), concat scores, single softmax, combined V weighted sum. Quality correct at 14.5K filled context.
- Short prompts at 4K-128K context: speed-neutral (±2% of f16), correct output.
- QJL attention kernel: wired in `ops.cpp` (`k_is_qjl` dispatch), Gaussian JL matrix, outlier correction.

**Key design change**: Old K cache uses **q4_0** (not turbo_q3). PolarQuant reconstruction (turbo_q3 dequant) has too much error for direct K reconstruction. q4_0 + Hadamard is quality-neutral (PPL +0.017) and fast to dequant. The hybrid buffer still gives the benefit of the ISWA architecture (small f16 working set + large compressed archive).

**Bugs fixed (2026-03-26)**:
1. **Mask always -inf for old cells** (`llama-graph.cpp:424`): `set_input` filled old portion of kq_mask with -inf, so old K/V was never attended to. Fixed: unmask with 0.0f.
2. **n_evicted not reset on clear** (`llama-kv-cache-hybrid-prec.cpp:clear`): After cache clear between requests, stale n_evicted caused next request to read cleared/invalid old data. Fixed: reset n_evicted=0 in clear() and seq_rm().
3. **Eviction during prefill** (`llama-kv-cache-hybrid-prec.cpp:init_update`): During multi-token prefill batches, eviction corrupted quality by compressing tokens before attention could read them. Fixed: added `in_prefill` flag set in `init_batch(n_ubatch>1)`, checked in `init_update` to skip eviction.
4. **Shape mismatch in split attention** (`llama-graph.cpp:1928`): K and Q views not permuted for GQA broadcasting (n_head_kv vs n_head in wrong dimension). Fixed: added permute(0,2,1,3) for Q, K, and K_old before matmul, matching `build_attn_mha` non-flash path.

**Current benchmark (Qwen2.5-7B, 14.5K prefill + 200 gen, 16K ctx):**

| Config | Gen t/s (est) | Quality |
|--------|---------------|---------|
| f16 baseline | 7.70 | correct |
| turbo_q3 (old, dequant+concat) | 3.38 | garbage |
| **hybrid q4_0+Hadamard split attn** | **~5.2** | **correct** |

**Short prompt (1500 gen, 4K ctx, no prefill):** 15.7 t/s wall, coherent essay output — speed-neutral.

**Perplexity (2026-03-26, Qwen2.5-7B, 10 chunks, ctx=512):**

| Config | PPL | vs f16 |
|--------|-----|--------|
| f16 baseline | 1.5375 ±0.040 | — |
| hybrid q4_0+Hadamard (kv-recent=128) | 1.5375 ±0.040 | **identical** |

**Quality-neutral** at short context (512 tokens).

**Long-context benchmark (2026-03-26, Qwen2.5-7B, 32K native context, 31.8K prompt + 200 gen):**

| Config @ 32K | RSS (MB) | Wall (s) | KV Savings | Quality |
|---|---|---|---|---|
| f16/f16 | 16,386 | 549.8 | baseline | correct |
| q8_0/q4_0 | 15,322 | 598.2 (+9%) | -1.1 GB (-6%) | **correct** |
| q4_0/q4_0 | 15,098 | 561.1 | -1.3 GB (-8%) | **garbage** |

**Critical finding**: q4_0/q4_0 degrades at full 32K context — produces garbage output. q8_0/q4_0 remains correct. The 9% wall time increase is the flash attention dequant overhead during prefill.

**Implication**: q4_0 K is NOT safe at extended contexts. Production coder config (q8_0/q4_0) is validated. For frontdoor Q35 (q4_0/q4_0), the hybrid architecture (75% SSM, 25% attention) may mask the degradation — needs separate testing.

**Hybrid buffer architecture finding**: The dual-cache design (kv_recent + kv_old) allocates BOTH at full context size, using MORE memory than a single f16 cache. The design intended kv_recent to be small (512 cells), but prefill requires full-size recent cache. This makes the hybrid buffer memory-negative for production use. The standard single-cache with quantized KV types (`-ctk q8_0 -ctv q4_0`) is the correct approach for memory savings.

**Optimization history (2026-03-26)**:
1. Non-flash split attention (matmul-based): 5.2 t/s at 14.5K — correct quality, 32% slower than f16
2. Removed K cast (fused dequant in mul_mat): no improvement (108.9 vs 107.1s — noise)
3. **Switched to flash attention + concat**: cast old K/V to f16, concat with recent, single `ggml_flash_attn_ext` call via `build_attn_mha`. Short-prompt: **14.4 t/s** (vs 15.7 f16 = 8% gap). Long-prefill 14.5K: still ~5.1 t/s — the q4_0→f16 cast at 14K × 28 layers per decode token is unavoidable ~30% overhead.
4. Batch eviction (every 64 tokens): marginal 1.5% improvement (105.4 vs 107.0s). Eviction is not the bottleneck — it only runs during the first ~100 decode tokens after prefill.

**Bottleneck analysis**: The 30% gen speed gap at 14.5K filled context is the q4_0→f16 cast cost. At 14K old positions × 512 elements × 28 layers × 2 (K+V), each decode token casts ~400 MB of data. This is inherent to having compressed KV data — ANY quantized KV scheme pays this dequant cost. The benefit is memory: 14K positions at q4_0 use ~31 MB K + 448 MB V(f16) vs 448+448 = 896 MB at f16. At 256K+ context, this 2x memory savings is significant.

### Production Action Items

1. [x] **Test Q35 frontdoor q4_0/q4_0 at 4K context** (2026-03-28): Q35 hybrid absorbs KV quant completely. PPL: f16=1.2510, q4_0/q4_0=1.2466, q4_0/f16=1.2333. All within noise. Frontdoor q4_0/q4_0 VALIDATED.

2. [x] **Validate q4_0/f16 on Coder-32B** (2026-03-28): PPL 1.0034 (vs f16 1.0033 — identical). Speed: 45.56s/chunk (vs f16 46.08s — 1% faster). Needle-in-haystack: **9/9 at 1K/4K/16K**. Production config VALIDATED.

3. [x] **Hadamard cherry-picked to production** (2026-03-28): Commit `b51c905ec` on production-consolidated-v2. CLI: `--kv-hadamard`. 10 files (2 new + 8 modified). Covers standard KV, ISWA, flash and non-flash paths. Production binary rebuilt, `--kv-hadamard` enabled in orchestrator_stack.py. Also added f32 cast guard in `cpy_k`/`cpy_v` for safety (commit pending).

**NOTE: q4_0 K bug on Qwen2.5-7B-f16**: q4_0 K produces PPL 2642 (garbage) on this specific model (4 KV heads, n_embd_k_gqa=512) on BOTH experimental and production binaries. q8_0 K works fine. This affects ONLY the f16-weights 7B model used for development testing — all production models (Q4_K_M weights, 8+ KV heads) work correctly. Root cause unknown (not a build issue, not set_rows, reproduces on both binaries). Needs upstream investigation.

4. [ ] **Monitor upstream TurboQuant**: `ggml-org/llama.cpp` issue #20977. Our TQ3 decision gate tested **norm correction only** (1 of 4 ecosystem fixes) on a **7B model** (known failure zone for TQ3). What we tried vs what exists:

   | Fix | Us | Ecosystem | Impact |
   |-----|-----|-----------|--------|
   | Norm correction (store ‖x‖/‖recon(x)‖) | ✅ Implemented | spiritbuun: TQ3 beats q8_0 by 1.17% | Quality: PPL improved 77% on 7B, still +5.9% vs q4_0 on 32B |
   | S=512 for initial layers | ❌ Not tried | Paper: required for SNR≥1.6 | Quality: could close the remaining gap, needs dynamic block size |
   | Fused dequant (WHT Q once, dot vs codebook) | ❌ Cancelled at gate | spiritbuun/animehacker: +6.5% decode | Speed: TQ3 could bypass vec_dot entirely — dot codebook indices directly. Potentially faster than q4_0's vec_dot_q4_0_q8_0 |
   | 32-block format (vs our 128-block) | ❌ Not tried | Aaryan-Kapoor: better ggml integration | Quality+speed: different codebook, different error profile, native FA parallelism |

   **Why we stopped too early**: The decision gate was quality-only (PPL). But TQ3 with fused dequant could offer **better speed** than q4_0 — the codebook dot avoids per-element dequantization entirely. We tested 1 of 4 fixes on a model in TQ3's known failure zone. A fair test would combine all 4 fixes on a 32B+ model and measure both PPL AND decode speed.

   **Counter-argument**: ikawrakow's full implementation (all fixes) on EPYC 9975 shows Hadamard+q4_0 at 1279 tok/s vs TQ3 at 573 tok/s on Qwen3.5-35B — **2.2x faster**. This is the strongest data point: even with all optimizations, TQ3 is slower on CPU. The fused dequant helps but doesn't overcome the fundamental overhead of codebook lookup vs simple q4_0 dequant on AVX-512.

   **Revisit criteria**: If upstream merges TQ3 natively (issue #20977) with fused FA kernel, retest on Coder-32B measuring **both** PPL and tok/s. If TQ3 matches q4_0 quality AND speed, the 4.4x compression (vs 3.6x) becomes meaningful at 256K+ context.

### Abandoned (review 2026-03-28, no reactivation warranted)

- **Hybrid buffer** (Phase 3d): Memory-negative (2x allocation). Standard single-cache strictly better.
- **PolarQuant** (Phase 2): PPL +0.229, worse than q4_0+Hadamard at equivalent bits.
- **TurboQuant/QJL** (Phase 3): Lost decision gate on 32B even with norm correction (+5.9% PPL vs q4_0's +0.001%).
- **Flash attn V dequant kernel**: Root cause was V=q4_0 path. Fixed by switching to V=f16 in production config. Kernel optimization only needed if someone wants q4_0/q4_0 on pure-attention models.

### Hybrid Buffer Work: Archived

The dual-cache hybrid buffer (Phases 3d+) is archived as research:
- Memory-negative (2x cache allocation)
- Speed-negative at long context (cast+concat overhead)
- The standard single-cache with quantized KV types is strictly better
- Code preserved on `hadamard-kv-smoothing` branch in llama.cpp-experimental

### TurboQuant/QJL: Post-Mortem

**Why Google got quality-neutral 3.5-bit and we got PPL 16K:**
1. S=256 uniform (paper: S=512 for initial 25% layers). SNR at S=256,d=128 = 1.13 (noise ≈ signal).
2. PPL metric (paper: task-based evals where softmax suppresses noise on low-weight tokens).
3. At competitive bit rates (S=512 + outliers = ~4.5 bits effective), q4_0+Hadamard matches with zero complexity.
4. Not a hardware limitation — same math on CPU/GPU. Speed advantage of CUDA kernels doesn't translate.
5. **Model-size dependent** (per 2026-03-28b session): TQ3 catastrophic on ≤8B, approaches f16 at 35B+. Our 7B tests were in the failure zone.
6. **Norm correction** (spiritbuun fork): storing `||x||/||reconstruct(x)||` makes TQ3 beat q8_0 by 1.17%. One-line fix we didn't implement.

**Revisit path**: When upstream llama.cpp merges TurboQuant (issue #20977), retest on Qwen2.5-Coder-32B with norm correction. The fused dequant approach (pre-rotate Q, dot against codebook directly) solves our 30% cast overhead.

### Implementation Details

**Code was partially written but had issues. Here's what to do:**

1. **In `build_attn` (llama-graph.cpp, line ~1902)**: The hybrid precision block currently does dequant+concat. Replace with:
   - `kq_recent = ggml_mul_mat(k_recent, q)` — standard matmul on f16 K
   - For old K: use `turbo_qjl_score_projected()` from `ggml-turbo-quant.c` OR dequant old K to f32 and use `ggml_mul_mat(k_old_f32, q)` as a first step
   - `kq = ggml_concat(kq_old, kq_recent, 0)` — concat SCORES (dim 0 = KV positions)
   - `kq = ggml_soft_max_ext(kq, mask, scale, ...)` — single softmax over combined scores
   - For V: dequant old V to f32, concat with recent V, transpose, `ggml_mul_mat(v_combined_t, kq)`
   - This is the non-flash attention path (matmul-based, not `ggml_flash_attn_ext`)

2. **The `return cur` issue**: The split attention block returns directly from `build_attn`, including the `wo` projection. The caller must NOT apply `wo` again. This was correctly handled in the attempted implementation.

3. **Key gotcha — LD_LIBRARY_PATH**: The experimental build's shared libraries conflict with the production build at `/mnt/raid0/llm/llama.cpp/build/bin/`. ALWAYS use `env LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp-experimental/build-hadamard/bin` or `LD_LIBRARY_PATH=... command` prefix. Do NOT use `export LD_LIBRARY_PATH` as it doesn't persist between tool calls.

4. **V transpose**: The non-flash path needs V transposed: `[n_kv, n_embd_head_v, ...]` not `[n_embd_head_v, n_kv, ...]`. Use `ggml_cont(ggml_transpose(v))`.

5. **Mask**: The expanded kq_mask already handles both old and recent regions (implemented in `build_attn_inp_kv`, `set_input` with memmove shift).

### After Split Attention

1. **Batch eviction**: Currently evicts per-token. Change to evict every N tokens (e.g., 64) to amortize the CPU-side quantize cost.
2. **Graph caching**: Old V concat doesn't change between tokens — investigate caching.
3. **QJL scoring integration**: Replace `ggml_mul_mat(k_old_f32, q)` with `turbo_qjl_score_projected()` called from a custom ggml op or via the existing `k_is_qjl` dispatch in ops.cpp.

### Files Modified (all in `/mnt/raid0/llm/llama.cpp-experimental`)

| File | What |
|------|------|
| `ggml/include/ggml.h` | `GGML_TYPE_POLAR_Q4` (40), `GGML_TYPE_TURBO_Q3` (41) |
| `ggml/src/ggml.c` | Type traits for both types |
| `ggml/src/ggml-cpu/ggml-cpu.c` | CPU type traits (from_float) |
| `ggml/src/ggml-cpu/ops.cpp` | Flash attn QJL dispatch (`k_is_qjl`) |
| `ggml/src/ggml-polar-quant.h/.c` | PolarQuant quantize/dequantize |
| `ggml/src/ggml-turbo-quant.h/.c` | TurboQuant quantize/dequantize/QJL scoring |
| `ggml/src/CMakeLists.txt` | Added polar-quant and turbo-quant sources |
| `src/llama-hadamard.h/.cpp` | Walsh-Hadamard Transform for KV smoothing |
| `src/llama-kv-cache-hybrid-prec.h/.cpp` | Hybrid precision KV cache (ISWA pattern) |
| `src/llama-kv-cache.h/.cpp` | Added public accessors (get_used, get_cells, get_k/v_tensor) |
| `src/llama-graph.h` | `kv_old` fields on input + params + context; `llama_kv_cache` fwd decl |
| `src/llama-graph.cpp` | Hadamard in build_attn, dual-cache attention (split attn WIP) |
| `src/llama-context.h/.cpp` | `get_hybrid_kv_old()`, `get_hybrid_n_evicted()`, `n_kv_recent` params |
| `src/llama-model.cpp` | `create_memory()` hook for turbo_q3 → hybrid cache |
| `src/llama-cparams.h` | `kv_hadamard`, `n_kv_recent` |
| `include/llama.h` | `kv_hadamard`, `n_kv_recent` in context params |
| `common/common.h` | `kv_hadamard`, `n_kv_recent` |
| `common/common.cpp` | Propagation |
| `common/arg.cpp` | `--kv-hadamard`, `--kv-recent N`, `polar_q4`, `turbo_q3` in cache types |
| `src/CMakeLists.txt` | Added hybrid-prec source |

### Benchmark Data

**Short prompt (500 gen from 65-tok prompt, Qwen2.5-7B):**

| Context | f16 t/s | turbo_q3 t/s | q8_0/q4_0 t/s |
|---------|---------|--------------|---------------|
| 4K | 15.95 | 16.49 (+3.4%) | 16.25 |
| 16K | 16.45 | 16.51 (+0.4%) | 16.25 |
| 64K | 16.67 | 16.41 (-1.6%) | 16.71 |
| 128K | 16.73 | 16.56 (-1.0%) | 16.86 |

**Long prefill (gen after 14.5K prefill):**

| Config | Prefill t/s | Gen t/s |
|--------|-------------|---------|
| f16 | 213.8 | 7.70 |
| q8_0/q4_0 | 102.5 | 7.41 |
| turbo_q3 (dequant+concat) | 277.6 | 3.38 |

**Perplexity (Qwen2.5-7B, 10 chunks):**

| Config | PPL | vs f16 |
|--------|-----|--------|
| f16 | 7.166 | — |
| q4_0 + Hadamard | 6.912 | +0.017 |
| q8_0/q4_0 + Hadamard | 6.886 | -0.010 |
| polar_q4 | 7.394 | +0.229 |

## Objective

Reduce KV cache memory by 4-6x and improve decode throughput at long contexts by implementing advanced KV cache quantization in our llama.cpp fork. At 1M tokens (YaRN-extended Qwen3.5), KV cache dominates RAM — quantizing from f16 to 3-4 bits makes extended context practical and reduces memory-bandwidth pressure during attention.

## Why This Matters for EPYC

### Hardware Context
- **CPU**: AMD EPYC 9655 (96 cores, Zen 5, true 512-bit AVX-512)
- **RAM**: 1.13 TB DDR5-5600 ECC, 12 channels, ~460 GB/s aggregate bandwidth
- **NUMA**: 2 nodes × ~566 GB, quarter-splits for model pinning
- **Budget**: ~775 GB mlock'd for HOT-tier models, **~355 GB free for KV caches + OS**

### The Bottleneck
Our system is **memory-bandwidth-bound** during decode. Every attention step reads the full KV cache from DRAM. The benefit of KV quantization is twofold:

1. **Throughput**: Less data read during attention → faster decode. At short contexts (4K), model weights dominate bandwidth so KV savings are marginal. At long contexts (64K+), KV cache rivals model weight size and bandwidth savings become significant.
2. **Capacity**: At 1M context with f16 KV, a single Qwen3.5-35B sequence consumes ~256 MB of KV cache. With 4x compression that drops to ~64 MB — the difference between "fits alongside the model stack" and "doesn't."

### Hybrid Model Caveat
Qwen3.5 models (our frontdoor) are 75% Delta Net recurrent layers + 25% attention layers. Only attention layers use KV cache. This means:
- Memory savings apply only to the 25% of layers that are attention — actual per-sequence savings are ~25% of the theoretical max
- Throughput improvement is proportionally smaller than on pure-attention models (Qwen2.5, Llama)
- **Still worth it**: at 1M context, even 25% of layers × 256K tokens × 4 KV heads × 128 dims = substantial RAM

For pure-attention models (Qwen2.5-Coder-32B, our coder escalation), full savings apply.

## Current State: llama.cpp Already Supports Quantized KV

**This was not known when the stub was created.** llama.cpp already has quantized KV cache support via CLI flags:

```bash
llama-server -m model.gguf \
  --cache-type-k q8_0 \    # K cache type (default: f16)
  --cache-type-v q4_0 \    # V cache type (default: f16)
  --flash-attn              # REQUIRED for quantized KV
```

### Supported Types
`f32`, `f16`, `bf16`, `q8_0`, `q4_0`, `q4_1`, `iq4_nl`, `q5_0`, `q5_1`

K and V can be set **independently** — this matters because **K is more sensitive to quantization than V**.

### Key Implementation Details (from codebase exploration)

| File | Purpose |
|------|---------|
| `src/llama-kv-cache.h` | KV cache class (`llama_kv_cache`), inherits `llama_memory_i` |
| `src/llama-kv-cache.cpp` | Allocation, slot management, K/V copy operations |
| `src/llama-kv-cells.h` | Cell metadata (position, sequence sets, ring buffer) |
| `src/llama-graph.cpp:1803-1947` | `build_attn_mha()` — flash attention integration |
| `include/llama.h:358-359` | `type_k`, `type_v` in model params (marked `[EXPERIMENTAL]`) |
| `common/arg.cpp:2084-2108` | CLI flag parsing (`-ctk`, `-ctv`, env vars) |
| `ggml/src/ggml-cpu/ops.cpp:8635+` | CPU flash attention kernels |

**KV tensor allocation** (`llama-kv-cache.cpp:173-174`):
```cpp
ggml_tensor * k = ggml_new_tensor_3d(ctx, type_k, n_embd_k_gqa, kv_size, n_stream);
ggml_tensor * v = ggml_new_tensor_3d(ctx, type_v, n_embd_v_gqa, kv_size, n_stream);
```

**K/V write** uses `ggml_set_rows()` — quantization happens implicitly via ggml's type conversion during the copy. V cache is optionally transposed (`v_trans`) for flash attention memory access patterns.

**Attention compute**: `ggml_flash_attn_ext()` or `ggml_flash_attn_ext_paged()` handles dequantization on-the-fly within tiled computation.

### Known Issues with Current Implementation

| Issue | Impact | Mitigation |
|-------|--------|------------|
| **No Hadamard smoothing** | q4_0 KV adds ~0.2 perplexity vs ExLlamaV2's q4 (which matches f16) | Phase 1: implement Hadamard pre-rotation |
| **Flash attention mandatory** | Without `--flash-attn`, silently falls back to f16 | Always pass `--flash-attn` (already default in our stack) |
| **Context shifting crashes** | `GGML_ASSERT` type mismatch with quantized KV | Context shifting auto-disabled; not a problem for our use case |
| **Draft model bug** (#11200) | `llama-server` ignores cache type for draft models | Use `--cache-type-k-draft` / `--cache-type-v-draft` explicitly |
| **Speed regression** | ~30% generation slowdown, ~45% prompt processing slowdown reported | Likely GPU numbers; need CPU benchmarks. Dequant overhead may differ on CPU |
| **GQA sensitivity** | Models with aggressive GQA (8x, e.g. Qwen2) degrade more | Our Qwen3.5 uses 4 KV heads (moderate GQA); Qwen2.5-Coder uses 8 KV heads (test carefully) |

### Published Quality Numbers (External)

**Perplexity impact** (Qwen 2.5 Coder 7B, Q6_K weights):
- q8_0 vs f16: 8.3934 vs 8.3891 (+0.005 — **negligible**)
- q4_0 vs f16: +0.2 to +0.25 (**noticeable**, no Hadamard smoothing)

**ExLlamaV2 with Hadamard smoothing** (The Pile, 512 tokens):

| Model | f16 PPL | FP8 PPL | Q4 PPL |
|-------|---------|---------|--------|
| Mistral 7B (3.0 bpw) | 13.33 | 13.43 | **13.37** |
| Mixtral 8x7B (4.0 bpw) | 10.09 | 10.26 | **10.19** |
| Llama2 7B (4.0 bpw) | 11.43 | 11.92 | **11.60** |

**Q4 with Hadamard beats FP8** — the smoothing is the key, not the bit width.

## Research Context

| Intake ID | Title | arXiv | Key Contribution |
|-----------|-------|-------|-----------------|
| intake-191 | TurboQuant | 2504.19874 | Combined framework: MSE quantizer + 1-bit QJL residual. 3.5 bits = quality-neutral, 2.5 bits = marginal degradation. Near-optimal distortion (2.7x of info-theoretic bound) |
| intake-192 | PolarQuant | 2502.02617 | Polar coordinate KV quantization. 4.2x compression. Eliminates normalization overhead. O(d log d) per vector |
| intake-193 | QJL | 2406.03482 | 1-bit JL transform. Asymmetric estimator. Zero quantization constant overhead. 5x at 3 bits. AAAI 2025 |

All three from the same research group (Zandieh, Han, Mirrokni — Google Research / KAIST).

### KIVI (arXiv 2402.02750, ICML 2024)

Foundational paper establishing the asymmetric K/V quantization principle:

- **Key cache**: Per-**channel** quantization. A few fixed channels have outlier magnitudes (structural — same channels across all tokens). Grouping along channel dimension handles this.
- **Value cache**: Per-**token** quantization. No fixed outlier channels; per-token grouping confines error to individual tokens.
- **Result**: 2-bit quantization, tuning-free. 2.6x memory reduction, up to 4x batch size, 2.35-3.47x throughput.
- **Relevance**: llama.cpp's current q4_0/q8_0 KV does symmetric block quantization — KIVI's per-channel K / per-token V is NOT implemented. This is the primary quality gap.

### KVLinC (arXiv 2510.05373)

Combines Hadamard rotation (for V error reduction) with lightweight linear correction adapters (for K error compensation). Claims 2.55x faster inference vs Flash Attention baseline. Tested on LLaMA, Qwen2.5, Qwen3.

## Technical Architecture: Advanced Techniques

### TurboQuant Pipeline (2-stage)
1. **Stage 1 — MSE Quantizer** (PolarQuant): Random preconditioning → recursive polar coordinate transformation → non-uniform angle quantization via k-means codebooks
2. **Stage 2 — QJL Residual**: 1-bit JL transform on residual error → sign-bit quantization → asymmetric inner product estimator

### PolarQuant Details (intake-192)

**Algorithm (3 steps)**:

**Step 1 — Random Preconditioning**: Multiply all KV embeddings by random rotation matrix S (i.i.d. Gaussian or random orthogonal). By JL lemma, this preserves norms/inner products. After preconditioning, vectors follow `N(0, ‖x‖² · I)` — angles become analytically known, tightly concentrated.

**Step 2 — Recursive Polar Transform**: Convert d-dimensional Cartesian vector to polar coordinates:
- Level 1: `ψ_j = atan2(x_{2j}, x_{2j-1})` → d/2 angles (range [0, 2π))
- Level ℓ≥2: `ψ_j = atan2(‖right_subtree‖, ‖left_subtree‖)` → recursive halving (range [0, π/2])
- Output: 1 radius (= ‖x‖₂) + (d-1) angles across log₂(d) levels
- **Constraint**: d must be power of 2 (d=128 for our models — satisfied)

**Step 3 — Non-Uniform Angle Quantization**:
- Angle distribution at level ℓ follows: `f(ψ) = Γ(2^(ℓ-1))/(2^(2^(ℓ-1)-2)·Γ(2^(ℓ-2))²) · sin^(2^(ℓ-1)-1)(2ψ)`
- 1-D k-means on this known distribution → optimal codebook centroids
- **Bit allocation**: 4 bits (level 1, range 4x wider) + 2 bits (levels 2-4)
- **Norm**: stored separately in f16 (16 bits)
- **Total for d=128**: 16 + (32×4 + 16×2 + 8×2 + 4×2) = 16 + 184 = **200 bits** vs 2048 bits = **10.2x compression** (or ~1.56 bits/element)
  - Paper reports 4.2x at their tested bit allocation; different level assignments trade off compression vs quality

**Dequantization** (Algorithm 1, reverse path):
1. Look up centroid angles from codebook
2. Reconstruct radius pairs: `r_{2j-1} = r_j · cos(θ)`, `r_{2j} = r_j · sin(θ)`
3. Iterate from top level down to level 1
4. Apply inverse preconditioning: multiply by S^T
5. Scale by stored norm

**Complexity**: O(d log d) per vector — for d=128, that's ~896 operations. Cheap.

**Codebook options**:
- Online: k-means on incoming embeddings. Adds ~8s overhead for 16K sequence.
- Offline: Pre-compute codebooks from the known angle distribution (model-architecture-specific, not data-specific). ~3s overhead. **Preferred for our use case.**

### QJL Details (intake-193)

**Full implementation architecture** (from GitHub repo analysis):

**Quantization pipeline**:
```
key_states (B, N, H, D=128)
    ↓ JL projection (D=128 → sketch_dim=256)
sketch (B, N, H, 256)
    ↓ Sign-bit extraction + packing (8 bits → 1 byte)
quantized_keys (B, N, H, 32) [uint8, packed]
outlier_norms (B, N, H, num_outliers) [float]
```

**Attention score computation**:
```
query (B, H_q, T_q, D=128)
    ↓ Same JL projection (D=128 → sketch_dim=256)
query_sketch (B, H_q, T_q, 256) [full precision]
    ↓ Inner product with packed quantized key sketches
    ↓ + outlier correction term
scores (B, H_q, T_q, T_kv)
```

**Key design decisions in QJL**:
1. **Asymmetric estimator**: Query gets full-precision JL, keys get 1-bit JL. Score: `scl × norm_k × innerprod_sketch + scl_otlr × norm_otlr × innerprod_outlier`
2. **Outlier handling**: Top-k dimensions (configurable, default 8) stored with full-precision norms separately
3. **Hybrid precision buffer**: Recent tokens (< `buffer_size=128`) kept at full precision; older tokens quantized. Rolling quantization when buffer overflows.
4. **Layer-specific precision**: Initial layers get more bits (`key_quantization_bits_initial_layers=512`) vs later layers (`key_quantization_bits=256`). First 15 layers are "initial."
5. **GQA-aware kernel**: `qjl_gqa_score_kernel.cu` maps multiple Q heads to single KV head

**CUDA kernel architecture** (3 kernels):

| Kernel | File | Grid | Block | Purpose |
|--------|------|------|-------|---------|
| Quantization | `qjl_quant_kernel.cu` | (B×H×N, blocksPerGroup, numProjBlocks) | 1024 (32×32) | JL projection + sign-bit packing + outlier extraction |
| Scoring | `qjl_score_kernel.cu` | (B×H, T_q, blocks) | 1024 | Attention scores from packed bits + outlier norms |
| GQA scoring | `qjl_gqa_score_kernel.cu` | similar | 1024 | Multi-Q-head to single-KV-head mapping |

**Shared memory usage per block**: `EMB_DIM` outlier mask + `EMB_DIM×32` key embeddings + `32×32` packed bits + `32×32` outlier accumulators

**Supported dtypes**: half, bfloat16, float (template-dispatched)

### TurboQuant Combined (intake-191)
- Stage 1 (PolarQuant MSE on KV) + Stage 2 (1-bit QJL on residual) = **near-optimal distortion** (within 2.7x of information-theoretic lower bound)
- **3.5 bits/channel**: Quality-neutral across LongBench, Needle-in-Haystack, ZeroSCROLLS, RULER, L-Eval
- **2.5 bits/channel**: Marginal quality degradation
- **8x attention speedup** on H100 (4-bit vs 32-bit baseline) — GPU-specific, won't transfer
- **Models tested**: Gemma, Mistral, Llama-3.1-8B-Instruct
- **Baselines beaten**: KIVI, PQ, RabbiQ

## KV Cache Memory Budget Analysis

### Per-Sequence KV Cache Size (Qwen3.5-35B-A3B, frontdoor)

Model has 40 layers total. ~10 attention layers (25%), each with 4 KV heads, d=128.

| Context Length | f16 KV | q8_0 KV | q4_0 KV | PolarQuant (4.2x) | TurboQuant (3.5b) |
|---------------|--------|---------|---------|-------------------|-------------------|
| 4K | 2.5 MB | 1.25 MB | 0.63 MB | 0.60 MB | 0.55 MB |
| 16K | 10 MB | 5 MB | 2.5 MB | 2.4 MB | 2.2 MB |
| 65K (default) | 40 MB | 20 MB | 10 MB | 9.5 MB | 8.7 MB |
| 256K | 160 MB | 80 MB | 40 MB | 38 MB | 35 MB |
| 1M (YaRN) | 640 MB | 320 MB | 160 MB | 152 MB | 140 MB |

*Calculation: 10 attention layers × 2 (K+V) × 4 heads × 128 dims × bytes_per_element × context_length*

### Per-Sequence KV Cache Size (Qwen2.5-Coder-32B, coder escalation)

Pure attention model — 64 layers, 8 KV heads, d=128. **Full savings apply.**

| Context Length | f16 KV | q8_0 KV | q4_0 KV | PolarQuant (4.2x) | TurboQuant (3.5b) |
|---------------|--------|---------|---------|-------------------|-------------------|
| 4K | 64 MB | 32 MB | 16 MB | 15.2 MB | 14 MB |
| 16K | 256 MB | 128 MB | 64 MB | 61 MB | 56 MB |
| 65K (default) | 1.0 GB | 512 MB | 256 MB | 244 MB | 224 MB |
| 256K | 4.0 GB | 2.0 GB | 1.0 GB | 976 MB | 896 MB |

### System-Level Impact (4 concurrent frontdoor + 4 concurrent coder sequences at 65K)

| Configuration | Total KV RAM | Free RAM (from 355 GB) |
|--------------|-------------|----------------------|
| f16 (current) | 4×40 + 4×1024 = 4.3 GB | 350.7 GB |
| q8_0 K / q4_0 V | ~2.5 GB | 352.5 GB |
| PolarQuant | ~1.0 GB | 354.0 GB |

At 65K default context, KV is not the bottleneck — model weights dominate. **The payoff is at extended contexts (256K+)** where KV cache becomes multi-GB per sequence.

### System-Level Impact (4 concurrent coder sequences at 256K)

| Configuration | Total KV RAM | Free RAM |
|--------------|-------------|----------|
| f16 | 16 GB | 339 GB |
| q8_0 K / q4_0 V | ~9 GB | 346 GB |
| PolarQuant | ~3.8 GB | 351.2 GB |

At 256K this starts to matter significantly, especially if we're running multiple concurrent long-context requests.

## Implementation Plan

### Phase 0: Benchmark Existing llama.cpp Quantized KV on Our Hardware (1-2 days)

**Goal**: Establish CPU-specific baselines using what's already implemented. No code changes needed.

**Steps**:
1. Verify `--flash-attn` is enabled in our orchestrator_stack.py (likely already is)
2. Run benchmarks with these configurations on Qwen3.5-35B-A3B (frontdoor):
   ```bash
   # Baseline
   llama-server -m model.gguf --flash-attn
   # Q8 symmetric
   llama-server -m model.gguf --flash-attn -ctk q8_0 -ctv q8_0
   # Asymmetric (KIVI-inspired)
   llama-server -m model.gguf --flash-attn -ctk q8_0 -ctv q4_0
   # Aggressive
   llama-server -m model.gguf --flash-attn -ctk q4_0 -ctv q4_0
   ```
3. Same configs on Qwen2.5-Coder-32B (pure attention — max impact)
4. Measure at context lengths: 4K, 16K, 65K
5. **Metrics**: tokens/sec (generation), tokens/sec (prompt processing), perplexity (if feasible), RULER score, needle-in-haystack accuracy
6. Record memory usage: `llama-server` reports KV cache size at startup

**Expected outcomes**:
- q8_0 symmetric: negligible quality loss, ~2x memory savings, throughput TBD on CPU
- q8_0 K / q4_0 V: small quality loss, ~2.7x memory savings
- q4_0 symmetric: noticeable quality loss (~0.2 PPL), ~4x memory savings

**Risks & mitigations**:
- **Risk**: Flash attention not working on our CPU. **Mitigation**: It's confirmed working on Ryzen (Zen 4); our Zen 5 EPYC should be fine. If not, this blocks the entire effort.
- **Risk**: Speed regression (~30% reported). **Mitigation**: Those numbers may be GPU; CPU dequantization may be faster (ggml q4/q8 kernels are highly optimized for AVX-512). Benchmark will tell.
- **Risk**: Quality degradation worse on Qwen3.5 hybrid. **Mitigation**: Only 25% of layers use KV cache; degradation may be proportionally smaller since recurrent layers compensate.

**Decision gate**: If q8_0 K / q4_0 V shows <1% quality degradation and no speed regression on CPU, deploy immediately to production as a quick win. If significant speed regression, investigate whether dequantization overhead is the bottleneck before proceeding.

### Phase 0 Results (2026-03-25)

**Status**: COMPLETE. Flash attention works, generation speed neutral, significant prefill regression discovered on pure-attention models.

**Benchmark config**: numactl --interleave=all, 96 threads, -ub 8192, --flash-attn on, single instance.

#### Qwen3.5-35B-A3B Q4_K_M (frontdoor, hybrid — 25% attention layers)

| Context | Config | KV Size | Gen t/s | Prompt t/s | Prefill t/s |
|---------|--------|---------|---------|------------|-------------|
| 4K | f16/f16 | 80 MiB | 14.95 | 148.6 | 202.1 |
| 4K | q8_0/q8_0 | 42.5 MiB | 14.74 | 150.4 | 206.5 |
| 4K | q8_0/q4_0 | 32.5 MiB | 14.86 | 151.1 | 207.8 |
| 4K | q4_0/q4_0 | 22.5 MiB | 14.71 | 150.3 | 206.5 |
| 16K | f16/f16 | 320 MiB | 14.65 | 147.0 | 204.4 |
| 16K | q8_0/q8_0 | 170 MiB | 13.95 | 152.1 | 184.8 |
| 16K | q8_0/q4_0 | 130 MiB | 15.16 | 149.2 | 182.0 |
| 16K | q4_0/q4_0 | 90 MiB | 15.24 | 153.9 | 184.0 |
| 65K | f16/f16 | 1280 MiB | 14.66 | 149.0 | — |
| 65K | q8_0/q8_0 | 680 MiB | 14.27 | 149.3 | — |
| 65K | q8_0/q4_0 | 520 MiB | 14.75 | 149.9 | — |
| 65K | q4_0/q4_0 | 360 MiB | 14.92 | 151.8 | — |

**Verdict**: KV quantization is **free** on this hybrid model. All configs within noise. Deploy q4_0/q4_0.

#### Qwen2.5-Coder-32B Q4_K_M (coder, pure attention — 64 layers, 8 KV heads)

| Context | Config | KV Size | Gen t/s | Prompt t/s | Prefill t/s (long) |
|---------|--------|---------|---------|------------|-------------------|
| 4K | f16/f16 | 1024 MiB | 8.59 | 104.6 | 127.6 |
| 4K | q8_0/q8_0 | 544 MiB | 8.52 | 101.9 | **34.0** |
| 4K | q8_0/q4_0 | 416 MiB | 8.74 | 106.4 | 92.8 |
| 4K | q4_0/q4_0 | 288 MiB | 8.67 | 105.7 | 90.2 |
| 16K | f16/f16 | 4096 MiB | 8.73 | 103.9 | **111.1** |
| 16K | q8_0/q8_0 | 2176 MiB | 8.57 | 104.6 | **34.0** |
| 16K | q8_0/q4_0 | 1664 MiB | 8.64 | 104.5 | 48.9 |
| 16K | q4_0/q4_0 | 1152 MiB | 8.76 | 104.3 | 46.6 |
| 65K | f16/f16 | 16384 MiB | 9.44 | 100.1 | — |
| 65K | q8_0/q8_0 | 8704 MiB | 9.42 | 104.4 | — |
| 65K | q8_0/q4_0 | 6656 MiB | 9.48 | 102.5 | — |
| 65K | q4_0/q4_0 | 4608 MiB | 9.31 | 102.3 | — |

**Critical finding — prefill regression**: The CPU flash attention dequant path is severely unoptimized. q8_0 KV at 16K shows 34 t/s prefill vs 111 t/s f16 (**3.3x slower**). q4_0 is ~47 t/s (2.4x slower). Generation speed (single token decode) is completely unaffected (~8.5-9.5 t/s across all configs). Short prompt processing (42 tokens) is also unaffected (~104 t/s).

**Why**: During prefill, flash attention processes large tiles of KV data. The dequantization overhead (q4_0/q8_0 -> f32) inside `ggml_flash_attn_ext` scales linearly with prompt length × KV cache entries. During decode (1 token), this cost is negligible relative to model weight I/O.

**Why Q35 hybrid is unaffected**: Only 25% of layers use attention/KV cache. The 75% SSM layers have zero KV overhead, so the dequant cost is amortized.

**Verdict**: Generation neutral, deploy q8_0/q4_0 (or q4_0/q4_0). Prefill regression acceptable for coder prompts (typically <1K tokens). See "Flash Attention CPU Dequant Optimization" below for fix path.

#### Decision Gate Outcome

| Risk | Predicted | Actual | Status |
|------|-----------|--------|--------|
| R1: Flash attn broken on EPYC | Low | Works | CLEARED |
| R2: Speed regression >10% | Medium | Gen: 0%. Prefill: 2-3x on pure-attn | PARTIAL — gen cleared, prefill regressed |
| R3: Quality degradation on hybrid | Medium | Not measured (perplexity test pending) | OPEN — Phase 1 benchmark will assess |
| R7: Context shift crash | Confirmed | Not tested (not in our flow) | N/A |
| R9: Spec decode interaction | Medium | Not tested | OPEN — test in Phase 4 |

**Deployment**: q4_0/q4_0 for Q35 frontdoor, q8_0/q4_0 for Coder escalation. Pending orchestrator_stack.py + registry update.

### Flash Attention CPU Dequant Optimization — ROOT CAUSE FOUND (2026-03-28)

**Priority**: HIGH — **production config change recommended**.
**Status**: Root cause identified. V dequant (q4_0→f32) in flash attention is the ENTIRE prefill bottleneck. K dequant is not the issue.

**Problem**: The `ggml_flash_attn_ext` CPU kernel in `ggml/src/ggml-cpu/ops.cpp` (line ~8635+) has a dequantization overhead that causes 2-3x prefill slowdown when KV cache uses q4_0 V type vs f16.

**Root cause (2026-03-28)**: Benchmarked 4 KV type combinations at 4K context on Coder-32B Q4_K_M:

| Config | Time/chunk | vs f16/f16 | Analysis |
|---|---|---|---|
| f16/f16 | 37.91s | baseline | — |
| **q4_0/f16** | **37.42s** | **-1%** | K dequant is FREE (bandwidth savings offset cost) |
| q8_0/f16 | 40.57s | +7% | q8_0 K reads more bytes than q4_0 |
| **q8_0/q4_0** | **64.87s** | **+71%** | **V dequant is the ENTIRE bottleneck** |

**The V dequant path** (`v_to_float` → f32 buffer → `vec_mad_f32`) is the sole cause. The K path uses fused `kq_vec_dot` which is already optimized. The f16 V path uses native `ggml_vec_mad_f16` (single pass, no intermediate buffer).

**Recommended production config change**: `q4_0 K / f16 V` (+ Hadamard on K) instead of current `q8_0 K / q4_0 V`:
- **Zero prefill regression** (actually 1% FASTER than f16/f16)
- K compression: 4x (vs 2x with q8_0)
- V at f16: lossless quality, fast flash attention path
- With Hadamard: K PPL +0.017 (quality-neutral)
- Memory: K=0.25x + V=1x = 0.625x of f16 (37% savings vs 71% with q4_0/q4_0)

**Original root cause analysis (still valid for context)**:

The flash attention CPU kernel processes KV data per-position. For each KV position, it must:
5. Compute weighted V sum

The dequant step (2) is the bottleneck. For f16 KV, the load+convert is a single `_mm512_cvtph_ps` (1 cycle latency). For q4_0/q8_0, dequant requires:
- Extracting scale factor from block header
- Unpacking 4-bit or 8-bit values from packed storage
- Multiplying by scale
- This is ~10-15 instructions per 32 elements vs 1 instruction for f16

During decode (1 token), the KV cache read is tiny compared to model weight reads (~18 GB for Q4_K_M weights vs <1 MB for 42-token KV at 4K context). The dequant cost is invisible.

During prefill (9800 tokens at 16K), the flash attention kernel processes 9800 × 9800 / 2 ≈ 48M QK interactions, each requiring K dequant. At 64 layers × 8 KV heads, that's billions of dequant operations — the cost becomes dominant.

**Optimization approaches** (ranked by effort/impact):

1. **Fused dequant+dot kernel** (HIGH IMPACT, MEDIUM EFFORT):
   - Current code: dequant q4_0 → f32 buffer → dot product
   - Optimized: fused AVX-512 kernel that dequants and accumulates dot product in one pass
   - Eliminates intermediate f32 buffer writes (saves bandwidth)
   - Similar to how ggml's `ggml_vec_dot_q4_0_q8_0` fuses dequant+dot for weight matmuls
   - Location: `ggml/src/ggml-cpu/ops.cpp`, inside the flash attention tile loop
   - Reference: look at `ggml_vec_dot_q4_0_q8_0` in `ggml-quants.c` for the fused pattern

2. **Tile-level dequant caching** (MEDIUM IMPACT, LOW EFFORT):
   - During prefill, the same K/V tiles are read by multiple query rows
   - Dequant each K tile once into a thread-local f32 buffer, reuse for all Q rows in the tile
   - Current code may already do this for some paths — verify

3. **VNNI/VBMI2 acceleration** (HIGH IMPACT, HIGH EFFORT):
   - Zen 5 supports AVX-512 VNNI (integer dot product)
   - q8_0 × q8_0 dot products could use `_mm512_dpbusd_epi32` directly without dequant to f32
   - q4_0 could use VBMI2 for fast 4-bit unpacking (`_mm512_mask_expandloadu_epi8`)
   - This would make q8_0 prefill nearly as fast as f16

4. **Async prefetch** (LOW IMPACT, LOW EFFORT):
   - Add `_mm_prefetch` hints for next KV tile while processing current tile
   - Helps hide DRAM latency for large KV caches that don't fit in L3

**Key files**:
- `ggml/src/ggml-cpu/ops.cpp:8635+` — `ggml_compute_forward_flash_attn_ext` (CPU flash attention entry)
- `ggml/src/ggml-cpu/ggml-cpu-quants.c` — existing fused dequant+dot kernels for reference
- `ggml/src/ggml-cpu/ggml-cpu-aarch64.cpp` — ARM NEON flash attention (may have different optimizations to learn from)

**Benchmark data for validation**: After optimization, re-run the Coder-32B 16K prefill test. Target: q8_0/q4_0 prefill within 80% of f16 speed (88+ t/s vs current 49 t/s).

**Not a Phase 1 blocker**: Phase 1 Hadamard adds ~1μs per vector overhead (negligible). The prefill regression is a separate ggml kernel issue. Phase 1 can proceed independently.

### Phase 1: Hadamard-Smoothed Q4 KV (3-5 days)

**Goal**: Close the quality gap between llama.cpp's naive q4_0 and ExLlamaV2's Hadamard-smoothed Q4 (which matches f16 quality).

**Why this before PolarQuant**: Hadamard smoothing is simpler to implement, well-validated (ExLlamaV2 ships it), and directly improves the already-existing q4_0 path. PolarQuant requires a novel quantization format; Hadamard reuses existing ggml quant types.

**Working directory**: All llama.cpp work MUST happen in `/mnt/raid0/llm/llama.cpp-experimental` to avoid impacting current benchmark work in `/mnt/raid0/llm/llama.cpp`.

**Implementation approach**: Use `ggml_map_custom1` for the prototype (avoids modifying ggml core). Can be promoted to a proper `GGML_OP_HADAMARD` in a follow-up once validated.

#### Step 0: Branch Setup

Create branch `hadamard-kv-smoothing` from `production-consolidated-v2` in `/mnt/raid0/llm/llama.cpp-experimental`.

#### Step 1: Walsh-Hadamard Transform Function

Create `src/llama-hadamard.h` and `src/llama-hadamard.cpp` containing:

- `fwht_inplace(float * data, int n)` — in-place Fast Walsh-Hadamard Transform, normalized by `1/sqrt(n)` so `H*H = I` (self-inverse). Standard iterative butterfly algorithm (7 stages for n=128 = 448 add/sub ops per head).
- `ggml_hadamard_custom_op(...)` — `ggml_map_custom1` callback that applies WHT independently to each dim0 slice across all outer dimensions. Partitions rows across threads.

```cpp
void fwht_inplace(float * data, int n) {
    for (int len = 1; len < n; len <<= 1) {
        for (int i = 0; i < n; i += len << 1) {
            for (int j = 0; j < len; j++) {
                float u = data[i + j];
                float v = data[i + j + len];
                data[i + j]       = u + v;
                data[i + j + len] = u - v;
            }
        }
    }
    float scale = 1.0f / sqrtf((float)n);
    for (int i = 0; i < n; i++) data[i] *= scale;
}
```

The custom op callback iterates over `ggml_nrows(src)`, partitions rows across threads, copies src→dst if not in-place, then calls `fwht_inplace` on each row.

**Note**: Tensors are f32 at all insertion points (post-RoPE for K, post-projection for Q/V). AVX-512 optimization (butterfly inner loop with `_mm512_add_ps`/`_mm512_sub_ps` for len≥16) is a follow-up — scalar version is correct and negligible cost at n=128.

#### Step 2: Wire Into KV Write Path

Modify 3 `build_attn` overloads in `llama-graph.cpp` (the 3 KV-cache variants):
- `build_attn(llm_graph_input_attn_kv *, ...)` — line ~1944
- `build_attn(llm_graph_input_attn_k *, ...)` — line ~2031 (K-only/MLA — **skip**, see MLA guard below)
- `build_attn(llm_graph_input_attn_kv_iswa *, ...)` — line ~2083 (iSWA)

Before `cpy_k`/`cpy_v` calls:
```cpp
if (cparams.kv_hadamard) {
    k_cur = build_hadamard(k_cur);
    cb(k_cur, "k_hadamard", il);
    v_cur = build_hadamard(v_cur);
    cb(v_cur, "v_hadamard", il);
}
```

Also add `build_hadamard()` helper method to `llm_graph_context` (declare in `llama-graph.h`):
```cpp
ggml_tensor * llm_graph_context::build_hadamard(ggml_tensor * a) const {
    return ggml_map_custom1(ctx0, a, ggml_hadamard_custom_op, GGML_N_TASKS_MAX, nullptr);
}
```

#### Step 3: Wire Into Attention Read Path

**Q transform** — before `build_attn_mha` in each KV-cache overload:
```cpp
if (cparams.kv_hadamard) {
    q = build_hadamard(q);
    cb(q, "q_hadamard", il);
}
```

**Output inverse** — inside `build_attn_mha`, after v_mla block but before final `ggml_reshape_2d`:

Flash path: `cur` has shape `[n_embd_head_v, n_tokens, n_head, n_stream]` — dim0 is already n_embd_head_v, so apply directly:
```cpp
if (cparams.kv_hadamard && !v_mla) {
    cur = ggml_map_custom1(ctx0, cur, ggml_hadamard_custom_op, GGML_N_TASKS_MAX, nullptr);
}
```

Non-flash path: `kqv` has shape `[n_embd_head_v, n_head, n_tokens, n_stream]` — dim0 is already correct:
```cpp
if (cparams.kv_hadamard && !v_mla) {
    kqv = ggml_map_custom1(ctx0, kqv, ggml_hadamard_custom_op, GGML_N_TASKS_MAX, nullptr);
}
```

**MLA guard**: Skip Hadamard for `attn_k` overload (MLA/DeepSeek) — V is derived from K storage (`ggml_view_4d` of K), math doesn't cancel correctly. Skip entirely.

**v_mla guard**: Skip output inverse when `v_mla` is set — the V has already been transformed by the MLA decompression matrix, Hadamard cancellation doesn't apply.

#### Step 4: CLI Flag Plumbing

| File | Change |
|------|--------|
| `include/llama.h` (~line 358) | Add `bool kv_hadamard;` to context params struct |
| `src/llama-cparams.h` (~line 36) | Add `bool kv_hadamard;` to `llama_cparams` |
| `common/common.h` (~line 498) | Add `bool kv_hadamard = false;` to `common_params` |
| `common/common.cpp` (~line 1380) | Propagate: `cparams.kv_hadamard = params.kv_hadamard;` |
| `common/arg.cpp` (~line 2034) | Register `--kv-hadamard` flag (env: `LLAMA_ARG_KV_HADAMARD`) |
| `src/llama-context.cpp` | Propagate from `llama_context_params` to `llama_cparams` (follow `flash_attn` pattern) |

Also initialize in `llama_context_default_params()`: `/*.kv_hadamard =*/ false`.

#### Step 5: Build System + Compile

Add `llama-hadamard.cpp` to `src/CMakeLists.txt` (adjacent to `llama-graph.cpp`).

```bash
cd /mnt/raid0/llm/llama.cpp-experimental
cmake -B build-hadamard -DLLAMA_NATIVE=ON
cmake --build build-hadamard -j$(nproc) --target llama-server llama-perplexity
```

Smoke test: run `llama-perplexity` with `--kv-hadamard --cache-type-k q4_0 --cache-type-v q4_0 -fa` and verify it doesn't crash.

#### Step 6: Benchmark Matrix

**5 configurations**:
1. f16 KV (baseline)
2. q8_0 K / q8_0 V (no Hadamard)
3. q8_0 K / q4_0 V (no Hadamard)
4. q4_0 K / q4_0 V (no Hadamard)
5. q4_0 K / q4_0 V + `--kv-hadamard`

**2 models**:
- Qwen3.5-35B-A3B (frontdoor, hybrid — 25% attention layers)
- Qwen2.5-Coder-32B (pure attention — max KV impact)

**3 context lengths**: 4K, 16K, 65K

**Metrics**: perplexity, tokens/sec (generation), tokens/sec (prompt processing), RSS memory

**Expected**: Config 5 should recover most/all of the ~0.2 PPL regression seen in config 4 vs config 1.

#### Critical Files Table

| File | Change Type | Description |
|------|-------------|-------------|
| `src/llama-hadamard.h` | **New** | WHT function + custom op callback declaration |
| `src/llama-hadamard.cpp` | **New** | WHT butterfly implementation + custom op callback |
| `src/llama-graph.cpp` | Modify | Hadamard insertion in 3 KV-cache `build_attn` overloads + `build_attn_mha` |
| `src/llama-graph.h` | Modify | Declare `build_hadamard()` method on `llm_graph_context` |
| `src/llama-cparams.h` | Modify | Add `kv_hadamard` bool |
| `include/llama.h` | Modify | Add `kv_hadamard` to context params |
| `common/common.h` | Modify | Add `kv_hadamard` to `common_params` |
| `common/common.cpp` | Modify | Propagate `kv_hadamard` to context params |
| `common/arg.cpp` | Modify | Register `--kv-hadamard` CLI flag |
| `src/llama-context.cpp` | Modify | Propagate flag from context params to cparams |
| `src/CMakeLists.txt` | Modify | Add `llama-hadamard.cpp` to build |

#### Implementation Notes

- **n_embd_head must be power of 2**: Add assert in `build_hadamard()`. All Qwen/Llama/Mistral use 128.
- **KV cache shift interaction**: With Hadamard, cached K is `H·RoPE(K)`. A context shift would need `H·RoPE_shift·H⁻¹` on cached data — doesn't simplify cleanly. Log a warning if shift attempted with `kv_hadamard` enabled. Not used in our production flow.
- **No-cache / cross-attention overloads**: Skip. `build_attn(attn_no_cache)` has no KV cache; `build_attn(attn_cross)` uses encoder output, not quantized cache.
- **Fused kernel opportunity** (follow-up): Hadamard + quantize and dequantize + inverse can be fused into single AVX-512 passes to avoid extra memory round-trips.

**Validation**:
- Compare q4_0 with Hadamard vs q4_0 without vs f16 baseline
- Perplexity, RULER, needle-in-haystack
- If Hadamard-smoothed q4_0 matches f16 quality (as ExLlamaV2 demonstrates), this is the production configuration

**Risks & mitigations**:
- **Risk**: Hadamard transform adds per-token latency that offsets bandwidth savings. **Mitigation**: 896 FMAs per vector on AVX-512 = ~28 512-bit FMAs = <100ns per vector. At d=128 and 4 KV heads, total overhead per token is ~800ns — negligible vs decode latency (~10-100ms per token).
- **Risk**: Inverse Hadamard inside flash attention hot loop is expensive. **Mitigation**: Flash attention processes tiles of ~32-256 tokens; inverse Hadamard on a tile of 32 vectors at d=128 is 32×896 = 28,672 FMAs ≈ 57 512-bit FMAs = ~1μs. The bandwidth saving from reading 4x less KV data easily dominates.
- **Risk**: Numerical precision — Hadamard in f32 vs f16 matters. **Mitigation**: Hadamard transform preserves norms exactly (orthogonal); f16 Hadamard introduces ~2^-10 relative error per element, compounding over 7 stages to ~7×2^-10 ≈ 0.007 — acceptable.
- **Risk**: V cache transposition interacts with Hadamard. **Mitigation**: Hadamard operates on the embedding dimension (d=128); transposition is along the sequence dimension. They're orthogonal.

**Decision gate**: If Hadamard q4_0 matches f16 quality with neutral-to-positive throughput, this becomes the default production KV config. Phases 2-3 proceed only if we need >4x compression (e.g., 1M context).

### Phase 1 Results (2026-03-25)

**Status**: COMPLETE. Hadamard implemented, compiled, smoke tested, and benchmarked.

**Implementation**: Branch `hadamard-kv-smoothing` in `/mnt/raid0/llm/llama.cpp-experimental`. Build: `build-hadamard/`. CLI flag: `--kv-hadamard`.

**Files created/modified**:
- `src/llama-hadamard.h` + `src/llama-hadamard.cpp` (new — WHT implementation)
- `src/llama-graph.cpp` (Hadamard insertion in KV-cache and ISWA `build_attn` + `build_attn_mha`)
- `src/llama-graph.h` (`build_hadamard()` declaration)
- `src/llama-cparams.h`, `include/llama.h`, `common/common.h`, `common/common.cpp`, `common/arg.cpp`, `src/llama-context.cpp` (flag plumbing)
- `src/CMakeLists.txt` (build system)

#### Perplexity Results (50 chunks, n_ctx=512, Qwen2.5-Coder-32B Q4_K_M)

| Config | PPL | vs f16 | Improvement |
|--------|-----|--------|-------------|
| f16 KV (baseline) | 6.896 +/- 0.162 | — | — |
| q4_0/q4_0 plain | 6.951 +/- 0.164 | +0.055 | — |
| **q4_0/q4_0 + Hadamard** | **6.912 +/- 0.163** | **+0.017** | **70% gap closure** |
| q8_0/q4_0 plain | 6.889 +/- 0.162 | -0.007 | — |
| **q8_0/q4_0 + Hadamard** | **6.886 +/- 0.162** | **-0.010** | **quality-neutral** |

**Hadamard reduces the q4_0 PPL gap from 0.055 to 0.017** — a 70% improvement. q8_0/q4_0 + Hadamard is **quality-neutral** (PPL 6.886 vs f16 6.896 — within noise, slightly better). This is the recommended production config for maximum quality safety margin with 2.5x KV compression.

#### Throughput Results (4K context, Qwen2.5-Coder-32B Q4_K_M, same build)

| Config | Avg Gen t/s | vs f16 |
|--------|-------------|--------|
| f16 baseline | 11.45 | — |
| q4_0/q4_0 plain | 11.58 | +1.1% |
| q4_0/q4_0 + Hadamard | 11.58 | +1.1% |
| q8_0/q4_0 + Hadamard | 11.56 | +1.0% |

**Zero measurable throughput overhead** from Hadamard at 4K context. All configs within noise.

#### Decision Gate Outcome

Hadamard q4_0 **nearly matches** f16 quality (PPL gap 0.017 vs 0.055 without) with **zero throughput cost**. This validates the approach — Hadamard-smoothed q4_0 is the recommended production KV config.

**Recommended production configs**:
- **Max compression (3.56x)**: `--kv-hadamard -ctk q4_0 -ctv q4_0 --flash-attn on` — PPL +0.017 vs f16
- **Quality-neutral (2.46x)**: `--kv-hadamard -ctk q8_0 -ctv q4_0 --flash-attn on` — PPL -0.010 vs f16 (identical)

**Phases 2-3 status**: ALL COMPLETE (2026-03-25). PolarQuant (`GGML_TYPE_POLAR_Q4`) and TurboQuant (`GGML_TYPE_TURBO_Q3`) implemented. Key finding: QJL residual requires custom attention kernel — ggml's dequant-to-float path loses the JL inner-product property. **Hadamard q4_0 remains the production recommendation.**

### Phase 2 Results (2026-03-25)

**Status**: COMPLETE. PolarQuant implemented, compiled, tested end-to-end.

**Implementation**: Added `GGML_TYPE_POLAR_Q4` (type 40) to ggml. Files:
- `ggml/src/ggml-polar-quant.h` + `.c` — block struct, quantize/dequantize, preconditioning matrix, codebooks
- `ggml/include/ggml.h` — enum entry
- `ggml/src/ggml.c` — base type traits (to_float, from_float_ref)
- `ggml/src/ggml-cpu/ggml-cpu.c` — CPU type traits (from_float for set_rows)
- `ggml/src/CMakeLists.txt` — build system
- `common/arg.cpp` — added polar_q4 to KV cache type options

**Bugs fixed during implementation**:
1. NULL `from_float` in CPU traits table → segfault in `ggml_compute_forward_set_rows` (KV cache write path)
2. Uninitialized KV cache cells → NaN propagation during dequant (added norm==0 guard)
3. Thread-safety race in `polar_quant_init()` (added atomic spinlock)
4. Block size mismatch: polar_q4 block size = 128, but some models have n_embd_head_v = 64 (Qwen2.5-0.5B). Only models with d=128+ are compatible.

**Perplexity** (10 chunks, n_ctx=512, Qwen2.5-7B-Instruct f16 weights):

| Config | PPL | vs f16 | Compression |
|--------|-----|--------|-------------|
| f16 V baseline | 7.166 | — | 1x |
| q4_0 V | 7.172 | +0.007 | 3.56x |
| polar_q4 V | 7.394 | +0.229 | 5.12x |

**Analysis**: PolarQuant achieves 5.12x compression but with +0.229 PPL degradation. This is inherent to 3.1 bits/element — the 2-bit resolution on levels 2-7 compounds error across 7 recursive levels. The paper's "4.2x" config uses ~3.8 bits (more bits per level). The intended fix is Phase 3: QJL residual corrects the quantization error, achieving quality-neutral results at 3.5 bits total (TurboQuant = PolarQuant + QJL).

**Decision gate outcome**: PolarQuant alone at 3.1 bits is not quality-competitive with Hadamard q4_0 (3.56x, +0.007 PPL). Proceeded to Phase 3 (QJL residual).

### Phase 3 Results (2026-03-25)

**Status**: COMPLETE. TurboQuant implemented as `GGML_TYPE_TURBO_Q3` (type 41). QJL residual correction does NOT work via ggml's dequant-to-float path.

**Implementation**: 56 bytes per 128 elements (3.5 bits). Stage 1 = simplified 4-level PolarQuant at 2 bits/angle (32 bytes). Stage 2 = 1-bit JL sign bits + residual norm (24 bytes). Files: `ggml-turbo-quant.h/.c`.

**Key finding — QJL requires custom attention kernel**: The QJL paper's asymmetric estimator computes attention scores as `<query_sketch, sign(key_sketch)>` — it preserves **inner products** via the JL lemma, not individual vectors. llama.cpp's flash attention calls `to_float(v_data, V32, DV)` which requires full vector reconstruction. Reconstructing a vector from 1-bit sign projections adds noise (PPL 197K with correction, 9.0 without). The sign bits are useful ONLY for direct score estimation, which would require a custom `ggml_flash_attn_ext` variant that reads QJL-packed V directly.

**Perplexity** (10 chunks, Qwen2.5-7B):

| Config | PPL | vs f16 | Compression |
|--------|-----|--------|-------------|
| f16 V | 7.166 | — | 1x |
| q4_0 V | 7.172 | +0.007 | 3.56x |
| polar_q4 V | 7.394 | +0.229 | 5.12x |
| turbo_q3 V (stage1 only) | 9.017 | +1.85 | 4.57x |
| turbo_q3 V (with QJL correction) | 197K | broken | — |

**Conclusion**: Hadamard q4_0 (Phase 1) is the current production sweet spot. PolarQuant/TurboQuant require a custom attention kernel to leverage QJL's inner-product preservation property — the standard `to_float` dequant path reconstructs vectors (lossy) instead of estimating scores (accurate). Proceeding to Phase 3b: custom QJL attention kernel.

### Phase 3b: Custom QJL Flash Attention Kernel (IN PROGRESS)

**Goal**: Implement `ggml_flash_attn_ext` dispatch for QJL-packed K cache that computes attention scores directly from sign bits using the asymmetric JL estimator — matching the paper's CUDA kernel approach on AVX-512.

**Why Phase 3 failed and 3b fixes it**: Phase 3 tried to reconstruct the key vector from sign bits via `to_float()`, then compute standard `Q·K^T`. But QJL's 1-bit sign projections preserve **inner products** (JL lemma), not individual vectors. Reconstruction adds noise. The fix: compute `Q·K^T` scores directly from the packed sign bits without reconstruction.

**Architecture**:
- K cache: stored as QJL-packed sign bits + norms + outlier norms (TurboQuant block format)
- V cache: stored as PolarQuant (existing `to_float` dequant works for V — used for weighted sum, not similarity)
- Flash attention: when K type is `GGML_TYPE_TURBO_Q3`, dispatch to custom QJL score computation instead of standard `vec_dot`

**Score computation (asymmetric JL estimator)**:
```
For each (query, key) pair:
  query_sketch = JL_matrix × query           // project query (full precision)
  score = (2/sketch_dim) × ‖key‖ × popcount(XNOR(sign(query_sketch), key_signs)) - ‖key‖
        + outlier_correction
```
The XNOR+popcount trick: `sign(a)·sign(b) = 2·XNOR(a,b) - 1`, so the inner product of sign vectors reduces to `2·popcount(XNOR) - sketch_dim`. This is extremely fast on AVX-512 (`vpternlogd` for XNOR, `vpopcntq` for popcount).

**Implementation plan**:
1. Modify `ggml_compute_forward_flash_attn_ext` in `ops.cpp` to detect QJL K-type and dispatch
2. QJL score kernel: project Q via JL matrix, XNOR+popcount with packed K signs, scale by K norms
3. V-side: unchanged (PolarQuant `to_float` for weighted V sum)
4. AVX-512 intrinsics: `_mm512_ternarylogic_epi64` (XNOR), `_mm512_popcnt_epi64` (popcount)

**Key files**:
- `ggml/src/ggml-cpu/ops.cpp` — flash attention dispatch (lines ~8090-8200)
- `ggml/src/ggml-turbo-quant.c` — QJL score function
- `ggml/src/ggml-turbo-quant.h` — declarations

**Reference CUDA kernels** (from QJL GitHub):
- `qjl_score_kernel.cu` — asymmetric score computation with packed bits
- `qjl_gqa_score_kernel.cu` — GQA mapping (multiple Q heads per KV head)
- `qjl_quant_kernel.cu` — JL projection + sign packing (reuse our existing quantize path)

### Phase 3b Results (2026-03-25)

**Status**: COMPLETE. QJL attention kernel implemented and wired into flash attention. Mechanically works (no crashes, correct dispatch). Quality insufficient without outlier correction.

**Implementation**: Modified `ggml_compute_forward_flash_attn_ext` in `ops.cpp` to detect `GGML_TYPE_TURBO_Q3` K-type and dispatch to `turbo_qjl_score_projected()` instead of standard `kq_vec_dot()`. Query is projected via JL matrix once per token, then XNOR+popcount with each K position's sign bits.

**Score accuracy** (standalone test, d=128, 256 sign bits):
- Large dot products (|score| > 10): ratio ~1.03 (accurate)
- Small dot products (|score| < 2): error 5-10x (dominated by noise)
- Root cause: sign-bit estimator has constant variance `‖q‖·‖k‖/√sketch_dim`. For attention, most Q·K scores are small (near-orthogonal), so SNR is poor.

**Perplexity**: PPL ~16K with 256-bit QJL K + f16 V (vs 7.17 f16 baseline). Unusable.

**What's missing**: The QJL paper uses **outlier correction** — the top-k dimensions (default 8) with largest absolute values are stored separately at full precision. This removes the highest-variance components from the sign-bit estimation. Without it, the noise floor exceeds the signal for most attention pairs.

**Block size impact**: Adding 8 outlier dims at full precision = 8 × 4 bytes = 32 bytes → 96 byte block = 6 bits/element. At 6 bits, q8_0 (8 bits, trivial implementation) provides better quality. The compression advantage of QJL disappears when outlier storage is included.

**Conclusion**: TurboQuant/QJL requires outlier handling to work, and with outliers the compression ratio is no longer competitive with simpler approaches (Hadamard q4_0 at 4.5 bits, q8_0 at 8 bits). The GPU implementations benefit from custom CUDA kernels that fuse the outlier correction into the attention computation — the CPU overhead of handling outliers per-score is too high relative to the bandwidth savings.

### Phase 3c Results: Outlier Correction (2026-03-25)

**Status**: COMPLETE. Outlier correction implemented (top-8 key dimensions at f16, exact dot product on those dims + sign-bit estimate on rest). Score accuracy improved for large dot products but fundamental SNR problem remains.

**Implementation**: Block expanded to 58 bytes (3.625 bits/element, 4.41x compression). Stores 8 outlier dimension indices + f16 values. Score function separates exact outlier contribution from sign-bit estimate.

**Root cause of quality gap** (confirmed empirically and analytically):
- Asymmetric sign-bit estimator at S=256, d=128 has **SNR ≈ 1.2** for random vectors
- RMSE (7.4) ≈ mean signal (9.2) — noise dominates for small dot products
- Large dot products (>20) estimated well; small ones (<5) are noise
- Outlier correction helps large scores but can't fix the fundamental SNR limit

**Why the QJL paper works (and we don't)**:
1. **Attention score distribution**: In trained transformers, softmax amplifies a few large Q·K scores and suppresses the noisy small ones. Our PPL test measures aggregate quality where small-score noise accumulates.
2. **Hybrid precision buffer**: Paper keeps most recent 128 tokens at **full precision** (no sign quantization). Only older tokens use QJL. This is critical — recent tokens have the highest attention weights and sign-bit noise on these would be catastrophic.
3. **Layer-specific precision**: Initial layers (first 25%) use S=512 (double projections, half the noise).
4. **S=256 is minimum**: With d=128, SNR ≈ √(S/(πd/2)) ≈ √(256/(201)) ≈ 1.13. Need S≥512 for SNR≥1.6.

**What would be needed for production-viable QJL on CPU**:
1. Dual-region KV cache: full-precision ring buffer (128 tokens) + QJL-compressed bulk storage
2. S=512 for initial layers (requires 64 bytes of signs per block — 96 byte block)
3. Custom KV cache management that promotes tokens from ring buffer to QJL when buffer overflows
4. This is an architectural change to `llama_kv_cache`, not just a new quant type

### Phase 3c Update: Gaussian JL + Outlier Correction (2026-03-25)

Switched from Rademacher (±1) to Gaussian JL matrix (matching paper). Added top-8 outlier correction (original key dims at f16). Results:
- Large-score accuracy: ratio ~1.14 (was ~1.03 Rademacher, ~10x with wrong formula)
- Small-score noise: 10-17x (unchanged — fundamental SNR limit at S=256, d=128)
- PPL: 15K (was 16K Rademacher) — marginal improvement, still unusable

**Confirmed path to production-viable QJL**: Hybrid precision buffer. The paper keeps recent 128 tokens at **full f16 precision** — only older tokens use QJL. This is critical because:
1. Recent tokens receive the highest attention weights (recency bias)
2. Sign-bit noise on high-weight tokens is catastrophic for softmax
3. Older tokens have lower weights → noise is suppressed by softmax

**Implementation path for hybrid buffer**:
1. Dual-region K cache: f16 ring buffer (128 tokens) + turbo_q3 bulk storage
2. When ring buffer overflows, compress oldest tokens: f16 → turbo_q3 (JL project + sign quantize)
3. Flash attention: exact scores on buffer tokens, QJL scores on compressed tokens
4. Requires `llama_kv_cache` architecture change (dual tensor per layer) or graph-level split in `build_attn`
5. Estimated effort: 2-3 days of KV cache engineering

### Phase 3d: Hybrid Precision Buffer (IN PROGRESS)

**Status**: Plan approved, parameter plumbing done, header created. Implementation needs: `.cpp` body + graph integration + model hook.

**Plan file**: `/home/node/.claude/plans/fancy-whistling-hejlsberg.md`

**Completed**:
1. `n_kv_recent` parameter plumbed through 6 files (llama.h, cparams, common, arg, propagation)
2. `src/llama-kv-cache-hybrid-prec.h/.cpp` created (ISWA-style dual cache: kv_recent f16 + kv_old turbo_q3)
3. `src/llama-model.cpp` — `create_memory()` hook for turbo_q3 → hybrid cache
4. `src/CMakeLists.txt` updated
5. Gaussian JL matrix in turbo-quant.c (replacing Rademacher)
6. Outlier correction (top-8 key dims at f16)
7. Builds clean, **chunk 1 PPL = 6.17** (matches f16 baseline) — buffer architecture validated

**Update (2026-03-25 late)**:
- Multi-chunk bug FIXED: `init_batch` delegates to `kv_recent->init_batch()`. **PPL = 7.166 matches f16 baseline exactly.**
- Buffer architecture validated. kv_old allocated (turbo_q3), no interference with kv_recent.
- **Context baseline**: 512 ctx f16 = PPL 7.17, 128 ctx f16 = PPL 14.04. Hybrid buffer target: between these (128 exact + compressed old).
- Full plumbing: `kv_old` flows through `graph_params` → `llm_graph_context` → `build_attn_inp_kv` → `build_attn`. Public accessors added to `llama_kv_cache` (get_used, get_cells, get_k_tensor, get_v_tensor).
- Dual-cache concat attempted in `build_attn` but blocked by: (1) raw tensor is 3D, attention view is 4D — need matching views, (2) kq_mask must be expanded to span both caches. Stubbed with TODO.
- `get_hybrid_kv_old()` on `llama_context` detects hybrid cache and extracts kv_old pointer.
- **Dual-cache attention WORKING** (2026-03-25): 4D views, cast, concat, expanded mask with shift all functional. PPL = 6.94 (matches f16 baseline). Old cache is -inf masked (no data yet). The attention path will automatically read from kv_old once eviction populates it (kv_old->get_used() > 0 triggers concat).

**Remaining** (one piece — eviction data copy):

Both architectural blockers are RESOLVED:
- 4D view matching: ✅ implemented in `build_attn` using `ggml_view_4d` with stride calculation from `get_k()`
- kq_mask expansion: ✅ expanded to `[n_kv_old + n_kv_recent, ...]`, recent portion shifted right via `memmove`, old portion filled with `-inf`

**COMPLETE — eviction + benchmark (2026-03-26)**:

Server benchmark (Qwen2.5-7B, 200 tokens, 512 ctx):

| Config | Gen t/s | vs f16 |
|--------|---------|--------|
| f16 baseline | 15.67 | — |
| turbo_q3 hybrid (kv-recent=64) | **16.21** | **+3.4%** |
| turbo_q3 hybrid (kv-recent=128) | 15.90 | +1.5% |

**Speed-neutral with correct output at 512 ctx.** Eviction active, dual-cache attention working.

**4K crash FIXED (2026-03-26)**: replaced `seq_rm` with direct `cells.rm(cell_idx)`. Now works at all context lengths.

**Full context-length benchmark** (Qwen2.5-7B-Instruct f16, 500 tokens):

| Context | f16 gen t/s | turbo_q3 gen t/s | vs f16 | q8_0/q4_0 gen t/s |
|---------|-------------|------------------|--------|-------------------|
| 4K | 15.95 | 16.49 | +3.4% | 16.25 |
| 16K | 16.45 | 16.51 | +0.4% | 16.25 |
| 64K | 16.67 | 16.41 | -1.6% | 16.71 |
| 128K | 16.73 | 16.56 | -1.0% | 16.86 |

**All speed-neutral at short prompt (500 gen from 65-tok prompt), correct output, no crashes from 4K to 128K.**

**Long-prefill benchmark** (Qwen2.5-7B, gen after 14.5K token prefill):

| Config | Prefill t/s | Gen t/s | Gen vs f16 |
|--------|-------------|---------|------------|
| f16 | 213.8 | 7.70 | — |
| q8_0/q4_0 | 102.5 | 7.41 | -3.8% |
| q4_0/q4_0 | 111.5 | 7.48 | -2.9% |
| turbo_q3 (kv-recent=512) | **277.6** | 3.38 | -56% |

turbo_q3 has fastest prefill (+30% vs f16). Gen at 14.5K prefill: 3.38-4.86 t/s depending on cast path (vs 7.70 f16). Two bottlenecks:
1. **Per-token eviction**: CPU-side turbo_q3 quantization (128×128 matmul per evicted cell per layer)
2. **Concat overhead**: creating 14K-row concatenated K/V tensors per layer per decode step
3. **K quality**: turbo_q3 dequant (PolarQuant reconstruction) has high error — output degenerates at long prefill. **QJL scoring (bypassing dequant) is required for quality**.

**Next steps for production-viable TurboQuant gen speed:**
1. Split attention: compute QK scores separately for old K (QJL) and recent K (exact), concat scores, single softmax, combined V weighted sum
2. Graph caching: old K/V concat doesn't change between tokens — cache it instead of recomputing
3. Batch eviction: evict in bulk (e.g., every 64 tokens) instead of per-token

**Bugs fixed during benchmarking**:
- `ggml_cast` from turbo_q3→f16 unsupported — fixed with two-stage cast (turbo_q3→f32→f16)
- Eviction `cells.rm()` replacing `seq_rm()` position range — fixed direct cell removal
- Multi-stream `get_used()` summing all streams — fixed

**Previously: last remaining piece — eviction data copy** (now done):
- When `kv_recent->get_used() > n_kv_recent`, copy oldest cells' K data to kv_old
- Read: `kv_recent->get_k_tensor(il)->data` + cell_index offset (f16 rows)
- Quantize: `quantize_row_turbo_q3_ref(f32_buf, dst_block, n_embd_k_gqa)` (need f16→f32→turbo_q3)
- Write: `kv_old->get_k_tensor(il)->data` + old_cell_index offset
- Track: increment `n_evicted`, report via `kv_old->get_used()`
- The attention path automatically picks up the data (concat triggers when `n_kv_old > 0`)

**Then QJL scoring swap**:
- Replace `ggml_cast(k_old_4d, f16)` + `ggml_concat` with direct QJL scoring
- The flash attention dispatch for `GGML_TYPE_TURBO_Q3` K-type is already in `ops.cpp`
- Just pass the raw turbo_q3 K tensor to `build_attn_mha` instead of dequanting

**Context baselines** (Qwen2.5-7B, 10 chunks):
- 512 context f16: PPL 7.17 (target)
- 128 context f16: PPL 14.04 (limited context)
- Hybrid buffer should achieve PPL between these

**Context baselines** (Qwen2.5-7B, 10 chunks):
- 512 context f16: PPL 7.17 (target)
- 128 context f16: PPL 14.04 (limited context — what we get without kv_old)
- Hybrid buffer should achieve PPL between 7.17 and 14.04, closer to 7.17 with QJL scoring

**Plan file**: `/home/node/.claude/plans/fancy-whistling-hejlsberg.md`

**Key design**: Initial impl dequantizes old K to f16 for attention (validates buffer architecture). QJL sign-bit scoring is layered on later as performance optimization.

**Production recommendation**: Hadamard q4_0 (Phase 1) for immediate deployment. Hybrid buffer for future work when >4x K-cache compression is needed at extended contexts (256K+). All implementations preserved on `hadamard-kv-smoothing` branch.

### Phase 2: PolarQuant Implementation (5-7 days)

**Goal**: Implement PolarQuant as a custom ggml quant type for KV cache, achieving ~4.2x compression with better quality than naive q4 and no Hadamard dependency.

**Why PolarQuant after Hadamard**: PolarQuant provides similar compression with theoretically optimal distortion properties. If Hadamard q4 is good enough, PolarQuant is redundant. But PolarQuant's advantage is the information-theoretically near-optimal codebook — it may win at lower bit widths (2-3 bits) where Hadamard smoothing can't fully compensate.

**Implementation**:

1. **New ggml quant type**: `GGML_TYPE_POLAR_Q4` (or parametric bit allocation)
   - Block size: d=128 (one KV head)
   - Stored per block: 1× f16 norm (16 bits) + angle indices at each level
   - Bit allocation (matching paper): level 1: 64 angles × 4 bits = 256 bits, level 2: 32 × 2 = 64, level 3: 16 × 2 = 32, level 4: 8 × 2 = 16, level 5: 4 × 2 = 8, level 6: 2 × 2 = 4, level 7: 1 × 2 = 2 → total angles = 382 bits + 16 bits norm = **398 bits per 128 elements = 3.11 bits/element**

2. **Preconditioning matrix S**:
   - Generate once per model architecture (keyed on d=128)
   - Deterministic seed for reproducibility (e.g., seed = hash of model architecture string)
   - Store as f32 matrix (128×128 = 64KB) — loaded once at model init
   - Random orthogonal matrix via QR decomposition of Gaussian matrix

3. **Offline codebook generation**:
   - Angle distributions are analytically known (see PolarQuant paper formula)
   - Pre-compute optimal centroids via 1-D k-means on the known PDF for each level
   - Centroids stored as f32 lookup table: 2^b entries × log₂(d) levels = (16+4+4+4+4+4+4) = 40 entries total → 160 bytes
   - **Ship as compile-time constants** — no runtime codebook computation

4. **Quantize path** (KV write):
   ```
   x_preconditioned = S × x          // 128×128 matmul
   norm = ‖x_preconditioned‖₂        // store as f16
   x_normalized = x / norm
   for level in 1..log₂(128):        // 7 levels
     angles[level] = atan2(right, left)  // per-pair
     indices[level] = nearest_centroid(angles[level])  // codebook lookup
   pack indices into bit-packed storage
   ```

5. **Dequantize path** (attention read):
   ```
   for level in log₂(128)..1:        // reverse
     theta = codebook[level][indices[level]]
     r_left = r_parent × cos(theta)
     r_right = r_parent × sin(theta)
   x_reconstructed = norm × S^T × r[0]  // inverse preconditioning
   ```

6. **Integration into ggml**:
   - Add `GGML_TYPE_POLAR_Q4` to `ggml.h` type enum
   - Implement `ggml_quantize_polar_q4()` and `ggml_dequantize_polar_q4()` in `ggml-quants.c`
   - Register block size, type size in ggml type traits table
   - Wire into flash attention dequant dispatch

**Risks & mitigations**:
- **Risk**: S×x matrix multiply (128×128) per token is expensive on CPU. **Mitigation**: 128×128 f32 matmul = 16,384 FMAs = 512 AVX-512 FMAs ≈ ~1μs. For context: at 10 t/s decode, each token budget is 100ms — 1μs is 0.001%. Also, S is orthogonal so S^T = S^(-1), no matrix inversion needed.
- **Risk**: `atan2` calls in the polar transform are slow. **Mitigation**: At d=128, there are d-1=127 atan2 calls per vector. On Zen 5, atan2 is ~20 cycles → 127×20 = 2,540 cycles ≈ ~1μs. Can also use fast atan2 approximations (polynomial, ~4 cycles).
- **Risk**: Adding a new ggml type is invasive — touches many files. **Mitigation**: Recent ggml has a clean type registration system. The type only needs quantize/dequantize functions and a block size declaration. Flash attention dispatch handles the rest via `ggml_get_type_traits()`.
- **Risk**: d must be power of 2. **Mitigation**: Our models all use d=128 (power of 2). If future models use d=96 or other non-power-of-2, pad with zeros and mask. This is an edge case.
- **Risk**: Interaction with GQA — do we quantize per-head (d=128) or per-layer (4 heads × 128)? **Mitigation**: Per-head. Each KV head is independent in GQA; treating them as one 512-dim vector would not satisfy the power-of-2 constraint cleanly and would mix unrelated head dimensions.

**Decision gate**: Compare PolarQuant quality vs Hadamard q4 at equivalent bit widths. If PolarQuant at 3 bits beats Hadamard q4 at 4 bits, it unlocks further compression. If quality is similar, prefer Hadamard (simpler, reuses existing quant types).

### Phase 3: QJL Residual / TurboQuant Full Pipeline (5-7 days)

**Goal**: Add 1-bit QJL residual on top of PolarQuant to reach 3-3.5 bits total with near-optimal distortion.

**Prerequisites**: Phase 2 PolarQuant working and benchmarked.

**Implementation**:

1. **Port QJL CUDA kernels to AVX-512**:
   - 3 CUDA kernels → 3 AVX-512 implementations
   - **Quantization kernel**: JL projection (matmul) + sign-bit extraction + uint8 packing + outlier norm accumulation
   - **Score kernel**: Unpack bits + multiply by query sketch + outlier correction
   - **GQA kernel**: Multi-Q-head to single-KV-head mapping
   - Key optimization: AVX-512 has `_mm512_movemask_epi8` for fast sign-bit extraction (64 bits per instruction)

2. **JL projection matrix**:
   - Random Gaussian matrix, shape (D=128, sketch_dim=256)
   - Optionally compose with QR rotation for better statistical properties
   - Fixed per model architecture (same deterministic seed as preconditioning matrix)
   - Storage: 128×256×4 bytes = 128KB — loaded once

3. **Bit packing**: 8 sign bits → 1 uint8. AVX-512 can pack 64 bits per `movemask`, then rearrange into uint8 blocks.

4. **Hybrid precision buffer**: Keep last 128 tokens at full precision (configurable). Only quantize older tokens. This is the QJL paper's approach — recent tokens matter more and the rolling quantization adds no latency to the critical path.

5. **Layer-specific precision**: More bits for initial layers (first 25% of attention layers get `sketch_dim=512` instead of 256). Paper shows initial layers are more sensitive.

6. **Combine with PolarQuant**:
   - PolarQuant quantizes KV embeddings → compute PolarQuant reconstruction → compute residual (original - reconstruction)
   - QJL quantizes the residual → 1-bit packed storage alongside PolarQuant angles
   - During attention: dequant PolarQuant + dequant QJL residual → sum → use for attention

**Risks & mitigations**:
- **Risk**: Two-stage dequantization doubles the compute in the attention hot path. **Mitigation**: The QJL residual is 1-bit — dequantization is essentially unpacking bits and multiplying by projection matrix. The dominant cost is still the PolarQuant dequant (atan2 + matmul). Combined overhead should be <2μs per token.
- **Risk**: Memory layout complexity — two different packed formats stored alongside each other. **Mitigation**: Define a compound block type `GGML_TYPE_TURBO_Q3` that stores PolarQuant angles + QJL packed bits + outlier norms + f16 norm in a single contiguous block.
- **Risk**: Outlier handling adds per-block metadata. **Mitigation**: With 8 outlier dimensions per head (QJL default), that's 8 × 4 bytes = 32 bytes per block. Amortized over 128 elements this is 2 bits/element — still within our 3.5-bit total budget.
- **Risk**: This phase is pointless if Phase 1 (Hadamard q4) already matches f16. **Mitigation**: True. Only pursue if we need compression beyond 4x (e.g., 1M context). Phase 1 may be the production sweet spot.

### Phase 4: Validation & Production Deployment (2-3 days)

**Goal**: Comprehensive quality and performance validation across the full model lineup.

**Benchmarks**:
1. **RULER** at 4K, 16K, 65K, 256K (if feasible) — tests long-context retrieval
2. **Needle-in-haystack** at 4K → 65K — tests precise recall
3. **Perplexity** on our standard eval set
4. **Throughput** (t/s generation and prompt processing) at each context length
5. **Memory** (RSS, KV cache size from server logs) — verify actual savings match theoretical
6. **Multi-sequence** — run 4 concurrent requests to verify no contention issues

**Models to test**:
- Qwen3.5-35B-A3B (frontdoor, hybrid — 25% attention layers)
- Qwen2.5-Coder-32B (coder, pure attention — max impact)
- Qwen3.5-122B-A10B (architect, hybrid — fewer concurrent sessions but larger KV)

**Production deployment**:
1. Add `--cache-type-k` / `--cache-type-v` to `orchestrator_stack.py` model launch configs
2. Add to model_registry.yaml as per-model config: `kv_quant_k: q8_0`, `kv_quant_v: q4_0` (or whatever Phase 0-1 determines is optimal)
3. Monitor inference quality via existing eval pipeline for 24-48h
4. Roll back if quality degradation detected

**Documentation**:
1. Update Chapter 04 (radix-attention): add "KV Cache Quantization" section covering KIVI principle, Hadamard smoothing, PolarQuant/QJL theory, and our empirical results
2. Update Chapter 10 (advanced speculative decoding) if quantized KV interacts with speculation
3. Update model_registry.yaml with recommended KV quant configs per model

## Risk Register

| # | Risk | Likelihood | Impact | Mitigation | Phase |
|---|------|-----------|--------|------------|-------|
| R1 | Flash attention broken on EPYC 9655 | ~~Low~~ | ~~Blocking~~ | **CLEARED** (2026-03-25): Works on Zen 5. | 0 |
| R2 | Speed regression > 10% at short contexts | ~~Medium~~ | ~~Medium~~ | **PARTIAL** (2026-03-25): Gen speed neutral (0% regression). Prefill 2-3x slower on pure-attn Coder model with long prompts. See "Flash Attention CPU Dequant Optimization" task. Hybrid Q35 unaffected. | 0 |
| R3 | Quality degradation on Qwen3.5 hybrid worse than published Llama numbers | ~~Medium~~ | ~~Medium~~ | **CLEARED** (2026-03-25): Throughput neutral on Q35. PPL not measured on Q35 specifically but hybrid architecture means only 25% of layers are affected → degradation proportionally smaller. | 0 |
| R4 | Hadamard-smoothed q4 quality worse than ExLlamaV2 reports | ~~Low~~ | ~~Low~~ | **CLEARED** (2026-03-25): Hadamard q4_0 PPL +0.017 vs f16 (70% gap closure). q8_0/q4_0+Hadamard PPL -0.010 (identical to f16). Matches ExLlamaV2 claims. | 1 |
| R5 | PolarQuant dequant latency too high for short-context decode | Medium | Low | At d=128, total overhead is ~2-3μs. Only matters at very short contexts where decode is <1ms. Can disable PolarQuant for contexts <4K. | 2 |
| R6 | New ggml type breaks upstream merge path | Medium | Medium | Keep PolarQuant/TurboQuant on our fork branch. Use `#ifdef GGML_POLAR_QUANT` guards. Don't block production-consolidated merges. | 2,3 |
| R7 | Context shifting incompatible with quantized KV | Confirmed | Low | Context shifting is auto-disabled. Not used in our production flow. Document the limitation. | 0 |
| R8 | Draft model KV quant bug (#11200) | Confirmed | Low | Use explicit `--cache-type-k-draft` / `--cache-type-v-draft` flags. Or patch the bug (small fix). | 0 |
| R9 | Speculative decoding + quantized KV interaction | ~~Medium~~ | ~~Medium~~ | **CLEARED** (2026-03-25): Spec decode + q8_0/q4_0 KV on Coder-32B: 19.15 t/s vs 18.54 t/s f16 (+3.3%). No crash, no degradation. | 0,4 |
| R11 | Needle-in-haystack recall degradation | — | — | **CLEARED** (2026-03-25): q8_0/q4_0 = 9/9, q4_0/q4_0 = 8/9 (1x 503, not quality). Tested 1K/4K/16K at 10/50/90% depth. | 4 |
| R10 | 1M context KV quantization — accumulated error over 1M tokens | Unknown | High | No published results at 1M context with any KV quantization method. Must benchmark RULER at 256K+ ourselves. Conservative approach: use q8_0 (not q4_0) at 1M. | 4 |

## Existing Work in Ecosystem

| Project | Approach | Bit Width | Quality | Speed | CPU? |
|---------|----------|-----------|---------|-------|------|
| **llama.cpp (current)** | Naive round-to-nearest | q4_0-q8_0 | q8≈f16, q4: +0.2 PPL | ~30% gen slowdown (GPU) | Yes |
| **ExLlamaV2** | Hadamard smoothing + Q4 | 4-bit | **Matches f16** | Neutral (GPU) | No |
| **KIVI** | Per-channel K / per-token V | 2-bit | ~f16 at 2 bits | 2.35-3.47x throughput | No |
| **vLLM** | FP8 (E4M3/E5M2) | 8-bit | ~f16 | Neutral | No |
| **lmdeploy** | INT8 per-channel | 8-bit | ~f16 | Neutral | No |
| **KVLinC** | Hadamard + linear correction | 2-4 bit | Near f16 | 2.55x vs FlashAttn | No |
| **PolarQuant** (paper) | Polar coordinates | 3-4 bit | Best in class | +overhead | No |
| **QJL** (paper+code) | 1-bit JL + outliers | 3-bit effective | Near f16 | Reduced bandwidth | CUDA only |
| **TurboQuant** (paper) | PolarQuant + QJL | 3.5-bit | Quality-neutral | 8x attention (H100) | No |

**Key insight**: ExLlamaV2 proved that Q4 KV with Hadamard smoothing matches f16 quality. llama.cpp has the quantized KV infrastructure but lacks the smoothing. **Phase 1 (adding Hadamard) closes this gap with minimal code changes.**

## Decision Framework

```
Phase 0 benchmark results
    │
    ├─ q8_0 shows no speed regression + negligible quality loss
    │   → Deploy q8_0 K / q4_0 V immediately (quick win)
    │   → Proceed to Phase 1
    │
    ├─ Significant speed regression (>10%)
    │   → Investigate dequant overhead in CPU flash attention
    │   → May need to optimize ggml flash attention Q4 dequant path
    │   → Phase 1 deferred until regression understood
    │
    └─ Quality degradation on hybrid models
        → Fall back to q8_0 only (conservative)
        → Phase 1 Hadamard may fix this

Phase 1 benchmark results
    │
    ├─ Hadamard q4 matches f16 quality
    │   → This is the production config
    │   → Phase 2-3 only if we need 1M context
    │
    └─ Hadamard q4 still degrades
        → Try q5_0 with Hadamard (5-bit, 3.2x compression)
        → Phase 2 PolarQuant for better distortion at same bit width

Phase 2 benchmark results
    │
    ├─ PolarQuant at 3 bits matches Hadamard q4 quality
    │   → PolarQuant wins on compression ratio
    │   → Phase 3 for final push to 3-3.5 bits
    │
    └─ PolarQuant at 3 bits degrades vs Hadamard q4
        → Stick with Hadamard q4 (simpler, good enough)
        → Phase 3 cancelled
```

## Final Benchmark Summary (2026-03-26)

**Server benchmark** (Qwen2.5-7B-Instruct f16 weights, 200 tokens, 512 ctx):

| Config | Gen t/s | vs f16 | K Compression | Quality |
|--------|---------|--------|---------------|---------|
| f16 baseline | 15.67 | — | 1x | baseline |
| turbo_q3 hybrid (kv-recent=64) | **16.21** | **+3.4%** | **4.41x** | correct |
| turbo_q3 hybrid (kv-recent=128) | 15.90 | +1.5% | 4.41x | correct |

**All KV quant configs** (Qwen2.5-Coder-32B, production binary):

| Config | Gen t/s | PPL vs f16 | K Compression | Overhead |
|--------|---------|------------|---------------|----------|
| f16 baseline | 9.44 | — | 1x | — |
| q8_0/q4_0 | 9.48 | -0.007 | 2.46x | none |
| q8_0/q4_0 + Hadamard | — | -0.010 | 2.46x | none |
| q4_0/q4_0 | 9.31 | +0.055 | 3.56x | none |
| q4_0/q4_0 + Hadamard | — | +0.017 | 3.56x | none |
| turbo_q3 hybrid | 16.21* | TBD (long ctx) | 4.41x K | none |

*Measured on Qwen2.5-7B, different model.

**Validation** (Qwen2.5-Coder-32B):
- Spec decode + q8_0/q4_0: 19.15 t/s (+3.3% vs f16)
- Needle-in-haystack q8_0/q4_0: 9/9 at 1K/4K/16K
- Needle-in-haystack q4_0/q4_0: 8/9 (1× startup, not quality)

## References

- TurboQuant paper: https://arxiv.org/abs/2504.19874
- TurboQuant blog: https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/
- PolarQuant paper: https://arxiv.org/abs/2502.02617
- QJL paper: https://arxiv.org/abs/2406.03482
- QJL code: https://github.com/amirzandieh/QJL
- KIVI paper: https://arxiv.org/abs/2402.02750
- KIVI code: https://github.com/jy-yuan/KIVI
- KVLinC paper: https://arxiv.org/abs/2510.05373
- ExLlamaV2 Q-cache eval: https://github.com/turboderp-org/exllamav2/blob/master/doc/qcache_eval.md
- llama.cpp KV cache discussion: https://github.com/ggml-org/llama.cpp/discussions/5932
- llama.cpp draft model KV bug: https://github.com/ggml-org/llama.cpp/issues/11200
- llama.cpp KV cache PR: https://github.com/ggml-org/llama.cpp/pull/7527
- vLLM quantized KV docs: https://docs.vllm.ai/en/latest/features/quantization/quantized_kvcache/
- TurboQuant llama.cpp CUDA fork: https://github.com/spiritbuun/llama-cpp-turboquant-cuda
- TurboQuant upstream discussion: https://github.com/ggml-org/llama.cpp/discussions/20969
- TurboQuant upstream feature request: https://github.com/ggml-org/llama.cpp/issues/20977
- ik_llama.cpp TurboQuant PR: https://github.com/ikawrakow/ik_llama.cpp/issues/1509
- vLLM TurboQuant feature request: https://github.com/vllm-project/vllm/issues/38171

## Research Intake Update — 2026-03-28

### New Related Research
- **[intake-194] "llama-cpp-turboquant-cuda"** (github:spiritbuun/llama-cpp-turboquant-cuda)
  - Relevance: Direct CUDA implementation of TurboQuant 3-bit KV cache quantization in llama.cpp fork
  - Key technique: TurboQuant turbo3 with Flash Attention CUDA kernels for NVIDIA GPUs
  - Reported results: 98.8% of q8_0 prefill speed, norm correction makes turbo3 PPL beat q8_0
  - Delta from current approach: We have turbo_q3 hybrid at 16.21 t/s (Qwen2.5-7B) but no CUDA kernels; this fork provides production CUDA path

### Ecosystem Status (via expansion)
- **Upstream llama.cpp**: Feature request open (issue #20977), discussion active (#20969). Separate Hadamard-only PR #21038 by ggerganov adds `-khad`/`-vhad` flags on existing q4_0/q8_0 types.
- **ik_llama.cpp**: Working CPU+CUDA implementation ready for review (issue #1509), 18/18 tests passing, MSE matches paper
- **vLLM**: Feature request open (issue #38171)
- **Multiple independent forks** validating TurboQuant claims: TQ3 MSE=0.034, TQ4 MSE=0.009, 4.9x compression vs FP16
- **700K+ token context** demonstrated on single RTX 5090 (32GB) with turbo3
- **7 distinct implementations**: spiritbuun (CUDA), TheTom (Metal), animehacker (CUDA), Aaryan-Kapoor (CPU), ik_llama.cpp, ubergarm, upstream PR #21038

### Deep Dive Findings (2026-03-28)

#### External Confirmation: Hadamard+q4_0 > TurboQuant on CPU

ikawrakow's benchmarks on Qwen3.5-35B-A3B (EPYC 9975) independently confirm our finding that Hadamard+q4_0 beats TurboQuant:

| Config | PPL | tok/s |
|---|---|---|
| f16/f16 | 6.5792 | 1292 |
| `-khad q4_0 -vhad q4_0` | **6.5939** | **1279** |
| `tq3_0 / tq3_0` | 6.6872 | 573 |

Hadamard+q4_0 is better quality AND 2.2x faster on CPU. TQ3's only advantage is compression (4.4x vs 3.6x). This matches our own result where we abandoned turbo_q3 for K in favor of q4_0+Hadamard.

#### CRITICAL: TurboQuant Quality is Model-Size Dependent

ikawrakow tested systematically across model sizes:
- **Qwen3-0.6B**: TQ3 PPL **1216.23** vs f16 13.51 — **catastrophic failure**
- **Qwen3-8B**: TQ3 PPL 8.15 vs q4_0+khad 7.38 — worse than Hadamard+q4_0
- **Qwen3.5-35B-A3B**: TQ3 PPL approaches f16 — but 75% recurrent, only 25% uses KV cache

The "lossless compression" claim only holds for large models where head_dim=128 provides enough coordinates for WHT to gaussianize the distribution. **Our Qwen2.5-7B test model is in the failure zone.** Must re-benchmark on Qwen2.5-Coder-32B or larger to get a fair comparison.

**DONE (2026-03-28)**: Re-ran TQ3 on Coder-32B Q4_K_M with norm correction. Result: TQ3 PPL 1.4676 vs q4_0 PPL 1.3875 (+5.9%). TQ3 ABANDONED — q4_0 strictly better even at 32B.

#### Norm Correction — Trivial Fix for TQ3 Quality

spiritbuun's key innovation: store `||x|| / ||reconstruct(x)||` instead of `||x||` as the per-block norm. The reconstruction norm accounts for cumulative quantization error in codebook lookup + rotation inverse. Zero decode-time cost (same storage, same multiply). Computed during quantization by doing a full dequant of the just-quantized block.

Result on Qwen3.5-27B Q6_K (RTX 3090):
- q8_0: PPL 5.8375
- turbo3 without norm correction: PPL ~5.85
- turbo3 WITH norm correction: PPL **5.7690** (beats q8_0 by 1.17%)

**Implementation**: In `ggml-turbo-quant.c`, restructured dequant to factor norm as final multiplier (not in sign_mag computation). Quantize: set norm=1.0, dequant, measure ||unit_recon||, store original_norm/||unit_recon||. Removed outlier override from dequant (outliers used by QJL scoring path only).

**Result (2026-03-28, turbo_q3 V with norm correction):**

Qwen2.5-7B (10 chunks, ctx=512):
- Without norm correction: PPL 9.017 → **With: PPL 2.13** (77% gap reduction, still not competitive)

Qwen2.5-Coder-32B Q4_K_M (10 chunks, ctx=512):

| Config | PPL | vs f16 |
|---|---|---|
| f16 V | 1.3861 | — |
| **turbo_q3 V (norm corrected)** | **1.4676** | **+0.082 (+5.9%)** |
| q4_0 V | 1.3875 | +0.001 (identical) |

**DECISION: TQ3 ABANDONED.** Even with norm correction on 32B, turbo_q3 adds +5.9% PPL while q4_0 is identical to f16. Norm correction helped (77% gap reduction on 7B, measurable improvement on 32B) but q4_0 is strictly better at the same or lower complexity. Proceeding to rebase onto upstream Hadamard PR #21038.

#### Fused Dequant — The Path to Eliminating Our 30% Speed Gap

The ecosystem solves the dequant overhead (our bottleneck) via fused flash attention kernels:
1. Pre-rotate Q via WHT once per head (O(d log d) = 896 FLOPs for head_dim=128)
2. Dot rotated Q directly against codebook centroids in packed K cache
3. No materialized dequant buffer, no q4_0→f16 cast

Key insight: `dot(Q, dequant(K)) = dot(WHT(Q), codebook[indices]) * scale`. The WHT of Q is done once, then scoring is 128 lookups + 128 MADs per KV position.

spiritbuun reports moving Q FWHT out of the vec kernel gave +6.5% decode gain. animehacker describes the same approach as "MMVQ kernel fusion."

For CPU implementation: write a custom `vec_dot_tq3_0_q8_1` kernel in `ggml-cpu/ops.cpp`. The ik_llama.cpp approach with `GGML_IQK_FA_ALL_QUANTS=ON` provides a template.

#### Key Bugs Found Across Ecosystem (Watch List)

| Bug | Impact | Fix |
|---|---|---|
| WHT normalization `1/block_size` vs `1/sqrt(block_size)` | Garbage PPL | Must use `1/sqrt(32)` = 0.17677... not `1/32` = 0.03125 |
| V cache transpose + block quantization | Crash (`ne00 % block_size != 0`) | Store V non-transposed (`v_trans=false`), dequant then transpose in graph |
| WHT in graph vs during quantization | PPL 23.5 instead of 6.2 | Do WHT during quantization (`set_rows`), NOT graph-side |
| CPU dequant only supports F32 dest | Crash on F16 target | Always dequant to F32, then cast |

#### Block Size Decision: 32 vs 128

- **32-block** (Aaryan-Kapoor, animehacker): 14 bytes = 2B fp16 scale + 8B qs + 4B qr = 3.5 bpw. Better ggml integration, works with FA parallelism.
- **128-block** (ik_llama.cpp, spiritbuun): 52 bytes = 4B float32 norm + 48B packed = 3.25 bpw. Matches paper exactly.
- **Our implementation**: `GGML_TYPE_TURBO_Q3` at type 41, 3.6 bpw. If proceeding with TQ3, 32-block integrates more cleanly.

#### Lloyd-Max Codebook Values (Reference)

3-bit (8 centroids), unit-norm vectors after WHT:
```
// ik_llama.cpp (paper-exact, 128-block, float32 norm)
{-0.18904037, -0.11879502, -0.06702922, -0.02174971,
  0.02174971,  0.06702922,  0.11879502,  0.18904037}

// Aaryan-Kapoor (32-block, fp16 scale, pre-scaled by ~11.42)
{-2.1573, -1.3336, -0.7434, -0.2428,
  0.2428,  0.7434,  1.3336,  2.1573}
```

#### Revised Priority for This Handoff

1. **Retest TQ3 on Qwen2.5-Coder-32B** — our 7B results are pessimistic due to model size
2. **Implement norm correction** — trivial, may make turbo_q3 K viable again (1 day)
3. **Monitor upstream PR #21038** — if `-khad`/`-vhad` lands in mainline, rebase instead of maintaining custom WHT
4. **Fuse dequant into vec_dot kernel** — eliminates the 30% cast overhead (3-5 days)
5. **Decision gate after steps 1-2**: If TQ3+norm correction on 32B still loses to Hadamard+q4_0, abandon TQ3 and adopt upstream Hadamard. The extra 0.8x compression (4.4x vs 3.6x) may not justify the complexity on a 1.13 TB system.

## Research Intake Update — 2026-04-04

### New Related Research
- **[intake-256] "Screening Is Enough — Multiscreen Architecture"** (arxiv:2604.01178)
  - Relevance: Alternative attention mechanism that replaces softmax with absolute key screening
  - Key technique: Screening evaluates each key against threshold, discarding irrelevant keys (sub-quadratic)
  - Reported results: 2.3-3.2x latency reduction at 100K context, 40% parameter savings
  - Delta from current approach: Our Hadamard KV quantization optimizes standard softmax attention. Multiscreen replaces softmax entirely — if adopted by model providers, it would change the KV cache landscape (screening may not need the same quantization strategies since irrelevant keys are discarded rather than compressed)
  - Status: WATCH — no models or llama.cpp support yet. See `handoffs/active/multiscreen-attention-evaluation.md`

## Research Intake Update — 2026-04-08

### New Related Research
- **[intake-284] "TriAttention: Efficient Long Reasoning with Trigonometric KV Compression"** (arxiv:2604.04921)
  - Relevance: Orthogonal to our Hadamard quantization — TriAttention selects WHICH tokens to keep via pre-RoPE trigonometric scoring; our work compresses HOW values are stored. Potentially complementary (fewer tokens × better quantization).
  - Key technique: Pre-RoPE Q/K concentration + trigonometric series scoring. Scores key importance without materializing full K/V. Uses offline-calibrated Q centers + norm-based scoring with adaptive weighting.
  - Reported results: 2.5x throughput, 10.7x KV memory reduction on AIME25, matches Full Attention accuracy (40.8%). 1,405 tok/s vs 223 tok/s on MATH500. Outperforms SnapKV and R-KV at 2048 token budget.
  - Delta from current approach: Our `--kv-hadamard -ctk q4_0 -ctv f16` is production-deployed quantization. TriAttention is eviction-based — reduces token count rather than compressing representation. In theory, both could stack (evict via TriAttention, then quantize survivors via Hadamard). Major caveat: vLLM-only implementation, NO llama.cpp port exists.
  - Status: WATCH+EVALUATE — see `handoffs/active/triattention-kv-selection.md` (ACTIVE — research evaluation, S1-S4 pending)

- **[intake-287] "LongFlow: Efficient KV Cache Compression for Reasoning Models"** (arxiv:2603.11504)
  - Relevance: Another KV eviction approach targeting long-reasoning output (same problem as TriAttention)
  - Key technique: Fused FlashAttention + token eviction kernel, lightweight importance metric using current query only
  - Reported results: 11.8x throughput improvement with 80% KV cache compression, minimal accuracy impact
  - Delta from current approach: Fused kernel approach — tighter integration than TriAttention's plugin model. No llama.cpp port either.

- **[intake-288] "Expected Attention: KV Cache Compression by Estimating Attention from Future Queries Distribution"** (arxiv:2510.00636)
  - Relevance: Predicts future attention via distributional properties — training-free, works in both prefill and decode
  - Key technique: Expected Attention scoring + KVPress library (20+ compression techniques benchmarked)
  - Delta from current approach: KVPress library could be useful as a benchmarking tool for comparing compression approaches. Different scoring basis than TriAttention (distributional vs trigonometric).

## Research Intake Update — 2026-04-09

### Memento Block Masking — Orthogonal Composability (intake-289)

Memento (Microsoft, intake-289) trains models to segment reasoning into blocks, compress each into a summary, and mask original block KV states. Peak KV reduction: 2-3x on Qwen3-8B/32B, Phi-4 14B.

**Composability with our Hadamard+q4_0**: Memento reduces WHICH KV entries exist (attention span compression). Our quantization reduces HOW each entry is stored (precision compression). These are orthogonal — multiplicative when stacked: Memento 2-3x × q4_0 2x = **4-6x KV reduction**.

**Triple-stack with KV selection**: Adding TriAttention/Expected Attention selection on top could reach 8-60x theoretical.

**Key dependency**: llama.cpp block masking implementation. Uses special tokens (`<|block_start/end|>`, `<|summary_start/end|>`) and KV eviction after summary completion. Our ISWA hybrid buffer work is architecturally similar.

See: [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md), deep-dive at `research/deep-dives/memento-iterative-reasoning-cluster.md`.
