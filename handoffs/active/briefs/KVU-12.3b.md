---
schema: epyc.brief.v1
id: KVU-12.3b
box_text_sha: 98866cbd586faa5f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/analytics-20261024/KVU-12.3a/analyze2.py
approach: 'Re-check KVU-12.3a under load once >=100 resumed turns at >=3 busy slots exist on :8083. First step: watcher check
  of the trigger and the rerun script.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-12\.3b\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/analytics-20261024/KVU-12.3a/analyze2.py: f9aab9b2e981aaf2d8dc36b495d2a047466ec0b9
---
