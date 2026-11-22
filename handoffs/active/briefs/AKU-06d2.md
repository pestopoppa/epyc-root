---
schema: epyc.brief.v1
id: AKU-06d2
box_text_sha: t:8c683f5b049cfa90
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/operation_accounting.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_control.py
approach: 'Define the outcome rules for an actor-only operation (planner/critic accepted, no build child) so it settles as
  advice-ready rather than failed, without prerequisite authority.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_actor_preparation_state.py -k actor_only
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/operation_accounting.py: 46fea2360590c08c461c1f991a9a28a14637280c
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_control.py: 04ed5ca4da1d60868e5e47cc0cfbec30806818e4
---
