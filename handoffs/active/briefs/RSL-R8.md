---
schema: epyc.brief.v1
id: RSL-R8
box_text_sha: t:778792b767911e16
author: planning
written: '2026-11-24'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/graph_kld_policy.json
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/stage_bodies.py
approach: 'graph_kld_policy gains frontdoor A3B CPU and planned A3B MI210 entries with their own floors; the oracle-kld stage
  looks up the policy per candidate path from served_set and reports quality-ungated when none exists

  '
acceptance: nice -n 19 taskset -c 84-87 python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_stage_bodies.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/graph_kld_policy.json: c590400a7d52920592215f54512cf4baa43562cc
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/stage_bodies.py: 9f066e390ba10a7d20432308fd3d4765b53024ab
---
