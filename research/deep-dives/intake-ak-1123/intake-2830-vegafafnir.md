# Dive — vegafafnir — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2611.27554v1", retrieved: "2026-11-23", sha256: "950a1a67866c" (paper.pdf; no HTML render exists, so there is no page.txt)}

Read method: `paper.pdf` (27 pages) was text-extracted locally with a cached pypdf 7.1.0 (the Read tool could not render PDF pages because poppler is missing on this host). The extracted text sits in the session scratchpad only. Every quote below comes from that extraction, keyed by PDF page, and still needs a hand-check against the PDF. Some words in the extraction carry ligature glyphs (ﬁ, ﬀ); I chose quotes that avoid them.

## 1. Stage-1 fields

- **Title**: Vega-Fafnir: Is Greedy Decoding the Same Decoding? Where Rounding Noise in Speculative Verification Comes From and What Removing It Costs
- **Authors**: Mohammed Nayeem Khan, Navin Kumar R (Intel Corporation)
- **Version**: v1, 19 November 2026, arXiv cs.AI (cross-list cs.CL, cs.LG), PDF p.1
- **Categories**: speculative_decoding, benchmark_methodology, inference_serving, local_inference
- **Novelty**: medium. Prior work already shows that batch shape changes bf16 greedy output (the paper's own related work cites arXiv:2506.09501, 2605.14220 and 2510.22876). Three parts are new: the batch-1 measurement against a width-1 reference, the teacher-forced split into query-shape noise and cache noise, and the stale-cache vs rebuild comparison of margin gates. For us the novelty is low. In-house INF-70 already found the same mechanism and the same stale-fallback failure on CPU (section 5).
- **Relevance**: high. Production is always speculative, and our correctness gates repeatedly compare token identity across arms that change the verify width. The paper predicts that some of these arms will fail identity on near-ties with no defect present, and section 5 lists lane cases where this has already happened.
- **credibility_score**: 2. Arithmetic: not peer-reviewed (0); 4 days old, so within 12 months (+1); I do not count the Intel Corporation affiliation as a major-lab byline for this two-author note (0); no commercial bias (0); independent corroboration of the mechanism from in-house measurements, INF-70 BATCH-ENVELOPE and E2a in cpu-decode-roofline-program.md (+1). The VERGE abstract found by web search was not read, so I do not count it.
- **Verdict**: adopt_patterns. We already own the mechanism and much of the remedy: the `LLAMA_SPEC_EXACT` modes, the opt-in `GGML_ROWEXACT_N` row-exact kernels, the `GGML_DETERMINISTIC` test knob and the statistical identity protocol. The paper adds three patterns worth adopting: (a) a teacher-forced noise statistic S that calibrates the near-tie bound τ, instead of the fixed 0.05 nat we use now; (b) the "kernel group" model, which predicts which A/B arms will flip; (c) the evidence that any width-1 fallback reading a wide-written cache is not exact. Nothing in the paper is a component we would ship.

## 2. Key claims

0. **Verify-4 changes 60% of 150 prompts and padding changes 68%: CONFIRMED.** Qwen3-0.6B bf16, 128 new tokens. Exact counts are 90/150 and 102/150; batch-of-4 changes 104/150; a rerun of the reference changes 0/60.
   - PDF p.1: "Verifying 4 guessed tokens per pass changes 60% of 150 prompts and padding changes 68%"
1. **Every first divergence has a top-1/top-2 gap of at most 0.375: CONFIRMED, with scope.** The gap is the reference margin, pooled over three paths (296 first divergences from 127 prompts). The median is 0.125, and 99.7% are at 0.25 or less. Logits sit on the bf16 grid (0.125 apart between 16 and 32), and 39.2% of first divergences are exact bf16 ties.
   - PDF p.9: "with a median reference margin of 0.125, a maximum of 0.375 and 99.7% at 0.25 or less"
2. **Margin gate 58/100 vs 61/100 for plain verification: CONFIRMED (stale-cache gate, eps = q99 = 0.375, McNemar p = 0.664).** Even an oracle trigger over the stale cache leaves 49/100 different.
   - PDF p.2: "Margin gate with a stale cache (eps = q99): 58.0% [48.2, 67.2] (58/100)"
   - PDF p.15: "Even a perfect trigger cannot repair a width-1 pass that reads"
3. **One-token cache rebuild gives 0/100 at 7.2 passes per token: CONFIRMED (7.24, against 1.00 for the reference and 0.75 for plain verification).** The cheapest exact bound, eps = 0.125, costs 3.55 passes per token. Every exact variant costs more than plain decode.
   - PDF p.1: "costs 7.2 model passes per token, against 1.0 for the reference"
   - PDF p.15: "smallest bound that left no divergence is eps = 0.125"
4. **Fixed-width decoding gives 0/100 at 0.75 passes per token: PARTIAL (the steering framing is wrong).** The 0/100 compares drafted fixed-width-5 decoding against plain fixed-width-5 decoding. Both still differ from the width-1 reference on 66/100. Fixed shape makes speculation consistent with itself, not with plain decode.
   - PDF p.2: "Fixed-width 5 decoding, drafts against plain: 0 of 100 prompts"
   - PDF p.25 (Conclusion): "at 0.75 passes per token, which is one way to keep speculation lossless"
5. **"Method hardware-agnostic": OVERTURNED as stated.** The measurement method is portable, but the authors say the width groupings and every rate are properties of one RTX 4090 with PyTorch 2.11 and transformers 5.20. In their width scan, widths 2–3 share kernels and widths 4–6 share kernels, and width 1 shares none with any wider width.
   - PDF p.4: "is loaded with transformers 5.20 and PyTorch 2.11 on one RTX 4090"
   - PDF p.24: "Which widths share a kernel is a property of that stack"
   - PDF p.18: "Widths therefore fall into groups that share a kernel, and a width-1 pass shares none with a wider pass."

## 3. Reported results (as the source states them)

Setup: one RTX 4090 shared with about eight other jobs; Qwen3-0.6B bf16 (Qwen3-1.7B as a replication); transformers 5.20, PyTorch 2.11, SDPA, TF32 off; greedy, 128 new tokens; GSM8K and ARC evaluation prompts; prompt-lookup drafts (n-gram up to 3), k = 4.

- Divergence from the width-1 reference: verify-4 90/150 (60.0%); padded-to-64 102/150 (68.0%); batch-4 104/150 (69.3%); reference rerun 0/60.
- 32.0% of prompts had diverged by position 64, against 60.0% by position 128, so the rate grows with length. By source: GSM8K 41.1%, ARC-Easy 81.4%, ARC-Challenge 73.5%.
- Noise split (42 calibration prompts, 5253 positions): mean S is 0.078 for the wide query over the reference cache, 0.117 for the width-1 query over the wide cache, and 0.120 for both. Argmax flips are 40, 42 and 37.
- Gates (eps = q99 = 0.375 unless stated), as share of prompts differing and target passes per token:
  - stale 58/100, 0.86
  - chunk 32/60, 0.88
  - rebuild-16 19/60, 2.37
  - rebuild 0/100, 7.24
  - rebuild with eps 0.125: 0/100, 3.55
  - rebuild with eps 0: 15/45, 1.59
  - oracle stale 49/100, 1.02
  - oracle rebuild 0/30, 1.24
- Fixed width 5: drafts vs plain 0/100; each differs from the reference on 66/100; drafted runs cost 0.75 passes per token, plain 1.00.
- Width scan (20 prompts, 2459 positions): no wider width is bit-identical to width 1. Widths 2 and 3 are identical, and widths 4, 5 and 6 are identical. Width 8 matches width 5 at 65.4%; widths 12, 16 and 32 match at 0.0%.
- Shifted MMLU/HellaSwag prompts: plain verification 48/60 differ; stale gate 41/60; rebuild 0/60 at 10.71 passes per token.
- Bound coverage: flips missed by the q99 bound were 0 of 37, 0 of 162 and 0 of 147.
- float32 check: the bf16 reference disagrees with float32 at 34/5380 positions, and the verify pass at 24/5380. The reference is not the more accurate path.
- ARC answer letters changed in 2 of 192 differing prompt-path pairs.
- Wall clock (context only, 12 prompts, shared GPU): verify-4 0.71x of the reference's time per token; fixed-width-5 with drafts 0.68x; rebuild gate 6.13x.

## 4. Performance-principles table (mechanism and cost model)

Each principle is assessed for transfer to the MI210 (gfx90a) and to the Zen 5 EPYC CPU.

**P1. Rounding depends on the pass width (kernel groups); width 1 shares no kernel with verify widths.**
- MI210: YES. C19 dispatches on width throughout the verify path. `GGML_HIP_MMVF_CDNA_MAX_NE11` defaults to 8 (`e6c7bf11e`). GDN K=1 runs the rows kernel while K=T runs the fused kernel (`fe8016395`, `40e9e146b`). FA picks GQA_VERIFY for 2–16 rows and VEC for n_q = 1 (speculative-decoding.md:2394). Different kernels for width 1 and for verify widths imply shape-dependent rounding.
- Zen 5: YES, already measured in house. INF-70 BATCH-ENVELOPE found two carriers. The F32 tinyBLAS mul_mat is tiled at ne11 ≥ 2 but runs generic vec_dot at ne11 = 1 (MoE router). CPU FA stops being row-exact at n_kv > 256 (cpu-decode-roofline-program.md:4262-4290). iqk also has Ny-specialised kernels (`iqk_mul_mat.cpp:58-63 @ a6a32c1`).

**P2. Cache or state entries written by wide passes carry noise that a width-1 fallback inherits.**
- MI210: YES by the same mechanism (KV written by the verify pass; GDN state written by the batched kernel). Not measured on GPU in house.
- Zen 5: YES, measured. INF-70 E2a: `LLAMA_SPEC_EXACT=drop` failed identity on 2/3 prompts and `redecode` on 0/3 passed, "every failure is at a VERIFIED row"; only `serial` was 3/3 exact (cpu-decode-roofline-program.md:4107-4117). This is the paper's stale-fallback result, found two months earlier.

**P3. Margin gate plus full width-1 cache rebuild gives exactness at more than 1 pass per token.**
- Both devices: NO for serving. Even the oracle rebuild costs 1.24 passes per token, above plain decode, so it is a test oracle only. In-house equivalents already exist: the `serial` mode at `server-context.cpp:42-60 @ a6a32c1`, and the fresh-prefill oracle used by the DTREE gates.

**P4. Fixed-shape decoding (pad every pass to W) makes speculation self-consistent at no extra passes.**
- MI210: PARTIAL. On the 27B, every padded row costs verify time (the lane treats the verify slope as at least about 1 ms per row, speculative-decoding.md:895). Padding plain or zero-draft steps to W is therefore not free, and it buys reproducibility only. It does not buy equality with plain decode.
- Zen 5: PARTIAL. Decode is bandwidth-bound, so a few extra rows are cheap (uncited general reasoning). The in-house `GGML_ROWEXACT_N` is strictly better, because it makes verify rows bit-equal to the width-1 reference. Its measured cost is MTP n-max 4 22.93 → 21.56 t/s (−6.0%), with the trunk free (`ggml-cpu.c:1710-1727 @ a6a32c1`). Both are opt-in; ROWEXACT defaults to 0.

**P5. Teacher-forced noise statistic S (largest rival lift) with a held-out q99 bound.**
- Both devices: YES, code and measurement only. The reference tokens can be teacher-forced as one batch at width 1 and again at width W in llama.cpp. S calibrates the near-tie τ in the identity gate.

**P6. Tie-breaking at exact ties (39.2% of their first divergences).**
- Both devices: PARTIAL. Their logits were stored in bf16, which makes exact ties common. Our logits are f32, so exact ties should be far rarer (uncited reasoning). C19 `9c891b455` already aligns CPU argmax, HIP argmax and the host scan on the first maximum (`ggml/src/ggml-cpu/vec.h:1673-1682 @ a6a32c1`). The paper explicitly did not study tie-breaking.

## 5. In-house state

- **The mechanism is known and named in code.** `tools/server/server-context.cpp:42-77 @ a6a32c1` (INF-70 E2a) describes a target "whose multi-token forward is not row-exact against its single-token forward". It offers the modes drop, redecode, serial, row, and batched-greedy-inexact (the last is a measurement instrument).
- **Row-exact CPU kernels exist.** `ggml/src/ggml-cpu/ggml-cpu.c:1505-1519` and `:1708-1754`, plus `iqk_mul_mat.cpp:58-63 @ a6a32c1`. The compiled default is 0, so the opt-in knob is off in serving.
- **GPU run-to-run noise is attributed to unordered float atomics, not to shape.** Sources are Q8_MF V5 and the q8_skinny split-K. Under `GGML_DETERMINISTIC`, A/A is 0/16, against 7/16 with the knob off, at 2.4x cost (docs/design/spec-decode-run-nondeterminism-20261122.md §5a, L159-168 @ d785b6d). The design doc already states the paper's conclusion: "Deterministic mode makes **A/A** exact. It cannot make **A/B** byte-identical" (L83). It replaced single-sample identity with a statistical tie/defect protocol (L86-101).
- **Gap the paper exposes.** Our τ is a fixed 0.05 nat or 2x the largest A/A margin (L93). The paper calibrates the bound from teacher-forced S on held-out prompts, and that bound missed 0 of 346 held-out flips. We have never measured S on our stack.
- **Lane identity results the paper explains as A/B shape effects, not defects:**
  - DF2-13-ATTRIB (`df2-13-attrib-bisect-gpu-20261121`): CULPRIT_NMAX1+EXACT+SPEC_PATH+NEAR_TIE_ONLY. The run was deterministic with n-max 1, with EXACT=serial, or with spec off; all 4 baseline divergent pairs were near-ties (progress/2026-11/2026-11-22-handoff-df2.md:19).
  - COPYSPEC-NO-DIVERGENCE: the ngram-only control diverged on 32/85 prompts. That server ran a different recurrent-state configuration (n_rs_seq = 0, checkpoint restore plus re-decode) and had width-1 rounds; the cause was attributed to fp near-ties (artifacts/copyspec-20261006/NO_DIVERGENCE.md).
  - SPEC-RNG.1.1: np1 vs np4 diverged on 7/8 and depth 0 vs 3 on 6/8, all from batch-shape drift (speculative-decoding.md:641-643).
- **Gates the paper predicts will fail with no defect present:**
  - CAFE-1 declined p-min 0.5/0.75/0.9 on "100% greedy identity" alone (4/15, 6/15 and 5/15 matched vs baseline 15/15; speculative-decoding.md:505-507). p-min trims drafts, which moves rounds into other width groups, including width 1.
  - CAFE-3's done-when still requires "identity 100%" against the best static width (speculative-decoding.md:523). An adaptive width controller changes the verify width by design.
- **Served path.** Production runs speculative decoding at temperature 0.1–0.3 for most roles (orchestration/model_registry.yaml L2256-3011 @ orchestrator 1a10541b; worker_math 0.0). Greedy identity is therefore a test instrument, not a serving property.

## 6. Derived-actionables ledger

**A1. Calibrate the identity-gate tie bound from S.**
- Task: Measure the teacher-forced noise statistic S (width-1 vs widths 2, 4, 8 and 16 over the same reference tokens) on 27B Q8_0 + DFlash2 on the MI210, with `GGML_DETERMINISTIC=1` so the atomics noise is excluded, and on Q38FN on CPU. Then set the identity-gate τ from the held-out q99 of S.
- Owner: speculative-decoding.md (INF-50; DF2-12.1 owns the near-tie rule, and CH-37 at kernel-champion-and-promotion.md:617 defers to it). Exists, not frozen.
- Compute: one GPU row plus one CPU row (CPU q0-q2), teacher-forced only, about 8 prompts × 256 tokens per width.
- Stop rule: question = what bound covers 99% of shape-only noise on our kernels? Stop when q99 and q999 are stable within 10% between two prompt halves. If the GPU q99 is below 0.05 nat, keep the current τ and close.

**A2. Re-judge the CAFE-1 decline.**
- Task: Re-judge CAFE-1's p-min decline under the §3 tie/defect protocol, using the retained runs. Each first divergence needs its top-2 margin; if the raw responses lack logprobs, re-run only the divergent prompts with `n_probs: 2`.
- Owner: speculative-decoding.md (CAFE-1 is ticked; record the re-judgement as a note under it, and open a child box only if the verdict changes).
- Compute: CPU row, only if logprobs are missing.
- Stop rule: question = were the p-min identity failures near-ties? If every divergence is a tie, the p-min values return to a speed-only decision. If any defect appears, the decline stands.

**A3. Fix CAFE-3's identity criterion before its P9 runs again.**
- Task: Replace "identity 100%" in CAFE-3's P9 done-when with the §3 protocol (zero defects, and the ON-vs-OFF rate within the A/A rate plus its Wilson bound). Alternatively, run P9 with `GGML_ROWEXACT_N ≥ 4·(n_max+1)` on CPU so that width changes become row-exact.
- Owner: speculative-decoding.md CAFE-3 (owner workspace-ec; the integrator prepares the text and the owner applies it).
- Compute: code/doc-only.
- Decision: answers whether an adaptive-width controller can pass P9 at all. Under strict identity the paper predicts it cannot.

**A4. Dose-response test of the GDN state-write path on the 27B GPU.**
- Task: Add to the DF2-13-ATTRIB follow-up a GPU arm that separates query-shape noise from noise in state written by the verify pass. Use `LLAMA_SPEC_EXACT=redecode` against `serial` on 27B DFlash2 under `GGML_DETERMINISTIC=1`. This repeats E2a on the MI210.
- Owner: speculative-decoding.md (DF2-13 track).
- Compute: GPU row (fresh server per arm, 8 prompts × 128 tokens).
- Stop rule: question = does a width-1 fallback over a verify-written GDN state flip as often as plain verify on HIP? It is answered when redecode-vs-plain divergence is within ±1 prompt of verify-vs-plain (cache noise dominates) or at 0 (it does not).

**Declines (each with an entry-specific reason):**
- Margin gate with rebuild for serving: declined. Every exact variant costs ≥ 1.24 target passes per token (oracle trigger), above plain decode, and production samples at T > 0, where greedy bit-identity has no serving value.
- Fixed-shape decoding for serving: declined. It does not match plain decode (66/100 differ), and ROWEXACT already gives width-1 exactness on CPU at a measured 6%.

## 7. Dive-surfaced sources (none in the intake index; grepped unbounded)

- **VERGE**, "Verifier Execution Regimes Break Greedy Equivalence in Speculative LLM Serving" (NeurIPS 2026 listing, https://neurips.cc/virtual/2026/178991). A web-search snippet reports 53.55% of 592 prompts diverging by token 128; I did not read the page, so that figure is unverified. It would settle whether the 60% rate replicates on a second stack and engine. Recommendation: ingest-and-dive. It is the only candidate independent replication.
- **LLM-42**, arXiv:2601.17768 (fixed-shape verify-rollback for determinism). Its cost figures for batch-invariant kernels (up to 63% GEMM throughput, 56% end-to-end) bear on any GGML_DETERMINISTIC-style knob, our 2.4x cost and the GGML-DETERMINISTIC-REDUCE-SCRATCH box. Recommendation: ingest-and-dive.
- **arXiv:2510.22876**, batch speculative decoding correctness forensics (95% exact match at batch size 8). It bears on DF2-12.1 np4 parity. Recommendation: ingest-and-dive.
- **arXiv:2605.14220** (training-inference mismatch; batch-invariant kernels with KV splitting disabled). Recommendation: decline for now. It is an RL-pipeline focus, and our KV-split determinism question is already covered by the design doc.
- **arXiv:2506.09501, 2605.19537, 2601.15498 (MARS), 2608.03447, 2510.26788, 2405.02803, 2606.30265.** Recommendation: decline. They are cited background whose claims this dive does not rest on. 2606.30265 is exact-arithmetic theory, and MARS and 2608.03447 are lossy-verification methods outside the identity question.
- **HTML companion**: none found. The paper names no repo or project page (its scripts are local `a15b_*.py`), and a web search for "Vega-Fafnir" returned no companion.

## 8. Contradiction / adversarial pass

- **Authors' own limitations (PDF p.24-25):** one GPU and one stack; a 0.6B main model; prompt-lookup as the only drafter; 128 tokens; greedy only; the bound set on 42 prompts; zero differences in 100 prompts is consistent with a true rate of up to about 4%; pass counts are a lower bound on cost; ties were not examined; the text was LLM-assisted.
- **Scale caveat for us.** Their margins sit on a bf16 logit grid (step 0.125). Our llama.cpp logits are f32 with Q8_0 weights, so the absolute bound (0.375) does not transfer. Our measured A/A divergence margins are 0.006–0.19 nat (design doc §5a). Only the method transfers.
- **Their divergence rate mixes deterministic shape effects with nothing else.** The reference rerun was 0/60. Our GPU additionally has run-to-run atomics noise, so an A/B identity gate here combines two sources. The paper does not cover that case.
- **Contested framing.** "Fixed-width decoding makes drafted and plain decoding identical" is true only within width 5, not against width-1 decoding (claim 4).
- I found no reviewer pushback or failed reproduction. VERGE (unread) appears to report a similar rate; that is possible corroboration, not yet a check.

## 9. read_depth

PARTIAL. All 27 pages were read through text extraction. Figures 1–26 were not viewed as images (only captions and in-text numbers were used). Anchors cannot be machine-verified because no page.txt exists, so the entry stays `stage1-unverified`. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## 10. Artifact audit

artifact audit: clean, with one note. paper.pdf (sha256 950a1a67866c…) parsed to 27 pages; there is no page.txt by design. Quotes were taken from the pypdf extraction and need a hand-check against the PDF.
