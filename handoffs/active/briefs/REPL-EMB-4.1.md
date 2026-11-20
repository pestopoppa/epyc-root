---
schema: epyc.brief.v1
id: REPL-EMB-4.1
box_text_sha: 0c0c488b3f030710
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/repl_environment/context_bundle.py
- epyc-orchestrator:tests/unit/test_oab7_context_bundle.py
approach: 'Add context.search(): repl_view closure plus namespace key, op=''search'' pull accounting, lazy index on first
  call (the bundle is built twice per request), describe and render_root_block entries; extend the dir(view) test in test_oab7_context_bundle.py.
  ContextBundle.search was LOW blast radius; do not touch get.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_oab7_context_bundle.py
non_goals:
- no default-on
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/repl_environment/context_bundle.py: 71d6613f751afc7a0a28754dd19af820d638ce5b
    epyc-orchestrator:tests/unit/test_oab7_context_bundle.py: 3849ee8a2e0cd469d7d82e715fb3e0b75ff095ba
---
