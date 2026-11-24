---
schema: epyc.brief.v1
id: RKA-GV-PSCALE-1
box_text_sha: t:c70766206b3d04cc
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:ggml/src/ggml-cuda/fattn.cu
- epyc-llama:tests/test-backend-ops.cpp
approach: 'Add a test-backend-ops FLASH_ATTN_EXT case with GQA-verify shapes (head dim 256, n_q 4-8) whose first key gets
  a +20 logit bias, so P mass concentrates there. Compare max abs error of the gv path and the vector path against CPU. Then
  add an env-gated 2^10 scale before the f16 P store and its inverse in the PV accumulate, and rerun.

  '
acceptance: test case committed with its SHA and the error ratio gv/vector with and without P scaling recorded under this
  box; adopt the scaling (default-off knob, then fold) only if gv error exceeds 2x the vector-path error
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/fattn.cu: f0661dc65131db25cf836a7f6cab3b621e39ce8e
    epyc-llama:tests/test-backend-ops.cpp: b44bb46a742b7c1e0d6de94d9b59671dd75835d0
---
