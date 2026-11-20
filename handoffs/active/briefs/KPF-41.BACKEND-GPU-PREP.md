---
schema: epyc.brief.v1
id: KPF-41.BACKEND-GPU-PREP
box_text_sha: 725c6f6df0cc79e1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Publish backend GPU qualification with a model-free publisher witness for GPU residency. First step: run the publisher
  and file the witness.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-41\.BACKEND\-GPU\-PREP\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
