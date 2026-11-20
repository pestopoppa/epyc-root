---
schema: epyc.brief.v1
id: KVU-19b
box_text_sha: 55bb9525a3bbdb62
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:ggml/src/ggml-cuda/fattn.cu
approach: 'Per-sequence (per-query-row) block skipping inside a multi-sequence FA tile. First step: prototype on experimental
  tree with the FA nondeterminism test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-19b\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/fattn.cu: f0661dc65131db25cf836a7f6cab3b621e39ce8e
---
