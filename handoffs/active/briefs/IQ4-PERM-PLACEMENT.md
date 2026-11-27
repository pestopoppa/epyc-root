---
schema: epyc.brief.v1
id: IQ4-PERM-PLACEMENT
box_text_sha: t:9549116a48e93a55
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3007.md
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3021.md
- epyc-llama:ggml/src/ggml-cuda/vecdotq.cuh
approach: 'Both IQ4 vector dots already call get_int_from_table_16 with HIP permutes; EXL3 codebooks need their own representation
  proof. Freeze the full nibble, sign and scale oracle and retained kernel traces; compare existing permute helper with alternative
  decode-to-issue placement at equal layout. On wave64 price VGPR occupancy, 64 KB LDS per CU, memory stalls, MFMA issue and
  spills. Reject a numerical mismatch; require improvement on later actual shapes before a served trial. CPU analogue is lane-local
  byte shuffles plus widened signed dot, measured separately.

  '
acceptance: Freeze the full nibble, sign and scale oracle and retained kernel traces; compare existing permute helper with
  alternative decode-to-issue placement at equal layout. On wave64 price VGPR occupancy, 64 KB LDS per CU, memory stalls,
  MFMA issue and spills. Reject a numerical mismatch; require improvement on later actual shapes before a served trial. CPU
  analogue is lane-local byte shuffles plus widened signed dot, measured separately.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3007.md: e82a2b61bcb8391f47382cb31cd5afe91238ff91
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3021.md: debd1b6a01380017c5389fba1a17833f6dc46390
    epyc-llama:ggml/src/ggml-cuda/vecdotq.cuh: f9c802737ed6b6f7961206b7134df563889ad221
---
