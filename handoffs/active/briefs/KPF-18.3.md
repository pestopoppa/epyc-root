---
schema: epyc.brief.v1
id: KPF-18.3
box_text_sha: 358b7ecd1d6ca35c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/kpf18
approach: 'Chunk-split cost, end-checkpoint position, request lane and warm-vs-cold logprob rows for KPF-18. First step: prefill
  tokens/s and wall with vs without checkpoint_at=[len(trunk)].

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-18\.3\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/kpf18: tree:bc899b86a18dd2f5fffdf8827bb9f2356e1ccc19
---
