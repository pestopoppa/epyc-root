---
schema: epyc.brief.v1
id: LOOP-54
box_text_sha: 7f8d4e22da715faf
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:.github/workflows
- epyc-root:artifacts/operator/staged
approach: 'CI green: F2 owner branches forked before 561e6ae9b still run on every push (owners merge main: codex3-root-lane,
  m4-c3, lb49, lane/codex-refactor-*); F4 stale workflow registrations (66 with no file on main); root tests already green
  from d69e5165d; the operator applies the staged ratification-exemptions-add-20261109.json for the dashboard step. Step:
  list red workflows per branch with gh, message each owner to merge main, delete stale registrations. Done when every main
  is green and no owner branch is red.

  '
acceptance: gh run list --branch main --limit 5 --json conclusion
non_goals:
- no workflow re-enable of the AutoKernel guards (operator click)
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:.github/workflows: tree:59e94e22588451f9c5f0d0042bf339c0696888fc
    epyc-root:artifacts/operator/staged: tree:5ee438301754f656d8a59fedc3430fb40d36543e
---
