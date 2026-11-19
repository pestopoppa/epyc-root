# XPress (arXiv 2608.02438v2) Stage-2 dive, intake-2665

- read_depth: FULL (whole LaTeXML text from disk, including Tables 1-3, Props 1-2, Sec 4.3). Figures 3 and 4 are images and were read only through their captions and body prose.
- version: v2 (26 Oct 2026). Raw html sha256 `cf5d8f06cccf2d6560768c0a2f0b2b3ac123a0207fdf5dece10fd5610823dbca`.
- Companion code read, not executed: github.com/Supercomputing-System-AI-Lab/xPress @ `4718c90b5885dbdf83048c045431f47a834b4251` (committed 2026-10-23). Also read: speculators `examples/train/xpress_qwen3_8b_regen_online.sh` and `docs/user_guide/algorithms/xpress.md` (main branch, unpinned), and the HF model list for UIUC-SSAIL.
- In-house source read at `ffc1bac82`: `src/models/dflash.cpp` (`build_post_sampling`), `common/speculative.cpp:1640-1710`.
- Lane snapshot origin/main `ad1e73525f6b86077936d9a1065f4da35c27c9d5`.

## Bottom line for the three questions asked

1. **Does parallel refinement add drafter passes? No.** The backbone runs once; `h` and `g` are fixed across iterations. K passes are of the refiner head only. On MI210 the refiner lands on the critical path, but it is a small add (estimate 0.5-2 ms on a 78.2 ms busy round). Caveat: `K << B` is a block-16 claim. At our block 8, K=6-7 is essentially B-1, so the "parallel" advantage over a serial sweep disappears.
2. **Does it need retraining? Yes.** The refiner is new weights, and the paper co-trains the drafter with it. No result with a frozen drafter is reported. No head exists for Qwen3.8-27B (published: Qwen3-4B, Qwen3-8B, gemma4-26b-a4b). Training cost as stated: 32 H100s per setting; steps, wall-hours and token count are not stated.
3. **Is any part a zero-training selector change on existing DFlash2 weights? No.** Jacobi is a solver for a sequential decode, and by the paper's own Prop 2 its fixed point equals the serial decode. DFlash2 already does the serial decode as a CPU loop over a precomputed 16x16 table (`common/speculative.cpp:1680-1706`). Jacobi there can only reproduce that walk, or a worse unconverged version, and there is no latency to save. The acceptance gain comes from the learned wider conditioning (the mixer `L`, `h_k`, `g`), which is what requires training.

## Mechanism

Refiner reads drafter hidden states and the prior token guess, projects to rank r=256, mixes causally with a per-channel strictly lower-triangular matrix over block positions, applies an r->2r->r MLP, reads out to vocabulary, and adds the bias to the drafter's own logits. The causal dependency is solved by K Jacobi passes seeded from the drafter's argmax. Backbone features are held fixed, so each pass is head-only.

Companion-code detail not in the paper: the shipped vLLM default is `xpress_topc=512` and `xpress_num_passes=6`. The README says each pass re-reads a `[vocab, r]` matrix of 78 MB in bf16, and that restricting the readout to top-512 base-logit candidates saturates acceptance.

## Claim table

| # | Claim | Status | Locator | Verbatim quote |
|---|---|---|---|---|
| 1 | Backbone runs once; K passes are head-only | CONFIRMED | Sec 4.2 | "are computed once and held fixed across iterations" |
| 2 | Refiner needs training and is co-trained with the drafter | CONFIRMED | Sec 4.3 | "The causal refiner is co-trained with the (co-adapted) drafter" |
| 3 | Training hardware | CONFIRMED; steps/hours NOT-FOUND-IN-SOURCE | Sec 5.1 | "For the training process, we use 32 H100 GPUs to train each setting." |
| 4 | ~30% tau / ~1.3x over dFlash at T=0 | CONFIRMED arithmetically, PARTIAL as framing | Abstract, Table 1 | "We compare against the plain dFlash drafter" |
| 5 | Over the Markov head (the closer analogue of DFlash2's selector) | Table-derived, see below; not headlined | Table 1 | derived |
| 6 | Lossless at T>0 for any K>=1 | CONFIRMED by my derivation; paper asserts without proof | Sec 4.2 | "the verifier receives the refined distribution of the final iteration as the proposal" |
| 7 | ~75 us per pass | CONFIRMED (Table 3: (681-150)/7 = 75.9 us; H200, block 16) | Sec 5.2 | "each Jacobi iteration adds about" |
| 8 | "near-zero cost" | PARTIAL: Table 3 has K=7 at 603 us vs Markov 601 us, and K=4-8 is 379-681 us per block | Contributions | "Causal dependency injection at near-zero cost" |
| 9 | Does not change verification or enlarge the drafter | CONFIRMED for the backbone; a new head is added | Sec 2.1 | "neither enlarges the drafter nor changes verification" |
| 10 | Edge over dFlash is batch-invariant | CONFIRMED vs plain dFlash only (my recomputation 1.156-1.471x across bs 4-32); Table 2 has no Markov row | Sec 5.2 | "essentially batch-invariant" |
| 11 | Adaptive K | NOT implemented; listed as future work. Companion vLLM path has fixed K | Sec 6 | "is currently fixed for a whole run" |

Arithmetic checks that held: all Table 1 average rows recompute; the 18-56% (T=0) and 19-58% (T=1) tau ranges recompute; K=4 gives 601/379 = 1.59x and K=6 gives 1.13x against the Markov head.

### Headline reframing, the main finding

Against plain dFlash the gains hold. Against the Markov head, which conditions on the previous token as DFlash2's selector does, the gain is far smaller.

| Table 1 average (Qwen3-8B, b16, single sequence, H200) | dFlash | Markov | XPress | XPress/dFlash | XPress/Markov |
|---|---|---|---|---|---|
| T=0 tau | 6.25 | 7.64 | 8.02 | 1.283 | **1.050** |
| T=0 speedup | 4.9x | 5.9x | 6.2x | 1.29 | **1.05** |
| T=1 tau | 4.94 | 6.62 | 6.97 | 1.411 | **1.053** |
| T=1 speedup | 3.6x | 4.7x | 5.3x | 1.46 | **1.11** |

Per dataset, XPress/Markov tau is 1.030-1.070 at T=0 and 1.034-1.074 at T=1.

### Numeric and protocol problems

- **T=1 XPress/Markov throughput (1.11x) exceeds its tau gain (1.05x) by about 6%.** Table 3 gives no compensating latency saving at the K used, since K=6-8 costs 530-681 us vs Markov 601 us. The excess is unexplained.
- **Several cells show throughput gain above tau gain over dFlash, which an added-cost head cannot do at fixed verify cost:** GSM8K T=0 1.70x vs tau 1.56x; GSM8K T=1 1.60x vs 1.58x; HumanEval T=0 1.32x vs 1.27x. MATH-500 T=0 goes the other way (1.10x vs tau 1.25x), where the dFlash cell looks high (6.8x at tau 7.71). The 1.70x headline therefore carries noise beyond the tau effect and should not be cited as the effect size.
- **K is chosen per cell by throughput.** The paper does not state K for Table 1; the README states each entry is "the throughput-optimal K" and the script sweeps K=4,5,6,7 at T=0 and 6,7,8 at T=1. XPress is best-of-3 or 4, baselines are single-configuration.
- **T=1 baseline protocol:** `bench_fair_fast.sh` sets `DRAFT_T` to TEMP, with a comment that `DRAFT_T=0` "also switches the DRAFT to argmax (dFlash conv.)". So the published T=1 dFlash arm samples its draft, which the script itself labels as not dFlash's convention. I did not verify which logs produced Table 1. The "severe degradation" of plain dFlash at T=1 may partly reflect this. It is the same question DF2-PM asks.
- README Markov T=0 average prints 6.1x; the paper's 5.9x is what the row recomputes to (5.91).
- Paper's consistency loss is one extra pass from `argmax(p_b)`; the speculators recipe trains `CONSISTENCY_PASSES=3` free-running rounds. The training recipe in code differs from the paper text.
- Sec 5.2 "Single Batch" text cites Table 2 where it means Table 1.

## Baselines and fairness

- The Markov head was trained on the identical recipe, which is a fair control and the paper's best feature.
- Plain dFlash is not retrained. It is measured "as released", while XPress and Markov are co-trained with their heads, so the dFlash comparison also credits additional training of the backbone. That confound inflates the headline.
- No comparison against DFlash2, DSpine, LiLiCorr or Domino. All results are one target (Qwen3-8B, dense), one block size (16), one GPU type (H200).
- Serving table: T=0 only, no Markov head, vs plain dFlash.

## Verify-cost model

Paper's Eq. 1: `L = (T_draft + T_verify) / tau`. XPress leaves `T_verify` unchanged, with the same linear draft and verification width. Draft side: Fig 4 caption/prose has Markov's 601 us at about 24% of the draft cost, implying a draft side of about 2.5 ms and a backbone+lm_head of about 1.9 ms (derived).

Per-pass cost, our block 8, r=256, V=248320 (GGUF header in DF2-FT-1, lane speculative-decoding.md:1611), FMA counts are my arithmetic:

| Op | FMA per pass |
|---|---|
| Read, full vocab: 8 x 256 x 248320 | 508.6M |
| Read, top-512: 8 x 256 x 512 | 1.05M |
| Read, top-16: 8 x 256 x 16 | 32.8k |
| MLP: 8 x 3 x (2 x 256 x 256) | 3.1M |
| in_proj: 8 x 3r x r | 1.6M |
| causal mix: r x 36 | 9.2k |

The full-vocab readout is 98% of a pass, and would stream a 127 MB matrix (248320 x 256 x 2 B) every pass. Top-C restriction is required for us, not optional.

## Drafter training requirement

Required. Adam-class co-training of refiner plus drafter against a frozen target, on target-regenerated Open-PerfectBlend, 32 H100s per setting, lr 6e-4, beta 0.3, lambda 0.6 to 0.2. Steps, hours and token counts are not stated in the paper. The published recipe is a 5k-sample pipeline check and its own comment says "the model performance will not be very good". Published recipe uses an online vLLM verifier and a second pair of GPUs.

Local path: DF2-FT-1 (lane speculative-decoding.md:1611) has the feature-dump contract and a planned whole-drafter fine-tune in 64 GB. An XPress arm would be a build cost on top of that pipeline. Warm-starting `W_e`/`W_r` from the DFlash2 selector codebooks (same 256 x 248320 shape) is my suggestion and is untested.

## What it needs from the target

Nothing new: a single linear draft, standard verify, no multi-branch, no change to rollback. Training needs target features, which is the existing DF2-FT-1 dump.

## Hybrid-SSM analysis

**Neutral: neither kills nor prices the technique.** The refiner is entirely drafter-side and runs before verification. The target still sees one linear draft, so per-branch recurrent state is not needed beyond the existing single-path rollback/replay. The hybrid only affects the training-side feature dump, which already exists as a contract. The drafter-side Gumbel at T>0 is per-block state and carries no target state.

## Lossless check at T>0 (my derivation)

Noise `G` is drawn once per block and shared across passes. The final token `y_k^(K)` is sampled with `G_k` from `q_k(.|Y^(K-1)_{<k})`. `Y^(K-1)_{<k}` depends only on `G_{<k}`, and `q_k` reads only the prefix, so `G_k` is independent of `q_k` given the past, and `y_k` is a true sample from the proposal handed to the verifier. Claim holds, on the condition that the proposal is the final-iteration `q` conditioned on the iteration K-1 prefix. A port must store that exact distribution, not recompute it from `Y^(K)`.

## Estimate for our regime (ESTIMATE, not measured)

**Inputs:** in-house round profile 27B Q8_0 + DFlash2, MI210, `-np 1 -c 16384`: 78.2 ms busy, verify 67.1 ms, drafter about 11.1 ms by segment-size heuristic; wall about 124 ms (kernel-champion-and-promotion.md:465, Pass L). Tuned reference 78-84 t/s (np1, n7, temp 0, short M1 prompts, 128 tokens, acceptance 0.62-0.73 benchmark shape).

**Refiner latency, assumption-driven:** 75 us per pass on H200 x (8/16 x 248320/152000 = 0.82 FMA scale) x assumed MI210 slowdown 2-4x = 123-246 us per pass full-vocab. Over K=4-7 that is 0.5-1.7 ms. Top-C makes the readout negligible, but per-pass dispatch overhead then dominates; take R = 0.5-2 ms. Round cost +0.6-2.6% of busy.

**Case A, DFlash2's selector is comparable to the Markov head** (both condition on the previous token; DFlash2's unary+pair score is a hidden-conditioned rank-256 first-order score). Paper delta: tau +3-7% at b16. At b8 only 7 positions can benefit and depth is shorter, so take g = +2 to +6% (assumption; no b8 data exists).
- low: 1.02 x 78.2/80.2 = 0.995x
- central: 1.04 x 78.2/79.2 = 1.027x
- high: 1.06 x 78.2/78.7 = 1.053x
- np1 temp-0, n7, 27B, MI210: **0.99-1.05x, central +3%**, about 77-88 t/s vs 78-84. Inside the DSpine comparison's epsilon of 7.3%, so a measurement needs a matched A/A design.

**Case B, DFlash2's selector adds little over plain DFlash.** The lane note says the z-lab card "reports no tau gain over DFlash 1". If that is taken literally, the plain-dFlash row applies: paper tau +28%, with block 8 cap and depth shrink, g = +10 to +20% (assumption). Speedup about 1.08-1.18x. Probability is unknown until DF2-LAT runs. It is not the base case, because the card's silence is not a measurement.

**Real :8083 temp-1 traffic** (acceptance 0.29-0.39, about 3-3.7 tokens per round): no evidence that causal mismatch, rather than distribution mismatch, is the dominant loss. DF2-FT-1 is the deciding probe. No separate estimate.

**np4 MI210:** the batch-invariance in Table 2 is against plain dFlash only, and bs=4 is its lowest cell. Lane says np4 X3 about X7 and C8-NP4-GARBAGE is open. No improvement claim; depends on np4 being fixed first.

**A3B (Qwen3.6-35B-A3B Q8_0):** served CPU with MTP. MTP drafts autoregressively and is already causal, so XPress has nothing to repair and there is no block-diffusion drafter in the lane. **0% today.** For GPU-eventual A3B, it needs a DFlash-family drafter first; then Case A applies. Hybrid-SSM is neutral there too.

**CPU decode:** 27B DFlash is served MI210-only (lane SPEC-6 note). For a future CPU diffusion drafter, the full-vocab readout is bandwidth-bound (127 MB per pass x K); top-C would be mandatory. No gain to estimate now.

**Small models at high concurrency on MI210:** Table 2's compression (GSM8K XPress 6.0x at bs4 to 2.8x at bs32) applies to speedup vs AR; the relative edge over plain dFlash holds. Needs a drafter trained for that small model; no in-house row.

Evidence grade: **B-** for the paper's within-setup claims (open code and weights, controlled Markov baseline, no independent replication, noise and K-selection issues). **C** for transfer to Qwen3.8-27B, block 8, DFlash2.

## DSpine overlap

**Different bet in cost, same risk in transfer.** DSpine (CLOSED NOT_OUTPERFORMS, best 0.915x DFlash2 n7, speculative-decoding.md:1598-) replaced the drafter and paid backbone/width cost for acceptance. XPress keeps the backbone and adds a head costing about 0.6-2.6% of the round, so it does not repeat that cost failure. The shared risk: DSpine's +9.8% tau / +11.1% throughput on Qwen3-8B b16 did not transfer to 27B, and XPress's numbers are from the same regime. Its realistic improvement over a first-order selector (+5%) is half of DSpine's reported paper gain, so it needs a stronger reason to run than DSpine had.

## Adversarial pass

One WebSearch (standard mode) found the arXiv listing, HF papers mirror and related dFlash/SpecDiff papers. These restate the abstract. **No independent replication or critique found.** The vLLM merge (#54448) and speculators merge (#1061) are stated in the authors' README; I did not read those PRs. An upstream merge shows maintainers accepted code, not that the numbers replicate; both are author-adjacent (IBM/vLLM-ecosystem authors). The strongest criticism is internal and listed above.

## Derived-actionables ledger

| ID | Action | Task or decline |
|---|---|---|
| XP-1 | Amend DF2-LAT: in the same zero-training dump, record the rank of the verifier's token in the full base logits, and add oracle arms for top-16 and top-512. Reason: XPress's shipped readout saturates at C=512 while DFlash2's lattice has C=16, so the selector's candidate set may itself cap any re-selector, and H as defined cannot see above 16. | **Task** (owning session applies, no new box needed) |
| XP-2 | Jacobi over the existing DFlash2 lattice | **Decline**: Prop 2 fixed point equals the serial walk; the walk is a CPU loop over a precomputed table. Zero acceptance gain, zero latency to save. |
| XP-3 | Train an XPress-style head on DFlash2 for 27B at block 8 as an arm of DF2-FT-1, frozen backbone first, then co-trained; port as a static ggml sub-graph with top-C readout | **Trigger, no checkbox yet**: fires when DF2-LAT opens a trained-selector port under its existing rule, or when DF2-FT-1 yields a working pipeline and DF2-LAT shows the top-512 ceiling warrants it. Sits with SPEC-3 trigger as a competing head. |
| XP-4 | At block 8, evaluate serial refine in a static graph alongside Jacobi | **Part of XP-3**: since ggml graphs are static, a 7-step serial sweep has 1/K the FMAs at the cost of more dispatches; K<<B is not available at B=8 |
| XP-5 | Reuse DF2-PM to control for the T=1 dFlash-baseline concern | **No new task**: DF2-PM already covers point-mass proposals |
| XP-6 | DF2-BLOCK16 interaction | **No change**. If a b16 DFlash2 lands, XPress's K<<B premise returns and its value rises; re-read at that time |
| XP-7 | CAFE-3 / SPEC-CONF.1 / SL-2 / DF2-LB1 | **No overlap**: XPress does not change width or verify |
| XP-8 | Port test using a released checkpoint without training | **Decline for now**: released heads target Qwen3-8B, Qwen3-4B and gemma4-26b-a4b at b16. Reconsider if XP-3 fires, as a pre-training check of MI210 per-pass latency |
| XP-9 | A3B / CPU | **Decline for now**: MTP is causal, no diffusion drafter. Reopen when a DFlash-family drafter for A3B exists |

## Dive-surfaced sources (not in the index copy, bearing on conclusions)

1. https://github.com/vllm-project/speculators/blob/main/docs/user_guide/algorithms/xpress.md plus `examples/train/xpress_qwen3_8b_regen_online.sh`: the only public training recipe. It would settle real training scale if a full-scale configuration is published (the checked-in one is a 5k tutorial).
2. https://huggingface.co/UIUC-SSAIL/gemma4-26b-a4b-XPress-b16: the only published head for a non-Qwen3 target. It would show whether acceptance gains hold on a target near our worker model; card not read in this dive.
