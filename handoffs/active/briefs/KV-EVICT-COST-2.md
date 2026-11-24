---
schema: epyc.brief.v1
id: KV-EVICT-COST-2
box_text_sha: t:74ea8cf2d49a296c
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Extend the KV-EVICT-COST-1 table script with two derived columns: compressor and agent seconds from retained prefill
  t/s and context-slope rows per device, with the re-prefill length set by GDN can_shift=false; and rho_cross = 1 - 1/r with
  a mutated-prefix flag. Output break-even trajectory length or NO-GO per device.

  '
acceptance: both columns added to the table under KV-EVICT-COST-1 with per-device break-even length or NO-GO recorded under
  this box
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 2da7db85eebe30ed94eab354c9b7b65a1868f66e
---
