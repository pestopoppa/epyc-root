---
schema: epyc.brief.v1
id: KVU-19
box_text_sha: fb442b427d6a2b13
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:ggml/src/ggml-cuda/fattn.cu
approach: 'Masked-block skip for unified-KV flash attention on llama.cpp-experimental. First step: next unticked sub-item
  in the box with its kernel test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-19\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/fattn.cu: f0661dc65131db25cf836a7f6cab3b621e39ce8e
---
