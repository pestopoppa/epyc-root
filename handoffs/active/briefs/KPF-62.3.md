---
schema: epyc.brief.v1
id: KPF-62.3
box_text_sha: 247ada7a8faaded9
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Selector: head window W=64 + check-layer K deviation + group-contiguous runs. First step: selector function with
  unit tests.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-62\.3\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
