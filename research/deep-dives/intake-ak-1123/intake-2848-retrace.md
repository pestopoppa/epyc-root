# Dive — retrace — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/pdf/2608.29748v2", retrieved: "2026-11-23", sha256: "ab5f5989bbcd"}

Note: the sha256 above is of `retrace/paper.pdf` (13 pages, 1,189,944 bytes); there is no page.txt because arXiv has no HTML render for this paper. I extracted text with pypdf 7.1.1 into `retrace/paper.extract.txt` (reading material only; anchors below come from that extraction and need a hand-check against the PDF). Hyphenation artefacts from line breaks are avoided in the quotes.

Bearing entry: intake-2832 (copyro). Surfaced by the copyro dive §7 ("ReTrace (Lin et al. 2026; conditions DFlash on the previous round's rejected suffix)"). Found by web search; the arXiv abs page (fetched 2026-11-23) gives the title "ReTrace: Rejected-Trajectory Conditioning for Speculative Decoding", v1 30 Aug 2026, v2 5 Sep 2026, cs.CL, no code link. The PDF's own header reads "Date: September 9, 2026"; I use the arXiv v2 date.

## 1. Stage-1 fields
- **Title**: ReTrace: Rejected-Trajectory Conditioning for Speculative Decoding
- **Authors**: Luxi Lin, Zhanpeng Zeng, Shuang Peng, Songwei Liu, Rongrong Ji (Xiamen University; ByteDance)
- **Version**: v2, 5 Sep 2026, cs.CL. Code: none listed on the abs page.
- **Categories**: speculative_decoding, training_distillation
- **Novelty**: medium-high. It reuses the hidden states of the drafts that follow the first rejection to condition the next draft block, through a learned gate, with target-side correction taken from the same verification pass. Token Recycling reuses discrete token transitions; Lyanna (named in the paper) redesigns the drafter to resample from reusable states. ReTrace feeds states to the next ordinary block.
- **Relevance**: medium. It acts on our served drafter family (a block drafter on the 27B), is orthogonal to CoPyro's proposal inputs, and is the larger reported effect of the two on a DFlash backbone. It needs training, so it can only enter through DF2-FT-1.
- **credibility_score**: 2. Not peer-reviewed (0); about 2.6 months old (+1); ByteDance co-affiliation (+1); no commercial bias claim (0); no independent replication and no released code (0). Total 2.
- **Verdict**: worth_investigating. The mechanism is sound by construction (input-side only, lossless) and the reported gains persist at T = 1 and under concurrency, but the paper evaluates DFlash-b16 on Qwen3-4B and 8B only, trains for 8 epochs on 32 GPUs, and says nothing about a headless selector-lattice drafter like ours.

## 2. Key claims
0. **Mechanism: CONFIRMED.**
   - After a round, keep the final-layer drafter states for positions strictly after the first rejected one, shift them to the start of the next block, add a target-aware correction `W_c [m; u]` (u is the target's final-layer state from the same verification pass), and admit the result into the mask-token input embeddings through a vector gate, `e + W_v r * sigmoid(W_g [e; r])`. `W_v` is zero-initialised, so training starts from plain DFlash. The signal lives for one round and is reset on a fully accepted block. Verification is unchanged, so the method is lossless.
   - Anchors: Abstract "Because rejected tokens are never committed and target-side verification remains unchanged, ReTrace preserves the lossless property of speculative decoding"; Method "The conditioning lasts for one round"; Method "so the residual vanishes at initialization".
1. **Gains over DFlash: CONFIRMED, with a narrow caveat.**
   - Table 2 (Qwen3-4B and 8B, DFlash-b16 backbone, block 16): average acceptance length rises in every one of the 28 benchmark cells at both temperatures; macro averages over the four model-temperature settings are +6.97% in acceptance length and +5.34% in speedup. I recomputed: mean of per-setting ratios is +6.97% (τ) and +5.55% (speedup); the paper's +5.34% is the ratio of averaged speedups (13.81 against 13.11).
   - Speedup does not rise everywhere: Qwen3-4B, T = 1, Alpaca goes from 1.45x to 1.44x while τ rises from 3.43 to 3.56.
   - Temperatures tested are 0 and 1 (top_p 0.95, top_k 20 at T = 1). Nothing at 0.1-0.3, our production range (NOT-FOUND-IN-SOURCE).
   - Anchors: Table 2 rows "DFlash (16) 3.37× 6.36 5.18× 8.25 ..." and "ReTrace (16) 3.73× 7.36 5.47× 8.88 ..."; Main Results "average acceptance length by 6.97%".
2. **Training is required and heavy; there is no training-free path: CONFIRMED.** Initialised from the public DFlash-b16 checkpoints, trained on a 40K-prompt pool for 8 epochs on 32 A800 40GB GPUs, with the drafter backbone trained jointly with the new modules. Zero-initialised `W_v` gives identity at step 0, so an untrained insertion gains nothing. How the rejected rounds are produced during training (online rollout with the drafter in the loop, versus precomputed) is only described as "cached draft and target representations are detached before being reused in the next decoding round" (NOT-FOUND-IN-SOURCE for the rollout procedure). Anchors: Appendix B "ReTrace is trained on a prompt-only pool of 40K"; Appendix D "Training runs on 32 NVIDIA A800 40GB GPUs across four eight-GPU nodes."; Table 7 "Training epochs 8".
3. **Overhead and batching: CONFIRMED, different realisation under batching.** On one A800, Qwen3-4B, batch 1, context 1,024: conditioning costs 0.13 ms per cycle (0.40% of the 32.49 ms DFlash cycle); τ 6.36 to 7.36 and speedup 3.37x to 3.73x on GSM8K. Under SGLang concurrency 1 to 32 the gain persists (1.62x against 1.50x at 32), but that run uses a low-rank realisation (rank-64 latents, rank-32 correction), not the main one. Anchors: Table 4 "Conditioning overhead (ms) – 0.13"; Table 8 row "32 0.80× / 3.31 0.42× / 3.69 1.50× / 6.45 1.62× / 7.42".
4. **The rejected suffix carries a bounded predictive signal: CONFIRMED (bounded).** Under greedy decoding with Qwen3-4B and DFlash-b16, cumulative coverage of the true target token by draft rank beyond the first rejection is 30.4% at rank 1, 53.5% by rank 2, 75.2% by rank 5 and 86.4% by rank 10 (Figure 2, read from the extracted labels); cosine similarity of rejected draft states to the true target trajectory is 0.351 on average against 0.128 for random windows (Table 1). The authors conclude the suffix is not reliable enough to accept or copy, only to condition on. Anchors: Table 1 "True trajectory 0.396 0.330 0.307 0.371 0.351"; Table 1 "Random 0.171 0.121 0.105 0.115 0.128"; Predictive-signal section "The rejected suffix is therefore not reliable enough to accept or copy directly".

## 3. Reported results
- Setup: Qwen3-4B and Qwen3-8B targets, official DFlash-b16 as backbone baseline and EAGLE-3 as a reference; GSM8K, MATH-500, AIME25, HumanEval, LiveCodeBench, MT-Bench, Alpaca; one request at a time, block 16, at most 8,192 new tokens, thinking off; T = 0 (top_k 1) and T = 1 (top_p 0.95, top_k 20), seed 42; speed against vanilla autoregressive on the same model. Hardware for the latency table and concurrency study: NVIDIA A800.
- Table 2 averages (speedup / τ): Qwen3-4B T = 0 DFlash 3.74x / 6.41, ReTrace 3.93x / 6.85; Qwen3-8B T = 0 4.05x / 6.35 and 4.22x / 6.79; Qwen3-4B T = 1 2.49x / 5.52 and 2.68x / 5.91; Qwen3-8B T = 1 2.83x / 5.41 and 2.98x / 5.79.
- Table 3 (Qwen3-4B, greedy, mean τ / speedup over four benchmarks): no conditioning 6.45 / 3.67x; overwrite 6.51 / 3.68x; raw gated 6.79 / 3.80x; corrected gated 6.90 / 3.86x.
- Figure 4 (figure-only): an SFT control that continues DFlash training with the same data and budget saturates marginally while ReTrace keeps rising, so the gain is not extra training.
- Table 5: ReTrace on Domino, throughput 287.17 to 301.39 tok/s and τ 7.43 to 7.79 (macro, greedy, 1,024 tokens).
- Table 8 (Qwen3-4B GSM8K, SGLang, A800, low-rank variant): at concurrency 1/2/4/8/16/32 ReTrace 3.73x / 3.49x / 3.15x / 2.56x / 2.01x / 1.62x against DFlash 3.37x / 3.20x / 2.89x / 2.38x / 1.83x / 1.50x.

## 4. Performance-principles table
| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| Cross-round state carry: FP16 states for B positions kept per sequence for one round | YES. Memory is B x d per sequence (negligible); the open item is exporting the drafter's pre-selector hidden states, which the drafter graph does not output today (§5). | NO consumer. Block drafters are not served on CPU; CPU speculation is MTP. |
| Correction and gating modules (W_c 2d x d, W_v d x d, W_g 2d x d) | PARTIAL. Full rank at the 27B drafter's width (d = 5120 inferred from the drafter's 25600 to 5120 projection) is 5d^2, about 131M parameters, roughly 7% of a 1.9B-parameter drafter that is read once per round (my arithmetic); the paper's own low-rank realisation (ranks 64 and 32, used in its concurrency study) avoids that; the 0.13 ms per cycle in Table 4 is measured on an A800 at Qwen3-4B width, and I did not extrapolate it to d = 5120. | NO consumer. |
| Gated residual injection into input embeddings (elementwise sigmoid gate) | YES. An elementwise epilogue on the embedding load; no new kernel class. | Not applicable. |
| Training: joint drafter fine-tune with cross-round detached states | NOT a hardware principle. It needs a loop of draft, verify, carry during training, which offline per-token feature dumps cannot provide (§5). | Not applicable. |

## 5. In-house state
- **No cross-round reuse exists.** Each DFlash2 round decodes a fresh block of mask tokens: `common_batch_add(batch, i == 0 ? dp.id_last : mask_token_id, ...)` (common/speculative.cpp:1760 @ a6a32c1). The drafter's output is the selector lattice (`llama_get_embeddings_nextn(ctx_dft)`, speculative.cpp:1790-1800), not a hidden state; a grep of speculative.cpp for rejected-suffix reuse finds nothing relevant.
- **Target side of the signal is already in the FT-1 contract.** DF2-FT-1's feature dump writes the five target taps plus the target post-norm final hidden, 61,440 B per row (speculative-decoding.md:2250 and the 2026-11-18 note @ d785b6d), which covers ReTrace's `u`. The drafter-side `m` is not captured by any tool I found.
- **Drafter facts that differ from the paper's.** The served 27B DFlash2 is headless with block size 8 (the copyro dive; kernel-champion-and-promotion.md:196) and a selector lattice of top-16 candidates with predecessor-conditioned scores; the paper's DFlash-b16 has block 16 and plain token logits. At the production :8083 shape the drafter accepts 0.29-0.39 on temp-1 agentic traffic (speculative-decoding.md:2250), so the rejected suffix is long in our traffic.
- **Training shape in FT-1.** The reference trainer is offline-feature (`train_df2.py`) with CE, KL and top-16 selector losses (speculative-decoding.md 2026-11-18 note). ReTrace's training needs the drafter's own states from its previous round, so FT-1 would need an on-policy round loop or a detached approximation, not just precomputed features.
- **Served path does not reach it.** Nothing in the registry or champion carries it; DF2-FT-1 is open and has not started training.

## 6. Derived-actionables ledger
**R1. Offline signal probe on the existing DTREE dump (refines intake-2832 A2; gates R2).**
- Task: On the 27B capture `ak-dtree-dump-gpu-20261120` (545 rounds, DFlash2 lattice D7 x K plus target token streams), for positions after the first rejection in each round, report the rank of the realised target token among the top-16 lattice candidates (cumulative at ranks 1, 2, 5, 16) and compare with ReTrace's Figure 2 values for DFlash-b16 (30.4%, 53.5%, 75.2%, 86.4% at ranks 1, 2, 5, 10).
- Owner: speculative-decoding.md DTREE-TREE-QUALITY capture family (a child under the ticked box) or the DF2-FT-1 prep notes.
- Compute: code-only, CPU seconds; reuses `/mnt/raid0/llm/tmp/ak-dtree-dump-gpu-20261120/sim/tree_sim.py`. If the dump does not align positions beyond the first mismatch, one replay-mode capture with the FT-1 feature-dump tool.
- Stop/decision rule (predeclared judgement, not from the paper): question = does the rejected suffix of our drafter retain the token-level signal ReTrace exploits? If rank-1 coverage beyond the first rejection is under 10% (a third of the paper's 30.4%), drop ReTrace; if at least 20%, carry it into R2. This tests the token signal only; the hidden-state alignment (Table 1) needs the drafter-side export.

**R2. Add a ReTrace arm to the DF2-FT-1 design (refines intake-2832 A2; doc-only until R1 passes).**
- Task: Record in the DF2-FT-1 arm list, beside CoPyro's inputs, a ReTrace arm (gated conditioning on the previous round's rejected-suffix states, zero-initialised `W_v`), with three facts for the design: the cheapest variant is the raw gated one (Table 3: τ 6.79 against 6.90 for the corrected one, 76% of the corrected gain over 6.45), its training needs an on-policy draft-verify-carry loop that the offline-feature trainer lacks, and a drafter-side hidden-state export from the DFlash2 graph is missing.
- Owner: speculative-decoding.md DF2-FT-1 (open; the owning session applies).
- Compute: training rides the DF2-FT-1 budget; one serving A/B row at np1 and np4.
- Stop rule: KEEP iff tok/s CI-lower is above 1.0 against the plain re-aligned drafter at np1 and np4 and τ gain is at least 1% (same keep rule as intake-2832 A2). DROP if R1 fails.

**Does it change intake-2832 A1 or A2?** A1 (training-free copy-proposal probe) is unaffected: ReTrace has no training-free path. A2 changes shape: CoPyro's inputs are data-precomputable (retrieval over token streams), ReTrace's depend on model state; they are separable, orthogonal arms of the same fine-tune, and the factorial design is {plain re-aligned, +CoPyro, +ReTrace, +both}. Separately reported effect sizes (CoPyro +1.08-2.00% acceptance length per the copyro dive; ReTrace +6.97% here) are on different backbones and training budgets and are not combined.

**Declines.** None for ReTrace itself. Training cost is not a decline reason and the paper's own low-rank variant shows a cheaper deployment form.

## 7. Dive-surfaced sources (grepped unbounded: 2608.29748, "ReTrace", "Make Every Draft Count", "Lyanna", "JetFlow")
- Lyanna, "Make Every Draft Count" (the paper's [5], not in the index): decline. It redesigns the drafter and resamples candidates that must be verified again; it would change no row of R1 or R2.
- JetFlow (parallel tree drafting): already referenced in the index (1 hit); no new action.
- Domino and DFlash: already in the index; ReTrace's Table 5 shows composition with Domino, consistent with the lane's existing Domino note (speculative-decoding.md SPEC-5 trigger).
- Not in the intake index as of 2026-11-23: arXiv 2608.29748 (0 hits).

## 8. Contradiction / adversarial pass
- Single backbone family and scale (Qwen3-4B and 8B, DFlash-b16, block 16); no 27B-class or headless selector drafter; no temperatures between 0 and 1; no released code; no independent replication.
- Baseline fairness: the controlled comparison is the SFT continuation (Figure 4, figure-only); the headline table compares against the official DFlash checkpoint, not the SFT-continued one.
- The authors state the signal is imperfect: moderate absolute similarity (0.351) and token coverage of 30.4% at rank 1; the suffix is conditioning, not a proposal.
- Concurrency evidence uses a different (low-rank) realisation from the main results.
- Restatement note: the copyro dive described it as "training-light"; the appendix shows 8 epochs on 32 GPUs. The dive's description of it as a competing DFlash input change is correct.

## 9. read_depth
PARTIAL: all 13 PDF pages were read through pypdf text extraction only; Figures 1-4 were not viewed as images (labels and captions only), and no HTML render exists, so anchors cannot be machine-verified against a page.txt (entry stays stage1-unverified; quotes need a hand-check). lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## 10. Artifact audit
artifact audit: clean, with one note. paper.pdf (sha256 ab5f5989bbcd...) parsed to 13 pages; there is no page.txt by design. Quotes were checked against the whitespace-normalised extraction, not against the PDF itself.
