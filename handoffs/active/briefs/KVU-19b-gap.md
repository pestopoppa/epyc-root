---
schema: epyc.brief.v1
id: KVU-19b-gap
box_text_sha: 293d978ac86d0869
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:ggml/src/ggml-cuda/fattn.cu
approach: 'Commit 1 trails no-kvu at draft=1 in p3batch; find out why with gemma-3-1b Q8. First step: attribution run manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-19b\-gap\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/fattn.cu: f0661dc65131db25cf836a7f6cab3b621e39ce8e
---
