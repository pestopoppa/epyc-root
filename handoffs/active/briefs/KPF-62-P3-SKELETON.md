---
schema: epyc.brief.v1
id: KPF-62-P3-SKELETON
box_text_sha: 4391e8e61ab3f302
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Build the chunk-KV phase-3 skeleton in parallel with phase 1; carry the hybrid affine-state phase decision to the
  phase-0 drift-curve gate. First step: skeleton with interfaces only and a compile test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-62\-P3\-SKELETON\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
