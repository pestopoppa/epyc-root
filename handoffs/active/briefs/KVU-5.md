---
schema: epyc.brief.v1
id: KVU-5
box_text_sha: ac5e67aef488bab1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/inference/prefix_cache.py
approach: 'Preemption on the orchestrator side: when the pool is short, cancel the youngest. First step: preemption policy
  in SharedKVPoolAdmission with a unit test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-5\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/inference/prefix_cache.py: 23f4c015bdad34fe24d38892014396d1561ced6d
---
