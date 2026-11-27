---
schema: epyc.brief.v1
id: AP-W66-TRACE
box_text_sha: t:621e2d6bdd969c9d
author: planning
written: '2026-11-27'
accepted: auto
where:
- epyc-root:docs/reports/autopilot-w66-replay-plan.md
- epyc-root:artifacts/analysis/ap-w66-replay-inputs/requests.json
approach: 'Reproduce those denominators from all 140 receipts, keeping cancellations and unknowns explicit. Rank by seconds
  consumed and by excess seconds against a matched reference. Join predecessor requests, cache reuse, overlap on other slots,
  prompt shape, MTP proposals/accepts and server events. Locate the benchmark behind the expected speed, and tabulate its
  commit, model/quant, context depth, KV, sampler, generation length, speculation and batch occupancy alongside W66. Where
  they differ, report the mismatch. Output a hashed replay manifest, timing breakdown, comparison reference and the hypotheses
  the live pairs can distinguish.

  '
acceptance: all 140 receipts reconcile with the published per-mode totals, four replay inputs have verified bytes and predecessor
  plans, and a benchmark comparison records matched and mismatched settings.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:docs/reports/autopilot-w66-replay-plan.md: ec15417f839d78efe2cc894c3d9a77e3c8fc43d9
    epyc-root:artifacts/analysis/ap-w66-replay-inputs/requests.json: 56ef151a0476edce35db77c09c0044db4b0e9043
---
