---
schema: epyc.brief.v1
id: LOOP-76
box_text_sha: 25ca9e956cdf46d3
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave1.json
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/run.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/validation_semantic_adapter.py
approach: 'K1 remaining: C1-24 (run.py:668, pyproject.toml:55, autokernel-guards workflow) and C2-06 (validation_semantic_adapter.py:41).
  C1-05 is already tested/reviewed on refactor/autokernel-rollback-reviewed-01a16fc3 and held unmerged (RESUME-3). Live loop
  only (serial_run -> run.main -> pool -> pipeline -> loop); do not delete dormant planes. Step: reproduce each finding with
  a failing test, then fix.

  '
acceptance: cd /workspace/repos/epyc-inference-research && python3 -m pytest -q scripts/kernel_rnd/autokernel/loop -x -q -k
  validation_semantic
non_goals:
- no kernel (llama.cpp) patch
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave1.json: bb376c30536182d94ec0a5257025cef934db2098
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/run.py: 6b7280304b3e420ce45b984ec1ed847f5f9a04c4
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/validation_semantic_adapter.py: c6f0c7a790eebd4f2d863c8e28981a440a30243e
---
