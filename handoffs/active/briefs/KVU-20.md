---
schema: epyc.brief.v1
id: KVU-20
box_text_sha: 54ef4d145b266ba7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/inference/trunk_prefill.py
approach: 'Cross-slot prefix fork anchored on recurrent checkpoints plus trunk-first dispatch. First step: trunk-first dispatch
  ordering in the orchestrator with a unit test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-20\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/inference/trunk_prefill.py: d010a59f22c2882984a1ec4949e377da8f9ce167
---
