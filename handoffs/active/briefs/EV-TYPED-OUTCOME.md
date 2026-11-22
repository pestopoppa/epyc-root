---
schema: epyc.brief.v1
id: EV-TYPED-OUTCOME
box_text_sha: t:4dbb155a95c40d1d
author: intake
written: '2026-11-22'
accepted: pending
where:
- epyc-inference-research:scripts/benchmark
approach: 'Add an errored outcome with failure classes (environment, internal, verifier, verifier_timeout, agent_timeout,
  budget, cancelled) to the shared scorer result type; exclude errored attempts from pass-rate denominators and print them
  per class. Stamp a SHA-256 suite digest (canonical JSON of task rows plus pinned source) on every run record. Add a descriptive
  stratified exact one-sided regression report plus a per-task one-sided Fisher lost/gained call; futility-only, not a formal
  gate, until OP-ABSEQ/OP-PQP/OP-ALPHAWIN. Validate against hand-computed fixtures and replay over existing run records. Pattern
  from nanoeval (intake-2791).

  '
acceptance: python3 -m pytest -q tests/test_typed_outcome_regression.py
new_tests:
- tests/test_typed_outcome_regression.py
non_goals:
- no formal gate use
- no inference
tier: terra
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/benchmark: tree:4a6481255d63e44a9d465d19dda64aed1c509788
---
