# llama.cpp PR #32505: CUDA: implement support for duplicate expert IDs

- **Intake**: intake-2719 (`intake-2719#record`)
- **Source**: https://github.com/ggml-org/llama.cpp/pull/32505
- **Verification**: dive-verified · read depth FULL
- **Disposition**: integrated; handoffs: autokernel-loop.md, kernel-champion-and-promotion.md, rocm-kernel-authoring.md
- **Run**: intake-kspec-20261120 (research-intake Stage 2/2b, 2026-11-20)

## Reader should conclude

Take this PR only with a whole upstream sync (it needs #31617, #31047, #27466). Do not claim it changes MoE top-k dispatch. No served model hits the duplicate-ID bug today; do not serve GROVEMOE or hash-routed archs on GPU before it lands.

## Key claims (anchored)

0. PR #32505 makes CUDA/HIP MUL_MAT_ID correct for duplicate expert IDs: it rewrites the mm_ids helper with ballot/popc, adds a wave64-safe ggml_cuda_popc, and removes the small-batch MMF kernel variant that does not use mmid.
   - PR body: "I rewrote the mmid helper kernel to use __popc and __ballot which has the added benefit of being faster than the previous version using __shfl instructions"
   - PR body: "Because AMD GPUs, particularly those with a warp size of 64 need special consideration I added a function ggml_cuda_popc to handle this"
   - PR body, MMF bullet: "So this PR simply removes the MMF kernel variant that does not use mmid"
1. Reported gains on wave64 CDNA1 are small: MI100 granitemoe 3B Q4_0 pp4096 1.01-1.04 with the first kernel, 1.00-1.03 with the final kernel.
   - Author comment 2026-11-18, final kernel table: "MI100 granitemoe 3B.A800M Q4_0 2048 pp4096 10754.51 11058.07 1.03"
   - PR body table, first kernel: "MI100 granitemoe 3B.A800M Q4_0 2048 pp4096 10695.00 11092.57 1.04"
2. A reviewer showed that few-row MMQ (mmq-few) still loses duplicate-ID entries on Ampere to Blackwell; the merged diff does not touch that path.
   - Review am17an 2026-11-18, item 1: "Two slots of one token that use the same expert get the same rank and write the same pair column, so one of them is lost"
   - Review am17an 2026-11-18, item 1: "MUL_MAT_ID uses this path on Ampere to Blackwell for Q8_0, Q3_K, Q4_K, Q5_K, Q6_K, IQ3_S, IQ4_NL and IQ4_XS with 9..24 tokens"
3. Before the final kernel a reviewer measured a Strix regression for Qwen3.8-Flash-Next with 10 experts used (0.909 at ub2048); the final push was not re-measured for that case.
   - Comment am17an 2026-11-18, Strix table: "Qwen3.8-Flash-Next UD-IQ1_S 10 2048 609.0 553.8 0.909"
   - Author comment 2026-11-18: "I pushed a new kernel that should not run into performance issues at large batch sizes and be consistently faster"
4. Removing the host-fallback break slows the BF16 MoE cuBLAS fallback.
   - Review am17an, item 3: "Removing the break slows the host fallback"

## Claim corrections

- claim 0: **narrowed** — The removed MMF variant serves only F16/BF16/F32 weights at ncols_dst<=16; our served MoE experts are quantized (MMQ/MMVQ), so the removal is perf-neutral for us.
- claim 1: **reattributed** — Stage-1 put 1.03-1.04 in comments; 1.01-1.04 is the PR body (first kernel), the final kernel comment shows 1.00-1.03.
- claim 2: **unaffected** — Reviewer finding confirmed; the merged diff does not change quantize.cu or mmq-few.cu.
- claim 3: **unaffected** — Confirmed; final Strix table re-measured only granitemoe.

## Dive record

2026-11-20 Stage-2 dive (opus; PR page, comments and diff; C14 eee3da838 and v10 ffc1bac82 via git show only). Value moves from 'rebase onto C14 for +1-4% pp' to 'take with the next whole upstream sync': C14/v10 fork from upstream a8dc0e326 (2026-07-16) and lack prerequisites #31617 (ggml_cuda_ballot / thread mask), #31047 (tile_spec MoE layout), #27466 (radix TOP_K gather) and the sparse-FA mask kernel; 4 of 9 hunks have no target, mmid.cu needs a ~200-line manual port; no hunk touches AK-changed code (mmf.cu/mmf.cuh/mmid.cu byte-identical v10 vs C14). MoE top-k dispatch is NOT changed (top-k.cu hunk only swaps a popc lambda inside GGML_OP_TOP_K; C14 routing uses ggml_argsort_top_k, the topk-moe fusion or the AITER asm). Duplicate-ID reachability on our served models: none found; argsort/top-k fusion give unique IDs on finite logits (llama-graph.cpp L2307, topk-moe.cu L137-147/L180-230 @eee3da8); GROVEMOE and deepseek4 hash routing can produce duplicates but are not served. C14 MMQ helper silently drops duplicate slots (mmid.cu L40-89 @eee3da8); host fallback asserts. Unverified: whether the AK-ASM-H11 AITER topksoftmax asm guarantees unique IDs on NaN/tie rows. mmq-few is absent from C14 and v10. Extra find: C14 mm_ids_helper templates cover n_expert_used 2/4/6/8/16/32 only (mmid.cu L146-167 @eee3da8); upstream #27978 adds <10>, so Q38FN (top-10) takes the generic per-token loop on MI210. Adversarial pass: Metal #30373, WebGPU #30451, Vulkan #29998 fixed the same bug class separately (independent); no independent HIP speed replication. Dive-surfaced #26631/#32504/#29998 declined (no zero-expert arch served; Volta-only; historical). lane_head 1650e3d9315f (pre-rebase sibling of e9ee76c07; in-house cites @1650e3d)
