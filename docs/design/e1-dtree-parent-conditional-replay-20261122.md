# E1 — parent-conditional tree siblings for 27B + DFlash2: offline replay (2026-11-22)

This is a CPU-only replay. It adds no new measurement. Evidence: `/mnt/raid0/llm/tmp/ak-dtree-dump-gpu-20261120/out/dump-27b.jsonl`
(Qwen3.8-27B Q8_0 + DFlash2 n-max 7, temp 0, 3 P5 tasks x 1024 tokens, 550 live rounds, 546 of them aligned to the
target's greedy stream). The dump code is on branch `llama.cpp-experimental-dtree-dump-20261120`,
`common/speculative.cpp:1836`. `sc[d][q][k]` is the DFlash2 **selector score of candidate k at depth d, given
parent candidate q at depth d-1**. So the lattice is already parent-conditional, and the live chain walks it by argmax.

Method: greedy acceptance counts the tree nodes on the target path (prefix-closed), and tau = accepted + 1.
Trees are built best-first on path probability (softmax over the 16 candidates). The baseline is the selector's own
argmax chain (tau 5.02, which matches the measured 4.9-5.25). Speedup = tau/tau_chain x 45.5/(45.5+(B-7)s).
The 95% CIs come from a bootstrap over rounds (1000 resamples). The replay script stays in the session scratchpad and is not committed.

| B | arm | tau | ratio [CI] | x @2.39 | x @1.0 | x @0.5 |
|---|---|---|---|---|---|---|
| 3 | oracle | 3.91 | 0.78 | 0.98 | 0.85 | 0.81 |
| 6 | oracle | 6.29 | 1.25 [1.20,1.30] | 1.32 | 1.28 | 1.27 |
| 12 | oracle | 6.92 | 1.38 | 1.09 | 1.24 | 1.31 |
| 16 | oracle | 6.92 | 1.38 | 0.94 | 1.15 | 1.25 |
| 6 | marginal proxy | 3.85 | 0.77 | 0.81 | 0.78 | 0.78 |
| 12 | marginal proxy | 4.34 | 0.86 | 0.68 | 0.78 | 0.82 |
| 16 | marginal proxy | 4.47 | 0.89 | 0.60 | 0.74 | 0.81 |
| 6 | conditional (selector) | 4.80 | 0.96 [0.95,0.97] | 1.01 | 0.98 | 0.97 |
| 12 | conditional (selector) | 5.62 | 1.12 [1.10,1.14] | 0.89 | 1.01 | 1.06 |
| 16 | conditional (selector) | 5.79 | 1.15 [1.13,1.18] | 0.78 | 0.96 | 1.05 |

The oracle uses perfect conditional scores, limited to the top-16 lattice and at most 7 deep. An oracle tree of 7
nodes or fewer is just a perfect chain, so its gain measures drafter quality, not tree value. "Marginal proxy" uses
the parent-averaged selector score, because the dump does not contain the pre-selector per-position unary logits.
So the served marginal tree cannot be reproduced here: the proxy chain reaches tau 3.82, against 5.02 for the real chain.
**The missing dump is the per-position unary drafter logits and ranks, plus the target's full-vocabulary logits.**

**Verdict.** The stop-if-futile rule does not fire on the oracle, because the oracle at 6 nodes or fewer reaches 1.32x.
The realistic conditional tree adds +0.60 accepted tokens at B=12 and +0.77 at B=16. That is right at break-even (0.61 and 0.83), and
it loses at s = 2.39 ms/row (0.89x and 0.78x). To reach 1.03x it needs s <= 0.79 ms/row at B=12, or s <= 0.60 at B=16.
Conditional trees of 6 nodes or fewer never beat the chain (ratio 0.96). Tree drafting on 27B/DFlash2 stays closed
until the verify slope falls below about 0.8 ms/row.
