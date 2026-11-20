---
schema: epyc.brief.v1
id: KPF-19
box_text_sha: 7a5676d86588a5e2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Rebase watch on server-context.cpp at the v11 rebase. First step: a conflict-risk checklist listing KPF hunks in
  server-context.cpp and a check script that detects them post-rebase.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-19\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
