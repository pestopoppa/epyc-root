---
schema: epyc.brief.v1
id: UFH14-B4d
box_text_sha: 0e84fc68688a0b61
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/design/ufh14-b4-prefix-cache-policy-20261003.md
- epyc-orchestrator:src/graph/helpers.py
- epyc-orchestrator:src/api/routes/chat.py
- epyc-orchestrator:src/api/routes/chat_pipeline/stream_adapter.py
approach: 'Add default-off flag per_query_material_at_tail moving CoT prefixes to the tail at the three sites: graph/helpers.py:936-940,
  api/routes/chat.py:1642-1644, chat_pipeline/stream_adapter.py:365-367 (RAG half is ABANDONED: rag_enabled off). Then A/B
  on missed_prefill_share and quality using the reconstructed runbook. First step: the flag + byte-identical-when-off test.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_per_query_material_at_tail.py
new_tests:
- tests/unit/test_per_query_material_at_tail.py
non_goals:
- no RAG-snippet move
- no default-on
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/design/ufh14-b4-prefix-cache-policy-20261003.md: ff90378ca69a29bef7be4957afa2290a89141d2e
    epyc-orchestrator:src/graph/helpers.py: eb930e373b30b65239d1a6e4d0b95d2e9eab124a
    epyc-orchestrator:src/api/routes/chat.py: f5b585c6c630d4001b279ea37be22e908fe3b54f
    epyc-orchestrator:src/api/routes/chat_pipeline/stream_adapter.py: 7f5d9c09b1a84bb2766572c2d986bb4858a86d98
---
