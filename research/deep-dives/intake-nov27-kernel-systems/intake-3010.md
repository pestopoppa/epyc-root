# opencl: add multi token f32 GEMV for spec verify

[Primary source](https://github.com/ggml-org/llama.cpp/pull/33098) · intake-3010 · 2026-11-27

Merged 2026-11-26 at 9fa7a33c. Contiguous aligned 2D F32 rows, N=2..8 K divisible by four, load a float4 weight once per lane for all N columns, lane-tile K with 4..64 lanes per row in a 64-thread group, local memory reduction and private accumulators. M<=512 and at least 256 workgroups in final code. Initial commit admitted M>512; follow-up specifically keeps those on tiled GEMM. Adreno X2E/A8X enabled by default, E17 quirks guarded, controls allow opt-in. Author Gemma-4-E4B-it-Q4_K_M with draft max 7 reported 907.127→924.818 encoded t/s (+1.95%) and 32.959→34.280 decoded t/s (+4.01%), unchanged 194/465 accepted, 41.720%; no runs, confidence interval or exact device identified in PR body.

handoffs/active/rocm-kernel-authoring.md:L1150-L1154 @ b93bd31 already tests Q8-MULTICOL-GEMV-1 and Q8-W8-GEMV-1. Local Q8 row-reuse first design lost served performance with width-8 dominant; width-8 successors already underway. MI210 transfer is shape gates, weight reuse and register/LDS pressure controls only, no OpenCL port. On EPYC 9655 use the same principle only for a measured small-width CPU verification matrix where existing iqk behavior and vector register pressure leave room.

The final PR merged on November 26. The current local Q8 in-place path passed its op gate; its served profile against V5I showed almost no gain. See rocm-kernel-authoring.md under Q8-W8-INPLACE-E2E-1 and Q8-SERVED-PROFILE-1. The F32 census is distinct.

## Evidence

- The kernel hoists each weight vector before iterating narrow columns. [ggml/src/ggml-opencl/kernels/mul_mm_f32_f32_l4_lm.cl:L225-L232 @ 9fa7a33](https://raw.githubusercontent.com/ggml-org/llama.cpp/9fa7a33cbbba2400eeb773a475038bc49e4dbe16/ggml/src/ggml-opencl/kernels/mul_mm_f32_f32_l4_lm.cl)
- The final merged route is limited to N=2..8 and at most 512 output rows. [ggml/src/ggml-opencl/ggml-opencl.cpp:L33713-L33720 @ 9fa7a33](https://raw.githubusercontent.com/ggml-org/llama.cpp/9fa7a33cbbba2400eeb773a475038bc49e4dbe16/ggml/src/ggml-opencl/ggml-opencl.cpp)

## Scope and local transfer

Patch second commit contradicts first commit's wide-M behavior. No independent replication found; the PR describes one unchanged acceptance trace and a narrow gain, while our separate HIP width-8 work demonstrates the motif's register-pressure tradeoff.



Completed Q8 w8 and queued fused small-K width 1–4 work do not count F32 rows by M and verify width. Classify retained verify calls by input type, rows, K, verify columns and selected kernel. Bound F32 time that a weight-sharing GEMV could recover against served dispatch. Stop at zero eligible share or an immaterial upper bound.

## Sources surfaced

No additional decision-changing source identified.
