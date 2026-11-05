# HIP (MI210) FLASH_ATTN_EXT: unsupported shapes

Status 2026-11-05: kernel fix **shelved by operator**. This page exists so the gap is recognised at once
when a GPU model hits it (box `C6-HIP-FA-SHAPES` in `handoffs/active/kernel-champion-and-promotion.md`).

**Evidence.** Code: `ggml/src/ggml-cuda/fattn.cu` `ggml_cuda_get_best_fattn_kernel` and `fattn-tile.cuh`
`launch_fattn_tile_switch_ncols2` on champion C6 tip `f9f872ebc`. Suite log:
`/mnt/raid0/llm/tmp/c6-q4fix-takeover-20261105/suiteopt2-row/runs/*/FLASH_ATTN_EXT/stdout.log`
(seed 71, 2229 unsupported). Production v10 and C5 have the same gates. Upstream `origin/master` `45b6604b2`
(2026-11-05) has identical gates, so there is nothing to port. An unbuilt and untested fix is on
`fork/experimental/c6-hip-fa-f16-hs-20261105` @ `5c89f670d`.

## What is supported

- **Head sizes** (K == V): 40, 64, 72, 80, 96, 112, 128, 256. These are always supported, in any mask, GQA or ALiBi shape.
- **Head sizes** 192/128, 320/256, 512/512, 576/512 are supported **only** when the GQA-grouped kernel applies.
  That requires all of the following:
  - gqa_ratio ≥ 2;
  - a mask is present;
  - `max_bias == 0` (no ALiBi);
  - KV length % 256 == 0;
  - for 192, gqa % 8 == 0 and, on AMD, rows × gqa_eff ≤ 256;
  - for 320, gqa % 32 == 0.
- **192/192**: no kernel at all.
- **KV cache types**: f32, f16, bf16, q4_0, q8_0, and **K type == V type**.
  - q4_1, q5_0 and q5_1 need `GGML_CUDA_FA_ALL_QUANTS` (not set in our builds).
  - iq4_nl and the other quant types are never supported.
- **Mask**: `mask->ne[2] != 1` (a per-head mask) is unsupported.

## Unsupported cases (seed-71 suite)

| Case | Gate | Suite count |
|---|---|---|
| (a) f16 192/128, 192/192, 320/256, 512/512, 576/512 with gqa=1, no mask, ALiBi, or a non-dividing GQA ratio | fattn.cu `switch (K->ne[0])` returns NONE without `gqa_opt_applies`. The tile ncols2=1 path is compiled only for `DV <= 256`; 192 and 320 `GGML_ABORT` otherwise. | 876 |
| (b) **mixed K/V types**: q4_0/f16, f16/q4_0, q8_0/q4_0, q4_0/q8_0, q1_0 pairs, f16/f32 | `if (K->type != V->type) return NONE` under `#ifndef GGML_CUDA_FA_ALL_QUANTS` | 9 (the "64/64" and "128/128" cases) |
| (c) q4_1, q5_0, q5_1, iq4_nl (K == V) | `ggml_cuda_fattn_kv_type_supported` | 336 each |

**Watch out:** the orchestrator registry `server_defaults` sets `kv_cache_type_k: q4_0` and
`kv_cache_type_v: f16`. That is case (b). A GPU role inheriting the defaults instead of its recipe (the 27B recipe
sets `ctk f16`) loses GPU FA.

## Symptom

The output stays correct, so no quality gate catches this.

- **`-fa on`**: the scheduler places every attention layer's FA node on the **CPU**. The log shows extra
  graph splits and a large slowdown in prefill and decode, with K/V copied host↔device per layer.
- **`-fa auto`** (the llama.cpp default): `llama-context.cpp` probes FA placement, then disables FA:
  - it warns `layer N is assigned to device ROCm0 but ... is assigned to device CPU (usually due to missing support)`;
  - then `... not supported, set to disabled`.
  - The non-FA attention path runs instead, which is slower at long context and uses more VRAM.

## Detect it in one step

Start the server (or `llama-cli`) on the real model with the serving `-ctk`/`-ctv`, then grep its startup log:

```
grep -E "usually due to missing support|not supported, set to disabled|graph splits" server.log
```

A healthy fully-offloaded GPU role shows no "missing support" line and a small, constant `graph splits`
(for example 2). Verified in source (`src/llama-context.cpp:591-603, 751-753`) on C6. Not yet run against a model.
`GGML_SCHED_DEBUG=2` (`ggml-backend.cpp:1749`) prints the per-node backend assignment if you need to see which op fell back.
`test-backend-ops -o FLASH_ATTN_EXT` cannot select an exact model shape. It only shows the class of gap.

## Current GPU lineup: not affected

Qwen3.8-27B Q8 on :8083 runs at head dim 256 with an f16/f16 KV cache (recipe
`qwen3.8-27b-q8-gpu-dflash2-np4.json`). Qwen3.6-35B-A3B also uses hd256 with a masked GQA shape. Both fall in
the always-supported set. The GQA ratios were not re-measured here.

## Rule

If a GPU role uses a head size outside {40, 64, 72, 80, 96, 112, 128, 256}, or K/V cache types that differ or are
not one of f16/q8_0/q4_0/bf16, run the detection step before serving.

Kernel fix, only if detection shows a fallback:
- extend the tile kernel's ncols2=1 path to DV 512/192/320;
- add AMD tile configs;
- add a 192/192 instance;
- route these shapes to TILE.

The fix is about 1 day and already drafted at `5c89f670d`.
