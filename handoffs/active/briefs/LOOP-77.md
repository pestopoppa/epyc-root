---
schema: epyc.brief.v1
id: LOOP-77
box_text_sha: cc7a00192d5c4a3b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave1.json
- epyc-root:research/refactor-audit-2026-10/K2-CURRENT-SOURCE-REVIEW.md
- epyc-inference-research:scripts/kernel_rnd/autokernel/evaluator/api.py
approach: 'K2: evaluator/execution integrity package (C4 findings were never adversarially verified): verify each first-hand
  against current source (K2-CURRENT-SOURCE-REVIEW.md) and skip any that does not reproduce. C4-05 (evaluator/api.py:1442,
  :1355) is incomplete and C4-05/C4-06 affect keep/discard and binary attestation: write a failing test demonstrating the
  defect before fixing. Kernel defects go to the champion fold, not here.

  '
acceptance: cd /workspace/repos/epyc-inference-research && python3 -m pytest -q scripts/kernel_rnd/autokernel/evaluator -x
  -q
non_goals:
- no llama.cpp patch
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave1.json: bb376c30536182d94ec0a5257025cef934db2098
    epyc-root:research/refactor-audit-2026-10/K2-CURRENT-SOURCE-REVIEW.md: 475b4052be27c024bb21af66ad8235f836357883
    epyc-inference-research:scripts/kernel_rnd/autokernel/evaluator/api.py: 833934a01af10da480f784cadb3101809f24de17
---
