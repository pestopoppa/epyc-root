# 2026-10-28 ws58 results filing: LB4.9 FU-DIVERGE-02 run

- `codex-inf81-lb49-fu-diverge-02-20261028` (codex-ni, diagnostic) ended rc0 complete 22:45:36Z. Result: `/mnt/raid0/llm/tmp/codex-ni-lb49-fu-diverge-02-20261028/runs/run-1793227386*/RESULT.json`.
- Outcome: knob proven ON (argv `--cpu-iqk-fa on`, `iqk_runtime_enabled: true`). Step-0 logits vs r2 baseline: 129,280/129,280 differ, max abs 0.409 logit units (floor 0.0), mean abs 0.069; top-1 token 11111 unchanged (margin about 3.4), top-5 identical, top-20 overlap 19/20 with adjacent swaps.
- Meaning: class (b), a real, deterministic numeric difference from iqk-FA at step 0 that does not flip top-1; it does not explain the missing prompt echo. Acceptability is undecided (no predeclared tolerance).
- Next: FU-DIVERGE-02 ticked; FU-DIVERGE-04 (teacher-forced steps 1-7 ON vs baseline), FU-DIVERGE-05 (localise the drift), FU-OPCASES-01 addendum (compare against FA tolerance). FU-DIVERGE-03 stays open. [belief: cc]
