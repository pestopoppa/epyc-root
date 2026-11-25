# K2-shifter-quant: Shifter Quantization (SQ / SHI) on gfx90a and Zen 5

- **Entry covered:** intake-2957, "Shifter Quantization: Compact Representations for Native Integer Computation", arXiv 2611.33080v1 (Yufeng Huang, single author).
- **Source:** s02 = `/mnt/raid0/llm/tmp/dive-kspec-1125/src/s02/source.txt`.
- **Read depth:** FULL. I read the whole source, including Tables 1-10 and Appendices A-C.
- **In-house pins:** lane `f19b902` (handoffs read with `git show f19b902:`, because the worktree HEAD has moved to `65c5bee6e`). C21 llama.cpp `98ff8a4`.
- **Verification:** dive-verified. Every number in the entry matches the source. Three claims are narrowed because of baseline or configuration mismatches, and part of the SHI2 claim is overturned.

## 1. What the method actually is (the math, checked)

**SQ reconstruction (§3.2, Eq. 4-7).** Each weight has a signed x-bit code q. Each group of y weights shares an m-bit append field a_g and an n-bit shift selector r_g. The integer operand is
P = clip_t( R_δ( R_{r_g}( 2^ℓ · (2^m·q + a_g) ) ) ), where R_d is an arithmetic right shift (floor).
- Before rounding, the effective value is 2^(ℓ−r_g−δ)·(2^m·q + a_g). In effect each group gets a power-of-two exponent (n bits), and its mantissa gets m low bits shared by the group. The fixed ℓ and δ only align the value. They carry no learned fields.
- Appendix A (SQ2-G4A1S1, ℓ=2, δ=1): q=(−2,−1,0,1), a=1, r=1 gives P=(−3,−1,1,3). Setting a=0 moves every weight in the group down by one output LSB. So the shared bit works like a fine group offset.
- **Is it an exact integer dot product over the whole K?** Yes, for A8. P is a plain int8 tensor. Activations are per-token INT8 with one scale per token row ("flat per-token INT8 activation scales", §5.4; B.2). The kernel accumulates Σ_k P_jk·a_k in INT32 across all of K, then applies c_o,j · s_token once after the reduction. No float group scale is applied inside the reduction. That matches the stated claim (§3.2.4: "the dot product requires no floating-point group scale along K").
  - Overflow (my own bound, not a source number): 127·127·17,408 ≈ 2.8e8, which is below 2^31. So the INT32 accumulation is safe at the paper's largest K.
- **Where the approximation error sits.** All of it is outside the reduction:
  1. the weight fit, where the group adaptation is limited to power-of-two shifts plus a shared low-order offset (no free float scale);
  2. per-token INT8 activation rounding, with one scale per row, made workable by the signed H512 Hadamard and the input-channel scales C_i applied before quantization;
  3. BF16 rounding of the rotated activations (B.1);
  4. optional saturation.
  The channel scales C_i (input side) and C_o (output side) are float, but they sit outside the K loop: C_i is folded into the activation before quantization, and C_o is applied after the reduction.
- **Bits per weight.** B_SQ = x + (m+n)/y, plus channel scales, H512 signs and padding (Eq. 7). SQ2-G4A1S1 = 2 + 2/4 = 2.5. SQ4-G8A2S2 = 4 + 4/8 = 4.5. Both match Tables 2 and 3. Q2_K is 2.625 bpw and Q4_K is 4.5 bpw, so SQ4 and Q4_K store the same number of bytes.
- **SQ8 is not a shifter format in practice.** §5.4 says Shifter "fits per-output-channel INT8 weights after the signed Hadamard rotation". There are no groups, appends or shifts: SQ8 is plain per-channel W8A8 plus rotation.

**SHI (§3.3, Eq. 8-16, Table 1).** The weight is w = ρ·q + r_g: an INT4 base plus a signed correction shared by the group.
- **Main product:** one INT4 product over all of K.
- **Weight correction:** Σ_g r_g · Σ_{k∈g} ξ_k. This is a second product of length K/y over the activation group sums h_g. Those sums are re-quantized to 4-bit b_g with a per-token scale t.
- **Activation correction (SHI4):** a third product, Σ_g d_jg·c_g, where d is the weight group sum S_w re-quantized to 4 bits with a per-row scale u_j. It also absorbs the cross term, so no fourth product is needed.
- **Cost:** 1.125K of work at G8 for two products, 1.25K for three (Table 1).
- **Approximation:** the residual error comes from quantizing the group sums to INT4. The paper says Eq. 16 "approximates" Eq. 14.
- **SHI2:** a single product. The SQ2-G4A1S1 weight fits in INT4 exactly, so all the extra error comes from the A4 activations. Output error rises from 22.971% to 27.924% (Table 2).
- **Bits:** SHI4 G8 is 4.5 bpw serialized and 5.0 bpw resident if the prepared d plane is kept (§3.3).

## 2. Per-claim verdicts

| # | Claim (Stage 1) | Verdict | Locator | Note |
|---|---|---|---|---|
| 0 | SQ rebuilds INT8/INT4 operands by append + grouped shift + truncate; integer MMA spans the whole K with no float group scale | CONFIRMED | §3.2, Eq. 4-7, §3.2.4 | Exact INT32 dot over K for A8. The residual error is in the weight fit and the per-token activation rounding. Channel scales stay outside the loop. |
| 1 | SHI keeps the main product in INT4 and adds grouped weight/activation corrections as shorter integer products | CONFIRMED | §3.3.1-3.3.3, Table 1 | The correction products re-quantize group sums to 4 bits, which adds error (Eq. 16 vs 14). |
| 2 | RTX 5090 27B down projection at 4,096 tokens: 2.77x (SQ2/INT8) and 4.55x (SHI2/INT4) vs Q2_K | PARTIAL (numbers confirmed, narrowed) | Table 2, §4.1 | 1,504.74 / 914.34 vs 4,162.47 µs. The Q2_K tensor is a local refit. llama.cpp is timed with FP32 input, residual and output, while Shifter uses BF16. **SHI2's 4.55x has higher output error than Q2_K (27.924% vs 24.152%).** |
| 3 | Released 2-bit checkpoints prefill 4,096 tokens 2.71x (SQ2) and 3.77x (SHI2) faster than a Q2_K GGUF, with lower KL | PARTIAL; overturned for SHI2 "with lower KL" | Table 5, §5.2.2 | 8,378.4 / 11,662.4 vs 3,090.7 tok/s; KL 0.15322 / 0.15537 vs 0.16627. **Both Shifter KLs were measured with INT8 activations, but SHI2's prefill speed uses four-bit activations.** The 3.77x configuration has no reported KL. The paper does not state the llama.cpp version, its `-ub` (ubatch size) or its flags. |
| 4 | SQ8 beats vLLM FP8 W8A8 on 27B in prefill throughput with lower KL | PARTIAL (narrowed) | Table 7, §5.4 | 9,206.3 vs 7,226.8 tok/s; KL 0.00211 vs 0.00774. vLLM uses **per-tensor** E4M3 weights, while SQ8 is per-channel INT8 plus Hadamard. The KL win reflects the coarse baseline more than the shifter idea. Prefill is batch one with CUDA graphs off. |
| 5 (append) | SQ4 is 1.43-2.47x NInfer groupwise-INT prefill | PARTIAL (narrowed) | Table 8, §6.1 | The NInfer numbers are its **published** rates for rev a754fcf3, not re-run by the author. The KV formats differ (Shifter INT8 KV vs NInfer FP8 / INT8 G64). Shifter uses tuned per-workload profiles. |
| 6 (append) | SHI4 is slower than native NVFP4 in serving | CONFIRMED | Table 8, §7 | 0.80x / 0.88x / 0.92x. |

Counts: C 2 (claims 0, 1) + 1 appended (6) · P 3 (claims 2, 3, 4) + 1 appended (5) · O 0 full, 1 partial (SHI2 "lower KL" in claim 3) · NF 1 (the llama.cpp baseline's version, ubatch and flags).

**Q2_K baseline path.** The paper says only that "the llama.cpp CUDA graph prepares Q8_1 activations". Q8_1 activations mean llama.cpp's integer MMQ/MMVQ kernels. In the C21 tree, `ggml_cuda_should_use_mmq` returns true for Q2_K on any GPU with Turing-class int8 MMA (`ggml/src/ggml-cuda/mmq.cu:L328-330 @ 98ff8a4`), so the 5090 Q2_K baseline is almost certainly MMQ with int8 MMA. That is an inference from code: the source names no version.

## 3. Adversarial pass

- I ran two WebSearch queries (title/ID and "Shifter Engine"). Neither found an independent replication, a reproduction, a code release or any discussion. The paper is a day old (v1, 24 Nov 2026). Corroboration: none.
- Internal consistency holds. The KL-improvement percentages and the bpw values follow from the tables.
- **Baseline weaknesses:**
  1. FP32 vs BF16 I/O asymmetry in the projection timing;
  2. a local Q2_K refit for the projection, but Bartowski's imatrix file for prefill;
  3. no llama.cpp ubatch or version;
  4. NInfer published rates instead of a same-box run;
  5. per-tensor FP8 for the 8-bit comparison;
  6. SHI2 speed and quality measured in different activation configurations.
- The claim that low-bit decode tracks bandwidth is supported by the paper's own Figure 1 statement: decode tracks memory bandwidth across four GPUs. Its decode gains are modest (Table 8 structured decode 1.01-1.13x for SQ4).

## 4. In-house comparison (pinned)

- **Q8-W8-GEMV-1 design 4** (`handoffs/active/rocm-kernel-authoring.md:L1159 @ f19b902`) used an int8 MFMA w8 GEMV. It cut static instructions per byte from 0.101 to 0.034, yet ran at 0.478x (MW2) and 0.304x (MW4) of stock q8wv. Per-lane row-scattered 4 B-aligned loads touched about 3x more TA/L1 requests per byte. Verdict there: "Coalescing, not instruction count". SQ changes the instruction count and the scale application. It does not by itself fix load coalescing.
- **Design 5** (`:L1160`) uses an MFMA-operand-order packed copy: GATE_PASS_PW2 at 1.316x, about 73% of peak, KLD 0.000234.
- **Q8-W8-INPLACE-E2E-1** (`:L1161-1164`) is design 5 in place: KEEP, but only +0.6-1% end to end.
- **Q8-SERVED-PROFILE-1** (`:L1165`): weight GEMV is 44% of the 64.2 ms step. The ceiling is 1.18x at 1638 GB/s.
- The paper independently arrives at the same layout rule: "For 27B SQ4 it pins tiled weights through eight verifier columns … Wider waves … use row-major weights" (§6.3). A tiled, MMA-fragment-order layout for narrow verify widths is exactly our design-5 lesson. It is the layout, not the code format, that pays at w8.
- **quantization-and-low-bit.md (INF-80):**
  - The low-bit gate is KLD-based: KLD ≤ 0.003 on the Q8 rows (rka `:L1154`).
  - The 27B quant switch is trigger-gated: "no quant switch without a significant speedup" (EXL3-X0b, `quantization-and-low-bit.md:L102 @ f19b902`).
  - The MI210 low-bit decode profile (EXL3-LB1, `:L107-L112`) found Q4_K MMVQ at 46.5% of roofline vs Q8_0 at 70.2%, and Q8_0 MMQ at about 31% at M=8/16.
  - We serve IQ2_XXS / IQ3_XXS mixes for the large MoE models (`:L392-393`).
  - QUANT-ROT-1 (`:L232`) is an open offline activation-rotation probe at a per-32 budget.
- **Where float block scales enter the K loop today (C21 `98ff8a4`):**
  - **GPU, MMQ Q8_0, CDNA int8 MFMA:** `ggml/src/ggml-cuda/mmq-vec-dot.cuh:L143-199`. Each 32-element K step issues two `v_mfma_i32_16x16x16i8` (`mma.cuh:L1313-1315`). Then every output element does `sum += C.x[l]*dA*dB` (`:L197`). dA is the per-32 weight scale read from LDS, and dB is the **per-32 activation Q8_1 scale**.
  - **GPU, MMQ Q2_K:** `mmq-vec-dot.cuh:L683-750`. Each 16-element step issues one 16x16x16 i8 MFMA. Then a per-16 float scale and min epilogue runs (`:L748-749`), plus an all-ones MFMA (Cm) for the min term. The loader pre-multiplies d·sc and dmin·m into half2 (`mmq-load-tiles.cuh:L461-520`). Q2_K therefore applies twice as many float rescales per K as Q8_0.
  - **GPU routing:** on CDNA2, dense Q8_0 and Q2_K use MMQ only at ne11 ≤ 128 (`mmq.cu:L346-362`). Larger prefill batches are dequantized to f16 and run through hipBLAS.
  - **CPU, Q8_0 × Q8_0:** `ggml-cpu/arch/x86/quants.c:L1417-1480`. Each 32-block runs `vpdpbusd` (sign trick, `:L105-133`), converts to float and does one FMA with dx·dy (`:L1465`).
  - **CPU, Q2_K × Q8_K:** `quants.c:L1787-1862`. This is **already SQ/SHI-like**. The 4-bit sub-block scales are applied as an integer `madd_epi16`, and the whole 256-element super-block accumulates in int32 (`:L1856`). Only one float FMA runs per 256 (`:L1859`). The min term is an integer bsums × mins product (`:L1818`), which is the same structure as SHI's grouped correction (Eq. 10).

## 5. Principles table

| Principle | Source evidence | MI210 (gfx90a) verdict | EPYC Zen 5 verdict | Why (mechanism) | Port cost |
|---|---|---|---|---|---|
| (a) Shared-bit packing (power-of-two shift + shared low bits) instead of per-group float scales, so the K reduction stays integer | §3.2, Eq. 6-7, App. A | TRANSFERS-WITH-CHANGES (only where MFMA-bound: MMQ at ne11 9-128 and prefill) | ALREADY-PRESENT for K-quants × Q8_K; DOES-NOT-TRANSFER as a decode win | GPU MMQ applies a float FMA per 32 (Q8_0) or per 16 (Q2_K) per output element. Removing it saves VALU only when MFMA-bound, and **it also requires per-token activation scales**: Q8_1's per-32 dB is a second in-loop scale. On CPU the K-quant dot already accumulates int32 across 256 with integer sub-scales. Decode is bandwidth-bound, so the epilogue is hidden. | New GGUF type + quantizer + Hadamard + per-token activation quant + MMQ path: high |
| SQ8 = per-channel INT8 + Hadamard | §5.4 | UNKNOWN-NEEDS-PROBE (decode bytes) | UNKNOWN-NEEDS-PROBE (decode bytes) | 8 bpw vs Q8_0's 8.5, so at most about 6% fewer weight bytes (my arithmetic). Rows become pure int8, 16 B-aligned, with no scale gather. The quality versus Q8_0's per-32 scales is unknown: the paper's KL win is against per-tensor FP8, and Q8_0's scale granularity is finer than per-channel. | Offline quality probe is cheap; the runtime change (online H512 + format) is high |
| (b) Mapping to int8 MMA (v_mfma_i32_16x16x16i8 / 32x32x8i8; vpdpbusd) | §3.2.4, B.2 | TRANSFERS (int8 MFMA exists); no rate gain over f16 | TRANSFERS (VNNI; signed weights need the sign/offset trick, as today) | P is a plain int8 operand. On CDNA2 the int8 MFMA processes the same K per instruction as f16 (16x16x16i8; CDNA3 doubles it to x32, `mma.cuh:L1311-1315`). So int8 adds no MFMA throughput over the hipBLAS f16 prefill path. The gain would be removing the dequant-to-f16 pass and halving operand bytes. | Medium |
| SHI INT4 main product plus grouped correction products | §3.3, Table 1 | DOES-NOT-TRANSFER (no INT4 MFMA on gfx90a) | DOES-NOT-TRANSFER as INT4; correction-product idea ALREADY-PRESENT (Q2_K bsums × mins) | The SHI speedup depends on INT4 having twice the INT8 rate. The correction-sum structure is already how K-quant mins are handled, on CPU and in MMQ's Cm MFMA. | n/a |
| (c) Coalescing / tiled layout of packed rows for narrow verify widths | §6.3: tiled weights through 8 (SQ4) or 16 (SHI4) verifier columns, row-major wider | ALREADY-PRESENT (design 5 q8wp MFMA-operand-order permutation, in place, KEEP) | UNKNOWN-NEEDS-PROBE (minor; iqk Q8_0_R8 repack already interleaves for prefill, `iqk_dispatch.cpp:L90`) | Design 4 showed row-scattered packed loads lose 2-3x even with fewer instructions. SQ's sub-byte fields (2 bits per group of 4) make row-scattered gathers worse unless they are packed into fragment order. The paper does not specify its storage interleave (NOT-FOUND-IN-SOURCE). | Already paid for Q8_0 |
| Hadamard H512 + per-token static/dynamic activation clipping | §3.1 Eq. 3, App. B | UNKNOWN-NEEDS-PROBE | UNKNOWN-NEEDS-PROBE | This is the enabler for per-token INT8 activations (and so for removing the in-loop dB). It overlaps QUANT-ROT-1. | Offline: low. Online: an H512 butterfly before every projection, fusable with the activation quantize |
| Decode is bandwidth-bound, prefill compute-bound | §6.4, Fig. 1, App. C | ALREADY-PRESENT (in-house profiles) | ALREADY-PRESENT | Format gains in decode come only from bytes. SQ2 (2.5 bpw) is larger than the IQ2_XXS we serve, and SQ4 is the same size as Q4_K. | n/a |

### Regime answer

- **gfx90a, prefill (compute-bound, ne11 > 128 → dequant + hipBLAS f16).** An SQ8-style int8 GEMM gets no MFMA-rate gain on CDNA2. Any win comes from dropping the per-ubatch f16 dequant pass and halving LDS and register operand bytes: UNKNOWN-NEEDS-PROBE, probably modest.
- **gfx90a, MMQ ne11 9-128 (MFMA-bound-ish).** Removing the per-32 epilogue (`mmq-vec-dot.cuh:L197`) could matter, because the VALU epilogue is the same order as the MFMA issue count. It needs both a per-row weight scale and per-token activation scales. The served profile puts the hot verify width at w8, which runs on the GEMV path rather than MMQ, so the payoff in serving is small.
- **gfx90a, decode and w8 verify (bandwidth-bound).** Bytes and coalescing decide. SQ8 gives at most about 6% fewer bytes. At a 44% weight-GEMV share that is under about 3% of the step (inferred upper bound), and only if the quality matches Q8_0 at our KLD ≤ 0.003 gate. SQ2/SQ4 are only relevant if the trigger-gated 27B low-bit switch reopens. SHI does not apply (no INT4 MFMA).
- **EPYC, decode (bandwidth-bound).** No compute win: K-quant × Q8_K is already integer across 256, and the Q8_0 per-32 FMA is hidden under bandwidth. The byte change from SQ2 vs Q2_K is −0.125 bpw, and SQ2 is worse than IQ2_XXS. Not worth a format.

## 6. Derived-actionables ledger

| ID | Action | Owner guess | Disposition | Reason |
|---|---|---|---|---|
| KS-K2-shifter-quant-1 | Add an offline arm to QUANT-ROT-1: per-output-channel INT8 after signed H512 (the SQ8 recipe) vs Q8_0's per-32 FP16 scales on real 27B rows. Measure weight and output error, and dKLD if it is cheap. No kernel work. | handoffs/active/quantization-and-low-bit.md (QUANT-ROT-1) | immediate | Decides whether the only bandwidth lever SQ offers for our Q8_0 serving (8 vs 8.5 bpw, 16 B-aligned rows, no scale gather) is quality-viable before any kernel work. |
| KS-K2-shifter-quant-2 | When a counter row next profiles MMQ Q8_0 at ne11 9-128 on CDNA2, record the VALU epilogue share (the `C.x*dA*dB` loop) against MFMA busy. | handoffs/active/rocm-kernel-authoring.md | monitor | This sizes the in-loop scale cost SQ claims to remove, on our hardware. It is low priority because the served hot path is w8 GEMV. |
| KS-K2-shifter-quant-3 | Record: on gfx90a an int8 GEMM has the same per-instruction K as f16 MFMA, so an SQ8-style prefill gain is limited to removing the dequant pass and halving operand bytes. | handoffs/active/rocm-kernel-authoring.md | knowledge-only | Prevents carrying NVIDIA's INT8 = 2x speedup framing over to CDNA2. |
| KS-K2-shifter-quant-4 | Record: SHI (INT4 main product) does not transfer to MI210. The CPU K-quant dot already does SHI-style integer correction products. SQ2/SQ4 are relevant only if EXL3-X0b's low-bit trigger reopens. | handoffs/active/quantization-and-low-bit.md (EXL3-X0b) | knowledge-only | A real hardware constraint (no INT4 MFMA), plus existing CPU code. |

## 7. Dive-surfaced sources

- NInfer rev a754fcf3 (`https://github.com/Neroued/ninfer/tree/a754fcf3bf524494aa927c2f54e0cbfb58f569ab`). It would settle the SQ4 baseline numbers, which are published rates, not re-measured. Recommend: decline (a CUDA-only serving engine used as a baseline).
- "QServe: W4A8KV4 Quantization and System Co-design for Efficient LLM Serving" (MLSys 2025), cited for the claim that partial-sum dequantization overhead is substantial. Recommend: decline (known technique class; the claim is checked here directly in our MMQ code).
