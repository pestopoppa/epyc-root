# Non-Inference Backlog — history through 2026-09-27

> **Historical ledger only; current work lives in [../active/non-inference-backlog.md](../active/non-inference-backlog.md).**

Superseded planning material moved out of the active handoff at the workspace-8d wrap-up of 2026-09-27. Nothing here is
dispatchable. The graph below is the April 2026 Round-2 priority view; every node in it is closed or retired except
NIB2-18, which stays open in the active file (gated on DS-E1 evidence).

## Dependency & priority graph

```
HIGHEST LEVERAGE (do first):
├── NIB2-01 (_batch_llm_query)          → unblocks REPL efficiency wins
├── ~~NIB2-12 (parallel seeding)~~       → retired 2026-06-13; old two-stream design is stale/unsafe
├── NIB2-09 (</think> investigation)    → unblocks Qwen3.5 hybrid budget control
└── NIB2-06 (vision tool register)      → proactive vision delegation

CODE THAT WILL PAY OFF WHEN INFERENCE RUNS:
├── NIB2-13/14 (OpenDataLoader swap + bench)
├── NIB2-16/17 (DAR-3/DAR-4)
├── NIB2-18/19 (DS-6/DS-7)
├── NIB2-20 (AM layer-adaptive)
├── NIB2-25/26 (CF Phase 3b/3c)
└── NIB2-21/22 (ColBERT + tool-output harness scaffolding)

CLEAN-UP / LOW-EFFORT:
├── NIB2-04 (DAR-2 unit test)
├── NIB2-07 (retrain-routing archive move, 5min)
├── NIB2-27 (canonicalizer doc)
├── NIB2-28/29/30 (infra)
└── NIB2-05 (top-k instrumentation)
```

## Superseded Status line (as of 2026-09-27)

**Status**: ACTIVE — 43 Round-2 baseline tasks catalogued + 4 May 2026 cluster supplements. 40/43 Round-2-baseline done. Open Round-2 baseline (3 items): NIB2-18, 43, 46. NIB2-33 moved to excluded (hermes-outer-shell auth deferral). May 2026 cluster supplement: NIB2-49 and NIB2-50 are closed from existing May evidence; NIB2-51 X-MAS non-inference scaffolding is closed as default-off shadow/advisory telemetry; NIB2-52 StreamingLLM C++ scaffold landed and its 4-axis bench sweep is inference-gated.
