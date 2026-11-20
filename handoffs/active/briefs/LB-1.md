---
schema: epyc.brief.v1
id: LB-1
box_text_sha: t:96b0aff133f4b640
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/autopilot/screening_tier_runner.py
- epyc-orchestrator:src/trace/review_ledger.py
approach: 'Reproduce and attribute the review-throughput regression on the RD-12 replay baseline: which calls dominate (plan-review
  prompt count vs prompt length vs architect queueing). Zero-inference offline attribution from the review ledger and serving_calls:
  per-call counts, prompt tokens and queue wait, decomposed. Stop when the decomposition sums to the observed delta; output
  a table.

  '
acceptance: test -f docs/reports/reviewer-lb1-regression-attribution.md
non_goals:
- no policy change
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/autopilot/screening_tier_runner.py: b0110ac99b04c08454b4d604e739f1d63f5cd43b
    epyc-orchestrator:src/trace/review_ledger.py: 8a8b73bae47b13671f3d5ea9badb6e39b243989a
---
