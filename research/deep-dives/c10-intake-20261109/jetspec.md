# JetSpec (arXiv 2606.18394v5) — Stage-2 dive, intake-2666

- **read_depth:** FULL. v5 text read end to end including appendices A-G and all tables.
- **version:** v5, 2026-10-03. Raw HTML sha256 `ba26192e0636b453ef75a375d7c31541d075c9b191c937442fa570d0580d3652` (`src/paper-2606.18394-v5.html`).
- **Also read:** arXiv HTML v1, v3, v4 (fetched to `dives/jetspec-src/`, compared by string search on the load-bearing passages, not read in full); abs page history; companion repo `hao-ai-lab/JetSpec` at `673267e4faba71a63099c258f0802c2f3aa44f8e` (2026-10-30), read selectively, never executed.
- **lane_head:** ad1e73525f6b86077936d9a1065f4da35c27c9d5.

## Verdict in one paragraph

JetSpec is DDTree (best-first tree over per-depth top-W lists) on a DFlash-style head with a causal attention mask, plus a tree-attention verifier. The "scaling ceiling" is never given a number. What is measured: going from budget 16 to 256 (16x the nodes) raises accepted length by 36-50% and speedup by 52-71% at temp 0, and it verifies 24-43 nodes per accepted token. The advantage over the best-tuned bidirectional head on matched data is +1.7% speedup (Table 7), not the +9.8% of the headline table. It needs spare accelerator width: on one H100 at batch 16 the best budget is 32 and budget 128 is worse. It was tested on no hybrid target, and the authors' own code refuses tree verification on hybrid targets. Expected np1 effect on 27B against DFlash2 n7: about 0.83-1.09x (estimate, s unmeasured), so not worth building ahead of two cheap probes.

## v1 to v5 changes (abs page plus version diffs)

Abs history: v1 2026-06-16, v2 06-24, v3 06-25, v4 09-27, v5 10-03.

| Change | v1/v3 | v4/v5 | Why it matters |
|---|---|---|---|
| Name | v1 "JetFlow" (84 mentions, 0 JetSpec) | "JetSpec" from v3 at latest | Search both names |
| Core mechanism | "predict multiple tree nodes in one forward pass while preserving branch-wise causal conditioning"; tree-causal mask over ancestors `M_v,u` (v1 Sec. 2.2, eq 5-6) | "predict distributions for multiple draft depths in one forward pass"; mask over positions `B_i,j` (v5 Sec 3.2 eq 3) | **The method description was rewritten from per-node branch conditioning to per-depth marginals.** v1 Appendix A.2 and A.4 already said off-argmax branches inherit a mismatched context, so v1's body contradicted its own appendix |
| Abs page abstract | "branch-wise causal conditioning" | **still** "branch-wise causal conditioning" on the abs page at v5; v5 HTML abstract says "causal information flow across draft representations" | Abs metadata is stale. Anyone quoting the abs page gets the retracted description |
| Serving prose | v1 "from 16 to 256 raises throughput from 443.3 to 968.2 TPS ... 3.09x to 6.75x"; v3 "from 16 to 128 ... 443.3 to 968.2" | v4/v5 "from 16 to 128 raises throughput from 224.0 to 553.3 TPS ... 1.75x to 4.33x" | Table 11 in v1 already showed 224.0-553.3. The older prose did not match the table; v4 fixed the prose. **A web summary quoting 6.75x is quoting a sentence the table never supported** |
| Related work | no Domino | Domino cited | Related work caught up |

Tables 2, 7 and 11 numbers I checked (9.64, 10.76, 553.3, 8.50) are unchanged v1 to v5. I did not diff every cell.

## Mechanism

- Head: DFlash-style, 5 layers, block 16, fused target hidden states injected as context, mask-token inputs (App D).
- The only architectural difference from DFlash: attention mask so position i sees prefix and earlier draft positions only (eq 3).
- Drafting: **one** forward pass yields r_1..r_N; take top-W per depth (W=7 in App A.1); best-first expansion by accumulated log r to node budget B (Alg 1). A node's children are the depth-(d+1) top-W list, the same for every node at that depth. No draft token is fed back in.
- Consequence, stated by the authors: r_2 "is anchored to the model's own argmax at depth 1" (A.4). The head sees draft-position hidden states, not sampled branch tokens. Coupling helps the top chain only; siblings get the same marginals. This is DDTree's scoring with better calibrated marginals.
- Verify: all B nodes in one target forward under an ancestor mask; accept deepest root-to-node greedy-consistent path (App E). Verified-node accounting is one round.

## What "scaling ceiling" means numerically

The paper offers Eq 1 and Fig 2 and no ceiling number. Eq 1 is the chain formula `Speedup = (1 - a^(N+1)) / ((1 - a)(Nc + 1))`, and it **assumes verification costs 1 at every N**, which is what the trees then spend.

Derived from Tables 1-2 (Qwen3-8B, temp 0, 8xH100, offline):

| Benchmark | tau B16 → B256 | Speedup B16 → B256 | tau/Speedup at B256 | Nodes verified per accepted token at B256 |
|---|---|---|---|---|
| GSM8K | 6.00 → 8.62 (+44%) | 4.80 → 7.82 (+63%) | 1.10 | 29.7 |
| MATH-500 | 7.75 → 10.76 (+39%) | 6.06 → 9.64 (+59%) | 1.12 | 23.8 |
| AIME25 | 7.23 → 9.82 (+36%) | 5.78 → 8.78 (+52%) | 1.12 | 26.1 |
| HumanEval | 5.32 → 7.78 (+46%) | 4.26 → 7.12 (+67%) | 1.09 | 32.9 |
| MBPP | 4.96 → 7.43 (+50%) | 3.97 → 6.73 (+70%) | 1.10 | 34.5 |
| LCB | 6.24 → 8.79 (+41%) | 4.77 → 7.67 (+61%) | 1.15 | 29.1 |
| MT-Bench | 3.98 → 5.94 (+49%) | 2.68 → 4.58 (+71%) | 1.30 | 43.1 |

So roughly 16x budget buys about 1.4-1.5x tau; 96-98% of verified nodes are discarded. The ceiling moved rather than broke: DDTree MATH-500 B256 8.78x / tau 9.81, JetSpec 9.64x / tau 10.76. Last doubling (128→256) on MATH-500 adds 0.81 accepted tokens for 128 nodes (158 nodes per extra token). Depth is capped at 16, so tau cannot exceed 16 whatever the budget.

**Non-monotone anomaly in the main tables:** MATH-500 tau is 8.23 at B32 (Table 1) and 7.42 at B64 (Table 2), AIME25 7.25 then 7.00. Tables 1 and 2 are not one curve. Table 1 caption does not state tree or linear, and the text calls B16 "a short linear draft". The curve above uses them together only with that caveat.

## Verify-cost model

- **Paper has none for trees.** App G measures DFlash (not JetSpec) with **linear** verification of N candidates on an H200. c = T_draft / (N T_verify).
- **The headline "c below 1%, falling to 0.05%" is an artifact of dividing by N.** Multiply c back by N (L=2048): T_draft/T_verify = 13.3% at N=2,4,8,16,32, 13.5% at 64, 14.1% at 128, 16.4% at 256, 18.4% at 512. The draft pass stays about 13-18% of one verification pass at every N. Draft and verify both scale with N, so nothing amortizes against the verify pass. c is only small relative to Eq 1's "1" if T_verify does not grow, which Table 12 cannot show because it never reports T_verify against AR.
- Evidence that verify width is near-free on H100 **offline**: tau/Speedup ≈ 1.09-1.15 at B256 means a round (256-node verify plus draft) costs about 1.1 AR steps, using custom Triton kernels. Repo engine note: "per-round verify ≈ per-token AR forward, ratio ≈ 0.95" (DESIGN.md), but that metric is verify-only, excludes the drafter.
- Evidence it is not free when serving: Table 11 below.

## Single accelerator, no spare concurrency (Table 11, vLLM, one H100, Qwen3-8B, MATH-500, greedy, TPS and speedup)

| Batch | AR | B16 | B32 | B64 | B128 |
|---|---|---|---|---|---|
| 1 | 127.8 | 224.0 (1.75x) | 312.0 (2.44x) | 447.3 (3.50x) | 553.3 (4.33x) |
| 4 | 203.8 | 433.6 (2.13x) | 534.2 (2.62x) | 664.2 (3.26x) | 742.9 (3.64x) |
| 8 | 246.2 | 679.3 (2.76x) | 839.3 (3.41x) | 859.3 (3.49x) | 803.5 (3.26x) |
| 16 | 287.3 | 891.8 (3.10x) | **1094.6 (3.81x)** | 995.8 (3.47x) | 803.1 (2.80x) |

- Offline MATH-500 at B128 was 8.93x; **serving at batch 1 on one H100 is 4.33x**, about half. Offline 8xH100 "up to 9.64x" is not the deployable number. This is what we would be comparing against.
- Budget 128 saturates: 803.5 TPS at batch 8, 803.1 at batch 16. Optimal budget falls with load (128 → 64 → 32).
- Table 11 lacks tau per cell, so per-round time cannot be derived. Budget-16 at batch 1 (1.75x) against offline B16 (6.06x) is a 3.5x gap that the paper does not explain.
- At zero spare width, the paper has no data on one accelerator being the bottleneck apart from this table. It runs AR at 127.8 TPS, i.e. AR at batch 1 leaves the GPU idle; the win is mostly filling width that AR wastes. MI210 is not an H100 and our per-node slope is unmeasured.

## Claim table

| # | Claim | Status | Locator | Verbatim |
|---|---|---|---|---|
| 0 | Up to 9.64x MATH-500, 4.58x chat | CONFIRMED as reported; PARTIAL as generalization | Abstract; Table 2 | "On H100 GPUs, JetSpec achieves up to 9.64 × speedup on MATH-500 and 4.58 × on open-ended conversational workloads" |
| 1 | Branch-wise causal conditioning (abs page) | **OVERTURNED** by v5 body and A.4 | Abs page; v5 A.2 | "off-argmax branches inherit a conditioning context that does not match their own ancestor token" |
| 2 | Causal head outperforms tree baseline | PARTIAL: +9.8% (Table 2, unweighted-training baseline) vs **+1.7%** vs tuned diffusion (Table 7) | Table 7 | "while the diffusion head is sensitive to" (γ) |
| 3 | Larger budgets win at low load, moderate under heavy load | CONFIRMED | App E, Table 11 | "relative gain decreases at larger batch sizes as verification and memory pressure become more prominent" |
| 4 | Per-token draft cost under 1% (and 0.05%) | PARTIAL: numerically right, misleading; draft/verify ratio is flat 13-18% | App G | "amortizes the parallel draft-head forward cost across the" |
| 5 | Generalizes across dense and MoE | CONFIRMED; **no hybrid or SSM target tested** | Sec 4.1 | "covering both dense and MoE target models" |
| 6 | Needs regenerated data | CONFIRMED | Table 6: JetSpec-Corpus 2.06x vs 4.80x GSM8K B16 | "Regenerated target-model sequences provide the strongest performance" |
| 7 | Training scale | CONFIRMED hardware; hours NOT-FOUND-IN-SOURCE | App D | "All draft-head training runs are conducted on 8 H100 GPUs with a micro batch of 2." |
| 8 | Temp-1 robust | PARTIAL: tables show temp 1 offline; vLLM path greedy only (App E); mechanism not derived for trees | Sec 3.4, App E | Eq 9 is chain rejection; repo `tree_accept` instead samples the target posterior and follows the matching child, q unused |

## Baselines and fairness

- **Missing DFlash2 entirely** (our incumbent; no DFlash2 or DSpark in v5). The "given told" incoherence is exactly what DFlash2's learned top-16 rank-256 transition selector addresses, so the claimed defect may not exist on our drafter. Biggest gap for our purpose.
- DDTree trained on the same data, good. But main-table DDTree is described as pure block-diffusion "trained without loss weighting", while Table 7 shows the unweighted diffusion head at 5.46x, and Table 2 DDTree at 8.78x. Same config cannot give both. Different training set (math-only ablation) likely explains it; the paper does not say. Treat as an internal inconsistency.
- Tuned comparison (Table 7, same data, MATH-500): causal best 8.50x / tau 10.00; diffusion best 8.36x / tau 9.72. +1.7% speedup, +2.9% tau.
- Causal head robust across γ (8.29-8.50) is the real contribution; diffusion ranges 5.46-8.36. That is a training-recipe robustness result, not throughput.
- AR denominator for offline speedup not stated as same kernels; repo DESIGN.md records an earlier verify-only `decode_cuda_speedup` that excludes the drafter. Tables' tau/Speedup ≈ 1.1 is consistent with drafter included, but I could not confirm from the paper.

## Drafter training

Required. Retrain head on target-regenerated sequences; 780K examples plus 20K CodeAlpaca, up to 512 anchors per example, on 8 H100 at micro-batch 2, ~3 epochs on the math-only cut (Table 4). Hours: not stated. Local pipeline does not exist (DF2-FT-1). A build cost, not a decline. Publisher heads exist for Qwen3-8B/30B-A3B, Qwen3.6-35B-A3B, Gemma4-26B, GPT-OSS-20B, Step-3.7-Flash, none for our 27B (JetSpec++ has a 27B checkpoint for its own different chain method). The 3.6-35B-A3B head loads only with a target path that would need the hybrid work below.

## Target requirements

Multi-branch forward over B nodes, tree attention mask (not a sequence position), per-node KV sharing, and on rollback a gather of accepted path nodes. llama.cpp has none of this for a batch shape other than per-seq chains.

## Hybrid SSM analysis (Qwen3.8-27B, A3B)

- **Paper:** silent. Zero hybrid or GDN mentions, and "dense and MoE" scope.
- **Authors' code refuses it:** `jetspec/core/model_runner.py:136` and `methods/jetspec_plus_plus/models/hybrid.py:195` raise `hybrid target supports only causal width-one trees`, and the hybrid path steps tokens one at a time. JetSpec++, whose Qwen3.8-27B results exist, verifies a chain. So the 27B-relevant public work is explicitly **not** tree verification.
- **Not a mathematical kill, a priced one.** GDN state at node v is f(state(parent(v)), x_v), a function of the path. It is well-defined on a tree. Workaround design: level-synchronous evaluation. Process depth 1..D, each level a width-B_d batch whose initial state is gathered from the parent's slot. GDN sweeps stay D (same as an 8-token chain's); width grows. Attention layers use the ancestor mask as usual.
- **Price:** (a) per-node recurrent state and conv tail, B copies of the per-layer state rather than 1, stored until commit; (b) level-gather/indexing per GDN layer; (c) a ggml graph op, not a batch shape: `split_equal` already turns ragged slots into extra full weight sweeps (DF2-LB1, speculative-decoding.md:1569), and a tree is maximally ragged. Lucebox did a DDTree port with tree-aware GDN rollback at budget 22 with 3 CUDA kernels (intake entry at index:25534-25540), which is an existence proof of the shape at small budget, on another GPU family and without a quality check.
- Conclusion: hybrid does not kill it. It adds an unmeasured per-node state cost on top of the attention cost, and the tree must stay narrow.

## Estimate for our regime (labeled ESTIMATE; no measurement in this dive)

Inputs. 27B np1, DFlash2 Q8_0 n7, temp 0, short M1 prompts, 128 tokens, MI210: 78-84 t/s, midpoint 81; acceptance 0.62-0.73, midpoint 0.68. Tokens per round ≈ 1 + 7 x 0.68 = 5.76; T_round ≈ 5.76/81 = 71 ms. Slope from LongHealth (32.7k RAG, np1, X3/5/7: 61.2 @0.89, 88.6 @0.81, 105.4 @0.80; tokens/round 3.67, 5.05, 6.6 give 60, 57, 62.6 ms): round time nearly flat, node slope **s ≈ 0-0.65 ms/node** within noise, 8 nodes or fewer only. **s beyond 8 nodes is unmeasured.** Scenarios s = 0.15, 0.65, 3 ms/node.

Tau gain proxy from the paper, budget ratio against its B16 baseline, mean of 7 benchmarks: x2 +2.5%, x4 +8.5%, x8 +34%. Depth is capped at 8 for us, so I discount x8 to +20% and tree-size labels B=15, 28, 56.

| B (from 8 nodes) | tau gain | s 0.15 | s 0.65 | s 3 |
|---|---|---|---|---|
| 15 | +2.5% | T 72.1 ms → 1.01x | 75.6 → 0.96x | 92 → 0.79x |
| 28 | +8.5% | 74 → 1.04x | 84 → 0.92x | 131 → 0.59x |
| 56 | +20% | 78.2 → 1.09x | 102 → 0.83x | 215 → 0.40x |

**np1 27B estimate: 0.83-1.09x DFlash2 n7, center near 0.95x** (s 0.15-0.65), before any GDN per-node penalty, which is entirely additive against the column. Real temp-1 agentic traffic (acceptance 0.29-0.39) has more to gain from breadth: MT-Bench temp 1 tau B16 → B64 +24%, → B128 +42%; with depth-8 discount and s 0.15-0.65, B28 is 1.05-1.19x and B56 0.90-1.18x (tau +30% after discount). Low confidence; the proxy is a depth-16 head on math-chat prompts. Temp-1 needs tree sampling (see claim 8), not just greedy.

**A3B:** CPU today, MTP; CAFE-2 r2 T(5)/T(1) = 1.79 (95% 1.60-1.97), about +20% per extra row. Budget 15 from 5 rows: 3.8/1.79 ≈ 2.12x round cost for +2.5% tau ≈ 0.48x. CPU tree is net-negative by measurement, and expert unions grow with width (8.0/17.9/34.4 at 1/5/9 rows). GPU-eventual A3B: no DFlash2 baseline exists to compare; same analysis as 27B.

**MI210 small models at high concurrency:** Table 11 says if used, budget ≤32 and dense-only. Best-case shape is a dense small model where tree attention is the only build. Requires a head per model; no such model is in our MI210 lineup, so unpriced.

**Evidence grade:** C. Authors' numbers on H100/H200 with custom CUDA kernels; no independent replication found; internal inconsistencies (Table 1/2 monotonicity, Table 7 vs Table 2 baseline, abs page drift); no comparison to DFlash2; no hybrid.

## DSpine overlap

Different bet on where the cost lands, same dependency on block-16 acceptance. DSpine (0.915x DFlash2 n7, n15 0.815x M1) spent **draft-side** time (serial bridge selector, vocab-wide tables) and lost it at the round level. JetSpec keeps draft to one pass and spends **verify width** instead, so the DSpine failure does not directly refute it. But it does not escape the closed finding: DSpine n15 shows that a wider block's extra depth did not repay its cost at np1 M1, and JetSpec's gains above depth 8 sit in the same range. The Qwen3-8B / depth-16 tau curve here does not transfer to block 8.

## Adversarial pass (bounded web search, 2026-11-09)

One search plus the HF card. Result: no independent replication or criticism found.

- Restatements only: Hugging Face papers, Gigazine, besthub.dev, sotaverified listing (no independent results).
- Adoption signal, not evaluation: NVIDIA NeMo Automodel has a `jetspec_core` component.
- Authors' own successor JetSpec++ (arXiv 2610.19792, from repo README) moves to two-GPU overlap and **chain** verification and compares against DSpark, not JetSpec trees. Reading it as a quiet concession is my inference.
- HF card for jetspec-Qwen3.6-35B-A3B has no model card content.

## Derived actionables ledger

| # | Action | Type | Notes |
|---|---|---|---|
| A1 | Add a **tree-headroom arm** to DF2-LAT: from the dumped top-16 per position, count how often the target's token at the first miss lies in top-W (W=2,4,7), and bound tau for B=15/28/56 under best-first | task (extends DF2-LAT) | Zero training, one MI210 window already scoped. Decides whether DFlash2's lattice has tree value at all; continuation beyond the miss is bounded, not exact |
| A2 | Measure **MI210 verify ms/node** for 27B at 8/16/32/64 nodes (GPU analog of CAFE-2, plus 1 no-GDN control) | task (extends DF2-LB1 / CAFE-3) | s is the whole uncertainty in the estimate. Sample during, fresh server per arm |
| A3 | Level-synchronous tree verify for hybrid targets on HIP (ggml graph + state pool + tree mask) | conditional task, gate: A1 shows tau ≥ +10% at B≤28 AND A2 shows s ≤ 0.5 ms/node | Build cost only. Workaround design above. Port shape exists on CUDA (Lucebox) |
| A4 | In DF2-BLOCK16 / DF2-FT-1 training, add a **causal-mask arm** (one mask line) and a γ sweep | addendum task | Table 7's robust finding. Cheap if a pipeline exists; depends on that pipeline. Do not train ahead of it |
| A5 | CPU tree verification for A3B | **decline** | Measured width cost (CAFE-2) gives about 0.48x estimate; a cost-model reason, not missing software |
| A6 | Load-dependent budget from Table 11 for CAFE-3 | knowledge note | Static budget optimum falls with concurrency; supports CAFE-3's direction |
| A7 | Do not cite abs-page "branch-wise causal conditioning" or prose "6.75x" | knowledge note | Both are stale against the tables and v5 text |

SPEC-CONF.1, DF2-PM unaffected, with one note for DF2-PM: repo's tree `tree_accept` is sample-then-lookup with q unused.

## Dive-surfaced sources (not in index copy)

1. arXiv 2604.12989 (DDTree, Ringel and Romano; id from the paper's reference list). Settles what the tree-construction baseline actually claims and whether causal heads matter once the head is tuned.
2. arXiv 2610.19792 (JetSpec++, id observed in the repo README only). Settles whether the authors abandoned tree verification for hybrid targets and how much overlap-based drafting returns on Qwen3.8-27B. It is the closest work to our actual target.
