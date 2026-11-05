# AITER MI300 kernels → MI210 (gfx90a): what can be reverse-engineered, re-expressed, or written as our own

Date 2026-11-05. Static investigation only: nothing was built, run on the GPU, or committed. Inputs:

- AITER `src/` @ `3ba5ff7be51c04ad`.
- `OPS.md` (the buildability table).
- C6 = `729599d69` at worktree `/mnt/raid0/llm/worktrees/kernels/refactor-c6-20261030`, with the build recipe in
  `/mnt/raid0/llm/kernels/builds/gpu-20261030-729599d69-c6/CMakeCache.txt`.
- Project docs, plus a web prior-art sweep.

Analysis scripts and disassemblies are in `/mnt/raid0/llm/tmp/aiter-port-scratch-20261105/`. That folder is
disposable: `analyze_co.py`, `retarget_check.py`, `hazard_scan.py`, `schedtest.hip`, and three `.s` dumps. Paths
below are relative to `src/` unless stated otherwise.

**Evidence tags.**

- **[R]** I read it in source or disassembly, or ran a tool and saw the output.
- **[R-sub]** A subagent read it and gave file:line, and I spot-checked some of these lines.
- **[W]** From the web; [F] means the page was fetched, [S] means only a search snippet was seen.
- **[I]** My inference or estimate. No number tagged [I] has been measured on our MI210.

---

## 0. Headline findings

1. **AITER's gfx942 (MI300) bf16 asm kernels use no MI300-only instruction in their MFMA, LDS or VALU mix.** [R]
   - gfx940 renamed `v_mfma_f32_32x32x8bf16_1k` to `v_mfma_f32_32x32x8_bf16` and `16x16x16bf16_1k` to
     `16x16x16_bf16`. Only the opcode byte differs (`0xe6` vs `0xe0`, `0xe7` vs `0xe1`). The semantics are the same.
   - I disassembled the gfx942 code with LLVM 18, applied those two renames, and re-assembled every line with
     `llvm-mc -mcpu=gfx90a` (`retarget_check.py`). Results:

| gfx942 kernel | lines | lines that fail on gfx90a |
|---|---|---|
| `hsa/gfx942/fmha_v3_fwd/MI300/fwd_hd128_bf16_causal_rtne.co` (FA fwd, d128, causal) | 3206 | **0** |
| `hsa/gfx942/pa_a16w16_b16.co`, `pa/pa_bf16_noquant_gqa8_1tg_4w.co` (paged attention, bf16 KV) | 2285 / 3303 | **0** |
| `hsa/gfx942/bf16gemm/bf16gemm_fp32bf16_tn_128x64_bshuffle_splitk.co` (bf16 GEMM, split-K) | 2801 | 48, all `global_atomic_pk_add_bf16` |
| `hsa/gfx942/fmha_v3_bwd/bwd_hd128_bf16_a16_rtne.co` | 4740 | 20, all `global_atomic_pk_add_bf16` |
| `hsa/gfx942/fmoe_b16.co` (bf16 fused MoE) | 4217 | 48, all `global_atomic_pk_add_bf16` |
| `hsa/gfx942/i8gemm/I8gemm_bf16_perTokenI8_BpreShuffle_128x128.co` | 1988 | 416: 384 × `v_mfma_i32_16x16x32_i8` and 32 × atomic |
| `hsa/gfx942/pa_a16w8_b16.co` (int8 KV) | 2321 | 192 × `v_mfma_i32_16x16x32_i8` |

   "Assembles" does not mean "correct and fast". Section 6 covers the hazard, kernel-descriptor and timing caveats.

2. **The hard MI300-only dependencies are few:** [R]
   - FP8 MFMA: `v_mfma_f32_{16x16x32,32x32x16}_fp8_fp8`, `v_cvt_pk_fp8_f32`.
   - The K-doubled int8 MFMAs: `v_mfma_i32_16x16x32_i8`, `v_mfma_i32_32x32x16_i8`.
   - `global_atomic_pk_add_bf16`, `v_mov_b64`, and `global_load_lds_dword`.

   Everything else the kernels lean on exists on gfx90a, confirmed with `llvm-mc -mcpu=gfx90a` (encodings were
   identical to gfx942 unless noted):
   - `buffer_load_dword … lds` (LDS-DMA, with identical encoding), `s_setprio`, and `v_pk_mul/fma/add/mov_f32` /
     `v_pk_mov_b32`.
   - MFMA with VGPR acc/dst, which shows the unified VGPR/AGPR file is present.
   - VMEM loads directly into AGPRs.
   - The 64 KiB LDS. Every gfx942 kernel I looked at declares `group_segment_fixed_size: 65536`.

3. **gfx950 (MI355) kernels are not portable. Use only the gfx942 directory as source material.** [R]
   - They use 160 KiB / 130 KiB LDS (`fwd_hd128_bf16_causal.co` 163840, `fwd_hd256_bf16_causal_group.co` 133120).
   - They use `ds_read_b64_tr_b16`, `buffer_load_dwordx4 … lds`, and `v_mfma_f32_{32x32x16,16x16x32}_bf16`, none of
     which gfx90a has.
   - Disassembled with the ROCm 10.1 LLVM at `/mnt/raid0/llm/rocm-10.1.0-q38p/install/lib/llvm/bin`, because LLVM 18
     does not know gfx950.
   - **Consequence: the only hd256 v3 FA asm is gfx950-only.** The gfx942 FA is hd128 and hd192x128 only
     (`csrc/cpp_itfs/mha_fwd.cu:219-231`). So for the 27B (hd256) there is no AITER asm to lift.

4. **On gfx90a, int8 MFMA has the same rate as bf16 MFMA**: 1024 ops/clk/CU, so 181 TOPS = 181 TFLOPS. [I, from ISA
   pass counts and the datasheet]
   - On MI300 int8 is 2× bf16.
   - Int8 MMQ on MI210 therefore saves bytes and dequant work, never MFMA time.

5. **MI210 is relatively richer in bandwidth and LDS than MI300.** [I, from spec arithmetic]
   - MI210: 1024 flop/clk/CU against ~9 B/clk/CU of HBM and 128 B/clk/CU of LDS. MI300X: 2048 flop/clk/CU against
     ~8.3 B/clk/CU of HBM and 128 B/clk/CU of LDS.
   - MFMA is also twice as long per shape on gfx90a: 64 cycles for 32x32x8 bf16 vs 32 cycles on gfx942.
   - So a schedule that is barely balanced on MI300 becomes MFMA-bound on MI210, with VALU, softmax and LDS work
     hidden more easily. MI300's scheduling tricks (ping-pong, exp/MFMA interleave) are therefore worth less on MI210
     than on MI300.
   - The tricks that keep HBM busy at small M (deep prefetch, weights straight to registers, split-K) are worth as
     much or more.

---

## 1. Inventory by family: hard ISA dependencies vs techniques

Instruction mixes come from `analyze_co.py` [R]. LDS = `group_segment_fixed_size`; VGPR = the unified VGPR+AGPR
count; WG = maximum workgroup threads. All kernels are wave64.

| Family (gfx942 .co) | LDS / VGPR / WG | MFMA used | gfx90a-blocking instructions | Techniques visible in the disassembly |
|---|---|---|---|---|
| bf16 GEMM `bf16gemm_*_bshuffle_splitk` (M tiles 32…160 × N 64; `bf16gemm_fp32bf16.csv`) | 64K / 512 / 256 | 384× `v_mfma_f32_16x16x16_bf16` (= gfx90a `16x16x16bf16_1k`) | `global_atomic_pk_add_bf16` (split-K bf16 output) | **B pre-shuffled** in HBM and loaded with `buffer_load_dwordx4` **straight into AGPRs** (`a[128:131]`), skipping LDS. A goes through **LDS-DMA** (240 `buffer_load_dword … lds`, m0 stepped per load). Fully unrolled K with the steady pattern `M s D M s D R R` (MFMA, LDS-DMA, ds_read), about 18 loads in flight (`s_waitcnt vmcnt(18)`), split-K with atomic reduction |
| int8 GEMM `I8gemm_bf16_perTokenI8_BpreShuffle_*`, `gemm_a8w8_m128_*` | 64K / 512 / 256 | `v_mfma_i32_16x16x32_i8`, `v_mfma_i32_32x32x16_i8` | both MFMAs; re-express as 2× `16x16x16i8` / `32x32x8i8` (gfx90a), as C6 already does (`mma.cuh:1311-1314`) | same B-preshuffle direct-to-AGPR and LDS-DMA scheme; per-token scale epilogue with `v_pk_mul_f32` (exists on gfx90a) |
| FA fwd v3 `fmha_v3_fwd/MI300/fwd_hd128_bf16*` | 64K / 256 / **512 (8 waves)** | 176× `v_mfma_f32_32x32x8_bf16` | none | **8-wave ping-pong**: two loop copies run at `s_setprio 0` / `s_setprio 1` (scratch `fmha_fwd_hd128_causal.s:721,1517`), synchronised by `s_barrier`. One group does MFMA while the other does softmax and loads. **Softmax interleaved with MFMA**: `M v v v v v v v M …` and `E M E E M E E M` (one MFMA per 7 VALU, `v_exp_f32` threaded between MFMAs). K/V via LDS-DMA, interleaved with ds_reads (`R R R R D` ×4). Software bf16 rounding variants (rtne/rtna/rtz), 2× unrolled loop, separate causal variant |
| FA bwd v3 | 64K / 512 / 256 | 480× `16x16x16_bf16` | `global_atomic_pk_add_bf16` (dQ) | atomic dQ accumulation; not needed for inference |
| Paged attention asm `pa_a16w16_b16`, `pa/pa_bf16_noquant_gqa8_1tg_4w` | 64K / 412–512 / 256 | 416× `16x16x16_bf16` | none (bf16 KV). Int8/fp8 KV variants use `16x16x32_i8` / fp8 MFMA | **GQA-packed Q** (8 or 16 q heads share one KV read, so MFMA runs on decode), 160× `dwordx4` KV loads, 1 workgroup with 4 waves |
| Fused MoE asm `fmoe_b16`, `fmoe_int8_*`, `fmoe_bf16_blockscaleFp8_*` | 64K / 512 / 256 | bf16 `16x16x16`; int8 `16x16x32_i8`; fp8 | atomic bf16; int8 and fp8 MFMA | expert-sorted token tiles, gate+up fused (`g1u1`), multi-x, atomic bf16 output |
| RMSNorm (`allreduce_rmsnorm_N8192.co` asm; the plain `module_rmsnorm` is HIP) | 64K / 512 | none | none | `v_pk_add/mul/fma_f32` packed-fp32 math, dwordx4 loads. The HIP version already builds for gfx90a with `__gfx90a__` `v_pk_mul_f32` branches (`csrc/include/aiter_opus_plus.h:24`; OPS.md) |
| Quant / FP8 / MXFP (`f4gemm`, `fp8gemm_blockscale`, `flatmm_uk_*_f16f8`) | n/a | FP8/FP4 MFMA | the MFMA itself | weight-only upconvert ideas only (§3) |

**Feature checklist from the brief.** [R] unless tagged.

- **FP8/BF8 MFMA:** MI300-only. It is the hard blocker for every fp8 kernel.
- **gfx940+ MFMA variants:**
  - xf32 does not appear in any kernel I sampled.
  - The 32x32x16 / 16x16x32 bf16 shapes are gfx950-only.
  - The K-doubled int8 shapes are gfx940+.
- **v_pk_* fp32:** present on gfx90a.
- **buffer_load … lds:** present on gfx90a, but only for dword, ubyte and ushort. `dwordx4 … lds` is rejected for
  both gfx90a and gfx942 (gfx950 only).
- **`global_load_lds_*`:** gfx940+.
- **sched_group_barrier:** a compiler pseudo, not an ISA instruction. `llvm-mc` rejects it for both arches. Section 5
  covers its compiler support.
- **s_setprio:** present.
- **LDS size:** 64 KiB on both gfx90a and gfx942; 160 KiB on gfx950.
- **Unified AGPR/VGPR:** gfx90a has it. `llvm-mc -mcpu=gfx90a` accepts `v_mfma_f32_32x32x8bf16_1k v[64:79], …` with
  a VGPR accumulator, which gfx908 could not.
- **Dual issue:** no new mechanism on either arch. Both rely on different waves on a SIMD issuing to MFMA and VALU in
  the same cycle, which is what ping-pong exploits. [I, ISA knowledge]
- **wave64:** both arches.

---

## 2. Can each technique be expressed on gfx90a, and what does it buy at our shapes?

Shapes are from the timing packet README: 27B with hidden 5120, ffn 17408, 24q/4kv heads, d=256, FA every 4th layer;
Qwen3-4B with d=128. MI210 practical ceilings:

- 1433 GB/s, 87.5% of spec (`/workspace/handoffs/active/autokernel-loop.md:1951`, R-sub).
- MFMA microbench 172 TFLOPS (`handoffs/completed/mi210-mfma-compute-bound-paths.md:28`, R-sub).

| Technique (where AITER uses it) | Expressible on gfx90a? | Regime it helps | Expected value on MI210 [I unless noted] |
|---|---|---|---|
| B-preshuffle (weights stored in MFMA operand order, dwordx4 straight to registers, no LDS) | Yes, in HIP: a repacked weight layout plus 16-byte loads. The AGPR destination is asm or compiler-dependent | small-M GEMM (M=1…32), which is bandwidth-bound | high at M=5…16 (§4 item 1) |
| Deep prefetch / many loads in flight (`vmcnt(18)`) | Yes (HIP unroll, or `raw.buffer.load.lds`) | bandwidth-bound GEMV and skinny GEMM | +10–25% kernel BW where C6 sits at 31–70% of roofline |
| Split-K with atomic reduction | Yes, with an f32 `global_atomic_add_f32` or `pk_add_f16`. bf16 pk atomics are missing | skinny GEMM with too few output tiles to fill 104 CUs | enables the above at N·M/tile < 104 |
| LDS-DMA ping-pong double buffering | Yes, dword-wide only (`buffer_load_dword … lds`, identical encoding) | compute-bound GEMM, FA | moderate: removes load→MFMA serialization (C6 MMQ has none) |
| 8-wave ping-pong + `s_setprio` | Yes (`__builtin_amdgcn_s_setprio` + barriers; verified to compile, §5) | compute-bound FA, large GEMM | lower than on MI300 because gfx90a is MFMA-bound sooner; maybe +5–15% over a well-pipelined single-schedule kernel |
| Softmax-in-registers + exp/MFMA interleave | Yes (sched_group_barrier, VALU/TRANS masks; verified to compile) | FA prefill | large vs C6's rocWMMA FA, which runs softmax through LDS (§4 item 2) |
| Causal block skipping | Yes (pure control flow) | FA prefill | up to 2× on causal FA FLOPs; C6 does it only for ≥1024 Q rows or multi-seq (`fattn-common.cuh:1477`, R-sub) |
| 32x32 MFMA tiles instead of 16x16 | Yes (`32x32x8i8`, `32x32x8bf16_1k`) | MMQ, FA | same MFMA rate, half the LDS operand traffic per flop (32x32x8: 512 B per 64 cycles vs 16x16x16: 512 B per 32 cycles). Matters once LDS-bound |
| Stream-K / persistent | Yes; C6 already does stream-K MMQ on AMD (`mmq.cuh:894-1135`, R-sub) | tail effects | already present |
| GQA-packed decode attention (PA asm) | Yes | decode attention with GQA 6:1 (27B) | small for llama.cpp (FA is 1–5% at ~300 tokens; `kernel-champion-and-promotion.md:3779`, R-sub), more at 32k |
| Fused norm/quant epilogues (rmsnorm+quant, `v_pk_*`) | Yes; the HIP versions already build for gfx90a | decode non-GEMM tail (27–31% on dense, 62% on 30B-A3B; `quantization-and-low-bit.md:101`, R-sub) | small per kernel, cheap |

**Regime summary for our shapes.** [I]

- **Decode M=1…4** is HBM-bound. 27B Q8_0 ≈ 28.7 GB of weights gives a ~50 tok/s ceiling at 1433 GB/s, against C6's
  33.0 tok/s with speculation off. MFMA tricks are irrelevant here; load depth, width and alignment are what matter.
- **DFlash verify M≈7…16** is still HBM-bound, and 70% of the 67 ms step is `mul_mat_q`
  (`kernel-champion-and-promotion.md:327`, R-sub). The ideal is ≈20 ms of weight streaming against ≈47 ms spent.
  **This is the largest single gap.**
- **Prefill M=512…2048:**
  - Compute-bound in principle. 27B pp2048 ≈ 919 t/s ≈ 50 TFLOPS ≈ 27% of peak.
  - About 51% of prefill time is rocBLAS. Q8_0/Q6_K at ne11>128 are dequantized to f16 and sent to rocBLAS
    (`mmq.cu:296-312`, R-sub). The convert costs ~15% (`mi210-serving-program.md:1031`).
  - The remainder is GDN/SSM, norms and FA.
- **FA:**
  - pp512 at depth 16k costs ~25% more than at depth 0 (852 → 640–660 t/s).
  - In the 80k-context verify step, FA is 28.7 ms and the q8_0→f16 KV convert is 7.9 ms of 158.7 ms (R-sub).

---

## 3. FP8 on CDNA2

- **No FP8 MFMA, no FP8 cvt.** [R] `v_cvt_pk_fp8_f32` and the fp8 MFMAs fail on gfx90a. AITER's own gfx90a fallback
  decodes fp8 in software on the KV path (`csrc/include/attention_common.cuh:264-272`: `#if defined(__gfx90a__)` →
  `vllm::fp8::vec_conversion`, else `__builtin_amdgcn_cvt_pk_f32_fp8`).
- **Weight-only FP8 (W8A16) with in-register upconvert to bf16/f16 is feasible.** [I] For e4m3 the cost is about 2–4
  VALU ops per pair (shift/perm plus exponent rebias; subnormals need a select or a LUT, or can be ignored if
  calibrated). That is cheap against 64 cycles of MFMA at M≥64, and against HBM time at M=1.
- **For llama.cpp it buys nothing over Q8_0.** [I]
  - Q8_0 is 8.5 bits/weight. FP8 with per-channel scale is ≈8.0, so ≈6% fewer bytes, while Q8_0's per-32 block
    scaling is at least as accurate.
  - MMVQ already streams int8 and uses `v_dot4_i32_i8` (`common.cuh:694-697`, R-sub). An FP8 GEMV would have to
    upconvert to f16 and use `v_dot2_f32_f16` at the same byte count, so it is a wash at best.
- **For vLLM it is the only way to serve FP8 checkpoints at 1 byte/weight on MI210.** This is the analogue of CUDA's
  FP8-Marlin W8A16 for Turing/Ampere [W-S].
  - vLLM's `supports_fp8()` returns true for any CDNA [W-F], but no gfx90a W8A16 kernel was found.
  - Value: halves weight traffic against bf16 on decode, so up to ~1.8× decode for bf16-served models. [I]
  - Effort M. Worth doing only if vLLM-on-MI210 serving of FP8 checkpoints is a goal.
- FP8 KV cache: an emulated fp8 KV is equivalent to llama.cpp's q8_0 KV in bytes, so there is no gain for llama.cpp.

---

## 4. C6 vs AITER per op: where C6 leaves the most, ranked

C6 facts are [R-sub] from `ggml/src/ggml-cuda/`. I spot-checked several lines [R]:

- `mma.cuh:1311-1314`: two `16x16x16i8` on CDNA2.
- `mmq-config-cdna.cuh`: 512 threads, occupancy 1, mmq_y 128, J ≤ 64.
- `mmq.cuh:849-884`: synchronous `load_tiles` → `__syncthreads` → `vec_dot` with no double buffer.
- `fattn-wmma-f16.cu:1`: "Old and deprecated".
- `mmf.cu:171-173`: dense MMF off on CDNA2.
- PR #21519's CDNA2 constant fix is present (`common.cuh:72` = `0x90a`).

The build is `GGML_HIP_ROCWMMA_FATTN=ON`, `GGML_HIP_MMQ_MFMA=ON`, gfx90a.

| C6 op | What C6 does on gfx90a | What AITER does for the same op | Gap at our shapes |
|---|---|---|---|
| `mul_mat_q`, M=5…16 (DFlash verify; Q8_0 / K-quants route to MMQ from ne11 ≥ 5) | 512-thread tile with mmq_y=128, J≥16, 16x16x16i8 MFMA, synchronous global→LDS, no prefetch, stream-K over 104 blocks. Q8_0 MMQ is about **31% of BW roofline** at M=8/16 (`quantization-and-low-bit.md:101`) | `bf16gemm`/`I8gemm` with 16…48-row M tiles: pre-shuffled B straight to AGPR, deep vmcnt pipelining, split-K atomics | **Largest.** ≈47 ms vs ≈20 ms ideal per 27B verify step |
| `flash_attn_ext_f16` rocWMMA (prefill and verify with rows >2) | 16x16x16 f16 fragments, **f16 VKQ accumulation**, K read from global, softmax through LDS, nwarps 4 (8 in C6's d128 cell), q8_0 KV **fully converted to f16 first** | FA v3: 32x32 MFMA, softmax in registers interleaved with MFMA, LDS-DMA K/V, 8-wave ping-pong, causal variants | Large at long context: FA 18% plus convert 5% of the 80k verify step |
| prefill `mul_mat` Q8_0/Q6_K/IQ at ne11>128 | dequant → f16 → rocBLAS | asm/CK a8w8 straight on int8 with fused per-token/per-channel scales | ~15% convert, plus whatever rocBLAS loses |
| `mul_mat_vec_q` M=1…4 | `sdot4`, 2/4/8 warps, Q8_0 ints assembled from u16 loads (34-byte blocks are 2-byte aligned). **70%** of roofline for Q8_0 at M=1; Q4_K 46%. An LDS-DMA prefetch variant exists but is **off by default** (`GGML_CUDA_Q8_PREFETCH=0`, `mmvq.cu:1719-1726`) | (AITER has no quantized GEMV asm; its skinny bf16 HIP and preshuffle ideas apply) | Q8_0: about 15 points to the 85–87% ceiling |
| norm / quantize tail | separate kernels | fused add+rmsnorm(+quant), `v_pk_*` | 3–7% of decode for `quantize_q8_1` (docs conflict) |

---

## 5. The own-kernel option (operator addendum)

### 5a. Tooling path

- **Assembling gfx90a: verified.** [R] The ROCm 6.2 `llvm-mc -mcpu=gfx90a` assembles everything listed in §0. The
  CDNA2 ISA guide is public.
- **How AITER loads `.co`:** [R] `csrc/include/aiter_hip_common.h:285-425`.
  - It does not use `hipModuleLoad`. It registers the in-memory hsaco with `__hipRegisterFatBinary` +
    `__hipRegisterFunction`, keyed by the mangled kernel symbol from the per-arch CSV (e.g.
    `hsa/gfx942/fmha_v3_fwd/fmha_fwd.csv`: `_ZN5aiter24fmha_fwd_hd128_bf16_rtneE`).
  - It resolves the handle with `hipGetFuncBySymbol` and launches with `hipModuleLaunchKernel`, passing one packed
    argument blob via `HIP_LAUNCH_PARAM_BUFFER_POINTER/SIZE`.
- **Argument layout:** [R] packed structs in which every field is padded to 16 bytes (e.g. `fmha_fwd_v3_args`,
  `csrc/include/mha_fwd.h:274-330`: a pointer plus `p2` padding, a u32 plus `p3` padding).
  - The kernel reads the fields with `s_load_dword sN, s[0:1], 0x…`; offsets 0x10, 0x20, … are visible in the
    disassembly.
  - Grid and block are computed on the host (`csrc/cpp_itfs/mha_fwd.cu:178-209,270-282`; FA fwd uses
    bdx=512 = 8 waves).
  - The arch is gated at runtime (`mha_fwd.cu:224`; `aiter/ops/attention.py:35`).
- **For llama.cpp:** [I] embed a gfx90a `.co` (or load it from the kernel store) with `hipModuleLoadData` /
  `hipModuleGetFunction`, then launch with `hipModuleLaunchKernel` and a packed arg blob.
  - C6 runs with `GGML_HIP_GRAPHS=ON`. Module-launched kernels should be capturable into hipGraphs, but this has to
    be verified on ROCm 6.2 before relying on it.

### 5b. The middle tier: builtins and scheduling hints in HIP

**Verified on our toolchain.** [R] `schedtest.hip` was compiled to assembly only (`clang -x hip --offload-arch=gfx90a
--cuda-device-only -S -o -`, ROCm 6.2 clang, LLVM 18). It wrote no binary and produced zero errors.

- The compiler accepts these for gfx90a: `__builtin_amdgcn_mfma_f32_32x32x8bf16_1k`,
  `__builtin_amdgcn_sched_group_barrier` (MFMA 0x008, VALU 0x002, DS-read 0x100 masks), `__builtin_amdgcn_sched_barrier`,
  `__builtin_amdgcn_iglp_opt(0)` and `__builtin_amdgcn_s_setprio`.
- The emitted code shows `v_exp_f32` interleaved between `v_mfma_f32_32x32x8bf16_1k`, with the accumulator in
  `a[0:15]`.
- `llvm.amdgcn.raw.buffer.load.lds` (LDS-DMA) is already used in C6's opt-in `mul_mat_vec_q8_0_prefetch`
  (`mmvq.cu:962-1118`, R-sub).

The compiler also inserts the MFMA hazard `s_nop`s itself, which is the main safety advantage over hand-written asm.

**Not verified:** whether the newer `iglp_opt` modes for FA-style MFMA/exp interleave (added in later LLVM) exist in
LLVM 18 and are tuned for gfx90a. Use explicit `sched_group_barrier` sequences instead; they are arch-agnostic.

Known compiler limits [W-F, HipKittens; I]:
- HIPCC will not use AGPRs as MFMA A/B inputs, and it can spill under 512-register pressure.
- Those two, plus exact cross-wave ping-pong timing, are where asm still pays.

### 5c. When hand-written asm pays on gfx90a [I]

- **Less than on MI300**, because MFMA is twice as long relative to VALU, LDS and HBM: the schedule saturates MFMA
  with less precision.
- **Asm is justified when:**
  - (1) register pressure: hd256 FA, where the O accumulator is 256 columns and the compiler spills or drops occupancy;
  - (2) direct-to-AGPR weight streaming in skinny GEMM, if the compiler refuses it;
  - (3) after builtins have plateaued and a profile shows issue stalls rather than bandwidth stalls.
- **Cost:**
  - Per-shape and per-dtype variants (AITER ships 23 bf16 GEMM and 160 FA bwd `.co` for gfx942 alone).
  - Hazard correctness by hand.
  - Maintenance across llama.cpp rebases is low if the kernel sits behind a stable arg blob, but high if the
    tensor layouts change.
- **Autokernel fit:** the sched_group_barrier pattern (group sizes and order), unroll depth, vmcnt depth and tile
  shape are all discrete knobs. They are a natural search space for the existing autokernel loop, at HIP level and
  without asm.

### 5d. The cheapest asm experiment: retarget AITER's gfx942 bf16 kernels

Retargeting is mechanical (§0). Before any timing it needs three things:

1. **An MFMA hazard audit at gfx90a pass counts.** gfx90a 32x32x8 bf16 = 16 passes and 16x16x16 = 8 passes, against
   8 and 4 on gfx942 [I]. The gfx942 code is padded for gfx942 latencies, and gfx90a needs software wait states for
   VALU reads of MFMA results.
   - A linear scan (`hazard_scan.py`) found the closest MFMA→VALU consumer in the PA kernel at 13 wait states. I
     believe that clears gfx90a's ~10 for an 8-pass MFMA, but this comes from memory of the ISA table [I].
   - In the FA kernel the consumers cross control-flow boundaries, so the scan cannot settle it. A CFG-aware audit is
     needed.
2. **A gfx90a kernel descriptor.** Rebuild the `.amdhsa_*` block: accum_offset, VGPR/AGPR split, and LDS 65536.
3. **A numerical check against a reference.**

Where it applies:
- FA hd128 fwd: Qwen3-4B and vLLM.
- bf16 PA: vLLM decode with bf16 KV.
- bf16 split-K GEMM: replace the bf16 pk atomics with f32 atomics plus a convert pass, or with `pk_add_f16`.

It does **not** give the 27B an hd256 FA.

---

## 6. Caveats on reading the gfx942 asm as "almost gfx90a"

- Timing is untested. MFMA latency doubles, so the ping-pong phase balance changes. My expectation is that the
  kernel ends up MFMA-bound, which is fine, but this is [I].
- The kernels use no gfx940 cache-policy bits (`sc0/sc1/nt`: zero occurrences in the three dumps) and no `s_getreg`
  XCC/HW-ID tricks. The buffer descriptor word3 is `0x20000`, the same constant CK uses for all of gfx9 including
  gfx90a (`3rdparty/composable_kernel/include/ck/ck.hpp:86-88`). [R]
- These are all positive signs, but any kernel can still depend on gfx940 timing in ways a static check cannot see.

---

## 7. Prior art (web; [F] fetched, [S] snippet)

- **llama.cpp:**
  - #14624 (MFMA MMQ; on by default only for CDNA3; MI300 numbers only) [F].
  - **#23227 (MMVQ↔MMQ crossover tuned on MI250X; batched 27B Q4_K_M B=8 66.8→107.6 t/s)** [F]. C6 already carries
    the analogue (commit 387c4d9e1, R-sub).
  - #21519 (the CDNA2 constant fix; present in C6) [F].
  - #19806 (fattn-mma on CDNA3: +39% pp4096 on MI300X; on MI100 MMA vs tile 1.26–1.44× at batch 512) [F].
  - IMbackK: rocWMMA builds are suboptimal on CDNA [F]. rocWMMA FA reportedly removed upstream in #26046 [S].
- **CK-tile FMHA:** the gfx9 codegen (`fmha_fwd.py`) covers gfx90a. It emits `qr_async` for non-bias fp16/bf16 and
  `qr` for hdim 256 [F]. Only the `trload` pipelines are gfx950-only. **This makes CK-tile fwd the ready-made gfx90a
  hd256 reference.** AITER's `module_mha_fwd` wraps it (OPS.md).
- **vLLM:**
  - wvSplitK skinny GEMM builds for gfx90a, but only on the `v_dot2` path [F].
  - The custom paged attention is allowed on any CDNA for head 64/128 [F].
  - AITER is disabled on gfx90a [F].
  - FP8 Marlin (W8A16) exists for CUDA only [S].
- **HipKittens** (arXiv 2511.08083) [F]: 8-wave ping-pong, 4-wave interleave, AGPR pinning, chiplet swizzle. It is
  evaluated on MI325X and MI355X only and does not discuss CDNA2. Everything except the chiplet swizzle, 16-byte
  LDS-DMA and large LDS carries over in principle [I].
- **MI210 measurements:**
  - BabelStream 1.24–1.37 TB/s [S].
  - No public MI210 rocBLAS/hipBLASLt bf16 GEMM TFLOPS were found. One Triton bf16 4096³ run reports ~94–100 TFLOPS
    [S, 403 on fetch].
  - hipBLASLt bf16 support on gfx90a may only have arrived in ROCm 7.2 [S]. Our host runs ROCm 6.2.
- **Not found:** public reverse engineering of the AITER asm, or public MI210 FA TFLOPS for d128.

---

## 8. Ranked shortlist

Gain ranges are **estimates [I]** unless marked; none was measured on our MI210. Tier key:

- **T1** = re-express with CK/HIP using existing libraries or patterns.
- **T2** = HIP plus MFMA builtins plus `sched_group_barrier`/`setprio`/LDS-DMA intrinsics.
- **T3** = our own gfx90a asm, either retargeted from gfx942 or hand-written.

| # | Technique (AITER source) | C6 op | Expected gain on MI210 | Right first tier, and gain per tier | Effort | First concrete step |
|---|---|---|---|---|---|---|
| 1 | **Skinny-M weight streaming**: pre-shuffled weights loaded with dwordx4 straight to registers, deep vmcnt prefetch, split-K (`bf16gemm_*_bshuffle_splitk`, `I8gemm_*_16x128…48x128`) | `mul_mat_q` at ne11 5…16 (DFlash2 verify; Q8_0 at ~31% of BW roofline) | kernel 31% → 60–75% of BW. 27B verify step 67 → ~45–50 ms. **DFlash2 tok/s +20–35%** [I] | **T2.** A "multi-column MMVQ" with 16x16x16i8 MFMA or sdot4, a repacked 16 B-aligned Q8_0 layout (qs and scales split), many loads in flight, and split-K with f32 atomics. T2 should reach most of the gain because the op is bandwidth-bound. T3 adds ≤10% [I] (AGPR-direct loads) | M | rocprof the 27B 7-token verify per `mul_mat_q` shape and record achieved GB/s. Then prototype Q8_0 M=8 on the qproj/gate_up/down shapes in `test-backend-ops perf` against the current MMQ |
| 2 | **FA prefill rewrite**: softmax in registers, 32x32 MFMA, LDS-DMA double buffer, fp32 accumulation, in-kernel q8_0 dequant, causal skipping; optionally 8-wave ping-pong (`fmha_v3_fwd`) | `flash_attn_ext_f16` (rocWMMA) for D=256 (27B) and D=128 | FA kernel 1.5–3× [I]. End to end: +5–10% pp at 16k depth, **+15–25% on 80k verify steps** (FA 18% + convert 5% of the step) [I] | **T1 first:** time the CK-tile fmha fwd for gfx90a hd256 (`module_mha_fwd`; packet B "fa" cells) against C6, and A/B C6's already-tuned `fattn-mma` D=256 path, which is inert under ROCWMMA=ON. **T2:** port the winning structure into ggml with q8_0 dequant in-kernel. **T3:** retarget the gfx942 hd128 v3 asm (0 assembly errors) for d128 only; own hd256 asm only if T2 spills | M (T1/T2), L (T3 hd256) | When packet B runs, read its fa rows. Also time C6 with `GGML_HIP_ROCWMMA_FATTN=OFF` on the D=256 prefill shapes, noting the documented DFlash long-prompt failure (`llama-v11-manifest.md:47`) |
| 3 | **Q8_0 MMVQ load path**: aligned/repacked weights, more loads in flight, LDS-DMA prefetch (AITER preshuffle plus deep-vmcnt idea) | `mul_mat_vec_q` M=1…4 (Q8_0 70%, Q6_K 63%, Q4_K 46% of roofline) | Q8_0 kernel +10–20% → spec-off decode +7–14% [I]. More for K-quants, but those are not the key-role quants | **T2.** The prefetch kernel already exists and is off by default. A repacked layout removes the u16-assembled loads. T3 is not needed (bandwidth-bound) | S–M | A/B `GGML_CUDA_Q8_PREFETCH=1` on 27B Q8 tg; dump ISA of the eight-warp cell to check whether `bff30cebe`'s 16 B memcpy really emits dwordx4 |
| 4 | **Pipelined int8 MMQ for large M**: LDS-DMA double buffer, 32x32x8i8 tiles, J up to 128, sched_group_barrier MFMA/DS interleave (`I8gemm`/`gemm_a8w8` schedule pattern `M s D M s D R R`) | prefill `mul_mat` Q8_0/Q6_K at ne11>128 (dequant→rocBLAS) and MMQ at ne11≤128 | Drops the ~15% convert. At parity with rocBLAS that is **pp +10–20%** [I]. No 2× int8 advantage on gfx90a | **T2** in `mmq.cuh` (MFMA is already wired; add the double buffer, 32x32 tiles and a schedule). Alternatively, T1 CK a8w8 from AITER (packet B "gemm_i8" rows). T3 only if T2 stalls well below rocBLAS | M–L | Read packet B's gemm_i8 rows against C6. Profile pp2048 to get the split between convert, rocBLAS, GDN and FA before touching code |
| 5 | **Fused norm/quant epilogues** (`v_pk_*` rmsnorm+quant; HIP versions build on gfx90a) | `rms_norm` + `quantize_q8_1` + add tail | decode +2–5% [I] (`quantize_q8_1` 3–7%; norm tail 43% at B=128) | **T1/T2** | S | Read packet B's rmsnorm rows; fuse `quantize_q8_1` into the preceding norm in ggml |
| 6 | **Retargeted gfx942 asm (FA d128, bf16 PA, bf16 split-K GEMM)** as an existence proof and for vLLM | 4B-class FA d128; vLLM attention and bf16 GEMM | unknown until timed. Plausibly near MFMA-bound [I] | **T3 (retarget)**: hazard audit, then gfx90a descriptor, then a correctness test | M | Build a CFG-aware MFMA-hazard checker over the `.s` dumps (extend `hazard_scan.py`) and audit `fwd_hd128_bf16_causal_rtne` |
| 7 | **FP8 W8A16 upconvert** (Marlin-style) | vLLM FP8 checkpoints only; **none for llama.cpp** (Q8_0 is the same bytes) | up to ~1.8× decode against bf16 serving in vLLM [I] | **T2** | M | Only if vLLM-on-MI210 with FP8 checkpoints becomes a goal |
| 8 | Fused MoE asm (`fmoe_b16`) | `mul_mat_id` (30B-A3B) | unknown; MoE decode is dominated by non-weight kernels (62%) | T1 CK 2-stage first (OPS.md "uncertain") | L | Wait for packet A/B MoE results |

**Recommended order** (it agrees with the operator's framing):

1. Find the gaps with the rocprof per-shape GB/s and TFLOPS numbers plus packet B's AITER timing rows. The packet B
   timing has not run yet: there is no `out/` under `rock-aiter-timing-20261105/`.
2. Run T2 on items 1, 3 and 4, with the autokernel loop searching scheduling and tile knobs.
3. Go to T3 only for FA hd256 (item 2), if T2 spills or plateaus, and for the item-6 retarget as a cheap existence
   proof.
