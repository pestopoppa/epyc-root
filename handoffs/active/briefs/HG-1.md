---
schema: epyc.brief.v1
id: HG-1
box_text_sha: t:22d29cd4d288e652
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/proactive_delegation/policy_reducer.py
- epyc-orchestrator:src/proactive_delegation/review_envelope.py
approach: 'Threshold policy from H4/H5 reliability-by-confidence-bucket curves, per domain. Method: from the review ledger
  (orchestrator src/trace/review_ledger.py) bin decisions by confidence, compute observed reliability per bucket per domain
  with CIs, pick the confidence cut where reliability crosses the requirement, write it as a policy_reducer input. Evidence
  does not exist yet (stub, deliberately last): first step is the curve-extraction script plus a report stating n per bucket;
  thresholds stay observations until RC-6a merges.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_reliability_buckets.py
new_tests:
- tests/unit/test_reliability_buckets.py
non_goals:
- no enforce-mode flip
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/proactive_delegation/policy_reducer.py: ef0244aaf50936ee3d3dcedcdede90afdb77370c
    epyc-orchestrator:src/proactive_delegation/review_envelope.py: c0c8fcbb2f39367b46bae87ebee5d5dfc743f605
---
