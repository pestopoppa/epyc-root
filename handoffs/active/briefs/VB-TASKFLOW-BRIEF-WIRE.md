---
schema: epyc.brief.v1
id: VB-TASKFLOW-BRIEF-WIRE
box_text_sha: d948b94b0d25c99c
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/taskflow/brief.py::compile_brief
- epyc-root:scripts/vidya/adapters/README.md
approach: 'Project the P6 per-run verified outcome (arm label strong/self/none) through the existing measurement carrier;
  compile states enter only as structural observations.

  '
acceptance: 'the P6 pilot verdict carries a [belief: clm_<id>] tag and the planning-context canary passes'
non_goals:
- no new grading ladder
- no retrospective warrant for pre-P1 runs
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/taskflow/brief.py: e2d48f07fbb5c998e3d7ea9137c5f0faf60a3714
    epyc-root:scripts/vidya/adapters/README.md: e3c2ef4730581badb912189e13072542bc78a2cf
---
