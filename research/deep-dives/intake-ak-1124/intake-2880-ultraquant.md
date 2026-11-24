# Dive — ultraquant — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2606.20474v3", retrieved: "2026-11-24", sha256: "297ee39be56c"}

## 1. Stage-1 fields
- Title: UltraQuant: 4-bit KV Caching for Context-Heavy Agents. Authors: Inesh Chakrabarti, David Limpus, Aditi Ghai Rana, Bowen Bao, Spandan Tiwari, Thiago Crepaldi, Ashish Sirasao (AMD, UCLA, Purdue). v3, 2026-09-11 (paper dated 2026-08-28), cs.LG. Version in `arxiv_meta.json` is v3, not v1.
- Categories: kv_cache, quantization, hardware_optimization, inference_serving.
- Novelty: medium. Two AMD kernel paths (software codebook "Ultra-TQ" and FP4 scaled-MFMA "UltraQuant"), on CDNA4 only.
- Relevance: medium. It is the only AMD 4-bit KV decode measurement in the chain, but on MI355X (CDNA4) with hardware FP4 MFMA; the slow path it measures is a codebook LUT, not q4_0.
- credibility_score: 1 = peer-reviewed 0; <=12 months +1; AMD authors (major lab) +1; commercial bias -1 (AMD hardware and vLLM stack promotion); independent corroboration 0.
- Verdict: worth_investigating. It calibrates D1's prior (below) and supplies no portable technique: the fast path needs CDNA4 `v_mfma_scale_*` instructions.

## 2. Key claims
1. **Settled: AMD MI355X 4-bit KV measurement.** CONFIRMED, with a correction to fp4kv's framing. Decode-attention at 32K context, batch 8, MiniMax-M2.5, MI355X: FP8 KV 1071 (1.00x), Ultra-TQ 2624 (2.45x), UltraQuant 1268 (1.18x), HBM bytes per step about 23 MB / 12 MB / 12 MB (anchors 1, 2). The table prints units as "ms"; per-step kernel time at 32K batch 8 is implausibly milliseconds-scale for a decode kernel, so the unit is as printed and unverified.
2. **Settled: what made it slow.** CONFIRMED. The slow path (Ultra-TQ) is a TurboQuant-style calibrated codebook: "software codebook decode, an LDS gather, and a VALU FMA per element", dequant-bound (anchor 3). The fast path removes dequantization by feeding FP4 codes and UE8M0 scales to `v_mfma_scale_f32_16x16x128_f8f6f4` (CDNA4) (anchor 4). The 2.45x is therefore a codebook-gather cost, not the cost of plain integer decode.
3. **Roofline numbers.** CONFIRMED: achieved compute vs the bandwidth-implied ceiling: FP8 KV 23%, UltraQuant 10%, Ultra-TQ 4% (anchor 5). Even the hardware-FP4 path sits 2.3x off its byte floor in the kernel counters (1268 vs 0.52 x 1071 = 557, my arithmetic from Table 3).
4. **End-to-end gain.** PARTIAL: UltraQuant 1.38x BF16 throughput vs FP8 1.37x on MiniMax-M2.5 C = 64 (anchor 6). The paper itself states the benefit is capacity, not kernel speed: "4-bit KV buys capacity, not kernel speed" (anchor 7), and the benefit vs FP8 appears only when FP8 exceeds resident-cache capacity. Non-CDNA4 performance is out of scope (anchor 8).
5. **Rotation and quality.** CONFIRMED as stated: MXFP4 (32-channel groups, UE8M0), Hadamard-rotated queries, a global scale constant c = 0.156 (section 5). No q4_0 or INT4 quality measurement; nothing on gfx90a.

## 3. Reported results
MI355X, 2 GPUs (TP = 2), MiniMax-M2.5 and Qwen3-235B. Throughput vs BF16: UltraQuant 1.38x, FP8 KV 1.37x (C = 64, 32K/1K). Median TPOT vs BF16: UltraQuant 1.40x, FP8 1.37x, Ultra-TQ 1.58x, vLLM OSS TurboQuant 5.56x. Claude-Code trace replay (adaptive SLO): UltraQuant 2.71x (MiniMax-M2.5) and 4.38x (Qwen3-235B) of BF16 qualified requests. Qwen3.6-27B accuracy (GSM8K, LiveCodeBench) appears in a figure only.

## 4. Performance-principles table
| Principle | MI210 gfx90a | Zen 5 |
|---|---|---|
| Native scaled FP4 MFMA (dequant folded into the instruction) | **NO.** `v_mfma_scale_f32_*_f8f6f4` is CDNA4; gfx90a has f16/bf16/i8/f32 MFMA only (uncited). A software E2M1 + UE8M0 decode costs more than INT4's LOP3 path. Real hardware limit; the paper scopes non-CDNA4 out. | NO (no FP4 unit; AVX-512 has no E2M1 conversion, uncited). |
| Codebook LUT decode (Ultra-TQ) | **NO for our path.** It costs an LDS gather plus a VALU FMA per element on MI355X. q4_0 is a plain nibble decode with no table, so this cost is the one to avoid, not the one to predict. | NO (gather is the reason CPU iqk uses arithmetic decode). |
| SoA KV layout + GQA-aware tiling + hoisting the quantized query out of the K-tile loop (A.1/A.2) | **PARTIAL.** gv already keeps Q as the register A operand (`fattn-gqa-verify.cu:L225 @ 98ff8a4`); an SoA layout (codes and scales in separate streams) is a layout change behind set_rows and is fp4kv D2's fallback. | PARTIAL: already the iqk layout for weights. |
| Roofline gap bookkeeping (fraction of ceiling, per scheme) | **YES.** Gives D1 a reporting metric: q4_0 time over (q8_0 time x 18/34). | n/a |

## 5. In-house state
No q4_0 gv path (`fattn-gqa-verify.cu:L680 @ 98ff8a4`). q4_0 KV at n_q > 1 runs whole-cache dequant plus f16 MMA, 2.1x (8k) to 3.6x (16k) slower per round than q8_0 at n-max 7 (`speculative-decoding.md:L395 @ f74b175`, as cited by fp4kv). That baseline is a different kind of slow from the paper's 2.45x (it is a separate dequant pass, not a LUT).

## 6. Derived-actionables ledger
| # | Draft task line | Owner | Kind | Stop / decision rule |
|---|---|---|---|---|
| U1 | **Refines fp4kv D1.** Add a byte-floor ratio to D1's report: q4_0 us/call divided by (q8_0 gv us/call x 18/34 = 0.53), at kv32768 nb1/8, and quote the MI355X precedent (hardware FP4 path 2.3x off its byte floor, software LUT 4.7x). | `autokernel-loop.md` (AK-GVFATTN section) | doc-only (metric added to the D1 row's report) | Does not change D1's KEEP/FUTILITY rule (>= 1.3x faster than q8_0, FUTILITY < 1.0x). It reads the result: q4_0 within 1.5x of the byte floor means issue/latency is not the limit. |
| U2 | Port the FP4+UE8M0 scaled-MFMA path or the MXFP4 cache layout. | DECLINE | - | Specific to the entry: it needs CDNA4 instructions absent on gfx90a, and the paper puts non-CDNA4 performance out of scope. The software-only alternative (E2M1 decode) has a higher per-value cost than INT4's 0.625 instr/value. |

## 7. Dive-surfaced sources
| Source | In index? | Bears on | Recommendation |
|---|---|---|---|
| AMD ROCm blog "Productionizing TurboQuant on AMD GPUs" (cited by the paper), D'Alberto arXiv 2605.08114 | 0 hits | the Ultra-TQ kernel ladder; FP4 MSE analysis | decline: no ledger row changes (the ladder is codebook-specific; q4_0 has no codebook) |
| vLLM mainline FlyDSL kernel (upstreamed Ultra-TQ) | not an intake source | MFMA layout selection in a DSL | decline: CDNA4-tuned |

## 8. Contradiction / adversarial pass
- Vendor paper: AMD authors, AMD hardware, own vLLM stack. The authors state the speed result is capacity-driven and that the benefit vs FP8 vanishes at short context or low concurrency (Limitations item 2).
- The kernel table gives one configuration (32K, batch 8, one model) and no variance. The UltraQuant kernel is "planned" for release, not released, so the 1.18x cannot be reproduced.
- Version drift: the page is v3 (September), not v1.

## 9. read_depth
PARTIAL. Read: abstract, sections 5, 7, 9, Appendices A.1-A.3, B.1 head, references head. Not read: sections 3, 4, 6 (accuracy tables), Appendices B.2-F, figures. `lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9`.

## 10. Artifact audit
artifact audit: clean (the "ms" unit and the 2.3x/4.7x ratios are flagged as printed / my arithmetic).
