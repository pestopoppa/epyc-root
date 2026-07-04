# Handoff: MI210 batch-1 latency wall — greenfield kernel research (prefetch → megakernel)

**Status**: OPEN — greenfield kernel-authoring research. **Created**: 2026-07-04 (MI210 campaign; operator-prioritized over the cheap n-gram lever).
**Owner tree**: `/mnt/raid0/llm/llama.cpp-experimental` (kernel work here ONLY, never production-v6). Builds ON the dequant-GEMV work in `mi210-q8-dequant-gemv-roofline.md` — coordinate; don't edit `mmvq.cu` in parallel with that thread.
**Substrate**: MI210 gfx90a/CDNA2, 64 GB HBM2e ~1.64 TB/s, 8 MB L2, 64 KB LDS/CU, 64-wide wavefront, ROCm 6.2. All numbers OBSERVATION.
**Context**: `fable5-window2-findings-05b-mi210-inference-architecture.md` §1/§9; `mi210-q8-dequant-gemv-roofline.md` (Tier-2).

## UPDATE 2026-07-04 — design research landed (supersedes parts of §Novelty + re-ranks the levers)

Read-only design pass complete (verified against fork source + on-box CK headers). Key corrections:

1. **The "no ROCm/CDNA2 megakernel exists" premise (below, §Novelty) is now STALE.** AMD Research shipped **Fleet** (arXiv **2604.15379**, 2026-04-15) — a persistent **HIP** megakernel porting Mirage-MPK to AMD Instinct, **1.3–1.5× lower batch-1–8 decode latency than vLLM-ROCm `--enforce-eager`** (demonstrated on CDNA3/4). Our novelty narrows to a **CDNA2 monolithic-8MB-L2, 104-CU, ggml-graph-integrated** instantiation. Mine Fleet + Mirage-MPK (2512.22219) + Hazy "Look Ma No Bubbles" (`github.com/HazyResearch/Megakernels`). All three sync op-to-op with **device-scope atomic counters + fences, NOT `grid.sync()`** — the control plane ports cleanly; cooperative-groups grid-sync already compiles+runs on HIP in-tree (`softmax.cu:148,355`, runtime-gated on `hipDeviceAttributeCooperativeLaunch`).

2. **Lever re-ranking — async prefetch (lever 1) strictly dominates the megakernel (lever 3) on effort-adjusted return, because HIP graphs are ALREADY ON in this build** (`GGML_HIP_GRAPHS=ON`; the `cc<AMPERE` disable at `ggml-cuda.cu:4456` never fires for AMD). Graphs already amortize *host* launch latency — so the megakernel's marginal value over graphs+prefetch is ONLY the residual *device-side* grid drain/fill + cold-L2-across-op-boundaries bubble. **Pass-2 of the measurement (below) must size that residual before committing the large build.** Sequence: **prefetch (1) → measure → swizzle (2) → measure Pass-2 → megakernel (3) only if residual bubble is large.**

3. **Exact gfx90a async-copy intrinsic** (the CDNA2 `cp.async` analog — note `CP_ASYNC_AVAILABLE` is hard-CUDA-gated at `common.cuh:291`, so today the AMD MMVQ has ZERO async copy): use the MUBUF direct-to-LDS DMA **`llvm.amdgcn.raw.buffer.load.lds`** (supported on gfx9 incl. gfx90a). **DO NOT use `__builtin_amdgcn_global_load_lds`** — that Clang builtin is gated to `gfx940-insts` (its aux cache bits don't exist on gfx90a). On-box reference to mine: `/opt/rocm/include/ck/utility/amd_buffer_addressing.hpp:959-1004` (`amd_direct_load_global_to_lds`, 4 B/lane) + `gridwise_gemm_pipeline_v4_direct_load.hpp`. Prefetch distance = the **VMCNT** counter (`s_waitcnt vmcnt(N)`); a 1-stage / two-LDS-buffer scheme is the right start. Load weights with **SLC/nontemporal** (stream — read once/token) but **A/B that knob** (8 MB L2); keep the activation vector `y` default-cached (temporal reuse). A `sched_barrier(0)` after the waitcnt is mandatory (else the compiler hoists LDS consumers past it).

4. **rocBLAS/hipBLASLt verdict**: keep the hand-rolled MMVQ — rocBLAS GEMV is **dense-only** (forces dequant-to-fp16 in HBM → 2–4× bytes moved → fatal for BW-bound decode; this is *why* MMQ beat forced-rocBLAS at batch-1, a bytes-moved gap not a kernel-quality gap). But **steal its double-buffer structure**: `rocblas_gemvn_double_buffered_kernel` is explicitly `is_gfx90a`-gated (`blas2/rocblas_gemv_kernels.cpp`) — proof double-buffered GEMV is a real gfx90a win (validates lever 1). Port the *structure* into the quantized MMVQ.

5. **Swizzle (lever 2)**: the 34-byte Q8_0 block (not power-of-2, not 128 B-aligned) straddles cache lines → an offline **SoA repack** (int8 quants contiguous 128 B-aligned + fp16 scales separate) is the fix — **shared with the dequant-GEMV handoff; do it once, jointly.** Do NOT reuse CK/Tensile MFMA-swizzled layout (de-coalesces at M=1). Gate on Pass-1 showing high sub-line `TCC_EA_RDREQ_32B` ratio.

**Measurement refinement**: the wall-budget below should run **Pass-2 both with graphs on AND `GGML_HIP_GRAPHS=0`** — the delta isolates residual host-launch overhead from the device-side bubble that only a megakernel removes. Expected dominant term is **latency-unhidden** (MemUnitStalled high + VALUBusy low + ~42% occupancy, matching the prior `gated_delta_net` profile) → confirms prefetch-first. Full report: subagent a327c35d (this session); primary sources arXiv 2512.22219, 2604.15379, Hazy Megakernels repo, LLVM D124884/PR#92962.

## The problem (why this is the ceiling nothing else touches)

Single-stream decode t/s = achieved_BW ÷ bytes/token. Measured: Q8 ~47% of roofline, fp16 ~62%. The **62→100% gap is the batch-1 latency wall**: by Little's law, sustained BW = requests-in-flight ÷ latency, and one token's GEMV can't issue enough independent HBM requests to hide memory latency. **62% is a kernel-MLP floor, not the physics floor.** The dequant handoff attacks 47→62 (dequant cost) + bytes/token (quant). This handoff attacks 62→~80 (memory-level parallelism), which nothing else can.

**Novelty**: every persistent-kernel / megakernel LLM-decode result (Hazy-flash, Mirage, megakernel-decoding) is CUDA/Hopper. **No ROCm/CDNA2 megakernel exists.** Porting the pattern to gfx90a is the research.

## Measure FIRST — characterize the wall's composition (don't build blind)

The 38% gap (62→100) is some mix of: (i) memory latency not hidden (insufficient in-flight requests), (ii) kernel-launch + grid-sync bubbles between the per-layer decode kernels, (iii) poor HBM coalescing. Each points to a different lever. rocprofv2 (v1 SQ/TA reads zero here) on the batch-1 Q8 decode of the 27B:
- **Achieved HBM BW vs peak** on `mul_mat_vec_q<Q8_0,1>` (MemUnitBusy, effective GB/s) — how far from the 1.64 TB/s / the 62% fp16 point.
- **Launch/bubble fraction** — HIP-trace gap analysis: sum of inter-kernel gaps vs kernel time per decode step (how many µs are launch/sync vs compute). HIGH → megakernel is the lever.
- **Occupancy + MemUnitStalled + L2 hit** on the GEMV — LOW occupancy / high mem-stall with idle ALU → prefetch/MLP is the lever.
- **Coalescing** — L2/MemUnit efficiency; poor → swizzle is the lever.
Deliver a "wall budget": of the 38pp, how much is launch-overhead vs latency-unhidden vs coalescing. This ranks the three levers below.

## The three levers (ranked by tractability; build order gated on the wall budget)

### 1. Async weight prefetch / double-buffering (MOST tractable — do first)
Software-pipeline the next weight tile's load under the current tile's compute in `mul_mat_vec_q`. gfx90a: `__builtin_nontemporal_load` / `buffer_load` with explicit prefetch distance, LDS double-buffering (64 KB/CU), `s_waitcnt` scheduling. Increases in-flight requests → higher achieved BW. **Acceptance**: achieved BW 62%→~70%, single-stream decode +~12%, PPL/output unchanged. **MEASURED 2026-07-04:** implemented (`raw.buffer.load.lds`, commit `7c28056b7`, runtime-gated); **+3.3% single-stream** (30.20→31.20), rocprofv2 **MemUnitStalled −62%** (mechanism confirmed), output byte-identical. Modest because it covers only ~half the Q8 GEMV dispatches — the fused-SwiGLU FFN up/gate matmuls are excluded; **fused-path extension in flight to ~double coverage.** Stacks with nwarps=4 (+4.6%). SoA-repack (lever 2) NOT warranted — coalescing measured healthy.

### 2. Weight swizzle / layout for gfx90a coalescing (medium)
Verify + fix the MMVQ HBM access pattern to coalesce to the 64-wide wavefront × 128 B cache line. A repack/layout of the Q8 weights offline + matching load pattern. Only worth it if the wall-budget shows poor coalescing. **Acceptance**: L2/MemUnit efficiency up, decode +~5-10%.

### 3. Persistent / megakernel decode (GREENFIELD, high-effort — the real prize)
One persistent kernel per decode step (or the whole step) that keeps the pipeline resident, streams weights with software pipelining, and eliminates the per-layer launch/sync bubbles (the Hazy/Mirage pattern). No ROCm precedent. **Scope from the wall budget**: only justified if launch/bubble fraction is large. Design surface: a grid-persistent kernel over the layer loop, LDS-staged weights, cooperative-groups grid sync (or a single-workgroup-per-CU persistent scheme), fused into `ggml`'s graph as a custom op. **Acceptance**: single-stream toward ~78% roofline (the Hazy H100 single-dispatch result), correctness-verified.

## Research grounding needed (non-GPU, startable now)
- Megakernel feasibility on ROCm/gfx90a: does HIP support the primitives (cooperative-groups grid sync `__syncthreads`-across-grid / `gridDim` persistence, or a single-wave-per-CU scheme)? What did Hazy/Mirage actually do, and which parts port? (arXiv + their code.)
- gfx90a async-copy intrinsics + LDS double-buffering patterns (CDNA2 ISA; `buffer_load_dword` prefetch; `ds_read`/`ds_write`; `s_waitcnt vmcnt`).
- rocBLAS/hipBLASLt Tensile: do their gfx90a GEMV/GEMM kernels already prefetch/swizzle better than llama.cpp's MMVQ? (They lost to MMQ at batch-1 decode — but why? profile.)

## Correctness / discipline
`test-backend-ops` parity + PPL/greedy-output unchanged for every kernel change; pair speed with correctness; OBSERVATION until P-GPU-1. Experimental tree only; operator-gated for prod. Coordinate `mmvq.cu` edits with the dequant handoff (don't double-edit).

## Key files
`ggml/src/ggml-cuda/mmvq.cu` (the GEMV to pipeline), `ggml/src/ggml-cuda/ggml-cuda.cu` (op dispatch + where a persistent op would hook the graph), `ggml/src/ggml-cuda/common.cuh` (CDNA2 defines). Prior profiles: `/mnt/raid0/llm/tmp/mi210-build/campaign/{prof,gdnprof,finish}/`.
