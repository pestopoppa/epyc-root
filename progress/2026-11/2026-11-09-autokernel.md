# 2026-11-09 AutoKernel

## LB3.2 re-pinned to C8; pair invalid

- r4 refused rc=6 before any arm: champion had moved 17 commits past C7r 62cb6a6af. Operator chose to rebase.
- New package `/mnt/raid0/llm/tmp/akx-lb32e-20261109`: G = store image `cpu-20261108-1bda248e3-c8rbseq`, M = clean 1bda248e3 with GGML_CPU_PROF=ON, champion guard relaxed to descends-from.
- Result PAIR_INVALID: GM SPLIT_UNRESOLVED (max F 9.54%, max S 51.9%, seed `node:norm`); MG INVALID on the 5% overhead gate (N=3 +8.77%, N=5 +5.21% at 64k). No retry under the one-fixed-pair rule.
- Filed under AKX-ALL-LB3.2, not ticked.

## LB3.2 median-overhead pair: order-sensitive

- Fresh pair lb32-c8m-20261109 under `AMENDMENT-median-overhead-r6.md` (median 64k overhead gate, seed-stability rule).
- PAIR_ORDER_SENSITIVE: GM LANE_LARGE (max F 10.14%), MG SPLIT_UNRESOLVED (max F 9.35%); max S about 52% and seed `node:norm` in both. Stop-on-futility, no retry.
- Filed under AKX-ALL-LB3.2, not ticked. Corrected the earlier arm-order remark to the single-repetition spike finding.

## Operator wrap-up

- Wiki sweep: tracked delta (6 sources) compiled into `wiki/hardware-optimization.md`; prune candidates none; README and belief ledger fresh.
- Derived actionables, explicit declines: (1) no box for a new LB3.2 predeclaration handling F near the 10% line, because the operator gates any further attempt; (2) median-gate branch `ak/lb32-median-overhead-20261109` not merged, because the pair did not decide and no consumer exists.
- Kept: `ak-lb32e-msrc` (named by the r5 package, gate refused), `ak-lb32f-rsrc` (branch unmerged). Result ticks this wrap-up: 0.
- Session bus drain refused: `autokernel` is not a roster id in config.yaml.
