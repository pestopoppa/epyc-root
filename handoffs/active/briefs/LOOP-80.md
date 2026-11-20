---
schema: epyc.brief.v1
id: LOOP-80
box_text_sha: c1f2d5225c952e10
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-inference-research:scripts/kernel_rnd/autokernel/check_regrowth_guards.py
- epyc-inference-research:.github/workflows/autokernel-guards.yml
approach: 'K4: AutoKernel regrowth guard and CI repair (operator decision 2026-10-24): infra repair before K3 (LOOP-60) and
  the post-prune size ratchet after K3; findings C2-04 (check_regrowth_guards.py:128), C5-02, C3-05, C1-02, C1-M3, C5-01,
  C6-01, C5-14, C6-13, C3-11, C2-02, C6-16. The operator re-enables the workflow in GitHub (LOOP-93). Step: C2-04 with test.

  '
acceptance: cd /workspace/repos/epyc-inference-research && python3 scripts/kernel_rnd/autokernel/check_regrowth_guards.py
  --help
non_goals:
- no workflow re-enable
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-inference-research:scripts/kernel_rnd/autokernel/check_regrowth_guards.py: d6159f05af351623d2cc6a9a1921e9e13654a028
    epyc-inference-research:.github/workflows/autokernel-guards.yml: 9792eef2212f89e0149045bae1b597ca728a702d
---
