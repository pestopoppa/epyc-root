---
schema: epyc.brief.v1
id: GDN-SLOTS-STRONGER
box_text_sha: t:4d22a540dddf41d1
author: intake
written: '2026-11-24'
accepted: owner
where:
- epyc-llama:tests/test-backend-ops.cpp
- epyc-llama:ggml/src/ggml-cuda/gated_delta_net.cu
approach: 'In test-backend-ops.cpp, add a named GATED_DELTA_NET case at n_tokens > K (e.g. n=300, K=9) on the chunked path
  whose comparison covers every snapshot slot. Name it so a grep finds it, and add a comment pointing to this box. Write the
  slot-guarantee note and the tbo-scope rule into the fold-gate section of kernel-champion-and-promotion.md.

  '
acceptance: witness case committed on the next experimental branch with its SHA, passing on ROCm0 and CPU, and the doc note
  plus scope rule committed in the fold-gate section of this handoff
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:tests/test-backend-ops.cpp: b44bb46a742b7c1e0d6de94d9b59671dd75835d0
    epyc-llama:ggml/src/ggml-cuda/gated_delta_net.cu: 27e580888e7d7092e53ae161dfc29c0c5fe0bacd
---
