---
schema: epyc.brief.v1
id: UFH14-B-7
box_text_sha: f77e66ff40b7caf8
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/budgets.py
- epyc-orchestrator:src/repl_environment/types.py
- epyc-orchestrator:src/config/__init__.py
approach: 'Zero-inference part is audited (2026-11-02 note). Remaining decision step: sweep ORCHESTRATOR_REPL_TURN_N_TOKENS
  over [256,4096] on the S4 runner and compare with the RLM constants (depth 1 vs LLM_MAX_RECURSION_DEPTH=5, 120 s per-call
  timeout vs 600, state-variable termination). First concrete step: a comparison table file with each constant, ours vs RLM,
  and the sweep row spec. Stop when the sweep shows a plateau; decision feeds whether to lower the recursion/timeout defaults.

  '
acceptance: test -f docs/reports/rlm-budget-constants-comparison.md
non_goals:
- no default changes in this box
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/budgets.py: 23f15fe2008fefdecb25d30c927db74a1d7b98ea
    epyc-orchestrator:src/repl_environment/types.py: 6e89bb3fb6dfbe02e0597ef5c4d5ae58b700c237
    epyc-orchestrator:src/config/__init__.py: 571ee5ccf23b6a955ae9b7f7bb96a2a97e3a607b
---
