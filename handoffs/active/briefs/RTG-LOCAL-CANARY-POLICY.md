---
schema: epyc.brief.v1
id: RTG-LOCAL-CANARY-POLICY
box_text_sha: t:ca6358d5b3954b2a
author: planning
written: '2026-11-28'
accepted: auto
where:
- epyc-orchestrator:orchestration/model_descriptors.yaml
- epyc-orchestrator:src/routing_bindings.py
- epyc-root:docs/reports/a3b-full-tools-canary-20261127.md@06b010e1361768b7d1d65b83cb4428df28a0d1c3
- epyc-root:docs/reports/27b-q38fn-full-tools-repeat-20261127.md@06b010e1361768b7d1d65b83cb4428df28a0d1c3
approach: 'Bind each observation to task, brief specificity, model, thinking mode, sampling, full tool profile, serving context,
  phase budget and actual guidance. Separate candidate checks, paid advice and owner acceptance. Q38FN OFF supplied two initial
  accepted implementations; A3B supplied accepted constrained implementations and guided analysis; 27B delivered MM under
  two fresh driving variants after initial failures. Treat those as candidate routing hints. An enabled warning which never
  fired establishes no warning effect. Replay the real descriptor and planner/report path with successful, incorrect and censored
  examples. Include all fallback and paid input/cache/output costs, worker wall and accepted-work rate, preserving missing
  values. Reuse the existing main-only baseline. Do not infer a device comparison or intrinsic capability ranking from unmatched
  studies.

  '
acceptance: the normal descriptor/report consumer distinguishes observed success, censoring, guidance, reviewer and owner
  outcomes; held-out controls preserve unknown cost and quality; proposed routes name evidence and uncertainty without automatically
  changing production routing.
non_goals: []
tier: local
grounded:
  at: '2026-11-28'
  blobs:
    epyc-orchestrator:orchestration/model_descriptors.yaml: dc3a71bcc0be57000e6850b55866afd5800647fa
    epyc-orchestrator:src/routing_bindings.py: 0f258cf26c57d29e93659ebf77e3db529b71ec4f
    epyc-root:docs/reports/a3b-full-tools-canary-20261127.md@06b010e1361768b7d1d65b83cb4428df28a0d1c3: 0ea990435bb2440c1d789ad2cc0df9142a388c2b
    epyc-root:docs/reports/27b-q38fn-full-tools-repeat-20261127.md@06b010e1361768b7d1d65b83cb4428df28a0d1c3: 5365e6dfa4fed72e3f85798df3b3d8c2ed7f0bf8
---
