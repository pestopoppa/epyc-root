# Dive — fp4kv — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2611.30027v1", retrieved: "2026-11-24", sha256: "4a2b6be209ee"}

Source: `fp4kv/page.txt` (LaTeXML HTML render of arXiv 2611.30027v1, 106,087 bytes, read in full including
appendix A and references). Code repo named in the paper (github.com/thomaszhang2661/kv4-hopper) was NOT fetched.

## 1. Stage-1 fields

- **Title**: Fast 4-bit KV-Cache Decoding on Hopper GPUs: Why vLLM's 4-bit Paths Are Slow and How to Fix Them
- **Authors**: Jian Zhang (Northeastern University). Single author.
- **Version**: arXiv 2611.30027v1, [cs.LG], 23 Nov 2026. Preprint, not peer reviewed.
- **Categories**: kv_cache, quantization, hardware_optimization, inference_serving, benchmark_methodology
- **Novelty**: medium. The author says plainly that no single part is new. The warp-specialised pipeline follows
  FlashAttention-3 and LiquidGEMM, the operand swap is a standard GEMM trick, and the write-time layout follows
  Marlin and BitDecoding. What is new is the combination: E2M1 and INT4 KV decode on Hopper, which has no FP4
  hardware, running faster than the best FP8 decode kernels. Two further contributions are new: the diagnosis by
  instruction count per byte, and a weights-only proof that Qwen2's layer-0 K mean is its key bias.
- **Relevance**: high. A native q4_0 KV `gv_fattn` (GQA-verify flash attention) kernel for MI210 is being designed
  now. The lane records that q4_0 KV "would need a native q4_0 GQA-verify kernel to compete"
  (`handoffs/active/speculative-decoding.md:L379 @ f74b175`). This paper is the closest published design for software
  4-bit KV decode on a matrix-unit GPU that has no 4-bit hardware. Its accuracy recipe also bears on llama.cpp's
  automatic Hadamard rotation of quantized K on Qwen3.x models.
- **credibility_score**: 2. Arithmetic: peer-reviewed 0 (arXiv preprint), +1 (published 2026-11, within 12 months),
  major lab or known contributor 0 (single university author), commercial bias 0, independent corroboration +1
  (the Qwen2-family FP8-KV collapse is independently reported by Li et al. 2510.18672 and by Easy-Kuant, and its
  key-bias mechanism by Liu et al. 2504.04823 = intake-863). Total 0+1+0+0+1 = 2. The kernel speed claims have no
  independent corroboration.
- **Verdict**: **adopt_patterns**. Four patterns carry over to the q4_0 `gv_fattn` design: register-direct decode,
  the operand swap (on gfx90a it keeps P in registers), staging codes rather than decoded values, and the
  instruction-budget-per-byte check. The accuracy recipe gives two cheap tests: rotation on vs off, and the K mean.
  The kernel itself (TMA, wgmma, head dim 128, G ≤ 8) cannot be ported as written.

## 2. Key claims (operator steering numbers checked)

| # | Claim | Verdict | Evidence / anchor |
|---|---|---|---|
| 0 | vLLM's NVFP4 KV path (FlashInfer decode) on H200 reaches 10-20% of bandwidth and is up to 1.7x slower than FP8 | **CONFIRMED** (kernel level). Narrowing: inside vLLM, per step, it is 1.4-2.3x slower than FP8 at batch ≥ 8. At batch 32 / 16K: FP8 0.395 ms, NVFP4 0.669 ms, XQA FP8 0.255 ms | Abstract: "On H200, vLLM’s NVFP4 KV path (FlashInfer’s decode) reaches 10–20% of memory bandwidth and is up to 1.7"; §1: "FlashInfer [ 59 ] takes 0.495 ms in BF16, 0.395 ms in FP8 (0.255 ms with its XQA kernel…" |
| 1 | The new kernel reaches 67-75% of peak at batch 32-128 and is 1.12-1.49x faster than the faster of XQA and FA4 FP8 at all 11 shapes | **CONFIRMED**, with a narrowing. 67% is at B=32, 75% at B=128, both at 16K. At B=1 it reaches only 18% (16K) to 38% (64K). The FA4 FP8 baseline comes from two unmerged PRs and was timed as CUDA-graph replays. The split count is the best of 1-64 for the new kernel, while baselines use their own heuristics (the authors say this "slightly favor[s]" their kernel) | Abstract "On H200 it reaches 67–75% of peak bandwidth at batch 32–128 and at all 11 shapes is 1.12–1.49"; §6 "NVFP4 reaches 67% ( B = 32 …) to 75% ( B = 128 …, both at 16K)"; §9 "At B = 1 … about 38% of bandwidth at 64K context (18% at 16K)" |
| 2 | Inside vLLM: 1.12-1.64x per step on Llama-3.1-8B vs FlashInfer FP8 at batch ≥ 8, and 1.63x token capacity | **CONFIRMED**. Level at batch 1 (1.01-1.05x per step, 0.96-1.03x end to end). Against FA4 native FP8 the gain is only 1.04-1.24x. Capacity is 2,867,200 vs 1,761,600 tokens | §7 "our plugin decodes 1.12–1.64 × … faster than FlashInfer FP8 (XQA decode) at batch 8 and above, and is level with it at batch 1"; "The KV cache holds 2,867,200 tokens against 1,761,600 for FP8 … (1.63"; abstract "1.04–1.24 × \times over FlashAttention-4’s FP8" |
| 3 | Prefill is 7% slower | **CONFIRMED**: 9.29 vs 8.66 s for 8 prompts of 32,000 tokens. TTFT is 1.5-6% slower end to end. Prefill-heavy serving streams are worse than FP8 | §7 Prefill: "Prefill alone is still 7% slower than FlashInfer FP8 (8 prompts of 32,000 tokens: 9.29 vs 8.66 s, same job)" |
| 4 | In the Qwen2 family, layer 0's key mean is the k-proj bias seen through RoPE | **CONFIRMED, reattributed**. The quantification is the paper's own: averaging RoPE(b) over positions accounts for 99.7-100% of layer-0 mean energy, computed from the weights alone. The mechanism comes from prior work (Liu et al. §3.3 / App. C.2, vLLM PR #63081), and the paper says so | §8 "averaging RoPE ⁡ ( b ) \mathrm{RoPE}(b) over positions removes 99.7–100% of layer 0’s mean energy"; "The mechanism is not new either: Liu et al. [ 30 ] (Section 3.3, Appendix C.2) traced the K outliers" |
| 5 | Keeping layer 0 in BF16 restores FP8 KV, and together with K mean removal it restores 4-bit KV | **CONFIRMED, narrowed**. Layer-0 BF16 alone fixes FP8 but NOT 4-bit: on Qwen2.5-7B-I, NVFP4 with 4 sinks and layer 0 in BF16 has KL 0.250, 17x the full recipe. K mean removal is the step that rescues 4-bit. R1-Distill-Qwen-14B does not collapse at all | §8 "Keeping only layer 0 in BF16 restores FP8 to 73.0% and the NVFP4 recipe to 73.0%"; "On its own it is not enough for 4-bit: on Qwen2.5-7B-Instruct, NVFP4 with four sinks and only layer 0 in BF16 has a KL of 0.250"; "R1-Distill-Qwen-14B is unaffected (70.0% BF16, 73.0% FP8)" |

Stage-1 framing correction: "relevance low because Hopper-only" is OVERTURNED. Every mechanism below has a gfx90a
reading, and one of them (operand swap → P stays in registers) is worth more on gfx90a than on Hopper, because MFMA
reads both operands from VGPRs.

## 3. Reported results (as stated; H200 SXM unless noted)

- Kernel, NVFP4 vs FlashInfer FA2 FP8: 1.4-2.3x. Vs XQA FP8: 1.2-2.1x. Vs the best FP8 kernel at each of the 11
  shapes (XQA or FA4 native FP8, CUDA graphs): 1.12-1.49x (Table 5). INT4 runs at 74-83% of peak. On H100 at
  batch ≥ 8, NVFP4 runs at 79-86% and INT4 at 82-90%.
- Removal ablation (Table 6): dropping E2M1 reconstruction gives 0.87x the time at B ≥ 8, so decode is about 13% of
  kernel time. Dropping both matmuls gives 0.92-0.94x. Interleaved-decode ILP is 8-18% slower. MXFP4 reads 6% fewer
  bytes than NVFP4 but takes the same time, so FP4 on H200 is limited on the compute side.
- Issue budget: H200 has about 7 thread instructions per byte (3.9 per value at 72 B per 128-value row). NVBit counts
  (Table 2): FlashInfer NVFP4 8.3 instructions per value at 19% bandwidth; vLLM UltraQuant 22.5 at 8%; BitDecoding
  INT4 3.6 without spin-waits at 25%, with 38% of instructions spin-waiting. XQA itself executes 3.9 per value and
  the paper's kernel 3.6.
- vLLM per step (Table 7, Llama-3.1-8B): 1.01-1.05x at B=1 and 1.12-1.64x at B ≥ 8. Qwen3-32B: 1.05-1.18x at B ≥ 8.
  Qwen3-30B-A3B: 0.94-0.95x at B=1 and 1.11-1.32x at B ≥ 8.
- Highest sustainable request rate (Table 9): 1.23-1.32x (8B), 1.45-1.80x (Qwen3-32B), 1.67-2.20x (Qwen2.5-72B FP8 weights).
- Accuracy (Table 13): no significant difference from BF16 KV on 7 model/test rows. The intervals span about ±2.5-3
  points, so the tests exclude only losses larger than about 3.5 points.
- Recipe ladder (Table 11, offline KL): on Qwen3-8B-Base, rotation without mean removal raises KL from 0.029 to 0.281.
  Mean removal brings it down to 0.0125.
- AMD datapoint (restated from the UltraQuant paper, not measured here): on MI355X, 4-bit KV decode takes 2.45x FP8's
  time with software dequant and 1.18x with native FP4.

## 4. Performance-principles table (MI210 gfx90a / Zen 5)

| Principle (paper) | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| **Q1. Write-time layout so decoded values feed the matrix unit from registers.** Each K row and each 256-token V block is permuted at write time, so every thread's fragment sits in contiguous 16-byte chunks: one 128-bit load, no bank conflicts, no shuffles. Scales are permuted the same way. | **PARTIAL→YES, cheaper than on Hopper.** The MFMA `v_mfma_f32_16x16x16f16` layout is lane l, kq=l/16; A[i][k] has i=l%16, k=4kq+0..3; B[k][j] has j=l%16, k=4kq+0..3 (`fattn-gqa-verify.cu:L16-L20 @ 98ff8a4`). **K side, stock q4_0 already fits.** `block_q4_0` holds byte j = value j (low nibble) and j+16 (high nibble) (`ggml-quants.c:L469-L474`, `ggml-common.h:L194-L198 @ 98ff8a4`). So lane kq needs exactly bytes 4kq..4kq+3 of each 32-value block for both 16-wide k-chunks: one dword per lane per block, no permutation. Caveat: the 18-byte block stride makes that dword 2-byte aligned only. **V side does not fit.** The PV operand needs 4 consecutive *tokens* for one d (sVt[d][key] today, `fattn-gqa-verify.cu:L201`), while q4_0 V is blocked along d, so it needs a token-contiguous (V^T) packing. The paper needed a *write-time* layout because TMA copies bytes verbatim into SMEM. gv's PIPE path already does global → register → LDS (`store_raw`, `fattn-gqa-verify.cu:L429`), so on gfx90a the permutation can happen **at LDS-store time** and the ggml cache format stays stock q4_0. A write-time V^T layout is the fallback if the LDS-store permutation costs too many instructions. | **YES, mostly already true.** CPU decode works in vector registers with no shared-memory stage. The transferable part is SoA scales and 64-byte-aligned code runs for AVX-512 loads. Gain is small because CPU decode is bandwidth-bound with ample issue slack (Q4 row). |
| **Q2. Producer/consumer overlap.** A TMA producer warp streams 256-token double-buffered stages (mbarriers). Two compute warpgroups each own half of every stage and their own online-softmax state, merged at the end. | **PARTIAL.** gfx90a has no TMA and no mbarrier (uncited). The in-house equivalent already exists: register-prefetch software pipelining (`GGML_CUDA_FA_GQA_VERIFY_PIPE`, `GGML_HIP_GV_PREFETCH_LATE`, `fattn-gqa-verify.cu:L65-L85`). The lane's binding limit is residency, not overlap: LDS 43.5-44.5 KB per WG gives 1 WG/CU, and the LDS cut alone gave 1.21-1.34x (`autokernel-loop.md:L11689-L11692 @ f74b175`). The transferable idea is the **key partition**: waves own key ranges with their own softmax state, merged at the end, instead of owning row tiles that each re-read K from LDS. Staging *codes* (q4_0 K+V for a 32-key × 256-d chunk ≈ 2 × 4.6 KB) instead of f16 (16.9 + 20.5 KB) removes the LDS limit, leaving VGPRs as the limit. Wave specialisation through LDS plus `s_barrier` is possible but costly. More resident waves is the gfx90a way to hide latency (uncited). | **NO (not needed).** Hardware prefetch and out-of-order execution already overlap load with decode. No action. |
| **Q3. Operand swap** S^T = K·q^T, O^T = V^T·P^T (`wgmma.m64n8k16`): decoded K / V^T is the register A operand, and query heads take N=8 (4 or 8 real), so softmax does no padding work. Only P goes through SMEM (2 KB per warpgroup). | **PARTIAL, with a different payoff.** The MFMA minimum tile is 16 in both M and N, so swapping does not cut padding. Useful rows/16 for R = gqa·n_q: **27B gqa 6** (24 Q / 4 KV heads, config-sourced): n_q 1 → 6/16, 2 → 12/16, 4 → 24/32, 7 → 42/48, 8 → 48/48, 16 → 96/96. **35B-A3B gqa 8** (16/2): 1 → 8/16, 2/4/8/16 exact, 7 → 56/64. **Q38FN gqa 12** (24/2): 1 → 12/16, 2 → 24/32, 4/8 exact. The real gfx90a gain: with the swap, the S^T accumulator layout D[i=key 4kq+v][j=row l%16] **equals** the B-operand layout of the next MFMA (B[k=key 4kq+t][j=row]). So P^T feeds PV from registers with no LDS round trip, which removes `sP` (`fattn-gqa-verify.cu:L175`, 5 KB at 4 waves) and one barrier per chunk. Softmax row reductions also become in-lane plus 2 cross-lane steps. With R > 16 (27B n_q 8 → R 48), one wave can run all N-tiles against one decoded K fragment, which decodes once and runs MFMA 3x. Cost: O^T accumulators of 16 d-tiles × N-tiles × 4 VGPRs; at R=48 that is 192 per lane, so AccVGPRs are needed (uncited: gfx90a has a separate 256-entry AGPR file). | **NO.** No matrix unit is in the CPU decode path. |
| **Q4. Issue budget per byte.** Instructions per byte at full bandwidth = issue rate ÷ bandwidth (FOSCAR Eq. 2). Implied utilisation = instructions per byte × bandwidth fraction ÷ budget. NVBit counts executed instructions. | **YES, as a roofline tool.** Rough MI210 budget (uncited clock): 104 CUs (lane) × 4 SIMDs × 16 lanes/cycle × ~1.7 GHz ≈ 11.3 T VALU thread-instructions/s ÷ 1.498 TB/s (measured) ≈ **7.6 per byte**, about **4.3 per q4_0 value** (18 B per 32) and **8.0 per q8_0 value** (34 B per 32). That is close to the paper's H200 figures (7 per byte, 3.9 per value), so the diagnosis transfers numerically. On gfx90a, rocprofv3 hardware counters (SQ_INSTS_VALU/SALU/LDS/VMEM_RD, SQ_WAIT_INST_ANY) replace NVBit. The paper had no counters. gv today runs at 13-34% of the 1 TB/s floor (G3-KTRACE-LONGCTX), so it is probably latency-bound rather than issue-bound. The count tells which, and for q4_0 the per-value budget is half of q8_0's. | **PARTIAL.** Same formula, ample margin. Rough figures (uncited): 24 cores × ~2 vector ops/cycle × ~4 GHz ≈ 190 G vector-instr/s ÷ 112.9 GB/s ≈ 1.7 per byte, about 30 vector instructions per 18-byte q4_0 block, against a decode of a few instructions per 64 values. The CPU is not issue-bound on KV decode. |
| **Cheap reconstruction**: INT4 FP16 magic numbers (`(w & 0x000F000F) \| 0x64006400` gives 1024+c, 0.625 instr per value), with the 16x factor folded into q. Scales folded around the matmul (affine folding). | **YES.** q4_0 is symmetric INT4 with one f16 scale per 32 values (offset 8). The magic-number trick is plain integer and f16 ALU work, so it applies directly with `v_and_or_b32` / `v_pk_add_f16` (uncited ISA names). The scale can be applied after the MFMA per key (K side: scale per key-block varies along k, so fold per 32-value block, which needs per-block partial sums or pre-scaling of the decoded half2). | **YES.** Already standard in iqk / ggml-cpu q4 paths. Nothing new. |
| **Numerics**: subtract the 1024 offset *before* the multiply (Hopper TC accumulation truncates). Scale P by 2^10 because many small P values next to a strong sink fell into FP16 subnormals, which random test data does not show. | **YES, and it applies to production q8_0 gv now.** gv stores P as `_Float16` in [0,1] (`fattn-gqa-verify.cu:L175`). Whether gfx90a f16 MFMA flushes denormals is uncited. The test fixture should include a sink with real KV. | n/a (CPU accumulates in f32). |
| **Split rule** min(16, ⌊2·nSM/(B·H_kv)⌋) | **Corroborating evidence** for the lane's split-default candidate (S26 fills one dispatch wave; gv auto = min(⌈2·nsm/n_head_kv⌉, n_kv/256) at `fattn-gqa-verify.cu:L770-L776`). It is not a new mechanism. | n/a |
| **Paged reads at contiguous speed** (0.99-1.035x, 64-token pages) | Supports the FAROWS-INPLACE row-list read in gv (`gv_kv_row`, ROWS template). There, too, a gather costs nothing if per-lane loads stay ≥ 16 B. | n/a |

## 5. In-house state (C21 `98ff8a4`)

- **GQA-verify kernel**: `gv_fattn_kernel<KV_Q8, PIPE, LATE, ROWS>` at `ggml/src/ggml-cuda/fattn-gqa-verify.cu:L225 @ 98ff8a4`.
  It handles head dim 256 only and accepts K/V types **f16 or q8_0 only** (reject "K/V type not equal f16/q8_0",
  `:L680`). It also rejects attention sinks (`:L682`). Q is the A operand (rows R = gqa·n_q packed into 16-row tiles,
  one tile per wave). K is dequantized into LDS as f16 [key][d] and V transposed into LDS [d][key]. P round-trips
  through LDS (`:L145`, `:L175`, `:L201`). **No q4_0 path exists.** q4_0 KV runs the VEC kernel at n_q=1
  (`vec_dot_fattn_vec_KQ_q4_0`, `fattn-common.cuh:L167`). At n_q > 1 it runs whole-cache dequant plus f16 MMA, which
  is 2.1x (8k) to 3.6x (16k) slower per round than q8_0 at n-max 7 (`speculative-decoding.md:L395 @ f74b175`).
- **Row `ak-gvfattn-q4kv-gpu-20261124` is ABSENT from the lane at f74b175** (grep for gvfattn / q4kv in
  handoffs/active finds only AK-GVFATTN-LONGCTX and its two result lines).
- **AK-GVFATTN-LONGCTX** (`autokernel-loop.md:L11689-L11692 @ f74b175`): the split sweep's best arm S26 gave 1.17x
  at kv32768 nb8; the LDS cut alone (24,832 B, 2 WG/CU) gave 1.21x; both are below the 1.5x bar. The supported lever
  is the split default at kv8192 (1.56-1.62x q8_0). This paper bears on it directly. Staging codes instead of f16
  plus keeping P in registers is a deeper LDS cut than the measured one (about 11 KB vs 24.8 KB).
- Possible lane inconsistency to check: AK-GVFATTN-LONGCTX says "R = gqa*n_q <= 32 -> 2 tiles" for the 27B census.
  With Qwen3.8-27B's config (24 Q heads / 4 KV heads, gqa 6), n_q=7 gives R=42, which is 3 tiles. This needs checking
  against the GGUF metadata before anyone relies on the 4-waves/WG figure.
- **Accuracy machinery**:
  - llama.cpp auto-enables Walsh-Hadamard rotation of K/V whenever the KV type is quantized and the head dim is a
    multiple of 64, with opt-out `LLAMA_ATTN_ROT_DISABLE` (`src/llama-kv-cache.cpp:L317-L340 @ 98ff8a4`).
  - Every Qwen3.5-family q4_0/q8_0 KV run is therefore in the paper's "rotation without mean removal" configuration.
    On Qwen3-8B-Base that configuration raised NVFP4 KL roughly 10x (0.029 to 0.281).
  - There is **no per-layer KV dtype**: one `type_k` / `type_v` for all layers (`llama-kv-cache.cpp:L235`). There is
    no K mean removal and no BF16 sink path.
- **Qwen2 k-bias finding vs our models**: the local HF configs have `attention_bias: False` for Qwen3.8-27B
  (`qwen3_5_text`, config sha256 dab9abc478e1), Qwen3.6-35B-A3B (`qwen3_5_moe_text`, 93a4693fa9d8),
  Qwen3.8-Flash-Next and Qwen3-4B. **The bias mechanism does not apply** (config-sourced).
  - The paper's other finding does apply: Qwen3-8B-Base K has a large per-channel mean, about half of K's energy,
    from a source other than bias. The paper does not trace its origin.
  - Qwen3.5-family attention uses `partial_rotary_factor 0.25`, so 192 of 256 dims are unrotated. A channel mean
    there is constant over positions, which favours a static mean (my inference).
  - "Layer 0" maps to the **first full-attention layer (index 3)**. Layers 0-2 are `linear_attention` (GDN) and have
    no KV cache.
  - The paper does not cover head dim 256 ("Not covered: … head dimension 256 (Qwen3.x …)").
- **Production**: 27B serves q8_0 KV on the native gv path (G3-KTRACE-REGRADE, NATIVE_AT_VERIFY). The 1M-context
  shape fits only with q4_0 KV, whose quality is unmeasured (`long-context-program.md:L56 @ f74b175`).

## 6. Derived-actionables ledger

| # | Draft task line | Owner (lane) | Kind | Stop / decision rule (question) |
|---|---|---|---|---|
| D1 | Build a default-off q4_0 K/V variant of `gv_fattn` on a fresh C21 experimental branch. It stages raw q4_0 codes in LDS (not f16), decodes into MFMA fragments in registers, and uses swapped operands (S^T = K·Q^T, O^T = V^T·P^T) so P never touches LDS. | `autokernel-loop.md` (AK-GVFATTN section; the row `ak-gvfattn-q4kv-gpu-20261124` does not exist at f74b175; not frozen) | code, then GPU row | Question: does a native q4_0 gv beat q8_0 gv per call at long context? KEEP if q4_0 us/call ≥ 1.3x faster than q8_0 gv A0 at kv32768 nb8, with all test-backend-ops GQA-verify cases passing. FUTILITY if < 1.0x vs q8_0 across kv32768 nb1-8 after one occupancy iteration. Also report it against the G3-KTRACE-LONGCTX q4_0 VEC/MMA baselines. |
| D2 | Write the q4_0 → MFMA 16x16x16 fragment map into the D1 design note and lock it with a model-free test. K: lane kq reads bytes 4kq..4kq+3 of each `block_q4_0`. V: needs a token-contiguous gather. Count VALU instructions per decoded value for the V gather. | `autokernel-loop.md` (step 0 of D1) | code/doc-only | Decision: if the stock-layout V gather plus LDS-store permutation costs more than about 4.3 VALU instructions per value (MI210 q4_0 budget), adopt a write-time V^T layout (new KV layout behind set_rows). Otherwise keep stock q4_0 for CPU, state save and test compatibility. |
| D3 | Run a rocprofv3 counter census (SQ_INSTS_VALU/SALU/LDS/VMEM_RD, SQ_WAIT_INST_ANY, SQ_BUSY_CYCLES) of `gv_fattn` q8_0 at kv32768 nb1/8. Compute instructions per KV byte and implied issue utilisation = instr/byte × bandwidth fraction ÷ budget, with the budget derived from the measured clock. | `rocm-kernel-authoring.md` (method) with consumer `autokernel-loop.md` | GPU row (short) | Question: is gv issue-bound or latency/occupancy-bound? If implied VALU utilisation ≥ 50%, a lean decode is D1's first lever. If ≤ 25%, residency stays first. One census, stop on answer. |
| D4 | Add a sink-heavy, real-KV-distribution case (one key with 10^3x weight over ≥ 16k keys) to the gv_fattn tests, and evaluate scaling P by 2^10 before the f16 store (fold 2^-10 into l). | `rocm-kernel-authoring.md` | code + model-free test (GPU test-backend-ops) | Adopt the scaling (behind a knob, then a KLD gate) if gv's max abs error vs an f32 reference exceeds the f16-KV VEC path's by > 2x on the sink case. Otherwise record it as a no-op for production q8_0. |
| D5 | Measure q4_0 KV KLD on Qwen3.8-27B: rotation default vs `LLAMA_ATTN_ROT_DISABLE=1`, against q8_0 and f16 KV, using llama-perplexity `--kl-divergence` with f16-KV reference logits. Add a CPU arm for 35B-A3B. | `quantization-and-low-bit.md` (active; `kv-cache-quantization.md` is completed). Consumer `long-context-program.md:L56` | GPU + CPU rows (no code) | Questions: does auto-rotation hurt q4_0 on Qwen3.5-family? Is q4_0 KV quality good enough for D1 and the 1M route? If rot-off KLD < 0.9x rot-on, file D6's mean-removal implementation. If q4_0 rot-on KLD ≤ 2x q8_0's, q4_0 may proceed to a served gate. |
| D6 | Dump post-RoPE K for the 16 full-attention layers of 27B (and the 10 of 35B-A3B) on a short prompt. Report the per-channel mean energy fraction, split into rotated and unrotated dims (partial_rotary 0.25). Simulate q4_0 with and without static mean removal and rotation. | `quantization-and-low-bit.md` | CPU (short forward plus offline Python) | Decision: if mean energy > 30% of K energy in any full-attention layer, or simulated mean removal cuts KL ≥ 20%, implement static per-layer K mean subtraction at the KV write behind a knob. No read-time correction is needed because q·μ cancels in softmax, but sinks are a precondition per the paper. Otherwise decline mean removal for this family. |
| D7 | Add a per-layer KV-type override so the first full-attention layer can stay f16 while the rest use q4_0. | `quantization-and-low-bit.md` | code (conditional) | Gate: only if D6 shows the first full-attention layer's error dominates (≥ 2x the median layer's simulated KL). The Qwen2 k-bias reason is absent (attention_bias False). |
| D8 | Time 35B-A3B CPU decode at 32k context with q4_0 vs q8_0 KV (rotation on), reporting tok/s and the attention share. | `cpu-decode-roofline-program.md` | CPU row | Keep q4_0 KV as a CPU-serving candidate if tok/s improves ≥ 5% at 32k and D5's CPU-arm KLD passes. Stop-on-futility if attention is < 10% of the step at 32k. |
| — | Split-count rule min(16, ⌊2·nSM/(B·H_kv)⌋) | evidence only, no new task | — | Corroborates the existing AK-GVFATTN split-default candidate (S26 / one dispatch wave). Attach as a citation to that candidate. |
| — | Port the Qwen2 k-bias handling (vLLM #59674 per-position subtraction, rtp-llm #1583 fixed center) | DECLINE | — | Every served Qwen3.5-family config has `attention_bias: False`, so there is no bias for it to act on (config-sourced). Revisit only if a biased-K model enters the lineup. |

## 7. Dive-surfaced sources (unbounded grep of `research/intake_index.yaml` @ lane)

| Source | In index? | Settles / bears on | Recommendation |
|---|---|---|---|
| github.com/thomaszhang2661/kv4-hopper (paper code) | 0 hits | The exact write-time permutation, decode instruction sequences and split merge. It would speed up D1/D2 | ingest-and-dive (code read only) |
| FOSCAR, arXiv 2611.09722 | 0 | The origin of the issue-budget model (Eq. 2) and affine folding for 2/4-bit KV. q4_0 is INT4, so folding applies to D1. Bears on D1, D3 | ingest-and-dive |
| UltraQuant, arXiv 2606.20474 | 0 | The only **AMD (MI355X)** 4-bit KV decode measurement in the chain (2.45x FP8 time with software dequant). It settles whether ROCm software 4-bit KV has been made fast. Bears on D1's prior | ingest-and-dive |
| FlagRot, arXiv 2611.03992 | 0 | Whole-head Hadamard raises NVFP4 KL on Qwen3-8B (+215%), and per-sub-vector selective rotation avoids it. Bears directly on llama.cpp's auto `attn_rot` for D5 | ingest-and-dive |
| Easy-Kuant (OpenReview byJQ7BNyPd) | 0 | A per-layer statistic that selects the BF16 layers. Bears on D7 for hybrids | ingest (Stage-1); dive only if D6 triggers D7 |
| BitDecoding-FP4, arXiv 2611.09825 | 0 | Swaps both attention operands, plus a key-smoothing recipe. Its transferable content is restated here. The rest is block-scaled FP4 tensor-core scale handling | ingest (Stage-1 only) |
| LiquidGEMM, arXiv 2509.01229 | 0 | 1 load + 2 compute warpgroups decoding in registers for W4A8 GEMM. Possible pattern for MI210 q4 weight GEMM | ingest (Stage-1 only) |
| Li et al., arXiv 2510.18672 (reasoning-serving study) | 0 | Independent report of the R1-Distill-Qwen FP8-KV collapse | decline: it gives no mechanism, and the collapse needs a key bias our models lack; recorded only as a corroboration pointer for claim 5 |
| FServe (EMNLP 2026 Findings) / FireQ 2505.20839 | 0 | INT4 KV → FP8 in registers for FA3. gfx90a has no FP8 MMA, so the transferable part (INT4 → f16 in registers) is already in this paper | decline (FP8-operand-specific) |
| vLLM PR #63081, #59674; rtp-llm PR #1583 | 0 | Qwen2 key-bias handling | decline (no k_proj bias in served configs) |
| BitDecoding 2503.18773, SAW-INT4 2604.19157 | cited inside other entries only (intake-1324, intake-1286 notes), no own entry | INT4 KV on Hopper with LDS dequant; per-token INT4 needs rotation | ingest SAW-INT4 (Stage-1) for D5. Decline BitDecoding: its LDS-dequant design is what gv already does |

Already in the index: Liu et al. 2504.04823 = **intake-863**, Marlin 2408.11743 = **intake-1546**.

## 8. Contradiction / adversarial pass

- **Self-favouring timing.** In the kernel tables the new kernel uses the best of 1-64 splits per shape, while the
  baselines use their own heuristics; the authors state this. The FA4 FP8 baseline comes from two unmerged PRs.
  Against FA4 inside vLLM the gain shrinks to 1.04-1.24x per step.
- **No batch-1 win.** At B=1 the kernel reaches only 18-38% of bandwidth. The sink merge, cache write and q rotation
  (848 vs 847 µs) erase the decode kernel's lead. Our spec-verify rows are batch-1-like per sequence but have
  n_q 2-16 rows, which the paper never measures: its query rows are always G heads of one token.
- **Out of scope for our models.** The paper covers head dim 128 and G ≤ 8 only, with an INT4 kernel that is dense
  and G=4 only. Our 27B, 35B-A3B and Q38FN all use head dim 256, and Q38FN's gqa of 12 exceeds 8. Register pressure
  for O doubles at d=256, so on gfx90a the VGPR budget, not decode, is the likely binding limit for D1 (my
  inference).
- **FP4 on H200 is compute-side limited.** MXFP4 reads 6% fewer bytes in the same time, and removing spin and address
  instructions gained at most 2%. The authors could not name the limit without stall counters. The issue-budget
  model alone does not explain their own kernel.
- **AMD counter-evidence (restated, not corroboration).** UltraQuant on MI355X found 4-bit KV "buys capacity, not
  kernel speed" with software dequant. That is a direct caution for D1's prior.
- **Statistics.** The accuracy intervals cannot exclude losses under about 3.5 points. Two serving runs did not
  reproduce, and both are retained.
- **Author disclosure.** Claude / Claude Code wrote the code, ran the experiments and drafted the text, with the
  author checking the results. This is noted, not used as a discount.
- **No reviewer pushback** exists (v1, one day old).

## 9. read_depth

FULL. All of page.txt was read (abstract, sections 1-9, Tables 1-14, Appendix A, references). The linked code repo
and the cited papers were not read. `lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9`.

## 10. Artifact audit

artifact audit: clean (29 quotes checked as verbatim substrings of `fp4kv/page.txt`, count = 1 each; no writes
outside the two allowed paths; no compute; in-house code read with `git show 98ff8a42a:`).
