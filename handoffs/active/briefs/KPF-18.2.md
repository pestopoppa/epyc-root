---
schema: epyc.brief.v1
id: KPF-18.2
box_text_sha: 57228c3dc9dd0937
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/kpf18
approach: 'Drafter parity and per-component attribution for KPF-18: MTP-on and MTP-off arms must report identical n_fork_tokens.
  First step: parity check in the runner with a fixture test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-18\.2\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/kpf18: tree:bc899b86a18dd2f5fffdf8827bb9f2356e1ccc19
---
