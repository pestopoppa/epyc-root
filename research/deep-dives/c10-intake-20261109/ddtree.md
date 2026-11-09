# DDTree (arXiv 2604.12989v1), intake-2667 Stage-2b dive (wave 2)

- read_depth: FULL (body, Table 1, Appendices A-B, Table 2; Figures 3-4 read from the arXiv SVGs)
- version: https://arxiv.org/html/2604.12989v1 (LaTeXML, 14 Apr 2026)
- sha256 of raw html: f6b462bcead6c4d047a38627693d100e0fa36c718680d3bf63a3814f06ff13be
- companion repo read, not executed: github.com/liranringel/ddtree @ c96427a185677bf4133ed865dd1626a5041aef9b (`dives/ddtree-src/repo/`)
- lane_head: ad1e73525f6b86077936d9a1065f4da35c27c9d5. `L<n>` = line of the converted text. Champion code read with `git show d210f85c2:` (read-only).

## Bottom line (the four questions)

1. **Zero training, yes.** It is a post-processing of one existing DFlash pass (L100-104, L212; repo `build_ddtree_tree(draft_logits[0], tree_budget)`, ddtree.py L383). Usable offline on a DFlash2 top-16 lattice for B <= 16 with an exact guarantee (Lemma 1: K = min(B, |V|), L165-169), **provided the dump also records one extra scalar per position, the full-vocabulary log-normaliser.** See "Offline on the lattice".
2. **Algorithm/objective.** Maximise the expected accepted length under the drafter's factorised distribution, Eq 6 (Q from Eq 2). Prop 1 / Eq 8 turns it into the sum of prefix masses q(u) (Eq 7), so the optimum is simply the top-B prefixes (Prop 2). Algorithm 1 pops them from a max-heap: each pop pushes next sibling and first child, O(B log B) (Remark 2, L204).
3. **Verifier needs.** One target pass over root + B nodes with position id = depth, an ancestor-only attention mask, and after the walk a gather of the accepted node indices from the KV cache and from the features the drafter consumes. No per-branch rollback search; the proposal is deterministic so acceptance is plain "sample from the target at this node, is it a child?" (L208; ddtree.py `posterior = sample(output.logits, temperature)`).
4. **Small budgets.** The paper never runs B < 16. At B=16 (MATH-500, Qwen3-8B, T=0, digitised Fig 3): **tau +10.5%, speedup +9.6%** vs the headline best-budget (B=512) +37.8% tau / +35.2% speedup on the same cell. **At our depth cap (7) and B=7-8 a homogeneous model says the tree is the chain, or chain plus one sibling: +2 to +8%** (estimate). Headline does not transfer.

## Mechanism

One DFlash pass gives per-position marginals `q_i` (Eq 2). Node at depth d = prefix u. `alpha_T(y)` = longest prefix of y in T (Eq 4). Ideal objective Eq 5 needs the target; surrogate Eq 6 replaces p with Q. Prop 1: `E_Q[alpha_T] = sum_{u in T} q(u)` (Eq 8). Because a child's mass is strictly below its parent's (Eq 11, assuming q in (0,1), L142), the top-B prefixes are automatically prefix-closed, so they are optimal (Prop 2). Algorithm 1 enumerates them by rank tuples (L172-200). Root does not count toward B (L114). Repo normalises against the whole vocabulary: `log_z = torch.logsumexp(logits, dim=-1)` (ddtree.py L108).

Verification: flatten to `[root, nodes]`, position ids by depth, tree attention, one forward; walk from root; compact KV to accepted indices (L207-208; ddtree.py compile_ddtree_tree + `compact_dynamic_cache`, `target_hidden...index_select(1, accepted_index_tensor)`).

## Claim table

| # | Claim | Status | Locator | Verbatim |
|---|---|---|---|---|
| 0 | Tree comes directly from a single pass's per-position distributions, no training | CONFIRMED (paper + code) | L42, L212; ddtree.py L383 | "a method that constructs a draft tree directly from the per-position distributions of a block diffusion drafter" |
| 1 | Best-first heap selects under fixed node budget; optimal for surrogate | CONFIRMED, proofs read (App. A). Exact only for Q, as the authors say | L42; L151 | "uses a simple best-first heap algorithm to select the continuations"; "not for the true target-model distribution" |
| 2 | Root excluded from budget | CONFIRMED; means B=16 is 17 verified rows while vanilla DFlash horizon is block_size-1 = 15 nodes plus root, 16 rows (ddtree.py L306) | L114 | "itself does not count toward the node budget" |
| 3 | One forward pass with ancestor-only mask | CONFIRMED | L207 | "under which each drafted node attends to the past context through the KV cache" |
| 4 | KV compacted to accepted path after walk | CONFIRMED | L208 | "the KV cache is compacted to retain only the accepted path" |
| 5 | DDTree improves all 60 settings | CONFIRMED, recomputed 60/60 on both speedup and tau. **PARTIAL as a claim of gain size:** every cell is the best of 7 budgets chosen on the evaluation data, no holdout | L215, L501 | "the DDTree entry uses the best node budget from" |
| 6 | Speedup peaks at B 256-512 | CONFIRMED on Fig 3. **Headline is a B=256-512 number** | L503 | "the end-to-end speedup improves until it peaks around budgets of 256 to 512" |
| 7 | Better speedup at the same conceptual budget as a block-16 chain | CONFIRMED, digitised +9.6% speedup at B=16, one extra node | L503, Fig 3 | "Note that the optimal budget can shift across hardware platforms and implementations." |
| 8 | Requires standard attention, not FlashAttention-2 | CONFIRMED; target SDPA, baselines best of SDPA/FA2, conservative for DDTree | L696 | "does not support the required tree attention pattern" |
| 9 | Results for B < 16 | NOT-FOUND-IN-SOURCE (budgets are {16,...,1024}, L695) | L695 | n/a |
| 10 | Hybrid/recurrent target | NOT-FOUND-IN-SOURCE (Qwen3-4B/8B dense, Coder-30B-A3B MoE only, L212) | L212 | "each paired with its corresponding DFlash checkpoint" |
| 11 | Quality/losslessness at T=1 proven | NOT-FOUND-IN-SOURCE as a proof; it follows from deterministic proposals (L208, ddtree.py). I agree with it | L208 | n/a |

Recomputed from Table 1 (60 cells, best-budget DDTree vs DFlash): T=0 mean speedup +46.0%, tau +47.6%, speedup range +30.8 to +63.5%; T=1 mean speedup +52.0%, tau +54.2%, speedup range +38.0 to +65.2%. **Tau gain correlates -0.87 with vanilla DFlash tau across cells**: low-acceptance sets (Alpaca +65.6% tau, SWE-bench +64.1%) gain the most, and high-acceptance sets the least (LiveCodeBench +41.2%). MT-Bench +53.9%.

## Gains at small budgets (B=16 is the smallest measured)

Figure 3 values digitised from marker coordinates in `math500_qwen3_8b_budget_tradeoff.svg` (`dives/ddtree-src/fig3.svg`). Calibration: axis ticks 34.107 pt/unit; baseline DFlash lines read 5.562x / 7.789 and Table 1 gives 5.56x / 7.79; B=512 reads 7.518x / 10.731 and Table 1 gives 7.52x / 10.73. MATH-500, Qwen3-8B, T=0, block 16, single sequence (ddtree.py batch shape 1), one H200 per worker, bf16:

| B | Speedup | tau | speedup vs DFlash | tau vs DFlash | tau/speedup (round cost in AR steps) |
|---|---|---|---|---|---|
| DFlash chain (15 nodes) | 5.56 | 7.79 | - | - | 1.40 |
| 16 | 6.09 | 8.61 | +9.6% | +10.5% | 1.41 |
| 32 | 6.60 | 9.27 | +18.7% | +19.0% | 1.40 |
| 64 | 6.97 | 9.75 | +25.3% | +25.2% | 1.40 |
| 128 | 7.33 | 10.20 | +31.7% | +31.0% | 1.39 |
| 256 | 7.44 | 10.43 | +33.7% | +33.9% | 1.40 |
| 512 | 7.52 | 10.73 | +35.2% | +37.8% | 1.43 |
| 1024 | 6.82 | 10.98 | +22.6% | +40.9% | 1.61 |

The round cost is flat from 16 to 512 rows: on H200 at batch 1 the width is free, then it is not. That flat region is what our regime cannot assume.

Independent B=16 rows: TreeFlash (ETH, a different group, same DFlash checkpoint family, GH200, 64 samples per set, `src/paper-2606.03819-v1.txt` L137-) has DFlash(16) vs DDTree(16). Qwen3 4B T=1 mean: speedup 3.82 -> 4.38 (+14.7%), tau 5.11 -> 6.06 (+18.6%). Its MT-Bench row: speedup 2.34 -> 2.84 (+21.4%), tau 3.08 -> 3.89 (+26.3%). So gains at B=16 are +10 to +26% tau across these datasets and grow as acceptance falls. These are depth-15 trees over a marginal chain, not a depth-7 lattice.

**B=8: no data anywhere in the sources.**

## Baselines and fairness

- Vanilla DFlash with the same checkpoint, and best of SDPA/FA2 for it (L696). Fair; slightly conservative for DDTree.
- **Oracle budget selection** on the same evaluation data per cell: optimistic. Sample sizes 30-164 per dataset (Table 2), no error bars in Table 1.
- No EAGLE-3 or DFlash2 column. **No DFlash2**: our selector already spends the drafter's information on predecessor conditioning (below), so the vanilla-DFlash baseline here is weaker than ours.
- MoE target (A3B) is covered only on the MoE side; no recurrent target.

## Verify-cost model

The paper gives none. Derived: tau/speedup ~1.40 for B 16-512 above, mean 1.41 vanilla vs 1.43 tree across Table 1 at best budget. Verify cost is effectively independent of B on H200 at batch 1 until B >= 1024 (L503). This does not transfer. In-house slope, 27B + DFlash2 on MI210 at np1 (cited from the wave-1 dives, not re-derived): up to 3.1 ms per extra row on short M1 prompts (DSpine-confounded upper bound) and 0-0.65 ms on LongHealth. The curve above is the shape we have not measured beyond 8 rows; the verify slope remains the whole uncertainty.

## Drafter training

None. Paper uses published DFlash checkpoints as is (L212). Note the marginal `q_i` are used directly; TreeFlash and JetSpec add training on top of this baseline. Our pipeline (DF2-FT-1) is not needed for this.

## What it needs from the target

- Multi-branch: yes, one forward over root + B nodes.
- Position ids by depth, ancestor mask, KV compaction by accepted index (L207-208).
- The drafter's context features must be selected along the accepted path (`target_hidden...index_select`, ddtree.py), because the next drafter pass consumes them. Our headless DFlash2 reads target hidden along the verify batch, so this is a requirement the wave-1 dives did not name.
- Sampling: per-node sampling from the target's own decoding rule at T=1; no q used in acceptance. So no draft-distribution correction, matches the point-mass soundness argument in DF2-PM.
- CPU heap of B pops, trivial at B<=16 (paper L204). The per-round mask build is O(B^2) on the CPU in the reference code, trivial at B=16.

## Hybrid SSM (27B, A3B)

Paper silent. Same conclusion as the wave-1 dives (`treeflash.md` L73-82, `jetspec.md` L105-111, with the champion evidence there): not a mathematical kill, a priced port by level-synchronous recurrent steps with parent-gather of per-node state. Depth stays <= 7, so GDN sweeps equal the chain's. What this dive adds: trees at B <= 16 are nearly chain-shaped. Under the marginal model below, B=8 has at most one branching node and B=16 has width 2-4 at the first three depths and tapers. So the per-node state is a handful of copies, and `split_equal` ragged-batch risk (DF2-LB1) is the real cost, not state memory. Rollback on the tree is a choice of one path through per-node snapshots. No new mathematical obstacle. Prerequisite unchanged: C8-NP4-GARBAGE is the hazard area.

## Offline on the DFlash2 lattice (settling the proposed arm)

What C9 actually computes (`src/models/dflash.cpp` L1312, L1366-1377 @ d210f85c2): the top-16 candidates per position by **unary** logit; scores = pair + unary, with pair conditioned on the previous position's candidate. `common/speculative.cpp` L1796-1819 walks the lattice from the anchor. DF2-LAT dumps ids, unary logits, pair scores and chosen ids.

Findings:

1. **Candidate set is sufficient for B <= 16.** Lemma 1 gives K = min(B, |V|), so top-16 per position holds an optimal tree for B <= 16. For B = 32 the lemma's bound is not met, so the optimum may be missed in principle (rare in practice, cost not quantified).
2. **Arm D1 (paper-faithful marginal DDTree) needs one more dumped field.** `log q_i(v) = logit - logsumexp over V` (ddtree.py L108). Renormalising over only the 16 stored logits inflates each position's masses by a position-dependent factor, and depth-vs-breadth ordering depends on those ratios. The lattice output `t_h_nextn` carries neither unary nor log_z separately: DF2-LAT's unary dump covers the first. **Add `logsumexp(t_logits)` per position to the dump** (one float per slot at the same graph point).
3. **Arm D2 (selector scores) is a different objective and still solvable.** Under a first-order Q with `q(v|pred)` from the lattice softmax, Prop 1 and Prop 2 proofs use only that Y is a distribution and factors are in (0,1), so top-B prefixes are still optimal for that Q. Algorithm 1 must change: siblings sort by each parent's own child ranking (16-way sort per expanded node). Its proof (pred chain, L684-690) carries over with per-node rankings. Caveat: selector softmax is over 16 candidates, not V, so probabilities ignore the mass outside the top 16. The tree optimises the selector's Q, not an audited probability.
4. **Simulation exactness.** Eq 4 needs only a target trajectory Y, not target logits at off-path nodes. At T=0, Y is the greedy trajectory; at T=1, a recorded sampled trajectory gives an unbiased, paired estimate (Eq 5). So no extra target forward is needed.
5. **Bias to fix.** DF2-LAT dumps per **live draft step**, so round starts are those the chain visited. A tree policy visits other starts. Paired-round comparison at chain starts is biased. Exact whole-policy simulation needs a lattice at every token position: run a shadow mode (target decodes AR, n-max 0, with a drafter pass at every position, using AR's hidden features). Cost is a slower run (no-draft 32.95 t/s versus 78, per the DSpine row) for the same DF2-LAT prompts and no training. It yields exact replay for every budget, including the chain, which also serves as the void check against the live acceptance counts.

## Estimate for our regime (ESTIMATE; no measurement in this dive)

Base (from `treeflash.md` L58-59, RESULT of `dspine-c9-gpu-tune-20261108`): 27B Q8_0 + DFlash2 Q8_0 n7, np1, temp0, short M1 prompts, 128 tokens, MI210: 78.04 t/s, tau 4.10, round 52.5 ms, 8 verify rows (7 nodes + root). Chain vs tree budget mapping: **chain = B=7**.

Simple geometric marginal model. Per-depth top-1 hit rate a; r = share of misses captured by rank 2 (r unmeasured; a bracket 0.3-0.5). Prefix mass of chain depth d = a^d.

- a = 0.80 (tau about 4.16, close to 4.10): chain masses .80,.64,.51,.41,.33,.26,.21. Rank-2 at depth 1 = r x .20 = .06-.10, below the depth-7 node (.21). **B=7 tree = chain.** B=8 adds one sibling (+.10, r=.5) = +2.4%. B=16 adds nine nodes worth .36-.61 = **+8.7 to +14.6% tau** (surrogate).
- a = 0.73 (temp-1 agentic, accepted about 2.4 = acceptance 0.29-0.39 x 7, tau about 3.40): chain masses .73,.53,.39,.28,.21,.15,.11. Rank-2 at depth 1 (r=.5) = .135 > depth-7 .11, so **B=7 swaps one node, +.025 (+0.7%)**. B=8 +.135 = +4.0%. B=16 next nine = .42-.71 = **+12.5 to +20.8% tau**.
- Per-round heterogeneity helps beyond this homogeneous model (low-confidence rounds branch early), so upper bands are stretched to B=8 +8%/+10%. The target may disagree with the surrogate, pushing them down. Real results decide, not this model.

Throughput, net factor = tau ratio / round ratio. Round ratio = (1 + rows_added x s / 52.5) x h, h = 1.07 tree overhead central (from `treeflash.md` L88), s = verify ms/row. Baseline 78.04 t/s, T=0 short M1 shape.

| T=0 | rows added | tau | s=0 | s=0.65 | s=3.1 |
|---|---|---|---|---|---|
| B=8 | +1 | +2 to +8% | 0.95-1.01x | 0.94-1.00x | 0.90-0.95x |
| B=16 | +9 | +9 to +15% | 1.02-1.07x | 0.92-0.97x | 0.67-0.70x |

In t/s, from 78.04: B=8 about 70-79; B=16 about 52-84. **np1 27B T=0: 0.90-1.01x at B=8, about 0.67-1.07x at B=16, central near 0.95x (tree overhead included).** Lower than `treeflash.md` L90's +3% central, because that used +5-15% tau at B=8 and the budget model above says B=8 is nearly the chain.

Temp-1 agentic :8083 (same round-time assumption, not measured in that traffic; tau from the a=0.73 block): B=16 at +12.5 to +20.8% tau gives 1.05-1.13x at s=0, 0.95-1.02x at s=0.65, 0.68-0.74x at s=3.1. So the only plausible positive region is low-acceptance traffic at low row slope.

Sensitivity: h=1.00 (no tree overhead) raises every cell by 7%.

**A3B:** CPU with MTP, no block drafter, so no lattice: 0% today. A tree on MTP/CPU is priced by CAFE-2 (jetspec.md L127: T(5)/T(1) 1.79, cited from that dive) and is net-negative at any useful width. GPU-eventual analysis as 27B.

**MI210 small models at high concurrency:** the paper has batch 1 only. JetSpec's Table 11 (via `jetspec.md` L71) has best budget 32 at batch 16 on H100. A dense small model is the build-cheapest case, but without a head and row-slope data it is not estimable.

**Evidence grade: B- for the algorithm, C for transfer.** The algorithm and proofs are simple and I checked them; code matches paper. Tables have oracle budgets, no error bars, one group, dense + MoE only; but B=16 is corroborated by a separate group's tables. No hybrid, no DFlash2, no B<16.

## DSpine overlap

A different bet. DSpine spent draft-side cost for block depth; DDTree spends none on drafting and adds no depth. It reallocates a fixed row budget from low-probability deep nodes to probable branches. At B = chain length that is free but, at our acceptance and depth, nearly a no-op. Above chain length it is the same row-cost wall DSpine hit (speculative-decoding.md:1600): +rows must repay in tau. So: different mechanism, same economic constraint on widening.

## Adversarial pass (bounded, one WebSearch)

No independent criticism or stand-alone replication found; results are restatements (themoonlight, catalyzex, papers.cool, takara tldr, wizwand). The TreeFlash and JetSpec papers do run DDTree as a baseline, which is the only independent corroboration (read directly). CaDDTree (surfaced by search, not read) argues acceptance length is monotone in budget, so maximising it ignores verify cost and favours bigger trees; that matches this dive's reading of Eq 6, which has no cost term.

## Derived actionables

| # | Item | Disposition |
|---|---|---|
| 1 | Amend DF2-LAT: arm **D1** (DDTree on unary marginals with dumped log_z) and **D2** (Algorithm 1 with per-parent child rankings on the selector Q), B in {7,8,16,32}, exact replay against Y. Add the dump field and a shadow-draft mode at every token position so the policy simulation is unbiased (live-round-start paired comparison is a stopgap). Report tau_tree/tau_live by B and acceptance stratum (dev and holdout), and joint with measured row slope | TASK, merge with TreeFlash arm D and JetSpec A1 as one amendment to DF2-LAT. Decision rule as a product: tree line opens only if tau_ratio(B) / ((1 + (B-7)*s/52.5) * 1.07) >= 1.05 with bootstrap lower >= 1.00 for some B <= 16 at measured s. TreeFlash's fixed 1.10 gate at B=8 is too strict under this model (B=8 is expected near +2-8%), and B=16 needs slope data |
| 2 | Measure MI210 verify ms/row at 8/16/32 rows, 27B | Keep JetSpec A2, no duplicate |
| 3 | Level-synchronous hybrid tree verify on HIP | DORMANT, gated on 1 and 2 and C8-NP4-GARBAGE, as in wave-1 |
| 4 | Budget-picking arm for CAFE-3 per round | Note only: Eq 6 has no cost term, so any shipped budget must come from a cost model; CAFE-3 owns that if the line opens |
| 5 | AR head training on top | Already in TreeFlash item; try D2 first (selector is the zero-training conditional) |
| 6 | Tree on A3B MTP / CPU | DECLINE for now: no block lattice and the CAFE-2 row cost (cost-model reason, not software). Revisit if a block drafter ships for A3B |
| 7 | Do not quote the paper's best-budget gains (B up to 512) as a chain-to-tree effect at our shape | Knowledge note |

## Dive-surfaced sources

Wave cap reached. Noticed but not listed: CaDDTree (search result only, id not confirmed by this source); DART (2601.19278, reference [15]) is already covered in the index.
