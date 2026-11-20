---
schema: epyc.brief.v1
id: LOOP-78
box_text_sha: d7910ef5406ce6ee
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-orchestrator:src/autopilot_core/infra_fingerprint.py
approach: 'P5: ONE batched evaluator era event (operator decision 2026-10-24): first B5-03 (normalize the evaluator fingerprint:
  AST of each .py with docstrings stripped and include_attributes=False, canonical JSON of yaml.safe_load for YAML; bump INFRA_FINGERPRINT_SCHEMA_VERSION;
  stamp evaluator_digest_method; test failing when a scoring-entry module sits outside DEFAULT_EVALUATOR_PATHS; compare_infra_fingerprints
  reports old-method fingerprints), then the remaining 19 B2/B5 findings in the same era. Step: B5-03 with its test.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_infra_fingerprint_normalized.py
new_tests:
- tests/unit/test_infra_fingerprint_normalized.py
non_goals:
- one era event only, no staggered evaluator changes
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-orchestrator:src/autopilot_core/infra_fingerprint.py: 5673025fff54213490cc6eee12a91ab1645074e3
---
