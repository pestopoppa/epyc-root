# Handoff: MI210 batch-1 latency wall — greenfield kernel research (prefetch → megakernel)

**Status**: OPEN — greenfield kernel-authoring research. **Created**: 2026-07-04 (MI210 campaign; operator-prioritized over the cheap n-gram lever).
**Owner tree**: `/mnt/raid0/llm/llama.cpp-experimental` (kernel work here ONLY, never production-v6). Builds ON the dequant-GEMV work in `mi210-q8-dequant-gemv-roofline.md` — coordinate; don't edit `mmvq.cu` in parallel with that thread.
**Substrate**: MI210 gfx90a/CDNA2, 64 GB HBM2e ~1.64 TB/s, 8 MB L2, 64 KB LDS/CU, 64-wide wavefront, ROCm 6.2. All numbers OBSERVATION.
**Context**: `fable5-window2-findings-05b-mi210-inference-architecture.md` §1/§9; `mi210-q8-dequant-gemv-roofline.md` (Tier-2).

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
Software-pipeline the next weight tile's load under the current tile's compute in `mul_mat_vec_q`. gfx90a: `__builtin_nontemporal_load` / `buffer_load` with explicit prefetch distance, LDS double-buffering (64 KB/CU), `s_waitcnt` scheduling. Increases in-flight requests → higher achieved BW. **Acceptance**: achieved BW 62%→~70%, single-stream decode +~12%, PPL/output unchanged.

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
