---
schema: epyc.brief.v1
id: EXL3-4
box_text_sha: 67a9ff1b49cab055
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/kernels.hip
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/test_runtime.hip
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/README.md
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Epic: standalone FP16/FP32 16x16x16 MFMA lane-map harness first, then packed trellis tile decode into fragments;
  first step is the lane-map harness with full 256-cell device lane check.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-4\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/kernels.hip: 10cc7690bc1baa7bf6367fd1033ee23fd731ec43
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/test_runtime.hip: 556ae92e73e20171e4bf14620dbfdd759528e684
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/README.md: 7593c6ea2c3fa6c2d3c6f5057f08fd6ed40b85bb
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
