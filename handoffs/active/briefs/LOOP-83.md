---
schema: epyc.brief.v1
id: LOOP-83
box_text_sha: d7a37bac7d374f59
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-orchestrator:src/api/routes/openai_compat.py
- epyc-orchestrator:tests/unit/test_openai_compat_default_golden.py
approach: 'D2: API layer de-duplication of openai_compat and /chat (A1-05 at openai_compat.py:1240, :1558 plus A1-06, A1-15,
  A1-19, A1-20, A1-12, A1-10, A1-14, A1-16, A1-18, A1-09, A1-07). Requires O1 (LOOP-65, LOOP-72) merged. Pin behaviour FIRST
  with golden tests for streaming and non-streaming of every /v1 mode and both /chat/stream paths, then de-duplicate. Coordinate
  with HS-OD-4 (max_tokens) which edits the same loops.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_openai_compat_default_golden.py
non_goals:
- no behaviour change without a golden update
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-orchestrator:src/api/routes/openai_compat.py: f83a4473bda2e3e0b064f2fbe373e1755069c4b3
    epyc-orchestrator:tests/unit/test_openai_compat_default_golden.py: 5dd9ebe659a5cb00f12d9c8dcb2ab4214ec2bbad
---
