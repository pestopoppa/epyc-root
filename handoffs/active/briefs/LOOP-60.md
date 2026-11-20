---
schema: epyc.brief.v1
id: LOOP-60
box_text_sha: 62bdb1aa1c97aa88
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:.github/workflows/autokernel-guards.yml
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-root:research/refactor-audit-2026-10/data/orch_baseline_failing_ids.txt
approach: 'RESUME-5: repair the AutoKernel guards CI infrastructure BEFORE K3 (dependency installation, independent jobs/steps,
  one shared executed-suite specification, honest collection floors); keep K4''s post-prune size ratchet after K3. Reconcile
  baseline collection/failure identities per test id (the B2 producer E comparator matched 396 baseline ids to passing candidate
  cases; the two known historical failures are the containment/EXDEV pair) instead of accepting aggregate counts. First step:
  split install from test in autokernel-guards.yml and pin the executed-suite list.

  '
acceptance: python3 -c "import yaml;yaml.safe_load(open('/workspace/repos/epyc-inference-research/.github/workflows/autokernel-guards.yml'))"
non_goals:
- workflow stays disabled until the operator re-enables it (LOOP-93)
- no post-prune ratchet before K3
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:.github/workflows/autokernel-guards.yml: 9792eef2212f89e0149045bae1b597ca728a702d
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-root:research/refactor-audit-2026-10/data/orch_baseline_failing_ids.txt: 6bb4bb925cb93c2a4abcca076ba710f906777b28
---
