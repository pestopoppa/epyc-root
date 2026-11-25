# S1-pando-trees: noise-coupled parallel draft trees, the speed-of-light bound, and UBTree

**Dive:** S1-pando-trees · Stage 2, wave 1 · 2026-11-25 · model claude-opus-5-5
**Entries covered:** intake-2963 (Pando, arXiv 2611.32269v1, `s08`), intake-2973 (Speculative Decoding Speed-of-Light, arXiv 2512.11718v1, `x03`), intake-2974 (UBTree, arXiv 2609.39972v2, `x04`).
**Read depth:** FULL for all three. Every `source.txt` was read end to end. Reference lists were skimmed for identifiers only.
**In-house pins:** lane worktree `f19b902`. The two handoff files are byte-identical at the worktree HEAD `65c5bee6e` (`git diff --stat f19b902 HEAD` is empty for both). Code pins are C21 `98ff8a4`.

## Bottom line

1. **Pando's noise coupling is lossless, but only under a target-sampling verifier.** The proof is sound in exact arithmetic (sketch below). It does **not** carry over to our recursive-rejection (RRS) tree verifier. Under RRS, a tree shape that depends on the verifier's randomness biases the output.
2. **Noise coupling does nothing at T = 0 and very little at low T.** The paper measures it only at T = 1. Our served traffic is mostly T 0.1-0.3. Our own replay of the same idea (SPEC-DTREE-DICE V3, "draw-informed selection") found no gain on A3B or 27B, even at T = 1.
3. **The headline 5.27x / 4.22x is greedy Pando with no noise coupling, and it is modelled.** Only acceptance length τ is measured, on a GPU. Latency and energy come from a roofline. At T = 1, the 16-node Pando+NC tree is 5.17x / 4.13x, also modelled.
4. **The ridge-point model does not predict our MI210 verify cost.** At 16 nodes it predicts verification within 1.02x of a decode step. We measured a step at 12 rows (W1/8/12/16 = 31.4/43.5/61.3/62.4 ms) and a round-cost ratio of 1.32x at T16. After the GDN-batch, device-accept and RRS work, the 27B sampled tree now gains: official C21 T1.0 T16 is 1.035x, and T0.3 is NULL. Pando does not change that position. On our hardware, kernel and hybrid-state costs dominate, not the ridge point.
5. **x03 does not bound Pando+NC.** It covers deterministic drafting only, and it excludes deterministic (T = 0) targets. It says nothing about concurrency, so the Stage-1 note that cited it for a high-concurrency tree loss is reattributed. **x04 is the concurrency evidence.** A fixed 64-node tree (DDTree) falls below the chain at C = 32. Load-adaptive trees stay 7-16% ahead.
6. **x04 holds the closest external datapoint to our lineup.** On Qwen3.8-27B (GDN hybrid, Bole-style state inheritance, TP4, bs1), UBTree has τ 7.08 and 4.78x speedup, against DFlash 2's τ 5.78 and 4.24x.

## Q1: how noise coupling works, and the losslessness proof

**Mechanism (s08 §3.2-3.5).** The target's draw at output position j is the Gumbel-max sample y_j = argmax_x (log p(x|y<j)/T + g_{y<j}(x)), with g ~ Gumbel(0,1). The noise vector is keyed only by the prefix, so it can be drawn before drafting. Each tree node v carries the vector g_v that the target will use if it samples at v. Siblings share that vector, and different prefixes get independent vectors. Each candidate edge is rescored as q̃ = λ·q + (1−λ)·softmax(log q/T + g_v), where the softmax runs over the expanded children plus one aggregate "rest" category with its own independent Gumbel draw. Paths are then ranked by the cumulative product of q̃ and pruned to N nodes. The paper uses λ = 0.25. Verification is the **target-sampling walk**: at each node, compute y with the same g_v and descend if y is a child; otherwise y becomes the bonus token. The noise is derived deterministically from the prefix (a counter-based generator), so it is never redrawn across iterations.

**Proof sketch (ours; it agrees with s08 §3.4).** Fix a request seed. The noise field {g_s : s a prefix} is i.i.d. across distinct prefixes. The emitted sequence follows y_j = F(p(·|y<j), g_{y<j}). That is a deterministic function of the target's probabilities and of the noise along the realized path, and it is the same sequence plain autoregressive Gumbel-max sampling would produce. The tree decides only how many y_j one pass commits; no y_j depends on it. y<j is a function of {g_{y<i} : i < j}, which are keys distinct from y<j itself. So g_{y<j} is independent of y<j, and y_j ~ softmax(log p/T) exactly. The drafter reading the noise is not a peeking bias, because the tree cannot change any y_j. This holds for any noise-dependent tree.

**Conditions, and where it breaks:**
- *The noise must be kept, not redrawn.* s08 states this itself: redrawing it every iteration gives proposed tokens extra chances to be committed.
- *The verifier must be the target-sampling walk.* Under a rejection-style tree verifier (SpecInfer/RRS, our C21 `common_dtree_rrs_walk`, `common/speculative-tree.cpp:L414-475 @ 98ff8a4`), the emitted token depends on which children are present, because the residual is formed from rejected siblings. Exactness then needs the sibling set to be independent of the verification randomness. Our own rule already says "Tree shape may depend only on earlier draws" (`handoffs/active/speculative-decoding.md:L2507 @ f19b902`). **So NC + RRS is not lossless.** NC needs the target-sample walk, which accepts less per node than RRS on the main chain.
- *Numerics.* The tree's shape depends on g, and the verify logits depend on the batch shape (bf16; for us, the wvsk/MMQ route switch by width and unordered atomics, `speculative-decoding.md:L1331, L2510 @ f19b902`). That is a tiny noise→logit channel. s08 concedes that bf16 outputs can flip on near-tied Gumbel draws, and its fp32 audits match. Treat this as a numerical deviation and test it with the chi-square gate we already run.
- *Sampler chain.* The Gumbel argmax must run on the post-sampler law (top-k/top-p/min-p, plus presence penalty with each column's own path history, L2507). Over a truncated top-K the result is exact for the truncated law.

**At T = 0 (greedy):** the draw is argmax p, so the noise has no effect and Pando+NC equals Pando (s08 §3.2, §5.2). It is trivially lossless and gains nothing. **At low T (our 0.1-0.3 role defaults, L2537):** log p/T dominates the O(1) Gumbel noise, so the noise rarely moves the argmax, and the expected NC gain shrinks toward zero. The paper gives no T between 0 and 1 (NOT-FOUND-IN-SOURCE).

## Per-claim verdicts

### intake-2963 Pando (s08)
| # | Claim | Verdict | Locator / note |
|---|---|---|---|
| 0 | Parallel drafters are deployed as chains capped at block length; Pando builds dynamic trees on them | CONFIRMED | Abstract, §1. Pando uses DSpark's Markov head for parent-conditioned children (§3.1). |
| 1 | Noise-coupled pruning pre-draws the target's Gumbel noise and ranks branches with it, losslessly and without retraining | CONFIRMED, narrowed | §3.2-3.5, App. A. Lossless only with target-sampling verify and kept noise; not with rejection verify; bf16 near-tie flips conceded. |
| 2 | NC raises acceptance by up to 8.4% on Qwen3-8B | PARTIAL | "Up to" is the 8-node, T = 1 maximum (Table 2 mean 4.59→4.98). It shrinks to ~1% at 128 nodes and is 0 at T = 0. λ was chosen on the evaluation prompts. The live check is 6 prompts × 64 tokens (+7.0% / +7.3%). |
| 3 | A 16-node tree gives 5.3x speedup and 4.2x energy on a modelled edge device | PARTIAL | §7.1: this is the **greedy (T = 0), no-NC** Pando tree, and it is modelled. The ridge point of the "representative edge device" is NOT-FOUND-IN-SOURCE in the text. At T = 1, Pando+NC at 16 nodes is 5.17x / 4.13x. |
| 4 | Speedups are normalised by an operator-level roofline to the ridge point | CONFIRMED | §4.3, Eq. 6-7. App. D: on an A100 the measured cost is 5-18% above the model at 16-128 nodes. All costs are predictions. |

### intake-2973 Speed-of-Light (x03)
| # | Claim | Verdict | Locator / note |
|---|---|---|---|
| 0 | Bounds the runtime of any deterministic speculative algorithm via branching random walks | CONFIRMED | Abstract, Thm 1. "Tight" is weakly shown: Fig. 1 plots the Lemma 7 *lower* bound, which EAGLE-3 exceeds, and the paper reports a ~2x gap to EAGLE-3. |
| 1 | Expected tokens per verify grow with log of capacity and depend on target entropy | CONFIRMED | Thm 1: E[X] ≤ (μ+μ₂)/μ²·log P + O(1). μ is measured at T = 1 (Qwen3-8B mean μ 0.319). |
| 2 | Analyses optimal draft-tree selection | CONFIRMED | Lemma 1: the top-P nodes by path probability, given perfect knowledge. Assumes i.i.d. prefixes. |
| 3 (append) | Scope | NEW | Excludes stochastic or coupled drafting (§6) and deterministic targets (Assumption 2), so it does not bound Pando+NC or greedy decoding. No concurrency analysis. |

### intake-2974 UBTree (x04)
| # | Claim | Verdict | Locator / note |
|---|---|---|---|
| 0 | A unigram proposer plus a bigram selector build the tree | CONFIRMED | §3.1. The proposer is a DFlash backbone. DFlash 2 already has a low-rank bigram selector (§2). |
| 1 | Tree-native training supervises beyond the greedy path | CONFIRMED | §3.2: T_train = 1 with renormalized KL. The objective's effect is small (CE vs KL τ 10.08→10.23); most of the gain is the selector architecture (Table 4). |
| 2 | Large speedups on Qwen3-4B/8B and wins all comparisons against DARTree | CONFIRMED, narrowed | 5.84-6.94x average; DARTree beaten in 28/28, +7.4-13.4%. HF transformers, bs1, one Hopper GPU, seed-0 subsets, one run each. |
| 3 | A serving evaluation on SGLang compares against DSpark | PARTIAL | The concurrency sweep (Table 2, C 1-32) has **no DSpark arm**. DSpark appears only in production-scale Table 3 at bs1 / TP4. |
| 4 (append) | Qwen3.8-27B result | NEW | UBTree τ 7.08, 4.78x vs DFlash 2 τ 5.78, 4.24x (TP4, GDN state inherited per node). Target temperature not stated ("greedy drafter decoding"). |
| 5 (append) | Concurrency | NEW | Qwen3-8B at C = 32: DDTree (fixed 64) 1.30x vs DFlash 1.90x; adaptive UBTree 2.11x. |

**Counts across the 3 entries (13 claim rows):** CONFIRMED 8 (2 of them narrowed), PARTIAL 3, OVERTURNED 0, NOT-FOUND 0 at claim level (1 sub-item, the edge-device ridge point), NEW appended 3. The Stage-1 `contradicting_evidence` that attributes a high-concurrency tree loss to arXiv 2512.11718 is **overturned / reattributed**: x03 has no concurrency analysis, and the evidence is x04 Table 2 and Appendix D.

## Q2: measured vs modelled, and where our hardware sits

- **Measured:** acceptance length τ only (s08 §4.1: τ is measured on a GPU; latency and energy are modelled per platform). There is one 6-prompt live wall-clock check of NC, showing "no measurable change in wall-clock time".
- **Modelled:** every speedup and energy figure (App. D: "All computational costs in this paper are predictions"). The energy constants are 28 pJ/B (LPDDR5X) and 0.5 pJ/op.
- **The ridge-point claim** is that the speed-optimal budget saturates near 64 nodes above about 64 FLOP/B, and that at 16 nodes verify stays within 1.02x of decode on every listed device (ridge ≥ 100). s08 places the EPYC 9654 at 35-50 FLOP/B, the low-ridge region where the optimal budget is small. The exact budget at that ridge is shown only in a figure (NOT-FOUND-IN-SOURCE in the text).
- **MI210 (measured, in-house).** Paper-style rooflines say rows are nearly free up to M ~50 (`autokernel-loop.md:L4937-4940 @ f19b902`). We measured a **step**: 31.4/43.5/61.3/62.4 ms at W1/8/12/16, caused by the wvsk→MMQ route switch (`speculative-decoding.md:L2510`). The implied round-cost ratios are T8/T12/T16 1.007/1.235/1.319 (L2541). The Q8_0 GEMM reaches about 850-983 GB/s at n8-16 (L1141). The binding constraint is skinny-M kernel efficiency, GDN per-row state and host time, not the compute/bandwidth ratio. **Verdict: the ridge-point model does not transfer as a predictor. Use the measured W→ms curve, as the DTREE-B controller already does (L2550).**
- **EPYC (production CPU models are MoE).** Pando's premise that tree rows share one weight stream fails for MoE. Each row can route to different experts, so verify bytes grow with unique experts. The A3B GPU trace shows MUL_MAT_ID at 1.07 ms/row with no cross-row reuse (L2547). Together with the 35-50 FLOP/B ridge point, this makes trees beyond the chain unlikely to pay on CPU. A dense CPU case is unmeasured.

## Q3: in-house comparison (pins @ f19b902)

- **We already tested Pando's NC idea.** SPEC-DTREE-DICE V3 ("draw-informed selection" with pre-sampled keyed draws) returned NULL: holdout V3/V1 0.997-1.011 on A3B at every T including 1.0, and ≤ 1.0 on 27B (`speculative-decoding.md:L2527, L2535, L2541`). Pando reports +7-8% at 8-16 nodes and T = 1. Possible reasons: different mixing (DICE fitted (α, σ); Pando uses λ = 0.25 with an aggregate "rest" category), different shapes (our A3B MTP trees are leaves-only, L2506; our 27B sampled builder adds siblings off the main chain, `common/speculative-tree.cpp:L482-529 @ 98ff8a4`, rather than a full best-first k-expansion), and served-T entropy. **Our measured null outranks Pando's +8.4% for our stack. Do not carry the +8.4% into plans.**
- **Our DFlash 2 tree is already Pando-shaped.** The lattice scores are parent-conditioned (`scores(j, pred)`, `common/speculative.cpp:L1848-1850 @ 98ff8a4`), the analogue of DSpark's Markov head. x04 §2 confirms DFlash 2 has a low-rank bigram selector. So "parallel drafter → tree" is ALREADY-PRESENT.
- **Tree result on 27B.** The brief's "trees lost on 27B" is stale. The 11-23 sampled LOSS (0.75-0.93, L2531/L2538) was ruled invalid for 27B: there were no siblings, and `spec_dists.clear()` downgraded DFlash 2's rejection accept (L2545-2546). DTREE-STOCH (point-mass rejection walk) failed at 0.93-0.96x (`autokernel-loop.md:L4932`). After DTREE-GDN-BATCH and device accept (post time 0.43 ms, L1325), the V2 RRS sampled tree gained at T1.0 (T16 1.088x, T12 1.072x), was NULL at T0.3, and reached 1.052x on greedy T16. The official C21 row gives T1 T10 1.030x and T16 1.035x (L1338).
- **Does Pando change this?** No. Pando's T = 1 acceptance gain from a 16-node tree over the 8-node chain is large (Table 2: 5.79 vs 4.55). Our 27B replay gives only V1/V0 1.06-1.07 at W16 against a served rejection chain (L2541), and our verify cost per added row is real, not ~2%. Measured width cost dominates. What Pando adds: (a) its full best-first shape is worth one offline replay against our sibling-of-main shape; (b) NC is ruled out on our verifier, because it needs the target-sample walk, which gives up rejection acceptance on the main chain.

## Q4: do x03 and x04 bound or contradict Pando?

- **x03** bounds deterministic drafters at log P / μ. Pando+NC is a *coupled* drafter. Given the noise, the target is deterministic, which x03 excludes, so it is not bounded by x03. x03's i.i.d. assumption, T = 1 entropies and constant-latency model make it a ceiling for *draw-blind* trees only. It gives no concurrency result. Use: a cheap headroom check from our capture's target logits (actionable KS-S1-pando-trees-2).
- **x04** supports trees at np > 1 only with adaptive budgets. A fixed 64-node tree loses to the chain at C = 32 (DDTree 1.30x vs DFlash 1.90x on Qwen3-8B). Adaptive UBTree keeps +7-16% over the next best method. Appendix D says spare compute shrinks with concurrency for all methods. Pando is single-stream only and says parallel drafters were designed for high-concurrency serving, where short chains suffice. **Net:** x04 bounds Pando's gains to low load. For np > 1 the budget must shrink with load (our DTREE-B already drops to the chain above batch 4, L2550).

## Principles table

| Principle | Source evidence | MI210 (gfx90a) | EPYC Zen 5 | Why (mechanism) | Port cost |
|---|---|---|---|---|---|
| Parallel-drafter tree vs chain | s08 Table 1-2 (T=1, 16 nodes τ 5.79 vs chain 4.55); x04 Table 3 (27B τ 7.08 vs 5.78) | ALREADY-PRESENT (C21 V2 RRS tree on the DFlash 2 lattice; official T1 T16 1.035x, T0.3 NULL) | DOES-NOT-TRANSFER for the MoE lineup; dense UNKNOWN-NEEDS-PROBE | Tree gain = Δτ minus per-row verify cost. On 27B, Δτ is small at served T. On MoE CPU, rows do not share expert bytes. | 0 (present); a best-first shape replay is ~0.5 agent-day offline |
| Noise coupling (pre-drawn Gumbel ranking) | s08 §3.3-3.4, §5.2; in-house DICE V3 NULL | DOES-NOT-TRANSFER (needs the target-sample walk; NC + RRS is not lossless; no gain at T 0.1-0.3; DICE NULL even at T=1) | DOES-NOT-TRANSFER (same reasons; A3B DICE NULL) | Gains need sampled T near 1 and small budgets. Exactness needs a verifier whose emitted token is independent of tree shape. | Keyed Gumbel sampler + walk: ~2-3 agent-days; not recommended |
| Node budget vs ridge point | s08 §4.3, §6, App. C-D (A100 +5-18% vs model) | DOES-NOT-TRANSFER as a predictor (measured step at 12 rows; T16 round 1.32x before levers) | TRANSFERS-WITH-CHANGES (low ridge → small budget, consistent with s08's EPYC 35-50 FLOP/B; MoE breaks byte sharing) | Rooflines assume ideal skinny-M kernels and weight-shared rows. Ours have route switches, GDN state and host time. | 0; keep the measured W→ms curve (DTREE-B) |
| Tree verify cost on hybrid GDN models | x04 §4.2 (per-node state inheritance, 27B 4.78x vs 4.24x); s08 cites Bole | ALREADY-PRESENT (batched tree GDN KEEP, T16 GDN 3.619 ms, L1338) | UNKNOWN-NEEDS-PROBE (no CPU tree-GDN path measured) | Each node needs its parent's recurrent state. Batching it into one state read per layer brings the per-row cost near the chain slope. | 0 on GPU; CPU port unscoped |

## Derived-actionables ledger

| ID | Action | Owner | Disposition | Reason |
|---|---|---|---|---|
| KS-S1-pando-trees-1 | We could replay a Pando-style full best-first tree (k-expansion per level, prune to N by cumulative lattice prob) against the current sibling-of-main builder on the existing 27B DFlash 2 capture, at T 0.3/1.0 and W 8/12/16, with V1 RRS verify. | handoffs/active/speculative-decoding.md (SPEC-DTREE-ACCEPT-GAP follow-on / DTREE-B) | immediate | Offline, capture exists (L2541). Tests whether tree shape, not NC, explains Pando's larger Δτ. |
| KS-S1-pando-trees-2 | We could compute x03's bound (μ, μ₂ → E[X] at P 8/12/16) per served T from the capture's target top-64 logits and compare it with measured τ. | handoffs/active/speculative-decoding.md (SPEC-DTREE-DICE knowledge) | immediate | Cheap headroom ceiling for draw-blind trees. Caveats: i.i.d. assumption, top-64 truncation lowers μ (looser bound), invalid at T=0. |
| KS-S1-pando-trees-3 | We should record the rule: noise-coupled or draw-informed tree shapes are lossless only with the target-sample walk; with RRS the tree must be blind to verifier randomness. | handoffs/active/speculative-decoding.md (L2507 knowledge note) | knowledge-only | Prevents an unsound NC + RRS build. |
| KS-S1-pando-trees-4 | We should not build NC on DFlash 2 / MTP. | handoffs/active/speculative-decoding.md (SPEC-DTREE-DICE, closed NULL) | decline | Measured DICE NULL; served T low; verifier incompatibility. Reopen only if T≈1 traffic share rises AND a target-walk tree beats RRS. |
| KS-S1-pando-trees-5 | We could check whether UBTree's Qwen3.8-27B selector or checkpoint is released and whether it drops into our DFlash 2 lattice path (same low-rank bigram form, precomputed codebooks). | handoffs/active/speculative-decoding.md (DFlash 2 drafter lane) | monitor | +12.7% speed / +22% τ over DFlash 2 on our exact target (vendor, TP4, bs1). Training-heavy if not released. |
| KS-S1-pando-trees-6 | At np > 1, keep load-adaptive tree budgets (shrink to chain); never a fixed large tree. | handoffs/active/speculative-decoding.md (DTREE-B) | knowledge-only | x04 Table 2: fixed 64-node DDTree loses to the chain at C=32; DTREE-B already does chain above batch 4. |

## Adversarial pass

- WebSearch (2 queries). Pando (posted 2026-11-24) has no replications. Related coupling work found: GLS Gumbel-max list sampling (arXiv 2506.05632, already cited inside intake-2845) and Daliri coupling (intake-2831/2845). No UBTree reproduction was found. A Latenode news item (restatement, not corroboration) quotes "5.36x on Ling3-Flash 124B". That figure is NOT in the source text: Table 3 gives Ling3-Flash 3.27x, and the only 5.36 in the text is DFlash's τ on Ling3-Tiny. Do not carry it.
- Internal checks: Pando's 8.4% is consistent with Table 2 (4.98/4.59 = 1.085). λ was tuned on the evaluation prompts, which the paper admits. The headline speedup belongs to the T = 0 arm, where NC is inert. x03's "tight" rests on correlation plots with a stated ~2x gap.

## Dive-surfaced sources

| ID | Title as printed | Settles | Bears on | Recommend |
|---|---|---|---|---|
| arXiv 2608.02123 | From Chains to Trees: Parent-Conditioned Drafting for Semi-Autoregressive Speculative Decoding (PCTree) | Greedy DSpark-tree baseline | intake-2963 | decline (greedy-only; Pando and our DTREE cover it) |
| arXiv 2608.01651 | Bole: Efficient Tree Speculation for Hybrid-Attention Language Models | GDN tree-state cost | intake-2963, intake-2974 | decline (already in index via intake-1847/2705) |
| arXiv 2609.22098 | TreeSpark: Calibrated, Load-Adaptive Draft Trees for Semi-Autoregressive Speculative Decoding | Tree budget vs load | intake-2963 | decline (already filed as intake-2975 this session) |
| arXiv 2611.12356 (search result) | DForkTree: Accelerating Speculative Decoding with Fork-Aware Block Diffusion Draft Trees | Block-diffusion tree shape | intake-2974 | decline (title only; shape heuristics covered by KS-S1-pando-trees-1) |
