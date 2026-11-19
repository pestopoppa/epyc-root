# 2026-11-09 apr2 rerun-fixes

Four failed rows diagnosed from their logs; each republished under a new id (rank >= 22), smokes queued by the keeper. Nothing ticked.

| failed row | root cause | fix | new row |
|---|---|---|---|
| td16-label-word-bias-20261109 | N == Nq: native prompt drops `Question.criteria`; J empty: Qwen3.6 thinking-ON ate the budget | conditions in question text, arm-prompt guard, `--reasoning off` + preflight (orchestrator `6fa88ace`) | td16-label-word-bias-r2-20261109 (rank 23, 150 valid units seeded) |
| parser-odl-hybrid-200pdf-20261109 | doc 141 failed once, no in-run retry, `ok+failed_final` 199 != 200, no scoring | in-run retry then censor, always score (`parser_quality_common.py`) | parser-odl-hybrid-200pdf-r2-20261109 (rank 26) |
| dripreview1-r3-20261109 | port 9461 held by r2's still-running smoke | own port 9463 | dripreview1-r4-20261109 (rank 22) |
| sliders-phase0-fb5-coder30b-20261109 | preflight record all strings; first question outlasts a 4-core smoke | numeric preflight fields | sliders-phase0-fb5-coder30b-r2-20261109 (rank 24) |

Belief tags: `[belief: cc]` on DAR-SPLIT-1 (routing-program.md) and M-15 (memory-program.md) had no register row; `wrap-up.md` Step 2 requires the row in the same commit. Added both through `cli.py conclusion add` (`data/belief/committed_conclusions.jsonl`).
