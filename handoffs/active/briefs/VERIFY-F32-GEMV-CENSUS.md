---
schema: epyc.brief.v1
id: VERIFY-F32-GEMV-CENSUS
box_text_sha: t:7b608db2085d1f21
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3010.md
- epyc-llama:ggml/src/ggml-cuda/mmvq.cu
approach: 'Completed Q8 w8 and queued fused small-K width 1–4 work do not count F32 rows by M and verify width. Freeze verify
  traces from both dense and MoE, train/test split by request. Report all rows and F32-eligible rows by width, M and K. Preserve
  actual dispatch including width one and wide M; compare incumbent GEMV versus tiled GEMM for surviving bins. On CPU compare
  blocked GEMV to existing GEMM with NUMA-local weights; never import Adreno subgroups or the numeric threshold.

  '
acceptance: Freeze verify traces from both dense and MoE, train/test split by request. Report all rows and F32-eligible rows
  by width, M and K. Preserve actual dispatch including width one and wide M; compare incumbent GEMV versus tiled GEMM for
  surviving bins. On CPU compare blocked GEMV to existing GEMM with NUMA-local weights; never import Adreno subgroups or the
  numeric threshold.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3010.md: 6b25bb5f9ce8723e979cf17c7d08a8c8e488ceaf
    epyc-llama:ggml/src/ggml-cuda/mmvq.cu: 77f711be4fd5b88e514d3f4ecfb3c91e9346164f
---
