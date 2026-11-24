# Dive — foscar — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2611.09722v1", retrieved: "2026-11-24", sha256: "9269e28223e9"}

## 1. Stage-1 fields
- Title: FOSCAR: Accelerating Decode Attention over 2- and 4-Bit KV Caches through Affine Folding. Authors: Donglin Zhuang, Pragaash Ponnusamy, Xiaoxia Wu, Shuaiwen Leon Song, Zhongzhu Zhou (Together AI; University of Sydney). v1, 2026-11-06, cs.AI. Code: github.com/FutureMLS-Lab/FOSCAR (not fetched).
- Categories: kv_cache, quantization, hardware_optimization.
- Novelty: medium. Affine folding itself is algebra (Eq. 3, 4); the contribution is the issue-budget argument (Eq. 2) and kernels for H100/B200.
- Relevance: medium-high for D1/D3 as a cost model; low as a kernel (wgmma/tcgen05 only).
- credibility_score: 1 = preprint 0; <=12 months +1; major lab 0; commercial bias 0 (open-source kernel library, vendor baselines run by the authors); independent corroboration 0.
- Verdict: adopt_patterns (the Eq. 2 definition and the folding algebra; nothing of the kernel).

## 2. Key claims
1. **Origin of the issue-budget model.** CONFIRMED: Eq. 2 is defined in this paper: a_issue / B_elem <= C_issue / B_HBM, with a_issue in lane-slots per value and C_issue the peak instruction-issue rate in lane-slots/s. H100 budget 9.99 lane-slots/byte, B200 4.65 (anchor 1). It is the paper's own construct, not cited from elsewhere. fp4kv's use of "FOSCAR Eq. 2" is correct. The paper counts instructions analytically (six per four values on H100), not by NVBit.
2. **Affine folding mechanism.** CONFIRMED: token-wise K folds into the accumulator (scale the group-local partial product, add offset x query sum); token-wise V folds into P (scale P before PV, add offset-weighted sum to the output); channel-wise is the mirror (anchors 2, 3). Exact in exact arithmetic.
3. **Cost of folding.** CONFIRMED with a limit the abstract hides: folding costs one scale multiply and one offset multiply-add per group **per query head**, 2·h_q/g scalar operations per stored value, versus 1 per value for per-value reconstruction (reused across heads). Break-even at g = 2·h_q (anchor 4). Evaluated only at g = 128, D = 128, h_q 1-32, n_q = 1 decode (anchor 5).
4. **Hardware effect.** PARTIAL/NARROWED: the big win is B200-specific (7.36-8.86x from folding on INT2) because there reconstruction exceeds the issue peak; on H100, where reconstruction stays inside the issue budget, folding adds only 1.07-1.15x (anchor 6). "Up to two orders of magnitude" fewer scale-and-offset operations (abstract) is a count of scalar affine ops at large g and small h_q, not a speedup.
5. **AMD / MFMA.** NOT-FOUND-IN-SOURCE: no AMD GPU, ROCm, HIP or MFMA is mentioned anywhere in the page text. No MI210 number exists.

## 3. Reported results
H100 (80 GB) and B200 (180 GB), H_Q 32, H_KV 8, D 128, page 64, token-wise groups g = 128 with FP32 scales and offsets. INT2/INT4 geo-mean over FlashInfer BF16: H100 3.36x / 2.83x, B200 2.67x / 2.30x; versus TensorRT-LLM FP8: H100 2.03x / 1.71x, B200 1.48x / 1.28x; INT4 on B200 is 1.00x versus TRT-LLM NVFP4. Effective KV throughput at B = 128, 32K: FOSCAR 91.3% (INT4) and 60.6% (INT2) of H100 peak. Table 1 ALU cost per stored value: Hopper INT4 to BF16 1.00, Blackwell INT4 to E4M3 0.38, INT2 to E2M1 0.19. Serving: up to +170% / +341% peak aggregate throughput over 2-bit and 16-bit baselines (Qwen3-8B, 100K in, SGLang).

## 4. Performance-principles table
| Principle | MI210 gfx90a | Zen 5 |
|---|---|---|
| Eq. 2 issue budget | **YES, as a tool.** Lane-slots per CU-cycle are 64 on gfx90a (wave64 over a 16-lane SIMD x 4; uncited) versus 128 per SM on H100, so the budget is ~7.6/byte at 1.498 TB/s (fp4kv Q4), below H100's 9.99 for HBM2e-class bandwidth. The paper's 6 instructions per 4 values (1.5/value) is one accounting; fp4kv's LOP3 path is 0.625/value. Compare in the same unit. | PARTIAL: ample margin (fp4kv Q4). |
| Acc-fold for token-wise K (scale the group-local partial product) | **PARTIAL, probably no VALU saving at q4_0 g32.** (My inference.) q4_0 groups are 32 dims = two k-steps of the 16x16x16 MFMA, so each group needs its own accumulator, then one scale-and-add into the running S per output element. Per MFMA the output has 256 elements = 4 per lane; decoding 512 values costs 8 values per lane. Folding therefore costs about 4 scale-FMAs per 8 values = 0.5 per value per 16-row N tile. Per-value reconstruction with packed f16 math (`v_pk_mul_f16`, uncited) costs about 0.5 per value, independent of R. Equal, before counting extra AGPR to VGPR moves of partial accumulators. | NO (no matrix unit; scale per block is already one multiply per 32 values). |
| Operand-fold for V (scale P per token) | **NO for q4_0 as stored.** The V scale varies with d-group as well as token, so one scaled-P copy per d-group is needed (8 groups at D 256): R x 8 multiplies per token vs 256 values. That is R/32 per value, the same 2·h_q/g law with R = gqa·n_q rows. | NO |
| Break-even g = 2·h_q, with R = gqa·n_q in verify | **Decisive.** q4_0 has g = 32, so break-even is R = 16 rows on the paper's accounting (offset kept) and R = 32 if q4_0's symmetric offset is absorbed into the magic centring (derived). 27B R = 6·n_q: n_q 1 gives R 6 (folding wins: 0.375/value vs 1); n_q 3 gives 18 (loses/ties); n_q 8 gives 48 (3.0/value vs 1). Production verify batches are n_q 2-16, so folding is not a general VALU cut here; it helps n_q = 1 only. | n/a |
| Mantissa injection (OR with 0x4300 BF16) | **YES, already in fp4kv's table** (f16 0x6400 variant, MFMA f16/bf16 both exist; uncited). | n/a |
| Warp-specialized TMA/tcgen05 pipeline, E4M3/E2M1 operands | **NO.** No FP8/FP4 MFMA operands on gfx90a and no TMA (uncited); not needed for the issue-budget question. | n/a |

## 5. In-house state
gv_fattn has no q4_0 path (`ggml/src/ggml-cuda/fattn-gqa-verify.cu:L680 @ 98ff8a4`). K is dequantised into LDS as f16 and P round-trips LDS (`:L145`, `:L175`, `:L201`), so there is no folding or per-group accumulator logic to compare against. q8_0 gv has the same per-value dequant (scale per 32), the same g = 32.

## 6. Derived-actionables ledger
| # | Draft task line | Owner | Kind | Stop / decision rule |
|---|---|---|---|---|
| F1 | **Refines fp4kv D1/D2.** In the D1 design note, choose the q4_0 K scale strategy by count: per-value packed-f16 reconstruction (~0.5 op/value, independent of R) versus acc-fold (~0.5 op/value per 16-row N tile, plus accumulator moves). Default to per-value reconstruction; make acc-fold an A/B only for the n_q = 1 path. | `autokernel-loop.md` (D1 step 0) | code/doc-only | Question: which scale placement uses fewer VALU+AGPR instructions per q4_0 value at R = 6, 12, 24, 48? Decide from a disassembly count of the two decode snippets (llvm-objdump of a standalone device function, no GPU row). Stop when counts are in. |
| F2 | **Refines fp4kv D3.** Report the census in Eq. 2 units: instr/value from the disassembly, lane-slot budget from the measured clock (rocprofv3), implied utilisation. | `rocm-kernel-authoring.md` | attaches to D3 (citation only, no new row) | Same stop rule as D3. |
| F3 | Port the wgmma/tcgen05 warp-specialized pipeline or E2M1/E4M3 operand tricks. | DECLINE | - | Specific to the entry: it relies on tensor-core operand formats and async memory units absent on gfx90a; the gfx90a-relevant content (integer decode, folding algebra) is already in F1. |

## 7. Dive-surfaced sources
| Source | In index? | Bears on | Recommendation |
|---|---|---|---|
| github.com/FutureMLS-Lab/FOSCAR | 0 hits | exact INT4 packing on H100/B200 | decline: CuTe DSL for Hopper/Blackwell; no ledger row changes |
| OSCAR (Zhou et al. 2026), WUSH-KV | already referenced in the index (8 and 51 hits) | - | none |

## 8. Contradiction / adversarial pass
- All speedups are against baselines the authors ran (FlashInfer BF16, TRT-LLM, BitDecoding, SAW-INT4), on two NVIDIA parts. No independent run.
- The headline "two orders of magnitude" counts scalar affine ops at large g and small h_q; the paper's own ablation shows H100 gains of only 1.07-1.15x.
- Folding was measured at g = 128 and n_q = 1; Appendix C shows the gain falls as h_q rises (H_KV = 1 gives 0.91x/1.10x on H100). Nothing covers g = 32 with multi-row verify.

## 9. read_depth
PARTIAL. Read: abstract, sections 1-4, 6.3-6.5, Appendix C, table captions; skimmed Appendices A/B and section 7 (related work). Not read: figures (text-only), 6.1/6.2 per-config numbers. `lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9`.

## 10. Artifact audit
artifact audit: clean (derived lane-slot and per-value counts are labelled as my inference/uncited).
