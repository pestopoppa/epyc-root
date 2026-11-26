---
schema: epyc.brief.v1
id: MOE-STATIC-POOL-REPLAY
box_text_sha: t:3cf0a2e8c890e7de
author: intake
written: '2026-11-26'
accepted: auto
where:
- epyc-root:handoffs/active/cpu-decode-roofline-program.md
- epyc-root:research/deep-dives/intake-nov26-kernels/2611.11533.md
approach: 'Freeze trace manifest, expert sizes, host bandwidth evidence and HBM reservations for weights, KV, scratch and
  allocator margin. Fill the remaining bytes by utility across layers. Fit on early turns, score later whole sessions. Return
  per-turn hits, cold rows, unique bytes, join bound and invalid/unattributed counts. Compare same capacity, loading and phase
  threshold to current placement and host-only. Stop if the saved bytes cannot exceed the join cost within timing uncertainty,
  or if route identities are missing.

  '
acceptance: MOE-STATIC-POOL-REPLAY.json contains reservations_bytes, pool_bytes, unique_upload_bytes, cold_rows, join_bound_ms.
  The pool fits after reservations and all route rows reconcile to resident, cold or unresolved.
non_goals: []
tier: local
grounded:
  at: '2026-11-26'
  blobs:
    epyc-root:handoffs/active/cpu-decode-roofline-program.md: 78e49998dc4a253717b5f591ab72856d295c1c91
    epyc-root:research/deep-dives/intake-nov26-kernels/2611.11533.md: d2e1b060958721b145cfe95f79a763196cbb13fa
---
