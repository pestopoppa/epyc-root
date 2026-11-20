---
schema: epyc.brief.v1
id: KPF-62.6
box_text_sha: aff8bb897aadec1e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'G3 harness on the frozen corpus (needs corpus manifest hash in P0_THRESHOLDS section 8). First step: harness runner
  that refuses without the hash.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-62\.6\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
