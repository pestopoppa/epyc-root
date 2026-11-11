# AITER on gfx90a (MI210): op inventory for ROCK-AITER-GFX90A

Source: `src/` = github.com/ROCm/aiter @ `3ba5ff7be51c04ad747a61da406cedf6c2d9c126` (shallow clone, 2026-11-05);
CK submodule `3rdparty/composable_kernel` fetched with `--depth 1`. Paths below are relative to `src/`. This is a
static source read. Nothing was built or run. "Plausible" means no MI300-only construct was found on the op's gfx90a
path. Packet A tests that.

## Build system

- **JIT is the default.** `setup.py:30` sets `PREBUILD_KERNELS` to 0 unless the variable is set. Each op is a
  `compile_ops("module_x")` module defined in `aiter/jit/optCompilerConfig.json` (142 modules). Ninja/hipcc builds a
  module the first time it is called, into `AITER_JIT_DIR` (`aiter/jit/core.py:910-922`; the default is the source
  `aiter/jit` dir when that dir is writable). CK modules also run a codegen step first (`blob_gen_cmd`).
- **Arch selection.** `GPU_ARCHS` (`;`-separated, default `native`) is validated against an allow-list that
  **includes gfx90a** (`aiter/jit/core.py:934-960`, `aiter/jit/utils/build_targets.py:12`). `PYTORCH_ROCM_ARCH` only
  matters to torch.
- **Hand-written asm (.co) exists only for newer archs.** `hsa/` contains `gfx942/`, `gfx950/` and `gfx1250/` and
  nothing for gfx90a. Every `*_asm` module therefore has no gfx90a kernel: `module_gemm_a16w16_asm`,
  `module_gemm_a8w8_asm`, `module_fmha_v3_*`, `module_attention_asm` (pa_fwd), `module_moe_fmoe_asm`, MLA asm, and
  the others. The runtime enforces this, for example `aiter/ops/attention.py:35`
  `_PA_FWD_ASM_SUPPORTED_ARCHS = ("gfx942", "gfx950")`.
- **Toolchain.** `requirements.txt` notes that torch and triton "are provided by the base image as ROCm-specific
  builds". `setup.py:116-135` needs torch >= 2.9.1 for its triton handling. Docs say ROCm 5.0+ is enough for gfx90a
  (`docs/index.rst:103`) and require "PyTorch 2.0+ with ROCm" (`docs/installation.rst:18`), but those lines are stale
  compared with the code, which uses torch 2.10-era APIs.
- **vLLM image.** `docker/Dockerfile.rocm_base` builds AITER at tag `v0.1.27` with
  `PREBUILD_KERNELS=1 GPU_ARCHS=${AITER_ROCM_ARCH}`, where `AITER_ROCM_ARCH="gfx942;gfx950"`. gfx90a is in
  `PYTORCH_ROCM_ARCH` but **not** in AITER's arch list. Torch in the image is `2.13.0+rocm10.0.0` on Python 3.12, and
  the wheel is installed into site-packages. **The aiter that ships in the image has no gfx90a code objects.** It must
  be rebuilt for gfx90a from source, which packet A does by JIT inside the container.
- **Host vs container.** The host has ROCm 6.2 userspace and no ROCm torch >= 2.9 installed. A host build would mean
  installing ROCm torch for 6.2: the last 6.2 wheels are torch 2.5.x, which is below the 2.9.1 the code expects. The
  realistic route is **the pinned vLLM ROCm 10.0 container** (torch 2.13, hipcc 10.0, which still targets gfx90a
  because it is in the image's own `PYTORCH_ROCM_ARCH`), with the source tree mounted and `GPU_ARCHS=gfx90a`.

## Ops relevant to inference

| Op | AITER module / entry | Impl type | gfx90a plausible? | Evidence |
|---|---|---|---|---|
| RMSNorm | `module_rmsnorm`, `aiter.rms_norm` (`aiter/ops/rmsnorm.py:424`) | HIP (opus) | **Yes** | `csrc/include/aiter_opus_plus.h:24` and `csrc/kernels/rmsnorm_quant_kernels.cu:166,205` have explicit `__gfx90a__` branches (v_pk_mul_f32) |
| Fused add+RMSNorm | `rmsnorm2d_fwd_with_add` (`rmsnorm.py:447`) → `module_rmsnorm_quant` / CK `module_norm` | HIP + CK-tile | **Yes** (bf16 path); fp8-quant variants no | same gates; CK layernorm2d codegen is arch-generic |
| Activation (silu_and_mul) | `module_activation` (`aiter/ops/activation.py:12`) | HIP | **Yes** | `csrc/kernels/activation_kernels.cu:101,278,468,596` gfx90a branches |
| RoPE | `module_pos_encoding`, `module_rope_*` (`aiter/ops/rope.py:365`) | HIP | **Yes** | `csrc/kernels/rope/rope_common.h:7528` gfx90a branch |
| INT8 scaled GEMM (a8w8 rowwise) | `module_gemm_a8w8`, `gemm_a8w8_CK` (`aiter/ops/gemm_op_a8w8.py:795`) | CK `DeviceGemmMultiD_Xdl_CShuffle_V3` (`csrc/ck_gemm_a8w8/include/gemm_a8w8_common.cuh:116`) | **Uncertain** | CK xdl supports gfx90a int8 MFMA (32x32x8i8), but the generated instances come from a gfx942-tuned CSV. Instances with K-pack 16 (i8 32x32x16 is gfx94x-only) may not compile or may be rejected at runtime. `gemm_op_a8w8.py:62-65` only gates on `gfx9*`. The asm/bpreshuffle/blockscale/FlyDSL a8w8 paths are gfx942/950/1250 only (`:46-56`, `:261`) |
| FP8 GEMM / FP8 scaled-mm / MXFP4/6 | `gemm_a8w8_blockscale*`, `f4gemm_asm`, etc. | asm / CK / FlyDSL | **No** | CDNA2 has no FP8 MFMA. `attention_common.cuh:266` software-converts fp8 on gfx90a only for KV dequant |
| BF16 GEMM | `tgemm.mm` (`aiter/tuned_gemm.py:830`) → hipBLASLt (`module_hipbsolgemm`) / skinny HIP / torch | hipBLASLt + HIP | **Yes** for hipBLASLt/skinny; asm a16w16 no | `tuned_gemm.py:292` routes `gfx90a` to skinny kernels; `custom_kernels.cu:21,29` define `__HIP__MI300_MI250__` for gfx90a. The win over torch here is small: it is the same hipBLASLt |
| Fused MoE (CK 2-stage) | `module_moe_ck2stages`, `module_moe_sorting` | CK codegen | **Uncertain** | sorting: `csrc/include/moe_sorting_opus.h:276-283` says "Supported: gfx90a". 2-stage GEMM instances are tuned for gfx942. a16wmix is excluded: `aiter/fused_moe.py:3929-3932` says gfx90a "compiles with s_waitcnt is not supported"; `fmoe_asm` is gfx942+ only |
| Paged attention (decode) | `module_attention` (`aiter/ops/attention.py:102`, `csrc/cpp_itfs/pa/pa.cuh`) | HIP | **Yes** (native path) | `pa.cuh:30` defines `__HIP__GFX9__` for gfx90a; the asm `pa_fwd` is gfx942/950 only (`attention.py:35`) |
| Flash / MHA fwd | `module_mha_fwd`, `module_mha_varlen_fwd`, `aiter.flash_attn_func` (`aiter/ops/mha.py:3068`) | CK-tile fmha (`01_fmha/generate.py --receipt 600`) | **Yes** for CK fwd, bf16/fp16; v3 asm no | CK-tile fmha has supported gfx90a for a long time; `fmha_v3_*` uses `hsa/` asm, which has no gfx90a. hdim 256 (27B) is in the CK fwd instance set |
| Triton FA / Triton ops | `aiter/ops/triton/...` | Triton | **Yes** (if the triton in the image targets gfx90a) | `flash_attn_triton_amd/utils.py:56` puts gfx90a in `CDNA_ARCHS`; `:69` FP8_ARCHS excludes it |
| MLA, FlyDSL ops, mega-MHC, all `*_asm` | various | asm / FlyDSL | **No** | `hsa/` has no gfx90a; FlyDSL guards to gfx942/950 |

## Bottom line

- **Can build on gfx90a:** RMSNorm, fused add+RMSNorm (bf16), activation, RoPE, the native-HIP paged attention, CK
  flash-attn fwd, the hipBLASLt/skinny bf16 GEMM route, MoE sorting, and Triton kernels.
- **Uncertain:** CK int8 a8w8 GEMM and CK 2-stage fused-MoE. The code paths are arch-generic, but the instance tables
  were tuned for gfx942.
- **Cannot build:** anything FP8/MXFP, every hand-asm kernel (the fast bf16 GEMM, fmha v3, the asm PA, the asm fused
  MoE), MLA and FlyDSL. These are the kernels AITER's headline MI300 wins come from. The handoff's earlier
  "AITER gfx942-only (intake-759)" is wrong as a statement about the source tree, since gfx90a is an allowed target and
  the HIP/CK ops have gfx90a branches. It is right as a statement about the *fast asm* tier and the vLLM-shipped wheel.

## module_custom gfx90a build fix (2026-11-05)

- **Root cause**: `csrc/kernels/custom_kernels.cu` compiles the fp8 skinny-GEMM kernels `wvSplitKQ_hf_sml_` / `wvSplitKQ_hf_` under `__HIP__MI350_MI300_MI250__` (includes gfx90a), but they call `__builtin_amdgcn_mfma_f32_32x32x16_fp8_fp8`, which needs `fp8-insts` (gfx942/gfx950 only). 16 errors, lines 1892/2107; nothing else in the module fails.
- **Patch**: `/mnt/raid0/llm/tmp/rock-aiter-gfx90a-20261105/module-custom-fix-20261105/module_custom-gfx90a-fp8-guard.patch` (sha256 `a4f2592f…0bcc4`). It adds `__HIP__MI350_MI300_FP8__` (gfx942||gfx950) and re-guards just those two kernels. On gfx90a they become the file's existing `UNREACHABLE_CODE` stubs. The bf16/fp16 kernels (wvSpltK, wv_splitk_small_fp16_bf16, LLMM1) are unchanged and still built for gfx90a.
- **Compile test**: pinned image, `--cpuset-cpus 120-127`, no device, on a copy (`.../module-custom-fix-20261105/src`) → `status: built`, `so_archs: ["gfx90a"]`, 984,752 B, 31.8 s. Log: `.../module-custom-fix-20261105/compile-test.log`.
- **Apply + rebuild in shared src** (not done; job owner applies):
  `cd /mnt/raid0/llm/tmp/rock-aiter-gfx90a-20261105/rock-aiter-prebuild-20261105/src-gfx90a && patch -p1 < /mnt/raid0/llm/tmp/rock-aiter-gfx90a-20261105/module-custom-fix-20261105/module_custom-gfx90a-fp8-guard.patch` (dry-run clean). Then re-run the module_custom unit with the packet's docker_argv and `prebuild_one.py '{"unit":"module_custom","base":"module_custom","kind":"static","force":true}'`, or copy the tested `.../module-custom-fix-20261105/src/aiter/jit/module_custom.so` into `src-gfx90a/aiter/jit/`. The source must be patched either way: core.py rebuilds when the source changes.
- **Now testable**: the gemm_bf16_tuned skinny path (`ops.wvSpltK`, `LLMM1`, `wv_splitk_small_fp16_bf16`, used by tuned_gemm `libtype=skinny`), e.g. `test_gemm_a16w16.py -t skinny`. Paged attention itself (`paged_attention_v1/v2/rocm`) is in `module_attention`, which was already built. module_custom only clears the module-load blocker for test_pa if something on that path imports it.
- **Cannot work on gfx90a**: `wvSplitKQ`, the fp8 per-tensor-scaled skinny GEMM. CDNA2 has no fp8 MFMA, and the fp8 e4m3fnuz types do not exist in hardware. Workaround design: dequantize fp8 to bf16 (scale by s_A*s_B) into the existing bf16 `wvSpltK`, or handle it on the host in tuned_gemm by routing fp8 on gfx90a to hipBLASLt/torch.mm after the upcast. Risk: a caller that dispatches `wvSplitKQ` on gfx90a reaches the device `assert(false)` stub rather than getting a clean host error. The `pa_fwd_asm` path is also gfx942/gfx950-only by design (`_PA_FWD_ASM_SUPPORTED_ARCHS`). Restrict test_pa to the native path, as the TRIAGE notes already say.
