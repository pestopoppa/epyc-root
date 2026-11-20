---
schema: epyc.brief.v1
id: KVU-22
box_text_sha: 8780c76cf6824d3c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Prefill placement rule: fill R_cpu(L) and R_gpu(L, ub) from mi210 roadmap PF1, then decide whether Layer 1 gets
  a length threshold (design only; blocked on PF1). First step: check PF1 result and write the design note.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KVU\-22\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
