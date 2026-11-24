---
schema: epyc.brief.v1
id: AK-GVFATTN-Q4KV-DESIGN
box_text_sha: t:ad4d33fc7a0d0f3e
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:ggml/src/ggml-cuda/fattn.cu
- epyc-llama:ggml/src/ggml-quants.c::dequantize_row_q4_0
approach: 'Write a numpy oracle that reproduces block_q4_0 nibble order into 16x16x16 MFMA A/B lane fragments and compare
  it bit-exact with dequantize_row_q4_0 on random blocks. Compile both decode snippets with hipcc --save-temps for gfx90a
  and count v_* instructions per value. Read 5141da459''s fattn-gqa-verify.cu and write the review note against its LDS layout.
  Annotate AK-GVFATTN-LONGCTX with the R = 42 tile arithmetic.

  '
acceptance: oracle test committed and passing bit-exact, the instruction-count table, and the review note filed under this
  box and linked from the ak-gvfattn-q4kv-gpu-20261124 row, with the AK-GVFATTN-LONGCTX premise correction recorded, each
  with its commit SHA
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/fattn.cu: f0661dc65131db25cf836a7f6cab3b621e39ce8e
    epyc-llama:ggml/src/ggml-quants.c: 1ebc50a763f16db909de37090da38cc8c0fdde94
---
