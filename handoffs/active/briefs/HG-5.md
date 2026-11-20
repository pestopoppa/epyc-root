---
schema: epyc.brief.v1
id: HG-5
box_text_sha: t:821a9bd0f8e53bd1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/openai_compat.py
- epyc-orchestrator:src/api/models/openai.py
- epyc-root:artifacts/ni08/hg5-force-source-20261008/README.md
approach: 'Source child VB-HG5-FORCE-SOURCE-CONFORMANCE accepted (force escalation default off, 87/87 controls). Remaining
  parent scope: runtime/H3 scope and the prospective request-event writer/reader: surface /v1 response fields for the escalation
  decision and the x_* override to force/suppress escalation in the live path, test off/default/auto goldens unchanged. First
  step: list the response fields and add them additively behind the existing flag with goldens.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_v1_escalation.py tests/unit/test_v1_escalation_off_golden.py
non_goals:
- no activation or efficacy claim
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/openai_compat.py: f83a4473bda2e3e0b064f2fbe373e1755069c4b3
    epyc-orchestrator:src/api/models/openai.py: 13841f37fbdef376972d16e9e8d8206b0c50ed52
    epyc-root:artifacts/ni08/hg5-force-source-20261008/README.md: 3f367305dc08de76c72bab16b6127ccd4485edfd
---
