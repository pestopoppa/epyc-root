---
schema: epyc.brief.v1
id: KPF-60.GPU-X
box_text_sha: 965617c7a3c3d9bb
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Turn the GPU timing into a crossover row (27B native measurement later; source build model-free). First step: source-bound
  build and linked tests.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-60\.GPU\-X\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
