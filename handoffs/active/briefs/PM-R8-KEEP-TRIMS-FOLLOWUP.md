---
schema: epyc.brief.v1
id: PM-R8-KEEP-TRIMS-FOLLOWUP
box_text_sha: t:b725ba479819b57b
author: wrap-up
written: '2026-11-25'
accepted: owner
where:
- scripts/coordination/churn/keep_failed.py
approach: 'Read findings F3/F4/F9 in /mnt/raid0/llm/tmp/review-r8-keep-20261125.md; one commit each; run rowflow unit and
  replay suites; deploy via deploy_rowflow

  '
acceptance: python3 -m pytest scripts/coordination/tests/test_keep_failed_evidence.py
non_goals: []
tier: local
grounded:
  at: '2026-11-25'
  blobs:
    epyc-root:scripts/coordination/churn/keep_failed.py: fdbc27f5f729eaada92a803ae989c9e254239347
---
