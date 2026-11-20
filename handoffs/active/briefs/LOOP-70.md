---
schema: epyc.brief.v1
id: LOOP-70
box_text_sha: 9a77601851b769ac
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave1.json
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/run.py
approach: 'Merge the AutoKernel live-loop bugs branch (K1; refactor/autokernel-rollback-reviewed-01a16fc3 in the research
  repo holds the C1-05 tested/reviewed work, held unmerged under RESUME-3) only after the AutoKernel launch hold lifts, with
  a deliberate re-pin (workspace-58). First step now: finish the C1-05 WIP (regression test plus loop suite) so the merge
  is one command when the hold lifts.

  '
acceptance: cd /workspace/repos/epyc-inference-research && git merge-base --is-ancestor refactor/autokernel-rollback-reviewed-01a16fc3
  origin/main
non_goals:
- no merge while the AutoKernel launch hold is active
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave1.json: bb376c30536182d94ec0a5257025cef934db2098
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/run.py: 6b7280304b3e420ce45b984ec1ed847f5f9a04c4
---
