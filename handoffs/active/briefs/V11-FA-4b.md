---
schema: epyc.brief.v1
id: V11-FA-4b
box_text_sha: 8b2e37a27b167e97
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:ggml/src/ggml-cuda/fattn.cu
approach: 'Model-level rocWMMA ON/OFF quality A/B: >=100 greedy prompts (-np 1, --cache-ram 0, n_predict 512) reporting token
  identity and first-divergence index. First step: manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*V11\-FA\-4b\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/fattn.cu: f0661dc65131db25cf836a7f6cab3b621e39ce8e
---
