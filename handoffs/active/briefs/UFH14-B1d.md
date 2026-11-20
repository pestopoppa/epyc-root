---
schema: epyc.brief.v1
id: UFH14-B1d
box_text_sha: 100f09dba2ecd072
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/design/ufh14-b1-timeout-stackchange-item-20261003.md
- epyc-orchestrator:src/api/routes/chat_pipeline/routing_decision.py::resolve_timeout
- epyc-orchestrator:src/features.py::derived_prefill_timeout
approach: 'Apply Option A from the stack-change item: the registry role timeout becomes the decode SLA (values unchanged,
  registry COMMENT-only edits) and resolve_timeout adds the derived prefill allowance behind the existing default-off derived_prefill_timeout
  flag. First step: a unit test pinning resolve_timeout = decode SLA + derived prefill for a full-context request; then one
  stack-change package (skill stack-change) for the operator signature.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_resolve_timeout_derived_prefill.py
new_tests:
- tests/unit/test_resolve_timeout_derived_prefill.py
non_goals:
- no registry value changes
- no apply without signature
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/design/ufh14-b1-timeout-stackchange-item-20261003.md: 5774c829761af9058dc27ac69fef002b55edf6ec
    epyc-orchestrator:src/api/routes/chat_pipeline/routing_decision.py: 0a887dd03cda096cb6389fea1bf4cb535f09f5de
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
---
