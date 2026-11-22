---
schema: epyc.brief.v1
id: AKU-06d4
box_text_sha: t:fa798ce1c3f59bb0
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/source_build_execution.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/unified_planner.py
approach: 'Persist each link through native ownership and refresh planner prerequisites from verified build results; never
  reuse a finished advice grant.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_source_build_execution.py -k chain
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/source_build_execution.py: 5db4c8f3aa75c99a6c1da2a4287ee4aac0e87b13
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/unified_planner.py: 913f9d3f9ff4724dd0d354f5d1b8e2bc93d985fb
---
