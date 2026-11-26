---
schema: epyc.brief.v1
id: KPF-STATE-COPY-CENSUS
box_text_sha: t:19928690759e7d07
author: intake
written: '2026-11-26'
accepted: auto
where:
- epyc-root:handoffs/active/kv-cache-program.md
- epyc-root:research/deep-dives/intake-nov26-kernels/9644.md
approach: 'Pin trace and source revisions plus the initial state; follow each pointer, dtype and byte count across gather,
  transition and scatter. Compare direct-write candidates to current device replay counts. Include a later trace and poisoned
  non-target slots. Report unresolved copies separately; stop at no remaining transfer. Require unique destination slots and
  read-before-write fences before any aliasing experiment. Count residual transitions separately from the host checkpoint
  copy already covered by Q8-SERVED-CKPT-COPY-1.

  '
acceptance: KPF-STATE-COPY-CENSUS.json contains slot, dtype, source, destination, bytes, barrier, phase. Every state-sized
  copy in the pinned paths has one owner or an explicit unresolved alias.
non_goals: []
tier: local
grounded:
  at: '2026-11-26'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 2711f1bf442a85a9d70e2fe437b06fcd51124bab
    epyc-root:research/deep-dives/intake-nov26-kernels/9644.md: 79ff2d372c5d521a4ba3745b49c643a4dd71e08e
---
