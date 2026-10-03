> Durable copy (2026-10-03, workspace-ec wrap-up) of the scratch fold record
> `/mnt/raid0/llm/tmp/fa-maskskip-20261003/FOLD.md` (sha256 below). Tracking: KVU-19a / KVU-19 in
> [`handoffs/active/kv-unified-stack-rollout.md`](../../handoffs/active/kv-unified-stack-rollout.md). Scratch paths
> named below (`/mnt/raid0/llm/tmp/...`) may be reclaimed; the branch on `fork` and the `kernels/builds/` dirs are the
> durable artifacts. Source sha256: `29d026d23c207c1818e92f8ba0750b1703806eb4e504a4c86500f81a754f6f55`. One edit vs the source: the title cites `intake-1849#record` (cite-check form) instead of `intake-1849`.

# FOLD.md: FlashAttention masked-KV-block skip (upstream #28495, intake-1849#record, EPYC P3)

The fold is owned by workspace-89 (the DS41/AutoKernel lane). This feature has **not** been merged into any
champion branch. This file has everything the fold needs.

## What it is

| | |
|---|---|
| branch | `experimental/fa-maskskip-20261003`, pushed to `fork` (github.com/pestopoppa/llama.cpp) |
| base | `90c12df42` = tip of `ak/champion/llama-cpp-ffc1bac82eec` (global champion, contains SW-9). Confirmed by workspace-89 on 2026-10-03. |
| commit 1 (GPU) | `ac97e305a26a11b1bf486d8c9118f4633011a01a` `ggml-cuda: skip fully masked KV blocks in FlashAttention (unified KV cache)`. Touches `ggml/src/ggml-cuda/fattn-{common,vec,tile,mma-f16}.cuh` and `fattn-wmma-f16.cu`. Its test travels with it: `tests/test-backend-ops.cpp` adds `test_flash_attn_ext_unified` (52 cases). |
| commit 2 (CPU) | `a0d0ae238e714aaab04e973ef4b5a4b7c9917744` `ggml-cpu: test runs of -INF mask values with wide compares in FlashAttention`. Touches `ggml/src/ggml-cpu/ops.cpp` only. |
| store builds | `kernels/builds/gpu-20261003-a0d0ae238` and `kernels/builds/cpu-20261003-a0d0ae238` (build 10310). The recipes match the champion builds `gpu-20260929-90c12df42` and `cpu-20260925-90c12df42`; the CMakeCache `GGML_*`/`LLAMA_*`/compiler entries are identical. Linkage is PASS for both. |
| runtime knobs | `GGML_CUDA_FA_MASK_SKIP=0` disables the feature, so one binary serves as its own A/B control. `GGML_CUDA_FA_MASK_SKIP_MIN_KV` (default 4096) is the smallest n_kv at which the extra mask-scan launch runs. |

The two commits are independent features with independent tests. Fold either one or both.

## Upstream status (2026-10-03)

- **#28495 is OPEN** and has no upstream fix.
- **PR #28943** ("hip: skip fully masked KV tiles in WMMA FA") was **closed**. JohannesGaessler asked for the approach used here: build on the auxiliary `flash_attn_mask_to_KV_max` kernel rather than add per-element instructions to the inner loop. That PR also targeted rocWMMA, which upstream removed in #26046.
- **PR #29510** (am17an, `flash_attn_ext_rows` + `kv_rows` indirection) is a **draft**. It changes the graph, the KV cache and every backend. It is NVIDIA-tested only and not portable as a kernel patch.
- **Upstream "sparse-fa"** (#27970, #28770, #29298) is **NVIDIA-only**. It is opt-in through an `n_kv_max` top-k hint for DSA/qwen4exp, and it aborts on HIP.
- **Metal** has interior block skipping (#28098, a sparse index list). **Vulkan** got it in #17186.

When the upstream design lands (probably #29510), drop commit 1 in favour of it at the next rebase.

## How it works

- `flash_attn_mask_to_KV_live` uses one warp per block of 256 KV cells. For each query tile it writes a byte that is 1 when any row of the tile has a non -INF mask value in the block.
  - This scan replaces the `KV_max` scan whenever it runs. The old `KV_max` scan never ran for decode at all: its gate is `ne1 >= 1024 || ne3 > 1`.
- The kernels skip dead chunks in two ways:
  - **vec** (including the CDNA2 fused-combine path) and **MMA** (only when `nstages <= 1`, which covers all of AMD) use one uniform branch per chunk.
  - **tile** and **WMMA** advance the loop index over dead chunks instead, so the loop body stays unchanged. A branch inside the tile loop made the D=512/576 GQA tile kernel's output run-to-run nondeterministic on gfx90a, even with the skip disabled. That points to a latent codegen-sensitive hazard in that upstream kernel, which this commit does not trigger.
- **FP16 conversion skips dead blocks too.** Quantized KV on the WMMA, tile and MMA paths is converted to FP16 only for blocks that some tile reads. This matters for drafted verify (q8_0 + WMMA on gfx90a), where the whole-cache conversion was most of the cost.
  - Q8_0 uses a grid-stride copy of `dequantize_block_q8_0_f16`, so the arithmetic is identical.
  - Other types reuse the stock converters' expressions.
- **Kernel selection on the MI210** (gfx90a, `GGML_HIP_ROCWMMA_FATTN=ON`) for the 27B (D=256, q8_0 KV):
  - Q->ne[1] <= 2 (plain decode) goes to **vec**.
  - 3 or more rows (DFlash2 verify, batched decode, prefill) go to **WMMA**, after a q8_0 to f16 conversion.
  - The tile and MMA paths serve other head sizes (40/72/192/512/576, and 320 with MMA).
- **CPU.** The FA paths already skipped -INF cells, but one cell at a time. They now test 64-cell runs, and whole tiles in the tiled path, with 64-bit compares on the raw fp16 bits.

## Evidence

All CPU work ran under nice 19, ionice -c3, taskset 160-183.

### Correctness

- **test-backend-ops `-o FLASH_ATTN_EXT -b ROCm0`: 2920/2920 passed**, including the 52 new cases. It also passed 2920/2920 with `GGML_CUDA_FA_MASK_SKIP_MIN_KV=0`, which sends the existing kv=512/1024 cases through the skip path.
  - Caveat: these runs used an intermediate dev build, before the Q8_0 converter was replaced by the `dequantize_block_q8_0_f16` copy and its grid-stride loop. The GPU freeze stopped me before I could re-run them on the final code.
  - `gpu_slot.sh` step 5 re-runs both on the store build.
  - The 64-case harness on/off bit-exactness was re-run after the first Q8_0 converter change (64/64 identical). Its final run is `gpu_slot.sh` step 1.
- **Harness, 64 FA cases on ROCm0** (f16, q8_0, q4_0, q5_0, q5_1, bf16; D 40..576; nb 1..512; ALiBi, softcap, MLA V-view-of-K, MMA D=320; masks shaped like a unified KV cache).
  - Outputs with the skip **on are bit-identical to skip off**, and two runs with the skip on are bit-identical to each other. These ran on the dev build after the tile/WMMA loop-index change.
  - Against the unpatched champion libraries, 58 of 64 are bit-identical. The remaining 6 differ at nmse <= 3.1e-7, with the same values deterministically on every run. They come from codegen of the changed kernels (WMMA nb=32, tile D=40/192), not from the skip. The test tolerance is 5e-4.
  - The worst GPU-vs-CPU nmse is 8.5e-5.
  - Harness: `/mnt/raid0/llm/tmp/fa-maskskip-20261003/harness/fa_harness.cpp`.
- **CPU harness, 86 cases.** Bit-identical against `cpu-20260925-90c12df42` for both the store build and the trial merge onto `b3e0b0902`.

### Kernel micro-benchmark

The shape is the 27B's attention: D=256, 4 KV heads, GQA 6, q8_0, 16k own cells plus F foreign cells. Figures are medians of 3 alternating rounds, in µs per FA op, with the dev build. These were measured on the shared GPU **while :8083 was serving**, so treat them as indicative. The coordinated GPU slot re-runs them on the store build (`gpu_slot.sh`).

| rows | foreign cells | base | skip on | skip off | on/base |
|---|---|---|---|---|---|
| 1 (vec) | 0 | 373.9 | 391.8 | 374.8 | 1.05 (noise; other rounds 0.99–1.00) |
| 1 (vec) | 16k | 665.7 | 391.1 | 710.7 | 0.59 |
| 1 (vec) | 48k | 1260.8 | 398.6 | 1264.1 | 0.32 |
| 1 (vec) | 112k | 2445.9 | 401.0 | 2795.6 | 0.16 |
| 8 (WMMA, drafted verify) | 0 | 641.8 | 670.0 | 656.8 | 1.04 |
| 8 (WMMA, drafted verify) | 16k | 1226.0 | 702.5 | 1621.2 | 0.57 |
| 8 (WMMA, drafted verify) | 48k | 2195.2 | 706.2 | 2275.1 | 0.32 |
| 8 (WMMA, drafted verify) | 112k | 4442.5 | 788.3 | 4467.8 | 0.18 |

Decode attention cost no longer scales with foreign cells. With rows=1 it is flat, at +2.5% over +112k cells. With rows=8 the residual is +18% at 112k, against +590% unpatched. The residual comes from parallel blocks that see only dead chunks.

The model-level P3-mini run (gemma-3-1b, one sequence decoding next to 3×32k idle neighbours) was **stopped at the coordinator's request** because it was perturbing workspace-89's timed :8083 measurements. Its partial numbers are unusable (the GPU was contended). It runs in the GPU slot.

### CPU path

The unpatched CPU decode op already barely scales with foreign cells: 2.85 ms → 2.87–3.01 ms from 0 to 112k foreign cells, at 24 threads. The CPU change is exact and cheap, but its effect is within noise on this shared host. **It is not a claimed speedup.**

## Fold instructions (workspace-89)

The trial merge was verified on 2026-10-03 in a throwaway detached worktree of the experimental clone, with no push:
- `git merge --no-ff experimental/fa-maskskip-20261003` onto `b3e0b0902` (the DS41 accumulator): **clean**. `ggml-cpu/ops.cpp` auto-merged; the DS41 hunks are e4m3 gather_rows, not FA.
- `git cherry-pick ac97e305a a0d0ae238` onto `b3e0b0902`: **clean**.
- The merged tree's `ggml-cpu` builds, and its FA output is bit-identical (86 cases) to `90c12df42`.
- `053c3bd82` and `a1faab471` both descend from `90c12df42` and touch the same files only outside FA.

```bash
# in the champion tree / its worktree (NOT the frozen production tree)
git fetch fork experimental/fa-maskskip-20261003
# preferred: keep both features as separate commits on the champion branch
git cherry-pick ac97e305a26a11b1bf486d8c9118f4633011a01a   # GPU FA skip + test_flash_attn_ext_unified
git cherry-pick a0d0ae238e714aaab04e973ef4b5a4b7c9917744   # CPU FA -INF run skip (optional, exact)
# or, equivalently: git merge --no-ff fork/experimental/fa-maskskip-20261003
```

Gates for the folded candidate, run on the full candidate binary rather than on this branch:

1. Build with the house GPU recipe (gfx90a-house-v1) and the CPU recipe (native-openmp-gcc15-cpu-v1).
2. `test-backend-ops -o FLASH_ATTN_EXT -b ROCm0`: all pass, including the 52 `n_seq=` cases. Run it again with `GGML_CUDA_FA_MASK_SKIP_MIN_KV=0`.
3. Exactness: `fa_harness ROCm0 exact` must give the same `ALL` hash with `GGML_CUDA_FA_MASK_SKIP=0` and `=1`.
4. The P3 re-measurement on the 27B (below). The no-regression check at zero foreign cells is the `L0_base` row: drafted 36.3 and no-draft 20.4 tok/s on v10.

## Full-scale P3 re-measurement (needs an exclusive MI210 window from the main session)

- **Harness.** `/mnt/raid0/llm/tmp/x0-27b-quants/p3_kvu_probe.sh` (owned by workspace-89).
  - The binary is hard-coded in two places: `BIN=` in `p3_kvu_probe.sh:23` and `x0_common.py:21`. The wrapper also checks that `kernels/production/gpu` resolves to `BIN` (`p3_kvu_probe.sh:65`).
  - The re-run needs a `BIN` override (for example a `P3_BIN` env var) and a separate results dir. The store-symlink check must be skipped for a non-production binary.
- **Arms, all on the same port, flags, prompt and park mode:**
  1. `BIN=kernels/builds/gpu-20261003-a0d0ae238/bin`
  2. the same binary with `GGML_CUDA_FA_MASK_SKIP=0` (in-binary control, equivalent to unpatched v10 kernels plus SW-9)
  3. optionally, v10 again for ABA
- **Phases.**
  - A1 (57k measurement plus three ~100k parked neighbours, fills L0..L3, drafted and no-draft).
  - B (llama-batched-bench, `-kvu` vs `-no-kvu`, npl 4).
- **Expectations, to falsify:**
  - L3 drafted ≥ about 33 tok/s (vs 15.4) and no-draft ≥ about 19 tok/s (vs 8.3), within ~10% of L0.
  - B `-kvu` S_TG within ~5% of `-no-kvu` (was -15.2%), and S_PP closer to `-no-kvu` (was -28.6%).
  - L0 unchanged within noise.
- **Footprint.** Same as P3 (about 52 GiB VRAM peak), so :8083 must be down or displaced for the window. Budget about 60–75 min per arm, judging from the original P3 run.
- **Small GPU validation before that window.** `/mnt/raid0/llm/tmp/fa-maskskip-20261003/gpu_slot.sh` takes about 15–20 min and peaks under 2 GiB. It covers exactness on the store build, the kernel micro-benchmark, P3-mini (gemma-3-1b) and small-scale batched-bench `-kvu` vs `-no-kvu`.

## Not done / follow-ups

- **MMA with `nstages > 1`** (NVIDIA Ampere and newer, cp.async pipeline) does not skip: `kv_skip_supported=false`, and the KV_max path is unchanged. Nothing on this host uses it.
- **WMMA rows=8 residual** (+18% at 112k foreign). Capping `parallel_blocks` by live blocks would need the live count on the host; it is not worth a sync.
- **Latent tile-kernel hazard.** The D=512/576 GQA tile kernel's output on gfx90a depends on codegen (a no-op branch in its KV loop made it nondeterministic, about 1e-4 nmse). This is pre-existing upstream code. It is worth an upstream issue, and it affects Gemma-4 D=512 layers on HIP.
