# MI300 (AITER) kernel → MI210 (gfx90a) port inventory: complete family table + new seeds

Date 2026-11-05. Static work only: disassembly + `llvm-mc -mcpu=gfx90a` assembly trials on CPU (taskset 120-127). No
GPU runs. Source: AITER tree `/mnt/raid0/llm/tmp/rock-aiter-gfx90a-20261105/rock-aiter-prebuild-20261105/src-gfx90a`
(`hsa/` paths relative to it). Target: C6 tree `/mnt/raid0/llm/worktrees/llama-c6-iqkq8pf-fold-20261105` (`f3a6a4baa`).
Builds on `mi300-to-mi210-portability-20261105.md` (§ refs below = that report) and `aiter-gfx90a-ops-20261105.md`.

Scratch (disposable): `/mnt/raid0/llm/tmp/mi300-asm-inventory-20261105/` — `retarget-families.txt` (per-family
llvm-mc results, reusing `aiter-port-scratch-20261105/retarget_check.py`), `scripts/i8split_check.py` +
`i8split-results.txt` (new int8 K-split trial).

Tags: **[R]** read/ran it; **[M]** measured on MI210 (prior rows, cited); **[I]** inference/estimate, not timed.

## 0. New findings from this pass

1. **The K-doubled int8 MFMA blocker is mechanically removable — 4 more asm families now assemble for gfx90a. [R]**
   `v_mfma_i32_16x16x32_i8 D, A[0:1], B[0:1], C` → `v_mfma_i32_16x16x16i8 D, A0, B0, C` + `v_mfma_i32_16x16x16i8 D,
   A1, B1, D` (and `32x32x16_i8` → 2× `32x32x8i8`). This is **exact**: each lane's 8 k-bytes are split into the same
   lo/hi dword for A and B, so the two MFMAs sum over a partition of the identical k set (int32 accumulation is
   associative). Register allocation is unchanged. Results after the split (`i8split-results.txt`):

   | gfx942 kernel | lines | int8 MFMAs split | still failing on gfx90a |
   |---|---|---|---|
   | `gemm_a8w8_m128_noSplitK.co` (a8w8 GEMM) | 1396 | 64 | **0** |
   | `pa_a16w8_b16_2tg_g8_i8.co` (paged attn, int8 KV) | 2339 | 192 | **0** |
   | `fmoe/silu/fmoe_fp16_pertokenInt8_g1u1_silu_1tg_32x128.co` (fused MoE int8, fp16 out) | 3140 | 384 | **0** |
   | `fmoe_2stages/fmoe_stage1_bf16_pertokenInt8_g1u1_112x128_pf2.co` (MoE stage-1 int8) | 7157 | 448 | **0** |
   | `i8gemm/I8gemm_bf16_perTokenI8_BpreShuffle_128x128.co` | 1988 | 384 | 32 (`global_atomic_pk_add_bf16`, split-K) |
   | `gemm_a8w8_m128_splitK.co` | 1435 | 64 | 32 (same atomic) |

   Cost: on gfx90a each int8 k-step takes 2× the MFMA cycles (int8 rate = bf16 rate, §0.4), so MI300's schedule
   becomes more MFMA-bound — fine for bandwidth-bound skinny shapes, a ~2× compute ceiling drop for large-M prefill.
   Hazard audit (dependent back-to-back MFMA on the same accumulator, SrcC) still required, as in H5.
2. **fp16-output variants avoid the bf16 atomic.** `fmoe_f16.co` (3736 lines) and
   `fmoe/silu/fmoe_fp16_noquantFp16_g1u0_atm_inlv_silu_1tg_32x512.co` (3833) assemble with **0** failures: gfx90a has
   `global_atomic_pk_add_f16`. Only the bf16-output twins need AK-ASM-H7. [R]
3. **More 0-fail families**: `topksoftmax_*` (984 lines), `mhc_seam_*` (777 / 266), `allreduce_rmsnorm_N8192`,
   `all_reduce`, `pa/*_mtp_msk*` bf16 (10762 lines — the multi-token "MTP" PA used for spec-verify), MLA a16w16,
   FA v3 fwd hd128 group and hd192x128. [R]
4. **New minor blockers** (topk_per_row decode/prefill, flatmm): `v_lshl_add_u64` (20–67 sites), `v_mov_b64` (2–5),
   `v_fmamk_f32` (2). `v_mov_b64` → `v_pk_mov_b32 … op_sel:[0,1]` assembles [R]; `v_lshl_add_u64` → `v_lshlrev_b64` +
   `v_add_co_u32`/`v_addc_co_u32` needs a free VCC/SGPR pair per site (needs liveness); `v_fmamk_f32` → `v_fmac_f32`
   with a literal-loaded VGPR. Tooling only.
5. **Hard blockers unchanged**: FP8/BF8 MFMA + `v_cvt_pk_fp8_f32` (all fp8/mxfp4/6 families), gfx950 160/130 KiB LDS,
   `ds_read_b64_tr_b16`, `buffer_load_dwordx4 … lds`, 32x32x16/16x16x32 bf16 MFMA (gfx950 only).
6. **Two Q38FN-specific AITER sources nobody seeded**: AITER ships a **QSA** operator (`aiter/ops/triton/attention/qsa.py`
   + `_triton_kernels/attention/qsa.py`, 464 lines: paged MQA index logits incl. an MFMA variant, group selection,
   sparse paged GQA). C6 builds QSA from generic ops (`src/models/qwen4exp.cpp:675 build_qsa_top_k`, top-k + get_rows +
   masked FA). And Q38FN (`qwen4exp`) carries DSv4-style hyper-connections (`hc_mult`, `hc_*_down/up/inject`,
   `qwen4exp.cpp:25-173`) with **no fused GPU kernel** in C6; AITER has `mhc_seam` asm (0-fail) and `mhc_kernels.cu` /
   `mega_mhc.cu`. [R]
7. **Q8_0 vs AITER scaling is the semantic blocker for every int8 asm GEMM.** AITER int8 kernels use per-token A ×
   per-channel B scales applied once in the epilogue; Q8_0 has a scale per 32 k. Options: (a) requantize Q8_0 → int8
   per-channel at load (quality change, needs the KLD/top-1 gate), (b) patch the asm epilogue into a per-32-k
   `v_cvt_f32_i32` + `v_fma` into an fp32 accumulator (large asm edit: 2 MFMAs per block, 4–16 acc regs/lane converted
   per block — VALU heavy, but VALU is idle on the skinny path), (c) technique-only into C6 MMQ. [I]

## 1. C6 baseline (what each AITER family competes against)

| Stage | C6 kernel (gfx90a, ROCWMMA_FATTN=ON, MMQ_MFMA=ON) | % of roofline | Source |
|---|---|---|---|
| decode GEMV M=1..4 | `mul_mat_vec_q` sdot4; Q8_0 prefetch variant off | Q8_0 ~70% BW, Q4_K 46% | §4 [R-sub] |
| spec-verify M=5..16 | `mul_mat_q` 16x16x16i8, sync load→LDS, stream-K | ~31% BW; ~70% of 67 ms 27B verify step | §2, §4 |
| prefill M>128 | dequant→f16 + rocBLAS (convert ~15%) | ~27% of bf16 peak overall (27B pp2048) | §2 |
| FA prefill / verify | rocWMMA `flash_attn_ext_f16`, f16 acc, q8_0 KV → f16 convert | ~17% of bf16 peak [M: ak-asm-h5b] | §4 |
| FA decode | `fattn-vec` | BW-bound, small share at short ctx; 28.7/158.7 ms at 80k verify | §2 |
| MoE route | `topk-moe.cu` fused softmax+topk | launch/latency-bound | [R] |
| MoE expert GEMM | `mmid.cu` + MMQ/MMVQ id paths | est. 30–50% BW at verify M | [I] |
| GDN/SSM | recurrent `gated_delta_net.cu` (chunked TODO :191), `ssm-conv.cu` | 16.7% of one GPU profile (rank 3) | autokernel-loop.md:5506 |
| norms/rope/quantize | separate kernels | decode non-GEMM tail 27–31% dense, 62% A3B | §2 |
| hyper-connections (Q38FN) | generic mul_mat/norm/add chain per layer ×2 | unmeasured | [R] |
| QSA (Q38FN) | top_k + get_rows + masked FA | unmeasured | [R] |

## 2. Inventory: every `hsa/` family + inference-relevant CK/HIP/Triton op

Tier key: **RT** = llvm-mc retarget (renames/splits; then hazard audit + descriptor + loader as H5);
**BI** = HIP builtins rewrite; **CK** = CK instance build for gfx90a; **TO** = technique-only; **NA** = not applicable.
Gains are end-to-end on Qwen3.8-27B (27B), Qwen3.6-35B-A3B (A3B), Q38FN; all [I] unless cited.

### 2a. `hsa/gfx942` hand-asm families (the portable source set)

| Family | What it does | llama.cpp op / stage | C6 now | gfx90a blockers (trial) | Tier | Expected gain (reason) | Effort | Seed |
|---|---|---|---|---|---|---|---|---|
| `fmha_v3_fwd` (hd128, hd192x128, MI300+MI308, group) | FA fwd, 8-wave ping-pong, softmax in regs | FLASH_ATTN_EXT prefill/verify | rocWMMA ~17% peak | **none** (2 MFMA renames) [M: 3.87x vs C6] | RT | none on prod models directly (all hd256); technique template for hd256 | M | H5 (done), H5-PORT |
| `fmha_v4_fwd` | fp8 / i8fp8 / sparse FA | FA | — | fp8 MFMA | NA (i8 path: TO) | 0 | — | — |
| `fmha_v3_bwd` | FA backward | training | — | `pk_add_bf16` | NA | 0 | — | — |
| `pa` + top-level `pa_a16w16_*`, `pa_a16w8_*` | paged decode attn, GQA-packed Q (8/16 heads share KV read), **MTP variants qlen>1 for spec verify**, int8/fp8 KV | FA decode + verify at long ctx | `fattn-vec` / rocWMMA | bf16/fp16 **none**; int8 KV **none after K-split** [R]; fp8 KV blocked. **head_size==128 only** (`csrc/py_itfs_cu/asm_pa.cu:192`) | RT for hd128; TO for hd256 | 27B/A3B/Q38FN are hd256 → technique (GQA-packed MFMA decode/verify attention with int8 KV in-register dequant): +5–12% verify step at ≥32k ctx (FA 18% of 80k step), ~0 at short ctx | M | partly H2 (prefill FA only) → **new H10** |
| `bf16gemm` (bshuffle split-K, 23 tiles) | bf16 GEMM, B pre-shuffled direct-to-reg, split-K | f16/bf16 MUL_MAT (DFlash drafter, any bf16 tensors) | rocBLAS / MMF off on CDNA2 | `pk_add_bf16` (48) | RT + H7 | small: prod weights are Q8_0; drafter if bf16 [I] | M | H7 |
| `i8gemm` (perTokenI8 BpreShuffle) | int8 GEMM, per-token/channel scale | prefill MUL_MAT (int8 path) | dequant+rocBLAS | int8 MFMA (**split works**) + `pk_add_bf16` | RT(+split,+H7) | see H9 | M-L | H4 (HIP arm) → **new H9** (asm arm) |
| `gemm_a8w8_m128_{noSplitK,splitK}` | int8 GEMM M-tile 128 | prefill / verify | MMQ / rocBLAS | noSplitK **0 after split** [R] | RT(+split) | H9 | M | **H9** |
| `flatmm_uk_gfx9_f16f8_*` | f16 act × fp8 weight flat GEMM | — | — | fp8 MFMA (256), `v_lshl_add_u64` | NA / TO (W8A16 upconvert, §3) | 0 for Q8_0 | — | — |
| `fp8gemm_blockscale` | fp8 block-scaled GEMM | — | — | fp8 | TO: its 128-k block-scale epilogue is the template for Q8_0 per-32 scale in an int8 asm GEMM | enables H9 option (b) | — | H9 |
| `f4gemm` | mxfp4 GEMM | — | — | fp4 (csv only on gfx942) | NA | 0 | — | — |
| `fmoe` 1-stage (`fmoe/{silu,gelu}`, top-level `fmoe_*.co`) | fused MoE: sorted tokens, gate+up fused (g1u1), SiLU, down, atomic out; bf16/fp16 noquant, per-token int8, fp8 | MUL_MAT_ID + GLU (A3B, Q38FN) | `mmid.cu` + MMQ/MMVQ id, separate GLU | fp16-out noquant **0**; int8 fp16-out **0 after split**; bf16-out `pk_add_bf16`; fp8 blocked | RT(+split) | A3B/Q38FN prefill +10–20%, verify +5–10% (MoE GEMM is the bulk of A3B compute; fusion removes act round trips + per-expert launches) — subject to the Q8_0 scale blocker (§0.7) | L | **new H8** |
| `fmoe_2stages` (stage1 int8/fp8, 40+ tiles, pf2/pf3 prefetch) | 2-stage MoE (gate+up, then down) | MUL_MAT_ID prefill | as above | int8 **0 after split**; fp8 blocked | RT(+split) / CK | prefill variant of H8 | L | **H8** |
| `topksoftmax` (`4xNx{4,6,8}`) | MoE router softmax+topk | `topk-moe.cu` | fused HIP | **none** | RT | A3B/Q38FN decode +0.5–2% (one small kernel/layer, latency-bound) | S | **new H11** |
| `topk_per_row_{decode,prefill}` | per-row top-k (DSv4 indexer) | QSA top-k / sampling top-k | generic `argsort`/top_k | `v_lshl_add_u64`, `v_mov_b64`, `v_fmamk` | RT + rewrite pass | Q38FN QSA top-k (part of H12) | S-M | **H12** / **T1** |
| `mla`, `mla_dsl/opus/v4` | DeepSeek MLA decode | — | — | a16w16 **none**; a8w8/fp8 blocked | NA (no MLA model) | 0 | — | — |
| `mhc_seam` | DSv4 hyper-connection seam: fused residual/layer-input + split-K partials of next GEMM + gates | Q38FN `hc_*` chain | generic ops | **none** | TO (Q38FN's low-rank hc differs from DSv4 mHC) | Q38FN decode +2–6% if hc chain is several % of layer time (unmeasured; ~8 small ops/layer) | M | **new H13** |
| `all_reduce`, `allreduce_{rms,layer}norm*` | multi-GPU AR (+ fused norm) | — (single MI210) | — | none | NA now; relevant at second GPU | 0 | — | — |
| `f8_block_scale_mi350_*`, `a16w8gemm`, `f4f6/f6gemm`, `reduce` (gfx950) | MI355 kernels | — | — | 160 KiB LDS, gfx950 MFMA | NA | 0 | — | — |
| `gfx950/fmha_v3_fwd` hd256 | only hd256 asm FA | FA | — | gfx950 ISA + 130 KiB LDS | TO only | covered by CK hd256 (4.96x [M]) | — | H2(b)/H5-PORT |
| `gfx1250/*` | RDNA4/next | — | — | different ISA family | NA | 0 | — | — |

### 2b. CK / HIP / Triton ops relevant to inference

| Op (AITER) | What | llama.cpp op | C6 now | gfx90a status | Tier | Expected gain | Effort | Seed |
|---|---|---|---|---|---|---|---|---|
| CK-tile `fmha_fwd` (`module_mha_fwd`, hd256) | FA fwd | FLASH_ATTN_EXT | rocWMMA | builds [M: 4.96x vs C6 hd256] | CK | 27B/A3B/Q38FN prefill +15–30% at 8k+, verify +10–20% at long ctx | M | H2(b) + H5-PORT (hd256 arm) — covered |
| CK fused-MoE 2-stage + `moe_sorting` | sorted expert GEMM | MUL_MAT_ID | mmid | sorting gfx90a-supported; instances gfx942-tuned | CK | alt arm of H8 | M-L | **H8** arm |
| CK `gemm_a8w8` (Xdl CShuffle V3) | int8 GEMM | prefill MUL_MAT | rocBLAS | uncertain (instances) | CK | alt arm of H4/H9 | M | H4/H9 |
| `rmsnorm*`, `rmsnorm_quant_kernels.cu`, `gated_rmsnorm_quant_kernels.cu` | fused add+RMSNorm(+quant) | RMS_NORM + quantize_q8_1 | separate | gfx90a branches | BI | +1–3% decode | S | H6 — covered |
| `fused_qk_norm_rope_cache_quant.cu`, `fused_qk_norm.cu`, `fused_qk_rmsnorm_group_quant.cu` | q/k RMSNorm + RoPE + KV-cache write (+quant) in one kernel | Qwen3.x q_norm/k_norm + ROPE + SET_ROWS/CPY (q8_0 KV) | 4–6 kernels/attn layer | HIP, gfx942 branches only for fp8 | BI | +1–3% decode (attn layers only: every 4th on hybrids) | S-M | **new H14** |
| `activation_kernels.cu` (silu_and_mul) | GLU | GLU / SWIGLU | fused in C6 already | yes | — | ~0 | — | — |
| `rope/` | RoPE | ROPE | ok | yes | — | ~0 alone (in H14) | — | — |
| `chunk_gated_delta_rule_fwd_h.cu` (MFMA, gfx90a-guarded `:43`) | chunked GDN prefill | GATED_DELTA_NET prefill | recurrent, chunked TODO | yes | BI/TO | prefill ceiling previously gated at ~9% (G10, k28) | M | covered: G10/k28, G16 (model-architecture-readiness) — use AITER kernel as reference arm |
| `gdr_decode_packed_bf16.cu`, `fused_split_gdr_update.cu`, `causal_conv1d_update.cu`, triton `fused_gdn_decode_qkvz.py` | fused GDN decode: split qkvz + conv1d update + state update in one pass, bf16 packed state | GATED_DELTA_NET + SSM_CONV decode | recurrent f32 state, separate conv + split ops | plain HIP, no arch guard | BI | 27B/A3B/Q38FN decode +3–8% (GDN rank-3 16.7% in a profile; fusion removes 2–3 launches + intermediate traffic per GDN layer, ¾ of layers) | M | G9 rejected an *occupancy rewrite* only → **new H15** |
| `topk_softmax_kernels*.cu`, `moe_fused_gate.cu`, `topk_gating` | router | topk-moe | fused | yes | BI | as H11 | S | H11 |
| `moe_align_block_size_kernels.cu` | expert token sort/align | MUL_MAT_ID prep (`mmid.cu`) | ggml ids sort | yes | BI | part of H8 | S | H8 |
| `cache_kernels.cu` (reshape_and_cache, quant) | KV write+quant | SET_ROWS / CPY q8_0 | ok | yes | — | in H14 | — | H14 |
| `sample_kernels.cu` (top-k/top-p/min-p on GPU) | sampling | llama sampler (CPU) | CPU after logits copy | yes | TO | <1% (DFlash greedy verify) | S | none (below bar; one line in §4) |
| triton `qsa.py` (paged MQA logits MFMA, group select, sparse paged GQA) | QSA indexer + sparse attention | Q38FN `build_qsa_top_k` + masked FA | generic top_k/get_rows/FA over masked full KV | triton targets CDNA (gfx90a in CDNA_ARCHS) | TO/BI | Q38FN long-ctx prefill/verify +10–30% on attn layers: sparse attention should read only the selected blocks, C6 masks a dense FA [I] | M-L | **new H12** |
| triton `unified_attention`, `pa_decode`, `chunked_pa_prefill` | paged attn | FA | — | yes | TO | covered by H2/H10 | — | — |
| triton `moe_op_gemm_a8w8*`, `moe_int8_smoothquant` | MoE int8 GEMM | MUL_MAT_ID | mmid | yes | TO | H8 arm | — | H8 |
| triton gemm (a16w16 skinny, `tuned_gemm` skinny HIP `custom_kernels.cu`) | skinny GEMM for M≤16 | verify MUL_MAT | MMQ | yes (`__HIP__MI300_MI250__`) | TO | technique source for H1 | — | H1 |
| `custom_all_reduce*`, `quick_all_reduce`, `mhc_kernels`/`mega_mhc` (DSv4) | multi-GPU / DSv4 | — | — | — | NA / TO(H13) | 0 / H13 | — | — |
| `mla/`, `sparse_attn/`, `dsv4_*`, `mxfp4_moe`, `quant_mxfp*`, `opus_mqa_logits` | DSv4/MLA/MXFP | — | — | fp4/fp8 or n/a | NA (opus_mqa_logits: TO for H12) | 0 | — | — |

## 3. Coverage check against existing seeds

Covered: H1 (skinny verify MMQ), H2 (FA off rocWMMA; CK hd256), H3 (decode prefetch), H4 (int8 prefill, HIP arm),
H5/H5-PORT (FA asm), H6 (norm+quant), H7 (bf16 atomic), T0 (loader + graph capture), G10/G16 (chunked GDN).
Uncovered gains → new seeds below. Not seeded (below bar or n/a): fp8/mxfp families, bwd, MLA, all-reduce (single
GPU), GPU sampling (<1%).

## 4. New seed boxes (ranked by expected end-to-end benefit)

- [ ] **AK-ASM-H8** [non-inference then inference] fused MoE expert GEMM from AITER `fmoe` / `fmoe_2stages` for Qwen3.6-35B-A3B and Q38FN: sorted-token tiles, gate+up fused (g1u1) with SiLU in the epilogue, down GEMM, atomic f16 output. Retarget evidence: fp16-out noquant (`fmoe/silu/fmoe_fp16_noquantFp16_g1u0_atm_inlv_silu_1tg_32x512.co`) and int8 (`fmoe/silu/fmoe_fp16_pertokenInt8_g1u1_silu_1tg_32x128.co`, `fmoe_2stages/…pertokenInt8_g1u1_112x128_pf2.co`) assemble 0-fail for gfx90a after renames + exact int8 K-split (`artifacts/analysis/mi300-asm-port-inventory-20261105.md` §0.1-0.2). Blocker: Q8_0 per-32 scales vs AITER per-channel (§0.7); arms (a) per-channel int8 requant at load behind the quality gate, (b) CK 2-stage MoE instance for gfx90a, (c) technique port into `mmid.cu` (sort + fused gate/up + GLU). Est. A3B/Q38FN prefill +10–20%, verify +5–10% [inferred]. Falsifier: MUL_MAT_ID op time at A3B shapes (M in {8,512,2048}) within noise, or KLD gate failure on arm (a). Effort L. [no-belief: seed hypothesis]
- [ ] **AK-ASM-H12** [non-inference then inference] fused QSA sparse attention for Q38FN: replace C6's `build_qsa_top_k` (top_k + get_rows + masked dense FA, `src/models/qwen4exp.cpp:675`) with a kernel that scores blocks, selects groups and runs GQA attention reading only the selected KV blocks, after AITER triton `qsa.py` (`_qsa_paged_mqa_logits_mfma_kernel`, `_qsa_sparse_paged_gqa_kernel`) and `topk_per_row` asm (needs the T1 rewrite pass). Est. Q38FN long-context prefill/verify +10–30% on QSA layers [inferred: dense masked FA reads all KV]. Falsifier: QSA-layer time at 32k/80k within noise, or output mismatch vs current path beyond FA tolerance. Effort M-L. [no-belief: seed hypothesis]
- [ ] **AK-ASM-H9** [non-inference then inference] asm arm of H4: int8 GEMM for prefill/verify from AITER `gemm_a8w8_m128_noSplitK.co` / `i8gemm` (assemble 0-fail / 32-atomic-only on gfx90a after the exact int8 K-split, §0.1), with either per-channel int8 requant of Q8_0 (quality gate) or an epilogue patched to Q8_0 per-32 scales using the `fp8gemm_blockscale` epilogue as template. Time against dequant+rocBLAS and against the H4 HIP kernel at 27B shapes (M 16/512/2048). Est. 27B prefill +10–20% [inferred: removes the ~15% convert; int8 compute ceiling = bf16 on gfx90a]. Falsifier: MUL_MAT at M=2048 not faster than C6, or quality gate fails. Effort M-L. [no-belief: seed hypothesis]
- [ ] **AK-ASM-H10** [non-inference then inference] GQA-packed multi-token verify attention for hd256 (technique of AITER `pa/*_mtp_msk*` asm: 8/16 q heads × qlen share one KV read, MFMA on decode, int8 KV dequant in registers). The hd128 bf16 MTP and int8-KV PA asm assemble 0-fail on gfx90a, but asm PA is head_size 128 only (`csrc/py_itfs_cu/asm_pa.cu:192`), so the 27B/A3B/Q38FN path is a HIP builtins kernel (or extend the asm). Target: FLASH_ATTN_EXT at q rows 5–16 with q8_0 KV, no full KV→f16 convert. Est. verify step +5–12% at ≥32k ctx (FA 28.7 + convert 7.9 of 158.7 ms at 80k), ~0 at short ctx [inferred]. Falsifier: verify-step FA time at 32k/80k within noise. Effort M. [no-belief: seed hypothesis]
- [ ] **AK-ASM-H15** [non-inference then inference] fused GDN decode step after AITER `gdr_decode_packed_bf16.cu` / `fused_split_gdr_update.cu` / `causal_conv1d_update.cu` (triton `fused_gdn_decode_qkvz.py`): split qkvz + conv1d state update + gated-delta state update in one kernel, optional bf16 state. Distinct from the rejected G9 occupancy rewrite (autokernel-loop.md:4534). Est. 27B/A3B/Q38FN decode +3–8% [inferred: recurrent GDN was rank 3 at 16.7% in a GPU profile, autokernel-loop.md:5506]. Falsifier: per-token decode time within noise, or state drift vs the f32 reference over 4k tokens. Effort M. [no-belief: seed hypothesis]
- [ ] **AK-ASM-H13** [non-inference then inference] fused hyper-connection seam for Q38FN (`qwen4exp` `hc_*_norm/down/up/inject`, ~2 chains/layer of small GEMV+norm+add ops, no fused GPU kernel in C6), after AITER `mhc_seam` asm (0-fail retarget, fuses residual/layer-input with split-K partials of the next GEMM) and `mhc_kernels.cu`. Step 1: measure the hc chain's share of Q38FN decode; build only if >= 4%. Est. Q38FN decode +2–6% [inferred]. Falsifier: hc share < 4% or fused time within noise. Effort M. [no-belief: seed hypothesis]
- [ ] **AK-ASM-H14** [non-inference then inference] fused q/k RMSNorm + RoPE + KV-cache write (+q8_0 quant) per attention layer, after AITER `fused_qk_norm_rope_cache_quant.cu`; replaces 4–6 launches per attention layer. Est. decode +1–3% on all three models [inferred]. Falsifier: decode tok/s within noise. Effort S-M. [no-belief: seed hypothesis]
- [ ] **AK-ASM-H11** [non-inference then inference] retargeted AITER `topksoftmax_4xNx{4,6,8}` asm (984 lines, 0 failures on gfx90a) vs C6 `topk-moe.cu` at A3B/Q38FN expert counts. Est. MoE decode +0.5–2% [inferred]. Falsifier: router kernel time within noise. Effort S (after T0). [no-belief: seed hypothesis]
- [ ] **AK-ASM-T1** [non-inference] retarget tooling: fold into one checked script the renames, the exact int8 K-split (`/mnt/raid0/llm/tmp/mi300-asm-inventory-20261105/scripts/i8split_check.py`), `v_mov_b64` → `v_pk_mov_b32 op_sel:[0,1]`, liveness-aware `v_lshl_add_u64` / `v_fmamk_f32` rewrites, cache-bit mapping, gfx90a hazard s_nop insertion (incl. SrcC chaining of split MFMAs) and descriptor rebuild, so H8/H9/H10/H11/H12 asm arms are mechanical. Done when every non-fp8 gfx942 `.co` in `hsa/gfx942` assembles for gfx90a and the H5 kernel round-trips bit-identically. Effort M. [no-belief: seed hypothesis]

Ranking rationale: H8 and H12 hit whole-model compute on two of three production models (MoE GEMM is the bulk of A3B
work; QSA governs Q38FN long context); H9 is the prefill GEMM for all models but overlaps H4; H10 only matters at long
context; H15/H13/H14/H11 are decode-tail fusions sized by the 27–62% non-GEMM decode tail. T1 is the enabler for every
asm arm. All gains are estimates; the biggest measured-or-covered levers remain H1 (verify MMQ) and H2/H5-PORT (FA).
