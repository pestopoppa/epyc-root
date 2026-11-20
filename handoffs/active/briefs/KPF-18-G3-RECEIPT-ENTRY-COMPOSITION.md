---
schema: epyc.brief.v1
id: KPF-18-G3-RECEIPT-ENTRY-COMPOSITION
box_text_sha: 2bd6829288d0a3fc
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Qualify real receipt verification at driver entry with the sealed copied group-3 driver main and small synthetic
  files; one CPU quarter 300 s. First step: run the fixture-digest composition.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-18\-G3\-RECEIPT\-ENTRY\-COMPOSITION\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
