---
schema: epyc.brief.v1
id: HSF-3
box_text_sha: bacf246e89d41a07
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/session/sqlite_store.py
approach: 'Measure the per-session inter-call gap distribution from existing logs (zero inference), per role and client class.
  First step: script over existing logs filing percentile table; stop when filed.

  '
acceptance: grep -qE '^ *- \[x\] \*\*HSF\-3\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/session/sqlite_store.py: 842175ef1dca1d442a698790667f419358d2f57f
---
