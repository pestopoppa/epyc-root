---
schema: epyc.brief.v1
id: LOOP-66
box_text_sha: cc87de95a08e1fe7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave1.json
- epyc-orchestrator:tests/conftest.py
approach: 'Adversarial review then merge of refactor/test-hazards (O7 partial, 4 commits ahead; its 3 original commits have
  no test report, so run the suites first). Priority per package: A6-01 tests aim destructive payloads at the REAL governance
  wiki, every such test must operate on a temp copy. Reviewed variant refactor/test-isolation-reviewed-01a16fc3 (6 ahead).
  Step: run the suites, review, merge via serialized_push.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && git merge-base --is-ancestor refactor/test-isolation-reviewed-01a16fc3
  origin/main
non_goals:
- no CI workflow added
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave1.json: bb376c30536182d94ec0a5257025cef934db2098
    epyc-orchestrator:tests/conftest.py: 42d3a8eb67e62164dfa23cd1772470680315aff0
---
