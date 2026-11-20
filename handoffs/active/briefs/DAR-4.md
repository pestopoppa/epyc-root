---
schema: epyc.brief.v1
id: DAR-4
box_text_sha: cd732e2810cd06e7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:orchestration/model_descriptors.yaml
approach: 'First concrete step for: Its prior null (P4.1.3: label-proxy IRT +9.02pp, observed-outcome IRT 0.00pp) is now explained
  — the observed outcome was constant. Re-run before drawing any conclusion about the model class. Scope (a. Box has no done-when;
  acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_dar_4.py
new_tests:
- tests/unit/test_dar_4.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:orchestration/model_descriptors.yaml: 404870b26f030b01116a84aee1df7628c272a5fa
---
