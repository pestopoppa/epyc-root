# Handoff: MI210 MFMA for compute-bound paths (prefill / diffusion / high-batch)

**Status**: OPEN — design + scoped-measurement first, then kernel work. **Created**: 2026-07-04 (MI210 campaign follow-on).
**Owner tree**: `/mnt/raid0/llm/llama.cpp-experimental` (kernel work here, never production-v6). **Substrate**: MI210 gfx90a/CDNA2 — has fp16/bf16/int8 **MFMA matrix cores**. All numbers OBSERVATION.
**Context doc**: `fable5-window2-findings-05b-mi210-inference-architecture.md` §9 (the GDN-MFMA-decode KILL, and why MFMA is alive for compute-bound regimes).

## Objective

The GDN-MFMA *decode* kernel was KILLED by profile: `gated_delta_net_cuda` @B=32 is memory/latency/occupancy-bound (MemUnitBusy 65.2%, VALUBusy 15.7%, MfmaUtil 0%), so MFMA has no compute headroom to exploit *in decode*. **But MFMA is the right lever for COMPUTE-bound paths**, which we have not optimized:
- **Prefill** — measured VALUBusy ~50% (vs 15.7% decode): far more ALU-active → MFMA-addressable. Long-context TTFT is the payoff (ingest role, big-prompt frontdoor).
- **Diffusion** — DiT image-gen (ERNIE-Image-Turbo on GPU) and block-diffusion drafters (DFlash): parallel denoise over a block, non-causal attention = large dense GEMMs = classic MFMA workload.
- **High-batch decode** — as batch grows, decode leaves the BW edge and becomes compute-bound (why bf16 batches better — fp16 runs native on matrix cores). The batched GEMM already routes to MMQ-MFMA; the question is whether it's fully utilizing MFMA.

## Decisive pre-build measurement (do this FIRST — don't build blind)

Profile MFMA utilization + the compute/memory split for each candidate path, to confirm MFMA is the bottleneck before authoring:
1. **Prefill**: rocprofv2 on `llama-batched-bench -npp 8192 -ntg 8` (long-prompt, decode-light) — MfmaUtil, VALUBusy, MemUnitBusy on the main GEMM kernels. If VALUBusy high + MfmaUtil low → MFMA GEMM path is a win. (Use rocprofv2 `--plugin file`; rocprof v1 SQ/TA counters read zero on this box.)
2. **High-batch decode**: rocprofv2 on `llama-batched-bench -npl 64/128` — is the batched MMQ path already MFMA-saturated (MfmaUtil high → no win) or MFMA-idle (win)?
3. **Diffusion**: N/A until a diffusion serving path exists (ERNIE DiT on ROCm/HIP is a separate pipeline task — `ernie-image-turbo-evaluation.md`); scope when that lands.

Acceptance to proceed to kernel work: a candidate path shows **high VALUBusy + low MfmaUtil** (compute-bound, matrix-core-idle). Otherwise defer.

## Kernel work (conditional on the measurement)

- Route the compute-bound GEMMs (prefill FFN/attention, diffusion denoise, high-batch expert GEMM) through **MFMA intrinsics** (`__builtin_amdgcn_mfma_*` / rocWMMA), matching CDNA2 tile shapes (16x16x16 / 32x32x8). rocBLAS/hipBLASLt Tensile kernels already MFMA-tune GEMM — check whether forcing the Tensile path for prefill beats llama.cpp's MMQ (we saw MMQ *beat* rocBLAS for batch-1 decode, but prefill is the opposite regime).
- Correctness: `test-backend-ops` + PPL/output parity.

## Cross-links / caveats

- This is **forward-looking**: prefill isn't today's complaint and there's no diffusion serving path yet, so this is lower-urgency than the single-stream dequant kernel (`mi210-q8-dequant-gemv-roofline.md`). Start with the *measurement* (cheap), gate the build on it.
- Ties to the DFlash port question (`fable5-window2-findings-05b` §2): if DFlash block-diffusion drafting is ever pursued on GPU, its denoise is exactly this compute-bound MFMA regime.
- Ties to gfx90a training viability [unverified] — training is compute-bound, MFMA-central.

## Key files
`ggml/src/ggml-cuda/mmq.cu` (MMQ-MFMA batched GEMM), `ggml/src/ggml-cuda/fattn*` (attention), `gated_delta_net.cu` (the decode kernel that was KILLED — reference for the memory-bound contrast). Prior profile: `/mnt/raid0/llm/tmp/mi210-build/campaign/finish/RESULTS.md` (Part B).
