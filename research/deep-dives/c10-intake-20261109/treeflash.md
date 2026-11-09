# TreeFlash (arXiv 2606.03819v1), intake-2664 Stage-2 dive

- read_depth: FULL (body, Tables 1-3, Limitations, Appendices A-D; figures as captions only)
- version: https://arxiv.org/html/2606.03819v1 (LaTeXML, dated 02 Jun 2026 in the source)
- sha256 of raw html: 465b38668a97b8d735de4d21aa4dcd02e05c8634572ab18337f86888ebdb6b18
- companion repo read (not executed): github.com/ETH-DISCO/TreeFlash @ f5c20b468cb77a33115103df2ce205c5cee6d912
- lane_head: ad1e73525f6b86077936d9a1065f4da35c27c9d5. Locators `L<n>` are lines of the converted text.

## Bottom line

1. **Yes, tree drafts need branch-aware target verification.** TreeFlash verifies all B nodes in one target forward pass with an ancestor-only attention mask. It is one pass, not one pass per branch, but every row needs its own ancestor context. The paper only tests attention-only targets, so it holds no evidence on recurrent state.
2. **Equal-verifier-cost gain over DFlash chain (B = gamma = 16 rows): +17.1% speedup, +24.8% tau (paper mean).** The tree structure alone gives most of it; DDTree already reaches 72% of the speedup gain. The AR head adds only +3.9% speedup at B=16 and +1.4% / +3.0% on MT-Bench T=1 (Qwen3 4B / 8B), the dataset closest to our low-acceptance traffic.
3. **The headline AR benefit is largely already in our drafter.** DFlash2 ships a predecessor-conditioned top-16 lattice. What we lack is the tree use of it and hybrid tree verification.

## Mechanism

DFlash one-shot block gives per-position marginals. TreeFlash adds a SwiGLU head: `h' = h + SwiGLU(norm(h) :: e_prev)` (L584-588). Two-stage construction: DFlash marginals pick top-M per depth (M=16), the head computes conditional distributions for those M predecessors per depth (M*gamma evaluations independent of B), then OPT-Tree greedy selection on CPU (L599-604, App. B L1070-1098). Verification is an equality check on a deterministic tree (L598), so one target pass with `candidate_position_ids = depth + start` and a compiled ancestor mask (repo `tree_flash.py` L432-454, L793-813), and the KV is compacted to accepted nodes (`_compact_dynamic_cache_tail`, L392-430, L834).

## Claim table

| # | Claim | Status | Locator | Verbatim |
|---|---|---|---|---|
| 0 | Beats all baselines everywhere | CONFIRMED on tables, narrowly: smallest cell MT-Bench 4B T=1 B=16 is 2.88 vs 2.84 speedup, with stdev 0.01 each | L755 | "TreeFlash consistently outperforms all baselines in every evaluated configuration" |
| 1 | Abstract: +12% tau, +9% speedup over marginal trees | PARTIAL: true only at B=64. B=16 is +7.5% / +3.9%. Abstract does not state the budget | L62, L765 | "improving over marginal tree drafting by 12 % higher block efficiency and 9 % higher speedup" |
| 2 | Tree structure, not AR, is the main driver | CONFIRMED, and this is the load-bearing reading | L757 | "The major driver of this improvement is the transition from chain to tree drafting" |
| 3 | O(1) drafting retained | PARTIAL: O(1) in B for the head, but tree build is CPU-iterative and M costs throughput (M<=32 recommended) | L603, L1069, L822 | "Part 2 is done iteratively on the CPU" |
| 4 | Gain grows with budget, most in high acceptance | CONFIRMED on tables; recomputed tau TF64/DDT64 +12.1 to +14.1% across the mean rows; MT-Bench +10.2% vs MATH-500 +13.3% stated | L764-769 | "the benefit of AR-approximation is most pronounced in high-acceptance regimes" |
| 5 | Scaling B is cheap | OVERTURNED for serving use by the authors' own caption: single-batch only | L774, L829 | "this is not the case in multi-batch settings, where the compute overhead of tree verification typically favors smaller draft budgets" |
| 6 | Head alone carries the gain | CONFIRMED (Table 3 mean: Frozen 8.6 / 7.4 vs TreeFlash 8.6 / 7.5 at T=0/1, B=64) | L750 | "keeping the backbone frozen has similar performance" |
| 7 | Non-linearity is needed | CONFIRMED on Qwen3 4B only (Linear 7.9 / 6.8 vs 8.6 / 7.5 means) | L749 | "Using a SwiGLU layer instead of a linear layer provides the largest improvement" |
| 8 | Scope: Qwen-family, dense only | CONFIRMED scope limit; recurrent/hybrid targets absent | L838 | "TreeFlash is evaluated exclusively on Qwen-family models" |
| 9 | Training hours/hardware cost | NOT-FOUND-IN-SOURCE. Only 100k samples, one epoch, effective batch 128, 128 anchors, peak LR 1e-4 are stated (L636-640); hardware for training not given (eval on GH200, L654) | L636-640 | n/a |

## Baselines and fairness

- DFlash, DDTree, TreeFlash share a checkpoint (L626); TreeFlash also fine-tunes. Table 3 "w/o AR-app." (fine-tuned DFlash, no head) is 7.6 / 6.6 means vs DDTree 7.7 / 6.6, so fine-tuning alone adds nothing: the comparison is fair.
- EAGLE-3 is unfair and the authors say so (trained on different data, L493-494, L623): ignore those rows.
- Sample size: 64 per dataset (L634). T=0 rows have no variance reported. The +1.4% MT-Bench cell is near noise.
- **No DFlash2 baseline.** The relevant comparator for us is absent.

## Verify-cost model

The paper gives none. Derived round cost `rho = tau / speedup` (vanilla steps per round) from the mean rows:

| | DFlash16 | DDTree16 | TF16 | DDTree64 | TF64 |
|---|---|---|---|---|---|
| Q3-4B T=1 | 1.338 | 1.384 | 1.430 | 1.348 | 1.393 |
| Q3-8B T=1 | 1.337 | 1.381 | 1.436 | 1.341 | 1.385 |
| Q3-4B T=0 | 1.331 | 1.381 | 1.431 | 1.348 | 1.392 |
| Q3-8B T=0 | 1.331 | 1.375 | 1.438 | 1.336 | 1.383 |

So going from 16 to 64 verified rows costs roughly nothing in this regime, and DDTree64 is cheaper than DDTree16, which I cannot explain from the paper (different run conditions is possible). This is a GH200 single-batch, 4B/8B regime far from any row-cost slope.

In-house, derived from `dspine-c9-gpu-tune-20261108` RESULT.json (27B Q8_0, q8_0 KV, np1, 65536 ctx, short M1 prompts, temp0, 128 tokens, MI210; tau = mean_accepted_len_derived + 1; round = tau / tok/s):

| Arm | tok/s | tau | round ms |
|---|---|---|---|
| no-draft | 32.95 | 1 | 30.3 |
| DFlash2 n7 | 78.04 / 83.7 | 4.10 / 4.41 | 52.5 / 52.7 |
| DSpine Q8 n7 / n11 / n15 | 71.4 / 56.07 / 52.94 | 3.79 / 4.23 / 4.16 | 53.1 / 75.5 / 78.6 |

Eight extra rows at fixed block cost +25 ms, about 3.1 ms/row, not smooth (n7 to n11 +22 ms, n11 to n15 +3 ms). Treat as an upper bound because DSpine's draft cost may also vary with n-max. Against that, `c8-decode-x-sweep` np1 (LongHealth ~32.7k, kernel handoff L54) gives X3/X5/X7 round times of about 60/57/62 ms assuming tau = 1 + X*acceptance: flat in rows 4 to 8. Verify rows are prompt-shape-dependent on MI210; the M1 slope is not universal. The acceptance field in this RESULT is ambiguous (field 0.47 vs label 0.78 for the same arm), so I use mean accepted length only.

## Drafter training

Required for the paper's method: head is trained, backbone from an existing DFlash checkpoint (L610, L832), teacher-forced (L835). Hours and training hardware are not stated. Frozen-backbone variant is sufficient (Table 3, claim 6), so a head-only pilot is the right shape. Our pipeline does not exist yet (DF2-FT-1), a build cost. But see next section: we may not need this head at all.

## What it needs from the target

- Multi-branch: yes. One target pass over B nodes, each with ancestor-only context (repo L793-813).
- Rollback: to the accepted path by node index, not position (compaction, L834). Equal length and contiguous chains are not guaranteed.

## Hybrid-SSM analysis (read at champion d210f85c2)

Not a mathematical kill; a priced port.

- Recurrent state is per-sequence with one tail cell. `seq_cp` shares the tail cell (src/llama-memory-recurrent.cpp L262-295); `seq_rm` partial rollback refuses a shared cell ("a cell shared by several sequences cannot move back for only one of them", L196-199), and rollback is bounded by `rs_max`, single-use (L201-210).
- `split_equal` with sequential and coupled sequences is an error (src/llama-batch.cpp L511-512), and the hybrid path forces sequential when `n_rs_seq > 0` (src/llama-memory-hybrid.cpp L89-90). So a branch-as-sequence tree batch with coupled shared prefixes fails today. Uncoupled sequences duplicate shared-prefix rows (rows = sum of leaf depths).
- Ragged per-seq lengths mean extra full weight sweeps (DF2-LB1, speculative-decoding.md:1569).
- Existence proof that tree over Gated DeltaNet works: intake-501 and intake-447 index entries describe a llama.cpp DDTree with 3 CUDA kernels for tree-aware rollback (budget 22). These are index records, not re-verified here; do not cite numbers.

Workaround design (no math barrier): level-synchronous verification. Each depth is one width-parallel recurrent step; per-node state selected by `parent_index` gather from the previous depth (generalising the existing per-row rollback snapshots, `rs_idx`). Attention masks come from `n_seq_id` membership (leaf sets). Width costs state memory and a gather, not extra sequential recurrent steps. Rough build: 5-10 agent-days, unmeasured estimate. Hazard: per-row snapshots and non-sequential splits are exactly the C8-NP4-GARBAGE area (hybrid.cpp L89 comment), so that must be resolved first.

## Estimate for our regime (ESTIMATE, not measured)

Base: 27B DFlash2 n7, np1, temp0, short M1 prompts, MI210, tau 4.10, 78.04 t/s, round 52.5 ms, 8 verify rows.

**Equal rows (B=8, the 'equal verifier cost' case).** Paper equal-row tree gain was tau +18.6% (DDTree16/DFlash16, 4B T=1), +26.3% on MT-Bench, but at gamma 16. Discount for: block 8 cap (shallow), DFlash2 selector already captures the AR conditioning, so only the branching remains.
- tau gain assumed +5 to +15%; round overhead +0 to +15% (hybrid state selection, tree build).
- low: 1.05/1.15 = 0.913 -> 71 t/s. high: 1.15/1.00 = 1.15 -> 90 t/s. central 1.10/1.07 = 1.03 -> 80 t/s (+3%).

**Wider (B=16).** Additional tau about +10% (paper TF16 to TF64 is +22% for 4x rows; about +10.5% per doubling) with verify rows +8 at 3.1 ms/row = +25 ms (+47%). Net (1.10*1.10)/(1.47*1.07) = 0.77x on short prompts. If rows are flat as on LongHealth, up to about +20%. This is the regime that cost DSpine n15 0.815x on M1 / 1.045x LongHealth.

**A3B.** Served CPU with MTP, not a block drafter; no drafter lattice; tree is not applicable today. CAFE-2 T(5)/T(1) = 1.72, CI 0.25-3.18, inconclusive. Expected change 0%, since nothing can be run; GPU-eventual analysis matches 27B.

**Concurrency.** np4 X3 about equals X7 (kernel handoff L54), so added verify rows do not pay. MI210 small models at high concurrency: the authors' caption predicts smaller budgets. Expected net <= 0.

**Evidence grade: C+.** Credible controlled tables for dense Qwen on GH200, 64 samples per set, one group, public code, no hybrid and no DFlash2 baseline. Our-regime number is an inference with a wide band.

## DSpine overlap

Different at equal rows: rows are reallocated from the low-probability deep tail to probable branches, with no extra draft cost. Same bet at B>8: spends verify rows for acceptance, hitting the same row-cost wall that closed DSpine (speculative-decoding.md:1600). It is not a deeper block bet (B-16 is free to stay at block 8, unlike DSpine and DF2-BLOCK16), so the wall applies only to widening.

## Adversarial pass (WebSearch 2 queries, standard)

- No independent replication or criticism found. Results were the paper, aggregators and restatements.
- CaDDTree (id not observed in the paper, seen via search of DDTree) argues the node budget must be chosen per round from modeled latencies, which agrees with our row-slope finding. Not read here.
- DFlash-TfM and DARTree appear as later related methods via search; unread, ids not from this paper's text.
- Open: search results did not expose any multi-batch tree-verify measurement. Independent verdict: none.

## Derived actionables

| # | Item | Disposition |
|---|---|---|
| 1 | Add arm D to DF2-LAT: OPT-Tree over the existing DFlash2 top-16 lattice with pair scores at B in {8,16,32}, simulated exactly against the temp-0 target trajectory. Same dump, same window, no new compute. Rule on holdout: tau_tree(B=8)/tau_live >= 1.10 with bootstrap lower >= 1.05 opens hybrid-verify design; < 1.03 closes the tree line | TASK (amendment to DF2-LAT, no new box) |
| 2 | Level-synchronous hybrid tree-verify port | DORMANT: trigger = arm D passes AND C8-NP4-GARBAGE resolved; no box until then |
| 3 | SwiGLU AR head training (frozen backbone) | MERGED into DF2-FT-1 pipeline as a follow-on experiment if arm D opens; DFlash2 pair scores are the zero-training substitute to try first |
| 4 | Temp>0 tree proposals | Covered: DF2-PM and SPEC-PIT.1 gates apply if ever run; no task |
| 5 | CAFE-3 per-round budget choice | Note only: adaptive width should take B as a tree budget if the line opens |
| 6 | np4/small-model high-concurrency trees | DECLINE: np4 X3~X7 and the caption L774 show added rows do not pay; no np4 evidence in the paper |
| 7 | CPU / A3B MTP tree | DECLINE today: no block drafter lattice on A3B; revisit if a block drafter ships there |

## Dive-surfaced sources

| id | Settles | Note |
|---|---|---|
| arXiv:2604.12989 (DDTree) | Chain-to-tree gain at equal budget independent of the AR head; ~72% of the speedup here is that method | Cited in paper L985, not in the index copy |
