---
schema: epyc.brief.v1
id: KPF-41
box_text_sha: d7c8d09339e94660
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Port the KPF fork work onto the v11 candidate (model-free source/build/fixture prerequisites first). First step:
  forward-port one feature per commit, starting with the first listed in the box.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-41\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
