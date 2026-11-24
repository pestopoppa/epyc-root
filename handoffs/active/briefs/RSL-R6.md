---
schema: epyc.brief.v1
id: RSL-R6
box_text_sha: t:685447d29980c616
author: planning
written: '2026-11-24'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/stage_bodies.py
approach: 'stage_bodies reads model GGUF, device and served argv per candidate path from census_coverage.served_set (on research
  main); each path gets its own greedy cell and A/A floor; a path without a cell is reported ungated

  '
acceptance: nice -n 19 taskset -c 84-87 python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_stage_bodies.py
non_goals:
- no DS41-Flash
tier: terra
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/stage_bodies.py: 9f066e390ba10a7d20432308fd3d4765b53024ab
---
