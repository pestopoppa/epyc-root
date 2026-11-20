---
schema: epyc.brief.v1
id: KPF-18-S1
box_text_sha: 62a22043a389708a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'ONE 27B GPU sweep window for the whole KPF-18 GPU half (prereq KPF-18.0e): one load, one shared anchor bank. First
  step: sweep manifest listing every sub-item; stop when all filed.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-18\-S1\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
