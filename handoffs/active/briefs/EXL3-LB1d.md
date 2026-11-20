---
schema: epyc.brief.v1
id: EXL3-LB1d
box_text_sha: dfb0c65f14d7840b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:ggml/src/ggml-cuda/mmvq.cu
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Fold the confirmed MMVQ/MMQ route into the AutoKernel GPU champion via the four-step workflow (fresh production
  to experimental, build, validate, deploy as new version); v11 candidate, never in v10.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-LB1d\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:ggml/src/ggml-cuda/mmvq.cu: 77f711be4fd5b88e514d3f4ecfb3c91e9346164f
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
