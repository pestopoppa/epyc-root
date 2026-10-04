# KVU-19b GPU validation — durable copy (2026-10-04)

Copied from `/mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/` (not durable) by the workspace-ec wrap-up.
Handoff: [`handoffs/active/kv-unified-stack-rollout.md`](../../handoffs/active/kv-unified-stack-rollout.md),
KVU-19b / KVU-19b-1 / KVU-19b-fold-c1 / KVU-19b-rework-c2 / KVU-19b-gap.

| File | What |
|---|---|
| `FOLD.md`, `DESIGN.md` | Fold record and design note for branch `experimental/fa-maskskip-batched-20261004` (`1bceceb05`, `c7f5ac9ad` on `a0d0ae238`) |
| `gpu_slot2.sh`, `gpu_slot2.run.log` | The slot runner and its console log |
| `slot2-20261004T044448Z/summary.txt` | Start here: exactness, kernel µs, p3batch, batched-bench, test-backend-ops |
| `slot2-…/exact*.txt` | Per-case harness-v2 comparisons (GPU arms and CPU reference) |
| `slot2-…/perf2_results.txt`, `p3batch_results.txt`, `bb_*.jsonl`, `tbo_*.log` | Raw per-section results |

Verdict: commit 1 (vec routing for one row per sequence) wins and is recommended for the fold. Commit 2 (WMMA
sequence tiles) is mixed (-14% aligned 4×8, +13% uneven) and breaks skip on/off bit-identity on 6 cases, so it
is being reworked. Caveat: the slot's host side ran unlocked on CPUs 160-183 during a peer's held CPU window
(INC-20261004-subagent-unlocked-cpu-in-held-window), so host-bound absolute numbers are noisier than usual.
