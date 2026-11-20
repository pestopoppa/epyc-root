---
schema: epyc.brief.v1
id: KVU-23
box_text_sha: e1c531c491bf7ebc
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Layer-3 autopilot residency policy (shadow-measure, vet allowlist, bounded auto-select); trigger second MI210.
  First step: shadow-measure design and the recorder stub.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-23\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
