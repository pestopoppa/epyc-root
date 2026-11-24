---
schema: epyc.brief.v1
id: RSL-R3
box_text_sha: t:e0706f655dfcd3e8
author: planning
written: '2026-11-24'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/stage_bodies.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/op_perf_screen.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/served_shape_cases.py
approach: 'wire op_perf_screen as chain stage op-perf before ab-timing; add a 27B dense lane to served_shape_cases; screening
  PASS never read as keep

  '
acceptance: nice -n 19 taskset -c 84-87 python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_op_perf_screen.py nice
  -n 19 taskset -c 84-87 python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_stage_bodies.py
non_goals:
- not a promotion gate
tier: terra
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/stage_bodies.py: 9f066e390ba10a7d20432308fd3d4765b53024ab
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/op_perf_screen.py: null
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/served_shape_cases.py: 334640d45d5eabbb77f37b16aa3c950e19361f32
---
