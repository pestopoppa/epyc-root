---
schema: epyc.brief.v1
id: KVU-1a
box_text_sha: 5cf62f0e44bbfe52
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Apply patches/opencode-OPERATOR-ACK-limit.patch (operator, outside the repo) and verify the opencode limit. First
  step: check patch applies cleanly (dry-run).

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-1a\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
