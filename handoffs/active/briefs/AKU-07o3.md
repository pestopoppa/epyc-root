---
schema: epyc.brief.v1
id: AKU-07o3
box_text_sha: t:9c954e0abfb2c195
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-root:scripts/vidya/adapters/autokernel_final_trial.py
approach: 'In _witness_receipts, require contention fail when report.facts.foreign_gpu_consumers.status is present and forbid
  pass unless it is none; projection only, no new ladder.

  '
acceptance: pytest tests/vidya/test_autokernel_final_trial.py -k foreign
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-root:scripts/vidya/adapters/autokernel_final_trial.py: 2f130dd31dcd44ff8d36f507bfc73fbfd9fb4c09
---
