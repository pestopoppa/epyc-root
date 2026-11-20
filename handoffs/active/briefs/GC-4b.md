---
schema: epyc.brief.v1
id: GC-4b
box_text_sha: t:2da9f3068e514d75
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reference/glm52-ram-residency-decision-input-2026-07-18.md
- epyc-root:handoffs/active/deepseek-v41-flash-evaluation.md
approach: 'Sizing input only: re-size V4.1-Flash residency against the real artifact (~483 GiB file; ~189 GiB native FP8 Engram
  n-gram tables, disk-streamable; always-resident ~294 GiB Q4_K experts plus Q8 attention/shared/output, before KV). Write
  a short memory-budget table (resident vs mmap-streamed Engram) and mark the policy as an operator decision (section A00).
  Step: read the actual GGUF header sizes now; the Engram access-pattern measurement waits on the port load.

  '
acceptance: test -f docs/reference/ds41-flash-ram-residency-sizing-input.md
non_goals:
- no residency policy decision
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reference/glm52-ram-residency-decision-input-2026-07-18.md: d3d322c018d77af27ebb3c85d5781d5f0796a0c0
    epyc-root:handoffs/active/deepseek-v41-flash-evaluation.md: 1f242655f90ad01ef9512b6a70f229762aa6a205
---
