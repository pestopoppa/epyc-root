# 2026-10-28 ws58 results filing: LB4.9 FU-DIVERGE-01 run r2

- `codex-inf81-lb49-diverge-20261028-r2` (codex-ni, diagnostic) ended rc0 complete 22:23:05Z. Result: `/mnt/raid0/llm/tmp/codex-ni-lb49-diverge-20261028/runs/run-1793225782*/RESULT.json` (the single run dir; full path in `COMPLETE.json`).
- Outcome: baseline x2 and candidate `--cpu-iqk-fa off` step-0 logits are bitwise identical (0 of 129,280 differ, top-20 identical, DS41, 24 threads, one prompt).
- Meaning: verdict (c) undetermined. Step-0 nondeterminism floor is 0.0, so the earlier text divergence is not step-0 noise; candidate-off equals baseline so the build is not at fault; `--cpu-iqk-fa on` step-0 logits were never captured, so an iqk-FA numeric difference is not demonstrated.
- Next: FU-DIVERGE-02 (iqk-FA ON step-0 capture) and FU-DIVERGE-03 (teacher-forced decode steps, llama-cli template check) filed under AKX-ALL-LB4.9. FU-DIVERGE-01 not ticked. [belief: cc]
