---
schema: epyc.brief.v1
id: KVU-19-P5A1
box_text_sha: bb91d1a61401a095
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:ggml/src/ggml-cuda/fattn.cu
approach: 'Full-scale parked-neighbour A1 on the champion: does masked-block skip remove the r3 cost. First step: A1 manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-19\-P5A1\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/fattn.cu: f0661dc65131db25cf836a7f6cab3b621e39ce8e
---
