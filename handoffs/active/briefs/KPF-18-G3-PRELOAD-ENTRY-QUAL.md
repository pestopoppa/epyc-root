---
schema: epyc.brief.v1
id: KPF-18-G3-PRELOAD-ENTRY-QUAL
box_text_sha: ef482a2c9b9b3e51
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Qualify receipt-backed preload driver entry ordering with a sealed copied group-3 driver main and fake guard; one
  CPU quarter 300 s. First step: build and run normal-ordering case.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-18\-G3\-PRELOAD\-ENTRY\-QUAL\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
