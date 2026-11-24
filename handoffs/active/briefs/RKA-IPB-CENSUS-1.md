---
schema: epyc.brief.v1
id: RKA-IPB-CENSUS-1
box_text_sha: t:0be4f6da40ac3a5e
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-llama:ggml/src/ggml-cuda/fattn.cu
approach: 'Run rocprofv3 --pmc SQ_INSTS_VALU SQ_INSTS_SALU SQ_INSTS_LDS SQ_WAVES SQ_BUSY_CYCLES on llama-bench (or the verify
  harness) with the 27B verify shapes, filtered to the gv_fattn kernel name. Divide instruction counts by the KV bytes per
  call and compare with the device issue budget (CUs x SIMD issue rate over HBM bandwidth).

  '
acceptance: 'per-shape instructions-per-byte and VALU utilisation filed under this box with the run path, and the verdict:
  >= 50% VALU utilisation means a decode diet comes first in AK-GVFATTN-Q4KV, <= 25% means LDS residency comes first'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/fattn.cu: f0661dc65131db25cf836a7f6cab3b621e39ce8e
---
