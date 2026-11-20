---
schema: epyc.brief.v1
id: KPF-18.1
box_text_sha: 52e92f46208defae
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/kpf18
approach: 'Hit-length rows for the KPF-18 gate: arm A trunk-then-private-suffix with checkpoint_at=[len(trunk)] vs tail-only
  etc., --slot-fork-min-tokens 0 vs on. First step: arm runner extension and manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-18\.1\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/kpf18: tree:bc899b86a18dd2f5fffdf8827bb9f2356e1ccc19
---
