---
schema: epyc.brief.v1
id: KVU-12.1
box_text_sha: f2a5bd908fc74108
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/f8-kvu121-kpf18-verdicts/kvu121_decide.json
approach: 'Checkpoint-policy arms in the CPU np x ctx matrix on frontdoor 35B-A3B and 27B: four hybrid-checkpoint arms. First
  step: arm definitions and sweep manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-12\.1\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/f8-kvu121-kpf18-verdicts/kvu121_decide.json: 8c43fa9c96ac10d109ecf87cef0f170eec09c8eb
---
