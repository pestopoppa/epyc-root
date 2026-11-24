# Dive — lowbitdec — intake-ak-1124 (Stage 2b wave 1, expanded from intake-2872 exactpaper)

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2608.06564v5", retrieved: "2026-11-24", sha256: "988428c81cf1"}

Note: the retained page is v5 (5 Oct 2026, CC BY-NC-SA 4.0), not v1; figures below are from v5.

## 1. Stage-1 fields
- **Title:** Which Decisions Low-Bit Quantization Breaks, and How to Predict Them
- **Authors:** Zekun Wu, Swati Dhiman, Adriano Koshiyama (Holistic AI; UCL Centre for AI). arXiv 2608.06564 v5.
- **Setup:** 16 models, 8 families, 0.6B to 32B; weights quantized by RTN, activation-aware scaling, GPTQ and GGUF at 4/3/2 bits (8/6/5 on subsets); embeddings and output heads stay full precision. Decisions are scored at the **first token** as a logit margin between two candidate tokens (tool-call vs text, which tool, refusal vs comply, MMLU/BoolQ options); 1,092 items, eleven decision kinds. Activation and KV-cache precision axes are also swept on 4 to 5 models. Not covered: rollouts, speculative decoding, drift over a generation, HIP/CPU kernels.
- **Categories:** quantization, benchmark_methodology, kv_cache.
- **Novelty:** medium. Margin shrinkage as the flip mechanism is a modelling claim; for us the useful part is a held-out flip forecast and the KV-cache sensitivity numbers.
- **Relevance:** medium-high: bears on A4/A5 (a cheaper flip predictor) and on tau design, but it predicts deterministic quantization effects at one token, not scheduling noise over a generation.
- **credibility_score: 2.** Arithmetic: peer-reviewed 0 (arXiv; no venue stated); <=12 months +1; known lab 0; commercial bias 0; independent corroboration +1 (qnoise's measurement that flips concentrate where the reference is unsure, 86 to 100% of flips below p<0.7 on the 9B, is what this account predicts; qnoise cites it and does not replicate the law). AI-assisted analysis disclosed with a 422-claim consistency check.
- **Verdict: worth_investigating.** One offline test (LB-1) decides whether the forecast gives us a stable tau.

## 2. Key claims
1. **Quantized margin is approximately linear in the original margin, m' ~ c m + b, with c usually below 1 and falling with bit width; this is shrinkage plus a per-kind offset, not additive noise.** CONFIRMED as the paper's central modelling claim (median c 0.86 at 4 bits, 0.29 at 3, 0.00 at 2; the multiplicative account wins all 642 damaged conditions by BIC). A quarter of conditions have too little margin spread to estimate c (SE must be <=0.10). Anchor A1.
2. **A held-out forecast predicts flip rates to a median error of 1.0 percentage point over 1,082 conditions** (fit c, b, sigma on half the items, predict the other half; reusing the first half's own flip rate misses by 1.3). CONFIRMED with limits: error is 4.3 points (median) on the 316 mid-range conditions; constants copied from another model miss by 26.8 points at 3 bits (2.6 at 4 bits); the forecast predicts a margin sign change, not generated output. Anchor A2.
3. **Which decision breaks depends on its kind: whether-to-call collapses at 3-bit RTN on most models while which-tool changes less; GGUF and GPTQ flip far fewer whether-to-call decisions than plain rounding.** CONFIRMED on the paper's models; "predicts which calls go missing" is validated only on Qwen3-4B at 4 bits. Anchor A3.
4. **KV-cache precision: an 8-bit cache is nearly free (median change in c 0.0055 over 28 checks on two models), a 4-bit cache costs more margin than 4-bit weights (c 0.57-0.81 vs 0.83-1.03), and no cache width below 8 bits is safe for every model.** CONFIRMED for two fully swept models plus four 8-bit-weight models; quantizer scheme matters (symmetric vs asymmetric per-token differ by up to 0.54 in c). Anchor A4.
5. **At 4-bit activations into the linear layers, margin is destroyed whatever the weights keep; KV-only 4-bit flips 3 to 18% of decisions on four models, linear-input 4-bit flips 44 to 84%.** CONFIRMED (activation, not our weight-only/KV axis). Anchor A5.

## 3. Reported results (as stated)
Weights: median surviving fraction c 0.86 / 0.29 / 0.00 at 4/3/2 bits (main matrix, mostly RTN and activation-aware). Forecast: median absolute error 1.0 point, 90th percentile 7.8 over 1,082 conditions (677 from additional experiments); 316 mid-range conditions 4.3 / 11.9. Cache: 8-bit cache median delta c 0.0055 (28 checks); 4-bit cache costs a median 0.30 in c on forced-choice safety and whether-to-call, 0.11 elsewhere; 3-bit takes the first two to zero. Hardware and engine for the runs: NOT-FOUND-IN-SOURCE in the portions read (the paper quantizes in its own pipeline and reads logits).

## 4. Performance-principles table (mechanism / cost model)
| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| Flip probability from margin: P(flip given m) = Phi(-(c m + b) sign(m) / sigma) | YES: analysis-only; needs top-2 margins at each position, which gate runs already retain (protocol §3) | YES, same |
| For pure noise (c=1, b=0) the law reduces to Phi(-abs(m)/sigma) with sigma the margin-delta spread between two arms | YES: a principled tau from the Delta-margin distribution (SPEC-ID-NOISE-1 already records |delta logit| q99) instead of the first-divergence maximum that was TAU_UNSTABLE | YES |
| Per-kind constants, refit on every model and bit width (copying constants misses by 26.8 points at 3 bits) | YES: so fit per (model, KV type, device) | YES |
| KV cache bits are costlier than weight bits at equal width; 8-bit nearly free | PARTIAL: our served q8_0 KV is the "nearly free" regime on their two models; q4_0 KV is the costly regime; gv_fattn q4_0 design should gate on it. Their cache quantizers are per-token, ours are block-wise (uncited difference), so c must be re-measured | PARTIAL: same |
| Activation quantization to 4 bits kills margin | N/A for MI210 (no such path in C21) and for CPU Q8_0 activations (8-bit activations are "effectively free" in their sweep) | same |

## 5. In-house state
- Gates capture top-2 margins at first divergence and classify them into exact0/le0.1/le0.5/gt0.5 (spec-identity-gate-protocol.md §3 @ f74b175); default tau 0.5 nats because SPEC-ID-NOISE-1 was TAU_UNSTABLE (20/34 classes unstable GPU; speculative-decoding.md:908 @ f74b175). The unstable estimator is a rare-event first-divergence maximum.
- Fold gates for quantized kernels use KLD<=0.003, |dPPL|<=0.5%, top-1 (kernel-champion-and-promotion.md:28 @ f74b175): a deterministic-effect gate, which is the regime this paper's law describes.
- No margin-law or c/b/sigma fit exists in the lane: a case-insensitive grep of handoffs/active, wiki and docs in the lane worktree for "surviving fraction", "margin law", "margin-law" returned no files.

## 6. Derived-actionables ledger
| # | Task line | Owner (lane file; status) | Compute | Stop / decision rule |
|---|---|---|---|---|
| LB-1 (refines exactpaper A2/A3) | Offline: from SPEC-ID-NOISE-1's retained per-position top-2 margins and the per-class |delta logit| samples, fit sigma per width class and predict the first-divergence rate over 128 tokens with the paper's normal-tail law (c=1, b=0); compare with the observed 20/64 (GPU DFlash2 M1 vs M2) and 0/64 (CPU) and with tau at k sigma | speculative-decoding.md, new box under SPEC-ID-GATE-1 | code/doc-only on retained data (if per-position margins were retained; otherwise first a small re-capture row) | Question: is a sigma-based tau stable where the first-divergence maximum was TAU_UNSTABLE? Stop-on-answer when predicted vs observed first-divergence share is within a pre-set tolerance (choose before the run) on calibration and holdout halves; stop-on-futility if margins were not retained |
| LB-2 (refines exactpaper A5) | Before any graded KV-quant flip run, add a screening pass: paired reference-vs-candidate (q4_0 vs q8_0/f16 KV) first-token margins on a held-out decision set that includes a whether-to-call class; fit c with SE<=0.10; report c and predicted flip rate; skip the graded replicas if c is within 0.04 of the 8-bit-cache result | kv-cache-program.md (check not frozen at apply); GPU/CPU small row | GPU + CPU | Question: is q4_0 KV in the paper's 'costly' regime (c 0.57-0.81) on our hybrid models? Done when c with SE is reported per (model, device); decision: c within 0.04 of the q8_0 KV c -> graded replicas optional; else graded flip budget (A5) required. Predictor validated against one observed flip rate before use (their median error 1.0 point is not ours) |

Declines: (a) using the law to choose weight quant formats or bit widths: the paper's collapses are 3-bit RTN on 0.6-32B dense models; our served weights are Q8_0/IQ4_XS-class and gated by KLD/QDEC, so no new decision; (b) activation-quantization and rotation sections: no 4-bit activation path in C21; (c) importing any c, b or sigma value (protocol forbids imported thresholds; paper says constants do not transfer across models).

**Is it a cheaper flip predictor than full graded replicas?** For first-token, discrete decisions, yes: one paired forward pass per item, no generation, 1.0-point median error. For us it is cheaper only as a screen and as a tau estimator: it predicts a margin sign change at one token, whereas a graded outcome flip needs any of hundreds of positions to flip, and for our scheduling-noise comparisons c=1, b=0 so the 'law' adds only the normal-tail form, which LB-1 tests offline.

## 7. Dive-surfaced sources
- 2606.09864 (Xu et al., alignment collapse under KV cache quantization): PRESENT in index (25 hits); not needed.
- 2407.09141 (Dutta et al., flips): PRESENT (14 hits); not needed.
- 2607.27275 (Jang et al., flat score amplified failures in quantized LLM agents) and 2607.01478 (boundary-aware quantization): ABSENT; cited here. Neither would change LB-1/LB-2. Decline.
- 2611.12634 (Lu and Ni): surfaced under qnoise; not repeated.

## 8. Contradiction / adversarial pass
- First-token decisions only; the authors say "how damage accumulates over a rollout is not covered" and the correspondence between margin and generated behaviour weakens under severe quantization. The missed-call forecast is validated on one model at 4 bits.
- Weights quantized by the authors' own RTN/AWQ/GPTQ pipelines with embeddings/heads in full precision; "4-bit" is above 4 effective bits. One activation-ladder model carries a caveat (Gemma-4-E4B keeps 35.5% of parameters full precision and is excluded from the activation counts).
- Forecast is least accurate mid-range (4.3 median, 11.9 p90) and constants do not transfer across models (26.8 points at 3 bits). A quarter of conditions have an inestimable slope.
- Authors disclose model-assisted analysis that produced at least one error caught late. Independent corroboration of the law itself: none read (qnoise shows concentration of flips at low confidence only).

## 9. read_depth
PARTIAL: abstract, sections 1-7 (through the forecast, conclusion, limitations), the KV-cache grid summary in an appendix, and the A.4 heading; appendices A.1-A.22 detail, figures and per-model tables not read. lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit
artifact audit: clean
