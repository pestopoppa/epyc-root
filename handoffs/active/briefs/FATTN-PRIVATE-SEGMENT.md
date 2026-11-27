---
schema: epyc.brief.v1
id: FATTN-PRIVATE-SEGMENT
box_text_sha: t:61f323b601472a1d
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3009.md
- epyc-llama:ggml/src/ggml-cuda/fattn-mma-f16.cuh
approach: 'A CUDA stack frame reduction gives no proof of scratch traffic on the active gfx90a specialization. RF7 changes
  wave-level streaming. Compare deployed GPU symbols on a train and holdout context length, retaining code-object hash, VGPR/scratch
  metadata, ISA and dispatch hits. A nonzero private segment alone cannot prove traffic. Stop on absent path or equal material
  scratch traffic; specialize and time only if affected. Check both padded and unpadded tails.

  '
acceptance: Compare deployed GPU symbols on a train and holdout context length, retaining code-object hash, VGPR/scratch metadata,
  ISA and dispatch hits. A nonzero private segment alone cannot prove traffic. Stop on absent path or equal material scratch
  traffic; specialize and time only if affected. Check both padded and unpadded tails.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3009.md: 91bdd0474df6d0063da125c0e9880675e8a42d19
    epyc-llama:ggml/src/ggml-cuda/fattn-mma-f16.cuh: 17bb58932a6ef6db481e5765083ed3ec7eb67c1b
---
