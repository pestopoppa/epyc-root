---
schema: epyc.brief.v1
id: KPF-23
box_text_sha: 7f8b5df91211f3c7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:tests/unit/test_prefix_cache_policy.py
approach: 'Decision, not measurement: id_slot pinning stays session-continuity only (idle slot, never hard pin); 256-char
  hash routing retired on kvu servers; canonicalize_prompt kept only if INF-05 KV-6 shows it cheap. Record in the prefix_cache.py
  module docstring (lines ~33-35 currently say ''waits on'') and INF-05 rows. Box has no runnable done-when; acceptance is
  the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_prefix_cache_policy.py tests/unit/test_prefix_cache.py
non_goals:
- no new KV-6 measurement run
- no change to chat lane slot handling
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:tests/unit/test_prefix_cache_policy.py: 3a52ad9829b93ee71ad5c0e2284188cf355925d6
---
