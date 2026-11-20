---
schema: epyc.brief.v1
id: HPR-REPUBLISH-RUN15
box_text_sha: 84bb029fc58f243d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Republish the hpr launcher row on filler_run15.sh (it still names filler_run13.sh). First step: republish via the
  row publisher and confirm the launcher argv names run15.

  '
acceptance: grep -qE '^ *- \[x\] \*\*HPR\-REPUBLISH\-RUN15\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
