---
schema: epyc.brief.v1
id: V11-FA-4a
box_text_sha: 97a2c58e1eccd372
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:ggml/src/ggml-cuda/fattn.cu
approach: 'Decide the exact-set control for synthetic bias1024 stress cases then rerun the band comparison. First step: control
  definition and rerun manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*V11\-FA\-4a\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/fattn.cu: f0661dc65131db25cf836a7f6cab3b621e39ce8e
---
