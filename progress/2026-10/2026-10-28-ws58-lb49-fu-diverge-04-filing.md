# 2026-10-28 ws58 results filing: LB4.9 FU-DIVERGE-04 run

- `codex-inf81-lb49-fu-diverge-04-20261028` (codex-ni, diagnostic) ended rc0 complete 23:19:12Z. Result: `/mnt/raid0/llm/tmp/codex-ni-lb49-fu-diverge-04-20261028/runs/run-17932291322*/RESULT.json`.
- Outcome: knob proven per arm (baseline x2 iqk off, candidate `--cpu-iqk-fa on`, `iqk_runtime_enabled: true`). Teacher-forced steps 1-7: baseline x2 bitwise identical; ON differs in all 129,280 logits every step, max abs 0.82 to 3.80 (step 5), mean abs 0.13 to 0.58; top-1 equal at all 7 steps (margins 1.28 to 11.0), top-20 overlap 17 to 19 of 20. First flip: none through step 7.
- Meaning: the step-0 drift is not a one-off and grows during decode, yet never changes the argmax on this easy n=1 prompt; thin-margin positions untested. Diagnostic, no tolerance verdict. FU-DIVERGE-05 and FU-OPCASES-01 were not in this run.
- Next: FU-DIVERGE-04 ticked; new FU-DIVERGE-06 (longer horizon, several prompts, flip rate vs margin); FU-DIVERGE-05, FU-OPCASES-01 and FU-DIVERGE-03 stay open. [belief: cc]
