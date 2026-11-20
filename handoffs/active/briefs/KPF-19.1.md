---
schema: epyc.brief.v1
id: KPF-19.1
box_text_sha: 9003b2901f04de14
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/server/server-context.cpp
approach: 'Explicit drafter restore before any rebase that takes #30514 (ckpt.load_dft(ctx_dft, dst.id, PARTIAL_ONLY) at server-context.cpp:1886
  restores the whole plain-KV drafter KV). First step: explicit restore change on the experimental fork branch with test_kpf191.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-19\.1\b' handoffs/active/kv-cache-program.md
non_goals:
- kernel edits only on llama.cpp-experimental, never the frozen production tree
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/server/server-context.cpp: 07544da91b739bcf8d83f95155841ce39e397ec4
---
