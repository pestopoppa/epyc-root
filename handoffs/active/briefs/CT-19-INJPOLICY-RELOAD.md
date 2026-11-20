---
schema: epyc.brief.v1
id: CT-19-INJPOLICY-RELOAD
box_text_sha: 9393b1d98d6f92e2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/services/document_preprocessor.py
approach: 'Default is already warn in a0062fe0. At the next API-only reload boundary (orchestrator_stack.py reload orchestrator,
  by the session that owns it) pick up the default, then confirm one document-body injection warning on a flagged fixture.
  First step: write the fixture check script so the confirmation is a single command after the reload.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_document_body_injection_policy.py
new_tests:
- tests/unit/test_document_body_injection_policy.py
non_goals:
- no service reload by the brief executor
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/services/document_preprocessor.py: 7cf45fd5a73943f36d13aacb7c5f900a39f8fd41
---
