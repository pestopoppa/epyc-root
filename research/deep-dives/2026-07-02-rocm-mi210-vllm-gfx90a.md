# ROCm on MI210 (gfx90a): vLLM-from-source build path and the gfx90a support matrix

**Date:** 2026-07-02
**Companion progress log:** [`progress/2026-07/2026-07-02-mi210.md`](../../progress/2026-07/2026-07-02-mi210.md)
**Companion handoffs:** [`handoffs/active/gpu-drafter-mi200-investigation.md`](../../handoffs/active/gpu-drafter-mi200-investigation.md) · [`handoffs/active/gpu-acceleration-path.md`](../../handoffs/active/gpu-acceleration-path.md) · [`handoffs/active/rocm-verify-profile-backend.md`](../../handoffs/active/rocm-verify-profile-backend.md)
**Intake entries:** intake-759 (ROCm/aiter) · intake-760 (ROCm/triton) · intake-761 (ROCm/flash-attention) · intake-762 (vLLM Dockerfile.rocm) · intake-763 (vLLM v0.6.5 ROCm docs)
**Scope:** the *evaluation-frontier* vLLM path on our newly-installed MI210 (gfx90a). Does NOT touch the working production GPU path (llama.cpp-HIP), which is documented in the progress log and needs no vLLM.
**Credibility:** the support-matrix facts below are CONFIRMED from vendor READMEs / official docs / the pinned Dockerfile (compile-compatibility claims). No AMD/MI210 *benchmark* number exists in any of these sources (the FlashAttention README ships A100/H100 plots only). Per `MEASUREMENT.md`, everything performance-related here is an **observation / hypothesis** until we run an actual build + bench on our own card — never decision-gating.

---

## TL;DR

- **Two things are now settled by the support matrix, on paper:** (1) gfx90a/MI210 is a *supported, buildable* vLLM target — `PYTORCH_ROCM_ARCH` includes `gfx90a`, and vLLM has **not** dropped gfx90a (current vLLM still ships ROCm 7.0/7.2.1 wheels; v0.6.5's default ROCm target is 6.2, matching our bind-mount exactly); (2) an MI210 vLLM build **loses AITER/MORI/DeepEP acceleration** — those three `*_ROCM_ARCH` lists are `gfx942;gfx950` only — and falls back to reference Triton/CK kernels.
- **The number is still not in.** No README/doc contains a gfx90a benchmark. The open "vLLM MI210 number" item in the progress log remains a build-and-measure task, not a literature question. The intake cluster de-risks the *path*, not the *result*.
- **llama.cpp-HIP is the working path; vLLM is a measurement instrument, not a second production binary.** Our production GPU path uses native ggml-cuda / rocWMMA / MFMA and does **not** use Triton or vLLM. The only reason to stand vLLM up on the MI210 is to answer one question: *do vLLM's gfx90a kernels beat llama.cpp's ~47%-roofline ceiling?*
- **Fastest route to that answer is the already-verified prebuilt image** (`rocm/vllm:rocm6.4.1_vllm_0.10.1_20250909`, found in the progress log) — a from-source build is the fallback/frontier if the prebuilt image is inadequate.

---

## 1. The two-binary-vs-one-binary context (why vLLM at all)

The 2026-06-26 v6 cutover consolidated CPU inference onto **one** kernel (llama.cpp production-consolidated-v6). The GPU story mirrors that discipline:

- **llama.cpp-HIP = the working / production GPU path (one binary).** Verified 2026-07-02 on gfx90a: isolated worktree `mi210-hip-enable` off `production-consolidated-v6`, `-DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a`, one fp8-guard fix (`0ebf1b4d7`). It runs GGUF weights, uses native `ggml-cuda` + **rocWMMA** (intake-303, the gfx90a-capable ROCm lib on our path) + MFMA, and — decisively — **gemma4-31B + NEXTN MTP spec-dec works GPU-only** (43.25 t/s, 1.44×). qwen35 (gated-delta-net) also decodes clean on this path. This path does **not** use Triton or vLLM.
- **vLLM = the evaluation frontier (a second engine, NOT a production deployment).** It loads HF weights, brings its own kernel stack (Triton fused-MoE / paged-attn, CK/Triton FlashAttention, and — on supported archs — AITER). We stand it up **only** to get an apples-to-apples throughput reference against llama.cpp-HIP. The progress log's kernel-headroom analysis found llama.cpp gfx90a decode tops out at ~33% (Q4_K) / ~47% (Q8_0) of the MI210's ~1.64 TB/s HBM roofline; vLLM is the instrument that tells us how much of that gap is llama.cpp-kernel-maturity vs a genuine CDNA2 ceiling.

Keeping vLLM framed as an *instrument* (not a candidate production engine) matters: vLLM 0.10.1 — and even current v0.22.0 — do **not** support our 2026 archs (`gemma4`, `qwen35`), so vLLM can never be the frontdoor/worker engine for our current models. The head-to-head therefore uses a **shared model both engines can load** (Qwen3-8B, via `Goedel-Code-Prover-8B-HF` → f16 GGUF for llama.cpp).

---

## 2. The gfx90a support matrix (CONFIRMED from sources)

| Component (repo) | Intake | gfx90a / MI210 status | ROCm target | Installs as / used by | On llama.cpp path? | Verdict |
|---|---|---|---|---|---|---|
| **ROCm/triton** | 760 | **First-class, tuned.** `main_perf` branch ships AMD-tuned FA/GEMM perf-kernels; gfx90a is a mature CDNA2 target (README says only "AMD GPUs, ROCm 5.2+", but AMD's GEAK-eval / TritonBench-revised suites are gfx90a-proven). | ROCm 5.2+ | `pytorch-triton-rocm`; dependency of vLLM (fused-MoE, paged-attn), FlashAttention's Triton path, AITER. Without it those Python-framework kernels fall back or fail on gfx90a. | **No** — llama.cpp-HIP uses native ggml-cuda, not Triton. | adopt_component |
| **ROCm/flash-attention** | 761 | **Supported.** README targets the MI200 family (CDNA2 = gfx90a = MI210/MI250) + MI300. Both backends cover MI200: **CK** (default; fwd+bwd, head dims ≤256, fp16/bf16) and **Triton** (opt-in via `FLASH_ATTENTION_TRITON_AMD_ENABLE=TRUE`; adds paged attention, FP8 WIP, fp32, RDNA). | **ROCm 6.0+** (satisfied by our 6.2 bind-mount) | Standard `flash_attn` PyTorch package → PyTorch/vLLM. **Not** llama.cpp. | **No** (llama.cpp has its own rocWMMA FATTN). | adopt_component |
| **vLLM Dockerfile.rocm** | 762 | **Split.** `PYTORCH_ROCM_ARCH` **includes gfx90a** (MI210 core builds compile) **BUT** `AITER_ROCM_ARCH` / `MORI_GPU_ARCHS` / `DEEPEP_ROCM_ARCH` = `gfx942;gfx950` **only** → an MI210 build gets **no AITER/MORI/DeepEP acceleration**; falls back to reference kernels. | **ROCm 7.2.3** base (`rocm/dev-ubuntu-22.04:7.2.3-complete`, Ubuntu 22.04 / Py 3.12) — a large gap above our 6.2. | Two-stage base/app Docker build (heavy toolchain in `rocm/vllm-dev:base`, thin vLLM wheel on top). | **No.** | adopt_patterns (reference build recipe) |
| **vLLM v0.6.5 ROCm docs** | 763 | **Documented buildable target.** Requirements list MI200s (gfx90a) + MI300 (gfx942); build section names "MI210/MI250/MI300" explicitly, via `PYTORCH_ROCM_ARCH="gfx90a"`. **Current vLLM has NOT removed gfx90a** (still listed; ships ROCm 7.0/7.2.1 wheels). | **DEFAULT ROCm 6.2** — coincides exactly with our devcontainer bind-mount. | Prebuilt (`docker build -f Dockerfile.rocm`, buildkit) or from-source vs host ROCm+PyTorch; Triton FA default, CK FA optional (`BUILD_FA`). | **No.** | worth_investigating |
| **ROCm/aiter** | 759 | **NOT supported.** Support matrix lists only gfx942 (CDNA3) + gfx950 (CDNA4); gfx90a absent. No llama.cpp/ggml binding (reachable only via vLLM/SGLang/JAX). | ROCm 6.x/7.0+ | The AMD operator library; default kernel/attention backend for vLLM/SGLang **on supported archs**. | **No** — and cannot be reached from our stack on gfx90a. | adopt_patterns (ceiling ref only: MLA 17× / MHA 14× / fused-MoE 3× — all MI300X/MI350, none gfx90a) |

**Reading of the matrix, in one line:** the *enabling* pieces (Triton, FlashAttention-2, the vLLM core wheel) all cover gfx90a; the *accelerator* pieces (AITER, MORI, DeepEP) do not. So a gfx90a vLLM is a **reference-kernel vLLM** — real, buildable, correct, but running Triton/CK kernels rather than AITER's hand-tuned CDNA3 paths. That is exactly the fair comparison we want against llama.cpp's own reference-maturity gfx90a kernels.

Pinned known-good combo in the vLLM recipe (carry as a starting reference, re-pin for whichever ROCm we target): **Triton** `0f380657` (+cherry-pick `555d04f`), **Flash-Attention** `0e60e394`, **AITER** `v0.1.16.post2`, **PyTorch** `d0c8b1f3` (release/2.11). Build accelerators: mold linker + ccache/sccache + uv; `VLLM_USE_PRECOMPILED=1` escape hatch.

---

## 3. Step-ordered build recommendation

The goal is a single decision-relevant number: **matched-precision Qwen3-8B, vLLM-gfx90a vs llama.cpp-HIP, fp16**, batch-1 (per-stream) and batched (vLLM aggregate). Ordered cheapest-first:

1. **Try the already-verified prebuilt image FIRST.** The progress log's scout already found and staged `rocm/vllm:rocm6.4.1_vllm_0.10.1_20250909` — upstream ROCm/vllm, no MI300 lock (confirmed via config blob), `PYTORCH_ROCM_ARCH=gfx90a;gfx942;...`, ROCm 6.4.1 within our host-6.2 driver compat window. This is the fastest path to a number; a from-source build is only warranted if this image is inadequate (won't load the model, ABI mismatch, or we need coverage the image's vLLM 0.10.1 lacks).
2. **If building from source, target CURRENT vLLM (~v0.22.0), not v0.6.5's model coverage.** v0.6.5 (~Dec 2024) bundles a vLLM that predates our models (the earlier docker dead-end was vLLM 0.4.3, too old for gemma4/qwen3.6). Use v0.6.5 **only** for its from-source *recipe* (ROCm-6.2 default, `PYTORCH_ROCM_ARCH="gfx90a"`), not its stale wheels. Caveat that doesn't change the plan: even current vLLM lacks `gemma4`/`qwen35`, so Qwen3-8B remains the shared head-to-head model.
3. **ROCm target: build against our host 6.2 bind-mount first; treat 7.2.3 as the fallback.** The canonical recipe pins ROCm **7.2.3** — well ahead of our **6.2**. But v0.6.5's default and current-vLLM wheels both cover the 6.2/7.0/7.2.1 range, and 6.2 matches the devcontainer exactly (least blast radius). Sub-decision: (a) build vs host ROCm 6.2 (recommended first attempt — matches driver, and the fp8/ABI-era gaps at 6.2 are already characterized on our card, see §4); (b) mirror the recipe's 7.2.3-complete base in a throwaway container if the 6.2 build fights toolchain gaps (bigger, but the vendor's known-good combo).
4. **`PYTORCH_ROCM_ARCH=gfx90a` (single arch).** Drop `gfx942;gfx950` to cut compile time — we only have a gfx90a card.
5. **Accept the AITER/MORI/DeepEP loss and set the reference-kernel env explicitly** (these are the pre-armed workarounds already recorded in the progress log): `VLLM_ROCM_USE_AITER=0`, `VLLM_USE_TRITON_FLASH_ATTN=1`, `TORCH_BLAS_PREFER_HIPBLASLT=0`, `--dtype float16`. This forces vLLM onto the Triton/CK reference path that *does* cover gfx90a and avoids the gfx942-only hipBLASLt/AITER kernels that caused the `std::bad_cast` ABI failure on the MI300-locked image.
6. **Reuse the Dockerfile.rocm two-stage split, with two overrides.** Keep the base/app factoring (heavy toolchain + framework build in `rocm/vllm-dev:base`; thin vLLM-wheel app layer on top; mold + ccache/sccache + uv). Overrides: (i) add `gfx90a` to the `*_ROCM_ARCH` lists (or accept that AITER/MORI/DeepEP won't build for it), and (ii) rebase FROM a ROCm-6.2 image instead of `7.2.3-complete` if pursuing the 6.2 path.
7. **FlashAttention backend: Triton FA as primary, CK as fallback.** The progress log already chose `VLLM_USE_TRITON_FLASH_ATTN=1` (the vLLM ROCm default), and Triton is a gfx90a-tuned target. Keep CK-FA (the FA-2 default backend, gfx90a-supported, fp16/bf16, head dim ≤256) as the fallback and **verify it actually builds for gfx90a** — the README claims MI200 support but ships zero AMD/MI210 numbers (see §4 risk).

---

## 4. Open risks (honest)

- **fp8 / ABI-era gaps at ROCm 6.2.** llama.cpp already hit this exact class on our card: `ggml-cuda/vendors/hip.h` guarded OCP fp8 typedefs on `HIP_VERSION>=60200000`, but ROCm 6.2 ships only the `_fnuz` fp8 types (OCP types landed in ROCm **6.3**) — every TU failed until the guard was bumped. A from-source vLLM/torch-ROCm at 6.2 can hit analogous fp8/ABI issues; the vendor's known-good combo is pinned at **7.2.3**, so a 6.2 build "fights the same fp8/ABI-era gaps" (intake-762 contradicting-evidence). Mitigation: the prebuilt 6.4.1 image sidesteps this entirely — prefer it for the first number.
- **CK-FA gfx90a build is claimed, not demonstrated.** ROCm/flash-attention README targets MI200 but publishes only A100/H100 plots. We must confirm compile + correctness of the CK backend on our gfx90a before trusting it; Triton FA is the lower-risk default.
- **No performance number exists anywhere upstream.** Every source in this cluster is compile-compatibility-confirmed and performance-unmeasured. The whole exercise is observation-tier until we run it on our card (`MEASUREMENT.md`).
- **Prebuilt image is 6.4.1, a bespoke 6.2 build is unproven.** The verified image runs ROCm 6.4.1 (within the host-6.2 compat window); a from-source build pinned *exactly* to host 6.2 has not been attempted and may need its own pin-matching.
- **Model coverage gap is structural.** Neither vLLM 0.10.1 nor current v0.22.0 supports `gemma4`/`qwen35`; the head-to-head is Qwen3-8B by necessity. A deployment-scale Gemma-3-27B comparison (~100–190 GB downloads, now feasible post-reclaim) is a separate, later step gated on the 8B result being surprising.

---

## 5. What is CONFIRMED vs what still needs a build+benchmark

**CONFIRMED (support-matrix facts, from READMEs/docs/the pinned Dockerfile):**
- gfx90a is a first-class, tuned ROCm/Triton target (`pytorch-triton-rocm`).
- FlashAttention-2 covers gfx90a via CK (default) + Triton at ROCm 6.0+.
- vLLM's `PYTORCH_ROCM_ARCH` includes gfx90a, and vLLM has **not** dropped gfx90a (v0.6.5 default ROCm = 6.2; current wheels ship ROCm 7.0/7.2.1; current mainline ≈ v0.22.0).
- AITER, MORI, and DeepEP **exclude** gfx90a (gfx942/gfx950 only) → gfx90a vLLM is a reference-kernel build.
- The vLLM-ROCm base image is pinned to ROCm 7.2.3, well above our 6.2 bind-mount.

**STILL NEEDS A BUILD + BENCHMARK (no source supplies it):**
- A gfx90a vLLM that actually loads and runs our shared model.
- The matched-precision Qwen3-8B throughput number vs llama.cpp-HIP — the single decision-relevant output. It answers the standing kernel-headroom question: is llama.cpp's ~47%-of-roofline gfx90a ceiling a llama.cpp-kernel-maturity gap (vLLM beats it) or a genuine CDNA2 reference-kernel ceiling (vLLM ties it)?

---

## 6. Cross-refs
- Working GPU path + first benchmarks + the open vLLM item this de-risks: [`progress/2026-07/2026-07-02-mi210.md`](../../progress/2026-07/2026-07-02-mi210.md).
- MI210 drafter/placement design (hardware gate now OPEN): [`gpu-drafter-mi200-investigation.md`](../../handoffs/active/gpu-drafter-mi200-investigation.md).
- gfx90a as an *authoring* target for hand-HIP kernels that close the roofline gap: [`rocm-verify-profile-backend.md`](../../handoffs/active/rocm-verify-profile-backend.md), [`agentic-rocm-kernel-authoring.md`](../../handoffs/active/agentic-rocm-kernel-authoring.md) (AITER is the vendor ceiling those handoffs must beat).
- AITER ceiling reference (gfx942/gfx950 only): intake-759; rocWMMA (intake-303) is the gfx90a-capable ROCm lib our llama.cpp-HIP path actually uses.
