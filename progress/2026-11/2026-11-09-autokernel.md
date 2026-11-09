# 2026-11-09 AutoKernel

## LB3.2 re-pinned to C8; pair invalid

- r4 refused rc=6 before any arm: champion had moved 17 commits past C7r 62cb6a6af. Operator chose to rebase.
- New package `/mnt/raid0/llm/tmp/akx-lb32e-20261109`: G = store image `cpu-20261108-1bda248e3-c8rbseq`, M = clean 1bda248e3 with GGML_CPU_PROF=ON, champion guard relaxed to descends-from.
- Result PAIR_INVALID: GM SPLIT_UNRESOLVED (max F 9.54%, max S 51.9%, seed `node:norm`); MG INVALID on the 5% overhead gate (N=3 +8.77%, N=5 +5.21% at 64k). No retry under the one-fixed-pair rule.
- Filed under AKX-ALL-LB3.2, not ticked.
