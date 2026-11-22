---
schema: epyc.brief.v1
id: AKU-09g4
box_text_sha: t:73b0e305f4cf6159
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_control.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/runtime_aggregates.py
approach: 'At controller startup rebuild the in-memory candidate replay cache from the candidate journal before first snapshot,
  so unified_candidate_status.v2 reports replay_verified true after restart; no publisher-thread replay.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_runtime_aggregates.py -k restart
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_control.py: 04ed5ca4da1d60868e5e47cc0cfbec30806818e4
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/runtime_aggregates.py: 46c59ca03518c6ff108d559270b60e2370af64b1
---
