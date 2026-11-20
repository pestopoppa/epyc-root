---
schema: epyc.brief.v1
id: LOOP-91
box_text_sha: 1182ab3f4886458e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-inference-research:scripts/kernel_rnd/autokernel/controller/hypotheses.py
approach: 'D10: AutoKernel remaining structure (controller, evaluator, execution, schemas, tests; C3-04 at controller/hypotheses.py:1551
  and 30+ more). Requires K1, K2, K3 merged; start with git fetch and rebase. Unit C4-C6 findings were never adversarially
  verified: verify each first-hand. Step: C3-04 with test.

  '
acceptance: cd /workspace/repos/epyc-inference-research && python3 -m pytest -q scripts/kernel_rnd/autokernel/controller -x
  -q
non_goals:
- no work before K1-K3 merge
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-inference-research:scripts/kernel_rnd/autokernel/controller/hypotheses.py: 04bced1a4255f23d94d68359f08e6c0e5613f7cf
---
