---
schema: epyc.brief.v1
id: KPF-18
box_text_sha: 48eec8ca14a65efb
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/kpf18
approach: 'P1 gate on the GPU window (:8083 production argv on the fork build): matched fork vs no-fork instrument. First
  step: gate manifest; stop on all gate items filed (see KPF-18-S1 for the sweep).

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-18\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/kpf18: tree:bc899b86a18dd2f5fffdf8827bb9f2356e1ccc19
---
